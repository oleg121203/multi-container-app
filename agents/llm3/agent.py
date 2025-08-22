"""
LLM3 Security Agent - Security monitoring and automated response

This agent integrates with Falco security monitoring to analyze security events
and trigger automated responses according to configurable policies.
"""

import asyncio
import logging
import json
import os
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import aiohttp
import uvicorn

logger = logging.getLogger(__name__)


class SecurityEventSeverity(Enum):
    """Security event severity levels"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class MitigationAction(Enum):
    """Available mitigation actions"""
    CORDON_NODE = "cordon_node"
    DELETE_POD = "delete_pod"
    ISOLATE_CONTAINER = "isolate_container"
    BLOCK_IP = "block_ip"
    ALERT_ONLY = "alert_only"
    QUARANTINE_NAMESPACE = "quarantine_namespace"


@dataclass
class SecurityEvent:
    """Security event from Falco"""
    time: str
    rule: str
    priority: str
    output: str
    source: str = "falco"
    proc: Optional[Dict[str, Any]] = None
    k8s: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class MitigationDecision:
    """Decision made by LLM3 for security event"""
    event_id: str
    severity: SecurityEventSeverity
    recommended_actions: List[MitigationAction]
    rationale: str
    confidence: float
    auto_execute: bool
    timestamp: float


class FalcoEventRequest(BaseModel):
    """Request model for Falco events"""
    time: str
    rule: str
    priority: str
    output: str
    source: str = "falco"
    proc: Optional[Dict[str, Any]] = None
    k8s: Optional[Dict[str, Any]] = None


class LLM3SecurityAgent:
    """LLM3 Security Agent for automated threat response"""
    
    def __init__(self):
        self.app = FastAPI(
            title="LLM3 Security Agent",
            description="Security monitoring and automated response agent",
            version="1.0.0"
        )
        
        # Configuration
        self.auto_mitigation_enabled = os.getenv('ATLAS_LLM3_AUTO_MITIGATION', 'false').lower() == 'true'
        self.severity_threshold = os.getenv('ATLAS_LLM3_SEVERITY_THRESHOLD', 'HIGH')
        self.k8s_api_url = os.getenv('KUBERNETES_SERVICE_HOST', 'kubernetes.default.svc.cluster.local')
        self.k8s_token_file = '/var/run/secrets/kubernetes.io/serviceaccount/token'
        
        # LLM configuration
        self.llm_provider = os.getenv('ATLAS_LLM3_PROVIDER', 'openai')
        self.llm_model = os.getenv('ATLAS_LLM3_MODEL', 'gpt-4o-mini')
        self.api_key = os.getenv('ATLAS_LLM3_API_KEY', os.getenv('OPENAI_API_KEY'))
        
        # Security policy
        self.security_policies = self._load_security_policies()
        
        # Event tracking
        self.processed_events = {}
        self.audit_log = []
        
        self.setup_routes()
    
    def _load_security_policies(self) -> Dict[str, Any]:
        """Load security policies from configuration"""
        default_policies = {
            "critical_rules": [
                "Write below etc",
                "Shell spawned by untrusted binary",
                "Container drift detected",
                "Unauthorized process in container"
            ],
            "auto_actions": {
                "Write below etc": [MitigationAction.DELETE_POD, MitigationAction.ALERT_ONLY],
                "Shell spawned by untrusted binary": [MitigationAction.ISOLATE_CONTAINER],
                "Container drift detected": [MitigationAction.DELETE_POD],
                "default": [MitigationAction.ALERT_ONLY]
            },
            "namespace_allowlist": ["kube-system", "kube-public"],
            "auto_mitigation_cooldown": 300  # 5 minutes
        }
        
        # TODO: Load from external configuration file
        return default_policies
    
    def setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "ok", 
                "service": "llm3-security-agent",
                "auto_mitigation": self.auto_mitigation_enabled
            }
        
        @self.app.post("/falco-event")
        async def receive_falco_event(
            event: FalcoEventRequest, 
            background_tasks: BackgroundTasks
        ):
            """Receive and process Falco security events"""
            try:
                security_event = SecurityEvent(
                    time=event.time,
                    rule=event.rule,
                    priority=event.priority,
                    output=event.output,
                    source=event.source,
                    proc=event.proc,
                    k8s=event.k8s
                )
                
                # Process event in background
                background_tasks.add_task(self._process_security_event, security_event)
                
                return {"status": "received", "event_id": f"{event.time}_{hash(event.rule)}"}
                
            except Exception as e:
                logger.error(f"Error processing Falco event: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/audit-log")
        async def get_audit_log(limit: int = 100):
            """Get security audit log"""
            return {
                "audit_log": self.audit_log[-limit:],
                "total_events": len(self.processed_events)
            }
        
        @self.app.get("/policies")
        async def get_security_policies():
            """Get current security policies"""
            return self.security_policies
        
        @self.app.post("/test-event")
        async def test_security_event(event: FalcoEventRequest, background_tasks: BackgroundTasks):
            """Test endpoint for security event processing"""
            await self.receive_falco_event(event, background_tasks)
            return {"status": "test_event_submitted"}
    
    async def _process_security_event(self, event: SecurityEvent):
        """Process a security event and determine response"""
        event_id = f"{event.time}_{hash(event.rule)}"
        
        logger.info(f"Processing security event: {event.rule} [ID: {event_id}]")
        
        try:
            # Analyze event with LLM
            decision = await self._analyze_security_event(event)
            
            # Store decision
            self.processed_events[event_id] = {
                "event": event,
                "decision": decision,
                "processed_at": time.time()
            }
            
            # Log to audit trail
            audit_entry = {
                "timestamp": time.time(),
                "event_id": event_id,
                "rule": event.rule,
                "priority": event.priority,
                "decision": {
                    "severity": decision.severity.value,
                    "actions": [action.value for action in decision.recommended_actions],
                    "rationale": decision.rationale,
                    "auto_execute": decision.auto_execute
                }
            }
            self.audit_log.append(audit_entry)
            
            # Execute mitigation if approved
            if decision.auto_execute and self.auto_mitigation_enabled:
                await self._execute_mitigation_actions(event, decision)
            else:
                logger.info(f"Manual approval required for event {event_id}")
                
        except Exception as e:
            logger.error(f"Error processing security event {event_id}: {e}")
    
    async def _analyze_security_event(self, event: SecurityEvent) -> MitigationDecision:
        """Analyze security event using LLM to determine response"""
        
        # Prepare context for LLM analysis
        context = {
            "event": {
                "rule": event.rule,
                "priority": event.priority,
                "output": event.output,
                "time": event.time
            },
            "kubernetes_context": event.k8s,
            "process_context": event.proc,
            "security_policies": self.security_policies
        }
        
        # Create prompt for security analysis
        prompt = f"""
Analyze this security event and recommend appropriate mitigation actions:

Event Details:
- Rule: {event.rule}
- Priority: {event.priority}
- Output: {event.output}
- Time: {event.time}

Kubernetes Context: {json.dumps(event.k8s, indent=2) if event.k8s else 'None'}
Process Context: {json.dumps(event.proc, indent=2) if event.proc else 'None'}

Security Policies: {json.dumps(self.security_policies, indent=2)}

Provide analysis in JSON format:
{{
    "severity": "CRITICAL|HIGH|MEDIUM|LOW|INFO",
    "recommended_actions": ["action1", "action2"],
    "rationale": "explanation of why these actions are recommended",
    "confidence": 0.0-1.0,
    "auto_execute": true/false
}}

Available actions: cordon_node, delete_pod, isolate_container, block_ip, alert_only, quarantine_namespace
"""
        
        try:
            # Call LLM for analysis
            llm_response = await self._call_llm(prompt)
            
            # Parse LLM response
            analysis = json.loads(llm_response)
            
            # Create decision object
            decision = MitigationDecision(
                event_id=f"{event.time}_{hash(event.rule)}",
                severity=SecurityEventSeverity(analysis.get('severity', 'LOW')),
                recommended_actions=[
                    MitigationAction(action) for action in analysis.get('recommended_actions', ['alert_only'])
                ],
                rationale=analysis.get('rationale', 'No rationale provided'),
                confidence=float(analysis.get('confidence', 0.5)),
                auto_execute=bool(analysis.get('auto_execute', False)),
                timestamp=time.time()
            )
            
            # Apply security policies
            decision = self._apply_security_policies(event, decision)
            
            return decision
            
        except Exception as e:
            logger.error(f"Error in LLM analysis: {e}")
            # Fallback to rule-based decision
            return self._fallback_analysis(event)
    
    def _apply_security_policies(self, event: SecurityEvent, decision: MitigationDecision) -> MitigationDecision:
        """Apply security policies to override or modify LLM decision"""
        
        # Check if namespace is in allowlist
        if event.k8s and event.k8s.get('namespace') in self.security_policies.get('namespace_allowlist', []):
            decision.auto_execute = False
            decision.rationale += " (Protected namespace - manual approval required)"
        
        # Check cooldown period
        recent_events = [
            e for e in self.processed_events.values()
            if time.time() - e['processed_at'] < self.security_policies.get('auto_mitigation_cooldown', 300)
        ]
        
        if len(recent_events) > 3:  # Rate limiting
            decision.auto_execute = False
            decision.rationale += " (Rate limited - too many recent events)"
        
        # Override based on severity threshold
        severity_levels = {'CRITICAL': 4, 'HIGH': 3, 'MEDIUM': 2, 'LOW': 1, 'INFO': 0}
        threshold_level = severity_levels.get(self.severity_threshold, 3)
        event_level = severity_levels.get(decision.severity.value, 0)
        
        if event_level < threshold_level:
            decision.auto_execute = False
        
        return decision
    
    def _fallback_analysis(self, event: SecurityEvent) -> MitigationDecision:
        """Fallback rule-based analysis when LLM fails"""
        
        # Map priority to severity
        priority_mapping = {
            'CRITICAL': SecurityEventSeverity.CRITICAL,
            'ERROR': SecurityEventSeverity.HIGH,
            'WARNING': SecurityEventSeverity.MEDIUM,
            'NOTICE': SecurityEventSeverity.LOW,
            'INFORMATIONAL': SecurityEventSeverity.INFO
        }
        
        severity = priority_mapping.get(event.priority, SecurityEventSeverity.LOW)
        
        # Get actions from policy
        rule_actions = self.security_policies['auto_actions'].get(
            event.rule,
            self.security_policies['auto_actions']['default']
        )
        
        return MitigationDecision(
            event_id=f"{event.time}_{hash(event.rule)}",
            severity=severity,
            recommended_actions=rule_actions,
            rationale=f"Rule-based fallback for {event.rule}",
            confidence=0.7,
            auto_execute=severity in [SecurityEventSeverity.CRITICAL, SecurityEventSeverity.HIGH],
            timestamp=time.time()
        )
    
    async def _call_llm(self, prompt: str) -> str:
        """Call LLM for security analysis"""
        
        if self.llm_provider == 'openai':
            return await self._call_openai(prompt)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.llm_provider}")
    
    async def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API for analysis"""
        
        if not self.api_key:
            raise ValueError("OpenAI API key not configured")
        
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.llm_model,
            "messages": [
                {"role": "system", "content": "You are a security analyst. Analyze security events and provide JSON responses."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 1000
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return data['choices'][0]['message']['content']
                else:
                    error_text = await response.text()
                    raise Exception(f"OpenAI API error: {response.status} - {error_text}")
    
    async def _execute_mitigation_actions(self, event: SecurityEvent, decision: MitigationDecision):
        """Execute approved mitigation actions"""
        
        logger.info(f"Executing mitigation actions for event: {decision.event_id}")
        
        for action in decision.recommended_actions:
            try:
                if action == MitigationAction.DELETE_POD:
                    await self._delete_pod(event)
                elif action == MitigationAction.CORDON_NODE:
                    await self._cordon_node(event)
                elif action == MitigationAction.ISOLATE_CONTAINER:
                    await self._isolate_container(event)
                elif action == MitigationAction.QUARANTINE_NAMESPACE:
                    await self._quarantine_namespace(event)
                elif action == MitigationAction.ALERT_ONLY:
                    await self._send_alert(event, decision)
                else:
                    logger.warning(f"Unsupported action: {action}")
                    
                logger.info(f"Successfully executed action: {action.value}")
                
            except Exception as e:
                logger.error(f"Failed to execute action {action.value}: {e}")
    
    async def _delete_pod(self, event: SecurityEvent):
        """Delete the pod associated with the security event"""
        if not event.k8s or not event.k8s.get('pod_name'):
            logger.warning("No pod information available for deletion")
            return
        
        # Mock implementation - would use Kubernetes API
        logger.info(f"MOCK: Deleting pod {event.k8s['pod_name']} in namespace {event.k8s.get('namespace', 'default')}")
    
    async def _cordon_node(self, event: SecurityEvent):
        """Cordon the node associated with the security event"""
        if not event.k8s or not event.k8s.get('node_name'):
            logger.warning("No node information available for cordoning")
            return
        
        # Mock implementation - would use Kubernetes API
        logger.info(f"MOCK: Cordoning node {event.k8s['node_name']}")
    
    async def _isolate_container(self, event: SecurityEvent):
        """Isolate the container associated with the security event"""
        if not event.k8s or not event.k8s.get('container_id'):
            logger.warning("No container information available for isolation")
            return
        
        # Mock implementation - would use container runtime API
        logger.info(f"MOCK: Isolating container {event.k8s['container_id']}")
    
    async def _quarantine_namespace(self, event: SecurityEvent):
        """Apply network policies to quarantine a namespace"""
        if not event.k8s or not event.k8s.get('namespace'):
            logger.warning("No namespace information available for quarantine")
            return
        
        # Mock implementation - would create restrictive NetworkPolicy
        logger.info(f"MOCK: Quarantining namespace {event.k8s['namespace']}")
    
    async def _send_alert(self, event: SecurityEvent, decision: MitigationDecision):
        """Send alert for security event"""
        alert_data = {
            "event": event.__dict__,
            "decision": decision.__dict__,
            "timestamp": time.time()
        }
        
        # Mock implementation - would send to alerting system
        logger.warning(f"SECURITY ALERT: {event.rule} - {decision.rationale}")


# Global agent instance
llm3_agent = LLM3SecurityAgent()


async def main():
    """Main entry point for LLM3 Security Agent"""
    import signal
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("Starting LLM3 Security Agent")
    
    # Setup graceful shutdown
    def signal_handler(signum, frame):
        logger.info("Received shutdown signal")
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start HTTP server
    config = uvicorn.Config(
        llm3_agent.app,
        host="0.0.0.0",
        port=int(os.getenv('ATLAS_LLM3_PORT', '8003')),
        log_level="info"
    )
    
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
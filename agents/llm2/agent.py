"""
LLM2 Agent - Orchestrator with Ollama, AutoGen, and MCP Hub integration
Local task orchestration with strict Ollama preference, Linear tool integration, and MCP services
"""
import logging
import asyncio
import os
from typing import List, Dict, Optional, Any
import uuid
from dataclasses import dataclass
from datetime import datetime
import json

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

# AutoGen import with fallback for local development
try:
    import autogen
    from autogen import AssistantAgent, UserProxyAgent
    AUTOGEN_AVAILABLE = True
except ImportError:
    try:
        # Try importing pyautogen dynamically to avoid static import errors
        import importlib
        _pyautogen = importlib.import_module('pyautogen')
        autogen = _pyautogen  # type: ignore[assignment]
        AssistantAgent = getattr(_pyautogen, 'AssistantAgent')  # type: ignore[assignment]
        UserProxyAgent = getattr(_pyautogen, 'UserProxyAgent')  # type: ignore[assignment]
        AUTOGEN_AVAILABLE = True
    except Exception:
        # Fallback for local development without autogen
        print("Warning: AutoGen not available - some features will be disabled")
        AUTOGEN_AVAILABLE = False
        autogen = None
        
        # Create mock classes for type checking
        class MockAssistantAgent:
            def __init__(self, *args, **kwargs):
                pass
                
        class MockUserProxyAgent:
            def __init__(self, *args, **kwargs):
                pass
                
        AssistantAgent = MockAssistantAgent  # type: ignore[assignment]
        UserProxyAgent = MockUserProxyAgent  # type: ignore[assignment]

from shared.config import config
from shared.llm_providers import LLMProviderManager, LLMProvider, OllamaProvider
from shared.linear_tool import LinearClient, LinearIssue, IssuePriority

logger = logging.getLogger(__name__)

# Phase 3: Import MCP Hub integration
try:
    from mcp_hub.registry import mcp_registry
    from mcp_hub.client import mcp_client
    MCP_AVAILABLE = True
except ImportError:
    logger.warning("MCP Hub not available - MCP functionality disabled")
    MCP_AVAILABLE = False


class TaskRequest(BaseModel):
    description: str
    requester_id: str
    priority: str = "medium"
    team_id: Optional[str] = None
    metadata: Dict[str, Any] = {}


class TaskResponse(BaseModel):
    task_id: str
    status: str
    linear_issue: Optional[Dict[str, Any]] = None
    execution_plan: List[str]
    agent_used: str
    fallback_used: bool


class HealthStatus(BaseModel):
    ollama_healthy: bool
    linear_healthy: bool
    fallback_enabled: bool
    audit_log_count: int


@dataclass
class AuditLogEntry:
    timestamp: datetime
    event_type: str  # "fallback_used", "ollama_failed", "task_created", etc.
    details: Dict[str, Any]
    severity: str  # "info", "warning", "error"


class LLM2Agent:
    """LLM2 Orchestrator Agent with Ollama preference and Linear integration"""
    
    def __init__(self):
        self.llm_manager = LLMProviderManager()
        self.ollama_provider = OllamaProvider(
            host=config.OLLAMA_HOST,
            port=config.OLLAMA_PORT,
            model=config.OLLAMA_MODEL
        )
        self.linear_client = LinearClient()
        
        # Phase 3: MCP Hub integration
        self.mcp_enabled = MCP_AVAILABLE and os.getenv('ATLAS_MCP_SERVERS', '')
        if self.mcp_enabled:
            logger.info("MCP Hub integration enabled")
        else:
            logger.info("MCP Hub integration disabled")
            
        self.audit_log: List[AuditLogEntry] = []
        self.app = FastAPI(title="LLM2 Orchestrator API", version="1.0.0")
        self._setup_routes()
        
        # AutoGen agents setup
        self.assistant_agent = None
        self.user_proxy = None
        self._setup_autogen()
    
    def _setup_autogen(self):
        """Setup AutoGen agents for orchestration"""
        
        if not AUTOGEN_AVAILABLE:
            logger.warning("AutoGen not available - disabling multi-agent orchestration")
            self.assistant_agent = None
            self.user_proxy = None
            return
        
        # Configure LLM for AutoGen to use Ollama
        llm_config = {
            "config_list": [
                {
                    "model": config.OLLAMA_MODEL,
                    "base_url": f"http://{config.OLLAMA_HOST}:{config.OLLAMA_PORT}/v1",
                    "api_key": "dummy"  # Ollama doesn't require API key
                }
            ],
            "timeout": 60,
            "temperature": 0.7
        }
        
        # Create assistant agent for task planning
        self.assistant_agent = AssistantAgent(
            name="task_planner",
            system_message="""You are a task planning assistant in the ATLAS multi-agent system.
            Your role is to:
            1. Break down user requests into actionable tasks
            2. Create issues in Linear for task tracking
            3. Provide clear execution plans
            
            When creating Linear issues, always include:
            - Clear, descriptive title
            - Detailed description with acceptance criteria
            - Appropriate priority level
            
            Keep responses concise and action-oriented.""",
            llm_config=llm_config
        )
        
        # Create user proxy for execution
        self.user_proxy = UserProxyAgent(
            name="task_executor",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=1,
            code_execution_config=False
        )
    
    async def initialize(self):
        """Initialize all components"""
        await self.linear_client.initialize()
        
        # Phase 3: Initialize MCP Hub if enabled
        if self.mcp_enabled:
            try:
                await mcp_registry.start()
                await mcp_client.start()
                logger.info("MCP Hub initialized successfully")
                await self._log_audit_event(
                    "mcp_hub_initialized", 
                    {"servers_count": len(mcp_registry.servers)}, 
                    "info"
                )
            except Exception as e:
                logger.error(f"Failed to initialize MCP Hub: {e}")
                await self._log_audit_event("mcp_hub_init_failed", {"error": str(e)}, "error")
        
        await self._log_audit_event("system_initialized", {"timestamp": datetime.now().isoformat()}, "info")
        logger.info("LLM2 Agent initialized")
    
    async def shutdown(self):
        """Shutdown all components"""
        await self.linear_client.close()
        
        # Phase 3: Shutdown MCP Hub if enabled
        if self.mcp_enabled:
            try:
                await mcp_client.stop()
                await mcp_registry.stop()
                logger.info("MCP Hub shutdown successfully")
            except Exception as e:
                logger.error(f"Error shutting down MCP Hub: {e}")
        
        logger.info("LLM2 Agent shutdown")
    
    def _setup_routes(self):
        """Setup FastAPI routes"""
        
        @self.app.post("/process_task", response_model=TaskResponse)
        async def process_task(task_request: TaskRequest):
            return await self.process_task_request(task_request)
        
        @self.app.get("/health", response_model=HealthStatus)
        async def health_check():
            return await self.check_health()
        
        @self.app.get("/audit_log")
        async def get_audit_log(limit: int = 50):
            """Get recent audit log entries"""
            recent_entries = self.audit_log[-limit:]
            return {
                "entries": [
                    {
                        "timestamp": entry.timestamp.isoformat(),
                        "event_type": entry.event_type,
                        "details": entry.details,
                        "severity": entry.severity
                    }
                    for entry in recent_entries
                ],
                "total_count": len(self.audit_log)
            }
        
        # Phase 3: MCP Hub endpoints
        @self.app.post("/mcp/execute")
        async def execute_mcp_action(action_request: dict):
            """Execute an action via MCP Hub"""
            if not self.mcp_enabled:
                raise HTTPException(status_code=503, detail="MCP Hub not enabled")
            
            try:
                action = action_request.get('action')
                args = action_request.get('args', {})
                server_preference = action_request.get('server_preference')
                
                # Validate required parameters
                if not action or not isinstance(action, str):
                    raise HTTPException(status_code=400, detail="Action parameter is required and must be a string")
                
                result = await mcp_client.execute_action(
                    action=action,
                    args=args,
                    server_preference=server_preference
                )
                
                await self._log_audit_event(
                    "mcp_action_executed",
                    {
                        "action": action,
                        "server_used": result.server_used,
                        "status": result.status.value,
                        "execution_time_ms": result.execution_time_ms
                    },
                    "info"
                )
                
                return {
                    "status": result.status.value,
                    "result": result.result,
                    "server_used": result.server_used,
                    "execution_time_ms": result.execution_time_ms,
                    "correlation_id": result.correlation_id
                }
                
            except Exception as e:
                await self._log_audit_event("mcp_action_failed", {"error": str(e)}, "error")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/mcp/servers")
        async def get_mcp_servers():
            """Get status of MCP servers"""
            if not self.mcp_enabled:
                raise HTTPException(status_code=503, detail="MCP Hub not enabled")
            
            return mcp_registry.get_registry_status()
        
        @self.app.get("/mcp/capabilities")
        async def get_mcp_capabilities():
            """Get available MCP capabilities"""
            if not self.mcp_enabled:
                raise HTTPException(status_code=503, detail="MCP Hub not enabled")
            
            return await mcp_client.get_available_capabilities()
        
        @self.app.get("/ollama_status")
        async def ollama_status():
            """Check Ollama service status"""
            try:
                is_healthy = await self.ollama_provider.health_check()
                return {
                    "status": "healthy" if is_healthy else "unhealthy",
                    "host": config.OLLAMA_HOST,
                    "port": config.OLLAMA_PORT,
                    "model": config.OLLAMA_MODEL,
                    "fallback_enabled": config.ATLAS_LLM2_ALLOW_FALLBACK
                }
            except Exception as e:
                await self._log_audit_event("ollama_check_failed", {"error": str(e)}, "error")
                return {"status": "error", "error": str(e)}
    
    async def _log_audit_event(self, event_type: str, details: Dict[str, Any], severity: str = "info"):
        """Log audit event"""
        entry = AuditLogEntry(
            timestamp=datetime.now(),
            event_type=event_type,
            details=details,
            severity=severity
        )
        self.audit_log.append(entry)
        
        # Keep only last 1000 entries to prevent memory issues
        if len(self.audit_log) > 1000:
            self.audit_log = self.audit_log[-1000:]
        
        logger.info(f"Audit: {event_type} - {details}")
    
    async def check_health(self) -> HealthStatus:
        """Comprehensive health check"""
        try:
            # Check Ollama
            ollama_healthy = await self.ollama_provider.health_check()
            if not ollama_healthy:
                await self._log_audit_event("ollama_unhealthy", {}, "warning")
            
            # Check Linear
            linear_healthy = await self.linear_client.health_check()
            if not linear_healthy:
                await self._log_audit_event("linear_unhealthy", {}, "warning")
            
            return HealthStatus(
                ollama_healthy=ollama_healthy,
                linear_healthy=linear_healthy,
                fallback_enabled=config.ATLAS_LLM2_ALLOW_FALLBACK,
                audit_log_count=len(self.audit_log)
            )
            
        except Exception as e:
            await self._log_audit_event("health_check_failed", {"error": str(e)}, "error")
            raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")
    
    async def _generate_with_ollama_preference(self, prompt: str, **kwargs) -> Any:
        """Generate response with strict Ollama preference"""
        try:
            # Always try Ollama first
            response = await self.ollama_provider.generate(prompt, **kwargs)
            await self._log_audit_event("ollama_used", {"model": config.OLLAMA_MODEL}, "info")
            return response, False  # No fallback used
            
        except Exception as e:
            await self._log_audit_event("ollama_failed", {"error": str(e)}, "warning")
            
            # Check if fallback is allowed
            if not config.ATLAS_LLM2_ALLOW_FALLBACK:
                await self._log_audit_event("fallback_denied", {"policy": "ATLAS_LLM2_ALLOW_FALLBACK=false"}, "error")
                raise Exception(f"Ollama failed and fallback is disabled: {str(e)}")
            
            # Use fallback chain
            await self._log_audit_event("fallback_initiated", {"original_error": str(e)}, "warning")
            
            try:
                response = await self.llm_manager.generate(
                    prompt,
                    preferred_provider=None,  # Skip Ollama in fallback
                    allow_fallback=True,
                    **kwargs
                )
                await self._log_audit_event("fallback_succeeded", {"provider": response.provider.value}, "info")
                return response, True  # Fallback used
                
            except Exception as fallback_error:
                await self._log_audit_event("fallback_failed", {"error": str(fallback_error)}, "error")
                raise Exception(f"Both Ollama and fallback failed: {str(fallback_error)}")
    
    def _parse_priority(self, priority_str: str) -> IssuePriority:
        """Parse priority string to enum"""
        priority_map = {
            "urgent": IssuePriority.URGENT,
            "high": IssuePriority.HIGH,
            "medium": IssuePriority.MEDIUM,
            "low": IssuePriority.LOW
        }
        return priority_map.get(priority_str.lower(), IssuePriority.MEDIUM)
    
    async def process_task_request(self, task_request: TaskRequest) -> TaskResponse:
        """Process task request using AutoGen orchestration"""
        try:
            task_id = str(uuid.uuid4())
            
            await self._log_audit_event(
                "task_received", 
                {
                    "task_id": task_id,
                    "description": task_request.description,
                    "requester": task_request.requester_id
                }, 
                "info"
            )
            
            # Create planning prompt
            planning_prompt = f"""
            Task Request: {task_request.description}
            Requester: {task_request.requester_id}
            Priority: {task_request.priority}
            
            Please analyze this task and provide:
            1. A clear breakdown of what needs to be done
            2. Suggested Linear issue title and description
            3. Recommended execution steps
            
            Format your response as JSON with these fields:
            - issue_title: string
            - issue_description: string
            - execution_plan: array of strings
            - analysis: string
            """
            
            # Generate task plan using Ollama-preferred approach
            llm_response, fallback_used = await self._generate_with_ollama_preference(
                planning_prompt,
                max_tokens=1000,
                temperature=0.7
            )
            
            # Try to parse the response as JSON, with fallback to text parsing
            try:
                if llm_response.content.strip().startswith('{'):
                    plan_data = json.loads(llm_response.content)
                else:
                    # Fallback: extract information from text response
                    plan_data = self._extract_plan_from_text(llm_response.content, task_request.description)
            except json.JSONDecodeError:
                plan_data = self._extract_plan_from_text(llm_response.content, task_request.description)
            
            # Create Linear issue if we have team_id
            linear_issue = None
            if task_request.team_id:
                try:
                    priority = self._parse_priority(task_request.priority)
                    issue = await self.linear_client.create_issue(
                        title=plan_data.get("issue_title", f"Task: {task_request.description[:50]}..."),
                        team_id=task_request.team_id,
                        description=plan_data.get("issue_description", task_request.description),
                        priority=priority
                    )
                    
                    linear_issue = {
                        "id": issue.id,
                        "title": issue.title,
                        "url": issue.url,
                        "identifier": issue.identifier
                    }
                    
                    await self._log_audit_event(
                        "linear_issue_created",
                        {
                            "task_id": task_id,
                            "issue_id": issue.id,
                            "issue_url": issue.url
                        },
                        "info"
                    )
                    
                except Exception as e:
                    await self._log_audit_event(
                        "linear_issue_failed",
                        {"task_id": task_id, "error": str(e)},
                        "error"
                    )
            
            execution_plan = plan_data.get("execution_plan", [
                "Analyze requirements",
                "Plan implementation",
                "Execute task",
                "Verify completion"
            ])
            
            return TaskResponse(
                task_id=task_id,
                status="planned",
                linear_issue=linear_issue,
                execution_plan=execution_plan,
                agent_used=llm_response.provider.value,
                fallback_used=fallback_used
            )
            
        except Exception as e:
            await self._log_audit_event(
                "task_processing_failed",
                {"description": task_request.description, "error": str(e)},
                "error"
            )
            raise HTTPException(status_code=500, detail=f"Failed to process task: {str(e)}")
    
    def _extract_plan_from_text(self, response_text: str, original_description: str) -> Dict[str, Any]:
        """Extract plan information from text response (fallback method)"""
        lines = response_text.split('\n')
        
        # Simple extraction logic
        issue_title = f"Task: {original_description[:50]}..."
        issue_description = original_description
        execution_plan = [
            "Analyze requirements",
            "Plan implementation", 
            "Execute task",
            "Verify completion"
        ]
        
        # Look for numbered lists or bullet points
        current_plan = []
        for line in lines:
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('-') or line.startswith('*')):
                # Clean up the line
                cleaned = line.lstrip('0123456789.-* ')
                if cleaned:
                    current_plan.append(cleaned)
        
        if current_plan:
            execution_plan = current_plan
        
        return {
            "issue_title": issue_title,
            "issue_description": issue_description,
            "execution_plan": execution_plan,
            "analysis": response_text
        }
    
    async def run_server(self, host: str = "0.0.0.0", port: int = 8002):
        """Run the FastAPI server"""
        config_obj = uvicorn.Config(
            app=self.app,
            host=host,
            port=port,
            log_level="info"
        )
        server = uvicorn.Server(config_obj)
        await server.serve()


# Entry point for running the agent
if __name__ == "__main__":
    import asyncio
    
    async def main():
        agent = LLM2Agent()
        await agent.initialize()
        try:
            await agent.run_server()
        finally:
            await agent.shutdown()
    
    asyncio.run(main())
"""
Health Monitor - Agent health tracking for ATLAS Phase 4

Monitors agent status, availability, and performs health checks.
Integrates with the Agent Registry to maintain current agent status.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from agents.registry.agent_registry import AgentRegistry, AgentInfo, AgentStatus
from agents.shared.config import config


logger = logging.getLogger(__name__)


@dataclass
class HealthCheckResult:
    """Result of a health check operation"""
    agent_id: str
    success: bool
    response_time_ms: float
    status: AgentStatus
    error_message: Optional[str] = None
    metadata: Dict[str, str] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class HealthMonitor:
    """
    Monitors agent health and availability
    
    Performs periodic health checks and updates agent status in the registry.
    Provides health statistics and alerting capabilities.
    """
    
    def __init__(self, registry: AgentRegistry):
        """Initialize the health monitor"""
        self.registry = registry
        self.check_interval = getattr(config, 'ATLAS_AGENT_REGISTRY_DISCOVERY_INTERVAL', 30)
        self.health_timeout = getattr(config, 'ATLAS_AGENT_REGISTRY_HEALTH_TIMEOUT', 10)
        
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._health_history: Dict[str, List[HealthCheckResult]] = {}
        self._max_history_size = 50
        
        # Health check callbacks
        self._health_callbacks: List[Callable[[HealthCheckResult], None]] = []
        
        logger.info("Health Monitor initialized")
    
    async def start_monitoring(self) -> None:
        """Start the health monitoring loop"""
        if self._monitoring:
            logger.warning("Health monitoring already running")
            return
        
        self._monitoring = True
        self._monitor_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Health monitoring started")
    
    async def stop_monitoring(self) -> None:
        """Stop the health monitoring loop"""
        if not self._monitoring:
            return
        
        self._monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Health monitoring stopped")
    
    async def check_agent_health(self, agent: AgentInfo) -> HealthCheckResult:
        """
        Perform a health check on a specific agent
        
        Args:
            agent: Agent to check
            
        Returns:
            Health check result
        """
        start_time = time.time()
        
        try:
            # For now, implement basic health check logic
            # In a full implementation, this would make actual HTTP calls to agent endpoints
            result = await self._perform_health_check(agent)
            
            response_time = (time.time() - start_time) * 1000
            
            health_result = HealthCheckResult(
                agent_id=agent.agent_id,
                success=result['success'],
                response_time_ms=response_time,
                status=result['status'],
                error_message=result.get('error'),
                metadata=result.get('metadata', {})
            )
            
            # Update agent status in registry
            await self.registry.update_agent_status(
                agent.agent_id,
                health_result.status,
                result.get('load_factor')
            )
            
            # Store in history
            self._store_health_result(health_result)
            
            # Notify callbacks
            for callback in self._health_callbacks:
                try:
                    callback(health_result)
                except Exception as e:
                    logger.error(f"Health callback error: {e}")
            
            return health_result
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            
            health_result = HealthCheckResult(
                agent_id=agent.agent_id,
                success=False,
                response_time_ms=response_time,
                status=AgentStatus.UNHEALTHY,
                error_message=str(e)
            )
            
            # Update agent status in registry
            await self.registry.update_agent_status(agent.agent_id, AgentStatus.UNHEALTHY)
            
            self._store_health_result(health_result)
            
            logger.error(f"Health check failed for agent {agent.agent_id}: {e}")
            return health_result
    
    async def check_all_agents(self) -> List[HealthCheckResult]:
        """
        Check health of all registered agents
        
        Returns:
            List of health check results
        """
        agents = await self.registry.list_agents()
        results = []
        
        # Run health checks concurrently
        tasks = [self.check_agent_health(agent) for agent in agents]
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out exceptions and log them
            filtered_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Health check exception for agent {agents[i].agent_id}: {result}")
                else:
                    filtered_results.append(result)
            
            results = filtered_results
        
        logger.info(f"Completed health check for {len(results)} agents")
        return results
    
    async def _perform_health_check(self, agent: AgentInfo) -> Dict:
        """
        Perform the actual health check logic
        
        This is a simplified implementation. In a full system, this would:
        - Make HTTP requests to agent health endpoints
        - Check response times and content
        - Validate agent capabilities
        - Monitor resource usage
        """
        
        # Simulate health check logic
        await asyncio.sleep(0.1)  # Simulate network delay
        
        # For agents with URLs, we would make actual HTTP calls
        if agent.url:
            # Placeholder for HTTP health check
            # In real implementation: response = await http_client.get(f"{agent.url}/health")
            return {
                'success': True,
                'status': AgentStatus.HEALTHY,
                'load_factor': 0.3,  # Simulated load
                'metadata': {
                    'last_activity': str(time.time()),
                    'health_check_type': 'http'
                }
            }
        else:
            # For agents without URLs (e.g., local agents), use different checks
            return {
                'success': True,
                'status': AgentStatus.IDLE,
                'load_factor': 0.1,
                'metadata': {
                    'last_activity': str(time.time()),
                    'health_check_type': 'local'
                }
            }
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop"""
        logger.info(f"Starting health monitoring loop (interval: {self.check_interval}s)")
        
        while self._monitoring:
            try:
                await self.check_all_agents()
                
                # Wait for next check interval
                await asyncio.sleep(self.check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
                await asyncio.sleep(5)  # Brief pause before retry
    
    def _store_health_result(self, result: HealthCheckResult) -> None:
        """Store health result in history"""
        if result.agent_id not in self._health_history:
            self._health_history[result.agent_id] = []
        
        history = self._health_history[result.agent_id]
        history.append(result)
        
        # Trim history if it gets too long
        if len(history) > self._max_history_size:
            history.pop(0)
    
    def get_agent_health_history(self, agent_id: str, limit: int = 10) -> List[HealthCheckResult]:
        """Get health history for a specific agent"""
        history = self._health_history.get(agent_id, [])
        return history[-limit:] if limit > 0 else history
    
    def get_health_statistics(self) -> Dict[str, float]:
        """Get overall health statistics"""
        if not self._health_history:
            return {}
        
        total_checks = 0
        successful_checks = 0
        total_response_time = 0.0
        
        for agent_history in self._health_history.values():
            for result in agent_history:
                total_checks += 1
                if result.success:
                    successful_checks += 1
                total_response_time += result.response_time_ms
        
        if total_checks == 0:
            return {}
        
        return {
            'success_rate': successful_checks / total_checks,
            'average_response_time_ms': total_response_time / total_checks,
            'total_checks': total_checks,
            'successful_checks': successful_checks
        }
    
    def add_health_callback(self, callback: Callable[[HealthCheckResult], None]) -> None:
        """Add a callback to be notified of health check results"""
        self._health_callbacks.append(callback)
    
    def remove_health_callback(self, callback: Callable[[HealthCheckResult], None]) -> None:
        """Remove a health check callback"""
        if callback in self._health_callbacks:
            self._health_callbacks.remove(callback)
    
    def get_unhealthy_agents(self) -> List[str]:
        """Get list of currently unhealthy agent IDs"""
        unhealthy = []
        for agent_id, history in self._health_history.items():
            if history and not history[-1].success:
                unhealthy.append(agent_id)
        return unhealthy
    
    async def force_health_check(self, agent_id: str) -> Optional[HealthCheckResult]:
        """Force an immediate health check for a specific agent"""
        agent = await self.registry.get_agent(agent_id)
        if not agent:
            logger.warning(f"Agent {agent_id} not found for health check")
            return None
        
        return await self.check_agent_health(agent)
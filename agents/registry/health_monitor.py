"""
Health Monitor

Monitors agent health and availability.
"""

import asyncio
import aiohttp
import time
from typing import Dict, List, Optional
import logging
from .agent_registry import AgentInfo, AgentStatus

logger = logging.getLogger(__name__)


class HealthMonitor:
    """Monitor agent health and availability"""
    
    def __init__(self, registry):
        self.registry = registry
        self.check_interval = 30  # seconds
        self.timeout = 10  # seconds
        self._session = None
        self._monitoring_task = None
        self._running = False
        
    async def start(self):
        """Start health monitoring"""
        logger.info("Starting Health Monitor")
        self._running = True
        
        # Create HTTP session
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        )
        
        # Start monitoring task
        self._monitoring_task = asyncio.create_task(self._monitor_loop())
        
    async def stop(self):
        """Stop health monitoring"""
        self._running = False
        
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
                
        if self._session:
            await self._session.close()
            
        logger.info("Health Monitor stopped")
        
    async def check_agent_health(self, agent: AgentInfo) -> AgentStatus:
        """Check health of a single agent"""
        try:
            # Try to reach the agent's health endpoint
            health_url = f"{agent.url.rstrip('/')}/health"
            
            start_time = time.time()
            async with self._session.get(health_url) as response:
                response_time = time.time() - start_time
                
                if response.status == 200:
                    # Update load score based on response time
                    load_score = min(response_time / 2.0, 1.0)  # Normalize to 0-1
                    await self.registry.update_agent_status(
                        agent.id, 
                        AgentStatus.HEALTHY, 
                        load_score
                    )
                    return AgentStatus.HEALTHY
                else:
                    await self.registry.update_agent_status(agent.id, AgentStatus.UNHEALTHY)
                    return AgentStatus.UNHEALTHY
                    
        except asyncio.TimeoutError:
            logger.warning(f"Health check timeout for agent {agent.name}")
            await self.registry.update_agent_status(agent.id, AgentStatus.UNHEALTHY)
            return AgentStatus.UNHEALTHY
            
        except Exception as e:
            logger.error(f"Health check failed for agent {agent.name}: {e}")
            await self.registry.update_agent_status(agent.id, AgentStatus.OFFLINE)
            return AgentStatus.OFFLINE
            
    async def _monitor_loop(self):
        """Main monitoring loop"""
        while self._running:
            try:
                await self._check_all_agents()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(5)  # Brief pause on error
                
    async def _check_all_agents(self):
        """Check health of all registered agents"""
        agents = await self.registry.list_agents()
        
        # Create tasks for concurrent health checks
        tasks = []
        for agent in agents:
            task = asyncio.create_task(self.check_agent_health(agent))
            tasks.append(task)
            
        if tasks:
            # Wait for all health checks to complete
            await asyncio.gather(*tasks, return_exceptions=True)
            
    async def get_health_summary(self) -> Dict:
        """Get overall health summary"""
        agents = await self.registry.list_agents()
        
        summary = {
            "total_agents": len(agents),
            "healthy": 0,
            "unhealthy": 0,
            "offline": 0,
            "average_load": 0.0,
            "last_check": time.time()
        }
        
        total_load = 0.0
        for agent in agents:
            if agent.status == AgentStatus.HEALTHY:
                summary["healthy"] += 1
            elif agent.status == AgentStatus.UNHEALTHY:
                summary["unhealthy"] += 1
            elif agent.status == AgentStatus.OFFLINE:
                summary["offline"] += 1
                
            total_load += agent.load_score
            
        if len(agents) > 0:
            summary["average_load"] = total_load / len(agents)
            
        return summary
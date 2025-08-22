"""
Agent Registry Core Implementation

Provides centralized registry for dynamic agent discovery and management.
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Agent status enumeration"""
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    OFFLINE = "offline"
    BUSY = "busy"
    AVAILABLE = "available"


@dataclass
class AgentCapability:
    """Agent capability definition"""
    name: str
    category: str
    description: str
    parameters: Dict = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}


@dataclass
class AgentInfo:
    """Agent information structure"""
    id: str
    name: str
    url: str
    status: AgentStatus = AgentStatus.UNKNOWN
    capabilities: List[AgentCapability] = None
    version: str = "1.0.0"
    last_health_check: float = 0
    metadata: Dict = None
    load_score: float = 0.0
    
    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []
        if self.metadata is None:
            self.metadata = {}


class AgentRegistry:
    """Central registry for agent discovery and management"""
    
    def __init__(self):
        self.agents: Dict[str, AgentInfo] = {}
        self.health_check_interval = 30  # seconds
        self.health_check_timeout = 10   # seconds
        self._health_check_task = None
        self._running = False
        
    async def start(self):
        """Start the agent registry"""
        logger.info("Starting Agent Registry")
        self._running = True
        
        # Load existing agents from environment or storage
        await self._discover_agents_from_env()
        
        # Start health monitoring
        self._health_check_task = asyncio.create_task(self._health_monitor())
        
        logger.info(f"Agent Registry started with {len(self.agents)} agents")
        
    async def stop(self):
        """Stop the agent registry"""
        self._running = False
        
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
                
        logger.info("Agent Registry stopped")
        
    async def register_agent(self, agent_info: AgentInfo) -> bool:
        """Register a new agent"""
        try:
            self.agents[agent_info.id] = agent_info
            agent_info.last_health_check = time.time()
            
            logger.info(f"Registered agent: {agent_info.name} ({agent_info.id})")
            return True
        except Exception as e:
            logger.error(f"Failed to register agent {agent_info.id}: {e}")
            return False
            
    async def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent"""
        try:
            if agent_id in self.agents:
                agent = self.agents.pop(agent_id)
                logger.info(f"Unregistered agent: {agent.name} ({agent_id})")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to unregister agent {agent_id}: {e}")
            return False
            
    async def get_agent(self, agent_id: str) -> Optional[AgentInfo]:
        """Get agent information by ID"""
        return self.agents.get(agent_id)
        
    async def list_agents(self, status: Optional[AgentStatus] = None) -> List[AgentInfo]:
        """List all agents, optionally filtered by status"""
        if status is None:
            return list(self.agents.values())
        return [agent for agent in self.agents.values() if agent.status == status]
        
    async def find_agents_by_capability(self, capability_name: str) -> List[AgentInfo]:
        """Find agents that have a specific capability"""
        matching_agents = []
        for agent in self.agents.values():
            for cap in agent.capabilities:
                if cap.name == capability_name:
                    matching_agents.append(agent)
                    break
        return matching_agents
        
    async def update_agent_status(self, agent_id: str, status: AgentStatus, load_score: float = None):
        """Update agent status and load score"""
        if agent_id in self.agents:
            self.agents[agent_id].status = status
            self.agents[agent_id].last_health_check = time.time()
            if load_score is not None:
                self.agents[agent_id].load_score = load_score
                
    async def get_registry_stats(self) -> Dict:
        """Get registry statistics"""
        stats = {
            "total_agents": len(self.agents),
            "status_breakdown": {},
            "capabilities": set(),
            "last_updated": time.time()
        }
        
        for agent in self.agents.values():
            status_str = agent.status.value
            stats["status_breakdown"][status_str] = stats["status_breakdown"].get(status_str, 0) + 1
            
            for cap in agent.capabilities:
                stats["capabilities"].add(cap.name)
                
        stats["capabilities"] = list(stats["capabilities"])
        return stats
        
    async def _discover_agents_from_env(self):
        """Discover agents from environment configuration"""
        import os
        
        # Get agent registry path from environment
        registry_path = os.getenv('ATLAS_AGENT_REGISTRY_PATH', './config/agents.json')
        
        try:
            if os.path.exists(registry_path):
                with open(registry_path, 'r') as f:
                    agent_configs = json.load(f)
                    
                for config in agent_configs.get('agents', []):
                    capabilities = [
                        AgentCapability(**cap) for cap in config.get('capabilities', [])
                    ]
                    
                    agent_info = AgentInfo(
                        id=config['id'],
                        name=config['name'],
                        url=config['url'],
                        capabilities=capabilities,
                        version=config.get('version', '1.0.0'),
                        metadata=config.get('metadata', {})
                    )
                    
                    await self.register_agent(agent_info)
                    
        except Exception as e:
            logger.warning(f"Could not load agents from {registry_path}: {e}")
            
    async def _health_monitor(self):
        """Background health monitoring task"""
        while self._running:
            try:
                await self._check_all_agents_health()
                await asyncio.sleep(self.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitor error: {e}")
                await asyncio.sleep(5)  # Brief pause on error
                
    async def _check_all_agents_health(self):
        """Check health of all registered agents"""
        for agent_id, agent in self.agents.items():
            try:
                # Implement actual health check logic here
                # For now, simulate health checks
                current_time = time.time()
                time_since_check = current_time - agent.last_health_check
                
                if time_since_check > self.health_check_timeout * 3:
                    await self.update_agent_status(agent_id, AgentStatus.OFFLINE)
                elif time_since_check > self.health_check_timeout:
                    await self.update_agent_status(agent_id, AgentStatus.UNHEALTHY)
                else:
                    await self.update_agent_status(agent_id, AgentStatus.HEALTHY)
                    
            except Exception as e:
                logger.error(f"Health check failed for agent {agent_id}: {e}")
                await self.update_agent_status(agent_id, AgentStatus.UNHEALTHY)
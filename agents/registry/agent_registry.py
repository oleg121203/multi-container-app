"""
Agent Registry - Core implementation for ATLAS Phase 4

Provides centralized registry for agent discovery, registration, and management.
Follows existing patterns from MCP Hub implementation for consistency.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set
from pydantic import BaseModel, Field
from agents.shared.config import config


logger = logging.getLogger(__name__)


class AgentStatus(str, Enum):
    """Agent status enumeration"""
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    OFFLINE = "offline"
    BUSY = "busy"
    IDLE = "idle"


class AgentCapability(BaseModel):
    """Agent capability definition"""
    name: str
    description: str
    parameters: Dict[str, str] = Field(default_factory=dict)
    required_tools: List[str] = Field(default_factory=list)


class AgentInfo(BaseModel):
    """Agent information model"""
    agent_id: str
    name: str
    description: str
    capabilities: List[AgentCapability] = Field(default_factory=list)
    status: AgentStatus = AgentStatus.UNKNOWN
    url: Optional[str] = None
    version: str = "1.0.0"
    load_factor: float = 0.0  # 0.0 = idle, 1.0 = max load
    last_health_check: float = 0.0
    metadata: Dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentRegistry:
    """
    Central agent registry for ATLAS Phase 4
    
    Manages agent registration, discovery, and basic lifecycle operations.
    Designed to be lightweight and focused on core registry functionality.
    """
    
    def __init__(self, registry_path: Optional[str] = None):
        """Initialize the agent registry"""
        self.registry_path = registry_path or getattr(config, 'ATLAS_AGENT_REGISTRY_PATH', './config/agents.json')
        self.agents: Dict[str, AgentInfo] = {}
        self.capabilities_index: Dict[str, Set[str]] = {}  # capability -> set of agent_ids
        self._lock = asyncio.Lock()
        
        logger.info(f"Initializing Agent Registry with path: {self.registry_path}")
    
    async def initialize(self) -> None:
        """Initialize the registry and load existing agents"""
        async with self._lock:
            await self._load_agents_from_config()
            await self._build_capabilities_index()
        
        logger.info(f"Agent Registry initialized with {len(self.agents)} agents")
    
    async def register_agent(self, agent_info: AgentInfo) -> bool:
        """Register a new agent or update existing one"""
        async with self._lock:
            agent_info.updated_at = datetime.now(timezone.utc)
            self.agents[agent_info.agent_id] = agent_info
            
            # Update capabilities index
            for capability in agent_info.capabilities:
                if capability.name not in self.capabilities_index:
                    self.capabilities_index[capability.name] = set()
                self.capabilities_index[capability.name].add(agent_info.agent_id)
            
            logger.info(f"Registered agent: {agent_info.agent_id} ({agent_info.name})")
            return True
    
    async def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent"""
        async with self._lock:
            if agent_id not in self.agents:
                return False
            
            agent_info = self.agents[agent_id]
            
            # Remove from capabilities index
            for capability in agent_info.capabilities:
                if capability.name in self.capabilities_index:
                    self.capabilities_index[capability.name].discard(agent_id)
                    if not self.capabilities_index[capability.name]:
                        del self.capabilities_index[capability.name]
            
            del self.agents[agent_id]
            logger.info(f"Unregistered agent: {agent_id}")
            return True
    
    async def get_agent(self, agent_id: str) -> Optional[AgentInfo]:
        """Get agent information by ID"""
        return self.agents.get(agent_id)
    
    async def list_agents(self, status_filter: Optional[AgentStatus] = None) -> List[AgentInfo]:
        """List all agents, optionally filtered by status"""
        agents = list(self.agents.values())
        
        if status_filter:
            agents = [agent for agent in agents if agent.status == status_filter]
        
        return agents
    
    async def get_agents_by_capability(self, capability_name: str) -> List[AgentInfo]:
        """Get all agents that have a specific capability"""
        if capability_name not in self.capabilities_index:
            return []
        
        agent_ids = self.capabilities_index[capability_name]
        return [self.agents[agent_id] for agent_id in agent_ids if agent_id in self.agents]
    
    async def update_agent_status(self, agent_id: str, status: AgentStatus, load_factor: Optional[float] = None) -> bool:
        """Update agent status and optionally load factor"""
        if agent_id not in self.agents:
            return False
        
        self.agents[agent_id].status = status
        self.agents[agent_id].updated_at = datetime.now(timezone.utc)
        self.agents[agent_id].last_health_check = time.time()
        
        if load_factor is not None:
            self.agents[agent_id].load_factor = max(0.0, min(1.0, load_factor))
        
        logger.debug(f"Updated agent {agent_id} status to {status}")
        return True
    
    async def get_healthy_agents(self) -> List[AgentInfo]:
        """Get all healthy agents"""
        return await self.list_agents(AgentStatus.HEALTHY)
    
    async def get_available_agents(self) -> List[AgentInfo]:
        """Get all available (healthy and not busy) agents"""
        return [
            agent for agent in self.agents.values()
            if agent.status in [AgentStatus.HEALTHY, AgentStatus.IDLE]
        ]
    
    async def _load_agents_from_config(self) -> None:
        """Load agent configurations from the registry file"""
        registry_file = Path(self.registry_path)
        
        if not registry_file.exists():
            logger.info(f"Registry file {self.registry_path} not found, starting with empty registry")
            return
        
        try:
            with open(registry_file, 'r') as f:
                data = json.load(f)
            
            for agent_data in data.get('agents', []):
                # Convert to AgentInfo model
                capabilities = [
                    AgentCapability(**cap) for cap in agent_data.get('capabilities', [])
                ]
                
                agent_info = AgentInfo(
                    agent_id=agent_data['agent_id'],
                    name=agent_data['name'],
                    description=agent_data.get('description', ''),
                    capabilities=capabilities,
                    url=agent_data.get('url'),
                    version=agent_data.get('version', '1.0.0'),
                    metadata=agent_data.get('metadata', {})
                )
                
                self.agents[agent_info.agent_id] = agent_info
                
            logger.info(f"Loaded {len(self.agents)} agents from configuration")
            
        except Exception as e:
            logger.error(f"Failed to load agents from config: {e}")
            # Continue with empty registry rather than failing
    
    async def _build_capabilities_index(self) -> None:
        """Build the capabilities index for fast lookup"""
        self.capabilities_index.clear()
        
        for agent_id, agent_info in self.agents.items():
            for capability in agent_info.capabilities:
                if capability.name not in self.capabilities_index:
                    self.capabilities_index[capability.name] = set()
                self.capabilities_index[capability.name].add(agent_id)
        
        logger.debug(f"Built capabilities index with {len(self.capabilities_index)} capabilities")
    
    def get_registry_stats(self) -> Dict[str, int]:
        """Get registry statistics"""
        stats = {
            "total_agents": len(self.agents),
            "healthy_agents": len([a for a in self.agents.values() if a.status == AgentStatus.HEALTHY]),
            "offline_agents": len([a for a in self.agents.values() if a.status == AgentStatus.OFFLINE]),
            "total_capabilities": len(self.capabilities_index)
        }
        return stats
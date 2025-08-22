"""
Load Balancer

Distributes workload across agent instances.
"""

import random
from typing import List, Optional, Dict
import logging
from .agent_registry import AgentInfo, AgentStatus

logger = logging.getLogger(__name__)


class LoadBalancingStrategy:
    """Base class for load balancing strategies"""
    
    async def select_agent(self, agents: List[AgentInfo], **kwargs) -> Optional[AgentInfo]:
        """Select an agent from the list"""
        raise NotImplementedError


class RoundRobinStrategy(LoadBalancingStrategy):
    """Round-robin load balancing"""
    
    def __init__(self):
        self._current_index = 0
        
    async def select_agent(self, agents: List[AgentInfo], **kwargs) -> Optional[AgentInfo]:
        if not agents:
            return None
            
        # Filter healthy agents
        healthy_agents = [a for a in agents if a.status == AgentStatus.HEALTHY]
        if not healthy_agents:
            return None
            
        # Round-robin selection
        selected = healthy_agents[self._current_index % len(healthy_agents)]
        self._current_index = (self._current_index + 1) % len(healthy_agents)
        
        return selected


class LeastLoadStrategy(LoadBalancingStrategy):
    """Select agent with least load"""
    
    async def select_agent(self, agents: List[AgentInfo], **kwargs) -> Optional[AgentInfo]:
        if not agents:
            return None
            
        # Filter healthy agents
        healthy_agents = [a for a in agents if a.status == AgentStatus.HEALTHY]
        if not healthy_agents:
            return None
            
        # Sort by load score (ascending)
        healthy_agents.sort(key=lambda x: x.load_score)
        return healthy_agents[0]


class WeightedRandomStrategy(LoadBalancingStrategy):
    """Weighted random selection based on inverse load"""
    
    async def select_agent(self, agents: List[AgentInfo], **kwargs) -> Optional[AgentInfo]:
        if not agents:
            return None
            
        # Filter healthy agents
        healthy_agents = [a for a in agents if a.status == AgentStatus.HEALTHY]
        if not healthy_agents:
            return None
            
        # Calculate weights (inverse of load + small base weight)
        weights = []
        for agent in healthy_agents:
            weight = 1.0 / (agent.load_score + 0.1)  # +0.1 to avoid division by zero
            weights.append(weight)
            
        # Weighted random selection
        total_weight = sum(weights)
        if total_weight == 0:
            return random.choice(healthy_agents)
            
        rand_val = random.uniform(0, total_weight)
        cumulative = 0
        
        for i, weight in enumerate(weights):
            cumulative += weight
            if rand_val <= cumulative:
                return healthy_agents[i]
                
        return healthy_agents[-1]  # Fallback


class CapabilityAwareStrategy(LoadBalancingStrategy):
    """Select agent based on capability match and load"""
    
    async def select_agent(self, agents: List[AgentInfo], **kwargs) -> Optional[AgentInfo]:
        required_capability = kwargs.get('capability')
        if not required_capability or not agents:
            return None
            
        # Filter agents with required capability
        capable_agents = []
        for agent in agents:
            if agent.status == AgentStatus.HEALTHY:
                for cap in agent.capabilities:
                    if cap.name.lower() == required_capability.lower():
                        capable_agents.append(agent)
                        break
                        
        if not capable_agents:
            return None
            
        # Select by least load among capable agents
        capable_agents.sort(key=lambda x: x.load_score)
        return capable_agents[0]


class LoadBalancer:
    """Distribute workload across agent instances"""
    
    def __init__(self, strategy_name: str = "least_load"):
        self.strategies = {
            "round_robin": RoundRobinStrategy(),
            "least_load": LeastLoadStrategy(),
            "weighted_random": WeightedRandomStrategy(),
            "capability_aware": CapabilityAwareStrategy()
        }
        
        self.current_strategy = self.strategies.get(strategy_name, LeastLoadStrategy())
        self.agent_assignments = {}  # Track agent assignments
        
    async def select_agent(
        self, 
        agents: List[AgentInfo], 
        strategy: str = None,
        **kwargs
    ) -> Optional[AgentInfo]:
        """Select an agent using the specified strategy"""
        
        # Use specified strategy or current default
        if strategy and strategy in self.strategies:
            selected_strategy = self.strategies[strategy]
        else:
            selected_strategy = self.current_strategy
            
        selected_agent = await selected_strategy.select_agent(agents, **kwargs)
        
        if selected_agent:
            # Track assignment
            self._record_assignment(selected_agent.id)
            logger.debug(f"Selected agent {selected_agent.name} for load balancing")
            
        return selected_agent
        
    async def select_agents_for_team(
        self,
        available_agents: List[AgentInfo],
        team_size: int,
        required_capabilities: List[str] = None
    ) -> List[AgentInfo]:
        """Select multiple agents for a team"""
        selected_agents = []
        remaining_agents = available_agents.copy()
        
        # First, satisfy required capabilities
        if required_capabilities:
            for capability in required_capabilities:
                agent = await self.select_agent(
                    remaining_agents,
                    strategy="capability_aware",
                    capability=capability
                )
                if agent:
                    selected_agents.append(agent)
                    remaining_agents = [a for a in remaining_agents if a.id != agent.id]
                    
        # Fill remaining slots with best available agents
        while len(selected_agents) < team_size and remaining_agents:
            agent = await self.select_agent(remaining_agents, strategy="least_load")
            if agent:
                selected_agents.append(agent)
                remaining_agents = [a for a in remaining_agents if a.id != agent.id]
            else:
                break
                
        return selected_agents
        
    def set_strategy(self, strategy_name: str):
        """Change the load balancing strategy"""
        if strategy_name in self.strategies:
            self.current_strategy = self.strategies[strategy_name]
            logger.info(f"Load balancing strategy changed to: {strategy_name}")
        else:
            logger.warning(f"Unknown strategy: {strategy_name}")
            
    def _record_assignment(self, agent_id: str):
        """Record agent assignment for tracking"""
        if agent_id not in self.agent_assignments:
            self.agent_assignments[agent_id] = 0
        self.agent_assignments[agent_id] += 1
        
    async def get_load_distribution(self) -> Dict:
        """Get load distribution statistics"""
        return {
            "strategy": self.current_strategy.__class__.__name__,
            "assignments": self.agent_assignments.copy(),
            "total_assignments": sum(self.agent_assignments.values())
        }
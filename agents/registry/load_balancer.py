"""
Load Balancer - Workload distribution for ATLAS Phase 4

Distributes workload across available agents based on capacity, capabilities, and current load.
Works with the Agent Registry and Health Monitor for optimal agent selection.
"""

import logging
import random
from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
from agents.registry.agent_registry import AgentRegistry, AgentInfo, AgentStatus
from agents.registry.capability_matcher import CapabilityMatcher, TaskRequirement


logger = logging.getLogger(__name__)


class LoadBalancingStrategy(str, Enum):
    """Load balancing strategy options"""
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    RANDOM = "random"
    CAPABILITY_AWARE = "capability_aware"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"


@dataclass
class TaskAssignment:
    """Represents a task assignment to an agent"""
    task_id: str
    agent_id: str
    capabilities_required: List[str]
    estimated_load: float  # 0.0 to 1.0
    priority: int = 1  # 1 = low, 5 = high
    assigned_at: float = 0.0
    

class LoadBalancer:
    """
    Distributes workload across available agents
    
    Provides different load balancing strategies and tracks task assignments
    to optimize agent utilization and system performance.
    """
    
    def __init__(self, registry: AgentRegistry, capability_matcher: Optional[CapabilityMatcher] = None):
        """Initialize the load balancer"""
        self.registry = registry
        self.capability_matcher = capability_matcher or CapabilityMatcher()
        
        # Load balancing state
        self.current_assignments: Dict[str, List[TaskAssignment]] = {}  # agent_id -> tasks
        self.round_robin_index = 0
        self.strategy = LoadBalancingStrategy.CAPABILITY_AWARE
        
        # Agent weights (for weighted strategies)
        self.agent_weights: Dict[str, float] = {}
        
        logger.info("Load Balancer initialized")
    
    async def assign_task(
        self,
        task_id: str,
        requirements: List[TaskRequirement],
        strategy: Optional[LoadBalancingStrategy] = None,
        estimated_load: float = 0.1
    ) -> Optional[TaskAssignment]:
        """
        Assign a task to the best available agent
        
        Args:
            task_id: Unique task identifier
            requirements: Task capability requirements
            strategy: Load balancing strategy to use
            estimated_load: Estimated load factor (0.0 to 1.0)
            
        Returns:
            Task assignment or None if no suitable agent found
        """
        if not requirements:
            logger.warning(f"No requirements specified for task {task_id}")
            return None
        
        strategy = strategy or self.strategy
        available_agents = await self.registry.get_available_agents()
        
        if not available_agents:
            logger.warning(f"No available agents for task {task_id}")
            return None
        
        # Select agent based on strategy
        selected_agent = await self._select_agent(
            available_agents, requirements, strategy, estimated_load
        )
        
        if not selected_agent:
            logger.warning(f"No suitable agent found for task {task_id}")
            return None
        
        # Create task assignment
        assignment = TaskAssignment(
            task_id=task_id,
            agent_id=selected_agent.agent_id,
            capabilities_required=[req.capability for req in requirements],
            estimated_load=estimated_load,
            priority=max((req.priority for req in requirements), default=1),
            assigned_at=__import__('time').time()
        )
        
        # Update agent load and assignment tracking
        await self._assign_task_to_agent(assignment)
        
        logger.info(f"Assigned task {task_id} to agent {selected_agent.agent_id} using {strategy}")
        return assignment
    
    async def complete_task(self, task_id: str, agent_id: str) -> bool:
        """
        Mark a task as completed and update agent load
        
        Args:
            task_id: Task identifier
            agent_id: Agent identifier
            
        Returns:
            True if task was found and removed
        """
        if agent_id not in self.current_assignments:
            return False
        
        assignments = self.current_assignments[agent_id]
        for i, assignment in enumerate(assignments):
            if assignment.task_id == task_id:
                # Remove assignment
                assignments.pop(i)
                
                # Update agent load
                await self._update_agent_load(agent_id)
                
                logger.info(f"Completed task {task_id} on agent {agent_id}")
                return True
        
        return False
    
    async def _select_agent(
        self,
        available_agents: List[AgentInfo],
        requirements: List[TaskRequirement],
        strategy: LoadBalancingStrategy,
        estimated_load: float
    ) -> Optional[AgentInfo]:
        """Select the best agent based on the specified strategy"""
        
        if strategy == LoadBalancingStrategy.CAPABILITY_AWARE:
            return await self._select_capability_aware(available_agents, requirements, estimated_load)
        elif strategy == LoadBalancingStrategy.LEAST_LOADED:
            return await self._select_least_loaded(available_agents, requirements)
        elif strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return await self._select_round_robin(available_agents, requirements)
        elif strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
            return await self._select_weighted_round_robin(available_agents, requirements)
        elif strategy == LoadBalancingStrategy.RANDOM:
            return await self._select_random(available_agents, requirements)
        else:
            logger.warning(f"Unknown strategy {strategy}, using capability_aware")
            return await self._select_capability_aware(available_agents, requirements, estimated_load)
    
    async def _select_capability_aware(
        self,
        available_agents: List[AgentInfo],
        requirements: List[TaskRequirement],
        estimated_load: float
    ) -> Optional[AgentInfo]:
        """Select agent using capability-aware strategy (best overall match)"""
        
        # Use capability matcher to find best matches
        matches = await self.capability_matcher.find_matching_agents(
            requirements, available_agents, max_results=5
        )
        
        if not matches:
            return None
        
        # Consider load balancing among top matches
        best_match = None
        best_score = -1.0
        
        for match in matches:
            agent = match.agent
            
            # Check if agent can handle additional load
            current_load = self._get_agent_current_load(agent.agent_id)
            if current_load + estimated_load > 1.0:
                continue
            
            # Combine capability score with load consideration
            load_factor = 1.0 - current_load  # Prefer less loaded agents
            combined_score = match.score * 0.7 + load_factor * 0.3
            
            if combined_score > best_score:
                best_score = combined_score
                best_match = agent
        
        return best_match
    
    async def _select_least_loaded(
        self,
        available_agents: List[AgentInfo],
        requirements: List[TaskRequirement]
    ) -> Optional[AgentInfo]:
        """Select the least loaded agent that meets requirements"""
        
        suitable_agents = []
        
        for agent in available_agents:
            # Check if agent has required capabilities
            agent_capabilities = {cap.name for cap in agent.capabilities}
            required_capabilities = {req.capability for req in requirements if req.required}
            
            if required_capabilities.issubset(agent_capabilities):
                current_load = self._get_agent_current_load(agent.agent_id)
                suitable_agents.append((agent, current_load))
        
        if not suitable_agents:
            return None
        
        # Sort by load (ascending) and return least loaded
        suitable_agents.sort(key=lambda x: x[1])
        return suitable_agents[0][0]
    
    async def _select_round_robin(
        self,
        available_agents: List[AgentInfo],
        requirements: List[TaskRequirement]
    ) -> Optional[AgentInfo]:
        """Select agent using round-robin strategy"""
        
        # Filter agents that meet requirements
        suitable_agents = []
        
        for agent in available_agents:
            agent_capabilities = {cap.name for cap in agent.capabilities}
            required_capabilities = {req.capability for req in requirements if req.required}
            
            if required_capabilities.issubset(agent_capabilities):
                suitable_agents.append(agent)
        
        if not suitable_agents:
            return None
        
        # Round-robin selection
        selected_agent = suitable_agents[self.round_robin_index % len(suitable_agents)]
        self.round_robin_index += 1
        
        return selected_agent
    
    async def _select_weighted_round_robin(
        self,
        available_agents: List[AgentInfo],
        requirements: List[TaskRequirement]
    ) -> Optional[AgentInfo]:
        """Select agent using weighted round-robin strategy"""
        
        # For now, use equal weights if not configured
        return await self._select_round_robin(available_agents, requirements)
    
    async def _select_random(
        self,
        available_agents: List[AgentInfo],
        requirements: List[TaskRequirement]
    ) -> Optional[AgentInfo]:
        """Select agent randomly from suitable candidates"""
        
        suitable_agents = []
        
        for agent in available_agents:
            agent_capabilities = {cap.name for cap in agent.capabilities}
            required_capabilities = {req.capability for req in requirements if req.required}
            
            if required_capabilities.issubset(agent_capabilities):
                suitable_agents.append(agent)
        
        if not suitable_agents:
            return None
        
        return random.choice(suitable_agents)
    
    async def _assign_task_to_agent(self, assignment: TaskAssignment) -> None:
        """Assign task to agent and update tracking"""
        
        if assignment.agent_id not in self.current_assignments:
            self.current_assignments[assignment.agent_id] = []
        
        self.current_assignments[assignment.agent_id].append(assignment)
        
        # Update agent status and load
        await self._update_agent_load(assignment.agent_id)
    
    async def _update_agent_load(self, agent_id: str) -> None:
        """Update agent load factor based on current assignments"""
        
        current_load = self._get_agent_current_load(agent_id)
        
        # Determine status based on load
        if current_load >= 0.9:
            status = AgentStatus.BUSY
        elif current_load <= 0.1:
            status = AgentStatus.IDLE
        else:
            status = AgentStatus.HEALTHY
        
        # Update in registry
        await self.registry.update_agent_status(agent_id, status, current_load)
    
    def _get_agent_current_load(self, agent_id: str) -> float:
        """Get current load factor for an agent"""
        if agent_id not in self.current_assignments:
            return 0.0
        
        total_load = sum(
            assignment.estimated_load 
            for assignment in self.current_assignments[agent_id]
        )
        
        return min(1.0, total_load)
    
    def get_load_statistics(self) -> Dict[str, float]:
        """Get load balancing statistics"""
        if not self.current_assignments:
            return {}
        
        total_agents = len(self.current_assignments)
        total_tasks = sum(len(tasks) for tasks in self.current_assignments.values())
        
        loads = [self._get_agent_current_load(agent_id) for agent_id in self.current_assignments]
        avg_load = sum(loads) / len(loads) if loads else 0.0
        max_load = max(loads) if loads else 0.0
        min_load = min(loads) if loads else 0.0
        
        return {
            'total_agents': total_agents,
            'total_tasks': total_tasks,
            'average_load': avg_load,
            'max_load': max_load,
            'min_load': min_load,
            'load_balance_ratio': min_load / max_load if max_load > 0 else 1.0
        }
    
    def get_agent_assignments(self, agent_id: str) -> List[TaskAssignment]:
        """Get current task assignments for an agent"""
        return self.current_assignments.get(agent_id, [])
    
    def set_strategy(self, strategy: LoadBalancingStrategy) -> None:
        """Set the default load balancing strategy"""
        self.strategy = strategy
        logger.info(f"Load balancing strategy set to {strategy}")
    
    def set_agent_weight(self, agent_id: str, weight: float) -> None:
        """Set weight for an agent (used in weighted strategies)"""
        self.agent_weights[agent_id] = max(0.1, min(10.0, weight))
        logger.debug(f"Set weight {weight} for agent {agent_id}")
    
    async def rebalance_if_needed(self, threshold: float = 0.3) -> bool:
        """
        Check if rebalancing is needed and suggest task reassignments
        
        Args:
            threshold: Load difference threshold to trigger rebalancing
            
        Returns:
            True if rebalancing was suggested
        """
        stats = self.get_load_statistics()
        
        if 'max_load' not in stats or 'min_load' not in stats:
            return False
        
        load_difference = stats['max_load'] - stats['min_load']
        
        if load_difference > threshold:
            logger.info(f"Load imbalance detected: {load_difference:.2f} > {threshold}")
            # In a full implementation, this would suggest specific task migrations
            return True
        
        return False
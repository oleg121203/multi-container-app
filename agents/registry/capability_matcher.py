"""
Capability Matcher - Agent matching logic for ATLAS Phase 4

Matches agents to task requirements based on capabilities and availability.
Used by the Team Constructor for dynamic team formation.
"""

import logging
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from agents.registry.agent_registry import AgentInfo, AgentStatus


logger = logging.getLogger(__name__)


@dataclass
class TaskRequirement:
    """Represents a task requirement for capability matching"""
    capability: str
    required: bool = True
    parameters: Dict[str, str] = None
    priority: int = 1  # 1 = low, 5 = high
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}


@dataclass
class MatchResult:
    """Result of capability matching"""
    agent: AgentInfo
    score: float  # 0.0 to 1.0, higher is better
    matched_capabilities: List[str]
    missing_capabilities: List[str]
    compatibility_notes: List[str] = None
    
    def __post_init__(self):
        if self.compatibility_notes is None:
            self.compatibility_notes = []


class CapabilityMatcher:
    """
    Matches agents to task requirements based on capabilities
    
    Provides scoring and ranking of agents for optimal team formation.
    Considers agent availability, load, and capability match quality.
    """
    
    def __init__(self):
        """Initialize the capability matcher"""
        self.match_cache: Dict[str, List[MatchResult]] = {}
        logger.info("Capability Matcher initialized")
    
    async def find_matching_agents(
        self,
        requirements: List[TaskRequirement],
        available_agents: List[AgentInfo],
        max_results: int = 10
    ) -> List[MatchResult]:
        """
        Find agents that match the given requirements
        
        Args:
            requirements: List of task requirements
            available_agents: List of available agents to consider
            max_results: Maximum number of results to return
            
        Returns:
            List of match results, sorted by score (highest first)
        """
        if not requirements or not available_agents:
            return []
        
        matches = []
        
        for agent in available_agents:
            # Skip agents that are not in suitable state
            if not self._is_agent_suitable(agent):
                continue
            
            match_result = await self._evaluate_agent_match(agent, requirements)
            if match_result.score > 0:
                matches.append(match_result)
        
        # Sort by score (highest first) and return top results
        matches.sort(key=lambda x: x.score, reverse=True)
        return matches[:max_results]
    
    async def find_best_agent_for_capability(
        self,
        capability: str,
        available_agents: List[AgentInfo],
        parameters: Optional[Dict[str, str]] = None
    ) -> Optional[MatchResult]:
        """
        Find the best agent for a specific capability
        
        Args:
            capability: Required capability name
            available_agents: List of available agents
            parameters: Optional capability parameters
            
        Returns:
            Best matching agent result or None
        """
        requirement = TaskRequirement(
            capability=capability,
            required=True,
            parameters=parameters or {},
            priority=5
        )
        
        matches = await self.find_matching_agents([requirement], available_agents, max_results=1)
        return matches[0] if matches else None
    
    async def _evaluate_agent_match(
        self,
        agent: AgentInfo,
        requirements: List[TaskRequirement]
    ) -> MatchResult:
        """Evaluate how well an agent matches the requirements"""
        
        agent_capabilities = {cap.name: cap for cap in agent.capabilities}
        matched_capabilities = []
        missing_capabilities = []
        compatibility_notes = []
        
        total_score = 0.0
        total_weight = 0.0
        
        for req in requirements:
            weight = req.priority
            total_weight += weight
            
            if req.capability in agent_capabilities:
                matched_capabilities.append(req.capability)
                
                # Calculate capability match score
                cap_score = self._calculate_capability_score(
                    agent_capabilities[req.capability],
                    req
                )
                total_score += cap_score * weight
                
                if cap_score < 1.0:
                    compatibility_notes.append(
                        f"Partial match for {req.capability}: {cap_score:.2f}"
                    )
            
            elif req.required:
                missing_capabilities.append(req.capability)
                # Required capability missing - significant penalty
                total_score -= weight * 0.5
            else:
                missing_capabilities.append(req.capability)
                # Optional capability missing - minor penalty
                total_score -= weight * 0.1
        
        # Calculate final score
        if total_weight > 0:
            base_score = max(0.0, total_score / total_weight)
        else:
            base_score = 0.0
        
        # Apply agent-specific modifiers
        final_score = self._apply_agent_modifiers(agent, base_score)
        
        # Add load factor considerations
        if agent.load_factor > 0.8:
            compatibility_notes.append("High load factor")
            final_score *= 0.8
        elif agent.load_factor < 0.3:
            compatibility_notes.append("Low load - good availability")
            final_score *= 1.1
        
        return MatchResult(
            agent=agent,
            score=min(1.0, max(0.0, final_score)),
            matched_capabilities=matched_capabilities,
            missing_capabilities=missing_capabilities,
            compatibility_notes=compatibility_notes
        )
    
    def _calculate_capability_score(
        self,
        agent_capability,
        requirement: TaskRequirement
    ) -> float:
        """Calculate how well an agent capability matches a requirement"""
        
        base_score = 1.0
        
        # Check parameter compatibility if specified
        if requirement.parameters:
            for param_name, param_value in requirement.parameters.items():
                if param_name in agent_capability.parameters:
                    agent_value = agent_capability.parameters[param_name]
                    if agent_value != param_value:
                        # Parameter mismatch - reduce score
                        base_score *= 0.8
                else:
                    # Missing parameter - reduce score
                    base_score *= 0.9
        
        return base_score
    
    def _apply_agent_modifiers(self, agent: AgentInfo, base_score: float) -> float:
        """Apply agent-specific score modifiers"""
        
        # Status modifier
        if agent.status == AgentStatus.HEALTHY:
            status_modifier = 1.0
        elif agent.status == AgentStatus.IDLE:
            status_modifier = 1.1  # Idle agents are preferred
        elif agent.status == AgentStatus.BUSY:
            status_modifier = 0.7  # Busy agents are less preferred
        else:
            status_modifier = 0.5  # Other statuses are penalized
        
        # Version considerations (newer versions preferred slightly)
        version_modifier = 1.0
        try:
            version_parts = agent.version.split('.')
            major = int(version_parts[0])
            if major >= 2:
                version_modifier = 1.05
        except (ValueError, IndexError):
            pass  # Use default modifier for invalid versions
        
        return base_score * status_modifier * version_modifier
    
    def _is_agent_suitable(self, agent: AgentInfo) -> bool:
        """Check if an agent is suitable for task assignment"""
        
        # Must be in good health status
        if agent.status not in [AgentStatus.HEALTHY, AgentStatus.IDLE, AgentStatus.BUSY]:
            return False
        
        # Must not be completely overloaded
        if agent.load_factor >= 1.0:
            return False
        
        # Must have at least one capability
        if not agent.capabilities:
            return False
        
        return True
    
    def get_capability_coverage(
        self,
        requirements: List[TaskRequirement],
        available_agents: List[AgentInfo]
    ) -> Dict[str, List[str]]:
        """
        Get coverage analysis for requirements
        
        Returns:
            Dict mapping each capability to list of agents that can provide it
        """
        coverage = {}
        
        for req in requirements:
            coverage[req.capability] = []
            
            for agent in available_agents:
                agent_capabilities = {cap.name for cap in agent.capabilities}
                if req.capability in agent_capabilities and self._is_agent_suitable(agent):
                    coverage[req.capability].append(agent.agent_id)
        
        return coverage
    
    def clear_cache(self) -> None:
        """Clear the match cache"""
        self.match_cache.clear()
        logger.debug("Capability matcher cache cleared")
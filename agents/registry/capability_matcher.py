"""
Capability Matcher

Matches agents to task requirements based on capabilities.
"""

from typing import Dict, List, Optional, Set
import logging
from dataclasses import dataclass
from .agent_registry import AgentInfo, AgentCapability

logger = logging.getLogger(__name__)


@dataclass 
class TaskRequirement:
    """Task requirement definition"""
    capability: str
    category: str = ""
    parameters: Dict = None
    priority: int = 1  # 1=high, 2=medium, 3=low
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}


@dataclass
class MatchResult:
    """Capability matching result"""
    agent: AgentInfo
    match_score: float
    matched_capabilities: List[str]
    reasons: List[str]


class CapabilityMatcher:
    """Match agents to task requirements based on capabilities"""
    
    def __init__(self):
        self.capability_weights = {
            "exact_match": 10.0,
            "category_match": 5.0,
            "parameter_match": 3.0,
            "agent_health": 2.0,
            "low_load": 1.0
        }
        
    async def match_agents(
        self, 
        task_requirements: List[TaskRequirement],
        available_agents: List[AgentInfo],
        max_results: int = 5
    ) -> List[MatchResult]:
        """Match agents to task requirements"""
        results = []
        
        for agent in available_agents:
            # Skip unhealthy agents
            if agent.status.value in ['offline', 'unhealthy']:
                continue
                
            match_result = await self._calculate_match_score(agent, task_requirements)
            if match_result.match_score > 0:
                results.append(match_result)
                
        # Sort by match score (highest first)
        results.sort(key=lambda x: x.match_score, reverse=True)
        
        return results[:max_results]
        
    async def _calculate_match_score(
        self, 
        agent: AgentInfo, 
        requirements: List[TaskRequirement]
    ) -> MatchResult:
        """Calculate match score for an agent against requirements"""
        total_score = 0.0
        matched_capabilities = []
        reasons = []
        
        # Check each requirement
        for req in requirements:
            best_cap_score = 0.0
            best_cap_name = ""
            
            # Check against all agent capabilities
            for cap in agent.capabilities:
                score = await self._score_capability_match(cap, req)
                if score > best_cap_score:
                    best_cap_score = score
                    best_cap_name = cap.name
                    
            if best_cap_score > 0:
                # Apply priority weighting
                priority_weight = 1.0 / req.priority
                weighted_score = best_cap_score * priority_weight
                total_score += weighted_score
                matched_capabilities.append(best_cap_name)
                reasons.append(f"Matches {req.capability} with {best_cap_name} (score: {best_cap_score:.2f})")
                
        # Add health bonus
        if agent.status.value == 'healthy':
            health_bonus = self.capability_weights["agent_health"]
            total_score += health_bonus
            reasons.append(f"Agent is healthy (+{health_bonus:.1f})")
            
        # Add load bonus (lower load = better)
        if agent.load_score < 0.5:  # Less than 50% load
            load_bonus = self.capability_weights["low_load"] * (1.0 - agent.load_score)
            total_score += load_bonus
            reasons.append(f"Low load factor (+{load_bonus:.1f})")
            
        return MatchResult(
            agent=agent,
            match_score=total_score,
            matched_capabilities=matched_capabilities,
            reasons=reasons
        )
        
    async def _score_capability_match(
        self, 
        capability: AgentCapability, 
        requirement: TaskRequirement
    ) -> float:
        """Score how well a capability matches a requirement"""
        score = 0.0
        
        # Exact name match
        if capability.name.lower() == requirement.capability.lower():
            score += self.capability_weights["exact_match"]
            
        # Partial name match
        elif requirement.capability.lower() in capability.name.lower():
            score += self.capability_weights["exact_match"] * 0.7
            
        # Category match
        if requirement.category and capability.category.lower() == requirement.category.lower():
            score += self.capability_weights["category_match"]
            
        # Parameter compatibility
        if requirement.parameters and capability.parameters:
            param_score = await self._score_parameter_compatibility(
                capability.parameters, 
                requirement.parameters
            )
            score += param_score * self.capability_weights["parameter_match"]
            
        return score
        
    async def _score_parameter_compatibility(
        self, 
        cap_params: Dict, 
        req_params: Dict
    ) -> float:
        """Score parameter compatibility between capability and requirement"""
        if not req_params:
            return 1.0  # No requirements means full compatibility
            
        if not cap_params:
            return 0.0  # Agent has no parameters but requirement does
            
        matches = 0
        total = len(req_params)
        
        for req_key, req_value in req_params.items():
            if req_key in cap_params:
                cap_value = cap_params[req_key]
                
                # Type compatibility
                if type(cap_value) == type(req_value):
                    matches += 1
                # String contains
                elif isinstance(req_value, str) and isinstance(cap_value, str):
                    if req_value.lower() in cap_value.lower():
                        matches += 0.8
                # Numeric range
                elif isinstance(req_value, (int, float)) and isinstance(cap_value, (int, float)):
                    if cap_value >= req_value:
                        matches += 1
                        
        return matches / total if total > 0 else 0.0
        
    async def find_best_agent_for_capability(
        self, 
        capability_name: str,
        available_agents: List[AgentInfo]
    ) -> Optional[AgentInfo]:
        """Find the best single agent for a specific capability"""
        requirement = TaskRequirement(capability=capability_name, priority=1)
        matches = await self.match_agents([requirement], available_agents, max_results=1)
        
        return matches[0].agent if matches else None
        
    async def validate_team_capabilities(
        self, 
        team_agents: List[AgentInfo],
        required_capabilities: List[str]
    ) -> Dict[str, bool]:
        """Validate that a team has all required capabilities"""
        validation_results = {}
        
        for capability in required_capabilities:
            found = False
            for agent in team_agents:
                for cap in agent.capabilities:
                    if cap.name.lower() == capability.lower():
                        found = True
                        break
                if found:
                    break
            validation_results[capability] = found
            
        return validation_results
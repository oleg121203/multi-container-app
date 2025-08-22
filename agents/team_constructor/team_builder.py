"""
Team Builder

Dynamic team formation logic based on task requirements.
"""

from typing import List, Optional, Dict
from dataclasses import dataclass
import logging
from .task_analyzer import TaskAnalysis, TaskRequirement
from ..registry.agent_registry import AgentInfo, AgentRegistry
from ..registry.capability_matcher import CapabilityMatcher
from ..registry.load_balancer import LoadBalancer

logger = logging.getLogger(__name__)


@dataclass
class TeamComposition:
    """Team composition specification"""
    agents: List[AgentInfo]
    roles: Dict[str, str]  # agent_id -> role
    capabilities_coverage: Dict[str, bool]  # capability -> covered
    team_score: float
    formation_strategy: str


class TeamBuilder:
    """Dynamic team formation based on task requirements"""
    
    def __init__(self, agent_registry: AgentRegistry, capability_matcher: CapabilityMatcher, load_balancer: LoadBalancer):
        self.agent_registry = agent_registry
        self.capability_matcher = capability_matcher
        self.load_balancer = load_balancer
        
    async def build_team_for_task(self, task_analysis: TaskAnalysis) -> Optional[TeamComposition]:
        """Build an optimal team for a given task"""
        
        # Get available agents
        available_agents = await self.agent_registry.list_agents()
        if not available_agents:
            logger.warning("No agents available for team formation")
            return None
            
        # Filter out unhealthy agents
        healthy_agents = [a for a in available_agents if a.status.value in ['healthy', 'available']]
        
        if not healthy_agents:
            logger.warning("No healthy agents available for team formation")
            return None
            
        # Try different formation strategies
        strategies = ["capability_first", "balanced", "load_optimized"]
        best_team = None
        best_score = 0.0
        
        for strategy in strategies:
            team = await self._form_team_with_strategy(task_analysis, healthy_agents, strategy)
            if team and team.team_score > best_score:
                best_team = team
                best_score = team.team_score
                
        if best_team:
            logger.info(f"Formed team with {len(best_team.agents)} agents using {best_team.formation_strategy} strategy")
            
        return best_team
        
    async def _form_team_with_strategy(
        self, 
        task_analysis: TaskAnalysis, 
        available_agents: List[AgentInfo],
        strategy: str
    ) -> Optional[TeamComposition]:
        """Form team using a specific strategy"""
        
        if strategy == "capability_first":
            return await self._capability_first_strategy(task_analysis, available_agents)
        elif strategy == "balanced":
            return await self._balanced_strategy(task_analysis, available_agents)
        elif strategy == "load_optimized":
            return await self._load_optimized_strategy(task_analysis, available_agents)
        else:
            logger.warning(f"Unknown strategy: {strategy}")
            return None
            
    async def _capability_first_strategy(
        self, 
        task_analysis: TaskAnalysis, 
        available_agents: List[AgentInfo]
    ) -> Optional[TeamComposition]:
        """Form team by prioritizing capability coverage"""
        
        selected_agents = []
        covered_capabilities = set()
        
        # First, ensure critical capabilities are covered
        critical_requirements = [r for r in task_analysis.required_capabilities if r.priority == 1]
        
        for req in critical_requirements:
            matches = await self.capability_matcher.match_agents(
                [req], available_agents, max_results=3
            )
            
            if matches:
                # Select best match that's not already selected
                for match in matches:
                    if match.agent not in selected_agents:
                        selected_agents.append(match.agent)
                        covered_capabilities.add(req.capability)
                        break
                        
        # Fill remaining slots with best available agents
        remaining_slots = task_analysis.suggested_team_size - len(selected_agents)
        remaining_agents = [a for a in available_agents if a not in selected_agents]
        
        while remaining_slots > 0 and remaining_agents:
            agent = await self.load_balancer.select_agent(remaining_agents, strategy="least_load")
            if agent:
                selected_agents.append(agent)
                remaining_agents.remove(agent)
                remaining_slots -= 1
            else:
                break
                
        # Calculate coverage and score
        coverage = await self._calculate_capability_coverage(
            selected_agents, task_analysis.required_capabilities
        )
        score = await self._calculate_team_score(selected_agents, coverage, "capability_first")
        
        # Assign basic roles
        roles = await self._assign_basic_roles(selected_agents, task_analysis)
        
        return TeamComposition(
            agents=selected_agents,
            roles=roles,
            capabilities_coverage=coverage,
            team_score=score,
            formation_strategy="capability_first"
        )
        
    async def _balanced_strategy(
        self, 
        task_analysis: TaskAnalysis, 
        available_agents: List[AgentInfo]
    ) -> Optional[TeamComposition]:
        """Form team with balanced consideration of capabilities and load"""
        
        # Get all requirements
        all_requirements = task_analysis.required_capabilities
        
        # Find best agents considering both capability and load
        team_agents = await self.load_balancer.select_agents_for_team(
            available_agents,
            task_analysis.suggested_team_size,
            [req.capability for req in all_requirements if req.priority <= 2]
        )
        
        if not team_agents:
            return None
            
        # Calculate coverage and score
        coverage = await self._calculate_capability_coverage(team_agents, all_requirements)
        score = await self._calculate_team_score(team_agents, coverage, "balanced")
        
        # Assign roles
        roles = await self._assign_basic_roles(team_agents, task_analysis)
        
        return TeamComposition(
            agents=team_agents,
            roles=roles,
            capabilities_coverage=coverage,
            team_score=score,
            formation_strategy="balanced"
        )
        
    async def _load_optimized_strategy(
        self, 
        task_analysis: TaskAnalysis, 
        available_agents: List[AgentInfo]
    ) -> Optional[TeamComposition]:
        """Form team optimized for load distribution"""
        
        # Sort agents by load score (ascending)
        sorted_agents = sorted(available_agents, key=lambda x: x.load_score)
        
        # Select top agents with lowest load
        team_size = min(task_analysis.suggested_team_size, len(sorted_agents))
        selected_agents = sorted_agents[:team_size]
        
        # Calculate coverage and score
        coverage = await self._calculate_capability_coverage(
            selected_agents, task_analysis.required_capabilities
        )
        score = await self._calculate_team_score(selected_agents, coverage, "load_optimized")
        
        # Assign roles
        roles = await self._assign_basic_roles(selected_agents, task_analysis)
        
        return TeamComposition(
            agents=selected_agents,
            roles=roles,
            capabilities_coverage=coverage,
            team_score=score,
            formation_strategy="load_optimized"
        )
        
    async def _calculate_capability_coverage(
        self, 
        agents: List[AgentInfo], 
        requirements: List[TaskRequirement]
    ) -> Dict[str, bool]:
        """Calculate which capabilities are covered by the team"""
        coverage = {}
        
        for req in requirements:
            covered = False
            for agent in agents:
                for cap in agent.capabilities:
                    if cap.name.lower() == req.capability.lower():
                        covered = True
                        break
                if covered:
                    break
            coverage[req.capability] = covered
            
        return coverage
        
    async def _calculate_team_score(
        self, 
        agents: List[AgentInfo], 
        coverage: Dict[str, bool],
        strategy: str
    ) -> float:
        """Calculate overall team score"""
        
        # Base score from capability coverage
        total_capabilities = len(coverage)
        covered_capabilities = sum(1 for covered in coverage.values() if covered)
        coverage_score = covered_capabilities / total_capabilities if total_capabilities > 0 else 0
        
        # Health score (percentage of healthy agents)
        healthy_count = sum(1 for agent in agents if agent.status.value == 'healthy')
        health_score = healthy_count / len(agents) if agents else 0
        
        # Load score (inverse of average load)
        avg_load = sum(agent.load_score for agent in agents) / len(agents) if agents else 1.0
        load_score = 1.0 - min(avg_load, 1.0)
        
        # Weighted combination based on strategy
        if strategy == "capability_first":
            score = coverage_score * 0.7 + health_score * 0.2 + load_score * 0.1
        elif strategy == "balanced":
            score = coverage_score * 0.5 + health_score * 0.3 + load_score * 0.2
        elif strategy == "load_optimized":
            score = coverage_score * 0.3 + health_score * 0.2 + load_score * 0.5
        else:
            score = coverage_score * 0.4 + health_score * 0.3 + load_score * 0.3
            
        return score
        
    async def _assign_basic_roles(
        self, 
        agents: List[AgentInfo], 
        task_analysis: TaskAnalysis
    ) -> Dict[str, str]:
        """Assign basic roles to team members"""
        roles = {}
        
        if not agents:
            return roles
            
        # Assign lead role to agent with highest overall capability match
        lead_agent = agents[0]  # For now, just use first agent
        roles[lead_agent.id] = "team_lead"
        
        # Assign specialist roles based on capabilities
        for i, agent in enumerate(agents[1:], 1):
            # Find best matching capability for this agent
            best_cap = None
            for req in task_analysis.required_capabilities:
                for cap in agent.capabilities:
                    if cap.name.lower() == req.capability.lower():
                        best_cap = cap.name
                        break
                if best_cap:
                    break
                    
            if best_cap:
                roles[agent.id] = f"{best_cap}_specialist"
            else:
                roles[agent.id] = f"team_member_{i}"
                
        return roles
        
    async def validate_team_composition(self, team: TeamComposition, task_analysis: TaskAnalysis) -> Dict[str, any]:
        """Validate that team composition meets task requirements"""
        validation = {
            "valid": True,
            "warnings": [],
            "errors": []
        }
        
        # Check team size
        if len(team.agents) < task_analysis.suggested_team_size:
            validation["warnings"].append(f"Team size ({len(team.agents)}) is smaller than suggested ({task_analysis.suggested_team_size})")
            
        # Check critical capability coverage
        critical_reqs = [r for r in task_analysis.required_capabilities if r.priority == 1]
        for req in critical_reqs:
            if not team.capabilities_coverage.get(req.capability, False):
                validation["errors"].append(f"Critical capability '{req.capability}' is not covered")
                validation["valid"] = False
                
        # Check agent health
        unhealthy_agents = [a for a in team.agents if a.status.value not in ['healthy', 'available']]
        if unhealthy_agents:
            validation["warnings"].append(f"{len(unhealthy_agents)} agents are not in healthy status")
            
        return validation
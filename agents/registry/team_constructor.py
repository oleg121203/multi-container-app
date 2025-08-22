"""
Team Constructor - Dynamic team formation for ATLAS Phase 4

Builds on the Agent Registry to dynamically form teams based on task requirements.
Implements TEAM-02 functionality from the Phase 4 planning document.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum
from dataclasses import dataclass
from agents.registry.agent_registry import AgentRegistry, AgentInfo, AgentStatus
from agents.registry.capability_matcher import CapabilityMatcher, TaskRequirement, MatchResult
from agents.registry.load_balancer import LoadBalancer, LoadBalancingStrategy
from agents.shared.config import config


logger = logging.getLogger(__name__)


class TeamFormationStatus(str, Enum):
    """Team formation status"""
    ANALYZING = "analyzing"
    FORMING = "forming"
    READY = "ready"
    FAILED = "failed"
    DISBANDED = "disbanded"


@dataclass
class TeamMember:
    """Represents a team member with assigned role"""
    agent: AgentInfo
    role: str
    capabilities_assigned: List[str]
    load_allocation: float = 0.0


@dataclass
class Team:
    """Represents a formed team"""
    team_id: str
    task_description: str
    members: List[TeamMember]
    status: TeamFormationStatus
    formation_time: float
    coordinator_agent_id: Optional[str] = None
    estimated_duration: Optional[float] = None
    metadata: Dict[str, str] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class TeamConstructor:
    """
    Dynamic team formation based on task requirements
    
    Analyzes tasks and automatically assembles optimal teams from available agents.
    Provides role assignment and coordination patterns for multi-agent collaboration.
    """
    
    def __init__(
        self,
        registry: AgentRegistry,
        capability_matcher: Optional[CapabilityMatcher] = None,
        load_balancer: Optional[LoadBalancer] = None
    ):
        """Initialize the team constructor"""
        self.registry = registry
        self.capability_matcher = capability_matcher or CapabilityMatcher()
        self.load_balancer = load_balancer or LoadBalancer(registry, self.capability_matcher)
        
        # Configuration
        self.max_team_size = getattr(config, 'ATLAS_TEAM_MAX_SIZE', 5)
        self.formation_timeout = getattr(config, 'ATLAS_TEAM_FORMATION_TIMEOUT', 30)
        
        # Active teams tracking
        self.active_teams: Dict[str, Team] = {}
        self.team_counter = 0
        
        logger.info("Team Constructor initialized")
    
    async def analyze_task_requirements(self, task_description: str) -> List[TaskRequirement]:
        """
        Analyze task description and determine required capabilities
        
        This is a simplified implementation. In a full system, this would use
        LLM-based analysis to understand task complexity and requirements.
        """
        # Simple keyword-based analysis for demo purposes
        requirements = []
        
        # Map keywords to capabilities
        capability_keywords = {
            "ui": "user_interface",
            "interface": "user_interface", 
            "user": "user_interface",
            "frontend": "user_interface",
            "orchestrate": "task_orchestration",
            "coordinate": "task_orchestration",
            "manage": "task_orchestration",
            "plan": "task_planning",
            "execute": "task_orchestration",
            "mcp": "mcp_integration",
            "tool": "mcp_integration",
            "integration": "mcp_integration",
            "linear": "linear_integration",
            "issue": "linear_integration",
            "security": "security_monitoring",
            "monitor": "security_monitoring",
            "compliance": "compliance_checking",
            "search": "rag_search",
            "memory": "semantic_memory",
            "data": "rag_search"
        }
        
        task_lower = task_description.lower()
        detected_capabilities = set()
        
        for keyword, capability in capability_keywords.items():
            if keyword in task_lower:
                detected_capabilities.add(capability)
        
        # Convert to TaskRequirement objects
        for capability in detected_capabilities:
            priority = 5 if capability in ["task_orchestration", "user_interface"] else 3
            requirements.append(TaskRequirement(
                capability=capability,
                required=True,
                priority=priority
            ))
        
        # Always include orchestration if not already present
        if not any(req.capability == "task_orchestration" for req in requirements):
            requirements.append(TaskRequirement(
                capability="task_orchestration", 
                required=True, 
                priority=5
            ))
        
        logger.info(f"Analyzed task requirements: {[req.capability for req in requirements]}")
        return requirements
    
    async def form_team(
        self,
        task_description: str,
        custom_requirements: Optional[List[TaskRequirement]] = None,
        max_team_size: Optional[int] = None
    ) -> Optional[Team]:
        """
        Form a team for the given task
        
        Args:
            task_description: Description of the task
            custom_requirements: Optional custom requirements (overrides analysis)
            max_team_size: Optional override for maximum team size
            
        Returns:
            Formed team or None if formation failed
        """
        start_time = time.time()
        team_id = f"team-{self.team_counter:04d}"
        self.team_counter += 1
        
        logger.info(f"🤝 Forming team {team_id} for task: {task_description}")
        
        try:
            # Analyze requirements
            if custom_requirements:
                requirements = custom_requirements
            else:
                requirements = await self.analyze_task_requirements(task_description)
            
            if not requirements:
                logger.warning(f"No requirements determined for task: {task_description}")
                return None
            
            # Get available agents
            available_agents = await self.registry.get_available_agents()
            if not available_agents:
                logger.warning("No available agents for team formation")
                return None
            
            # Find suitable agents for each requirement
            team_members = await self._select_team_members(
                requirements, available_agents, max_team_size or self.max_team_size
            )
            
            if not team_members:
                logger.warning(f"Could not form team for task: {task_description}")
                return None
            
            # Create team
            team = Team(
                team_id=team_id,
                task_description=task_description,
                members=team_members,
                status=TeamFormationStatus.READY,
                formation_time=time.time() - start_time
            )
            
            # Assign coordinator (agent with orchestration capability)
            coordinator = self._select_coordinator(team_members)
            if coordinator:
                team.coordinator_agent_id = coordinator.agent.agent_id
            
            # Track active team
            self.active_teams[team_id] = team
            
            # Update agent statuses
            await self._update_team_member_status(team_members)
            
            logger.info(f"✅ Team {team_id} formed successfully with {len(team_members)} members")
            self._log_team_composition(team)
            
            return team
            
        except Exception as e:
            logger.error(f"Failed to form team {team_id}: {e}")
            return None
    
    async def _select_team_members(
        self,
        requirements: List[TaskRequirement],
        available_agents: List[AgentInfo],
        max_team_size: int
    ) -> List[TeamMember]:
        """Select optimal team members for the requirements"""
        
        # Get capability matches
        matches = await self.capability_matcher.find_matching_agents(
            requirements, available_agents, max_results=max_team_size * 2
        )
        
        if not matches:
            return []
        
        # Team selection algorithm
        selected_members = []
        covered_capabilities = set()
        used_agents = set()
        
        # Required capabilities first
        required_caps = [req.capability for req in requirements if req.required]
        
        for capability in required_caps:
            if capability in covered_capabilities:
                continue
            
            # Find best available agent for this capability
            best_match = None
            best_score = -1
            
            for match in matches:
                if (capability in match.matched_capabilities and
                    match.agent.agent_id not in used_agents and
                    match.score > best_score):
                    best_match = match
                    best_score = match.score
            
            if best_match:
                member = TeamMember(
                    agent=best_match.agent,
                    role=self._determine_role(capability, best_match.matched_capabilities),
                    capabilities_assigned=best_match.matched_capabilities,
                    load_allocation=0.8  # Default load allocation
                )
                
                selected_members.append(member)
                covered_capabilities.update(best_match.matched_capabilities)
                used_agents.add(best_match.agent.agent_id)
                
                if len(selected_members) >= max_team_size:
                    break
        
        # Add optional capabilities if team size allows
        if len(selected_members) < max_team_size:
            optional_caps = [req.capability for req in requirements if not req.required]
            
            for capability in optional_caps:
                if capability in covered_capabilities or len(selected_members) >= max_team_size:
                    continue
                
                for match in matches:
                    if (capability in match.matched_capabilities and
                        match.agent.agent_id not in used_agents):
                        
                        member = TeamMember(
                            agent=match.agent,
                            role=self._determine_role(capability, match.matched_capabilities),
                            capabilities_assigned=match.matched_capabilities,
                            load_allocation=0.5  # Lower load for optional members
                        )
                        
                        selected_members.append(member)
                        covered_capabilities.update(match.matched_capabilities)
                        used_agents.add(match.agent.agent_id)
                        break
        
        return selected_members
    
    def _determine_role(self, primary_capability: str, all_capabilities: List[str]) -> str:
        """Determine appropriate role based on capabilities"""
        role_mapping = {
            "task_orchestration": "Coordinator",
            "user_interface": "Frontend Specialist", 
            "security_monitoring": "Security Guard",
            "mcp_integration": "Tool Specialist",
            "linear_integration": "Project Manager",
            "task_planning": "Planner",
            "rag_search": "Knowledge Specialist",
            "semantic_memory": "Memory Specialist"
        }
        
        # Primary role from main capability
        primary_role = role_mapping.get(primary_capability, "Specialist")
        
        # Check for multi-role capabilities
        if len(all_capabilities) > 1:
            if "task_orchestration" in all_capabilities:
                return "Lead " + primary_role
            elif len(all_capabilities) >= 3:
                return "Multi-" + primary_role
        
        return primary_role
    
    def _select_coordinator(self, team_members: List[TeamMember]) -> Optional[TeamMember]:
        """Select team coordinator from members"""
        # Prefer agents with orchestration capability
        for member in team_members:
            if "task_orchestration" in member.capabilities_assigned:
                return member
        
        # Fallback to first member if no orchestrator
        return team_members[0] if team_members else None
    
    async def _update_team_member_status(self, members: List[TeamMember]) -> None:
        """Update status of team members"""
        for member in members:
            await self.registry.update_agent_status(
                member.agent.agent_id, 
                AgentStatus.BUSY, 
                member.load_allocation
            )
    
    def _log_team_composition(self, team: Team) -> None:
        """Log team composition details"""
        logger.info(f"Team {team.team_id} composition:")
        for member in team.members:
            logger.info(f"  • {member.agent.name} as {member.role}")
            logger.info(f"    Capabilities: {member.capabilities_assigned}")
        
        if team.coordinator_agent_id:
            coordinator = next(
                (m for m in team.members if m.agent.agent_id == team.coordinator_agent_id), 
                None
            )
            if coordinator:
                logger.info(f"  🎯 Coordinator: {coordinator.agent.name}")
    
    async def disband_team(self, team_id: str) -> bool:
        """
        Disband a team and release agents
        
        Args:
            team_id: Team identifier
            
        Returns:
            True if team was disbanded successfully
        """
        if team_id not in self.active_teams:
            return False
        
        team = self.active_teams[team_id]
        
        # Release team members
        for member in team.members:
            await self.registry.update_agent_status(
                member.agent.agent_id, 
                AgentStatus.IDLE, 
                0.0
            )
        
        # Update team status
        team.status = TeamFormationStatus.DISBANDED
        
        # Remove from active teams
        del self.active_teams[team_id]
        
        logger.info(f"Team {team_id} disbanded successfully")
        return True
    
    async def get_team_info(self, team_id: str) -> Optional[Team]:
        """Get information about a specific team"""
        return self.active_teams.get(team_id)
    
    def list_active_teams(self) -> List[Team]:
        """List all active teams"""
        return list(self.active_teams.values())
    
    def get_formation_statistics(self) -> Dict[str, float]:
        """Get team formation statistics"""
        if not self.active_teams:
            return {}
        
        teams = list(self.active_teams.values())
        formation_times = [team.formation_time for team in teams]
        team_sizes = [len(team.members) for team in teams]
        
        return {
            "total_active_teams": len(teams),
            "average_formation_time": sum(formation_times) / len(formation_times),
            "average_team_size": sum(team_sizes) / len(team_sizes),
            "max_team_size": max(team_sizes) if team_sizes else 0,
            "min_team_size": min(team_sizes) if team_sizes else 0
        }
    
    async def suggest_team_improvements(self, team_id: str) -> List[str]:
        """Suggest improvements for an existing team"""
        if team_id not in self.active_teams:
            return ["Team not found"]
        
        team = self.active_teams[team_id]
        suggestions = []
        
        # Check for missing critical capabilities
        all_capabilities = set()
        for member in team.members:
            all_capabilities.update(member.capabilities_assigned)
        
        if "security_monitoring" not in all_capabilities:
            suggestions.append("Consider adding a security specialist")
        
        if "compliance_checking" not in all_capabilities:
            suggestions.append("Consider adding compliance monitoring")
        
        # Check team balance
        if len(team.members) == 1:
            suggestions.append("Single-member team - consider adding redundancy")
        
        # Check load distribution
        loads = [member.load_allocation for member in team.members]
        if max(loads) - min(loads) > 0.4:
            suggestions.append("Unbalanced load distribution - consider rebalancing")
        
        return suggestions if suggestions else ["Team composition looks optimal"]
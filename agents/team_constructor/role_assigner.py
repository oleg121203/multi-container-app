"""
Role Assigner

Assign specific roles to agents within teams.
"""

from typing import Dict, List
from dataclasses import dataclass
import logging
from ..registry.agent_registry import AgentInfo

logger = logging.getLogger(__name__)


@dataclass
class AgentRole:
    """Agent role definition"""
    name: str
    description: str
    responsibilities: List[str]
    required_capabilities: List[str]


class RoleAssigner:
    """Assign roles to team members based on capabilities and task needs"""
    
    def __init__(self):
        # Predefined role templates
        self.role_templates = {
            "team_lead": AgentRole(
                name="Team Lead",
                description="Coordinates team activities and makes decisions",
                responsibilities=["Coordinate team", "Make decisions", "Report progress"],
                required_capabilities=["coordination", "analysis"]
            ),
            "analyst": AgentRole(
                name="Analyst",
                description="Analyzes data and provides insights",
                responsibilities=["Analyze data", "Generate insights", "Create reports"],
                required_capabilities=["analysis", "research"]
            ),
            "developer": AgentRole(
                name="Developer",
                description="Implements code and technical solutions",
                responsibilities=["Write code", "Implement features", "Debug issues"],
                required_capabilities=["coding", "automation"]
            ),
            "monitor": AgentRole(
                name="Monitor",
                description="Monitors systems and processes",
                responsibilities=["Monitor health", "Track metrics", "Alert on issues"],
                required_capabilities=["monitoring", "analysis"]
            )
        }
        
    async def assign_roles(self, agents: List[AgentInfo], task_type: str = None) -> Dict[str, str]:
        """Assign roles to team members"""
        roles = {}
        
        if not agents:
            return roles
            
        # Assign team lead (agent with best coordination capability)
        lead_agent = await self._find_best_coordinator(agents)
        if lead_agent:
            roles[lead_agent.id] = "team_lead"
            
        # Assign specialist roles to remaining agents
        remaining_agents = [a for a in agents if a.id != (lead_agent.id if lead_agent else None)]
        
        for agent in remaining_agents:
            role = await self._assign_specialist_role(agent)
            roles[agent.id] = role
            
        return roles
        
    async def _find_best_coordinator(self, agents: List[AgentInfo]) -> AgentInfo:
        """Find the best agent for coordination role"""
        coordinator_candidates = []
        
        for agent in agents:
            for cap in agent.capabilities:
                if cap.name.lower() in ['coordination', 'management', 'orchestration']:
                    coordinator_candidates.append(agent)
                    break
                    
        # Return first coordinator candidate, or first agent if none found
        return coordinator_candidates[0] if coordinator_candidates else agents[0]
        
    async def _assign_specialist_role(self, agent: AgentInfo) -> str:
        """Assign specialist role based on agent capabilities"""
        
        # Check capabilities and assign most appropriate role
        for cap in agent.capabilities:
            cap_name = cap.name.lower()
            
            if cap_name in ['coding', 'programming', 'development']:
                return "developer"
            elif cap_name in ['analysis', 'analytics', 'research']:
                return "analyst"
            elif cap_name in ['monitoring', 'tracking', 'surveillance']:
                return "monitor"
                
        # Default role if no specific match
        return "team_member"
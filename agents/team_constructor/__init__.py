"""
ATLAS Team Constructor (TEAM-02)

Enable dynamic formation of agent teams based on task complexity and requirements.
"""

from .task_analyzer import TaskAnalyzer
from .team_builder import TeamBuilder
from .role_assigner import RoleAssigner
from .coordination_engine import CoordinationEngine

__all__ = [
    'TaskAnalyzer',
    'TeamBuilder', 
    'RoleAssigner',
    'CoordinationEngine'
]
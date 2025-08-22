"""
ATLAS Phase 4 - Role Templates System (TEAM-04)

Provides predefined agent roles and behavioral templates.
Enables standardized role definitions and runtime role assignment.
"""

from .role_template import (
    RoleTemplate, RoleCategory, BehaviorPattern, RoleConstraint, RoleMetrics,
    CommunicationStyle, DecisionMakingStyle
)
from .role_library import RoleLibrary
from .role_manager import RoleManager, RoleAssignment, AssignmentType, AssignmentStatus
from .behavioral_patterns import BehavioralPatternEngine, PatternExecutionStatus

__all__ = [
    "RoleTemplate",
    "RoleCategory", 
    "BehaviorPattern",
    "RoleConstraint",
    "RoleMetrics",
    "CommunicationStyle",
    "DecisionMakingStyle",
    "RoleLibrary",
    "RoleManager",
    "RoleAssignment",
    "AssignmentType",
    "AssignmentStatus",
    "BehavioralPatternEngine",
    "PatternExecutionStatus"
]
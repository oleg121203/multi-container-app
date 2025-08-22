"""
Role Template - Core role definition system for ATLAS Phase 4

Defines the structure and properties of agent roles.
Provides templates for consistent role behavior and capabilities.
"""

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class RoleCategory(str, Enum):
    """Categories of agent roles"""
    COORDINATOR = "coordinator"  # Manages and coordinates other agents
    SPECIALIST = "specialist"  # Domain-specific expertise
    ANALYST = "analyst"  # Data analysis and insights
    COMMUNICATOR = "communicator"  # Handles external communications
    MODERATOR = "moderator"  # Facilitates discussions and decisions
    EXECUTOR = "executor"  # Executes tasks and operations
    OBSERVER = "observer"  # Monitors and reports
    CREATIVE = "creative"  # Generates ideas and solutions
    VALIDATOR = "validator"  # Reviews and validates work


class CommunicationStyle(str, Enum):
    """Communication styles for roles"""
    FORMAL = "formal"
    CASUAL = "casual"
    TECHNICAL = "technical"
    PERSUASIVE = "persuasive"
    ANALYTICAL = "analytical"
    SUPPORTIVE = "supportive"
    ASSERTIVE = "assertive"
    COLLABORATIVE = "collaborative"


class DecisionMakingStyle(str, Enum):
    """Decision making approaches"""
    AUTHORITATIVE = "authoritative"
    DEMOCRATIC = "democratic"
    CONSULTATIVE = "consultative"
    DELEGATING = "delegating"
    CONSENSUS_SEEKING = "consensus_seeking"
    DATA_DRIVEN = "data_driven"
    INTUITIVE = "intuitive"


@dataclass
class BehaviorPattern:
    """Defines behavioral patterns for roles"""
    pattern_id: str
    name: str
    description: str
    triggers: List[str] = field(default_factory=list)  # When this pattern activates
    actions: List[str] = field(default_factory=list)  # What actions to take
    communication_rules: Dict[str, str] = field(default_factory=dict)
    priority: int = 0  # Higher priority patterns override lower ones
    conditions: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RoleConstraint:
    """Constraints and limitations for roles"""
    constraint_id: str
    constraint_type: str  # permission, resource, interaction, etc.
    description: str
    rules: List[str] = field(default_factory=list)
    exceptions: List[str] = field(default_factory=list)
    severity: str = "medium"  # low, medium, high, critical


@dataclass
class RoleMetrics:
    """Metrics for measuring role performance"""
    metric_name: str
    description: str
    measurement_type: str  # count, percentage, time, quality_score
    target_value: Optional[float] = None
    weight: float = 1.0
    calculation_method: Optional[str] = None


class RoleTemplate(BaseModel):
    """
    Template defining an agent role
    
    Provides structure for role definition including behaviors, capabilities,
    communication patterns, and interaction rules.
    """
    
    role_id: str
    name: str
    description: str
    category: RoleCategory
    version: str = "1.0.0"
    
    # Core characteristics
    required_capabilities: List[str] = Field(default_factory=list)
    preferred_capabilities: List[str] = Field(default_factory=list)
    communication_style: CommunicationStyle = CommunicationStyle.COLLABORATIVE
    decision_making_style: DecisionMakingStyle = DecisionMakingStyle.CONSULTATIVE
    
    # Behavioral patterns
    behavior_patterns: List[BehaviorPattern] = Field(default_factory=list)
    interaction_rules: Dict[str, str] = Field(default_factory=dict)
    response_templates: Dict[str, str] = Field(default_factory=dict)
    
    # Role hierarchy and relationships
    parent_roles: List[str] = Field(default_factory=list)  # Inherits from these roles
    child_roles: List[str] = Field(default_factory=list)   # Can delegate to these roles
    peer_roles: List[str] = Field(default_factory=list)    # Collaborates with these roles
    
    # Constraints and permissions
    constraints: List[RoleConstraint] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)
    resource_limits: Dict[str, Any] = Field(default_factory=dict)
    
    # Performance and metrics
    performance_metrics: List[RoleMetrics] = Field(default_factory=list)
    success_criteria: List[str] = Field(default_factory=list)
    
    # Metadata
    tags: List[str] = Field(default_factory=list)
    author: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def add_behavior_pattern(self, pattern: BehaviorPattern) -> None:
        """Add a behavior pattern to the role"""
        # Remove existing pattern with same ID
        self.behavior_patterns = [
            p for p in self.behavior_patterns if p.pattern_id != pattern.pattern_id
        ]
        self.behavior_patterns.append(pattern)
        self.behavior_patterns.sort(key=lambda p: p.priority, reverse=True)

    def remove_behavior_pattern(self, pattern_id: str) -> bool:
        """Remove a behavior pattern"""
        original_count = len(self.behavior_patterns)
        self.behavior_patterns = [
            p for p in self.behavior_patterns if p.pattern_id != pattern_id
        ]
        return len(self.behavior_patterns) < original_count

    def get_behavior_pattern(self, pattern_id: str) -> Optional[BehaviorPattern]:
        """Get a specific behavior pattern"""
        for pattern in self.behavior_patterns:
            if pattern.pattern_id == pattern_id:
                return pattern
        return None

    def add_constraint(self, constraint: RoleConstraint) -> None:
        """Add a constraint to the role"""
        # Remove existing constraint with same ID
        self.constraints = [
            c for c in self.constraints if c.constraint_id != constraint.constraint_id
        ]
        self.constraints.append(constraint)

    def remove_constraint(self, constraint_id: str) -> bool:
        """Remove a constraint"""
        original_count = len(self.constraints)
        self.constraints = [
            c for c in self.constraints if c.constraint_id != constraint_id
        ]
        return len(self.constraints) < original_count

    def is_capability_required(self, capability: str) -> bool:
        """Check if a capability is required for this role"""
        return capability in self.required_capabilities

    def is_capability_preferred(self, capability: str) -> bool:
        """Check if a capability is preferred for this role"""
        return capability in self.preferred_capabilities

    def get_interaction_rule(self, context: str) -> Optional[str]:
        """Get interaction rule for a specific context"""
        return self.interaction_rules.get(context)

    def get_response_template(self, template_type: str) -> Optional[str]:
        """Get response template for a specific type"""
        return self.response_templates.get(template_type)

    def calculate_compatibility_score(self, agent_capabilities: List[str]) -> float:
        """Calculate how well an agent's capabilities match this role"""
        if not self.required_capabilities and not self.preferred_capabilities:
            return 1.0
        
        # Check required capabilities
        required_score = 0.0
        if self.required_capabilities:
            required_matches = sum(
                1 for cap in self.required_capabilities 
                if cap in agent_capabilities
            )
            required_score = required_matches / len(self.required_capabilities)
        else:
            required_score = 1.0  # No required capabilities = perfect match
        
        # Check preferred capabilities
        preferred_score = 0.0
        if self.preferred_capabilities:
            preferred_matches = sum(
                1 for cap in self.preferred_capabilities 
                if cap in agent_capabilities
            )
            preferred_score = preferred_matches / len(self.preferred_capabilities)
        
        # Weight required capabilities more heavily
        total_score = (required_score * 0.7) + (preferred_score * 0.3)
        return min(1.0, max(0.0, total_score))

    def inherit_from_parent(self, parent_template: 'RoleTemplate') -> None:
        """Inherit properties from a parent role template"""
        # Inherit capabilities (merge, not replace)
        for cap in parent_template.required_capabilities:
            if cap not in self.required_capabilities:
                self.required_capabilities.append(cap)
        
        for cap in parent_template.preferred_capabilities:
            if cap not in self.preferred_capabilities:
                self.preferred_capabilities.append(cap)
        
        # Inherit behavior patterns (lower priority than own patterns)
        for pattern in parent_template.behavior_patterns:
            # Check if we already have this pattern
            existing = self.get_behavior_pattern(pattern.pattern_id)
            if not existing:
                # Add with reduced priority
                inherited_pattern = BehaviorPattern(
                    pattern_id=f"inherited_{pattern.pattern_id}",
                    name=f"Inherited: {pattern.name}",
                    description=pattern.description,
                    triggers=pattern.triggers.copy(),
                    actions=pattern.actions.copy(),
                    communication_rules=pattern.communication_rules.copy(),
                    priority=max(0, pattern.priority - 10),  # Lower priority
                    conditions=pattern.conditions.copy(),
                    metadata={**pattern.metadata, "inherited": True}
                )
                self.behavior_patterns.append(inherited_pattern)
        
        # Sort patterns by priority
        self.behavior_patterns.sort(key=lambda p: p.priority, reverse=True)
        
        # Inherit interaction rules (don't override existing ones)
        for context, rule in parent_template.interaction_rules.items():
            if context not in self.interaction_rules:
                self.interaction_rules[context] = rule
        
        # Inherit response templates (don't override existing ones)
        for template_type, template in parent_template.response_templates.items():
            if template_type not in self.response_templates:
                self.response_templates[template_type] = template
        
        # Inherit permissions (merge)
        for permission in parent_template.permissions:
            if permission not in self.permissions:
                self.permissions.append(permission)

    def validate_role_consistency(self) -> List[str]:
        """Validate role consistency and return any issues found"""
        issues = []
        
        # Check for required fields
        if not self.role_id:
            issues.append("Role ID is required")
        if not self.name:
            issues.append("Role name is required")
        if not self.description:
            issues.append("Role description is required")
        
        # Check for capability conflicts
        conflicting_caps = set(self.required_capabilities) & set(self.preferred_capabilities)
        if conflicting_caps:
            issues.append(f"Capabilities appear in both required and preferred: {conflicting_caps}")
        
        # Check behavior pattern priorities
        pattern_ids = [p.pattern_id for p in self.behavior_patterns]
        if len(pattern_ids) != len(set(pattern_ids)):
            issues.append("Duplicate behavior pattern IDs found")
        
        # Check constraint consistency
        constraint_ids = [c.constraint_id for c in self.constraints]
        if len(constraint_ids) != len(set(constraint_ids)):
            issues.append("Duplicate constraint IDs found")
        
        return issues

    def clone(self, new_role_id: str, new_name: Optional[str] = None) -> 'RoleTemplate':
        """Create a copy of this role template with a new ID"""
        cloned_data = self.dict()
        cloned_data['role_id'] = new_role_id
        if new_name:
            cloned_data['name'] = new_name
        cloned_data['created_at'] = datetime.now(timezone.utc)
        cloned_data['updated_at'] = datetime.now(timezone.utc)
        
        return RoleTemplate(**cloned_data)

    class Config:
        arbitrary_types_allowed = True
"""
Role Manager - Runtime role assignment and management for ATLAS Phase 4

Manages dynamic role assignment to agents and tracks role performance.
Handles role switching, inheritance, and behavioral pattern application.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from pydantic import BaseModel, Field

from agents.registry.agent_registry import AgentRegistry, AgentInfo
from agents.roles.role_template import RoleTemplate
from agents.roles.role_library import RoleLibrary

logger = logging.getLogger(__name__)


class AssignmentStatus(str, Enum):
    """Status of role assignments"""
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    COMPLETED = "completed"
    FAILED = "failed"


class AssignmentType(str, Enum):
    """Type of role assignment"""
    PRIMARY = "primary"  # Main role for the agent
    SECONDARY = "secondary"  # Supporting role
    TEMPORARY = "temporary"  # Temporary role for specific task
    FALLBACK = "fallback"  # Backup role if primary fails


@dataclass
class RolePerformanceMetric:
    """Tracks performance metrics for a role assignment"""
    metric_name: str
    current_value: float
    target_value: Optional[float]
    measurement_count: int = 0
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    history: List[float] = field(default_factory=list)


@dataclass
class RoleAssignment:
    """Represents an active role assignment"""
    assignment_id: str
    agent_id: str
    role_id: str
    role_template: RoleTemplate
    assignment_type: AssignmentType = AssignmentType.PRIMARY
    status: AssignmentStatus = AssignmentStatus.PENDING
    assigned_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    assigned_by: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, RolePerformanceMetric] = field(default_factory=dict)
    behavioral_overrides: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class RoleManager:
    """
    Manages role assignments and performance tracking
    
    Handles dynamic role assignment to agents, tracks performance metrics,
    and manages role transitions and behavioral patterns.
    """
    
    def __init__(
        self,
        agent_registry: AgentRegistry,
        role_library: RoleLibrary
    ):
        """Initialize the role manager"""
        self.agent_registry = agent_registry
        self.role_library = role_library
        self.active_assignments: Dict[str, RoleAssignment] = {}  # assignment_id -> assignment
        self.agent_roles: Dict[str, List[str]] = {}  # agent_id -> list of assignment_ids
        self.role_assignments: Dict[str, List[str]] = {}  # role_id -> list of assignment_ids
        self._assignment_counter = 0
        self._performance_trackers: Dict[str, Any] = {}
        
        logger.info("RoleManager initialized")

    async def assign_role(
        self,
        agent_id: str,
        role_id: str,
        assignment_type: AssignmentType = AssignmentType.PRIMARY,
        assigned_by: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        behavioral_overrides: Optional[Dict[str, Any]] = None
    ) -> Optional[RoleAssignment]:
        """Assign a role to an agent"""
        
        # Validate agent exists
        agent = await self.agent_registry.get_agent(agent_id)
        if not agent:
            logger.error(f"Agent {agent_id} not found in registry")
            return None
        
        # Validate role exists
        role_template = self.role_library.get_role_template(role_id)
        if not role_template:
            logger.error(f"Role template {role_id} not found in library")
            return None
        
        # Check role compatibility
        agent_capabilities = [cap.name for cap in agent.capabilities]
        compatibility = role_template.calculate_compatibility_score(agent_capabilities)
        
        if compatibility < 0.3:  # Minimum compatibility threshold
            logger.warning(f"Low compatibility ({compatibility:.2f}) between agent {agent_id} and role {role_id}")
        
        # Check for conflicting assignments
        if assignment_type == AssignmentType.PRIMARY:
            existing_primary = self._get_primary_role_assignment(agent_id)
            if existing_primary:
                logger.warning(f"Agent {agent_id} already has primary role {existing_primary.role_id}")
                # Suspend existing primary role
                await self.suspend_assignment(existing_primary.assignment_id)
        
        # Create assignment
        self._assignment_counter += 1
        assignment_id = f"assignment_{agent_id}_{role_id}_{self._assignment_counter}"
        
        assignment = RoleAssignment(
            assignment_id=assignment_id,
            agent_id=agent_id,
            role_id=role_id,
            role_template=role_template,
            assignment_type=assignment_type,
            assigned_by=assigned_by,
            context=context or {},
            behavioral_overrides=behavioral_overrides or {}
        )
        
        # Initialize performance metrics
        for metric in role_template.performance_metrics:
            assignment.performance_metrics[metric.metric_name] = RolePerformanceMetric(
                metric_name=metric.metric_name,
                current_value=0.0,
                target_value=metric.target_value
            )
        
        # Store assignment
        self.active_assignments[assignment_id] = assignment
        
        # Update indices
        if agent_id not in self.agent_roles:
            self.agent_roles[agent_id] = []
        self.agent_roles[agent_id].append(assignment_id)
        
        if role_id not in self.role_assignments:
            self.role_assignments[role_id] = []
        self.role_assignments[role_id].append(assignment_id)
        
        logger.info(f"Assigned role {role_id} to agent {agent_id} (assignment: {assignment_id})")
        return assignment

    async def activate_assignment(self, assignment_id: str) -> bool:
        """Activate a pending role assignment"""
        assignment = self.active_assignments.get(assignment_id)
        if not assignment:
            logger.warning(f"Assignment {assignment_id} not found")
            return False
        
        if assignment.status != AssignmentStatus.PENDING:
            logger.warning(f"Assignment {assignment_id} is not in pending state")
            return False
        
        assignment.status = AssignmentStatus.ACTIVE
        assignment.started_at = datetime.now(timezone.utc)
        
        # Apply role template behavioral patterns
        await self._apply_behavioral_patterns(assignment)
        
        logger.info(f"Activated assignment {assignment_id}")
        return True

    async def suspend_assignment(self, assignment_id: str) -> bool:
        """Suspend an active role assignment"""
        assignment = self.active_assignments.get(assignment_id)
        if not assignment:
            return False
        
        if assignment.status == AssignmentStatus.ACTIVE:
            assignment.status = AssignmentStatus.SUSPENDED
            logger.info(f"Suspended assignment {assignment_id}")
            return True
        
        return False

    async def complete_assignment(
        self,
        assignment_id: str,
        completion_reason: Optional[str] = None
    ) -> bool:
        """Complete a role assignment"""
        assignment = self.active_assignments.get(assignment_id)
        if not assignment:
            return False
        
        assignment.status = AssignmentStatus.COMPLETED
        assignment.ended_at = datetime.now(timezone.utc)
        
        if completion_reason:
            assignment.metadata["completion_reason"] = completion_reason
        
        # Calculate final performance metrics
        await self._calculate_final_metrics(assignment)
        
        logger.info(f"Completed assignment {assignment_id}")
        return True

    async def switch_role(
        self,
        agent_id: str,
        new_role_id: str,
        transition_type: str = "immediate"
    ) -> Optional[RoleAssignment]:
        """Switch an agent's primary role"""
        
        # Get current primary role
        current_assignment = self._get_primary_role_assignment(agent_id)
        
        # Assign new role
        new_assignment = await self.assign_role(
            agent_id=agent_id,
            role_id=new_role_id,
            assignment_type=AssignmentType.PRIMARY,
            context={"transition_type": transition_type}
        )
        
        if new_assignment:
            await self.activate_assignment(new_assignment.assignment_id)
            
            # Handle old assignment based on transition type
            if current_assignment:
                if transition_type == "immediate":
                    await self.complete_assignment(
                        current_assignment.assignment_id,
                        "Role switch"
                    )
                elif transition_type == "gradual":
                    await self.suspend_assignment(current_assignment.assignment_id)
            
            logger.info(f"Switched agent {agent_id} from {current_assignment.role_id if current_assignment else None} to {new_role_id}")
        
        return new_assignment

    def get_agent_roles(self, agent_id: str) -> List[RoleAssignment]:
        """Get all role assignments for an agent"""
        assignment_ids = self.agent_roles.get(agent_id, [])
        return [
            self.active_assignments[aid] for aid in assignment_ids
            if aid in self.active_assignments
        ]

    def get_primary_role(self, agent_id: str) -> Optional[RoleAssignment]:
        """Get the primary role assignment for an agent"""
        return self._get_primary_role_assignment(agent_id)

    def get_role_assignments(self, role_id: str) -> List[RoleAssignment]:
        """Get all assignments for a specific role"""
        assignment_ids = self.role_assignments.get(role_id, [])
        return [
            self.active_assignments[aid] for aid in assignment_ids
            if aid in self.active_assignments
        ]

    async def update_performance_metric(
        self,
        assignment_id: str,
        metric_name: str,
        value: float
    ) -> bool:
        """Update a performance metric for a role assignment"""
        assignment = self.active_assignments.get(assignment_id)
        if not assignment:
            return False
        
        if metric_name not in assignment.performance_metrics:
            # Create new metric
            assignment.performance_metrics[metric_name] = RolePerformanceMetric(
                metric_name=metric_name,
                current_value=value,
                target_value=None
            )
        else:
            metric = assignment.performance_metrics[metric_name]
            metric.history.append(metric.current_value)
            metric.current_value = value
            metric.measurement_count += 1
            metric.last_updated = datetime.now(timezone.utc)
            
            # Keep only last 100 measurements
            if len(metric.history) > 100:
                metric.history = metric.history[-100:]
        
        return True

    def get_performance_summary(self, assignment_id: str) -> Dict[str, Any]:
        """Get performance summary for a role assignment"""
        assignment = self.active_assignments.get(assignment_id)
        if not assignment:
            return {}
        
        summary = {
            "assignment_id": assignment_id,
            "agent_id": assignment.agent_id,
            "role_id": assignment.role_id,
            "status": assignment.status,
            "duration": None,
            "metrics": {}
        }
        
        # Calculate duration
        if assignment.started_at:
            end_time = assignment.ended_at or datetime.now(timezone.utc)
            duration = (end_time - assignment.started_at).total_seconds()
            summary["duration"] = duration
        
        # Compile metrics
        for metric_name, metric in assignment.performance_metrics.items():
            metric_summary = {
                "current_value": metric.current_value,
                "target_value": metric.target_value,
                "measurement_count": metric.measurement_count,
                "last_updated": metric.last_updated
            }
            
            # Calculate statistics if we have history
            if metric.history:
                metric_summary["average"] = sum(metric.history) / len(metric.history)
                metric_summary["trend"] = "improving" if metric.current_value > metric_summary["average"] else "declining"
            
            summary["metrics"][metric_name] = metric_summary
        
        return summary

    async def suggest_role_optimization(self, agent_id: str) -> List[str]:
        """Suggest role optimizations for an agent"""
        suggestions = []
        
        agent = await self.agent_registry.get_agent(agent_id)
        if not agent:
            return suggestions
        
        current_roles = self.get_agent_roles(agent_id)
        agent_capabilities = [cap.name for cap in agent.capabilities]
        
        # Check for better role matches
        compatible_roles = self.role_library.find_compatible_roles(
            agent_capabilities,
            min_compatibility=0.7
        )
        
        # Compare with current roles
        for role_template, compatibility in compatible_roles[:3]:  # Top 3
            current_role_ids = [r.role_id for r in current_roles if r.status == AssignmentStatus.ACTIVE]
            if role_template.role_id not in current_role_ids:
                suggestions.append(f"Consider role {role_template.name} (compatibility: {compatibility:.1%})")
        
        # Check performance of current roles
        for assignment in current_roles:
            if assignment.status == AssignmentStatus.ACTIVE:
                performance = self.get_performance_summary(assignment.assignment_id)
                if performance.get("metrics"):
                    poor_metrics = []
                    for metric_name, metric_data in performance["metrics"].items():
                        target = metric_data.get("target_value")
                        current = metric_data.get("current_value", 0)
                        if target and current < target * 0.7:  # Below 70% of target
                            poor_metrics.append(metric_name)
                    
                    if poor_metrics:
                        suggestions.append(f"Role {assignment.role_id} underperforming in: {', '.join(poor_metrics)}")
        
        return suggestions

    async def get_role_coverage_analysis(self) -> Dict[str, Any]:
        """Analyze role coverage across all agents"""
        analysis = {
            "total_agents": len(await self.agent_registry.list_agents()),
            "agents_with_roles": len(self.agent_roles),
            "role_distribution": {},
            "capability_gaps": [],
            "over_allocated_roles": [],
            "under_allocated_roles": []
        }
        
        # Count role assignments
        role_counts = {}
        for assignment in self.active_assignments.values():
            if assignment.status == AssignmentStatus.ACTIVE:
                role_id = assignment.role_id
                role_counts[role_id] = role_counts.get(role_id, 0) + 1
        
        analysis["role_distribution"] = role_counts
        
        # Identify over/under allocated roles
        all_roles = self.role_library.list_roles()
        for role_template in all_roles:
            count = role_counts.get(role_template.role_id, 0)
            
            # Simple heuristics for allocation assessment
            if count == 0:
                analysis["under_allocated_roles"].append(role_template.role_id)
            elif count > 3:  # More than 3 agents with same role might be over-allocation
                analysis["over_allocated_roles"].append(role_template.role_id)
        
        return analysis

    def _get_primary_role_assignment(self, agent_id: str) -> Optional[RoleAssignment]:
        """Get the primary role assignment for an agent"""
        assignment_ids = self.agent_roles.get(agent_id, [])
        for assignment_id in assignment_ids:
            assignment = self.active_assignments.get(assignment_id)
            if (assignment and 
                assignment.assignment_type == AssignmentType.PRIMARY and
                assignment.status == AssignmentStatus.ACTIVE):
                return assignment
        return None

    async def _apply_behavioral_patterns(self, assignment: RoleAssignment) -> None:
        """Apply behavioral patterns from role template to assignment"""
        # This would integrate with the behavioral pattern engine
        # For now, just log the patterns being applied
        patterns = assignment.role_template.behavior_patterns
        logger.info(f"Applied {len(patterns)} behavioral patterns to assignment {assignment.assignment_id}")

    async def _calculate_final_metrics(self, assignment: RoleAssignment) -> None:
        """Calculate final performance metrics for completed assignment"""
        if not assignment.started_at or not assignment.ended_at:
            return
        
        duration = (assignment.ended_at - assignment.started_at).total_seconds()
        assignment.metadata["total_duration"] = duration
        
        # Calculate average performance
        if assignment.performance_metrics:
            avg_performance = sum(
                metric.current_value for metric in assignment.performance_metrics.values()
            ) / len(assignment.performance_metrics)
            assignment.metadata["average_performance"] = avg_performance

    async def cleanup_completed_assignments(self, max_age_hours: int = 168) -> int:
        """Clean up old completed assignments (default: 1 week)"""
        cutoff_time = datetime.now(timezone.utc).timestamp() - (max_age_hours * 3600)
        removed_count = 0
        
        assignments_to_remove = []
        for assignment_id, assignment in self.active_assignments.items():
            if (assignment.status == AssignmentStatus.COMPLETED and
                assignment.ended_at and 
                assignment.ended_at.timestamp() < cutoff_time):
                assignments_to_remove.append(assignment_id)
        
        for assignment_id in assignments_to_remove:
            assignment = self.active_assignments[assignment_id]
            
            # Remove from indices
            if assignment.agent_id in self.agent_roles:
                if assignment_id in self.agent_roles[assignment.agent_id]:
                    self.agent_roles[assignment.agent_id].remove(assignment_id)
                if not self.agent_roles[assignment.agent_id]:
                    del self.agent_roles[assignment.agent_id]
            
            if assignment.role_id in self.role_assignments:
                if assignment_id in self.role_assignments[assignment.role_id]:
                    self.role_assignments[assignment.role_id].remove(assignment_id)
                if not self.role_assignments[assignment.role_id]:
                    del self.role_assignments[assignment.role_id]
            
            # Remove assignment
            del self.active_assignments[assignment_id]
            removed_count += 1
        
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} old role assignments")
        
        return removed_count
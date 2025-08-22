"""
Behavioral Patterns Engine - Runtime behavioral pattern application for ATLAS Phase 4

Applies behavioral patterns from role templates to agent interactions.
Manages pattern triggers, actions, and context-aware responses.
"""

import asyncio
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field

from agents.roles.role_template import BehaviorPattern

logger = logging.getLogger(__name__)


class PatternExecutionStatus(str, Enum):
    """Status of pattern execution"""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PatternContext:
    """Context for pattern execution"""
    agent_id: str
    role_id: str
    trigger_event: str
    event_data: Dict[str, Any] = field(default_factory=dict)
    session_context: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class PatternExecution:
    """Tracks execution of a behavioral pattern"""
    execution_id: str
    pattern_id: str
    agent_id: str
    context: PatternContext
    status: PatternExecutionStatus = PatternExecutionStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    actions_taken: List[str] = field(default_factory=list)
    results: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None


class BehavioralPatternEngine:
    """
    Engine for applying behavioral patterns from role templates
    
    Manages pattern triggers, execution, and context-aware behavioral responses.
    Integrates with role assignments to provide consistent agent behavior.
    """
    
    def __init__(self):
        """Initialize the behavioral pattern engine"""
        self.active_patterns: Dict[str, List[BehaviorPattern]] = {}  # agent_id -> patterns
        self.pattern_executions: Dict[str, PatternExecution] = {}  # execution_id -> execution
        self.trigger_handlers: Dict[str, List[Callable]] = {}  # trigger -> handlers
        self.execution_counter = 0
        self._context_memory: Dict[str, Dict[str, Any]] = {}  # agent_id -> context
        
        # Register default trigger handlers
        self._register_default_handlers()
        
        logger.info("BehavioralPatternEngine initialized")

    def register_agent_patterns(
        self,
        agent_id: str,
        patterns: List[BehaviorPattern]
    ) -> None:
        """Register behavioral patterns for an agent"""
        self.active_patterns[agent_id] = patterns
        
        # Initialize context memory for agent
        if agent_id not in self._context_memory:
            self._context_memory[agent_id] = {}
        
        logger.info(f"Registered {len(patterns)} patterns for agent {agent_id}")

    def update_agent_patterns(
        self,
        agent_id: str,
        patterns: List[BehaviorPattern]
    ) -> None:
        """Update patterns for an agent (replaces existing patterns)"""
        self.register_agent_patterns(agent_id, patterns)

    def add_pattern_to_agent(
        self,
        agent_id: str,
        pattern: BehaviorPattern
    ) -> None:
        """Add a single pattern to an agent"""
        if agent_id not in self.active_patterns:
            self.active_patterns[agent_id] = []
        
        # Remove existing pattern with same ID
        self.active_patterns[agent_id] = [
            p for p in self.active_patterns[agent_id] 
            if p.pattern_id != pattern.pattern_id
        ]
        
        # Add new pattern and sort by priority
        self.active_patterns[agent_id].append(pattern)
        self.active_patterns[agent_id].sort(key=lambda p: p.priority, reverse=True)

    def remove_pattern_from_agent(
        self,
        agent_id: str,
        pattern_id: str
    ) -> bool:
        """Remove a pattern from an agent"""
        if agent_id not in self.active_patterns:
            return False
        
        original_count = len(self.active_patterns[agent_id])
        self.active_patterns[agent_id] = [
            p for p in self.active_patterns[agent_id]
            if p.pattern_id != pattern_id
        ]
        
        return len(self.active_patterns[agent_id]) < original_count

    async def trigger_patterns(
        self,
        agent_id: str,
        trigger_event: str,
        event_data: Optional[Dict[str, Any]] = None,
        session_context: Optional[Dict[str, Any]] = None
    ) -> List[PatternExecution]:
        """Trigger behavioral patterns for an agent based on an event"""
        if agent_id not in self.active_patterns:
            return []
        
        triggered_executions = []
        event_data = event_data or {}
        session_context = session_context or {}
        
        # Find matching patterns
        matching_patterns = []
        for pattern in self.active_patterns[agent_id]:
            if self._pattern_matches_trigger(pattern, trigger_event, event_data):
                matching_patterns.append(pattern)
        
        # Execute patterns in priority order
        for pattern in matching_patterns:
            execution = await self._execute_pattern(
                agent_id=agent_id,
                pattern=pattern,
                trigger_event=trigger_event,
                event_data=event_data,
                session_context=session_context
            )
            if execution:
                triggered_executions.append(execution)
        
        return triggered_executions

    async def get_behavioral_response(
        self,
        agent_id: str,
        context: str,
        input_data: Dict[str, Any]
    ) -> Optional[str]:
        """Get a behavioral response based on agent's role patterns"""
        if agent_id not in self.active_patterns:
            return None
        
        # Look for patterns that handle this context
        relevant_patterns = []
        for pattern in self.active_patterns[agent_id]:
            if context in pattern.triggers or any(context in trigger for trigger in pattern.triggers):
                relevant_patterns.append(pattern)
        
        if not relevant_patterns:
            return None
        
        # Use highest priority pattern
        pattern = relevant_patterns[0]
        
        # Generate response based on pattern actions and communication rules
        response = await self._generate_response_from_pattern(
            agent_id=agent_id,
            pattern=pattern,
            context=context,
            input_data=input_data
        )
        
        return response

    def get_pattern_executions(
        self,
        agent_id: Optional[str] = None,
        status: Optional[PatternExecutionStatus] = None
    ) -> List[PatternExecution]:
        """Get pattern executions, optionally filtered by agent or status"""
        executions = list(self.pattern_executions.values())
        
        if agent_id:
            executions = [e for e in executions if e.agent_id == agent_id]
        
        if status:
            executions = [e for e in executions if e.status == status]
        
        return executions

    def get_agent_context(self, agent_id: str) -> Dict[str, Any]:
        """Get the current context memory for an agent"""
        return self._context_memory.get(agent_id, {}).copy()

    def update_agent_context(
        self,
        agent_id: str,
        context_updates: Dict[str, Any]
    ) -> None:
        """Update context memory for an agent"""
        if agent_id not in self._context_memory:
            self._context_memory[agent_id] = {}
        
        self._context_memory[agent_id].update(context_updates)

    def register_trigger_handler(
        self,
        trigger: str,
        handler: Callable[[PatternContext], Any]
    ) -> None:
        """Register a custom trigger handler"""
        if trigger not in self.trigger_handlers:
            self.trigger_handlers[trigger] = []
        
        self.trigger_handlers[trigger].append(handler)

    def get_behavioral_statistics(self) -> Dict[str, Any]:
        """Get statistics about behavioral pattern usage"""
        total_executions = len(self.pattern_executions)
        
        # Count by status
        status_counts = {}
        for execution in self.pattern_executions.values():
            status = execution.status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Count by agent
        agent_counts = {}
        for execution in self.pattern_executions.values():
            agent_id = execution.agent_id
            agent_counts[agent_id] = agent_counts.get(agent_id, 0) + 1
        
        # Count by pattern
        pattern_counts = {}
        for execution in self.pattern_executions.values():
            pattern_id = execution.pattern_id
            pattern_counts[pattern_id] = pattern_counts.get(pattern_id, 0) + 1
        
        return {
            "total_executions": total_executions,
            "status_distribution": status_counts,
            "agent_execution_counts": agent_counts,
            "pattern_usage_counts": pattern_counts,
            "active_agents": len(self.active_patterns)
        }

    def _pattern_matches_trigger(
        self,
        pattern: BehaviorPattern,
        trigger_event: str,
        event_data: Dict[str, Any]
    ) -> bool:
        """Check if a pattern matches a trigger event"""
        # Check direct trigger match
        if trigger_event in pattern.triggers:
            return True
        
        # Check pattern-based matches
        for trigger in pattern.triggers:
            if "*" in trigger:
                # Simple wildcard matching
                trigger_pattern = trigger.replace("*", ".*")
                import re
                if re.match(trigger_pattern, trigger_event):
                    return True
        
        # Check conditions if present
        if pattern.conditions:
            return self._evaluate_pattern_conditions(pattern.conditions, event_data)
        
        return False

    def _evaluate_pattern_conditions(
        self,
        conditions: Dict[str, Any],
        event_data: Dict[str, Any]
    ) -> bool:
        """Evaluate pattern conditions against event data"""
        for key, expected_value in conditions.items():
            if key not in event_data:
                return False
            
            actual_value = event_data[key]
            
            # Simple equality check for now
            # Could be extended to support operators like >, <, contains, etc.
            if actual_value != expected_value:
                return False
        
        return True

    async def _execute_pattern(
        self,
        agent_id: str,
        pattern: BehaviorPattern,
        trigger_event: str,
        event_data: Dict[str, Any],
        session_context: Dict[str, Any]
    ) -> Optional[PatternExecution]:
        """Execute a behavioral pattern"""
        self.execution_counter += 1
        execution_id = f"exec_{agent_id}_{pattern.pattern_id}_{self.execution_counter}"
        
        context = PatternContext(
            agent_id=agent_id,
            role_id="unknown",  # Could be passed in
            trigger_event=trigger_event,
            event_data=event_data,
            session_context=session_context
        )
        
        execution = PatternExecution(
            execution_id=execution_id,
            pattern_id=pattern.pattern_id,
            agent_id=agent_id,
            context=context
        )
        
        self.pattern_executions[execution_id] = execution
        
        try:
            execution.status = PatternExecutionStatus.EXECUTING
            execution.started_at = datetime.now(timezone.utc)
            
            # Execute pattern actions
            for action in pattern.actions:
                result = await self._execute_pattern_action(
                    action=action,
                    pattern=pattern,
                    context=context
                )
                execution.actions_taken.append(action)
                execution.results[action] = result
            
            execution.status = PatternExecutionStatus.COMPLETED
            execution.completed_at = datetime.now(timezone.utc)
            
            # Update agent context based on execution
            self._update_context_from_execution(execution)
            
        except Exception as e:
            execution.status = PatternExecutionStatus.FAILED
            execution.error_message = str(e)
            logger.error(f"Pattern execution failed: {e}")
        
        return execution

    async def _execute_pattern_action(
        self,
        action: str,
        pattern: BehaviorPattern,
        context: PatternContext
    ) -> Any:
        """Execute a single pattern action"""
        # This would integrate with actual agent capabilities
        # For now, just simulate action execution
        
        action_results = {
            "analyze_requirements": f"Analyzed requirements for {context.trigger_event}",
            "assign_tasks": f"Assigned tasks based on {context.trigger_event}",
            "monitor_progress": f"Started monitoring progress for {context.trigger_event}",
            "mediate_discussion": f"Initiated mediation for {context.trigger_event}",
            "find_compromise": f"Searching for compromise solutions",
            "escalate_if_needed": f"Evaluating need for escalation",
            "analyze_threat": f"Analyzed security threat: {context.event_data.get('threat_type', 'unknown')}",
            "assess_risk": f"Risk assessment completed",
            "recommend_action": f"Generated security recommendations"
        }
        
        return action_results.get(action, f"Executed action: {action}")

    async def _generate_response_from_pattern(
        self,
        agent_id: str,
        pattern: BehaviorPattern,
        context: str,
        input_data: Dict[str, Any]
    ) -> str:
        """Generate a response based on pattern communication rules"""
        
        # Check for specific communication rules
        if context in pattern.communication_rules:
            rule = pattern.communication_rules[context]
            # Simple template substitution
            response = rule.format(**input_data)
            return response
        
        # Generate default response based on pattern type
        if "coordinate" in pattern.name.lower():
            return f"I'll coordinate this {context} based on our team's needs."
        elif "analyze" in pattern.name.lower():
            return f"Let me analyze the {context} and provide insights."
        elif "security" in pattern.name.lower():
            return f"From a security perspective, I need to evaluate {context}."
        elif "creative" in pattern.name.lower():
            return f"Here's a creative approach to {context}..."
        
        return f"I'll handle this {context} according to my role guidelines."

    def _update_context_from_execution(self, execution: PatternExecution) -> None:
        """Update agent context based on pattern execution"""
        agent_id = execution.agent_id
        
        if agent_id not in self._context_memory:
            self._context_memory[agent_id] = {}
        
        # Store execution results in context
        self._context_memory[agent_id][f"last_{execution.pattern_id}"] = {
            "execution_id": execution.execution_id,
            "completed_at": execution.completed_at,
            "status": execution.status,
            "actions_taken": execution.actions_taken
        }
        
        # Update behavioral state
        if "behavioral_state" not in self._context_memory[agent_id]:
            self._context_memory[agent_id]["behavioral_state"] = {}
        
        state = self._context_memory[agent_id]["behavioral_state"]
        state["last_pattern"] = execution.pattern_id
        state["last_execution"] = execution.execution_id
        state["execution_count"] = state.get("execution_count", 0) + 1

    def _register_default_handlers(self) -> None:
        """Register default trigger handlers"""
        
        def handle_task_assignment(context: PatternContext):
            logger.info(f"Task assignment triggered for agent {context.agent_id}")
        
        def handle_conflict_detection(context: PatternContext):
            logger.info(f"Conflict detected for agent {context.agent_id}")
        
        def handle_security_alert(context: PatternContext):
            logger.info(f"Security alert triggered for agent {context.agent_id}")
        
        self.register_trigger_handler("task_assignment_needed", handle_task_assignment)
        self.register_trigger_handler("conflict_detected", handle_conflict_detection)
        self.register_trigger_handler("security_alert", handle_security_alert)

    async def cleanup_old_executions(self, max_age_hours: int = 24) -> int:
        """Clean up old pattern executions"""
        cutoff_time = datetime.now(timezone.utc).timestamp() - (max_age_hours * 3600)
        removed_count = 0
        
        executions_to_remove = []
        for execution_id, execution in self.pattern_executions.items():
            if (execution.completed_at and 
                execution.completed_at.timestamp() < cutoff_time):
                executions_to_remove.append(execution_id)
        
        for execution_id in executions_to_remove:
            del self.pattern_executions[execution_id]
            removed_count += 1
        
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} old pattern executions")
        
        return removed_count
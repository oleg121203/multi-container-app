"""
ATLAS Phase 4 - Orchestration Patterns (TEAM-05)

Advanced coordination patterns for complex multi-agent scenarios.
Provides workflow patterns, event-driven coordination, and parallel processing.
"""

from .orchestration_engine import OrchestrationEngine, OrchestrationStatus
from .workflow_patterns import (
    WorkflowPattern, WorkflowTask, WorkflowExecution, TaskStatus, PatternType,
    PipelinePattern, MapReducePattern, ParallelPattern,
    ConditionalPattern, LoopPattern
)
from .event_coordinator import EventCoordinator, EventType, CoordinationEvent, EventPriority
from .performance_monitor import PerformanceMonitor, PerformanceMetric, MetricType, AlertLevel

__all__ = [
    "OrchestrationEngine",
    "OrchestrationStatus",
    "WorkflowPattern",
    "WorkflowTask",
    "WorkflowExecution", 
    "TaskStatus",
    "PatternType",
    "PipelinePattern", 
    "MapReducePattern",
    "ParallelPattern",
    "ConditionalPattern",
    "LoopPattern",
    "EventCoordinator",
    "EventType",
    "CoordinationEvent",
    "EventPriority",
    "PerformanceMonitor",
    "PerformanceMetric",
    "MetricType",
    "AlertLevel"
]
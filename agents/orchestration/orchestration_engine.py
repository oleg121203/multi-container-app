"""
Orchestration Engine - Core orchestration system for ATLAS Phase 4

Coordinates complex multi-agent workflows using predefined patterns.
Manages workflow execution, monitoring, and error handling.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field

from agents.registry.agent_registry import AgentRegistry
from agents.orchestration.workflow_patterns import (
    WorkflowPattern, WorkflowExecution, WorkflowTask, TaskStatus,
    PipelinePattern, MapReducePattern, ParallelPattern, ConditionalPattern, LoopPattern,
    PatternType
)

logger = logging.getLogger(__name__)


class OrchestrationStatus(str, Enum):
    """Status of orchestration operations"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


@dataclass
class OrchestrationRequest:
    """Request for orchestrating a workflow"""
    request_id: str
    pattern_type: PatternType
    tasks: List[WorkflowTask]
    context: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    timeout_seconds: Optional[int] = None
    retry_count: int = 0
    callback: Optional[Callable] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class OrchestrationResult:
    """Result of an orchestration operation"""
    request_id: str
    execution: WorkflowExecution
    status: OrchestrationStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)


class OrchestrationEngine:
    """
    Core orchestration engine for multi-agent workflows
    
    Manages workflow patterns, executes complex coordination scenarios,
    and provides monitoring and error handling capabilities.
    """
    
    def __init__(self, agent_registry: AgentRegistry):
        """Initialize the orchestration engine"""
        self.agent_registry = agent_registry
        self.patterns: Dict[str, WorkflowPattern] = {}
        self.active_orchestrations: Dict[str, OrchestrationResult] = {}
        self.orchestration_queue: List[OrchestrationRequest] = []
        self.running_orchestrations: Dict[str, asyncio.Task] = {}
        
        # Statistics
        self._orchestration_stats = {
            "total_requests": 0,
            "successful_orchestrations": 0,
            "failed_orchestrations": 0,
            "cancelled_orchestrations": 0,
            "average_execution_time": 0.0
        }
        
        # Initialize standard patterns
        self._initialize_standard_patterns()
        
        logger.info("OrchestrationEngine initialized")

    def _initialize_standard_patterns(self) -> None:
        """Initialize standard workflow patterns"""
        patterns = [
            PipelinePattern("standard_pipeline", "Standard Pipeline", "Sequential task execution"),
            MapReducePattern("standard_mapreduce", "Standard MapReduce", "Parallel map with reduce"),
            ParallelPattern("standard_parallel", "Standard Parallel", "Parallel execution"),
            ConditionalPattern("standard_conditional", "Standard Conditional", "Conditional execution"),
            LoopPattern("standard_loop", "Standard Loop", "Iterative execution", max_iterations=5)
        ]
        
        for pattern in patterns:
            self.patterns[pattern.pattern_id] = pattern

    def register_pattern(self, pattern: WorkflowPattern) -> bool:
        """Register a custom workflow pattern"""
        if pattern.pattern_id in self.patterns:
            logger.warning(f"Pattern {pattern.pattern_id} already exists")
            return False
        
        self.patterns[pattern.pattern_id] = pattern
        logger.info(f"Registered pattern: {pattern.pattern_id}")
        return True

    def get_pattern(self, pattern_id: str) -> Optional[WorkflowPattern]:
        """Get a workflow pattern by ID"""
        return self.patterns.get(pattern_id)

    def list_patterns(self, pattern_type: Optional[PatternType] = None) -> List[WorkflowPattern]:
        """List available workflow patterns"""
        if pattern_type:
            return [p for p in self.patterns.values() if p.pattern_type == pattern_type]
        return list(self.patterns.values())

    async def orchestrate(
        self,
        pattern_id: str,
        tasks: List[WorkflowTask],
        context: Optional[Dict[str, Any]] = None,
        priority: int = 0,
        timeout_seconds: Optional[int] = None,
        callback: Optional[Callable] = None
    ) -> str:
        """Submit a workflow for orchestration"""
        
        # Validate pattern exists
        pattern = self.patterns.get(pattern_id)
        if not pattern:
            raise ValueError(f"Pattern {pattern_id} not found")
        
        # Validate tasks
        validation_issues = pattern.validate_tasks(tasks)
        if validation_issues:
            raise ValueError(f"Task validation failed: {validation_issues}")
        
        # Validate agents exist
        for task in tasks:
            agent = await self.agent_registry.get_agent(task.agent_id)
            if not agent:
                raise ValueError(f"Agent {task.agent_id} not found")
        
        # Create orchestration request
        request_id = f"orch_{uuid.uuid4().hex[:8]}"
        request = OrchestrationRequest(
            request_id=request_id,
            pattern_type=pattern.pattern_type,
            tasks=tasks,
            context=context or {},
            priority=priority,
            timeout_seconds=timeout_seconds,
            callback=callback
        )
        
        # Queue or execute immediately
        self.orchestration_queue.append(request)
        self._orchestration_stats["total_requests"] += 1
        
        # Start execution
        await self._process_orchestration_queue()
        
        return request_id

    async def orchestrate_pipeline(
        self,
        tasks: List[WorkflowTask],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Convenience method for pipeline orchestration"""
        return await self.orchestrate("standard_pipeline", tasks, context)

    async def orchestrate_parallel(
        self,
        tasks: List[WorkflowTask],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Convenience method for parallel orchestration"""
        return await self.orchestrate("standard_parallel", tasks, context)

    async def orchestrate_mapreduce(
        self,
        map_tasks: List[WorkflowTask],
        reduce_tasks: List[WorkflowTask],
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Convenience method for map-reduce orchestration"""
        all_tasks = map_tasks + reduce_tasks
        return await self.orchestrate("standard_mapreduce", all_tasks, context)

    async def get_orchestration_status(self, request_id: str) -> Optional[OrchestrationStatus]:
        """Get the status of an orchestration request"""
        if request_id in self.active_orchestrations:
            return self.active_orchestrations[request_id].status
        
        # Check if still in queue
        for request in self.orchestration_queue:
            if request.request_id == request_id:
                return OrchestrationStatus.PENDING
        
        return None

    async def get_orchestration_result(self, request_id: str) -> Optional[OrchestrationResult]:
        """Get the result of an orchestration request"""
        return self.active_orchestrations.get(request_id)

    async def cancel_orchestration(self, request_id: str) -> bool:
        """Cancel an orchestration request"""
        # Remove from queue if pending
        self.orchestration_queue = [
            req for req in self.orchestration_queue 
            if req.request_id != request_id
        ]
        
        # Cancel running orchestration
        if request_id in self.running_orchestrations:
            task = self.running_orchestrations[request_id]
            task.cancel()
            
            # Update result
            if request_id in self.active_orchestrations:
                result = self.active_orchestrations[request_id]
                result.status = OrchestrationStatus.CANCELLED
                result.completed_at = datetime.now(timezone.utc)
            
            self._orchestration_stats["cancelled_orchestrations"] += 1
            return True
        
        return False

    async def pause_orchestration(self, request_id: str) -> bool:
        """Pause an orchestration request"""
        if request_id in self.active_orchestrations:
            result = self.active_orchestrations[request_id]
            if result.status == OrchestrationStatus.RUNNING:
                result.status = OrchestrationStatus.PAUSED
                return True
        return False

    async def resume_orchestration(self, request_id: str) -> bool:
        """Resume a paused orchestration request"""
        if request_id in self.active_orchestrations:
            result = self.active_orchestrations[request_id]
            if result.status == OrchestrationStatus.PAUSED:
                result.status = OrchestrationStatus.RUNNING
                return True
        return False

    def get_orchestration_statistics(self) -> Dict[str, Any]:
        """Get orchestration statistics"""
        stats = self._orchestration_stats.copy()
        stats.update({
            "active_orchestrations": len(self.running_orchestrations),
            "queued_requests": len(self.orchestration_queue),
            "registered_patterns": len(self.patterns),
            "pattern_types": list(set(p.pattern_type for p in self.patterns.values()))
        })
        return stats

    def get_active_orchestrations(self) -> List[OrchestrationResult]:
        """Get all active orchestrations"""
        return [
            result for result in self.active_orchestrations.values()
            if result.status in [OrchestrationStatus.RUNNING, OrchestrationStatus.PAUSED]
        ]

    async def _process_orchestration_queue(self) -> None:
        """Process pending orchestration requests"""
        if not self.orchestration_queue:
            return
        
        # Sort by priority (higher priority first)
        self.orchestration_queue.sort(key=lambda x: x.priority, reverse=True)
        
        while self.orchestration_queue:
            request = self.orchestration_queue.pop(0)
            
            # Start orchestration
            task = asyncio.create_task(self._execute_orchestration(request))
            self.running_orchestrations[request.request_id] = task

    async def _execute_orchestration(self, request: OrchestrationRequest) -> None:
        """Execute a single orchestration request"""
        pattern = self.patterns.get(request.pattern_type) or self._get_pattern_by_type(request.pattern_type)
        if not pattern:
            logger.error(f"No pattern found for type {request.pattern_type}")
            return
        
        # Create result object
        result = OrchestrationResult(
            request_id=request.request_id,
            execution=pattern.create_execution(request.tasks),
            status=OrchestrationStatus.RUNNING,
            started_at=datetime.now(timezone.utc)
        )
        
        self.active_orchestrations[request.request_id] = result
        
        try:
            # Execute with timeout if specified
            if request.timeout_seconds:
                execution = await asyncio.wait_for(
                    pattern.execute(request.tasks, request.context),
                    timeout=request.timeout_seconds
                )
            else:
                execution = await pattern.execute(request.tasks, request.context)
            
            # Update result
            result.execution = execution
            result.status = OrchestrationStatus.COMPLETED if execution.status == TaskStatus.COMPLETED else OrchestrationStatus.FAILED
            result.completed_at = datetime.now(timezone.utc)
            
            # Calculate metrics
            if result.started_at and result.completed_at:
                duration = (result.completed_at - result.started_at).total_seconds()
                result.metrics["execution_time"] = duration
                self._update_average_execution_time(duration)
            
            # Update statistics
            if result.status == OrchestrationStatus.COMPLETED:
                self._orchestration_stats["successful_orchestrations"] += 1
            else:
                self._orchestration_stats["failed_orchestrations"] += 1
            
            # Call callback if provided
            if request.callback:
                try:
                    await request.callback(result)
                except Exception as e:
                    logger.error(f"Callback error for {request.request_id}: {e}")
            
        except asyncio.TimeoutError:
            result.status = OrchestrationStatus.FAILED
            result.error = "Execution timeout"
            result.completed_at = datetime.now(timezone.utc)
            self._orchestration_stats["failed_orchestrations"] += 1
            
        except asyncio.CancelledError:
            result.status = OrchestrationStatus.CANCELLED
            result.completed_at = datetime.now(timezone.utc)
            # Cancelled count already updated in cancel method
            
        except Exception as e:
            result.status = OrchestrationStatus.FAILED
            result.error = str(e)
            result.completed_at = datetime.now(timezone.utc)
            self._orchestration_stats["failed_orchestrations"] += 1
            logger.error(f"Orchestration {request.request_id} failed: {e}")
            
        finally:
            # Clean up
            if request.request_id in self.running_orchestrations:
                del self.running_orchestrations[request.request_id]

    def _get_pattern_by_type(self, pattern_type: PatternType) -> Optional[WorkflowPattern]:
        """Get a pattern by type (first match)"""
        for pattern in self.patterns.values():
            if pattern.pattern_type == pattern_type:
                return pattern
        return None

    def _update_average_execution_time(self, duration: float) -> None:
        """Update average execution time statistics"""
        completed = self._orchestration_stats["successful_orchestrations"]
        if completed > 1:
            current_avg = self._orchestration_stats["average_execution_time"]
            new_avg = ((current_avg * (completed - 1)) + duration) / completed
            self._orchestration_stats["average_execution_time"] = new_avg
        else:
            self._orchestration_stats["average_execution_time"] = duration

    async def suggest_optimal_pattern(
        self,
        tasks: List[WorkflowTask],
        context: Dict[str, Any]
    ) -> Optional[str]:
        """Suggest optimal workflow pattern for given tasks"""
        if not tasks:
            return None
        
        # Simple heuristics for pattern suggestion
        
        # Check for dependencies - if present, suggest pipeline
        has_dependencies = any(task.dependencies for task in tasks)
        if has_dependencies:
            return "standard_pipeline"
        
        # Check for map-reduce tasks
        map_tasks = [t for t in tasks if t.task_type == "map"]
        reduce_tasks = [t for t in tasks if t.task_type == "reduce"]
        if map_tasks and reduce_tasks:
            return "standard_mapreduce"
        
        # Check for conditions
        has_conditions = any(task.metadata.get("condition") for task in tasks)
        if has_conditions:
            return "standard_conditional"
        
        # Check for loop indicators
        if context.get("loop_condition") or any("loop" in task.task_type for task in tasks):
            return "standard_loop"
        
        # Default to parallel if no special requirements
        if len(tasks) > 1:
            return "standard_parallel"
        
        return "standard_pipeline"  # Single task

    async def create_workflow_from_template(
        self,
        template_name: str,
        agent_assignments: Dict[str, str],  # role -> agent_id
        context: Dict[str, Any]
    ) -> List[WorkflowTask]:
        """Create workflow tasks from a template"""
        templates = {
            "data_processing": [
                {"task_type": "extract", "role": "data_extractor"},
                {"task_type": "transform", "role": "data_transformer"},
                {"task_type": "load", "role": "data_loader"}
            ],
            "security_audit": [
                {"task_type": "scan", "role": "security_scanner"},
                {"task_type": "analyze", "role": "security_analyzer"},
                {"task_type": "report", "role": "security_reporter"}
            ],
            "ui_development": [
                {"task_type": "design", "role": "ui_designer"},
                {"task_type": "implement", "role": "ui_developer"},
                {"task_type": "test", "role": "ui_tester"}
            ]
        }
        
        template = templates.get(template_name)
        if not template:
            raise ValueError(f"Unknown template: {template_name}")
        
        tasks = []
        for i, task_def in enumerate(template):
            agent_id = agent_assignments.get(task_def["role"])
            if not agent_id:
                # Try to find a suitable agent
                available_agents = await self.agent_registry.list_agents()
                # Simple assignment - in real implementation would use role matching
                agent_id = available_agents[i % len(available_agents)].agent_id if available_agents else f"agent_{i}"
            
            task = WorkflowTask(
                task_id=f"{template_name}_{task_def['task_type']}_{i}",
                agent_id=agent_id,
                task_type=task_def["task_type"],
                task_data=context.copy()
            )
            
            # Add dependencies for pipeline
            if i > 0:
                task.dependencies = [tasks[i-1].task_id]
            
            tasks.append(task)
        
        return tasks

    async def cleanup_completed_orchestrations(self, max_age_hours: int = 24) -> int:
        """Clean up old completed orchestrations"""
        cutoff_time = datetime.now(timezone.utc).timestamp() - (max_age_hours * 3600)
        removed_count = 0
        
        orchestrations_to_remove = []
        for request_id, result in self.active_orchestrations.items():
            if (result.status in [OrchestrationStatus.COMPLETED, OrchestrationStatus.FAILED, OrchestrationStatus.CANCELLED] and
                result.completed_at and result.completed_at.timestamp() < cutoff_time):
                orchestrations_to_remove.append(request_id)
        
        for request_id in orchestrations_to_remove:
            del self.active_orchestrations[request_id]
            removed_count += 1
        
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} old orchestration results")
        
        return removed_count
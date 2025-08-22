"""
Workflow Patterns - Predefined orchestration patterns for ATLAS Phase 4

Provides standard workflow patterns for multi-agent coordination.
Includes pipeline, map-reduce, parallel, conditional, and loop patterns.
"""

import asyncio
import logging
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class PatternType(str, Enum):
    """Types of workflow patterns"""
    PIPELINE = "pipeline"
    MAP_REDUCE = "map_reduce"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    LOOP = "loop"
    SEQUENTIAL = "sequential"
    SCATTER_GATHER = "scatter_gather"


class TaskStatus(str, Enum):
    """Status of individual tasks in workflow"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


@dataclass
class WorkflowTask:
    """Represents a task in a workflow"""
    task_id: str
    agent_id: str
    task_type: str
    task_data: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)  # task_ids this depends on
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowExecution:
    """Tracks execution of a workflow pattern"""
    execution_id: str
    pattern_id: str
    pattern_type: PatternType
    status: TaskStatus = TaskStatus.PENDING
    tasks: List[WorkflowTask] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class WorkflowPattern(ABC):
    """
    Abstract base class for workflow patterns
    
    Defines the interface for all workflow orchestration patterns.
    Each pattern implements specific coordination logic.
    """
    
    def __init__(
        self,
        pattern_id: str,
        name: str,
        description: str,
        pattern_type: PatternType
    ):
        self.pattern_id = pattern_id
        self.name = name
        self.description = description
        self.pattern_type = pattern_type
        self.created_at = datetime.now(timezone.utc)
        self.metadata: Dict[str, Any] = {}
    
    @abstractmethod
    async def execute(
        self,
        tasks: List[WorkflowTask],
        context: Dict[str, Any]
    ) -> WorkflowExecution:
        """Execute the workflow pattern"""
        pass
    
    @abstractmethod
    def validate_tasks(self, tasks: List[WorkflowTask]) -> List[str]:
        """Validate that tasks are compatible with this pattern"""
        pass
    
    def create_execution(
        self,
        tasks: List[WorkflowTask],
        execution_id: Optional[str] = None
    ) -> WorkflowExecution:
        """Create a new workflow execution"""
        if not execution_id:
            execution_id = f"exec_{self.pattern_id}_{uuid.uuid4().hex[:8]}"
        
        return WorkflowExecution(
            execution_id=execution_id,
            pattern_id=self.pattern_id,
            pattern_type=self.pattern_type,
            tasks=tasks.copy()
        )


class PipelinePattern(WorkflowPattern):
    """
    Pipeline pattern - tasks execute in sequence
    
    Each task's output becomes the input for the next task.
    Suitable for linear data processing workflows.
    """
    
    def __init__(self, pattern_id: str, name: str = "Pipeline", description: str = "Sequential task execution"):
        super().__init__(pattern_id, name, description, PatternType.PIPELINE)
    
    async def execute(
        self,
        tasks: List[WorkflowTask],
        context: Dict[str, Any]
    ) -> WorkflowExecution:
        """Execute tasks in pipeline sequence"""
        execution = self.create_execution(tasks)
        execution.status = TaskStatus.RUNNING
        execution.started_at = datetime.now(timezone.utc)
        
        try:
            current_data = context.get("input_data", {})
            
            for task in execution.tasks:
                task.status = TaskStatus.RUNNING
                task.started_at = datetime.now(timezone.utc)
                task.task_data.update(current_data)
                
                try:
                    # Simulate task execution
                    result = await self._execute_task(task, current_data)
                    task.result = result
                    task.status = TaskStatus.COMPLETED
                    task.completed_at = datetime.now(timezone.utc)
                    
                    # Pass result to next task
                    current_data = result if isinstance(result, dict) else {"result": result}
                    
                except Exception as e:
                    task.error = str(e)
                    task.status = TaskStatus.FAILED
                    task.completed_at = datetime.now(timezone.utc)
                    execution.status = TaskStatus.FAILED
                    execution.error = f"Task {task.task_id} failed: {e}"
                    break
            
            if execution.status != TaskStatus.FAILED:
                execution.status = TaskStatus.COMPLETED
                execution.result = current_data
            
        except Exception as e:
            execution.status = TaskStatus.FAILED
            execution.error = str(e)
        finally:
            execution.completed_at = datetime.now(timezone.utc)
        
        return execution
    
    def validate_tasks(self, tasks: List[WorkflowTask]) -> List[str]:
        """Validate pipeline tasks"""
        issues = []
        
        if len(tasks) < 2:
            issues.append("Pipeline requires at least 2 tasks")
        
        # Check for circular dependencies
        task_ids = {task.task_id for task in tasks}
        for task in tasks:
            for dep in task.dependencies:
                if dep not in task_ids:
                    issues.append(f"Task {task.task_id} depends on non-existent task {dep}")
        
        return issues
    
    async def _execute_task(self, task: WorkflowTask, input_data: Dict[str, Any]) -> Any:
        """Simulate task execution - in real implementation would call agent"""
        await asyncio.sleep(0.1)  # Simulate processing time
        
        # Simple task simulation based on task type
        if task.task_type == "transform":
            return {"transformed": input_data, "by": task.agent_id}
        elif task.task_type == "filter":
            return {"filtered": input_data, "by": task.agent_id}
        elif task.task_type == "aggregate":
            return {"aggregated": input_data, "by": task.agent_id}
        else:
            return {"processed": input_data, "by": task.agent_id}


class MapReducePattern(WorkflowPattern):
    """
    Map-Reduce pattern - parallel map phase followed by reduce phase
    
    Splits data across multiple agents for parallel processing,
    then aggregates results.
    """
    
    def __init__(self, pattern_id: str, name: str = "MapReduce", description: str = "Parallel map with reduce aggregation"):
        super().__init__(pattern_id, name, description, PatternType.MAP_REDUCE)
    
    async def execute(
        self,
        tasks: List[WorkflowTask],
        context: Dict[str, Any]
    ) -> WorkflowExecution:
        """Execute map-reduce pattern"""
        execution = self.create_execution(tasks)
        execution.status = TaskStatus.RUNNING
        execution.started_at = datetime.now(timezone.utc)
        
        try:
            # Separate map and reduce tasks
            map_tasks = [t for t in execution.tasks if t.task_type == "map"]
            reduce_tasks = [t for t in execution.tasks if t.task_type == "reduce"]
            
            if not map_tasks or not reduce_tasks:
                raise ValueError("MapReduce requires both map and reduce tasks")
            
            # Execute map phase in parallel
            map_results = await self._execute_map_phase(map_tasks, context)
            
            # Execute reduce phase
            reduce_result = await self._execute_reduce_phase(reduce_tasks, map_results, context)
            
            execution.status = TaskStatus.COMPLETED
            execution.result = reduce_result
            
        except Exception as e:
            execution.status = TaskStatus.FAILED
            execution.error = str(e)
        finally:
            execution.completed_at = datetime.now(timezone.utc)
        
        return execution
    
    async def _execute_map_phase(
        self,
        map_tasks: List[WorkflowTask],
        context: Dict[str, Any]
    ) -> List[Any]:
        """Execute map tasks in parallel"""
        input_data = context.get("input_data", {})
        
        # Create coroutines for parallel execution
        map_coroutines = []
        for task in map_tasks:
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now(timezone.utc)
            map_coroutines.append(self._execute_task(task, input_data))
        
        # Execute in parallel
        map_results = await asyncio.gather(*map_coroutines, return_exceptions=True)
        
        # Update task statuses
        for i, (task, result) in enumerate(zip(map_tasks, map_results)):
            if isinstance(result, Exception):
                task.status = TaskStatus.FAILED
                task.error = str(result)
            else:
                task.status = TaskStatus.COMPLETED
                task.result = result
            task.completed_at = datetime.now(timezone.utc)
        
        # Return successful results only
        return [result for result in map_results if not isinstance(result, Exception)]
    
    async def _execute_reduce_phase(
        self,
        reduce_tasks: List[WorkflowTask],
        map_results: List[Any],
        context: Dict[str, Any]
    ) -> Any:
        """Execute reduce phase"""
        # For simplicity, use first reduce task
        reduce_task = reduce_tasks[0]
        reduce_task.status = TaskStatus.RUNNING
        reduce_task.started_at = datetime.now(timezone.utc)
        
        try:
            result = await self._execute_task(reduce_task, {"map_results": map_results})
            reduce_task.status = TaskStatus.COMPLETED
            reduce_task.result = result
            return result
        except Exception as e:
            reduce_task.status = TaskStatus.FAILED
            reduce_task.error = str(e)
            raise
        finally:
            reduce_task.completed_at = datetime.now(timezone.utc)
    
    def validate_tasks(self, tasks: List[WorkflowTask]) -> List[str]:
        """Validate map-reduce tasks"""
        issues = []
        
        map_tasks = [t for t in tasks if t.task_type == "map"]
        reduce_tasks = [t for t in tasks if t.task_type == "reduce"]
        
        if not map_tasks:
            issues.append("MapReduce requires at least one map task")
        if not reduce_tasks:
            issues.append("MapReduce requires at least one reduce task")
        
        return issues
    
    async def _execute_task(self, task: WorkflowTask, input_data: Dict[str, Any]) -> Any:
        """Simulate task execution"""
        await asyncio.sleep(0.1)
        
        if task.task_type == "map":
            return {"mapped": input_data, "by": task.agent_id}
        elif task.task_type == "reduce":
            map_results = input_data.get("map_results", [])
            return {"reduced": map_results, "count": len(map_results), "by": task.agent_id}
        else:
            return {"processed": input_data, "by": task.agent_id}


class ParallelPattern(WorkflowPattern):
    """
    Parallel pattern - execute all tasks simultaneously
    
    All tasks run in parallel without dependencies.
    Suitable for independent operations.
    """
    
    def __init__(self, pattern_id: str, name: str = "Parallel", description: str = "Parallel task execution"):
        super().__init__(pattern_id, name, description, PatternType.PARALLEL)
    
    async def execute(
        self,
        tasks: List[WorkflowTask],
        context: Dict[str, Any]
    ) -> WorkflowExecution:
        """Execute all tasks in parallel"""
        execution = self.create_execution(tasks)
        execution.status = TaskStatus.RUNNING
        execution.started_at = datetime.now(timezone.utc)
        
        try:
            input_data = context.get("input_data", {})
            
            # Start all tasks
            for task in execution.tasks:
                task.status = TaskStatus.RUNNING
                task.started_at = datetime.now(timezone.utc)
            
            # Create coroutines for parallel execution
            task_coroutines = [
                self._execute_task(task, input_data) for task in execution.tasks
            ]
            
            # Execute in parallel
            results = await asyncio.gather(*task_coroutines, return_exceptions=True)
            
            # Update task statuses and collect results
            successful_results = []
            failed_count = 0
            
            for task, result in zip(execution.tasks, results):
                task.completed_at = datetime.now(timezone.utc)
                if isinstance(result, Exception):
                    task.status = TaskStatus.FAILED
                    task.error = str(result)
                    failed_count += 1
                else:
                    task.status = TaskStatus.COMPLETED
                    task.result = result
                    successful_results.append(result)
            
            # Determine overall status
            if failed_count == 0:
                execution.status = TaskStatus.COMPLETED
                execution.result = successful_results
            elif failed_count < len(execution.tasks):
                execution.status = TaskStatus.COMPLETED  # Partial success
                execution.result = successful_results
                execution.metadata["partial_failure"] = True
                execution.metadata["failed_tasks"] = failed_count
            else:
                execution.status = TaskStatus.FAILED
                execution.error = "All tasks failed"
            
        except Exception as e:
            execution.status = TaskStatus.FAILED
            execution.error = str(e)
        finally:
            execution.completed_at = datetime.now(timezone.utc)
        
        return execution
    
    def validate_tasks(self, tasks: List[WorkflowTask]) -> List[str]:
        """Validate parallel tasks"""
        issues = []
        
        # Check for dependencies (not allowed in parallel pattern)
        for task in tasks:
            if task.dependencies:
                issues.append(f"Task {task.task_id} has dependencies, not allowed in parallel pattern")
        
        return issues
    
    async def _execute_task(self, task: WorkflowTask, input_data: Dict[str, Any]) -> Any:
        """Simulate task execution"""
        await asyncio.sleep(0.1)
        return {"processed": input_data, "by": task.agent_id, "task_type": task.task_type}


class ConditionalPattern(WorkflowPattern):
    """
    Conditional pattern - execute tasks based on conditions
    
    Evaluates conditions to determine which tasks to execute.
    Supports if-then-else logic.
    """
    
    def __init__(self, pattern_id: str, name: str = "Conditional", description: str = "Conditional task execution"):
        super().__init__(pattern_id, name, description, PatternType.CONDITIONAL)
    
    async def execute(
        self,
        tasks: List[WorkflowTask],
        context: Dict[str, Any]
    ) -> WorkflowExecution:
        """Execute tasks based on conditions"""
        execution = self.create_execution(tasks)
        execution.status = TaskStatus.RUNNING
        execution.started_at = datetime.now(timezone.utc)
        
        try:
            condition_data = context.get("condition_data", {})
            
            for task in execution.tasks:
                # Check if task should be executed based on condition
                if self._should_execute_task(task, condition_data):
                    task.status = TaskStatus.RUNNING
                    task.started_at = datetime.now(timezone.utc)
                    
                    try:
                        result = await self._execute_task(task, condition_data)
                        task.result = result
                        task.status = TaskStatus.COMPLETED
                    except Exception as e:
                        task.error = str(e)
                        task.status = TaskStatus.FAILED
                    finally:
                        task.completed_at = datetime.now(timezone.utc)
                else:
                    task.status = TaskStatus.SKIPPED
                    task.completed_at = datetime.now(timezone.utc)
            
            # Collect results from executed tasks
            results = [
                task.result for task in execution.tasks 
                if task.status == TaskStatus.COMPLETED and task.result is not None
            ]
            
            execution.status = TaskStatus.COMPLETED
            execution.result = results
            
        except Exception as e:
            execution.status = TaskStatus.FAILED
            execution.error = str(e)
        finally:
            execution.completed_at = datetime.now(timezone.utc)
        
        return execution
    
    def _should_execute_task(self, task: WorkflowTask, condition_data: Dict[str, Any]) -> bool:
        """Determine if task should be executed based on conditions"""
        # Simple condition evaluation based on task metadata
        condition = task.metadata.get("condition")
        if not condition:
            return True  # No condition means always execute
        
        # Simple condition format: "field:value" or "field:>value" etc.
        if ":" not in condition:
            return True
        
        field, condition_value = condition.split(":", 1)
        actual_value = condition_data.get(field)
        
        if actual_value is None:
            return False
        
        # Simple comparison operators
        if condition_value.startswith(">"):
            return actual_value > float(condition_value[1:])
        elif condition_value.startswith("<"):
            return actual_value < float(condition_value[1:])
        elif condition_value.startswith("="):
            return str(actual_value) == condition_value[1:]
        else:
            return str(actual_value) == condition_value
    
    def validate_tasks(self, tasks: List[WorkflowTask]) -> List[str]:
        """Validate conditional tasks"""
        issues = []
        
        # Check that tasks have conditions defined
        for task in tasks:
            condition = task.metadata.get("condition")
            if condition and ":" not in condition:
                issues.append(f"Task {task.task_id} has invalid condition format: {condition}")
        
        return issues
    
    async def _execute_task(self, task: WorkflowTask, input_data: Dict[str, Any]) -> Any:
        """Simulate task execution"""
        await asyncio.sleep(0.1)
        return {"processed": input_data, "by": task.agent_id, "condition_met": True}


class LoopPattern(WorkflowPattern):
    """
    Loop pattern - repeat tasks until condition is met
    
    Iteratively executes tasks until termination condition.
    Supports while-loop style iteration.
    """
    
    def __init__(
        self,
        pattern_id: str,
        name: str = "Loop",
        description: str = "Iterative task execution",
        max_iterations: int = 10
    ):
        super().__init__(pattern_id, name, description, PatternType.LOOP)
        self.max_iterations = max_iterations
    
    async def execute(
        self,
        tasks: List[WorkflowTask],
        context: Dict[str, Any]
    ) -> WorkflowExecution:
        """Execute tasks in loop until condition is met"""
        execution = self.create_execution(tasks)
        execution.status = TaskStatus.RUNNING
        execution.started_at = datetime.now(timezone.utc)
        
        try:
            input_data = context.get("input_data", {})
            loop_condition = context.get("loop_condition", "iterations:>=1")
            iteration_count = 0
            results = []
            
            while iteration_count < self.max_iterations:
                iteration_count += 1
                iteration_results = []
                
                # Execute all tasks in this iteration
                for task in execution.tasks:
                    # Create new task instance for this iteration
                    iteration_task = WorkflowTask(
                        task_id=f"{task.task_id}_iter_{iteration_count}",
                        agent_id=task.agent_id,
                        task_type=task.task_type,
                        task_data=task.task_data.copy(),
                        metadata={**task.metadata, "iteration": iteration_count}
                    )
                    
                    iteration_task.status = TaskStatus.RUNNING
                    iteration_task.started_at = datetime.now(timezone.utc)
                    
                    try:
                        result = await self._execute_task(iteration_task, input_data)
                        iteration_task.result = result
                        iteration_task.status = TaskStatus.COMPLETED
                        iteration_results.append(result)
                    except Exception as e:
                        iteration_task.error = str(e)
                        iteration_task.status = TaskStatus.FAILED
                    finally:
                        iteration_task.completed_at = datetime.now(timezone.utc)
                
                results.append({
                    "iteration": iteration_count,
                    "results": iteration_results
                })
                
                # Check termination condition
                if self._should_terminate_loop(loop_condition, iteration_count, iteration_results):
                    break
                
                # Update input data for next iteration
                if iteration_results:
                    input_data = {"previous_results": iteration_results}
            
            execution.status = TaskStatus.COMPLETED
            execution.result = {
                "iterations": iteration_count,
                "results": results
            }
            execution.metadata["total_iterations"] = iteration_count
            
        except Exception as e:
            execution.status = TaskStatus.FAILED
            execution.error = str(e)
        finally:
            execution.completed_at = datetime.now(timezone.utc)
        
        return execution
    
    def _should_terminate_loop(
        self,
        condition: str,
        iteration_count: int,
        iteration_results: List[Any]
    ) -> bool:
        """Determine if loop should terminate"""
        if ":" not in condition:
            return iteration_count >= 1  # Default: single iteration
        
        field, value = condition.split(":", 1)
        
        if field == "iterations":
            if value.startswith(">="):
                return iteration_count >= int(value[2:])
            elif value.startswith("<="):
                return iteration_count <= int(value[2:])
            else:
                return iteration_count >= int(value)
        elif field == "results_count":
            return len(iteration_results) >= int(value)
        
        return False  # Default: don't terminate
    
    def validate_tasks(self, tasks: List[WorkflowTask]) -> List[str]:
        """Validate loop tasks"""
        issues = []
        
        if not tasks:
            issues.append("Loop pattern requires at least one task")
        
        return issues
    
    async def _execute_task(self, task: WorkflowTask, input_data: Dict[str, Any]) -> Any:
        """Simulate task execution"""
        await asyncio.sleep(0.1)
        iteration = task.metadata.get("iteration", 1)
        return {
            "processed": input_data,
            "by": task.agent_id,
            "iteration": iteration,
            "task_type": task.task_type
        }
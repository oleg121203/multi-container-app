"""
Test TEAM-05: Orchestration Patterns functionality
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from agents.orchestration import (
    OrchestrationEngine, OrchestrationStatus,
    WorkflowPattern, PipelinePattern, MapReducePattern, ParallelPattern,
    ConditionalPattern, LoopPattern, WorkflowTask, TaskStatus, PatternType,
    EventCoordinator, EventType, CoordinationEvent, EventPriority,
    PerformanceMonitor, MetricType, AlertLevel
)
from agents.registry.agent_registry import AgentRegistry, AgentInfo, AgentCapability


@pytest.fixture
def sample_agents():
    """Create sample agents for testing"""
    return [
        AgentInfo(
            agent_id="agent_1",
            name="Data Processor",
            description="Agent specialized in data processing",
            capabilities=[
                AgentCapability(name="data_processing", description="Data processing tasks")
            ]
        ),
        AgentInfo(
            agent_id="agent_2",
            name="Analyzer",
            description="Agent specialized in analysis",
            capabilities=[
                AgentCapability(name="analysis", description="Analysis tasks")
            ]
        ),
        AgentInfo(
            agent_id="agent_3",
            name="Reporter",
            description="Agent specialized in reporting",
            capabilities=[
                AgentCapability(name="reporting", description="Reporting tasks")
            ]
        )
    ]


@pytest.fixture
def sample_tasks():
    """Create sample workflow tasks"""
    return [
        WorkflowTask(
            task_id="task_1",
            agent_id="agent_1",
            task_type="extract",
            task_data={"source": "database"}
        ),
        WorkflowTask(
            task_id="task_2",
            agent_id="agent_2",
            task_type="transform",
            task_data={"rules": ["clean", "normalize"]},
            dependencies=["task_1"]
        ),
        WorkflowTask(
            task_id="task_3",
            agent_id="agent_3",
            task_type="load",
            task_data={"target": "warehouse"},
            dependencies=["task_2"]
        )
    ]


@pytest.mark.asyncio
async def test_pipeline_pattern():
    """Test pipeline workflow pattern"""
    pattern = PipelinePattern("test_pipeline", "Test Pipeline")
    
    tasks = [
        WorkflowTask("task_1", "agent_1", "extract"),
        WorkflowTask("task_2", "agent_2", "transform"),
        WorkflowTask("task_3", "agent_3", "load")
    ]
    
    context = {"input_data": {"source": "test_data"}}
    
    # Test validation
    issues = pattern.validate_tasks(tasks)
    assert len(issues) == 0
    
    # Test execution
    execution = await pattern.execute(tasks, context)
    
    assert execution.pattern_type == PatternType.PIPELINE
    assert execution.status == TaskStatus.COMPLETED
    assert len(execution.tasks) == 3
    assert all(task.status == TaskStatus.COMPLETED for task in execution.tasks)
    assert execution.result is not None


@pytest.mark.asyncio
async def test_parallel_pattern():
    """Test parallel workflow pattern"""
    pattern = ParallelPattern("test_parallel", "Test Parallel")
    
    tasks = [
        WorkflowTask("task_1", "agent_1", "process_a"),
        WorkflowTask("task_2", "agent_2", "process_b"),
        WorkflowTask("task_3", "agent_3", "process_c")
    ]
    
    context = {"input_data": {"data": "parallel_test"}}
    
    # Test validation
    issues = pattern.validate_tasks(tasks)
    assert len(issues) == 0
    
    # Test execution
    execution = await pattern.execute(tasks, context)
    
    assert execution.pattern_type == PatternType.PARALLEL
    assert execution.status == TaskStatus.COMPLETED
    assert len(execution.tasks) == 3
    assert all(task.status == TaskStatus.COMPLETED for task in execution.tasks)
    assert isinstance(execution.result, list)
    assert len(execution.result) == 3


@pytest.mark.asyncio
async def test_mapreduce_pattern():
    """Test map-reduce workflow pattern"""
    pattern = MapReducePattern("test_mapreduce", "Test MapReduce")
    
    map_tasks = [
        WorkflowTask("map_1", "agent_1", "map"),
        WorkflowTask("map_2", "agent_2", "map")
    ]
    reduce_tasks = [
        WorkflowTask("reduce_1", "agent_3", "reduce")
    ]
    
    all_tasks = map_tasks + reduce_tasks
    context = {"input_data": {"data_set": ["chunk1", "chunk2"]}}
    
    # Test validation
    issues = pattern.validate_tasks(all_tasks)
    assert len(issues) == 0
    
    # Test execution
    execution = await pattern.execute(all_tasks, context)
    
    assert execution.pattern_type == PatternType.MAP_REDUCE
    assert execution.status == TaskStatus.COMPLETED
    assert execution.result is not None


@pytest.mark.asyncio
async def test_conditional_pattern():
    """Test conditional workflow pattern"""
    pattern = ConditionalPattern("test_conditional", "Test Conditional")
    
    tasks = [
        WorkflowTask(
            "task_1", "agent_1", "process_if_true",
            metadata={"condition": "flag:true"}
        ),
        WorkflowTask(
            "task_2", "agent_2", "process_if_false", 
            metadata={"condition": "flag:false"}
        ),
        WorkflowTask(
            "task_3", "agent_3", "always_process"
            # No condition = always execute
        )
    ]
    
    context = {"condition_data": {"flag": "true"}}
    
    # Test execution
    execution = await pattern.execute(tasks, context)
    
    assert execution.pattern_type == PatternType.CONDITIONAL
    assert execution.status == TaskStatus.COMPLETED
    
    # Check that only tasks with matching conditions were executed
    executed_tasks = [t for t in execution.tasks if t.status == TaskStatus.COMPLETED]
    skipped_tasks = [t for t in execution.tasks if t.status == TaskStatus.SKIPPED]
    
    assert len(executed_tasks) == 2  # task_1 (condition matches) and task_3 (always)
    assert len(skipped_tasks) == 1   # task_2 (condition doesn't match)


@pytest.mark.asyncio
async def test_loop_pattern():
    """Test loop workflow pattern"""
    pattern = LoopPattern("test_loop", "Test Loop", max_iterations=3)
    
    tasks = [
        WorkflowTask("task_1", "agent_1", "iterate"),
        WorkflowTask("task_2", "agent_2", "accumulate")
    ]
    
    context = {
        "input_data": {"counter": 0},
        "loop_condition": "iterations:>=3"
    }
    
    # Test execution
    execution = await pattern.execute(tasks, context)
    
    assert execution.pattern_type == PatternType.LOOP
    assert execution.status == TaskStatus.COMPLETED
    assert execution.metadata["total_iterations"] == 3
    assert isinstance(execution.result, dict)
    assert execution.result["iterations"] == 3


@pytest.mark.asyncio
async def test_orchestration_engine(sample_agents, sample_tasks):
    """Test orchestration engine functionality"""
    # Setup
    registry = AgentRegistry()
    engine = OrchestrationEngine(registry)
    
    # Register agents
    for agent in sample_agents:
        await registry.register_agent(agent)
    
    # Test pattern registration
    assert len(engine.patterns) > 0  # Should have default patterns
    
    # Test pattern listing
    patterns = engine.list_patterns()
    assert len(patterns) > 0
    
    pipeline_patterns = engine.list_patterns(PatternType.PIPELINE)
    assert len(pipeline_patterns) > 0
    
    # Test orchestration
    request_id = await engine.orchestrate_pipeline(
        tasks=sample_tasks,
        context={"input_data": {"test": "data"}}
    )
    
    assert request_id is not None
    
    # Wait for completion
    await asyncio.sleep(0.5)
    
    # Check status
    status = await engine.get_orchestration_status(request_id)
    assert status in [OrchestrationStatus.COMPLETED, OrchestrationStatus.RUNNING]
    
    # Get result
    result = await engine.get_orchestration_result(request_id)
    assert result is not None
    assert result.request_id == request_id


@pytest.mark.asyncio
async def test_orchestration_engine_convenience_methods(sample_agents):
    """Test orchestration engine convenience methods"""
    registry = AgentRegistry()
    engine = OrchestrationEngine(registry)
    
    # Register agents
    for agent in sample_agents:
        await registry.register_agent(agent)
    
    # Test parallel orchestration
    parallel_tasks = [
        WorkflowTask("task_1", "agent_1", "process"),
        WorkflowTask("task_2", "agent_2", "process"),
        WorkflowTask("task_3", "agent_3", "process")
    ]
    
    request_id = await engine.orchestrate_parallel(parallel_tasks)
    assert request_id is not None
    
    # Test map-reduce orchestration
    map_tasks = [
        WorkflowTask("map_1", "agent_1", "map"),
        WorkflowTask("map_2", "agent_2", "map")
    ]
    reduce_tasks = [
        WorkflowTask("reduce_1", "agent_3", "reduce")
    ]
    
    request_id = await engine.orchestrate_mapreduce(map_tasks, reduce_tasks)
    assert request_id is not None


@pytest.mark.asyncio
async def test_orchestration_engine_pattern_suggestion(sample_agents, sample_tasks):
    """Test pattern suggestion functionality"""
    registry = AgentRegistry()
    engine = OrchestrationEngine(registry)
    
    # Test with dependent tasks (should suggest pipeline)
    suggestion = await engine.suggest_optimal_pattern(sample_tasks, {})
    assert suggestion == "standard_pipeline"
    
    # Test with map-reduce tasks
    mapreduce_tasks = [
        WorkflowTask("map_1", "agent_1", "map"),
        WorkflowTask("reduce_1", "agent_2", "reduce")
    ]
    suggestion = await engine.suggest_optimal_pattern(mapreduce_tasks, {})
    assert suggestion == "standard_mapreduce"
    
    # Test with independent tasks (should suggest parallel)
    parallel_tasks = [
        WorkflowTask("task_1", "agent_1", "process"),
        WorkflowTask("task_2", "agent_2", "process")
    ]
    suggestion = await engine.suggest_optimal_pattern(parallel_tasks, {})
    assert suggestion == "standard_parallel"


@pytest.mark.asyncio
async def test_event_coordinator():
    """Test event coordinator functionality"""
    coordinator = EventCoordinator()
    await coordinator.start()
    
    # Test event subscription
    received_events = []
    
    def event_handler(event: CoordinationEvent):
        received_events.append(event)
    
    subscription_id = coordinator.subscribe(
        subscriber_id="test_subscriber",
        event_types=[EventType.TASK_COMPLETED, EventType.WORKFLOW_STARTED],
        callback=event_handler
    )
    
    assert subscription_id is not None
    
    # Test event publishing
    event_id = await coordinator.publish_event(
        event_type=EventType.TASK_COMPLETED,
        source_id="test_agent",
        payload={"task_id": "test_task", "status": "success"}
    )
    
    assert event_id is not None
    
    # Wait for event processing
    await asyncio.sleep(0.1)
    
    # Check that event was received
    assert len(received_events) == 1
    assert received_events[0].event_type == EventType.TASK_COMPLETED
    assert received_events[0].source_id == "test_agent"
    
    # Test unsubscription
    success = coordinator.unsubscribe(subscription_id)
    assert success
    
    await coordinator.stop()


@pytest.mark.asyncio
async def test_event_coordinator_rules():
    """Test event coordinator rule functionality"""
    coordinator = EventCoordinator()
    await coordinator.start()
    
    # Track rule executions
    rule_executions = []
    
    def rule_callback(event, rule):
        rule_executions.append((event.event_id, rule.rule_id))
    
    # Add a rule
    success = coordinator.add_rule(
        rule_id="test_rule",
        name="Test Rule",
        trigger_events=[EventType.TASK_FAILED],
        actions=[
            {
                "type": "log",
                "message": "Task failed - triggering recovery",
                "level": "warning"
            },
            {
                "type": "callback",
                "callback": rule_callback
            }
        ],
        conditions={"source_id": "critical_agent"}
    )
    
    assert success
    
    # Publish event that should trigger rule
    await coordinator.publish_event(
        event_type=EventType.TASK_FAILED,
        source_id="critical_agent",
        payload={"error": "timeout"}
    )
    
    # Wait for processing
    await asyncio.sleep(0.1)
    
    # Check that rule was triggered
    assert len(rule_executions) == 1
    
    await coordinator.stop()


@pytest.mark.asyncio
async def test_performance_monitor():
    """Test performance monitor functionality"""
    monitor = PerformanceMonitor()
    await monitor.start_monitoring()
    
    # Test metric recording
    metric_id = monitor.record_execution_time(
        execution_time=1.5,
        source_id="agent_1",
        pattern_name="pipeline",
        success=True
    )
    
    assert metric_id is not None
    
    # Test throughput recording
    throughput_id = monitor.record_throughput(
        throughput=100.0,
        source_id="system"
    )
    
    assert throughput_id is not None
    
    # Test custom metric
    custom_id = monitor.record_metric(
        metric_type=MetricType.CUSTOM,
        name="Custom Metric",
        value=42.0,
        unit="units",
        source_id="test"
    )
    
    assert custom_id is not None
    
    # Test getting metrics
    current_metrics = monitor.get_current_metrics()
    assert len(current_metrics) >= 3
    
    execution_metrics = monitor.get_current_metrics(MetricType.EXECUTION_TIME)
    assert len(execution_metrics) >= 1
    
    agent_metrics = monitor.get_metrics_by_source("agent_1")
    assert len(agent_metrics) >= 1
    
    await monitor.stop_monitoring()


@pytest.mark.asyncio
async def test_performance_monitor_alerts():
    """Test performance monitor alert functionality"""
    monitor = PerformanceMonitor()
    
    # Track alerts
    received_alerts = []
    
    def alert_handler(alert):
        received_alerts.append(alert)
    
    monitor.add_alert_callback(alert_handler)
    
    # Record a metric that should trigger an alert (execution time > 30s threshold)
    monitor.record_execution_time(
        execution_time=35.0,
        source_id="slow_agent",
        success=True
    )
    
    # Wait for alert processing
    await asyncio.sleep(0.1)
    
    # Check that alert was generated
    assert len(received_alerts) >= 1
    alert = received_alerts[0]
    assert alert.alert_level == AlertLevel.WARNING
    assert alert.actual_value == 35.0


@pytest.mark.asyncio
async def test_performance_monitor_summary():
    """Test performance monitor summary functionality"""
    monitor = PerformanceMonitor()
    
    # Record several metrics
    for i in range(10):
        monitor.record_execution_time(
            execution_time=1.0 + i * 0.1,
            source_id=f"agent_{i % 3}",
            pattern_name="test_pattern",
            success=i < 8  # 8 successes, 2 failures
        )
    
    # Get performance summary
    summary = monitor.get_performance_summary()
    
    assert summary.total_executions == 10
    assert summary.successful_executions == 8
    assert summary.failed_executions == 2
    assert summary.success_rate == 0.8
    assert summary.error_rate == 0.2
    assert summary.average_execution_time > 0
    assert summary.min_execution_time >= 1.0
    assert summary.max_execution_time >= 1.9


@pytest.mark.asyncio
async def test_performance_monitor_recommendations():
    """Test performance monitor optimization recommendations"""
    monitor = PerformanceMonitor()
    
    # Record metrics that should trigger recommendations
    
    # High execution times
    for i in range(5):
        monitor.record_execution_time(
            execution_time=35.0,  # High execution time
            source_id="slow_agent",
            success=True
        )
    
    # Low success rate
    for i in range(10):
        monitor.record_execution_time(
            execution_time=1.0,
            source_id="unreliable_agent",
            success=i < 5  # 50% success rate
        )
    
    recommendations = monitor.get_optimization_recommendations()
    assert len(recommendations) > 0
    # Just check that we got valid recommendations
    assert all(isinstance(rec, str) and len(rec) > 0 for rec in recommendations)


@pytest.mark.asyncio
async def test_integrated_orchestration_system(sample_agents):
    """Test integrated orchestration system with all components"""
    # Setup all components
    registry = AgentRegistry()
    engine = OrchestrationEngine(registry)
    coordinator = EventCoordinator()
    monitor = PerformanceMonitor()
    
    # Register agents
    for agent in sample_agents:
        await registry.register_agent(agent)
    
    # Start components
    await coordinator.start()
    await monitor.start_monitoring()
    
    # Subscribe to workflow events
    workflow_events = []
    
    def workflow_event_handler(event: CoordinationEvent):
        workflow_events.append(event)
    
    coordinator.subscribe(
        subscriber_id="monitor",
        event_types=[EventType.WORKFLOW_STARTED, EventType.WORKFLOW_COMPLETED],
        callback=workflow_event_handler
    )
    
    # Add rule to monitor performance
    coordinator.add_rule(
        rule_id="performance_tracker",
        name="Performance Tracking Rule",
        trigger_events=[EventType.WORKFLOW_COMPLETED],
        actions=[{
            "type": "log",
            "message": "Workflow completed - updating performance metrics"
        }]
    )
    
    # Create and execute workflow
    tasks = [
        WorkflowTask("task_1", "agent_1", "process"),
        WorkflowTask("task_2", "agent_2", "analyze"),
        WorkflowTask("task_3", "agent_3", "report")
    ]
    
    # Publish workflow start event
    await coordinator.publish_event(
        event_type=EventType.WORKFLOW_STARTED,
        source_id="orchestrator",
        payload={"workflow_type": "test_workflow"}
    )
    
    # Execute workflow
    request_id = await engine.orchestrate_pipeline(tasks)
    
    # Wait for completion
    await asyncio.sleep(0.5)
    
    # Get orchestration result
    result = await engine.get_orchestration_result(request_id)
    assert result is not None
    
    # Record performance metrics
    if result.execution.status == TaskStatus.COMPLETED:
        execution_time = (result.execution.completed_at - result.execution.started_at).total_seconds()
        monitor.record_execution_time(
            execution_time=execution_time,
            source_id="orchestrator",
            pattern_name="pipeline",
            success=True
        )
        
        # Publish completion event
        await coordinator.publish_event(
            event_type=EventType.WORKFLOW_COMPLETED,
            source_id="orchestrator",
            payload={"status": "success", "execution_time": execution_time}
        )
    
    # Wait for event processing
    await asyncio.sleep(0.1)
    
    # Verify integration
    assert len(workflow_events) >= 1  # Should have received workflow events
    
    # Get performance summary
    summary = monitor.get_performance_summary()
    assert summary.total_executions >= 1
    
    # Get orchestration statistics
    orchestration_stats = engine.get_orchestration_statistics()
    assert orchestration_stats["total_requests"] >= 1
    
    # Get event statistics
    event_stats = coordinator.get_event_statistics()
    assert event_stats["total_events"] >= 2  # Start and completion events
    
    # Cleanup
    await coordinator.stop()
    await monitor.stop_monitoring()
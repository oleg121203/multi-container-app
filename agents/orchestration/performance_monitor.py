"""
Performance Monitor - Performance tracking for ATLAS Phase 4 orchestration

Monitors and analyzes performance of multi-agent workflows and coordination.
Provides metrics, alerts, and optimization recommendations.
"""

import asyncio
import logging
import statistics
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """Types of performance metrics"""
    EXECUTION_TIME = "execution_time"
    THROUGHPUT = "throughput"
    SUCCESS_RATE = "success_rate"
    ERROR_RATE = "error_rate"
    RESOURCE_UTILIZATION = "resource_utilization"
    LATENCY = "latency"
    QUEUE_SIZE = "queue_size"
    AGENT_EFFICIENCY = "agent_efficiency"
    WORKFLOW_EFFICIENCY = "workflow_efficiency"
    CUSTOM = "custom"


class AlertLevel(str, Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class PerformanceMetric:
    """Individual performance metric"""
    metric_id: str
    metric_type: MetricType
    name: str
    value: float
    unit: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source_id: str = ""
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceAlert:
    """Performance alert"""
    alert_id: str
    metric_id: str
    alert_level: AlertLevel
    message: str
    threshold_value: float
    actual_value: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceThreshold:
    """Performance threshold definition"""
    threshold_id: str
    metric_type: MetricType
    operator: str  # >, <, >=, <=, ==, !=
    value: float
    alert_level: AlertLevel
    description: str
    enabled: bool = True
    cooldown_seconds: int = 300  # 5 minutes default
    last_triggered: Optional[datetime] = None


@dataclass
class PerformanceSummary:
    """Summary of performance metrics"""
    period_start: datetime
    period_end: datetime
    total_executions: int
    successful_executions: int
    failed_executions: int
    average_execution_time: float
    min_execution_time: float
    max_execution_time: float
    throughput_per_hour: float
    success_rate: float
    error_rate: float
    p95_execution_time: float
    p99_execution_time: float
    resource_efficiency: float
    agent_utilization: Dict[str, float] = field(default_factory=dict)
    pattern_performance: Dict[str, Dict[str, float]] = field(default_factory=dict)


class PerformanceMonitor:
    """
    Performance monitoring and analysis system
    
    Tracks workflow execution metrics, generates alerts,
    and provides performance optimization recommendations.
    """
    
    def __init__(self, max_history_size: int = 10000):
        """Initialize the performance monitor"""
        self.max_history_size = max_history_size
        
        # Metrics storage
        self.metrics_history: deque = deque(maxlen=max_history_size)
        self.current_metrics: Dict[str, PerformanceMetric] = {}
        self.metrics_by_type: Dict[MetricType, List[PerformanceMetric]] = defaultdict(list)
        
        # Alerts and thresholds
        self.alerts: Dict[str, PerformanceAlert] = {}
        self.thresholds: Dict[str, PerformanceThreshold] = {}
        self.alert_callbacks: List[Callable[[PerformanceAlert], None]] = []
        
        # Performance aggregations
        self.execution_times: deque = deque(maxlen=1000)  # Last 1000 executions
        self.throughput_samples: deque = deque(maxlen=100)  # Last 100 samples
        self.agent_metrics: Dict[str, Dict[str, deque]] = defaultdict(lambda: defaultdict(lambda: deque(maxlen=100)))
        self.pattern_metrics: Dict[str, Dict[str, deque]] = defaultdict(lambda: defaultdict(lambda: deque(maxlen=100)))
        
        # Background tasks
        self._monitoring_task: Optional[asyncio.Task] = None
        self._analysis_task: Optional[asyncio.Task] = None
        
        # Initialize default thresholds
        self._initialize_default_thresholds()
        
        logger.info("PerformanceMonitor initialized")

    def _initialize_default_thresholds(self) -> None:
        """Initialize default performance thresholds"""
        default_thresholds = [
            PerformanceThreshold(
                threshold_id="execution_time_warning",
                metric_type=MetricType.EXECUTION_TIME,
                operator=">",
                value=30.0,  # 30 seconds
                alert_level=AlertLevel.WARNING,
                description="Execution time exceeds 30 seconds"
            ),
            PerformanceThreshold(
                threshold_id="execution_time_critical",
                metric_type=MetricType.EXECUTION_TIME,
                operator=">",
                value=60.0,  # 60 seconds
                alert_level=AlertLevel.CRITICAL,
                description="Execution time exceeds 60 seconds"
            ),
            PerformanceThreshold(
                threshold_id="error_rate_warning",
                metric_type=MetricType.ERROR_RATE,
                operator=">",
                value=0.1,  # 10%
                alert_level=AlertLevel.WARNING,
                description="Error rate exceeds 10%"
            ),
            PerformanceThreshold(
                threshold_id="success_rate_critical",
                metric_type=MetricType.SUCCESS_RATE,
                operator="<",
                value=0.8,  # 80%
                alert_level=AlertLevel.CRITICAL,
                description="Success rate below 80%"
            )
        ]
        
        for threshold in default_thresholds:
            self.thresholds[threshold.threshold_id] = threshold

    async def start_monitoring(self) -> None:
        """Start background monitoring tasks"""
        if not self._monitoring_task:
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
            self._analysis_task = asyncio.create_task(self._analysis_loop())
            logger.info("Performance monitoring started")

    async def stop_monitoring(self) -> None:
        """Stop background monitoring tasks"""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            self._monitoring_task = None
        
        if self._analysis_task:
            self._analysis_task.cancel()
            self._analysis_task = None
        
        logger.info("Performance monitoring stopped")

    def record_metric(
        self,
        metric_type: MetricType,
        name: str,
        value: float,
        unit: str = "",
        source_id: str = "",
        tags: Optional[Dict[str, str]] = None
    ) -> str:
        """Record a performance metric"""
        
        metric_id = f"metric_{len(self.metrics_history)}_{int(datetime.now().timestamp())}"
        
        metric = PerformanceMetric(
            metric_id=metric_id,
            metric_type=metric_type,
            name=name,
            value=value,
            unit=unit,
            source_id=source_id,
            tags=tags or {}
        )
        
        # Store metric
        self.metrics_history.append(metric)
        self.current_metrics[metric_id] = metric
        self.metrics_by_type[metric_type].append(metric)
        
        # Update specific aggregations
        if metric_type == MetricType.EXECUTION_TIME:
            self.execution_times.append(value)
        elif metric_type == MetricType.THROUGHPUT:
            self.throughput_samples.append(value)
        
        # Update agent-specific metrics
        if source_id and source_id.startswith("agent_"):
            self.agent_metrics[source_id][metric_type.value].append(value)
        
        # Update pattern-specific metrics
        pattern_name = tags.get("pattern_name") if tags else None
        if pattern_name:
            self.pattern_metrics[pattern_name][metric_type.value].append(value)
        
        # Check thresholds
        asyncio.create_task(self._check_thresholds(metric))
        
        return metric_id

    def record_execution_time(
        self,
        execution_time: float,
        source_id: str = "",
        pattern_name: Optional[str] = None,
        success: bool = True
    ) -> str:
        """Convenience method to record execution time"""
        tags = {"success": "true" if success else "false"}
        if pattern_name:
            tags["pattern_name"] = pattern_name
        
        return self.record_metric(
            metric_type=MetricType.EXECUTION_TIME,
            name="Workflow Execution Time",
            value=execution_time,
            unit="seconds",
            source_id=source_id,
            tags=tags
        )

    def record_throughput(
        self,
        throughput: float,
        source_id: str = "",
        unit: str = "executions/hour"
    ) -> str:
        """Convenience method to record throughput"""
        return self.record_metric(
            metric_type=MetricType.THROUGHPUT,
            name="System Throughput",
            value=throughput,
            unit=unit,
            source_id=source_id
        )

    def add_threshold(self, threshold: PerformanceThreshold) -> None:
        """Add a performance threshold"""
        self.thresholds[threshold.threshold_id] = threshold
        logger.info(f"Added threshold: {threshold.threshold_id}")

    def remove_threshold(self, threshold_id: str) -> bool:
        """Remove a performance threshold"""
        if threshold_id in self.thresholds:
            del self.thresholds[threshold_id]
            logger.info(f"Removed threshold: {threshold_id}")
            return True
        return False

    def add_alert_callback(self, callback: Callable[[PerformanceAlert], None]) -> None:
        """Add callback for alert notifications"""
        self.alert_callbacks.append(callback)

    def get_current_metrics(self, metric_type: Optional[MetricType] = None) -> List[PerformanceMetric]:
        """Get current metrics, optionally filtered by type"""
        if metric_type:
            return [m for m in self.current_metrics.values() if m.metric_type == metric_type]
        return list(self.current_metrics.values())

    def get_metrics_by_source(self, source_id: str) -> List[PerformanceMetric]:
        """Get metrics by source ID"""
        return [m for m in self.current_metrics.values() if m.source_id == source_id]

    def get_active_alerts(self) -> List[PerformanceAlert]:
        """Get all active (unresolved) alerts"""
        return [alert for alert in self.alerts.values() if not alert.resolved]

    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        alert = self.alerts.get(alert_id)
        if alert and not alert.resolved:
            alert.resolved = True
            alert.resolved_at = datetime.now(timezone.utc)
            logger.info(f"Resolved alert: {alert_id}")
            return True
        return False

    def get_performance_summary(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> PerformanceSummary:
        """Get performance summary for a time period"""
        
        if not start_time:
            start_time = datetime.now(timezone.utc) - timedelta(hours=1)
        if not end_time:
            end_time = datetime.now(timezone.utc)
        
        # Filter metrics by time period
        period_metrics = [
            m for m in self.metrics_history
            if start_time <= m.timestamp <= end_time
        ]
        
        # Calculate execution metrics
        execution_metrics = [
            m for m in period_metrics 
            if m.metric_type == MetricType.EXECUTION_TIME
        ]
        
        if not execution_metrics:
            # Return empty summary
            return PerformanceSummary(
                period_start=start_time,
                period_end=end_time,
                total_executions=0,
                successful_executions=0,
                failed_executions=0,
                average_execution_time=0.0,
                min_execution_time=0.0,
                max_execution_time=0.0,
                throughput_per_hour=0.0,
                success_rate=0.0,
                error_rate=0.0,
                p95_execution_time=0.0,
                p99_execution_time=0.0,
                resource_efficiency=0.0
            )
        
        execution_times = [m.value for m in execution_metrics]
        successful_executions = len([m for m in execution_metrics if m.tags.get("success") == "true"])
        total_executions = len(execution_metrics)
        failed_executions = total_executions - successful_executions
        
        # Calculate statistics
        avg_execution_time = statistics.mean(execution_times)
        min_execution_time = min(execution_times)
        max_execution_time = max(execution_times)
        
        # Calculate percentiles
        p95_execution_time = self._calculate_percentile(execution_times, 95)
        p99_execution_time = self._calculate_percentile(execution_times, 99)
        
        # Calculate rates
        success_rate = successful_executions / total_executions if total_executions > 0 else 0.0
        error_rate = failed_executions / total_executions if total_executions > 0 else 0.0
        
        # Calculate throughput (executions per hour)
        period_hours = (end_time - start_time).total_seconds() / 3600
        throughput_per_hour = total_executions / period_hours if period_hours > 0 else 0.0
        
        # Calculate agent utilization
        agent_utilization = self._calculate_agent_utilization(period_metrics)
        
        # Calculate pattern performance
        pattern_performance = self._calculate_pattern_performance(period_metrics)
        
        # Estimate resource efficiency (simplified)
        resource_efficiency = success_rate * (1 / (avg_execution_time + 1))  # Higher is better
        
        return PerformanceSummary(
            period_start=start_time,
            period_end=end_time,
            total_executions=total_executions,
            successful_executions=successful_executions,
            failed_executions=failed_executions,
            average_execution_time=avg_execution_time,
            min_execution_time=min_execution_time,
            max_execution_time=max_execution_time,
            throughput_per_hour=throughput_per_hour,
            success_rate=success_rate,
            error_rate=error_rate,
            p95_execution_time=p95_execution_time,
            p99_execution_time=p99_execution_time,
            resource_efficiency=resource_efficiency,
            agent_utilization=agent_utilization,
            pattern_performance=pattern_performance
        )

    def get_optimization_recommendations(self) -> List[str]:
        """Get performance optimization recommendations"""
        recommendations = []
        
        if not self.execution_times:
            return ["Insufficient data for recommendations"]
        
        # Analyze execution times
        avg_time = statistics.mean(self.execution_times)
        if avg_time > 30:
            recommendations.append("Consider optimizing workflow patterns - average execution time is high")
        
        # Analyze success rate
        recent_metrics = list(self.metrics_history)[-100:] if self.metrics_history else []
        execution_metrics = [m for m in recent_metrics if m.metric_type == MetricType.EXECUTION_TIME]
        
        if execution_metrics:
            success_count = len([m for m in execution_metrics if m.tags.get("success") == "true"])
            success_rate = success_count / len(execution_metrics)
            
            if success_rate < 0.9:
                recommendations.append("Investigate and address high failure rate")
        
        # Analyze agent utilization
        if self.agent_metrics:
            low_utilization_agents = []
            for agent_id, metrics in self.agent_metrics.items():
                if MetricType.AGENT_EFFICIENCY.value in metrics:
                    efficiency_values = list(metrics[MetricType.AGENT_EFFICIENCY.value])
                    if efficiency_values and statistics.mean(efficiency_values) < 0.5:
                        low_utilization_agents.append(agent_id)
            
            if low_utilization_agents:
                recommendations.append(f"Consider redistributing work from underutilized agents: {low_utilization_agents}")
        
        # Analyze patterns
        if self.pattern_metrics:
            slow_patterns = []
            for pattern_name, metrics in self.pattern_metrics.items():
                if MetricType.EXECUTION_TIME.value in metrics:
                    times = list(metrics[MetricType.EXECUTION_TIME.value])
                    if times and statistics.mean(times) > avg_time * 1.5:
                        slow_patterns.append(pattern_name)
            
            if slow_patterns:
                recommendations.append(f"Optimize slow patterns: {slow_patterns}")
        
        return recommendations if recommendations else ["System performance is optimal"]

    async def _monitoring_loop(self) -> None:
        """Background monitoring loop"""
        while True:
            try:
                await asyncio.sleep(60)  # Every minute
                await self._collect_system_metrics()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")

    async def _analysis_loop(self) -> None:
        """Background analysis loop"""
        while True:
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                await self._analyze_trends()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Analysis loop error: {e}")

    async def _collect_system_metrics(self) -> None:
        """Collect system-level metrics"""
        # Calculate current throughput
        recent_executions = len([
            m for m in self.metrics_history
            if m.metric_type == MetricType.EXECUTION_TIME and
            m.timestamp > datetime.now(timezone.utc) - timedelta(hours=1)
        ])
        
        self.record_throughput(recent_executions, source_id="system")
        
        # Calculate current success rate
        if self.execution_times:
            recent_metrics = list(self.metrics_history)[-100:]
            execution_metrics = [m for m in recent_metrics if m.metric_type == MetricType.EXECUTION_TIME]
            
            if execution_metrics:
                success_count = len([m for m in execution_metrics if m.tags.get("success") == "true"])
                success_rate = success_count / len(execution_metrics)
                
                self.record_metric(
                    metric_type=MetricType.SUCCESS_RATE,
                    name="System Success Rate",
                    value=success_rate,
                    unit="ratio",
                    source_id="system"
                )

    async def _analyze_trends(self) -> None:
        """Analyze performance trends"""
        logger.debug("Analyzing performance trends")
        
        # Analyze execution time trends
        if len(self.execution_times) >= 10:
            recent_times = list(self.execution_times)[-50:]  # Last 50 executions
            older_times = list(self.execution_times)[-100:-50] if len(self.execution_times) >= 100 else []
            
            if older_times:
                recent_avg = statistics.mean(recent_times)
                older_avg = statistics.mean(older_times)
                
                if recent_avg > older_avg * 1.2:  # 20% increase
                    logger.warning("Performance degradation detected - execution times increasing")

    async def _check_thresholds(self, metric: PerformanceMetric) -> None:
        """Check metric against defined thresholds"""
        for threshold in self.thresholds.values():
            if not threshold.enabled or threshold.metric_type != metric.metric_type:
                continue
            
            # Check cooldown
            if threshold.last_triggered and threshold.cooldown_seconds > 0:
                time_since = (datetime.now(timezone.utc) - threshold.last_triggered).total_seconds()
                if time_since < threshold.cooldown_seconds:
                    continue
            
            # Evaluate threshold
            if self._evaluate_threshold(metric.value, threshold):
                await self._create_alert(metric, threshold)
                threshold.last_triggered = datetime.now(timezone.utc)

    def _evaluate_threshold(self, value: float, threshold: PerformanceThreshold) -> bool:
        """Evaluate if a value breaches a threshold"""
        if threshold.operator == ">":
            return value > threshold.value
        elif threshold.operator == "<":
            return value < threshold.value
        elif threshold.operator == ">=":
            return value >= threshold.value
        elif threshold.operator == "<=":
            return value <= threshold.value
        elif threshold.operator == "==":
            return value == threshold.value
        elif threshold.operator == "!=":
            return value != threshold.value
        return False

    async def _create_alert(self, metric: PerformanceMetric, threshold: PerformanceThreshold) -> None:
        """Create and notify about a performance alert"""
        alert_id = f"alert_{len(self.alerts)}_{int(datetime.now().timestamp())}"
        
        alert = PerformanceAlert(
            alert_id=alert_id,
            metric_id=metric.metric_id,
            alert_level=threshold.alert_level,
            message=f"{threshold.description} - Value: {metric.value} {metric.unit}",
            threshold_value=threshold.value,
            actual_value=metric.value
        )
        
        self.alerts[alert_id] = alert
        
        # Notify callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")
        
        logger.warning(f"Performance alert: {alert.message}")

    def _calculate_percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile of values"""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = int((percentile / 100.0) * len(sorted_values))
        if index >= len(sorted_values):
            index = len(sorted_values) - 1
        return sorted_values[index]

    def _calculate_agent_utilization(self, metrics: List[PerformanceMetric]) -> Dict[str, float]:
        """Calculate agent utilization from metrics"""
        agent_utilization = {}
        
        agent_metrics = defaultdict(list)
        for metric in metrics:
            if metric.source_id.startswith("agent_"):
                agent_metrics[metric.source_id].append(metric)
        
        for agent_id, agent_metric_list in agent_metrics.items():
            # Simple utilization calculation based on execution count
            execution_count = len([m for m in agent_metric_list if m.metric_type == MetricType.EXECUTION_TIME])
            # Normalize to 0-1 scale (assuming max 100 executions per hour is full utilization)
            utilization = min(1.0, execution_count / 100.0)
            agent_utilization[agent_id] = utilization
        
        return agent_utilization

    def _calculate_pattern_performance(self, metrics: List[PerformanceMetric]) -> Dict[str, Dict[str, float]]:
        """Calculate pattern performance from metrics"""
        pattern_performance = defaultdict(lambda: {"avg_time": 0.0, "success_rate": 0.0, "count": 0})
        
        pattern_metrics = defaultdict(list)
        for metric in metrics:
            pattern_name = metric.tags.get("pattern_name")
            if pattern_name and metric.metric_type == MetricType.EXECUTION_TIME:
                pattern_metrics[pattern_name].append(metric)
        
        for pattern_name, metric_list in pattern_metrics.items():
            execution_times = [m.value for m in metric_list]
            successful = len([m for m in metric_list if m.tags.get("success") == "true"])
            
            pattern_performance[pattern_name] = {
                "avg_time": statistics.mean(execution_times) if execution_times else 0.0,
                "success_rate": successful / len(metric_list) if metric_list else 0.0,
                "count": len(metric_list)
            }
        
        return dict(pattern_performance)
"""
Event Coordinator - Event-driven coordination for ATLAS Phase 4

Manages event-driven coordination between agents and workflows.
Provides publish-subscribe mechanisms and event-based triggering.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Types of coordination events"""
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    AGENT_AVAILABLE = "agent_available"
    AGENT_BUSY = "agent_busy"
    AGENT_OFFLINE = "agent_offline"
    RESOURCE_AVAILABLE = "resource_available"
    RESOURCE_EXHAUSTED = "resource_exhausted"
    THRESHOLD_EXCEEDED = "threshold_exceeded"
    STATE_CHANGED = "state_changed"
    CUSTOM = "custom"


class EventPriority(str, Enum):
    """Priority levels for events"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class CoordinationEvent:
    """Represents a coordination event"""
    event_id: str
    event_type: EventType
    source_id: str  # ID of the source (agent, workflow, etc.)
    target_ids: List[str] = field(default_factory=list)  # Specific targets (empty = broadcast)
    priority: EventPriority = EventPriority.MEDIUM
    payload: Dict[str, Any] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    correlation_id: Optional[str] = None  # For event chaining
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EventSubscription:
    """Represents an event subscription"""
    subscription_id: str
    subscriber_id: str
    event_types: Set[EventType]
    callback: Callable[[CoordinationEvent], Any]
    filters: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EventRule:
    """Represents an event-driven rule"""
    rule_id: str
    name: str
    trigger_events: Set[EventType]
    conditions: Dict[str, Any] = field(default_factory=dict)
    actions: List[Dict[str, Any]] = field(default_factory=list)
    is_active: bool = True
    priority: int = 0
    cooldown_seconds: int = 0
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class EventCoordinator:
    """
    Event-driven coordination system
    
    Manages event publishing, subscription, and rule-based automation
    for coordinating multi-agent workflows and system responses.
    """
    
    def __init__(self):
        """Initialize the event coordinator"""
        self.events: Dict[str, CoordinationEvent] = {}  # event_id -> event
        self.subscriptions: Dict[str, EventSubscription] = {}  # subscription_id -> subscription
        self.rules: Dict[str, EventRule] = {}  # rule_id -> rule
        self.event_history: List[CoordinationEvent] = []
        
        # Index for fast lookup
        self.subscribers_by_type: Dict[EventType, Set[str]] = {}  # event_type -> subscription_ids
        self.rules_by_type: Dict[EventType, Set[str]] = {}  # event_type -> rule_ids
        
        # Statistics
        self._event_stats = {
            "total_events": 0,
            "total_subscriptions": 0,
            "total_rules": 0,
            "rules_triggered": 0,
            "events_by_type": {},
            "average_processing_time": 0.0
        }
        
        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._processing_queue: asyncio.Queue = asyncio.Queue()
        self._processor_task: Optional[asyncio.Task] = None
        
        logger.info("EventCoordinator initialized")

    async def start(self) -> None:
        """Start the event coordinator"""
        if not self._processor_task:
            self._processor_task = asyncio.create_task(self._process_events())
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
            logger.info("EventCoordinator started")

    async def stop(self) -> None:
        """Stop the event coordinator"""
        if self._processor_task:
            self._processor_task.cancel()
            self._processor_task = None
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            self._cleanup_task = None
        
        logger.info("EventCoordinator stopped")

    async def publish_event(
        self,
        event_type: EventType,
        source_id: str,
        payload: Optional[Dict[str, Any]] = None,
        target_ids: Optional[List[str]] = None,
        priority: EventPriority = EventPriority.MEDIUM,
        tags: Optional[Set[str]] = None,
        correlation_id: Optional[str] = None,
        expires_in_seconds: Optional[int] = None
    ) -> str:
        """Publish a coordination event"""
        
        event_id = f"event_{uuid.uuid4().hex[:8]}"
        expires_at = None
        if expires_in_seconds:
            expires_at = datetime.now(timezone.utc).replace(
                second=datetime.now().second + expires_in_seconds
            )
        
        event = CoordinationEvent(
            event_id=event_id,
            event_type=event_type,
            source_id=source_id,
            target_ids=target_ids or [],
            priority=priority,
            payload=payload or {},
            tags=tags or set(),
            expires_at=expires_at,
            correlation_id=correlation_id
        )
        
        self.events[event_id] = event
        self.event_history.append(event)
        
        # Update statistics
        self._event_stats["total_events"] += 1
        self._event_stats["events_by_type"][event_type] = self._event_stats["events_by_type"].get(event_type, 0) + 1
        
        # Queue for processing
        await self._processing_queue.put(event)
        
        logger.debug(f"Published event {event_id}: {event_type} from {source_id}")
        return event_id

    def subscribe(
        self,
        subscriber_id: str,
        event_types: List[EventType],
        callback: Callable[[CoordinationEvent], Any],
        filters: Optional[Dict[str, Any]] = None
    ) -> str:
        """Subscribe to coordination events"""
        
        subscription_id = f"sub_{subscriber_id}_{uuid.uuid4().hex[:6]}"
        
        subscription = EventSubscription(
            subscription_id=subscription_id,
            subscriber_id=subscriber_id,
            event_types=set(event_types),
            filters=filters or {},
            callback=callback
        )
        
        self.subscriptions[subscription_id] = subscription
        
        # Update index
        for event_type in event_types:
            if event_type not in self.subscribers_by_type:
                self.subscribers_by_type[event_type] = set()
            self.subscribers_by_type[event_type].add(subscription_id)
        
        self._event_stats["total_subscriptions"] += 1
        
        logger.info(f"Created subscription {subscription_id} for {subscriber_id}: {event_types}")
        return subscription_id

    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from events"""
        subscription = self.subscriptions.get(subscription_id)
        if not subscription:
            return False
        
        # Remove from index
        for event_type in subscription.event_types:
            if event_type in self.subscribers_by_type:
                self.subscribers_by_type[event_type].discard(subscription_id)
                if not self.subscribers_by_type[event_type]:
                    del self.subscribers_by_type[event_type]
        
        del self.subscriptions[subscription_id]
        logger.info(f"Removed subscription {subscription_id}")
        return True

    def add_rule(
        self,
        rule_id: str,
        name: str,
        trigger_events: List[EventType],
        actions: List[Dict[str, Any]],
        conditions: Optional[Dict[str, Any]] = None,
        priority: int = 0,
        cooldown_seconds: int = 0
    ) -> bool:
        """Add an event-driven rule"""
        
        if rule_id in self.rules:
            logger.warning(f"Rule {rule_id} already exists")
            return False
        
        rule = EventRule(
            rule_id=rule_id,
            name=name,
            trigger_events=set(trigger_events),
            conditions=conditions or {},
            actions=actions,
            priority=priority,
            cooldown_seconds=cooldown_seconds
        )
        
        self.rules[rule_id] = rule
        
        # Update index
        for event_type in trigger_events:
            if event_type not in self.rules_by_type:
                self.rules_by_type[event_type] = set()
            self.rules_by_type[event_type].add(rule_id)
        
        self._event_stats["total_rules"] += 1
        
        logger.info(f"Added rule {rule_id}: {name}")
        return True

    def remove_rule(self, rule_id: str) -> bool:
        """Remove an event-driven rule"""
        rule = self.rules.get(rule_id)
        if not rule:
            return False
        
        # Remove from index
        for event_type in rule.trigger_events:
            if event_type in self.rules_by_type:
                self.rules_by_type[event_type].discard(rule_id)
                if not self.rules_by_type[event_type]:
                    del self.rules_by_type[event_type]
        
        del self.rules[rule_id]
        logger.info(f"Removed rule {rule_id}")
        return True

    def get_event(self, event_id: str) -> Optional[CoordinationEvent]:
        """Get an event by ID"""
        return self.events.get(event_id)

    def get_events_by_type(
        self,
        event_type: EventType,
        limit: int = 100
    ) -> List[CoordinationEvent]:
        """Get events by type"""
        events = [
            event for event in self.event_history
            if event.event_type == event_type
        ]
        return events[-limit:] if limit else events

    def get_events_by_source(
        self,
        source_id: str,
        limit: int = 100
    ) -> List[CoordinationEvent]:
        """Get events by source"""
        events = [
            event for event in self.event_history
            if event.source_id == source_id
        ]
        return events[-limit:] if limit else events

    def get_event_statistics(self) -> Dict[str, Any]:
        """Get event processing statistics"""
        stats = self._event_stats.copy()
        stats.update({
            "active_subscriptions": len([s for s in self.subscriptions.values() if s.is_active]),
            "active_rules": len([r for r in self.rules.values() if r.is_active]),
            "total_events_in_memory": len(self.events),
            "event_history_size": len(self.event_history)
        })
        return stats

    async def _process_events(self) -> None:
        """Background task to process events"""
        while True:
            try:
                event = await self._processing_queue.get()
                start_time = datetime.now()
                
                # Process subscriptions
                await self._notify_subscribers(event)
                
                # Process rules
                await self._process_rules(event)
                
                # Calculate processing time
                processing_time = (datetime.now() - start_time).total_seconds() * 1000
                self._update_average_processing_time(processing_time)
                
                self._processing_queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing event: {e}")

    async def _notify_subscribers(self, event: CoordinationEvent) -> None:
        """Notify subscribers of an event"""
        subscription_ids = self.subscribers_by_type.get(event.event_type, set())
        
        for subscription_id in subscription_ids:
            subscription = self.subscriptions.get(subscription_id)
            if not subscription or not subscription.is_active:
                continue
            
            # Check if event matches subscription filters
            if not self._matches_filters(event, subscription.filters):
                continue
            
            # Check target filtering
            if event.target_ids and subscription.subscriber_id not in event.target_ids:
                continue
            
            try:
                # Call subscriber callback
                if asyncio.iscoroutinefunction(subscription.callback):
                    await subscription.callback(event)
                else:
                    subscription.callback(event)
            except Exception as e:
                logger.error(f"Subscription callback error for {subscription_id}: {e}")

    async def _process_rules(self, event: CoordinationEvent) -> None:
        """Process event-driven rules"""
        rule_ids = self.rules_by_type.get(event.event_type, set())
        
        # Sort rules by priority
        rules = [self.rules[rule_id] for rule_id in rule_ids if rule_id in self.rules]
        rules.sort(key=lambda r: r.priority, reverse=True)
        
        for rule in rules:
            if not rule.is_active:
                continue
            
            # Check cooldown
            if rule.last_triggered and rule.cooldown_seconds > 0:
                time_since_trigger = (datetime.now(timezone.utc) - rule.last_triggered).total_seconds()
                if time_since_trigger < rule.cooldown_seconds:
                    continue
            
            # Check conditions
            if not self._matches_conditions(event, rule.conditions):
                continue
            
            try:
                # Execute rule actions
                await self._execute_rule_actions(rule, event)
                
                # Update rule stats
                rule.last_triggered = datetime.now(timezone.utc)
                rule.trigger_count += 1
                self._event_stats["rules_triggered"] += 1
                
                logger.debug(f"Rule {rule.rule_id} triggered by event {event.event_id}")
                
            except Exception as e:
                logger.error(f"Rule execution error for {rule.rule_id}: {e}")

    async def _execute_rule_actions(self, rule: EventRule, event: CoordinationEvent) -> None:
        """Execute actions defined in a rule"""
        for action in rule.actions:
            action_type = action.get("type")
            
            if action_type == "publish_event":
                # Publish a new event
                await self.publish_event(
                    event_type=EventType(action.get("event_type", "custom")),
                    source_id=f"rule_{rule.rule_id}",
                    payload=action.get("payload", {}),
                    correlation_id=event.event_id
                )
            
            elif action_type == "log":
                # Log a message
                message = action.get("message", f"Rule {rule.rule_id} triggered")
                level = action.get("level", "info")
                getattr(logger, level)(message)
            
            elif action_type == "callback":
                # Call a custom callback
                callback = action.get("callback")
                if callback and callable(callback):
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event, rule)
                    else:
                        callback(event, rule)

    def _matches_filters(self, event: CoordinationEvent, filters: Dict[str, Any]) -> bool:
        """Check if event matches subscription filters"""
        for key, value in filters.items():
            if key == "source_id":
                if event.source_id != value:
                    return False
            elif key == "priority":
                if event.priority != value:
                    return False
            elif key == "tags":
                required_tags = set(value) if isinstance(value, list) else {value}
                if not required_tags.issubset(event.tags):
                    return False
            elif key == "payload":
                # Check payload fields
                if isinstance(value, dict):
                    for payload_key, payload_value in value.items():
                        if event.payload.get(payload_key) != payload_value:
                            return False
        
        return True

    def _matches_conditions(self, event: CoordinationEvent, conditions: Dict[str, Any]) -> bool:
        """Check if event matches rule conditions"""
        if not conditions:
            return True
        
        return self._matches_filters(event, conditions)

    def _update_average_processing_time(self, processing_time: float) -> None:
        """Update average processing time statistics"""
        total_events = self._event_stats["total_events"]
        if total_events > 1:
            current_avg = self._event_stats["average_processing_time"]
            new_avg = ((current_avg * (total_events - 1)) + processing_time) / total_events
            self._event_stats["average_processing_time"] = new_avg
        else:
            self._event_stats["average_processing_time"] = processing_time

    async def _periodic_cleanup(self) -> None:
        """Periodically clean up expired events"""
        while True:
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                await self._cleanup_expired_events()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup error: {e}")

    async def _cleanup_expired_events(self) -> None:
        """Clean up expired events"""
        now = datetime.now(timezone.utc)
        expired_events = []
        
        for event_id, event in self.events.items():
            if event.expires_at and event.expires_at < now:
                expired_events.append(event_id)
        
        for event_id in expired_events:
            del self.events[event_id]
        
        # Keep event history limited
        if len(self.event_history) > 10000:
            self.event_history = self.event_history[-5000:]  # Keep last 5000
        
        if expired_events:
            logger.debug(f"Cleaned up {len(expired_events)} expired events")

    def create_event_chain(
        self,
        events: List[Dict[str, Any]],
        correlation_id: Optional[str] = None
    ) -> str:
        """Create a chain of related events"""
        if not correlation_id:
            correlation_id = f"chain_{uuid.uuid4().hex[:8]}"
        
        for event_data in events:
            asyncio.create_task(
                self.publish_event(
                    correlation_id=correlation_id,
                    **event_data
                )
            )
        
        return correlation_id
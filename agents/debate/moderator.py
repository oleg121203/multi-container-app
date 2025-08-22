"""
Moderator - AI-powered moderation for ATLAS Phase 4 debates

Provides intelligent moderation capabilities for productive multi-agent discussions.
Monitors conversation quality, enforces rules, and guides discussion flow.
"""

import asyncio
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ModerationAction(str, Enum):
    """Types of moderation actions"""
    WARNING = "warning"
    MUTE = "mute"
    TIMEOUT = "timeout"
    REDIRECT = "redirect"
    INTERVENTION = "intervention"
    END_SESSION = "end_session"


class ModerationSeverity(str, Enum):
    """Severity levels for moderation"""
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ModerationEvent:
    """Represents a moderation event"""
    event_id: str
    session_id: str
    participant_id: Optional[str]
    action: ModerationAction
    severity: ModerationSeverity
    reason: str
    message: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParticipantBehavior:
    """Tracks participant behavior metrics"""
    participant_id: str
    session_id: str
    message_count: int = 0
    word_count: int = 0
    question_count: int = 0
    interruption_count: int = 0
    time_violations: int = 0
    warnings_received: int = 0
    last_message_time: Optional[datetime] = None
    speaking_time: float = 0.0
    engagement_score: float = 0.0


class ModerationRule(BaseModel):
    """Configuration for moderation rules"""
    rule_id: str
    name: str
    description: str
    enabled: bool = True
    severity: ModerationSeverity = ModerationSeverity.MEDIUM
    action: ModerationAction = ModerationAction.WARNING
    threshold: Optional[float] = None
    cooldown_seconds: int = 60
    parameters: Dict[str, Any] = {}


class Moderator:
    """
    AI-powered moderator for debate sessions
    
    Monitors conversation quality, participant behavior, and debate flow.
    Enforces rules and takes moderation actions to maintain productive discussions.
    """
    
    def __init__(self):
        """Initialize the moderator"""
        self.session_behaviors: Dict[str, Dict[str, ParticipantBehavior]] = {}
        self.moderation_events: Dict[str, List[ModerationEvent]] = {}
        self.session_rules: Dict[str, List[ModerationRule]] = {}
        self.global_rules = self._initialize_default_rules()
        self._action_cooldowns: Dict[str, Dict[str, datetime]] = {}
        
        logger.info("Moderator initialized with default rules")

    def initialize_session_moderation(
        self,
        session_id: str,
        participants: List[str],
        custom_rules: Optional[List[ModerationRule]] = None
    ) -> None:
        """Initialize moderation for a session"""
        # Initialize participant behaviors
        self.session_behaviors[session_id] = {}
        for participant_id in participants:
            self.session_behaviors[session_id][participant_id] = ParticipantBehavior(
                participant_id=participant_id,
                session_id=session_id
            )
        
        # Initialize moderation events
        self.moderation_events[session_id] = []
        
        # Set up rules (global + custom)
        rules = self.global_rules.copy()
        if custom_rules:
            rules.extend(custom_rules)
        self.session_rules[session_id] = rules
        
        # Initialize cooldowns
        self._action_cooldowns[session_id] = {}
        
        logger.info(f"Initialized moderation for session {session_id} with {len(participants)} participants")

    async def moderate_message(
        self,
        session_id: str,
        participant_id: str,
        message: str,
        message_type: str = "statement",
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[ModerationEvent]:
        """Moderate a message and return any moderation events"""
        if session_id not in self.session_behaviors:
            logger.warning(f"Session {session_id} not initialized for moderation")
            return []
        
        events = []
        behavior = self.session_behaviors[session_id].get(participant_id)
        if not behavior:
            return events
        
        # Update behavior metrics
        self._update_behavior_metrics(behavior, message, message_type, metadata or {})
        
        # Check moderation rules
        for rule in self.session_rules.get(session_id, []):
            if not rule.enabled:
                continue
                
            event = await self._check_rule(session_id, participant_id, rule, behavior, message)
            if event:
                events.append(event)
                
        return events

    async def moderate_turn_time(
        self,
        session_id: str,
        participant_id: str,
        allocated_time: int,
        actual_time: float
    ) -> Optional[ModerationEvent]:
        """Moderate turn time violations"""
        if actual_time <= allocated_time + 5:  # 5 second grace period
            return None
            
        behavior = self.session_behaviors[session_id].get(participant_id)
        if behavior:
            behavior.time_violations += 1
            
        severity = ModerationSeverity.LOW
        if actual_time > allocated_time * 1.5:
            severity = ModerationSeverity.MEDIUM
        if actual_time > allocated_time * 2:
            severity = ModerationSeverity.HIGH
            
        event = ModerationEvent(
            event_id=f"time_violation_{session_id}_{participant_id}_{int(datetime.now().timestamp())}",
            session_id=session_id,
            participant_id=participant_id,
            action=ModerationAction.WARNING,
            severity=severity,
            reason=f"Turn time exceeded by {actual_time - allocated_time:.1f} seconds",
            metadata={
                "allocated_time": allocated_time,
                "actual_time": actual_time,
                "violation_count": behavior.time_violations if behavior else 1
            }
        )
        
        await self._record_moderation_event(event)
        return event

    async def check_session_health(self, session_id: str) -> Dict[str, Any]:
        """Check overall session health and suggest interventions"""
        if session_id not in self.session_behaviors:
            return {"status": "unknown", "suggestions": []}
        
        behaviors = self.session_behaviors[session_id]
        total_participants = len(behaviors)
        
        # Calculate participation balance
        message_counts = [b.message_count for b in behaviors.values()]
        avg_messages = sum(message_counts) / len(message_counts) if message_counts else 0
        participation_variance = sum((count - avg_messages) ** 2 for count in message_counts) / len(message_counts) if message_counts else 0
        
        # Calculate engagement
        engagement_scores = [b.engagement_score for b in behaviors.values()]
        avg_engagement = sum(engagement_scores) / len(engagement_scores) if engagement_scores else 0
        
        # Check for issues
        suggestions = []
        status = "healthy"
        
        if participation_variance > (avg_messages * 0.5) ** 2:
            suggestions.append("Participation is unbalanced - consider encouraging quieter participants")
            status = "attention_needed"
            
        if avg_engagement < 0.3:
            suggestions.append("Low overall engagement - consider changing topic or format")
            status = "attention_needed"
            
        # Check for excessive warnings
        total_warnings = sum(b.warnings_received for b in behaviors.values())
        if total_warnings > total_participants * 2:
            suggestions.append("High number of warnings - consider session intervention")
            status = "concerning"
            
        # Check for dominant speakers
        max_messages = max(message_counts) if message_counts else 0
        if max_messages > avg_messages * 2 and avg_messages > 0:
            suggestions.append("One participant is dominating - consider turn management")
            status = "attention_needed"
        
        return {
            "status": status,
            "participation_balance": 1.0 - (participation_variance / (avg_messages ** 2)) if avg_messages > 0 else 1.0,
            "average_engagement": avg_engagement,
            "total_warnings": total_warnings,
            "suggestions": suggestions,
            "participant_count": total_participants
        }

    async def suggest_intervention(self, session_id: str) -> Optional[str]:
        """Suggest moderator intervention based on session state"""
        health = await self.check_session_health(session_id)
        
        if health["status"] == "concerning":
            return "Consider pausing the session to address behavioral issues"
        elif health["status"] == "attention_needed":
            if "unbalanced" in " ".join(health["suggestions"]):
                return "Encourage participation from quieter members"
            elif "dominating" in " ".join(health["suggestions"]):
                return "Gently redirect conversation to include other participants"
            elif "engagement" in " ".join(health["suggestions"]):
                return "Consider introducing a new perspective or question"
        
        return None

    def get_participant_behavior(
        self,
        session_id: str,
        participant_id: str
    ) -> Optional[ParticipantBehavior]:
        """Get behavior metrics for a participant"""
        return self.session_behaviors.get(session_id, {}).get(participant_id)

    def get_session_events(self, session_id: str) -> List[ModerationEvent]:
        """Get all moderation events for a session"""
        return self.moderation_events.get(session_id, []).copy()

    async def get_moderation_summary(self, session_id: str) -> Dict[str, Any]:
        """Get moderation summary for a session"""
        events = self.moderation_events.get(session_id, [])
        behaviors = self.session_behaviors.get(session_id, {})
        
        event_counts = {}
        for event in events:
            action = event.action
            event_counts[action] = event_counts.get(action, 0) + 1
        
        participant_summary = {}
        for participant_id, behavior in behaviors.items():
            participant_summary[participant_id] = {
                "messages": behavior.message_count,
                "warnings": behavior.warnings_received,
                "engagement": behavior.engagement_score,
                "speaking_time": behavior.speaking_time
            }
        
        session_health = await self.check_session_health(session_id)
        
        return {
            "total_events": len(events),
            "event_counts": event_counts,
            "participant_summary": participant_summary,
            "session_health": session_health
        }

    async def cleanup_session(self, session_id: str) -> None:
        """Clean up moderation data for a session"""
        self.session_behaviors.pop(session_id, None)
        self.moderation_events.pop(session_id, None)
        self.session_rules.pop(session_id, None)
        self._action_cooldowns.pop(session_id, None)
        
        logger.info(f"Cleaned up moderation data for session {session_id}")

    def _initialize_default_rules(self) -> List[ModerationRule]:
        """Initialize default moderation rules"""
        return [
            ModerationRule(
                rule_id="excessive_messages",
                name="Excessive Messages",
                description="Participant sending too many messages in short time",
                threshold=5,
                action=ModerationAction.WARNING,
                severity=ModerationSeverity.MEDIUM,
                parameters={"time_window": 60}
            ),
            ModerationRule(
                rule_id="no_participation",
                name="No Participation",
                description="Participant not contributing to discussion",
                threshold=300,  # 5 minutes
                action=ModerationAction.INTERVENTION,
                severity=ModerationSeverity.LOW,
                parameters={"check_interval": 300}
            ),
            ModerationRule(
                rule_id="repeated_warnings",
                name="Repeated Warnings",
                description="Participant receiving multiple warnings",
                threshold=3,
                action=ModerationAction.TIMEOUT,
                severity=ModerationSeverity.HIGH,
                parameters={"timeout_duration": 120}
            )
        ]

    def _update_behavior_metrics(
        self,
        behavior: ParticipantBehavior,
        message: str,
        message_type: str,
        metadata: Dict[str, Any]
    ) -> None:
        """Update participant behavior metrics"""
        behavior.message_count += 1
        behavior.word_count += len(message.split())
        behavior.last_message_time = datetime.now(timezone.utc)
        
        if message_type == "question" or "?" in message:
            behavior.question_count += 1
            
        # Simple engagement score based on message length and type
        engagement_boost = 0.1
        if len(message) > 50:
            engagement_boost += 0.1
        if message_type in ["question", "response"]:
            engagement_boost += 0.1
            
        behavior.engagement_score = min(1.0, behavior.engagement_score + engagement_boost)

    async def _check_rule(
        self,
        session_id: str,
        participant_id: str,
        rule: ModerationRule,
        behavior: ParticipantBehavior,
        message: str
    ) -> Optional[ModerationEvent]:
        """Check if a rule violation has occurred"""
        # Check cooldown
        cooldown_key = f"{participant_id}_{rule.rule_id}"
        if (session_id in self._action_cooldowns and 
            cooldown_key in self._action_cooldowns[session_id]):
            last_action = self._action_cooldowns[session_id][cooldown_key]
            time_since = (datetime.now(timezone.utc) - last_action).total_seconds()
            if time_since < rule.cooldown_seconds:
                return None
        
        event = None
        
        if rule.rule_id == "excessive_messages":
            # Check message rate
            time_window = rule.parameters.get("time_window", 60)
            if behavior.last_message_time:
                # Simplified check - in production would track message timestamps
                recent_message_rate = behavior.message_count / max(1, time_window / 60)
                if recent_message_rate > rule.threshold:
                    event = ModerationEvent(
                        event_id=f"excessive_msg_{session_id}_{participant_id}_{int(datetime.now().timestamp())}",
                        session_id=session_id,
                        participant_id=participant_id,
                        action=rule.action,
                        severity=rule.severity,
                        reason=f"Sending messages too frequently: {recent_message_rate:.1f}/min",
                        metadata={"message_rate": recent_message_rate, "threshold": rule.threshold}
                    )
                    
        elif rule.rule_id == "repeated_warnings":
            if behavior.warnings_received >= rule.threshold:
                event = ModerationEvent(
                    event_id=f"repeat_warn_{session_id}_{participant_id}_{int(datetime.now().timestamp())}",
                    session_id=session_id,
                    participant_id=participant_id,
                    action=rule.action,
                    severity=rule.severity,
                    reason=f"Received {behavior.warnings_received} warnings",
                    metadata={"warning_count": behavior.warnings_received}
                )
        
        if event:
            await self._record_moderation_event(event)
            
            # Update cooldown
            if session_id not in self._action_cooldowns:
                self._action_cooldowns[session_id] = {}
            self._action_cooldowns[session_id][cooldown_key] = datetime.now(timezone.utc)
            
            # Update behavior
            if event.action == ModerationAction.WARNING:
                behavior.warnings_received += 1
        
        return event

    async def _record_moderation_event(self, event: ModerationEvent) -> None:
        """Record a moderation event"""
        if event.session_id not in self.moderation_events:
            self.moderation_events[event.session_id] = []
        
        self.moderation_events[event.session_id].append(event)
        logger.info(f"Moderation event: {event.action} for {event.participant_id} - {event.reason}")
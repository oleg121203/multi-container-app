"""
Debate Orchestrator - Core debate session management for ATLAS Phase 4

Manages multi-agent discussion sessions with structured formats.
Coordinates debate lifecycle from initiation to conclusion.
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pydantic import BaseModel, Field

from agents.registry.agent_registry import AgentRegistry, AgentInfo
from agents.registry.team_constructor import TeamConstructor, Team
from agents.shared.config import config

logger = logging.getLogger(__name__)


class DebateStatus(str, Enum):
    """Debate session status"""
    PENDING = "pending"
    ACTIVE = "active"
    PAUSED = "paused"
    CONCLUDED = "concluded"
    CANCELLED = "cancelled"


class DebateFormat(str, Enum):
    """Debate format types"""
    ROUND_ROBIN = "round_robin"  # Each agent speaks in turn
    OXFORD = "oxford"  # Formal oxford debate style
    FISHBOWL = "fishbowl"  # Open discussion with moderation
    CONSENSUS = "consensus"  # Focus on reaching agreement


@dataclass
class DebateParticipant:
    """Participant in a debate session"""
    agent_id: str
    agent_info: AgentInfo
    role: str = "participant"  # participant, moderator, observer
    speaking_time: float = 0.0
    contributions: int = 0
    joined_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class DebateMessage:
    """Message in a debate session"""
    message_id: str
    participant_id: str
    content: str
    timestamp: datetime
    message_type: str = "statement"  # statement, question, response, consensus
    metadata: Dict[str, Any] = field(default_factory=dict)


class DebateSession(BaseModel):
    """Debate session model"""
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    topic: str
    format: DebateFormat = DebateFormat.ROUND_ROBIN
    status: DebateStatus = DebateStatus.PENDING
    participants: Dict[str, DebateParticipant] = Field(default_factory=dict)
    messages: List[DebateMessage] = Field(default_factory=list)
    moderator_id: Optional[str] = None
    max_participants: int = 4
    turn_duration: int = 60  # seconds
    max_rounds: int = 10
    current_round: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    conclusion: Optional[str] = None
    consensus_reached: bool = False

    class Config:
        arbitrary_types_allowed = True


class DebateOrchestrator:
    """
    Orchestrates multi-agent debate sessions
    
    Manages debate lifecycle, participant coordination, and session state.
    Integrates with Agent Registry and Team Constructor for participant selection.
    """
    
    def __init__(
        self,
        registry: AgentRegistry,
        team_constructor: Optional[TeamConstructor] = None
    ):
        """Initialize the debate orchestrator"""
        self.registry = registry
        self.team_constructor = team_constructor
        self.active_sessions: Dict[str, DebateSession] = {}
        self._session_stats = {
            "total_sessions": 0,
            "concluded_sessions": 0,
            "cancelled_sessions": 0,
            "average_duration": 0.0,
            "consensus_rate": 0.0
        }
        
        logger.info("DebateOrchestrator initialized")

    async def create_debate_session(
        self,
        topic: str,
        format: DebateFormat = DebateFormat.ROUND_ROBIN,
        max_participants: int = 4,
        turn_duration: int = 60,
        max_rounds: int = 10,
        required_capabilities: Optional[List[str]] = None
    ) -> DebateSession:
        """Create a new debate session"""
        session = DebateSession(
            topic=topic,
            format=format,
            max_participants=max_participants,
            turn_duration=turn_duration,
            max_rounds=max_rounds
        )
        
        # Auto-select participants if team constructor is available
        if self.team_constructor and required_capabilities:
            await self._auto_select_participants(session, required_capabilities)
        
        self.active_sessions[session.session_id] = session
        self._session_stats["total_sessions"] += 1
        
        logger.info(f"Created debate session: {session.session_id} - Topic: {topic}")
        return session

    async def add_participant(
        self,
        session_id: str,
        agent_id: str,
        role: str = "participant"
    ) -> bool:
        """Add a participant to a debate session"""
        if session_id not in self.active_sessions:
            return False
            
        session = self.active_sessions[session_id]
        
        if len(session.participants) >= session.max_participants:
            logger.warning(f"Session {session_id} is at maximum capacity")
            return False
            
        # Get agent info from registry
        agent_info = await self.registry.get_agent(agent_id)
        if not agent_info:
            logger.warning(f"Agent {agent_id} not found in registry")
            return False
            
        participant = DebateParticipant(
            agent_id=agent_id,
            agent_info=agent_info,
            role=role
        )
        
        session.participants[agent_id] = participant
        logger.info(f"Added participant {agent_id} to session {session_id}")
        return True

    async def start_debate(self, session_id: str) -> bool:
        """Start a debate session"""
        if session_id not in self.active_sessions:
            return False
            
        session = self.active_sessions[session_id]
        
        if session.status != DebateStatus.PENDING:
            logger.warning(f"Session {session_id} is not in pending state")
            return False
            
        if len(session.participants) < 2:
            logger.warning(f"Session {session_id} needs at least 2 participants")
            return False
            
        session.status = DebateStatus.ACTIVE
        session.started_at = datetime.now(timezone.utc)
        session.current_round = 1
        
        logger.info(f"Started debate session: {session_id}")
        return True

    async def add_message(
        self,
        session_id: str,
        participant_id: str,
        content: str,
        message_type: str = "statement",
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Add a message to the debate session"""
        if session_id not in self.active_sessions:
            return False
            
        session = self.active_sessions[session_id]
        
        if participant_id not in session.participants:
            logger.warning(f"Participant {participant_id} not in session {session_id}")
            return False
            
        message = DebateMessage(
            message_id=str(uuid.uuid4()),
            participant_id=participant_id,
            content=content,
            timestamp=datetime.now(timezone.utc),
            message_type=message_type,
            metadata=metadata or {}
        )
        
        session.messages.append(message)
        
        # Update participant stats
        participant = session.participants[participant_id]
        participant.contributions += 1
        
        logger.debug(f"Added message to session {session_id} from {participant_id}")
        return True

    async def conclude_debate(
        self,
        session_id: str,
        conclusion: Optional[str] = None,
        consensus_reached: bool = False
    ) -> bool:
        """Conclude a debate session"""
        if session_id not in self.active_sessions:
            return False
            
        session = self.active_sessions[session_id]
        session.status = DebateStatus.CONCLUDED
        session.ended_at = datetime.now(timezone.utc)
        session.conclusion = conclusion
        session.consensus_reached = consensus_reached
        
        # Update statistics
        self._session_stats["concluded_sessions"] += 1
        if session.started_at and session.ended_at:
            duration = (session.ended_at - session.started_at).total_seconds()
            self._update_average_duration(duration)
            
        if consensus_reached:
            self._update_consensus_rate()
        
        logger.info(f"Concluded debate session: {session_id}")
        return True

    async def pause_debate(self, session_id: str) -> bool:
        """Pause a debate session"""
        if session_id not in self.active_sessions:
            return False
            
        session = self.active_sessions[session_id]
        if session.status == DebateStatus.ACTIVE:
            session.status = DebateStatus.PAUSED
            logger.info(f"Paused debate session: {session_id}")
            return True
        return False

    async def resume_debate(self, session_id: str) -> bool:
        """Resume a paused debate session"""
        if session_id not in self.active_sessions:
            return False
            
        session = self.active_sessions[session_id]
        if session.status == DebateStatus.PAUSED:
            session.status = DebateStatus.ACTIVE
            logger.info(f"Resumed debate session: {session_id}")
            return True
        return False

    async def cancel_debate(self, session_id: str) -> bool:
        """Cancel a debate session"""
        if session_id not in self.active_sessions:
            return False
            
        session = self.active_sessions[session_id]
        session.status = DebateStatus.CANCELLED
        session.ended_at = datetime.now(timezone.utc)
        
        self._session_stats["cancelled_sessions"] += 1
        
        logger.info(f"Cancelled debate session: {session_id}")
        return True

    def get_session(self, session_id: str) -> Optional[DebateSession]:
        """Get debate session by ID"""
        return self.active_sessions.get(session_id)

    def list_active_sessions(self) -> List[DebateSession]:
        """List all active debate sessions"""
        return [
            session for session in self.active_sessions.values()
            if session.status in [DebateStatus.ACTIVE, DebateStatus.PAUSED]
        ]

    def get_session_statistics(self) -> Dict[str, Any]:
        """Get debate session statistics"""
        return self._session_stats.copy()

    async def _auto_select_participants(
        self,
        session: DebateSession,
        required_capabilities: List[str]
    ) -> None:
        """Auto-select participants based on capabilities"""
        if not self.team_constructor:
            return
            
        # Form a team for the debate topic
        team = await self.team_constructor.form_team(
            f"Participate in debate: {session.topic}",
            max_team_size=session.max_participants
        )
        
        if team:
            for member in team.members:
                participant = DebateParticipant(
                    agent_id=member.agent_id,
                    agent_info=member.agent_info,
                    role="participant"
                )
                session.participants[member.agent_id] = participant
                
            logger.info(f"Auto-selected {len(team.members)} participants for session {session.session_id}")

    def _update_average_duration(self, duration: float) -> None:
        """Update average session duration"""
        concluded = self._session_stats["concluded_sessions"]
        if concluded > 1:
            current_avg = self._session_stats["average_duration"]
            new_avg = ((current_avg * (concluded - 1)) + duration) / concluded
            self._session_stats["average_duration"] = new_avg
        else:
            self._session_stats["average_duration"] = duration

    def _update_consensus_rate(self) -> None:
        """Update consensus rate statistics"""
        concluded = self._session_stats["concluded_sessions"]
        if concluded > 0:
            consensus_sessions = sum(
                1 for session in self.active_sessions.values()
                if session.status == DebateStatus.CONCLUDED and session.consensus_reached
            )
            self._session_stats["consensus_rate"] = consensus_sessions / concluded

    async def cleanup_old_sessions(self, max_age_hours: int = 24) -> int:
        """Clean up old concluded sessions"""
        cutoff_time = datetime.now(timezone.utc).timestamp() - (max_age_hours * 3600)
        removed_count = 0
        
        sessions_to_remove = []
        for session_id, session in self.active_sessions.items():
            if (session.status in [DebateStatus.CONCLUDED, DebateStatus.CANCELLED] and
                session.ended_at and session.ended_at.timestamp() < cutoff_time):
                sessions_to_remove.append(session_id)
                
        for session_id in sessions_to_remove:
            del self.active_sessions[session_id]
            removed_count += 1
            
        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} old debate sessions")
            
        return removed_count
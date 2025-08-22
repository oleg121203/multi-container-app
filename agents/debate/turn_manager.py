"""
Turn Manager - Speaking order and turn control for ATLAS Phase 4

Controls speaking order, time allocation, and turn transitions in debate sessions.
Ensures fair participation and structured discussion flow.
"""

import asyncio
import logging
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class SpeakingOrder(str, Enum):
    """Speaking order strategies"""
    ROUND_ROBIN = "round_robin"  # Each participant speaks in order
    RANDOM = "random"  # Random selection
    PRIORITY_BASED = "priority_based"  # Based on participant priorities
    RAISE_HAND = "raise_hand"  # Request-based speaking
    MODERATOR_CONTROLLED = "moderator_controlled"  # Moderator assigns turns


class TurnStatus(str, Enum):
    """Status of a speaking turn"""
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    INTERRUPTED = "interrupted"


@dataclass
class DebateTurn:
    """Represents a speaking turn in a debate"""
    turn_id: str
    session_id: str
    participant_id: str
    round_number: int
    turn_order: int
    status: TurnStatus = TurnStatus.PENDING
    allocated_time: int = 60  # seconds
    actual_time: float = 0.0
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    content: Optional[str] = None
    interrupted_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class TurnManager:
    """
    Manages speaking turns and order in debate sessions
    
    Controls who can speak when, enforces time limits, and manages turn transitions.
    Supports multiple speaking order strategies and moderation controls.
    """
    
    def __init__(self):
        """Initialize the turn manager"""
        self.session_turns: Dict[str, List[DebateTurn]] = {}
        self.current_turns: Dict[str, Optional[DebateTurn]] = {}
        self.turn_callbacks: Dict[str, List[Callable]] = {}
        self.speaking_queues: Dict[str, List[str]] = {}  # session_id -> participant queue
        self._turn_timers: Dict[str, asyncio.Task] = {}
        
        logger.info("TurnManager initialized")

    async def initialize_session_turns(
        self,
        session_id: str,
        participants: List[str],
        speaking_order: SpeakingOrder = SpeakingOrder.ROUND_ROBIN,
        turn_duration: int = 60,
        max_rounds: int = 10
    ) -> bool:
        """Initialize turn management for a session"""
        if session_id in self.session_turns:
            logger.warning(f"Session {session_id} already has turns initialized")
            return False
            
        self.session_turns[session_id] = []
        self.current_turns[session_id] = None
        self.turn_callbacks[session_id] = []
        self.speaking_queues[session_id] = []
        
        # Generate turns for all rounds
        for round_num in range(1, max_rounds + 1):
            ordered_participants = self._order_participants(participants, speaking_order, round_num)
            
            for turn_order, participant_id in enumerate(ordered_participants, 1):
                turn = DebateTurn(
                    turn_id=f"{session_id}-r{round_num}-t{turn_order}",
                    session_id=session_id,
                    participant_id=participant_id,
                    round_number=round_num,
                    turn_order=turn_order,
                    allocated_time=turn_duration
                )
                self.session_turns[session_id].append(turn)
        
        logger.info(f"Initialized {len(self.session_turns[session_id])} turns for session {session_id}")
        return True

    async def start_next_turn(self, session_id: str) -> Optional[DebateTurn]:
        """Start the next available turn in the session"""
        if session_id not in self.session_turns:
            logger.warning(f"No turns found for session {session_id}")
            return None
            
        # Find next pending turn
        next_turn = None
        for turn in self.session_turns[session_id]:
            if turn.status == TurnStatus.PENDING:
                next_turn = turn
                break
                
        if not next_turn:
            logger.info(f"No more pending turns for session {session_id}")
            return None
            
        # End current turn if active
        current_turn = self.current_turns.get(session_id)
        if current_turn and current_turn.status == TurnStatus.ACTIVE:
            await self.end_turn(session_id, "next_turn_started")
            
        # Start the new turn
        next_turn.status = TurnStatus.ACTIVE
        next_turn.started_at = datetime.now(timezone.utc)
        self.current_turns[session_id] = next_turn
        
        # Start turn timer
        await self._start_turn_timer(next_turn)
        
        # Notify callbacks
        await self._notify_turn_callbacks(session_id, "turn_started", next_turn)
        
        logger.info(f"Started turn {next_turn.turn_id} for participant {next_turn.participant_id}")
        return next_turn

    async def end_turn(
        self,
        session_id: str,
        reason: str = "completed",
        content: Optional[str] = None
    ) -> bool:
        """End the current turn in the session"""
        current_turn = self.current_turns.get(session_id)
        if not current_turn or current_turn.status != TurnStatus.ACTIVE:
            return False
            
        current_turn.status = TurnStatus.COMPLETED if reason == "completed" else TurnStatus.INTERRUPTED
        current_turn.ended_at = datetime.now(timezone.utc)
        current_turn.content = content
        current_turn.interrupted_reason = reason if reason != "completed" else None
        
        # Calculate actual speaking time
        if current_turn.started_at:
            duration = (current_turn.ended_at - current_turn.started_at).total_seconds()
            current_turn.actual_time = duration
            
        # Cancel turn timer
        if session_id in self._turn_timers:
            self._turn_timers[session_id].cancel()
            del self._turn_timers[session_id]
            
        # Notify callbacks
        await self._notify_turn_callbacks(session_id, "turn_ended", current_turn)
        
        logger.info(f"Ended turn {current_turn.turn_id}: {reason}")
        return True

    async def skip_turn(self, session_id: str, reason: str = "skipped") -> bool:
        """Skip the current turn"""
        current_turn = self.current_turns.get(session_id)
        if not current_turn or current_turn.status != TurnStatus.ACTIVE:
            return False
            
        current_turn.status = TurnStatus.SKIPPED
        current_turn.ended_at = datetime.now(timezone.utc)
        current_turn.interrupted_reason = reason
        
        # Cancel turn timer
        if session_id in self._turn_timers:
            self._turn_timers[session_id].cancel()
            del self._turn_timers[session_id]
            
        # Notify callbacks
        await self._notify_turn_callbacks(session_id, "turn_skipped", current_turn)
        
        logger.info(f"Skipped turn {current_turn.turn_id}: {reason}")
        return True

    async def request_speaking_turn(
        self,
        session_id: str,
        participant_id: str,
        priority: int = 0
    ) -> bool:
        """Request a speaking turn (for raise-hand mode)"""
        if session_id not in self.speaking_queues:
            return False
            
        queue = self.speaking_queues[session_id]
        if participant_id not in queue:
            queue.append(participant_id)
            logger.info(f"Participant {participant_id} requested speaking turn in session {session_id}")
            return True
        return False

    async def grant_speaking_turn(
        self,
        session_id: str,
        participant_id: str,
        duration: Optional[int] = None
    ) -> Optional[DebateTurn]:
        """Grant a speaking turn to a specific participant (moderator control)"""
        if session_id not in self.session_turns:
            return None
            
        # End current turn if active
        current_turn = self.current_turns.get(session_id)
        if current_turn and current_turn.status == TurnStatus.ACTIVE:
            await self.end_turn(session_id, "moderator_override")
            
        # Create an ad-hoc turn
        turn_id = f"{session_id}-adhoc-{int(time.time())}"
        turn = DebateTurn(
            turn_id=turn_id,
            session_id=session_id,
            participant_id=participant_id,
            round_number=0,  # Ad-hoc turns are round 0
            turn_order=0,
            allocated_time=duration or 60,
            status=TurnStatus.ACTIVE,
            started_at=datetime.now(timezone.utc)
        )
        
        self.session_turns[session_id].append(turn)
        self.current_turns[session_id] = turn
        
        # Start turn timer
        await self._start_turn_timer(turn)
        
        # Remove from speaking queue if present
        if participant_id in self.speaking_queues.get(session_id, []):
            self.speaking_queues[session_id].remove(participant_id)
            
        # Notify callbacks
        await self._notify_turn_callbacks(session_id, "turn_granted", turn)
        
        logger.info(f"Granted speaking turn to {participant_id} in session {session_id}")
        return turn

    def get_current_turn(self, session_id: str) -> Optional[DebateTurn]:
        """Get the current active turn for a session"""
        return self.current_turns.get(session_id)

    def get_next_speakers(self, session_id: str, count: int = 3) -> List[str]:
        """Get the next speakers in the turn order"""
        if session_id not in self.session_turns:
            return []
            
        next_speakers = []
        for turn in self.session_turns[session_id]:
            if turn.status == TurnStatus.PENDING:
                next_speakers.append(turn.participant_id)
                if len(next_speakers) >= count:
                    break
                    
        return next_speakers

    def get_speaking_queue(self, session_id: str) -> List[str]:
        """Get the current speaking queue (for raise-hand mode)"""
        return self.speaking_queues.get(session_id, []).copy()

    def get_turn_statistics(self, session_id: str) -> Dict[str, Any]:
        """Get turn statistics for a session"""
        if session_id not in self.session_turns:
            return {}
            
        turns = self.session_turns[session_id]
        
        total_turns = len(turns)
        completed_turns = len([t for t in turns if t.status == TurnStatus.COMPLETED])
        skipped_turns = len([t for t in turns if t.status == TurnStatus.SKIPPED])
        interrupted_turns = len([t for t in turns if t.status == TurnStatus.INTERRUPTED])
        
        # Calculate average speaking time
        speaking_times = [t.actual_time for t in turns if t.actual_time > 0]
        avg_speaking_time = sum(speaking_times) / len(speaking_times) if speaking_times else 0
        
        # Participant statistics
        participant_stats = {}
        for turn in turns:
            pid = turn.participant_id
            if pid not in participant_stats:
                participant_stats[pid] = {
                    "total_turns": 0,
                    "completed_turns": 0,
                    "total_time": 0.0,
                    "average_time": 0.0
                }
                
            participant_stats[pid]["total_turns"] += 1
            if turn.status == TurnStatus.COMPLETED:
                participant_stats[pid]["completed_turns"] += 1
                participant_stats[pid]["total_time"] += turn.actual_time
                
        # Calculate average times
        for stats in participant_stats.values():
            if stats["completed_turns"] > 0:
                stats["average_time"] = stats["total_time"] / stats["completed_turns"]
        
        return {
            "total_turns": total_turns,
            "completed_turns": completed_turns,
            "skipped_turns": skipped_turns,
            "interrupted_turns": interrupted_turns,
            "average_speaking_time": avg_speaking_time,
            "participant_stats": participant_stats
        }

    def add_turn_callback(
        self,
        session_id: str,
        callback: Callable[[str, str, DebateTurn], None]
    ) -> None:
        """Add a callback for turn events"""
        if session_id not in self.turn_callbacks:
            self.turn_callbacks[session_id] = []
        self.turn_callbacks[session_id].append(callback)

    def remove_turn_callback(
        self,
        session_id: str,
        callback: Callable[[str, str, DebateTurn], None]
    ) -> None:
        """Remove a turn callback"""
        if session_id in self.turn_callbacks:
            if callback in self.turn_callbacks[session_id]:
                self.turn_callbacks[session_id].remove(callback)

    async def cleanup_session(self, session_id: str) -> bool:
        """Clean up turn management for a session"""
        if session_id in self._turn_timers:
            self._turn_timers[session_id].cancel()
            del self._turn_timers[session_id]
            
        self.session_turns.pop(session_id, None)
        self.current_turns.pop(session_id, None)
        self.turn_callbacks.pop(session_id, None)
        self.speaking_queues.pop(session_id, None)
        
        logger.info(f"Cleaned up turn management for session {session_id}")
        return True

    def _order_participants(
        self,
        participants: List[str],
        speaking_order: SpeakingOrder,
        round_number: int
    ) -> List[str]:
        """Order participants based on speaking strategy"""
        if not participants:
            return []
            
        if speaking_order == SpeakingOrder.ROUND_ROBIN:
            # Rotate starting position each round
            start_index = (round_number - 1) % len(participants)
            return participants[start_index:] + participants[:start_index]
            
        elif speaking_order == SpeakingOrder.RANDOM:
            import random
            ordered = participants.copy()
            random.shuffle(ordered)
            return ordered
            
        elif speaking_order == SpeakingOrder.PRIORITY_BASED:
            # For now, just use round robin
            # TODO: Implement priority-based ordering
            return participants
            
        else:
            return participants

    async def _start_turn_timer(self, turn: DebateTurn) -> None:
        """Start a timer for the current turn"""
        async def timer_callback():
            try:
                await asyncio.sleep(turn.allocated_time)
                if turn.status == TurnStatus.ACTIVE:
                    await self.end_turn(turn.session_id, "time_expired")
            except asyncio.CancelledError:
                pass
                
        task = asyncio.create_task(timer_callback())
        self._turn_timers[turn.session_id] = task

    async def _notify_turn_callbacks(
        self,
        session_id: str,
        event_type: str,
        turn: DebateTurn
    ) -> None:
        """Notify all registered callbacks about turn events"""
        callbacks = self.turn_callbacks.get(session_id, [])
        for callback in callbacks:
            try:
                await callback(session_id, event_type, turn)
            except Exception as e:
                logger.error(f"Turn callback error: {e}")
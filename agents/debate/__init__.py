"""
ATLAS Phase 4 - Live Debate Mode (TEAM-03)

Enables structured collaborative discussions between multiple agents.
Provides debate orchestration, turn management, and consensus building.
"""

from .debate_orchestrator import DebateOrchestrator, DebateSession, DebateStatus, DebateFormat
from .turn_manager import TurnManager, DebateTurn, SpeakingOrder, TurnStatus
from .moderator import Moderator, ModerationAction, ModerationSeverity
from .consensus_builder import ConsensusBuilder, ConsensusResult, ConsensusMethod, ConsensusStatus

__all__ = [
    "DebateOrchestrator",
    "DebateSession", 
    "DebateStatus",
    "DebateFormat",
    "TurnManager",
    "DebateTurn",
    "SpeakingOrder",
    "TurnStatus",
    "Moderator",
    "ModerationAction",
    "ModerationSeverity",
    "ConsensusBuilder",
    "ConsensusResult",
    "ConsensusMethod",
    "ConsensusStatus"
]
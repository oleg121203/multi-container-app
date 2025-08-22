"""
Consensus Builder - Facilitates agreement and decision making for ATLAS Phase 4

Helps multi-agent teams reach consensus through structured decision-making processes.
Analyzes opinions, identifies common ground, and guides towards agreement.
"""

import asyncio
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ConsensusMethod(str, Enum):
    """Methods for reaching consensus"""
    UNANIMOUS = "unanimous"  # All participants must agree
    MAJORITY = "majority"  # Simple majority vote
    SUPERMAJORITY = "supermajority"  # 2/3 or 3/4 majority
    WEIGHTED = "weighted"  # Weighted voting based on expertise
    ITERATIVE = "iterative"  # Multiple rounds of discussion and voting


class ConsensusStatus(str, Enum):
    """Status of consensus building process"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    REACHED = "reached"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class Opinion:
    """Represents a participant's opinion"""
    participant_id: str
    position: str  # "agree", "disagree", "neutral"
    confidence: float  # 0.0 to 1.0
    reasoning: str
    alternatives: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Proposal:
    """A proposal for consensus"""
    proposal_id: str
    session_id: str
    author_id: str
    title: str
    description: str
    options: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    deadline: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Vote:
    """A vote on a proposal"""
    vote_id: str
    proposal_id: str
    participant_id: str
    choice: str  # The selected option or "yes"/"no"
    weight: float = 1.0
    reasoning: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ConsensusResult(BaseModel):
    """Result of a consensus building process"""
    proposal_id: str
    session_id: str
    status: ConsensusStatus
    method: ConsensusMethod
    final_decision: Optional[str] = None
    support_level: float = 0.0  # 0.0 to 1.0
    participant_agreement: Dict[str, str] = {}  # participant_id -> agreement level
    reasoning_summary: Optional[str] = None
    alternatives_considered: List[str] = []
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = {}

    class Config:
        arbitrary_types_allowed = True


class ConsensusBuilder:
    """
    Facilitates consensus building and decision making
    
    Guides multi-agent teams through structured decision-making processes.
    Analyzes different viewpoints and helps find common ground.
    """
    
    def __init__(self):
        """Initialize the consensus builder"""
        self.session_proposals: Dict[str, List[Proposal]] = {}
        self.session_opinions: Dict[str, Dict[str, List[Opinion]]] = {}  # session -> proposal -> opinions
        self.session_votes: Dict[str, Dict[str, List[Vote]]] = {}  # session -> proposal -> votes
        self.consensus_results: Dict[str, List[ConsensusResult]] = {}
        self._consensus_stats = {
            "total_proposals": 0,
            "successful_consensus": 0,
            "failed_consensus": 0,
            "average_time_to_consensus": 0.0,
            "consensus_rate": 0.0
        }
        
        logger.info("ConsensusBuilder initialized")

    def initialize_session(self, session_id: str) -> None:
        """Initialize consensus building for a session"""
        self.session_proposals[session_id] = []
        self.session_opinions[session_id] = {}
        self.session_votes[session_id] = {}
        self.consensus_results[session_id] = []
        
        logger.info(f"Initialized consensus building for session {session_id}")

    async def create_proposal(
        self,
        session_id: str,
        author_id: str,
        title: str,
        description: str,
        options: Optional[List[str]] = None,
        deadline_minutes: Optional[int] = None
    ) -> Proposal:
        """Create a new proposal for consensus"""
        proposal_id = f"prop_{session_id}_{int(datetime.now().timestamp())}"
        
        deadline = None
        if deadline_minutes:
            deadline = datetime.now(timezone.utc).replace(
                minute=datetime.now().minute + deadline_minutes
            )
        
        proposal = Proposal(
            proposal_id=proposal_id,
            session_id=session_id,
            author_id=author_id,
            title=title,
            description=description,
            options=options or ["agree", "disagree"],
            deadline=deadline
        )
        
        if session_id not in self.session_proposals:
            self.initialize_session(session_id)
            
        self.session_proposals[session_id].append(proposal)
        self.session_opinions[session_id][proposal_id] = []
        self.session_votes[session_id][proposal_id] = []
        
        self._consensus_stats["total_proposals"] += 1
        
        logger.info(f"Created proposal {proposal_id}: {title}")
        return proposal

    async def submit_opinion(
        self,
        session_id: str,
        proposal_id: str,
        participant_id: str,
        position: str,
        confidence: float,
        reasoning: str,
        alternatives: Optional[List[str]] = None
    ) -> bool:
        """Submit an opinion on a proposal"""
        if (session_id not in self.session_opinions or 
            proposal_id not in self.session_opinions[session_id]):
            logger.warning(f"Proposal {proposal_id} not found in session {session_id}")
            return False
        
        opinion = Opinion(
            participant_id=participant_id,
            position=position,
            confidence=max(0.0, min(1.0, confidence)),
            reasoning=reasoning,
            alternatives=alternatives or []
        )
        
        # Remove any existing opinion from this participant
        opinions = self.session_opinions[session_id][proposal_id]
        self.session_opinions[session_id][proposal_id] = [
            op for op in opinions if op.participant_id != participant_id
        ]
        
        # Add new opinion
        self.session_opinions[session_id][proposal_id].append(opinion)
        
        logger.info(f"Submitted opinion from {participant_id} on proposal {proposal_id}: {position}")
        return True

    async def submit_vote(
        self,
        session_id: str,
        proposal_id: str,
        participant_id: str,
        choice: str,
        weight: float = 1.0,
        reasoning: Optional[str] = None
    ) -> bool:
        """Submit a vote on a proposal"""
        if (session_id not in self.session_votes or 
            proposal_id not in self.session_votes[session_id]):
            logger.warning(f"Proposal {proposal_id} not found in session {session_id}")
            return False
        
        vote_id = f"vote_{proposal_id}_{participant_id}_{int(datetime.now().timestamp())}"
        
        vote = Vote(
            vote_id=vote_id,
            proposal_id=proposal_id,
            participant_id=participant_id,
            choice=choice,
            weight=max(0.0, weight),
            reasoning=reasoning
        )
        
        # Remove any existing vote from this participant
        votes = self.session_votes[session_id][proposal_id]
        self.session_votes[session_id][proposal_id] = [
            v for v in votes if v.participant_id != participant_id
        ]
        
        # Add new vote
        self.session_votes[session_id][proposal_id].append(vote)
        
        logger.info(f"Submitted vote from {participant_id} on proposal {proposal_id}: {choice}")
        return True

    async def check_consensus(
        self,
        session_id: str,
        proposal_id: str,
        method: ConsensusMethod = ConsensusMethod.MAJORITY,
        participants: Optional[List[str]] = None
    ) -> ConsensusResult:
        """Check if consensus has been reached on a proposal"""
        if (session_id not in self.session_votes or 
            proposal_id not in self.session_votes[session_id]):
            return ConsensusResult(
                proposal_id=proposal_id,
                session_id=session_id,
                status=ConsensusStatus.FAILED,
                method=method
            )
        
        votes = self.session_votes[session_id][proposal_id]
        opinions = self.session_opinions[session_id].get(proposal_id, [])
        
        if not votes and not opinions:
            return ConsensusResult(
                proposal_id=proposal_id,
                session_id=session_id,
                status=ConsensusStatus.PENDING,
                method=method
            )
        
        # Analyze votes and opinions
        result = await self._analyze_consensus(
            proposal_id, session_id, votes, opinions, method, participants
        )
        
        # Store result
        if session_id not in self.consensus_results:
            self.consensus_results[session_id] = []
        self.consensus_results[session_id].append(result)
        
        # Update statistics
        if result.status == ConsensusStatus.REACHED:
            self._consensus_stats["successful_consensus"] += 1
        elif result.status == ConsensusStatus.FAILED:
            self._consensus_stats["failed_consensus"] += 1
            
        self._update_consensus_rate()
        
        return result

    async def identify_common_ground(
        self,
        session_id: str,
        proposal_id: str
    ) -> Dict[str, Any]:
        """Identify areas of agreement and disagreement"""
        if (session_id not in self.session_opinions or 
            proposal_id not in self.session_opinions[session_id]):
            return {"common_ground": [], "disagreements": [], "alternatives": []}
        
        opinions = self.session_opinions[session_id][proposal_id]
        
        # Group by position
        positions = {}
        all_alternatives = set()
        
        for opinion in opinions:
            pos = opinion.position
            if pos not in positions:
                positions[pos] = []
            positions[pos].append(opinion)
            all_alternatives.update(opinion.alternatives)
        
        # Find common themes in reasoning
        common_themes = self._extract_common_themes(opinions)
        
        # Identify strong disagreements
        disagreements = []
        if len(positions) > 1:
            for pos1, opinions1 in positions.items():
                for pos2, opinions2 in positions.items():
                    if pos1 != pos2:
                        disagreements.append({
                            "position1": pos1,
                            "position2": pos2,
                            "supporters1": [op.participant_id for op in opinions1],
                            "supporters2": [op.participant_id for op in opinions2]
                        })
        
        return {
            "common_ground": common_themes,
            "disagreements": disagreements,
            "alternatives": list(all_alternatives),
            "position_distribution": {pos: len(ops) for pos, ops in positions.items()}
        }

    async def suggest_compromise(
        self,
        session_id: str,
        proposal_id: str
    ) -> Optional[str]:
        """Suggest a compromise based on different opinions"""
        common_ground = await self.identify_common_ground(session_id, proposal_id)
        
        if not common_ground["common_ground"]:
            return None
        
        # Simple compromise suggestion based on common themes
        themes = common_ground["common_ground"]
        alternatives = common_ground["alternatives"]
        
        if len(themes) >= 2:
            return f"Consider a solution that addresses: {', '.join(themes[:2])}"
        elif alternatives:
            return f"Alternative approaches to consider: {', '.join(list(alternatives)[:2])}"
        
        return "Consider finding middle ground between the different positions"

    async def facilitate_discussion(
        self,
        session_id: str,
        proposal_id: str
    ) -> List[str]:
        """Generate discussion prompts to help reach consensus"""
        analysis = await self.identify_common_ground(session_id, proposal_id)
        prompts = []
        
        if analysis["disagreements"]:
            prompts.append("What are the main concerns behind the different positions?")
            prompts.append("Are there any shared goals we can focus on?")
        
        if analysis["alternatives"]:
            prompts.append("Which alternative approaches might address everyone's concerns?")
        
        if analysis["common_ground"]:
            prompts.append(f"Since we agree on {', '.join(analysis['common_ground'][:2])}, how can we build on this?")
        
        if not prompts:
            prompts = [
                "What would need to change for everyone to feel comfortable with this proposal?",
                "Are there any deal-breakers we should address first?",
                "What information do we need to make a better decision?"
            ]
        
        return prompts

    def get_proposal(self, session_id: str, proposal_id: str) -> Optional[Proposal]:
        """Get a specific proposal"""
        proposals = self.session_proposals.get(session_id, [])
        for proposal in proposals:
            if proposal.proposal_id == proposal_id:
                return proposal
        return None

    def list_session_proposals(self, session_id: str) -> List[Proposal]:
        """List all proposals for a session"""
        return self.session_proposals.get(session_id, []).copy()

    def get_consensus_statistics(self) -> Dict[str, Any]:
        """Get consensus building statistics"""
        return self._consensus_stats.copy()

    async def cleanup_session(self, session_id: str) -> None:
        """Clean up consensus data for a session"""
        self.session_proposals.pop(session_id, None)
        self.session_opinions.pop(session_id, None)
        self.session_votes.pop(session_id, None)
        self.consensus_results.pop(session_id, None)
        
        logger.info(f"Cleaned up consensus data for session {session_id}")

    async def _analyze_consensus(
        self,
        proposal_id: str,
        session_id: str,
        votes: List[Vote],
        opinions: List[Opinion],
        method: ConsensusMethod,
        participants: Optional[List[str]]
    ) -> ConsensusResult:
        """Analyze votes and opinions to determine consensus"""
        if not votes:
            return ConsensusResult(
                proposal_id=proposal_id,
                session_id=session_id,
                status=ConsensusStatus.PENDING,
                method=method
            )
        
        # Count votes
        vote_counts = {}
        total_weight = 0
        participant_choices = {}
        
        for vote in votes:
            choice = vote.choice
            weight = vote.weight
            
            if choice not in vote_counts:
                vote_counts[choice] = 0
            vote_counts[choice] += weight
            total_weight += weight
            participant_choices[vote.participant_id] = choice
        
        # Determine result based on method
        consensus_reached = False
        winning_choice = None
        support_level = 0.0
        
        if vote_counts:
            # Find the choice with most support
            winning_choice = max(vote_counts.keys(), key=lambda k: vote_counts[k])
            support_level = vote_counts[winning_choice] / total_weight if total_weight > 0 else 0
            
            if method == ConsensusMethod.UNANIMOUS:
                consensus_reached = len(vote_counts) == 1
            elif method == ConsensusMethod.MAJORITY:
                consensus_reached = support_level > 0.5
            elif method == ConsensusMethod.SUPERMAJORITY:
                consensus_reached = support_level >= 0.67
            elif method == ConsensusMethod.WEIGHTED:
                # Same as majority for now
                consensus_reached = support_level > 0.5
        
        status = ConsensusStatus.REACHED if consensus_reached else ConsensusStatus.FAILED
        
        # Generate reasoning summary
        reasoning_summary = self._generate_reasoning_summary(opinions)
        
        # Get alternatives from opinions
        alternatives = []
        for opinion in opinions:
            alternatives.extend(opinion.alternatives)
        alternatives = list(set(alternatives))
        
        return ConsensusResult(
            proposal_id=proposal_id,
            session_id=session_id,
            status=status,
            method=method,
            final_decision=winning_choice if consensus_reached else None,
            support_level=support_level,
            participant_agreement=participant_choices,
            reasoning_summary=reasoning_summary,
            alternatives_considered=alternatives
        )

    def _extract_common_themes(self, opinions: List[Opinion]) -> List[str]:
        """Extract common themes from opinion reasoning"""
        # Simple keyword-based theme extraction
        themes = {}
        
        for opinion in opinions:
            words = opinion.reasoning.lower().split()
            # Look for important keywords
            keywords = [word for word in words if len(word) > 4 and word.isalpha()]
            
            for keyword in keywords:
                if keyword not in themes:
                    themes[keyword] = 0
                themes[keyword] += 1
        
        # Return themes mentioned by multiple participants
        common_themes = [
            theme for theme, count in themes.items() 
            if count >= max(2, len(opinions) // 2)
        ]
        
        return sorted(common_themes, key=lambda t: themes[t], reverse=True)[:5]

    def _generate_reasoning_summary(self, opinions: List[Opinion]) -> str:
        """Generate a summary of the reasoning provided"""
        if not opinions:
            return "No reasoning provided"
        
        # Group by position
        position_reasoning = {}
        for opinion in opinions:
            pos = opinion.position
            if pos not in position_reasoning:
                position_reasoning[pos] = []
            position_reasoning[pos].append(opinion.reasoning)
        
        summary_parts = []
        for position, reasonings in position_reasoning.items():
            count = len(reasonings)
            summary_parts.append(f"{count} participant(s) {position}")
        
        return "; ".join(summary_parts)

    def _update_consensus_rate(self) -> None:
        """Update consensus success rate"""
        total = self._consensus_stats["successful_consensus"] + self._consensus_stats["failed_consensus"]
        if total > 0:
            self._consensus_stats["consensus_rate"] = self._consensus_stats["successful_consensus"] / total
"""
Test TEAM-03: Live Debate Mode functionality
"""

import pytest
import asyncio
from agents.debate import (
    DebateOrchestrator, DebateSession, DebateStatus, DebateFormat,
    TurnManager, SpeakingOrder,
    Moderator, ModerationAction,
    ConsensusBuilder, ConsensusMethod
)
from agents.registry.agent_registry import AgentRegistry, AgentInfo, AgentCapability


@pytest.fixture
def sample_agents():
    """Create sample agents for testing"""
    agents = [
        AgentInfo(
            agent_id="agent_1",
            name="Logic Agent",
            description="An agent specialized in logical reasoning and analysis",
            capabilities=[
                AgentCapability(name="logical_reasoning", description="Logical analysis")
            ]
        ),
        AgentInfo(
            agent_id="agent_2", 
            name="Creative Agent",
            description="An agent focused on creative thinking and innovative solutions",
            capabilities=[
                AgentCapability(name="creative_thinking", description="Creative solutions")
            ]
        ),
        AgentInfo(
            agent_id="agent_3",
            name="Security Agent",
            description="An agent specialized in security monitoring and analysis",
            capabilities=[
                AgentCapability(name="security_monitoring", description="Security analysis")
            ]
        )
    ]
    return agents


@pytest.mark.asyncio
async def test_debate_orchestrator_basic(sample_agents):
    """Test basic debate orchestrator functionality"""
    registry = AgentRegistry()
    orchestrator = DebateOrchestrator(registry)
    
    # Register sample agents in the registry
    for agent in sample_agents:
        await registry.register_agent(agent)
    
    # Create a debate session
    session = await orchestrator.create_debate_session(
        topic="Should AI agents have voting rights?",
        format=DebateFormat.ROUND_ROBIN,
        max_participants=3
    )
    
    assert session.topic == "Should AI agents have voting rights?"
    assert session.format == DebateFormat.ROUND_ROBIN
    assert session.status == DebateStatus.PENDING
    assert session.session_id in orchestrator.active_sessions
    
    # Add participants
    for agent in sample_agents:
        success = await orchestrator.add_participant(session.session_id, agent.agent_id)
        assert success
    
    assert len(session.participants) == 3
    
    # Start debate
    success = await orchestrator.start_debate(session.session_id)
    assert success
    assert session.status == DebateStatus.ACTIVE
    
    # Add messages
    await orchestrator.add_message(
        session.session_id,
        "agent_1",
        "I believe AI agents should have voting rights if they demonstrate rational decision-making.",
        "statement"
    )
    
    await orchestrator.add_message(
        session.session_id,
        "agent_2", 
        "That's an interesting perspective. What about the ethical implications?",
        "question"
    )
    
    assert len(session.messages) == 2
    assert session.participants["agent_1"].contributions == 1
    assert session.participants["agent_2"].contributions == 1


@pytest.mark.asyncio 
async def test_turn_manager_functionality():
    """Test turn manager speaking order and timing"""
    turn_manager = TurnManager()
    
    participants = ["agent_1", "agent_2", "agent_3"]
    session_id = "test_session"
    
    # Initialize turns
    success = await turn_manager.initialize_session_turns(
        session_id=session_id,
        participants=participants,
        speaking_order=SpeakingOrder.ROUND_ROBIN,
        turn_duration=30,
        max_rounds=2
    )
    assert success
    
    # Check turns were created
    turns = turn_manager.session_turns[session_id]
    assert len(turns) == 6  # 3 participants * 2 rounds
    
    # Start first turn
    turn = await turn_manager.start_next_turn(session_id)
    assert turn is not None
    assert turn.participant_id == "agent_1"
    assert turn.round_number == 1
    
    # End turn
    success = await turn_manager.end_turn(session_id, "completed", "Test message")
    assert success
    
    # Start next turn
    turn = await turn_manager.start_next_turn(session_id)
    assert turn is not None
    assert turn.participant_id == "agent_2"
    
    # Get next speakers
    next_speakers = turn_manager.get_next_speakers(session_id, 2)
    assert len(next_speakers) >= 1


@pytest.mark.asyncio
async def test_moderator_functionality():
    """Test AI moderator capabilities"""
    moderator = Moderator()
    
    session_id = "test_session"
    participants = ["agent_1", "agent_2"]
    
    # Initialize moderation
    moderator.initialize_session_moderation(session_id, participants)
    
    # Test message moderation
    events = await moderator.moderate_message(
        session_id,
        "agent_1",
        "This is a reasonable statement about the topic.",
        "statement"
    )
    
    # Should not trigger any moderation events for normal message
    assert len(events) == 0
    
    # Test behavior tracking
    behavior = moderator.get_participant_behavior(session_id, "agent_1")
    assert behavior is not None
    assert behavior.message_count == 1
    
    # Test session health check
    health = await moderator.check_session_health(session_id)
    assert "status" in health
    assert "suggestions" in health


@pytest.mark.asyncio
async def test_consensus_builder_functionality():
    """Test consensus building and voting"""
    consensus_builder = ConsensusBuilder()
    
    session_id = "test_session"
    consensus_builder.initialize_session(session_id)
    
    # Create a proposal
    proposal = await consensus_builder.create_proposal(
        session_id=session_id,
        author_id="agent_1",
        title="Implement new security protocol",
        description="Should we implement enhanced security measures?",
        options=["yes", "no", "modify"]
    )
    
    assert proposal.title == "Implement new security protocol"
    assert len(proposal.options) == 3
    
    # Submit opinions
    success = await consensus_builder.submit_opinion(
        session_id,
        proposal.proposal_id,
        "agent_1",
        "agree",
        0.8,
        "Security is paramount for our system"
    )
    assert success
    
    success = await consensus_builder.submit_opinion(
        session_id,
        proposal.proposal_id,
        "agent_2",
        "disagree",
        0.6,
        "Might impact performance too much"
    )
    assert success
    
    # Submit votes
    await consensus_builder.submit_vote(
        session_id,
        proposal.proposal_id,
        "agent_1",
        "yes",
        1.0,
        "Strong support for security"
    )
    
    await consensus_builder.submit_vote(
        session_id,
        proposal.proposal_id,
        "agent_2", 
        "modify",
        1.0,
        "Need a balanced approach"
    )
    
    # Check for consensus
    result = await consensus_builder.check_consensus(
        session_id,
        proposal.proposal_id,
        ConsensusMethod.MAJORITY
    )
    
    assert result.proposal_id == proposal.proposal_id
    # Should fail consensus since votes are split
    assert result.status in ["failed", "pending"]
    
    # Test common ground identification
    common_ground = await consensus_builder.identify_common_ground(
        session_id,
        proposal.proposal_id
    )
    
    assert "common_ground" in common_ground
    assert "disagreements" in common_ground


@pytest.mark.asyncio
async def test_integrated_debate_flow(sample_agents):
    """Test integrated debate workflow"""
    # Initialize components
    registry = AgentRegistry()
    orchestrator = DebateOrchestrator(registry)
    turn_manager = TurnManager()
    moderator = Moderator()
    consensus_builder = ConsensusBuilder()
    
    # Register sample agents in the registry
    for agent in sample_agents:
        await registry.register_agent(agent)
    
    # Create and start debate
    session = await orchestrator.create_debate_session(
        topic="Best approach for multi-agent coordination",
        format=DebateFormat.ROUND_ROBIN
    )
    
    # Add participants
    for agent in sample_agents:
        await orchestrator.add_participant(session.session_id, agent.agent_id)
    
    # Initialize other components
    participants = list(session.participants.keys())
    await turn_manager.initialize_session_turns(
        session.session_id,
        participants,
        SpeakingOrder.ROUND_ROBIN,
        turn_duration=60,
        max_rounds=1
    )
    
    moderator.initialize_session_moderation(session.session_id, participants)
    consensus_builder.initialize_session(session.session_id)
    
    # Start debate
    await orchestrator.start_debate(session.session_id)
    
    # Simulate debate flow
    turn = await turn_manager.start_next_turn(session.session_id)
    assert turn is not None
    
    # Agent speaks
    message = "I propose we use event-driven coordination patterns."
    await orchestrator.add_message(
        session.session_id,
        turn.participant_id,
        message,
        "statement"
    )
    
    # Moderate the message
    events = await moderator.moderate_message(
        session.session_id,
        turn.participant_id,
        message,
        "statement"
    )
    
    # End turn
    await turn_manager.end_turn(session.session_id, "completed", message)
    
    # Create proposal for consensus
    proposal = await consensus_builder.create_proposal(
        session.session_id,
        turn.participant_id,
        "Coordination Pattern Decision",
        "Should we adopt event-driven coordination?",
        ["yes", "no", "hybrid"]
    )
    
    assert proposal is not None
    assert session.status == DebateStatus.ACTIVE
    assert len(session.messages) == 1
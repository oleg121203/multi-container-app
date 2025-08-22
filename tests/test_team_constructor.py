"""
Simple test for Phase 4 Team Constructor functionality
"""

import pytest
import asyncio
import tempfile
import json
from pathlib import Path

from agents.registry.agent_registry import AgentRegistry, AgentInfo, AgentCapability, AgentStatus
from agents.registry.team_constructor import TeamConstructor
from agents.registry.capability_matcher import TaskRequirement


@pytest.mark.asyncio
async def test_team_constructor_basic():
    """Test basic team constructor functionality"""
    # Create a temporary config file with test agents
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        test_config = {
            "agents": [
                {
                    "agent_id": "ui-agent",
                    "name": "UI Agent",
                    "description": "User interface specialist",
                    "capabilities": [
                        {"name": "user_interface", "description": "UI capability"},
                        {"name": "rag_search", "description": "Search capability"}
                    ]
                },
                {
                    "agent_id": "orchestrator-agent", 
                    "name": "Orchestrator Agent",
                    "description": "Task orchestration specialist",
                    "capabilities": [
                        {"name": "task_orchestration", "description": "Orchestration capability"},
                        {"name": "task_planning", "description": "Planning capability"}
                    ]
                },
                {
                    "agent_id": "security-agent",
                    "name": "Security Agent", 
                    "description": "Security monitoring specialist",
                    "capabilities": [
                        {"name": "security_monitoring", "description": "Security capability"},
                        {"name": "compliance_checking", "description": "Compliance capability"}
                    ]
                }
            ]
        }
        json.dump(test_config, f)
        f.flush()
        
        try:
            # Initialize components
            registry = AgentRegistry(registry_path=f.name)
            await registry.initialize()
            
            # Set agents to healthy status
            for agent_id in registry.agents:
                await registry.update_agent_status(agent_id, AgentStatus.HEALTHY, 0.1)
            
            team_constructor = TeamConstructor(registry)
            
            # Test task analysis
            requirements = await team_constructor.analyze_task_requirements(
                "Create a user interface with security monitoring"
            )
            assert len(requirements) > 0
            assert any(req.capability == "user_interface" for req in requirements)
            assert any(req.capability == "security_monitoring" for req in requirements)
            
            # Test team formation
            team = await team_constructor.form_team("Create a secure user interface")
            assert team is not None
            assert len(team.members) > 0
            assert team.status.value == "ready"
            
            # Test team info
            team_info = await team_constructor.get_team_info(team.team_id)
            assert team_info is not None
            assert team_info.team_id == team.team_id
            
            # Test active teams listing
            active_teams = team_constructor.list_active_teams()
            assert len(active_teams) == 1
            assert active_teams[0].team_id == team.team_id
            
            # Test statistics
            stats = team_constructor.get_formation_statistics()
            assert stats["total_active_teams"] == 1
            assert stats["average_team_size"] >= 1
            
            # Test suggestions
            suggestions = await team_constructor.suggest_team_improvements(team.team_id)
            assert isinstance(suggestions, list)
            assert len(suggestions) > 0
            
            # Test team disbanding
            result = await team_constructor.disband_team(team.team_id)
            assert result is True
            
            # Verify team is no longer active
            active_teams = team_constructor.list_active_teams()
            assert len(active_teams) == 0
            
            print("✅ Team Constructor basic functionality test - PASSED!")
            
        finally:
            # Cleanup
            Path(f.name).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_team_formation_scenarios():
    """Test different team formation scenarios"""
    
    registry = AgentRegistry("./config/agents.json")
    await registry.initialize()
    
    # Set agents to healthy status
    for agent_id in registry.agents:
        await registry.update_agent_status(agent_id, AgentStatus.HEALTHY, 0.1)
    
    team_constructor = TeamConstructor(registry)
    
    # Test simple UI task
    ui_team = await team_constructor.form_team("Create a user interface for search")
    assert ui_team is not None
    assert any("user_interface" in member.capabilities_assigned for member in ui_team.members)
    
    # Test security task
    security_team = await team_constructor.form_team("Monitor system security and compliance")
    assert security_team is not None
    assert any("security_monitoring" in member.capabilities_assigned for member in security_team.members)
    
    # Clean up
    if ui_team:
        await team_constructor.disband_team(ui_team.team_id)
    if security_team:
        await team_constructor.disband_team(security_team.team_id)
    
    print("✅ Team formation scenarios test - PASSED!")


if __name__ == "__main__":
    asyncio.run(test_team_constructor_basic())
    asyncio.run(test_team_formation_scenarios())
    print("\n🎉 All Team Constructor tests passed!")
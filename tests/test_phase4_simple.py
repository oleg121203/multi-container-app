"""
Simple functional tests for Phase 4 Agent Registry
Tests core functionality without complex async fixtures
"""

import pytest
import asyncio
import tempfile
import json
from pathlib import Path

from agents.registry.agent_registry import AgentRegistry, AgentInfo, AgentCapability, AgentStatus
from agents.registry.capability_matcher import CapabilityMatcher, TaskRequirement


@pytest.mark.asyncio
async def test_agent_registry_basic_functionality():
    """Test basic agent registry functionality"""
    # Create a temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        test_config = {
            "agents": [
                {
                    "agent_id": "test-agent-1",
                    "name": "Test Agent 1",
                    "description": "Test agent for unit tests",
                    "capabilities": [
                        {
                            "name": "test_capability",
                            "description": "A test capability",
                            "parameters": {"param1": "value1"}
                        }
                    ]
                }
            ]
        }
        json.dump(test_config, f)
        f.flush()
        
        try:
            # Initialize registry
            registry = AgentRegistry(registry_path=f.name)
            await registry.initialize()
            
            # Test initial state
            assert len(registry.agents) == 1
            assert "test-agent-1" in registry.agents
            assert "test_capability" in registry.capabilities_index
            
            # Test agent registration
            capability = AgentCapability(name="new_capability", description="A new capability")
            agent_info = AgentInfo(
                agent_id="test-agent-2",
                name="Test Agent 2", 
                description="Another test agent",
                capabilities=[capability]
            )
            
            result = await registry.register_agent(agent_info)
            assert result is True
            assert len(registry.agents) == 2
            assert "test-agent-2" in registry.agents
            
            # Test capability lookup
            agents = await registry.get_agents_by_capability("new_capability")
            assert len(agents) == 1
            assert agents[0].agent_id == "test-agent-2"
            
            # Test status update
            result = await registry.update_agent_status("test-agent-1", AgentStatus.HEALTHY, 0.5)
            assert result is True
            
            agent = await registry.get_agent("test-agent-1")
            assert agent.status == AgentStatus.HEALTHY
            assert agent.load_factor == 0.5
            
            print("✅ Agent Registry basic functionality test - PASSED!")
            
        finally:
            # Cleanup
            Path(f.name).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_capability_matcher_functionality():
    """Test capability matcher functionality"""
    matcher = CapabilityMatcher()
    
    # Create test agents
    capability1 = AgentCapability(name="web_scraping", description="Web scraping capability")
    capability2 = AgentCapability(name="data_analysis", description="Data analysis capability")
    
    agent1 = AgentInfo(
        agent_id="agent1",
        name="Web Agent",
        description="Web scraping agent",
        capabilities=[capability1],
        status=AgentStatus.HEALTHY,
        load_factor=0.3
    )
    
    agent2 = AgentInfo(
        agent_id="agent2", 
        name="Analysis Agent",
        description="Data analysis agent",
        capabilities=[capability2],
        status=AgentStatus.HEALTHY,
        load_factor=0.7
    )
    
    agent3 = AgentInfo(
        agent_id="agent3",
        name="Multi Agent",
        description="Multi-capability agent",
        capabilities=[capability1, capability2],
        status=AgentStatus.IDLE,
        load_factor=0.1
    )
    
    agents = [agent1, agent2, agent3]
    
    # Test matching
    requirements = [
        TaskRequirement(capability="web_scraping", required=True, priority=5),
        TaskRequirement(capability="data_analysis", required=False, priority=3)
    ]
    
    matches = await matcher.find_matching_agents(requirements, agents)
    assert len(matches) > 0
    
    # Agent3 should score highest (has both capabilities and is idle)
    assert matches[0].agent.agent_id == "agent3"
    assert "web_scraping" in matches[0].matched_capabilities
    assert "data_analysis" in matches[0].matched_capabilities
    
    # Test single capability search
    result = await matcher.find_best_agent_for_capability("web_scraping", agents)
    assert result is not None
    assert result.agent.agent_id in ["agent1", "agent3"]
    
    print("✅ Capability Matcher functionality test - PASSED!")


@pytest.mark.asyncio 
async def test_integration_with_existing_config():
    """Test integration with the actual agents.json config"""
    registry = AgentRegistry("./config/agents.json")
    await registry.initialize()
    
    # Should load the predefined agents
    assert len(registry.agents) >= 3  # llm1, llm2, llm3 agents
    
    # Check that specific agents are loaded
    expected_agents = ["llm1-agent", "llm2-agent", "llm3-agent"]
    for agent_id in expected_agents:
        assert agent_id in registry.agents
        agent = registry.agents[agent_id]
        assert len(agent.capabilities) > 0
    
    # Test capability index
    assert len(registry.capabilities_index) > 0
    
    # Test getting agents by capability
    ui_agents = await registry.get_agents_by_capability("user_interface")
    assert len(ui_agents) >= 1
    
    orchestration_agents = await registry.get_agents_by_capability("task_orchestration")
    assert len(orchestration_agents) >= 1
    
    print("✅ Integration with existing config test - PASSED!")


def test_load_balancer_basic():
    """Test basic load balancer functionality (synchronous test)"""
    from unittest.mock import MagicMock, AsyncMock
    from agents.registry.load_balancer import LoadBalancer, LoadBalancingStrategy
    
    registry = MagicMock()
    load_balancer = LoadBalancer(registry)
    
    # Test strategy setting
    load_balancer.set_strategy(LoadBalancingStrategy.LEAST_LOADED)
    assert load_balancer.strategy == LoadBalancingStrategy.LEAST_LOADED
    
    # Test agent weight setting
    load_balancer.set_agent_weight("agent1", 2.0)
    assert load_balancer.agent_weights["agent1"] == 2.0
    
    print("✅ Load Balancer basic functionality test - PASSED!")


if __name__ == "__main__":
    # Run the async tests
    asyncio.run(test_agent_registry_basic_functionality())
    asyncio.run(test_capability_matcher_functionality())
    asyncio.run(test_integration_with_existing_config())
    test_load_balancer_basic()
    print("\n🎉 All Phase 4 Agent Registry tests passed!")
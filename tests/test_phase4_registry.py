"""
Tests for ATLAS Phase 4 Agent Registry implementation

Tests the core functionality of the Agent Registry, Capability Matcher,
Health Monitor, and Load Balancer components.
"""

import pytest
import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from agents.registry.agent_registry import (
    AgentRegistry, AgentInfo, AgentCapability, AgentStatus
)
from agents.registry.capability_matcher import (
    CapabilityMatcher, TaskRequirement, MatchResult
)
from agents.registry.health_monitor import HealthMonitor, HealthCheckResult
from agents.registry.load_balancer import LoadBalancer, TaskAssignment, LoadBalancingStrategy


class TestAgentRegistry:
    """Test suite for Agent Registry"""
    
    @pytest.fixture
    async def registry(self):
        """Create a test agent registry with temporary config"""
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
            
            registry = AgentRegistry(registry_path=f.name)
            await registry.initialize()
            return registry
    
    @pytest.mark.asyncio
    async def test_registry_initialization(self, registry):
        """Test registry initializes correctly"""
        assert len(registry.agents) == 1
        assert "test-agent-1" in registry.agents
        assert "test_capability" in registry.capabilities_index
    
    @pytest.mark.asyncio
    async def test_register_agent(self, registry):
        """Test agent registration"""
        capability = AgentCapability(
            name="new_capability",
            description="A new capability"
        )
        
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
        assert "new_capability" in registry.capabilities_index
    
    @pytest.mark.asyncio
    async def test_unregister_agent(self, registry):
        """Test agent unregistration"""
        result = await registry.unregister_agent("test-agent-1")
        assert result is True
        assert len(registry.agents) == 0
        assert "test_capability" not in registry.capabilities_index
        
        # Test unregistering non-existent agent
        result = await registry.unregister_agent("non-existent")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_agents_by_capability(self, registry):
        """Test getting agents by capability"""
        agents = await registry.get_agents_by_capability("test_capability")
        assert len(agents) == 1
        assert agents[0].agent_id == "test-agent-1"
        
        # Test non-existent capability
        agents = await registry.get_agents_by_capability("non_existent")
        assert len(agents) == 0
    
    @pytest.mark.asyncio
    async def test_update_agent_status(self, registry):
        """Test updating agent status"""
        result = await registry.update_agent_status("test-agent-1", AgentStatus.HEALTHY, 0.5)
        assert result is True
        
        agent = await registry.get_agent("test-agent-1")
        assert agent.status == AgentStatus.HEALTHY
        assert agent.load_factor == 0.5
    
    @pytest.mark.asyncio
    async def test_get_healthy_agents(self, registry):
        """Test getting healthy agents"""
        await registry.update_agent_status("test-agent-1", AgentStatus.HEALTHY)
        
        healthy_agents = await registry.get_healthy_agents()
        assert len(healthy_agents) == 1
        assert healthy_agents[0].agent_id == "test-agent-1"


class TestCapabilityMatcher:
    """Test suite for Capability Matcher"""
    
    @pytest.fixture
    def matcher(self):
        """Create a test capability matcher"""
        return CapabilityMatcher()
    
    @pytest.fixture
    def sample_agents(self):
        """Create sample agents for testing"""
        capability1 = AgentCapability(name="web_scraping", description="Web scraping capability")
        capability2 = AgentCapability(name="data_analysis", description="Data analysis capability")
        capability3 = AgentCapability(name="web_scraping", description="Web scraping capability")
        
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
            capabilities=[capability3, capability2],
            status=AgentStatus.IDLE,
            load_factor=0.1
        )
        
        return [agent1, agent2, agent3]
    
    @pytest.mark.asyncio
    async def test_find_matching_agents(self, matcher, sample_agents):
        """Test finding agents that match requirements"""
        requirements = [
            TaskRequirement(capability="web_scraping", required=True, priority=5),
            TaskRequirement(capability="data_analysis", required=False, priority=3)
        ]
        
        matches = await matcher.find_matching_agents(requirements, sample_agents)
        
        assert len(matches) > 0
        # Agent3 should score highest (has both capabilities and is idle)
        assert matches[0].agent.agent_id == "agent3"
        assert "web_scraping" in matches[0].matched_capabilities
        assert "data_analysis" in matches[0].matched_capabilities
    
    @pytest.mark.asyncio
    async def test_find_best_agent_for_capability(self, matcher, sample_agents):
        """Test finding the best agent for a specific capability"""
        result = await matcher.find_best_agent_for_capability("web_scraping", sample_agents)
        
        assert result is not None
        assert result.agent.agent_id in ["agent1", "agent3"]
        assert "web_scraping" in result.matched_capabilities
    
    @pytest.mark.asyncio
    async def test_capability_coverage(self, matcher, sample_agents):
        """Test capability coverage analysis"""
        requirements = [
            TaskRequirement(capability="web_scraping", required=True),
            TaskRequirement(capability="data_analysis", required=True),
            TaskRequirement(capability="missing_capability", required=True)
        ]
        
        coverage = matcher.get_capability_coverage(requirements, sample_agents)
        
        assert "web_scraping" in coverage
        assert len(coverage["web_scraping"]) == 2  # agent1 and agent3
        assert "data_analysis" in coverage
        assert len(coverage["data_analysis"]) == 2  # agent2 and agent3
        assert "missing_capability" in coverage
        assert len(coverage["missing_capability"]) == 0


class TestHealthMonitor:
    """Test suite for Health Monitor"""
    
    @pytest.fixture
    async def health_monitor(self):
        """Create a test health monitor"""
        registry = MagicMock()
        registry.list_agents = AsyncMock(return_value=[])
        registry.update_agent_status = AsyncMock(return_value=True)
        
        monitor = HealthMonitor(registry)
        return monitor
    
    @pytest.fixture
    def sample_agent(self):
        """Create a sample agent for testing"""
        return AgentInfo(
            agent_id="test-agent",
            name="Test Agent",
            description="Test agent for health monitoring",
            url="http://test-agent:8001",
            status=AgentStatus.UNKNOWN
        )
    
    @pytest.mark.asyncio
    async def test_check_agent_health(self, health_monitor, sample_agent):
        """Test individual agent health check"""
        result = await health_monitor.check_agent_health(sample_agent)
        
        assert isinstance(result, HealthCheckResult)
        assert result.agent_id == "test-agent"
        assert result.response_time_ms >= 0
        assert result.status in [AgentStatus.HEALTHY, AgentStatus.IDLE, AgentStatus.UNHEALTHY]
    
    @pytest.mark.asyncio
    async def test_health_monitoring_lifecycle(self, health_monitor):
        """Test starting and stopping health monitoring"""
        assert not health_monitor._monitoring
        
        await health_monitor.start_monitoring()
        assert health_monitor._monitoring
        
        await health_monitor.stop_monitoring()
        assert not health_monitor._monitoring
    
    @pytest.mark.asyncio
    async def test_health_history(self, health_monitor, sample_agent):
        """Test health history tracking"""
        # Perform a health check
        await health_monitor.check_agent_health(sample_agent)
        
        # Check history
        history = health_monitor.get_agent_health_history("test-agent")
        assert len(history) == 1
        assert history[0].agent_id == "test-agent"
    
    @pytest.mark.asyncio
    async def test_health_statistics(self, health_monitor, sample_agent):
        """Test health statistics calculation"""
        # Perform multiple health checks
        for _ in range(3):
            await health_monitor.check_agent_health(sample_agent)
        
        stats = health_monitor.get_health_statistics()
        assert "success_rate" in stats
        assert "average_response_time_ms" in stats
        assert stats["total_checks"] == 3


class TestLoadBalancer:
    """Test suite for Load Balancer"""
    
    @pytest.fixture
    def load_balancer(self):
        """Create a test load balancer"""
        registry = MagicMock()
        registry.get_available_agents = AsyncMock(return_value=[])
        registry.update_agent_status = AsyncMock(return_value=True)
        
        return LoadBalancer(registry)
    
    @pytest.fixture
    def sample_agents(self):
        """Create sample agents for load balancing tests"""
        capability = AgentCapability(name="task_execution", description="Task execution capability")
        
        agent1 = AgentInfo(
            agent_id="agent1",
            name="Agent 1",
            description="First agent",
            capabilities=[capability],
            status=AgentStatus.HEALTHY,
            load_factor=0.2
        )
        
        agent2 = AgentInfo(
            agent_id="agent2",
            name="Agent 2",
            description="Second agent",
            capabilities=[capability],
            status=AgentStatus.HEALTHY,
            load_factor=0.8
        )
        
        return [agent1, agent2]
    
    @pytest.mark.asyncio
    async def test_assign_task_capability_aware(self, load_balancer, sample_agents):
        """Test task assignment with capability-aware strategy"""
        load_balancer.registry.get_available_agents.return_value = sample_agents
        
        requirements = [TaskRequirement(capability="task_execution", required=True)]
        
        assignment = await load_balancer.assign_task(
            "test-task",
            requirements,
            LoadBalancingStrategy.CAPABILITY_AWARE,
            0.3
        )
        
        assert assignment is not None
        assert assignment.task_id == "test-task"
        # Should prefer agent1 due to lower load
        assert assignment.agent_id == "agent1"
    
    @pytest.mark.asyncio
    async def test_complete_task(self, load_balancer, sample_agents):
        """Test task completion"""
        load_balancer.registry.get_available_agents.return_value = sample_agents
        
        requirements = [TaskRequirement(capability="task_execution", required=True)]
        
        # Assign task
        assignment = await load_balancer.assign_task("test-task", requirements)
        assert assignment is not None
        
        # Complete task
        result = await load_balancer.complete_task("test-task", assignment.agent_id)
        assert result is True
        
        # Verify task is removed
        assignments = load_balancer.get_agent_assignments(assignment.agent_id)
        assert len(assignments) == 0
    
    @pytest.mark.asyncio
    async def test_load_statistics(self, load_balancer, sample_agents):
        """Test load statistics calculation"""
        load_balancer.registry.get_available_agents.return_value = sample_agents
        
        # Assign some tasks
        requirements = [TaskRequirement(capability="task_execution", required=True)]
        await load_balancer.assign_task("task1", requirements, estimated_load=0.3)
        await load_balancer.assign_task("task2", requirements, estimated_load=0.2)
        
        stats = load_balancer.get_load_statistics()
        assert "total_agents" in stats
        assert "total_tasks" in stats
        assert stats["total_tasks"] >= 2
    
    @pytest.mark.asyncio
    async def test_different_strategies(self, load_balancer, sample_agents):
        """Test different load balancing strategies"""
        load_balancer.registry.get_available_agents.return_value = sample_agents
        requirements = [TaskRequirement(capability="task_execution", required=True)]
        
        strategies = [
            LoadBalancingStrategy.LEAST_LOADED,
            LoadBalancingStrategy.ROUND_ROBIN,
            LoadBalancingStrategy.RANDOM
        ]
        
        for strategy in strategies:
            assignment = await load_balancer.assign_task(
                f"test-task-{strategy}",
                requirements,
                strategy
            )
            assert assignment is not None
            assert assignment.agent_id in ["agent1", "agent2"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
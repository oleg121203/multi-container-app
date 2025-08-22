"""
Test suite for Phase 4 components - Agent Registry and Team Constructor
"""

import pytest
import pytest_asyncio
import asyncio
import json
import tempfile
import os
from unittest.mock import Mock, patch

from agents.registry.agent_registry import AgentRegistry, AgentInfo, AgentCapability, AgentStatus
from agents.registry.capability_matcher import CapabilityMatcher, TaskRequirement
from agents.registry.health_monitor import HealthMonitor
from agents.registry.load_balancer import LoadBalancer

from agents.team_constructor.task_analyzer import TaskAnalyzer, TaskComplexity, TaskType
from agents.team_constructor.team_builder import TeamBuilder
from agents.team_constructor.role_assigner import RoleAssigner
from agents.team_constructor.coordination_engine import CoordinationEngine, CoordinationMode


class TestAgentRegistry:
    """Test suite for Agent Registry (TEAM-01)"""
    
    @pytest_asyncio.fixture
    async def registry(self):
        """Create a test agent registry"""
        with patch.dict(os.environ, {'ATLAS_AGENT_REGISTRY_PATH': '/dev/null'}):
            registry = AgentRegistry()
            yield registry
            await registry.stop()
        
    @pytest.fixture
    def sample_agent(self):
        """Create a sample agent for testing"""
        capabilities = [
            AgentCapability(
                name="coding",
                category="development",
                description="Python programming capability"
            ),
            AgentCapability(
                name="analysis", 
                category="data",
                description="Data analysis capability"
            )
        ]
        
        return AgentInfo(
            id="test-agent-1",
            name="Test Agent 1",
            url="http://test-agent:8000",
            capabilities=capabilities,
            status=AgentStatus.HEALTHY
        )
        
    @pytest.mark.asyncio
    async def test_registry_initialization(self, registry):
        """Test registry initialization"""
        await registry.start()
        
        assert registry._running is True
        assert len(registry.agents) == 0
        
    @pytest.mark.asyncio
    async def test_agent_registration(self, registry, sample_agent):
        """Test agent registration"""
        await registry.start()
        
        result = await registry.register_agent(sample_agent)
        
        assert result is True
        assert sample_agent.id in registry.agents
        assert registry.agents[sample_agent.id].name == "Test Agent 1"
        
    @pytest.mark.asyncio
    async def test_agent_discovery_by_capability(self, registry, sample_agent):
        """Test finding agents by capability"""
        await registry.start()
        await registry.register_agent(sample_agent)
        
        coding_agents = await registry.find_agents_by_capability("coding")
        analysis_agents = await registry.find_agents_by_capability("analysis")
        missing_agents = await registry.find_agents_by_capability("nonexistent")
        
        assert len(coding_agents) == 1
        assert coding_agents[0].id == sample_agent.id
        assert len(analysis_agents) == 1
        assert len(missing_agents) == 0
        
    @pytest.mark.asyncio
    async def test_agent_status_update(self, registry, sample_agent):
        """Test agent status updates"""
        await registry.start()
        await registry.register_agent(sample_agent)
        
        await registry.update_agent_status(sample_agent.id, AgentStatus.BUSY, 0.8)
        
        updated_agent = await registry.get_agent(sample_agent.id)
        assert updated_agent.status == AgentStatus.BUSY
        assert updated_agent.load_score == 0.8
        
    @pytest.mark.asyncio
    async def test_registry_stats(self, registry, sample_agent):
        """Test registry statistics"""
        await registry.start()
        await registry.register_agent(sample_agent)
        
        stats = await registry.get_registry_stats()
        
        assert stats["total_agents"] == 1
        assert "healthy" in stats["status_breakdown"]
        assert "coding" in stats["capabilities"]
        assert "analysis" in stats["capabilities"]


class TestCapabilityMatcher:
    """Test suite for Capability Matcher"""
    
    @pytest.fixture
    def matcher(self):
        """Create a capability matcher"""
        return CapabilityMatcher()
        
    @pytest.fixture
    def test_agents(self):
        """Create test agents with different capabilities"""
        agents = [
            AgentInfo(
                id="coding-agent",
                name="Coding Agent",
                url="http://coding:8000",
                capabilities=[
                    AgentCapability("coding", "development", "Python coding"),
                    AgentCapability("testing", "qa", "Unit testing")
                ],
                status=AgentStatus.HEALTHY,
                load_score=0.3
            ),
            AgentInfo(
                id="analysis-agent", 
                name="Analysis Agent",
                url="http://analysis:8000",
                capabilities=[
                    AgentCapability("analysis", "data", "Data analysis"),
                    AgentCapability("research", "knowledge", "Information research")
                ],
                status=AgentStatus.HEALTHY,
                load_score=0.7
            )
        ]
        return agents
        
    @pytest.mark.asyncio
    async def test_capability_matching(self, matcher, test_agents):
        """Test capability matching logic"""
        requirements = [
            TaskRequirement(capability="coding", priority=1),
            TaskRequirement(capability="analysis", priority=2)
        ]
        
        matches = await matcher.match_agents(requirements, test_agents)
        
        assert len(matches) == 2
        # Coding agent should score higher due to exact match and low load
        assert matches[0].agent.id == "coding-agent"
        assert matches[0].match_score > matches[1].match_score
        
    @pytest.mark.asyncio
    async def test_best_agent_for_capability(self, matcher, test_agents):
        """Test finding best agent for specific capability"""
        best_coder = await matcher.find_best_agent_for_capability("coding", test_agents)
        best_analyst = await matcher.find_best_agent_for_capability("analysis", test_agents)
        
        assert best_coder.id == "coding-agent"
        assert best_analyst.id == "analysis-agent"


class TestTaskAnalyzer:
    """Test suite for Task Analyzer"""
    
    @pytest.fixture
    def analyzer(self):
        """Create a task analyzer"""
        return TaskAnalyzer()
        
    @pytest.mark.asyncio
    async def test_simple_task_analysis(self, analyzer):
        """Test analysis of a simple task"""
        task_description = "Write a simple Python function to add two numbers"
        
        analysis = await analyzer.analyze_task(task_description)
        
        assert analysis.task_type == TaskType.CODING
        assert analysis.complexity == TaskComplexity.SIMPLE
        assert analysis.suggested_team_size == 1
        assert any(req.capability == "coding" for req in analysis.required_capabilities)
        
    @pytest.mark.asyncio
    async def test_complex_task_analysis(self, analyzer):
        """Test analysis of a complex task"""
        task_description = """
        Develop a comprehensive enterprise-level data analysis system that can
        process multiple data sources, perform advanced analytics, generate
        automated reports, and provide real-time monitoring capabilities.
        This is a critical mission-critical system requiring expert knowledge.
        """
        
        analysis = await analyzer.analyze_task(task_description)
        
        assert analysis.complexity in [TaskComplexity.COMPLEX, TaskComplexity.EXPERT]
        assert analysis.suggested_team_size >= 3
        assert len(analysis.required_capabilities) > 1
        assert ("high_priority" in analysis.special_requirements or "security_clearance" in analysis.special_requirements)
        
    @pytest.mark.asyncio
    async def test_capability_extraction(self, analyzer):
        """Test capability extraction from task description"""
        task_description = "Analyze data, write automation scripts, and monitor system health"
        
        analysis = await analyzer.analyze_task(task_description)
        
        capability_names = [req.capability for req in analysis.required_capabilities]
        # Check for at least some of the expected capabilities
        expected_caps = ["analysis", "automation", "monitoring"]
        found_caps = [cap for cap in expected_caps if cap in capability_names]
        assert len(found_caps) >= 2  # At least 2 of the 3 capabilities should be found


class TestTeamBuilder:
    """Test suite for Team Builder"""
    
    @pytest_asyncio.fixture
    async def team_builder(self):
        """Create a team builder with mocked dependencies"""
        registry = Mock()
        matcher = Mock()
        load_balancer = Mock()
        
        return TeamBuilder(registry, matcher, load_balancer)
        
    @pytest.fixture
    def sample_task_analysis(self):
        """Create sample task analysis"""
        from agents.team_constructor.task_analyzer import TaskAnalysis
        
        return TaskAnalysis(
            task_id="test-task",
            complexity=TaskComplexity.MODERATE,
            task_type=TaskType.CODING,
            estimated_duration_minutes=60,
            required_capabilities=[
                TaskRequirement(capability="coding", priority=1),
                TaskRequirement(capability="testing", priority=1)  # Make testing critical
            ],
            suggested_team_size=2,
            special_requirements=[],
            confidence_score=0.8
        )
        
    @pytest.mark.asyncio
    async def test_team_formation_validation(self, team_builder, sample_task_analysis):
        """Test team formation validation"""
        # Create mock team composition
        from agents.team_constructor.team_builder import TeamComposition
        
        mock_agents = [
            AgentInfo(
                id="agent1", 
                name="Agent 1", 
                url="http://agent1:8000",
                capabilities=[AgentCapability("coding", "dev", "Coding")],
                status=AgentStatus.HEALTHY
            )
        ]
        
        team = TeamComposition(
            agents=mock_agents,
            roles={"agent1": "developer"},
            capabilities_coverage={"coding": True, "testing": False},
            team_score=0.7,
            formation_strategy="test"
        )
        
        validation = await team_builder.validate_team_composition(team, sample_task_analysis)
        
        assert "errors" in validation
        # Should have error about missing critical testing capability
        assert any("testing" in error for error in validation["errors"])


class TestIntegration:
    """Integration tests for Phase 4 components"""
    
    @pytest.mark.asyncio
    async def test_end_to_end_team_formation(self):
        """Test complete team formation workflow"""
        
        # Create components
        registry = AgentRegistry()
        matcher = CapabilityMatcher()
        load_balancer = LoadBalancer()
        team_builder = TeamBuilder(registry, matcher, load_balancer)
        task_analyzer = TaskAnalyzer()
        
        try:
            # Start registry
            await registry.start()
            
            # Register test agents
            test_agents = [
                AgentInfo(
                    id="dev-agent",
                    name="Developer Agent", 
                    url="http://dev:8000",
                    capabilities=[
                        AgentCapability("coding", "development", "Python development"),
                        AgentCapability("testing", "qa", "Unit testing")
                    ],
                    status=AgentStatus.HEALTHY,
                    load_score=0.2
                ),
                AgentInfo(
                    id="analyst-agent",
                    name="Analyst Agent",
                    url="http://analyst:8000", 
                    capabilities=[
                        AgentCapability("analysis", "data", "Data analysis"),
                        AgentCapability("research", "knowledge", "Research")
                    ],
                    status=AgentStatus.HEALTHY,
                    load_score=0.5
                )
            ]
            
            for agent in test_agents:
                await registry.register_agent(agent)
                
            # Analyze a task
            task_analysis = await task_analyzer.analyze_task(
                "Create a Python script to analyze data and write unit tests"
            )
            
            # Build team
            team = await team_builder.build_team_for_task(task_analysis)
            
            # Validate results
            assert team is not None
            assert len(team.agents) > 0
            assert team.team_score > 0
            assert len(team.roles) == len(team.agents)
            
        finally:
            await registry.stop()


class TestPhase4Configuration:
    """Test Phase 4 configuration loading"""
    
    def test_agent_config_loading(self):
        """Test loading agent configuration from JSON"""
        config_path = "./config/agents.json"
        
        # Check if config file exists and is valid JSON
        assert os.path.exists(config_path)
        
        with open(config_path, 'r') as f:
            config = json.load(f)
            
        assert "agents" in config
        assert len(config["agents"]) > 0
        
        # Validate agent structure
        for agent in config["agents"]:
            assert "id" in agent
            assert "name" in agent
            assert "url" in agent
            assert "capabilities" in agent
            
            # Validate capabilities
            for cap in agent["capabilities"]:
                assert "name" in cap
                assert "category" in cap
                assert "description" in cap
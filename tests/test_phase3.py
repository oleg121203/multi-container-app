"""
Test suite for Phase 3 components: MCP Hub, Playwright MCP, and LLM3
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch
import aiohttp
from typing import Dict, Any

# Import Phase 3 components
from agents.mcp_hub.registry import MCPRegistry, MCPServerInfo, MCPServerStatus
from agents.mcp_hub.client import MCPClient, MCPExecutionStatus
from agents.llm3.agent import LLM3SecurityAgent, SecurityEvent, SecurityEventSeverity


class TestMCPRegistry:
    """Test suite for MCP Registry"""
    
    @pytest.fixture
    async def registry(self):
        """Create a test MCP registry"""
        registry = MCPRegistry()
        yield registry
        if registry._session:
            await registry._session.close()
    
    @pytest.mark.asyncio
    async def test_registry_initialization(self, registry):
        """Test registry initialization"""
        assert registry.servers == {}
        assert registry.health_check_interval == 30
        assert registry.health_check_timeout == 5
    
    @pytest.mark.asyncio
    async def test_server_discovery_from_env(self, registry):
        """Test server discovery from environment variables"""
        with patch.dict('os.environ', {
            'ATLAS_MCP_SERVERS': 'playwright,automation',
            'ATLAS_MCP_PLAYWRIGHT_URL': 'http://localhost:4001',
            'ATLAS_MCP_AUTOMATION_URL': 'http://localhost:4002',
            'ATLAS_MCP_PLAYWRIGHT_AUTH_TOKEN': 'test_token'
        }):
            await registry._discover_servers_from_env()
            
            assert len(registry.servers) == 2
            assert 'playwright' in registry.servers
            assert 'automation' in registry.servers
            
            playwright_server = registry.servers['playwright']
            assert playwright_server.url == 'http://localhost:4001'
            assert playwright_server.auth_token == 'test_token'
            assert playwright_server.status == MCPServerStatus.UNKNOWN
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, registry):
        """Test successful health check"""
        # Add a test server
        server_info = MCPServerInfo(
            name="test_server",
            url="http://test:4001",
            status=MCPServerStatus.UNKNOWN,
            capabilities=[],
            last_health_check=0
        )
        registry.servers["test_server"] = server_info
        
        # Mock HTTP session
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"capabilities": ["test_action"]})
        
        mock_session = Mock()
        mock_session.get = AsyncMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        
        registry._session = Mock()
        registry._session.get = AsyncMock(return_value=mock_session)
        
        await registry._check_server_health("test_server")
        
        assert server_info.status == MCPServerStatus.HEALTHY
        assert server_info.last_health_check > 0
    
    @pytest.mark.asyncio
    async def test_get_healthy_servers(self, registry):
        """Test getting healthy servers"""
        # Add test servers with different statuses
        registry.servers["healthy1"] = MCPServerInfo(
            name="healthy1", url="http://test1:4001", 
            status=MCPServerStatus.HEALTHY, capabilities=[], last_health_check=0
        )
        registry.servers["healthy2"] = MCPServerInfo(
            name="healthy2", url="http://test2:4001", 
            status=MCPServerStatus.HEALTHY, capabilities=[], last_health_check=0
        )
        registry.servers["unhealthy"] = MCPServerInfo(
            name="unhealthy", url="http://test3:4001", 
            status=MCPServerStatus.UNHEALTHY, capabilities=[], last_health_check=0
        )
        
        healthy_servers = registry.get_healthy_servers()
        assert len(healthy_servers) == 2
        assert all(server.status == MCPServerStatus.HEALTHY for server in healthy_servers)
    
    @pytest.mark.asyncio
    async def test_get_servers_by_capability(self, registry):
        """Test filtering servers by capability"""
        registry.servers["playwright"] = MCPServerInfo(
            name="playwright", url="http://test:4001", 
            status=MCPServerStatus.HEALTHY, 
            capabilities=["browser_navigation", "page_screenshot"], 
            last_health_check=0
        )
        registry.servers["automation"] = MCPServerInfo(
            name="automation", url="http://test:4002", 
            status=MCPServerStatus.HEALTHY, 
            capabilities=["file_operations", "api_calls"], 
            last_health_check=0
        )
        
        browser_servers = registry.get_servers_by_capability("browser_navigation")
        assert len(browser_servers) == 1
        assert browser_servers[0].name == "playwright"
        
        file_servers = registry.get_servers_by_capability("file_operations")
        assert len(file_servers) == 1
        assert file_servers[0].name == "automation"


class TestMCPClient:
    """Test suite for MCP Client"""
    
    @pytest.fixture
    async def client(self):
        """Create a test MCP client"""
        client = MCPClient()
        yield client
        if client.session:
            await client.session.close()
    
    @pytest.fixture
    async def mock_registry(self):
        """Create a mock registry with test servers"""
        registry = Mock()
        registry.get_healthy_servers.return_value = [
            MCPServerInfo(
                name="test_server", url="http://test:4001",
                status=MCPServerStatus.HEALTHY, capabilities=["test_action"],
                last_health_check=0
            )
        ]
        registry.get_server.return_value = MCPServerInfo(
            name="test_server", url="http://test:4001",
            status=MCPServerStatus.HEALTHY, capabilities=["test_action"],
            last_health_check=0
        )
        registry.get_servers_by_capability.return_value = [
            MCPServerInfo(
                name="test_server", url="http://test:4001",
                status=MCPServerStatus.HEALTHY, capabilities=["test_action"],
                last_health_check=0
            )
        ]
        return registry
    
    @pytest.mark.asyncio
    async def test_execute_action_success(self, client, mock_registry):
        """Test successful action execution"""
        with patch('agents.mcp_hub.client.mcp_registry', mock_registry):
            # Mock HTTP response
            mock_response = Mock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value={"result": "success"})
            
            client.session = Mock()
            client.session.post = AsyncMock()
            client.session.post.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            client.session.post.return_value.__aexit__ = AsyncMock(return_value=None)
            
            result = await client.execute_action("test_action", {"param": "value"})
            
            assert result.status == MCPExecutionStatus.SUCCESS
            assert result.result == "success"
            assert result.server_used == "test_server"
            assert result.correlation_id is not None
    
    @pytest.mark.asyncio
    async def test_execute_action_no_server(self, client):
        """Test action execution when no server is available"""
        with patch('agents.mcp_hub.client.mcp_registry') as mock_registry:
            mock_registry.get_healthy_servers.return_value = []
            
            result = await client.execute_action("test_action", {})
            
            assert result.status == MCPExecutionStatus.NO_SERVER
            assert "No suitable MCP server available" in result.error
    
    @pytest.mark.asyncio
    async def test_server_selection_by_preference(self, client, mock_registry):
        """Test server selection by preference"""
        with patch('agents.mcp_hub.client.mcp_registry', mock_registry):
            server = await client._select_server(server_preference="test_server")
            
            assert server is not None
            assert server.name == "test_server"
            mock_registry.get_server.assert_called_once_with("test_server")


class TestLLM3SecurityAgent:
    """Test suite for LLM3 Security Agent"""
    
    @pytest.fixture
    def agent(self):
        """Create a test LLM3 agent"""
        with patch.dict('os.environ', {
            'ATLAS_LLM3_PROVIDER': 'openai',
            'ATLAS_LLM3_MODEL': 'gpt-4o-mini',
            'ATLAS_LLM3_API_KEY': 'test_key'
        }):
            agent = LLM3SecurityAgent()
            return agent
    
    @pytest.fixture
    def sample_security_event(self):
        """Create a sample security event"""
        return SecurityEvent(
            time="2024-01-15T10:30:00Z",
            rule="Write below etc",
            priority="CRITICAL",
            output="Detected write to /etc/passwd",
            source="falco",
            proc={"pid": 1234, "cmdline": "/bin/sh -c echo bad > /etc/passwd"},
            k8s={"pod_name": "attacker-abc", "namespace": "default", "container_id": "docker://..."}
        )
    
    def test_agent_initialization(self, agent):
        """Test agent initialization"""
        assert agent.llm_provider == 'openai'
        assert agent.llm_model == 'gpt-4o-mini'
        assert agent.api_key == 'test_key'
        assert 'critical_rules' in agent.security_policies
        assert 'auto_actions' in agent.security_policies
    
    @pytest.mark.asyncio
    async def test_security_event_processing(self, agent, sample_security_event):
        """Test security event processing"""
        # Mock LLM response
        mock_llm_response = json.dumps({
            "severity": "CRITICAL",
            "recommended_actions": ["delete_pod", "alert_only"],
            "rationale": "Critical file system modification detected",
            "confidence": 0.9,
            "auto_execute": True
        })
        
        with patch.object(agent, '_call_llm', return_value=mock_llm_response):
            decision = await agent._analyze_security_event(sample_security_event)
            
            assert decision.severity == SecurityEventSeverity.CRITICAL
            assert len(decision.recommended_actions) == 2
            assert decision.confidence == 0.9
            assert decision.auto_execute is True
            assert "Critical file system modification" in decision.rationale
    
    def test_fallback_analysis(self, agent, sample_security_event):
        """Test fallback rule-based analysis"""
        decision = agent._fallback_analysis(sample_security_event)
        
        assert decision.severity == SecurityEventSeverity.CRITICAL  # CRITICAL priority maps to CRITICAL severity
        assert decision.confidence == 0.7
        assert "Rule-based fallback" in decision.rationale
    
    def test_security_policy_application(self, agent, sample_security_event):
        """Test security policy application"""
        # Create a decision that would normally auto-execute
        from agents.llm3.agent import MitigationDecision, MitigationAction
        decision = MitigationDecision(
            event_id="test_event",
            severity=SecurityEventSeverity.CRITICAL,
            recommended_actions=[MitigationAction.DELETE_POD],
            rationale="Test decision",
            confidence=0.9,
            auto_execute=True,
            timestamp=0
        )
        
        # Test namespace allowlist protection
        sample_security_event.k8s = {"namespace": "kube-system"}
        modified_decision = agent._apply_security_policies(sample_security_event, decision)
        
        assert modified_decision.auto_execute is False
        assert "Protected namespace" in modified_decision.rationale
    
    @pytest.mark.asyncio
    async def test_mitigation_action_execution(self, agent, sample_security_event):
        """Test mitigation action execution (mock)"""
        from agents.llm3.agent import MitigationDecision, MitigationAction
        decision = MitigationDecision(
            event_id="test_event",
            severity=SecurityEventSeverity.CRITICAL,
            recommended_actions=[MitigationAction.DELETE_POD, MitigationAction.ALERT_ONLY],
            rationale="Test decision",
            confidence=0.9,
            auto_execute=True,
            timestamp=0
        )
        
        # Mock the individual action methods
        with patch.object(agent, '_delete_pod', new_callable=AsyncMock) as mock_delete, \
             patch.object(agent, '_send_alert', new_callable=AsyncMock) as mock_alert:
            
            await agent._execute_mitigation_actions(sample_security_event, decision)
            
            mock_delete.assert_called_once_with(sample_security_event)
            mock_alert.assert_called_once_with(sample_security_event, decision)


class TestPhase3Integration:
    """Integration tests for Phase 3 components"""
    
    @pytest.mark.asyncio
    async def test_mcp_hub_integration(self):
        """Test integration between MCP registry and client"""
        registry = MCPRegistry()
        client = MCPClient()
        
        # Setup test environment
        with patch.dict('os.environ', {
            'ATLAS_MCP_SERVERS': 'test_server',
            'ATLAS_MCP_TEST_SERVER_URL': 'http://localhost:4001'
        }):
            await registry._discover_servers_from_env()
            
            assert len(registry.servers) == 1
            assert 'test_server' in registry.servers
            
            # Test server status
            status = registry.get_registry_status()
            assert status['total_servers'] == 1
            assert 'test_server' in status['servers']
    
    @pytest.mark.asyncio
    async def test_llm3_falco_integration(self):
        """Test integration between LLM3 and Falco events"""
        agent = LLM3SecurityAgent()
        
        # Simulate Falco event
        falco_event = {
            "time": "2024-01-15T10:30:00Z",
            "rule": "Write below etc",
            "priority": "CRITICAL",
            "output": "Detected write to /etc/passwd",
            "source": "falco",
            "proc": {"pid": 1234, "cmdline": "/bin/sh -c echo bad > /etc/passwd"},
            "k8s": {"pod_name": "attacker-abc", "namespace": "default"}
        }
        
        # Mock LLM response
        mock_response = json.dumps({
            "severity": "CRITICAL",
            "recommended_actions": ["delete_pod"],
            "rationale": "Critical security violation",
            "confidence": 0.95,
            "auto_execute": False  # Require manual approval for test
        })
        
        with patch.object(agent, '_call_llm', return_value=mock_response):
            security_event = SecurityEvent(**falco_event)
            await agent._process_security_event(security_event)
            
            # Verify event was processed and logged
            assert len(agent.processed_events) == 1
            assert len(agent.audit_log) == 1
            
            audit_entry = agent.audit_log[0]
            assert audit_entry['rule'] == "Write below etc"
            assert audit_entry['decision']['severity'] == "CRITICAL"


# Pytest configuration for async tests
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
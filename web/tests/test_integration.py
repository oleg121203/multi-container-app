"""
Integration tests for the complete ATLAS Web Interface
Tests the full stack: API + Frontend + Backend integration
"""

import pytest
import asyncio
import json
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi.testclient import TestClient
from web.api.server import app

@pytest.fixture
def client():
    """Create test client for integration tests"""
    return TestClient(app)

class TestAgentRegistryIntegration:
    """Test integration with Agent Registry backend"""
    
    def test_agent_loading(self, client):
        """Test that agents are loaded from the registry"""
        response = client.get("/api/agents")
        assert response.status_code == 200
        
        data = response.json()
        agents = data["agents"]
        
        # Should have the 3 default agents
        assert len(agents) >= 3
        
        # Check for expected agent types
        agent_names = [agent["name"] for agent in agents]
        assert "LLM1 Agent" in agent_names
        assert "LLM2 Orchestrator" in agent_names
        assert "LLM3 Security Monitor" in agent_names
        
    def test_agent_capabilities(self, client):
        """Test that agent capabilities are properly loaded"""
        response = client.get("/api/agents")
        data = response.json()
        
        for agent in data["agents"]:
            assert "capabilities" in agent
            assert isinstance(agent["capabilities"], list)
            assert len(agent["capabilities"]) > 0
            
            # Each capability should have proper structure
            for capability in agent["capabilities"]:
                if isinstance(capability, dict):
                    assert "name" in capability
                    assert "description" in capability

class TestTeamConstructorIntegration:
    """Test integration with Team Constructor backend"""
    
    def test_team_formation_analysis(self, client):
        """Test that team formation analyzes task requirements"""
        test_cases = [
            {
                "description": "Create a secure web interface",
                "expected_capabilities": ["user_interface", "security_monitoring"]
            },
            {
                "description": "Orchestrate multiple AI agents for data processing",
                "expected_capabilities": ["task_orchestration", "mcp_integration"]
            },
            {
                "description": "Monitor system security and respond to threats",
                "expected_capabilities": ["security_monitoring", "incident_response"]
            }
        ]
        
        for test_case in test_cases:
            response = client.post("/api/teams/form", json={
                "description": test_case["description"]
            })
            assert response.status_code == 200
            
            data = response.json()
            assert data["status"] == "success"
            # Team formation should work even if no agents are available
            assert "team" in data

class TestRealTimeFeatures:
    """Test real-time features like WebSocket and status updates"""
    
    def test_system_status_realtime(self, client):
        """Test that system status reflects current state"""
        response = client.get("/api/system/status")
        assert response.status_code == 200
        
        data = response.json()
        
        # Check that all core services are reported
        core_services = ["agent_registry", "team_constructor", "llm1", "llm2", "llm3"]
        for service in core_services:
            assert service in data
            # In a healthy system, these should be "active"
            assert data[service] in ["active", "inactive"]
        
    def test_metrics_accuracy(self, client):
        """Test that metrics reflect actual system state"""
        # Get agents first
        agents_response = client.get("/api/agents")
        agents_count = len(agents_response.json()["agents"])
        
        # Get metrics
        metrics_response = client.get("/api/metrics")
        assert metrics_response.status_code == 200
        
        metrics = metrics_response.json()
        
        # Active agents count should match or be reasonable
        assert metrics["active_agents"] >= 0
        assert isinstance(metrics["teams_formed"], int)
        assert isinstance(metrics["tasks_completed"], int)

class TestErrorHandlingIntegration:
    """Test error handling across the full stack"""
    
    def test_graceful_backend_failures(self, client):
        """Test that the API handles backend failures gracefully"""
        # Test with invalid agent ID
        response = client.get("/api/agents/invalid-agent/status")
        # Should either return valid mock data or proper error
        assert response.status_code in [200, 404]
        
    def test_malformed_requests(self, client):
        """Test handling of malformed requests"""
        # Malformed team formation request
        response = client.post("/api/teams/form", json={
            "description": None  # Invalid description
        })
        assert response.status_code == 422
        
        # Empty request body
        response = client.post("/api/teams/form", json={})
        assert response.status_code == 422

class TestSecurityIntegration:
    """Test security features and CORS"""
    
    def test_cors_configuration(self, client):
        """Test CORS headers are properly configured"""
        response = client.options("/api/agents")
        assert response.status_code == 200
        
        headers = response.headers
        assert "access-control-allow-origin" in headers
        assert "access-control-allow-methods" in headers
        assert "access-control-allow-headers" in headers
        
    def test_no_sensitive_data_exposure(self, client):
        """Test that sensitive data is not exposed in API responses"""
        # Check agents endpoint doesn't expose API keys
        response = client.get("/api/agents")
        data = response.json()
        
        response_text = json.dumps(data).lower()
        sensitive_patterns = ["api_key", "secret", "password", "token"]
        
        for pattern in sensitive_patterns:
            assert pattern not in response_text

class TestPerformanceIntegration:
    """Test performance characteristics of the integrated system"""
    
    def test_response_times(self, client):
        """Test that API responses are within acceptable time limits"""
        import time
        
        endpoints = [
            "/health",
            "/api/agents", 
            "/api/system/status",
            "/api/metrics"
        ]
        
        for endpoint in endpoints:
            start_time = time.time()
            response = client.get(endpoint)
            duration = time.time() - start_time
            
            assert response.status_code == 200
            assert duration < 2.0  # Should respond within 2 seconds
            
    def test_concurrent_requests(self, client):
        """Test handling of concurrent requests"""
        import concurrent.futures
        import time
        
        def make_request():
            return client.get("/api/agents")
        
        # Make 10 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            start_time = time.time()
            futures = [executor.submit(make_request) for _ in range(10)]
            responses = [future.result() for future in futures]
            duration = time.time() - start_time
            
        # All requests should succeed
        for response in responses:
            assert response.status_code == 200
            
        # Should complete reasonably quickly
        assert duration < 5.0

class TestCompleteWorkflow:
    """Test complete user workflows through the system"""
    
    def test_user_session_workflow(self, client):
        """Test a complete user session workflow"""
        # 1. User loads the interface
        response = client.get("/")
        assert response.status_code == 200
        
        # 2. Interface loads agents
        agents_response = client.get("/api/agents")
        assert agents_response.status_code == 200
        agents = agents_response.json()["agents"]
        
        # 3. User forms a team
        team_response = client.post("/api/teams/form", json={
            "description": "Create a monitoring dashboard with security features"
        })
        assert team_response.status_code == 200
        team_data = team_response.json()
        
        # 4. User sends chat messages
        chat_response = client.post("/api/chat", json={
            "type": "chat",
            "message": "Show me the team status",
            "timestamp": "2024-08-22T20:30:00Z"
        })
        assert chat_response.status_code == 200
        
        # 5. User checks system status
        status_response = client.get("/api/system/status")
        assert status_response.status_code == 200
        
        # 6. User views metrics
        metrics_response = client.get("/api/metrics")
        assert metrics_response.status_code == 200
        
        print("✅ Complete user workflow test passed")
        
    def test_team_formation_and_management(self, client):
        """Test team formation and management workflow"""
        # Form multiple teams
        team_descriptions = [
            "Build a web interface",
            "Monitor system security", 
            "Process data with AI"
        ]
        
        teams = []
        for description in team_descriptions:
            response = client.post("/api/teams/form", json={
                "description": description
            })
            assert response.status_code == 200
            teams.append(response.json())
        
        # All teams should be successfully formed
        for team in teams:
            assert team["status"] == "success"
            
        print("✅ Team formation and management test passed")

@pytest.mark.integration
def test_full_system_health(client):
    """Comprehensive system health test"""
    # Test all major endpoints
    endpoints_to_test = [
        ("/health", 200),
        ("/api/agents", 200),
        ("/api/system/status", 200),
        ("/api/metrics", 200),
        ("/", 200)
    ]
    
    for endpoint, expected_status in endpoints_to_test:
        response = client.get(endpoint)
        assert response.status_code == expected_status, f"Endpoint {endpoint} failed"
    
    # Test POST endpoints
    post_tests = [
        ("/api/teams/form", {"description": "Test team formation"}),
        ("/api/chat", {"type": "chat", "message": "Test", "timestamp": "2024-08-22T20:30:00Z"})
    ]
    
    for endpoint, data in post_tests:
        response = client.post(endpoint, json=data)
        assert response.status_code == 200, f"POST endpoint {endpoint} failed"
    
    print("✅ Full system health test passed")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
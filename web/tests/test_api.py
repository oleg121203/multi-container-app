"""
Test suite for ATLAS Web Interface API endpoints
"""

import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from web.api.server import app

@pytest.fixture
def client():
    """Create test client for the FastAPI app"""
    return TestClient(app)

def test_health_endpoint(client):
    """Test the health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "atlas-web-interface"
    assert data["api_version"] == "1.0.0"
    assert "backend_connected" in data

def test_agents_endpoint(client):
    """Test the agents listing endpoint"""
    response = client.get("/api/agents")
    assert response.status_code == 200
    
    data = response.json()
    assert "agents" in data
    assert isinstance(data["agents"], list)

def test_system_status_endpoint(client):
    """Test the system status endpoint"""
    response = client.get("/api/system/status")
    assert response.status_code == 200
    
    data = response.json()
    expected_services = [
        "agent_registry", "team_constructor", "health_monitor",
        "mcp_hub", "llm1", "llm2", "llm3", "tts", "websocket"
    ]
    
    for service in expected_services:
        assert service in data

def test_metrics_endpoint(client):
    """Test the metrics endpoint"""
    response = client.get("/api/metrics")
    assert response.status_code == 200
    
    data = response.json()
    expected_metrics = [
        "active_agents", "teams_formed", "tasks_completed",
        "uptime_seconds", "request_count", "error_rate", "avg_response_time_ms"
    ]
    
    for metric in expected_metrics:
        assert metric in data
        assert isinstance(data[metric], (int, float))

def test_team_formation_endpoint(client):
    """Test the team formation endpoint"""
    team_request = {
        "description": "Create a test web interface with monitoring",
        "constraints": {}
    }
    
    response = client.post("/api/teams/form", json=team_request)
    assert response.status_code == 200
    
    data = response.json()
    assert "team" in data
    assert "status" in data
    assert data["status"] == "success"

def test_chat_endpoint(client):
    """Test the chat endpoint"""
    chat_message = {
        "type": "chat",
        "message": "Hello ATLAS",
        "timestamp": "2024-08-22T20:30:00Z"
    }
    
    response = client.post("/api/chat", json=chat_message)
    assert response.status_code == 200
    
    data = response.json()
    assert "response" in data
    assert "status" in data
    assert data["status"] == "success"

def test_agent_status_endpoint(client):
    """Test individual agent status endpoint"""
    # Test with a known agent ID
    response = client.get("/api/agents/llm1-agent/status")
    assert response.status_code == 200
    
    data = response.json()
    assert "agent_id" in data
    assert "status" in data
    assert "last_check" in data
    assert "health_score" in data

def test_agent_status_not_found(client):
    """Test agent status with non-existent agent"""
    response = client.get("/api/agents/nonexistent-agent/status")
    # Should still return 200 with mock data in development mode
    assert response.status_code in [200, 404]

def test_root_endpoint(client):
    """Test the root endpoint serves the frontend"""
    response = client.get("/")
    assert response.status_code == 200
    # Should return HTML content
    assert "html" in response.headers.get("content-type", "").lower()

def test_cors_headers(client):
    """Test CORS headers are present"""
    response = client.options("/api/agents")
    assert response.status_code == 200
    
    # Check for CORS headers
    headers = response.headers
    assert "access-control-allow-origin" in headers
    assert "access-control-allow-methods" in headers

@pytest.mark.asyncio
async def test_websocket_connection():
    """Test WebSocket connection (basic test)"""
    from fastapi.testclient import TestClient
    
    with TestClient(app) as client:
        # Test that the WebSocket endpoint exists
        # Note: Full WebSocket testing requires more complex setup
        response = client.get("/ws")
        # WebSocket endpoints return 426 when accessed via HTTP
        assert response.status_code == 426

def test_team_formation_invalid_data(client):
    """Test team formation with invalid data"""
    # Empty description
    response = client.post("/api/teams/form", json={"description": ""})
    assert response.status_code == 422  # Validation error
    
    # Missing description
    response = client.post("/api/teams/form", json={})
    assert response.status_code == 422  # Validation error

def test_chat_invalid_data(client):
    """Test chat endpoint with invalid data"""
    # Missing required fields
    response = client.post("/api/chat", json={})
    assert response.status_code == 422  # Validation error
    
    # Invalid message type
    response = client.post("/api/chat", json={
        "type": "invalid",
        "message": "test",
        "timestamp": "invalid-timestamp"
    })
    # Should still work as we don't validate timestamp format yet
    assert response.status_code == 200

def test_api_performance(client):
    """Test API response times are reasonable"""
    import time
    
    # Health check should be fast
    start = time.time()
    response = client.get("/health")
    duration = time.time() - start
    
    assert response.status_code == 200
    assert duration < 1.0  # Should respond within 1 second
    
    # Agents endpoint should be reasonably fast
    start = time.time()
    response = client.get("/api/agents")
    duration = time.time() - start
    
    assert response.status_code == 200
    assert duration < 2.0  # Should respond within 2 seconds

def test_error_handling(client):
    """Test error handling for various scenarios"""
    # Test non-existent endpoint
    response = client.get("/api/nonexistent")
    assert response.status_code == 404
    
    # Test malformed JSON
    response = client.post("/api/teams/form", 
                          data="malformed json",
                          headers={"Content-Type": "application/json"})
    assert response.status_code == 422

@pytest.mark.integration
def test_full_workflow(client):
    """Test a complete workflow through the API"""
    # 1. Check system health
    health_response = client.get("/health")
    assert health_response.status_code == 200
    
    # 2. Get agents list
    agents_response = client.get("/api/agents")
    assert agents_response.status_code == 200
    agents_data = agents_response.json()
    assert len(agents_data["agents"]) > 0
    
    # 3. Form a team
    team_response = client.post("/api/teams/form", json={
        "description": "Integration test team formation"
    })
    assert team_response.status_code == 200
    
    # 4. Send a chat message
    chat_response = client.post("/api/chat", json={
        "type": "chat",
        "message": "Integration test message",
        "timestamp": "2024-08-22T20:30:00Z"
    })
    assert chat_response.status_code == 200
    
    # 5. Check system status
    status_response = client.get("/api/system/status")
    assert status_response.status_code == 200

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
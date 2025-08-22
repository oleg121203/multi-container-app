"""
Unit tests for Linear tool integration
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
import json

from agents.shared.linear_tool import (
    LinearClient, LinearIssue, LinearTeam, IssueState, IssuePriority,
    CircuitBreaker, CircuitBreakerState
)


class TestCircuitBreaker:
    """Test circuit breaker pattern"""
    
    def test_circuit_breaker_closed_state(self):
        """Test circuit breaker in closed state"""
        cb = CircuitBreaker(failure_threshold=3, timeout=60)
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0
    
    def test_circuit_breaker_failure_tracking(self):
        """Test failure count tracking"""
        cb = CircuitBreaker(failure_threshold=2, timeout=60)
        
        # First failure
        cb._on_failure()
        assert cb.failure_count == 1
        assert cb.state == CircuitBreakerState.CLOSED
        
        # Second failure - should open circuit
        cb._on_failure()
        assert cb.failure_count == 2
        assert cb.state == CircuitBreakerState.OPEN
    
    def test_circuit_breaker_success_reset(self):
        """Test that success resets the circuit breaker"""
        cb = CircuitBreaker(failure_threshold=2, timeout=60)
        
        cb._on_failure()
        assert cb.failure_count == 1
        
        cb._on_success()
        assert cb.failure_count == 0
        assert cb.state == CircuitBreakerState.CLOSED


@pytest.mark.asyncio
class TestLinearClient:
    """Test Linear GraphQL client"""
    
    def setup_method(self):
        with patch('agents.shared.linear_tool.config') as mock_config:
            mock_config.LINEAR_API_KEY = "test_api_key"
            mock_config.LINEAR_API_URL = "https://api.linear.app/graphql"
            self.client = LinearClient()
    
    @patch('agents.shared.linear_tool.Client')
    async def test_initialize(self, mock_gql_client):
        """Test client initialization"""
        mock_client_instance = AsyncMock()
        mock_gql_client.return_value = mock_client_instance
        
        await self.client.initialize()
        
        assert self.client.client is not None
        mock_gql_client.assert_called_once()
    
    @patch('agents.shared.linear_tool.Client')
    async def test_get_teams(self, mock_gql_client):
        """Test getting teams"""
        mock_client_instance = AsyncMock()
        mock_gql_client.return_value = mock_client_instance
        self.client.client = mock_client_instance
        
        # Mock GraphQL response
        mock_response = {
            "teams": {
                "nodes": [
                    {"id": "team1", "name": "Engineering", "key": "ENG"},
                    {"id": "team2", "name": "Design", "key": "DES"}
                ]
            }
        }
        mock_client_instance.execute_async.return_value = mock_response
        
        teams = await self.client.get_teams()
        
        assert len(teams) == 2
        assert teams[0].id == "team1"
        assert teams[0].name == "Engineering"
        assert teams[0].key == "ENG"
        assert teams[1].id == "team2"
        assert teams[1].name == "Design"
        assert teams[1].key == "DES"
    
    @patch('agents.shared.linear_tool.Client')
    async def test_create_issue(self, mock_gql_client):
        """Test creating an issue"""
        mock_client_instance = AsyncMock()
        mock_gql_client.return_value = mock_client_instance
        self.client.client = mock_client_instance
        
        # Mock GraphQL response
        mock_response = {
            "issueCreate": {
                "success": True,
                "issue": {
                    "id": "issue123",
                    "title": "Test Issue",
                    "description": "Test description",
                    "state": {"name": "Todo"},
                    "priority": 2,
                    "url": "https://linear.app/team/issue/TEST-123",
                    "identifier": "TEST-123",
                    "team": {"id": "team1"},
                    "createdAt": "2023-01-01T00:00:00Z",
                    "updatedAt": "2023-01-01T00:00:00Z"
                }
            }
        }
        mock_client_instance.execute_async.return_value = mock_response
        
        issue = await self.client.create_issue(
            title="Test Issue",
            team_id="team1",
            description="Test description",
            priority=IssuePriority.HIGH
        )
        
        assert isinstance(issue, LinearIssue)
        assert issue.id == "issue123"
        assert issue.title == "Test Issue"
        assert issue.description == "Test description"
        assert issue.state == IssueState.UNSTARTED
        assert issue.priority == IssuePriority.HIGH
        assert issue.url == "https://linear.app/team/issue/TEST-123"
        assert issue.identifier == "TEST-123"
        assert issue.team_id == "team1"
    
    @patch('agents.shared.linear_tool.Client')
    async def test_create_issue_failure(self, mock_gql_client):
        """Test issue creation failure"""
        mock_client_instance = AsyncMock()
        mock_gql_client.return_value = mock_client_instance
        self.client.client = mock_client_instance
        
        # Mock failed response
        mock_response = {
            "issueCreate": {
                "success": False
            }
        }
        mock_client_instance.execute_async.return_value = mock_response
        
        with pytest.raises(Exception, match="Failed to create issue"):
            await self.client.create_issue(
                title="Test Issue",
                team_id="team1"
            )
    
    @patch('agents.shared.linear_tool.Client')
    async def test_get_issue(self, mock_gql_client):
        """Test getting an issue by ID"""
        mock_client_instance = AsyncMock()
        mock_gql_client.return_value = mock_client_instance
        self.client.client = mock_client_instance
        
        # Mock GraphQL response
        mock_response = {
            "issue": {
                "id": "issue123",
                "title": "Existing Issue",
                "description": "Existing description",
                "state": {"name": "In Progress"},
                "priority": 1,
                "url": "https://linear.app/team/issue/TEST-123",
                "identifier": "TEST-123",
                "team": {"id": "team1"},
                "createdAt": "2023-01-01T00:00:00Z",
                "updatedAt": "2023-01-01T00:00:00Z"
            }
        }
        mock_client_instance.execute_async.return_value = mock_response
        
        issue = await self.client.get_issue("issue123")
        
        assert issue is not None
        assert issue.id == "issue123"
        assert issue.title == "Existing Issue"
        assert issue.state == IssueState.STARTED
        assert issue.priority == IssuePriority.URGENT
    
    @patch('agents.shared.linear_tool.Client')
    async def test_get_issue_not_found(self, mock_gql_client):
        """Test getting non-existent issue"""
        mock_client_instance = AsyncMock()
        mock_gql_client.return_value = mock_client_instance
        self.client.client = mock_client_instance
        
        # Mock empty response
        mock_response = {"issue": None}
        mock_client_instance.execute_async.return_value = mock_response
        
        issue = await self.client.get_issue("nonexistent")
        assert issue is None
    
    @patch('agents.shared.linear_tool.Client')
    async def test_update_issue(self, mock_gql_client):
        """Test updating an issue"""
        mock_client_instance = AsyncMock()
        mock_gql_client.return_value = mock_client_instance
        self.client.client = mock_client_instance
        
        # Mock GraphQL response
        mock_response = {
            "issueUpdate": {
                "success": True,
                "issue": {
                    "id": "issue123",
                    "title": "Updated Issue",
                    "description": "Updated description",
                    "state": {"name": "Done"},
                    "priority": 3,
                    "url": "https://linear.app/team/issue/TEST-123",
                    "identifier": "TEST-123",
                    "team": {"id": "team1"},
                    "createdAt": "2023-01-01T00:00:00Z",
                    "updatedAt": "2023-01-01T01:00:00Z"
                }
            }
        }
        mock_client_instance.execute_async.return_value = mock_response
        
        issue = await self.client.update_issue(
            issue_id="issue123",
            title="Updated Issue",
            description="Updated description",
            priority=IssuePriority.MEDIUM
        )
        
        assert issue.title == "Updated Issue"
        assert issue.description == "Updated description"
        assert issue.priority == IssuePriority.MEDIUM
        assert issue.state == IssueState.COMPLETED
    
    @patch('agents.shared.linear_tool.Client')
    async def test_retry_mechanism(self, mock_gql_client):
        """Test retry mechanism on failures"""
        mock_client_instance = AsyncMock()
        mock_gql_client.return_value = mock_client_instance
        self.client.client = mock_client_instance
        
        # First two calls fail, third succeeds
        mock_client_instance.execute_async.side_effect = [
            Exception("Network error"),
            Exception("Timeout error"),
            {"teams": {"nodes": []}}
        ]
        
        # Should eventually succeed after retries
        result = await self.client._execute_with_retry(Mock())
        assert result == {"teams": {"nodes": []}}
        
        # Should have been called 3 times
        assert mock_client_instance.execute_async.call_count == 3
    
    @patch('agents.shared.linear_tool.Client')
    async def test_health_check(self, mock_gql_client):
        """Test health check"""
        mock_client_instance = AsyncMock()
        mock_gql_client.return_value = mock_client_instance
        self.client.client = mock_client_instance
        
        # Mock successful teams query
        mock_client_instance.execute_async.return_value = {
            "teams": {"nodes": []}
        }
        
        is_healthy = await self.client.health_check()
        assert is_healthy is True
    
    @patch('agents.shared.linear_tool.Client')
    async def test_health_check_failure(self, mock_gql_client):
        """Test health check failure"""
        mock_client_instance = AsyncMock()
        mock_gql_client.return_value = mock_client_instance
        self.client.client = mock_client_instance
        
        # Mock exception
        mock_client_instance.execute_async.side_effect = Exception("API error")
        
        is_healthy = await self.client.health_check()
        assert is_healthy is False
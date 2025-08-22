"""
Integration tests for Phase 2 components
Tests LLM1↔RAG, LLM2↔Ollama, Linear tool integration
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import json

from agents.llm1.agent import LLM1Agent, UserQuery
from agents.shared.rag_system import RAGSystem, Document
from agents.shared.linear_tool import LinearClient

# Skip LLM2 tests if autogen is not available
try:
    from agents.llm2.agent import LLM2Agent, TaskRequest
    LLM2_AVAILABLE = True
except ImportError:
    LLM2_AVAILABLE = False
    LLM2Agent = None
    TaskRequest = None


@pytest.mark.integration
@pytest.mark.asyncio
class TestLLM1RAGIntegration:
    """Test LLM1 agent integration with RAG system"""
    
    @patch('agents.shared.rag_system.AsyncQdrantClient')
    @patch('agents.shared.rag_system.redis.Redis')
    async def test_llm1_rag_workflow(self, mock_redis, mock_qdrant):
        """Test complete LLM1 workflow with RAG"""
        # Setup mocks
        mock_qdrant_client = AsyncMock()
        mock_qdrant.return_value = mock_qdrant_client
        mock_redis_client = AsyncMock()
        mock_redis.return_value = mock_redis_client
        
        # Create agent
        agent = LLM1Agent()
        agent.rag_system.vector_store.client = mock_qdrant_client
        agent.rag_system.semantic_cache.redis_client = mock_redis_client
        
        # Mock LLM response
        with patch.object(agent.llm_manager, 'generate') as mock_generate:
            mock_generate.return_value = Mock(
                content="Based on the context, here's my response...",
                provider=Mock(value="openai"),
                model="gpt-3.5-turbo"
            )
            
            # Mock RAG search results
            mock_redis_client.get.return_value = None  # Cache miss
            mock_search_result = Mock()
            mock_search_result.payload = {
                "content": "Relevant context about the query",
                "metadata": {"source": "test"},
                "doc_id": "doc1",
                "chunk_id": "doc1_chunk_0"
            }
            mock_search_result.score = 0.85
            mock_qdrant_client.search.return_value = [mock_search_result]
            
            # Test query processing
            query = UserQuery(
                message="What is the status of the project?",
                include_context=True
            )
            
            response = await agent.process_user_query(query)
            
            assert response.response == "Based on the context, here's my response..."
            assert response.provider_used == "openai"
            assert len(response.context_used) == 1
            assert response.context_used[0]["content"] == "Relevant context about the query"
            assert response.context_used[0]["score"] == 0.85


@pytest.mark.integration
@pytest.mark.skipif(not LLM2_AVAILABLE, reason="autogen not available")
@pytest.mark.asyncio
class TestLLM2OllamaIntegration:
    """Test LLM2 agent integration with Ollama"""
    
    @patch('agents.shared.llm_providers.ollama.AsyncClient')
    async def test_llm2_ollama_preference(self, mock_ollama):
        """Test LLM2 prefers Ollama over other providers"""
        # Setup mock Ollama client
        mock_client = AsyncMock()
        mock_ollama.return_value = mock_client
        mock_client.generate.return_value = {
            "response": "Task breakdown: 1. Analyze requirements 2. Create plan 3. Execute"
        }
        
        # Create agent
        agent = LLM2Agent()
        
        # Mock Linear client
        with patch.object(agent.linear_client, 'create_issue') as mock_create_issue:
            mock_issue = Mock()
            mock_issue.id = "issue123"
            mock_issue.title = "Test Task"
            mock_issue.url = "https://linear.app/test/issue/TEST-123"
            mock_issue.identifier = "TEST-123"
            mock_create_issue.return_value = mock_issue
            
            # Test task processing
            task_request = TaskRequest(
                description="Implement new feature for user authentication",
                requester_id="user123",
                priority="high",
                team_id="team1"
            )
            
            response = await agent.process_task_request(task_request)
            
            assert response.status == "planned"
            assert response.agent_used == "ollama"
            assert response.fallback_used is False
            assert response.linear_issue is not None
            assert response.linear_issue["id"] == "issue123"
            
            # Verify audit log
            assert len(agent.audit_log) > 0
            audit_events = [entry.event_type for entry in agent.audit_log]
            assert "task_received" in audit_events
            assert "ollama_used" in audit_events


@pytest.mark.skipif(not LLM2_AVAILABLE, reason="autogen not available")
@pytest.mark.integration
@pytest.mark.asyncio
class TestLLM2FallbackMechanism:
    """Test LLM2 fallback mechanism when Ollama fails"""
    
    @patch('agents.shared.llm_providers.ollama.AsyncClient')
    @patch('agents.shared.config.config')
    async def test_llm2_fallback_allowed(self, mock_config, mock_ollama):
        """Test fallback when ATLAS_LLM2_ALLOW_FALLBACK=true"""
        # Configure fallback enabled
        mock_config.ATLAS_LLM2_ALLOW_FALLBACK = True
        
        # Setup mock Ollama failure
        mock_client = AsyncMock()
        mock_ollama.return_value = mock_client
        mock_client.generate.side_effect = Exception("Ollama connection failed")
        
        # Create agent
        agent = LLM2Agent()
        
        # Mock successful fallback provider
        with patch.object(agent.llm_manager, 'generate') as mock_fallback:
            mock_fallback.return_value = Mock(
                content="Fallback response",
                provider=Mock(value="openai"),
                model="gpt-3.5-turbo"
            )
            
            # Test task processing
            task_request = TaskRequest(
                description="Simple task",
                requester_id="user123",
                priority="medium"
            )
            
            response = await agent.process_task_request(task_request)
            
            assert response.status == "planned"
            assert response.agent_used == "openai"
            assert response.fallback_used is True
            
            # Verify audit log shows fallback usage
            audit_events = [entry.event_type for entry in agent.audit_log]
            assert "ollama_failed" in audit_events
            assert "fallback_initiated" in audit_events
            assert "fallback_succeeded" in audit_events
    
    @patch('agents.shared.llm_providers.ollama.AsyncClient')
    @patch('agents.shared.config.config')
    async def test_llm2_fallback_denied(self, mock_config, mock_ollama):
        """Test that fallback is denied when ATLAS_LLM2_ALLOW_FALLBACK=false"""
        # Configure fallback disabled
        mock_config.ATLAS_LLM2_ALLOW_FALLBACK = False
        
        # Setup mock Ollama failure
        mock_client = AsyncMock()
        mock_ollama.return_value = mock_client
        mock_client.generate.side_effect = Exception("Ollama connection failed")
        
        # Create agent
        agent = LLM2Agent()
        
        # Test task processing should fail
        task_request = TaskRequest(
            description="Simple task",
            requester_id="user123",
            priority="medium"
        )
        
        with pytest.raises(Exception, match="Ollama failed and fallback is disabled"):
            await agent.process_task_request(task_request)
        
        # Verify audit log shows fallback was denied
        audit_events = [entry.event_type for entry in agent.audit_log]
        assert "ollama_failed" in audit_events
        assert "fallback_denied" in audit_events


@pytest.mark.integration
@pytest.mark.asyncio
class TestLinearToolIntegration:
    """Test Linear tool integration in real scenario"""
    
    @patch('agents.shared.linear_tool.Client')
    async def test_linear_workflow(self, mock_gql_client):
        """Test complete Linear workflow: get teams -> create issue -> update issue"""
        mock_client_instance = AsyncMock()
        mock_gql_client.return_value = mock_client_instance
        
        client = LinearClient()
        client.client = mock_client_instance
        
        # Mock teams response
        teams_response = {
            "teams": {
                "nodes": [
                    {"id": "team1", "name": "Engineering", "key": "ENG"}
                ]
            }
        }
        
        # Mock issue creation response
        create_response = {
            "issueCreate": {
                "success": True,
                "issue": {
                    "id": "issue123",
                    "title": "Test Integration Issue",
                    "description": "Integration test issue",
                    "state": {"name": "Todo"},
                    "priority": 2,
                    "url": "https://linear.app/team/issue/ENG-123",
                    "identifier": "ENG-123",
                    "team": {"id": "team1"},
                    "createdAt": "2023-01-01T00:00:00Z",
                    "updatedAt": "2023-01-01T00:00:00Z"
                }
            }
        }
        
        # Mock issue update response
        update_response = {
            "issueUpdate": {
                "success": True,
                "issue": {
                    "id": "issue123",
                    "title": "Updated Integration Issue",
                    "description": "Updated integration test issue",
                    "state": {"name": "In Progress"},
                    "priority": 1,
                    "url": "https://linear.app/team/issue/ENG-123",
                    "identifier": "ENG-123",
                    "team": {"id": "team1"},
                    "createdAt": "2023-01-01T00:00:00Z",
                    "updatedAt": "2023-01-01T01:00:00Z"
                }
            }
        }
        
        # Set up sequential responses
        mock_client_instance.execute_async.side_effect = [
            teams_response,
            create_response,
            update_response
        ]
        
        # 1. Get teams
        teams = await client.get_teams()
        assert len(teams) == 1
        assert teams[0].name == "Engineering"
        
        # 2. Create issue
        issue = await client.create_issue(
            title="Test Integration Issue",
            team_id="team1",
            description="Integration test issue"
        )
        assert issue.id == "issue123"
        assert issue.identifier == "ENG-123"
        
        # 3. Update issue
        updated_issue = await client.update_issue(
            issue_id="issue123",
            title="Updated Integration Issue",
            description="Updated integration test issue"
        )
        assert updated_issue.title == "Updated Integration Issue"
        assert updated_issue.description == "Updated integration test issue"
        
        # Verify all calls were made
        assert mock_client_instance.execute_async.call_count == 3
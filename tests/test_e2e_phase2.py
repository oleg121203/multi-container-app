"""
End-to-end tests for Phase 2: Full user → LLM1 (RAG) → LLM2 (plan + create issue)
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import httpx

from agents.llm1.agent import LLM1Agent, UserQuery
from agents.llm2.agent import LLM2Agent, TaskRequest
from agents.shared.rag_system import Document


@pytest.mark.e2e
@pytest.mark.asyncio
class TestPhase2E2E:
    """End-to-end test for Phase 2 complete workflow"""
    
    async def test_full_user_workflow(self):
        """Test complete workflow: user query → LLM1 (RAG) → LLM2 (Ollama + Linear)"""
        
        # Create agents
        llm1_agent = LLM1Agent()
        llm2_agent = LLM2Agent()
        
        with patch('agents.shared.rag_system.AsyncQdrantClient') as mock_qdrant, \
             patch('agents.shared.rag_system.redis.Redis') as mock_redis, \
             patch('agents.shared.llm_providers.ollama.AsyncClient') as mock_ollama, \
             patch('agents.shared.linear_tool.Client') as mock_linear:
            
            # Setup RAG mocks
            mock_qdrant_client = AsyncMock()
            mock_qdrant.return_value = mock_qdrant_client
            mock_redis_client = AsyncMock()
            mock_redis.return_value = mock_redis_client
            
            llm1_agent.rag_system.vector_store.client = mock_qdrant_client
            llm1_agent.rag_system.semantic_cache.redis_client = mock_redis_client
            
            # Setup Ollama mock
            mock_ollama_client = AsyncMock()
            mock_ollama.return_value = mock_ollama_client
            mock_ollama_client.generate.return_value = {
                "response": '{"issue_title": "Implement user authentication", "issue_description": "Based on the user request, we need to implement a comprehensive user authentication system with login, registration, and password reset functionality.", "execution_plan": ["Design authentication flow", "Set up database schemas", "Implement login/register endpoints", "Add password reset functionality", "Write tests", "Deploy to staging"], "analysis": "This is a complex task requiring both backend and frontend work."}'
            }
            
            # Setup Linear mock
            mock_linear_client = AsyncMock()
            mock_linear.return_value = mock_linear_client
            llm2_agent.linear_client.client = mock_linear_client
            
            mock_linear_client.execute_async.return_value = {
                "issueCreate": {
                    "success": True,
                    "issue": {
                        "id": "issue_auth_123",
                        "title": "Implement user authentication",
                        "description": "Based on the user request, we need to implement a comprehensive user authentication system with login, registration, and password reset functionality.",
                        "state": {"name": "Todo"},
                        "priority": 2,
                        "url": "https://linear.app/team/issue/AUTH-123",
                        "identifier": "AUTH-123",
                        "team": {"id": "engineering_team"},
                        "createdAt": "2023-01-01T00:00:00Z",
                        "updatedAt": "2023-01-01T00:00:00Z"
                    }
                }
            }
            
            # Setup LLM1 mock response
            with patch.object(llm1_agent.llm_manager, 'generate') as mock_llm1_generate:
                mock_llm1_generate.return_value = Mock(
                    content="I understand you need user authentication implemented. Based on the relevant documentation and best practices, I'll help you create a comprehensive authentication system. Let me work with our task orchestrator to break this down into actionable steps and create a tracking issue for this work.",
                    provider=Mock(value="openai"),
                    model="gpt-3.5-turbo"
                )
                
                # Mock RAG search results for context
                mock_redis_client.get.return_value = None  # Cache miss
                mock_search_result = Mock()
                mock_search_result.payload = {
                    "content": "Authentication should include JWT tokens, password hashing with bcrypt, email verification, and rate limiting for security.",
                    "metadata": {"source": "security_guidelines", "category": "authentication"},
                    "doc_id": "security_doc_1",
                    "chunk_id": "security_doc_1_chunk_0"
                }
                mock_search_result.score = 0.92
                mock_qdrant_client.search.return_value = [mock_search_result]
                
                # Step 1: User submits request to LLM1
                user_query = UserQuery(
                    message="I need to implement user authentication for our application. It should include login, registration, and password reset functionality.",
                    include_context=True,
                    max_context_results=5
                )
                
                llm1_response = await llm1_agent.process_user_query(user_query)
                
                # Verify LLM1 response
                assert "authentication" in llm1_response.response.lower()
                assert llm1_response.provider_used == "openai"
                assert len(llm1_response.context_used) == 1
                assert llm1_response.context_used[0]["content"].startswith("Authentication should include JWT tokens")
                assert llm1_response.context_used[0]["score"] == 0.92
                
                # Step 2: LLM1 creates task for LLM2 based on user request
                task_request = TaskRequest(
                    description="Implement comprehensive user authentication system with login, registration, and password reset functionality",
                    requester_id=llm1_response.session_id,
                    priority="high",
                    team_id="engineering_team",
                    metadata={
                        "source": "llm1_user_request",
                        "original_query": user_query.message,
                        "context_score": 0.92
                    }
                )
                
                # Step 3: LLM2 processes the task
                llm2_response = await llm2_agent.process_task_request(task_request)
                
                # Verify LLM2 response
                assert llm2_response.status == "planned"
                assert llm2_response.agent_used == "ollama"
                assert llm2_response.fallback_used is False
                
                # Verify Linear issue was created
                assert llm2_response.linear_issue is not None
                assert llm2_response.linear_issue["identifier"] == "AUTH-123"
                assert llm2_response.linear_issue["title"] == "Implement user authentication"
                
                # Verify execution plan was generated
                assert len(llm2_response.execution_plan) > 0
                plan_text = " ".join(llm2_response.execution_plan).lower()
                assert "authentication" in plan_text
                assert "login" in plan_text or "register" in plan_text
                
                # Verify audit trail
                audit_events = [entry.event_type for entry in llm2_agent.audit_log]
                assert "task_received" in audit_events
                assert "ollama_used" in audit_events
                assert "linear_issue_created" in audit_events
                
                # Step 4: Verify end-to-end data flow
                # User request should be traceable through the entire system
                auth_task_entry = next(
                    (entry for entry in llm2_agent.audit_log if entry.event_type == "task_received"),
                    None
                )
                assert auth_task_entry is not None
                assert "authentication" in auth_task_entry.details["description"].lower()
                assert auth_task_entry.details["requester"] == llm1_response.session_id
                
                # Linear issue should contain information from original user request
                linear_issue_entry = next(
                    (entry for entry in llm2_agent.audit_log if entry.event_type == "linear_issue_created"),
                    None
                )
                assert linear_issue_entry is not None
                assert linear_issue_entry.details["issue_url"] == "https://linear.app/team/issue/AUTH-123"
                
                print("✅ E2E Test passed: User → LLM1 (RAG) → LLM2 (Ollama + Linear)")
                print(f"📋 Created Linear issue: {llm2_response.linear_issue['identifier']}")
                print(f"🎯 Execution plan has {len(llm2_response.execution_plan)} steps")
                print(f"🔍 Used context with score: {llm1_response.context_used[0]['score']}")
                print(f"🤖 LLM1 used: {llm1_response.provider_used}")
                print(f"🤖 LLM2 used: {llm2_response.agent_used} (fallback: {llm2_response.fallback_used})")


@pytest.mark.e2e
@pytest.mark.asyncio  
class TestPhase2ErrorHandling:
    """Test error handling scenarios in E2E workflow"""
    
    async def test_rag_system_fallback_on_vector_db_failure(self):
        """Test that system handles vector DB failures gracefully"""
        
        llm1_agent = LLM1Agent()
        
        with patch('agents.shared.rag_system.AsyncQdrantClient') as mock_qdrant, \
             patch('agents.shared.rag_system.redis.Redis') as mock_redis:
            
            # Setup mocks - Qdrant fails, Redis works
            mock_qdrant_client = AsyncMock()
            mock_qdrant.return_value = mock_qdrant_client
            mock_qdrant_client.search.side_effect = Exception("Qdrant connection failed")
            
            mock_redis_client = AsyncMock()
            mock_redis.return_value = mock_redis_client
            mock_redis_client.get.return_value = None
            
            llm1_agent.rag_system.vector_store.client = mock_qdrant_client
            llm1_agent.rag_system.semantic_cache.redis_client = mock_redis_client
            
            with patch.object(llm1_agent.llm_manager, 'generate') as mock_generate:
                mock_generate.return_value = Mock(
                    content="I can help with your request, though I don't have access to specific context right now.",
                    provider=Mock(value="openai"),
                    model="gpt-3.5-turbo"
                )
                
                user_query = UserQuery(
                    message="Help me with authentication setup",
                    include_context=True
                )
                
                # Should not raise exception despite Qdrant failure
                response = await llm1_agent.process_user_query(user_query)
                
                assert response.response is not None
                assert len(response.context_used) == 0  # No context due to DB failure
                assert response.provider_used == "openai"
                
    async def test_llm2_audit_logging_on_failure(self):
        """Test that failures are properly logged in audit trail"""
        
        llm2_agent = LLM2Agent()
        
        with patch('agents.shared.llm_providers.ollama.AsyncClient') as mock_ollama, \
             patch('agents.shared.linear_tool.Client') as mock_linear:
            
            # Setup Ollama failure
            mock_ollama_client = AsyncMock()
            mock_ollama.return_value = mock_ollama_client
            mock_ollama_client.generate.side_effect = Exception("Ollama service unavailable")
            
            # Setup Linear failure
            mock_linear_client = AsyncMock()
            mock_linear.return_value = mock_linear_client
            mock_linear_client.execute_async.side_effect = Exception("Linear API error")
            
            llm2_agent.linear_client.client = mock_linear_client
            
            task_request = TaskRequest(
                description="Test task for failure handling",
                requester_id="test_user",
                priority="low",
                team_id="test_team"
            )
            
            # Should fail but log the failure
            with pytest.raises(Exception):
                await llm2_agent.process_task_request(task_request)
            
            # Check audit log contains failure events
            audit_events = [entry.event_type for entry in llm2_agent.audit_log]
            assert "task_received" in audit_events
            assert "ollama_failed" in audit_events
            assert "task_processing_failed" in audit_events
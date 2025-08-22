"""
Basic functionality tests for ATLAS agents
Test the current implementation and identify missing components
"""
import pytest
import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

# Set environment variables for testing
os.environ['OPENAI_API_KEY'] = 'test-key'
os.environ['LINEAR_API_KEY'] = 'test-linear-key'
os.environ['ATLAS_LLM2_ALLOW_FALLBACK'] = 'true'


class TestSharedComponents:
    """Test shared components"""
    
    def test_config_loading(self):
        """Test configuration loading"""
        from agents.shared.config import config
        
        assert config.QDRANT_HOST == "qdrant"
        assert config.QDRANT_PORT == 6333
        assert config.OLLAMA_HOST == "ollama"
        assert config.OLLAMA_PORT == 11434
        assert config.OLLAMA_MODEL == "gpt-oss:latest"
    
    def test_config_environment_override(self):
        """Test environment variable override"""
        from agents.shared.config import config
        
        # The test environment variables should be loaded
        assert config.ATLAS_LLM2_ALLOW_FALLBACK == True  # Set in test setup


class TestLLM2Agent:
    """Test LLM2 Agent basic functionality"""
    
    def test_llm2_priority_parsing(self):
        """Test priority string parsing"""
        with patch('agents.llm2.agent.mcp_registry'), \
             patch('agents.llm2.agent.mcp_client'), \
             patch('agents.shared.llm_providers.LLMProviderManager'), \
             patch('agents.shared.llm_providers.OllamaProvider'), \
             patch('agents.shared.linear_tool.LinearClient'):
            
            from agents.llm2.agent import LLM2Agent
            from agents.shared.linear_tool import IssuePriority
            
            agent = LLM2Agent()
            
            assert agent._parse_priority("urgent") == IssuePriority.URGENT
            assert agent._parse_priority("high") == IssuePriority.HIGH
            assert agent._parse_priority("medium") == IssuePriority.MEDIUM
            assert agent._parse_priority("low") == IssuePriority.LOW
            assert agent._parse_priority("unknown") == IssuePriority.MEDIUM  # default
    
    def test_llm2_text_plan_extraction(self):
        """Test plan extraction from text responses"""
        with patch('agents.llm2.agent.mcp_registry'), \
             patch('agents.llm2.agent.mcp_client'), \
             patch('agents.shared.llm_providers.LLMProviderManager'), \
             patch('agents.shared.llm_providers.OllamaProvider'), \
             patch('agents.shared.linear_tool.LinearClient'):
            
            from agents.llm2.agent import LLM2Agent
            
            agent = LLM2Agent()
            
            response_text = """
            Here is the plan:
            1. Analyze the requirements
            2. Design the solution
            3. Implement the code
            4. Test the implementation
            """
            
            plan = agent._extract_plan_from_text(response_text, "Test task")
            
            assert "issue_title" in plan
            assert "issue_description" in plan
            assert "execution_plan" in plan
            assert len(plan["execution_plan"]) == 4
            assert "Analyze the requirements" in plan["execution_plan"]


class TestLLM1Agent:
    """Test LLM1 Agent basic functionality"""
    
    def test_llm1_session_management(self):
        """Test session creation and management"""
        with patch('agents.shared.llm_providers.LLMProviderManager'), \
             patch('agents.shared.rag_system.RAGSystem'):
            
            from agents.llm1.agent import LLM1Agent
            
            agent = LLM1Agent()
            
            # Test session creation without session_id
            session = agent._get_or_create_session(None)
            assert session.session_id is not None
            assert len(session.messages) == 0
            
            # Test session retrieval
            session_id = session.session_id
            retrieved_session = agent._get_or_create_session(session_id)
            assert retrieved_session.session_id == session_id
            assert retrieved_session is session


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
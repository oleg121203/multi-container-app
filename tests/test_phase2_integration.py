"""
Phase 2 Integration Tests for ATLAS agents
Test the core Phase 2 requirements: MEM-01, ORC-01, CFG-01, CFG-02
"""
import pytest
import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch, Mock
import json

# Set test environment variables
os.environ.update({
    'OPENAI_API_KEY': 'test-openai-key',
    'LINEAR_API_KEY': 'test-linear-key',
    'ATLAS_LLM2_ALLOW_FALLBACK': 'true',
    'QDRANT_HOST': 'localhost',
    'REDIS_HOST': 'localhost',
    'OLLAMA_HOST': 'localhost',
})


class TestPhase2Requirements:
    """Test Phase 2 requirements implementation"""
    
    def test_mem01_rag_system_components(self):
        """MEM-01: Test RAG system components exist and can be initialized"""
        from agents.shared.rag_system import RAGSystem, Document, DocumentChunk, SearchResult, TextChunker
        
        # Test that core RAG components can be imported and initialized
        rag_system = RAGSystem()
        assert rag_system is not None
        
        # Test document structure
        doc = Document(
            content="Test document content",
            metadata={"source": "test"},
            doc_id="test-doc-1"
        )
        assert doc.content == "Test document content"
        assert doc.doc_id == "test-doc-1"
        
        # Test text chunker
        chunker = TextChunker(chunk_size=100, chunk_overlap=20)
        assert chunker.chunk_size == 100
        assert chunker.chunk_overlap == 20
    
    def test_cfg01_llm_provider_abstraction(self):
        """CFG-01: Test LLM provider abstraction exists"""
        from agents.shared.llm_providers import LLMProviderManager, LLMProvider
        
        # Test provider manager initialization
        with patch('agents.shared.llm_providers.QdrantClient'), \
             patch('agents.shared.llm_providers.redis'):
            manager = LLMProviderManager()
            assert manager is not None
        
        # Test that all required providers are defined
        assert hasattr(LLMProvider, 'OPENAI')
        assert hasattr(LLMProvider, 'ANTHROPIC')
        assert hasattr(LLMProvider, 'GOOGLE')
        assert hasattr(LLMProvider, 'OLLAMA')
    
    def test_orc01_linear_tool_integration(self):
        """ORC-01: Test Linear tool integration exists"""
        from agents.shared.linear_tool import LinearClient, LinearIssue, IssuePriority
        
        # Test Linear client can be initialized
        with patch('agents.shared.linear_tool.httpx.AsyncClient'):
            client = LinearClient()
            assert client is not None
        
        # Test priority enum
        assert IssuePriority.URGENT is not None
        assert IssuePriority.HIGH is not None
        assert IssuePriority.MEDIUM is not None
        assert IssuePriority.LOW is not None
    
    def test_cfg02_llm2_ollama_binding(self):
        """CFG-02: Test LLM2 Ollama strict binding configuration"""
        from agents.shared.config import config
        
        # Test Ollama configuration
        assert config.OLLAMA_HOST == "localhost"  # From test env
        assert config.OLLAMA_PORT == 11434
        assert config.OLLAMA_MODEL == "gpt-oss:latest"
        assert config.ATLAS_LLM2_ALLOW_FALLBACK == True  # From test env
    
    @pytest.mark.asyncio
    async def test_llm1_rag_integration(self):
        """Test LLM1 agent RAG integration"""
        with patch('agents.shared.llm_providers.LLMProviderManager'), \
             patch('agents.shared.rag_system.RAGSystem') as mock_rag, \
             patch('agents.shared.rag_system.AsyncQdrantClient'), \
             patch('agents.shared.rag_system.redis'):
            
            from agents.llm1.agent import LLM1Agent
            
            # Setup mock RAG system
            mock_rag_instance = AsyncMock()
            mock_rag.return_value = mock_rag_instance
            mock_rag_instance.search_relevant_context.return_value = []
            mock_rag_instance.format_context.return_value = "Mock context"
            
            agent = LLM1Agent()
            
            # Test that RAG system is initialized
            assert agent.rag_system is not None
            
            # Test prompt building with context
            prompt = agent._build_context_prompt("Test message", [])
            assert "Test message" in prompt
            assert "LLM1" in prompt
    
    @pytest.mark.asyncio 
    async def test_llm2_ollama_preference(self):
        """Test LLM2 Ollama preference and fallback logic"""
        with patch('agents.llm2.agent.mcp_registry'), \
             patch('agents.llm2.agent.mcp_client'), \
             patch('agents.shared.llm_providers.LLMProviderManager'), \
             patch('agents.shared.llm_providers.OllamaProvider') as mock_ollama, \
             patch('agents.shared.linear_tool.LinearClient'):
            
            from agents.llm2.agent import LLM2Agent
            
            # Setup mock Ollama provider
            mock_ollama_instance = AsyncMock()
            mock_ollama.return_value = mock_ollama_instance
            
            agent = LLM2Agent()
            
            # Test that Ollama provider is configured
            assert agent.ollama_provider is not None
            
            # Test audit logging functionality
            await agent._log_audit_event("test_event", {"key": "value"}, "info")
            assert len(agent.audit_log) == 1
            assert agent.audit_log[0].event_type == "test_event"
    
    def test_autogen_integration(self):
        """Test AutoGen framework integration in LLM2"""
        with patch('agents.llm2.agent.mcp_registry'), \
             patch('agents.llm2.agent.mcp_client'), \
             patch('agents.shared.llm_providers.LLMProviderManager'), \
             patch('agents.shared.llm_providers.OllamaProvider'), \
             patch('agents.shared.linear_tool.LinearClient'), \
             patch('autogen.AssistantAgent') as mock_assistant, \
             patch('autogen.UserProxyAgent') as mock_proxy:
            
            from agents.llm2.agent import LLM2Agent
            
            agent = LLM2Agent()
            
            # Verify AutoGen agents are created
            mock_assistant.assert_called_once()
            mock_proxy.assert_called_once()
            
            assert agent.assistant_agent is not None
            assert agent.user_proxy is not None


class TestKubernetesManifests:
    """Test that required Kubernetes manifests exist"""
    
    def test_k8s_manifests_exist(self):
        """Test that all required K8s manifests are present"""
        import os
        
        manifest_dir = "/home/runner/work/multi-container-app/multi-container-app/infra/k8s/manual"
        
        # Check that key manifests exist
        required_manifests = [
            "08-vector-database.yaml",  # Qdrant and Redis
            "09-ollama.yaml",           # Ollama service
            "10-atlas-agents.yaml",     # LLM1, LLM2, LLM3 agents
            "11-atlas-secrets-template.yaml"  # Secrets template
        ]
        
        for manifest in required_manifests:
            manifest_path = os.path.join(manifest_dir, manifest)
            assert os.path.exists(manifest_path), f"Required manifest {manifest} is missing"
    
    def test_agent_manifests_content(self):
        """Test that agent manifests contain required components"""
        manifest_path = "/home/runner/work/multi-container-app/multi-container-app/infra/k8s/manual/10-atlas-agents.yaml"
        
        with open(manifest_path, 'r') as f:
            content = f.read()
        
        # Check that all three agents are defined
        assert "name: llm1" in content
        assert "name: llm2" in content  
        assert "name: llm3" in content
        
        # Check important environment variables
        assert "OLLAMA_HOST" in content
        assert "QDRANT_HOST" in content
        assert "ATLAS_LLM2_ALLOW_FALLBACK" in content
    
    def test_vector_database_manifest_content(self):
        """Test vector database manifest content"""
        manifest_path = "/home/runner/work/multi-container-app/multi-container-app/infra/k8s/manual/08-vector-database.yaml"
        
        with open(manifest_path, 'r') as f:
            content = f.read()
        
        # Check Qdrant configuration
        assert "qdrant/qdrant" in content
        assert "6333" in content  # Qdrant HTTP port
        assert "6334" in content  # Qdrant gRPC port
        
        # Check Redis configuration
        assert "redis:7-alpine" in content
        assert "6379" in content  # Redis port


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
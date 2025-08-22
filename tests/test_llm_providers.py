"""
Unit tests for LLM provider abstraction (CFG-01)
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch

from agents.shared.llm_providers import (
    LLMProviderManager, LLMProvider, LLMResponse,
    OpenAIProvider, AnthropicProvider, GoogleProvider, OllamaProvider
)


@pytest.mark.asyncio
class TestOpenAIProvider:
    """Test OpenAI provider implementation"""
    
    @patch('agents.shared.llm_providers.openai.AsyncOpenAI')
    async def test_generate_success(self, mock_openai):
        """Test successful OpenAI response generation"""
        # Setup mock
        mock_client = AsyncMock()
        mock_openai.return_value = mock_client
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.usage.dict.return_value = {"total_tokens": 100}
        mock_client.chat.completions.create.return_value = mock_response
        
        provider = OpenAIProvider("test_key")
        result = await provider.generate("test prompt")
        
        assert isinstance(result, LLMResponse)
        assert result.content == "Test response"
        assert result.provider == LLMProvider.OPENAI
        assert result.usage["total_tokens"] == 100
    
    @patch('agents.shared.llm_providers.openai.AsyncOpenAI')
    async def test_health_check(self, mock_openai):
        """Test OpenAI health check"""
        mock_client = AsyncMock()
        mock_openai.return_value = mock_client
        mock_client.models.list.return_value = []
        
        provider = OpenAIProvider("test_key")
        is_healthy = await provider.health_check()
        assert is_healthy is True


@pytest.mark.asyncio
class TestOllamaProvider:
    """Test Ollama provider implementation"""
    
    @patch('agents.shared.llm_providers.ollama.AsyncClient')
    async def test_generate_success(self, mock_ollama):
        """Test successful Ollama response generation"""
        mock_client = AsyncMock()
        mock_ollama.return_value = mock_client
        mock_client.generate.return_value = {"response": "Ollama test response"}
        
        provider = OllamaProvider("localhost", 11434, "test-model")
        result = await provider.generate("test prompt")
        
        assert isinstance(result, LLMResponse)
        assert result.content == "Ollama test response"
        assert result.provider == LLMProvider.OLLAMA
    
    @patch('agents.shared.llm_providers.ollama.AsyncClient')
    async def test_health_check(self, mock_ollama):
        """Test Ollama health check"""
        mock_client = AsyncMock()
        mock_ollama.return_value = mock_client
        mock_client.list.return_value = []
        
        provider = OllamaProvider("localhost", 11434, "test-model")
        is_healthy = await provider.health_check()
        assert is_healthy is True


@pytest.mark.asyncio
class TestLLMProviderManager:
    """Test LLM provider manager with fallback chain"""
    
    @patch('agents.shared.llm_providers.config')
    def test_init_providers(self, mock_config):
        """Test provider initialization"""
        mock_config.OPENAI_API_KEY = "test_openai_key"
        mock_config.ANTHROPIC_API_KEY = "test_anthropic_key"
        mock_config.GOOGLE_API_KEY = None
        mock_config.OLLAMA_HOST = "localhost"
        mock_config.OLLAMA_PORT = 11434
        mock_config.OLLAMA_MODEL = "test-model"
        mock_config.LLM_FALLBACK_CHAIN = ["openai", "anthropic", "ollama"]
        
        manager = LLMProviderManager()
        
        assert LLMProvider.OPENAI in manager.providers
        assert LLMProvider.ANTHROPIC in manager.providers
        assert LLMProvider.OLLAMA in manager.providers
        assert LLMProvider.GOOGLE not in manager.providers
    
    @patch('agents.shared.llm_providers.config')
    async def test_generate_with_fallback(self, mock_config):
        """Test generation with fallback chain"""
        mock_config.OPENAI_API_KEY = "test_key"
        mock_config.ANTHROPIC_API_KEY = None
        mock_config.GOOGLE_API_KEY = None
        mock_config.OLLAMA_HOST = "localhost"
        mock_config.OLLAMA_PORT = 11434
        mock_config.OLLAMA_MODEL = "test-model"
        mock_config.LLM_FALLBACK_CHAIN = ["openai", "ollama"]
        
        manager = LLMProviderManager()
        
        # Mock providers
        mock_openai_provider = AsyncMock()
        mock_ollama_provider = AsyncMock()
        
        # First provider fails, second succeeds
        mock_openai_provider.generate.side_effect = Exception("OpenAI failed")
        mock_ollama_provider.generate.return_value = LLMResponse(
            content="Ollama response",
            provider=LLMProvider.OLLAMA,
            model="test-model"
        )
        
        manager.providers[LLMProvider.OPENAI] = mock_openai_provider
        manager.providers[LLMProvider.OLLAMA] = mock_ollama_provider
        
        result = await manager.generate("test prompt", allow_fallback=True)
        
        assert result.content == "Ollama response"
        assert result.provider == LLMProvider.OLLAMA
        
        # Verify both providers were tried
        mock_openai_provider.generate.assert_called_once()
        mock_ollama_provider.generate.assert_called_once()
    
    @patch('agents.shared.llm_providers.config')
    async def test_preferred_provider_success(self, mock_config):
        """Test successful generation with preferred provider"""
        mock_config.OPENAI_API_KEY = "test_key"
        mock_config.ANTHROPIC_API_KEY = None
        mock_config.GOOGLE_API_KEY = None
        mock_config.OLLAMA_HOST = "localhost"
        mock_config.OLLAMA_PORT = 11434
        mock_config.OLLAMA_MODEL = "test-model"
        mock_config.LLM_FALLBACK_CHAIN = ["openai", "ollama"]
        
        manager = LLMProviderManager()
        
        # Mock providers
        mock_openai_provider = AsyncMock()
        mock_openai_provider.generate.return_value = LLMResponse(
            content="OpenAI response",
            provider=LLMProvider.OPENAI,
            model="gpt-3.5-turbo"
        )
        
        manager.providers[LLMProvider.OPENAI] = mock_openai_provider
        
        result = await manager.generate(
            "test prompt",
            preferred_provider=LLMProvider.OPENAI,
            allow_fallback=True
        )
        
        assert result.content == "OpenAI response"
        assert result.provider == LLMProvider.OPENAI
        mock_openai_provider.generate.assert_called_once()
    
    @patch('agents.shared.llm_providers.config')
    async def test_no_fallback_on_preferred_failure(self, mock_config):
        """Test that fallback is not used when allow_fallback=False"""
        mock_config.OPENAI_API_KEY = "test_key"
        mock_config.OLLAMA_HOST = "localhost"
        mock_config.OLLAMA_PORT = 11434
        mock_config.OLLAMA_MODEL = "test-model"
        mock_config.LLM_FALLBACK_CHAIN = ["openai", "ollama"]
        
        manager = LLMProviderManager()
        
        # Mock providers
        mock_openai_provider = AsyncMock()
        mock_openai_provider.generate.side_effect = Exception("OpenAI failed")
        
        manager.providers[LLMProvider.OPENAI] = mock_openai_provider
        
        with pytest.raises(Exception, match="OpenAI failed"):
            await manager.generate(
                "test prompt",
                preferred_provider=LLMProvider.OPENAI,
                allow_fallback=False
            )
    
    @patch('agents.shared.llm_providers.config')
    async def test_health_check_all(self, mock_config):
        """Test health check for all providers"""
        mock_config.OPENAI_API_KEY = "test_key"
        mock_config.OLLAMA_HOST = "localhost"
        mock_config.OLLAMA_PORT = 11434
        mock_config.OLLAMA_MODEL = "test-model"
        mock_config.LLM_FALLBACK_CHAIN = ["openai", "ollama"]
        
        manager = LLMProviderManager()
        
        # Mock providers
        mock_openai_provider = AsyncMock()
        mock_ollama_provider = AsyncMock()
        mock_openai_provider.health_check.return_value = True
        mock_ollama_provider.health_check.return_value = False
        
        manager.providers[LLMProvider.OPENAI] = mock_openai_provider
        manager.providers[LLMProvider.OLLAMA] = mock_ollama_provider
        
        health_results = await manager.health_check_all()
        
        assert health_results[LLMProvider.OPENAI] is True
        assert health_results[LLMProvider.OLLAMA] is False
"""
LLM Provider Abstraction Layer (CFG-01)
Unified interface for OpenAI, Anthropic, Google, and Ollama with configurable fallback chain.
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from enum import Enum

import openai
import anthropic
import google.generativeai as genai
import ollama
from pydantic import BaseModel

from .config import config

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"


class LLMResponse(BaseModel):
    content: str
    provider: LLMProvider
    model: str
    usage: Optional[Dict[str, Any]] = None


class BaseLLMProvider(ABC):
    """Base class for LLM providers"""
    
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        pass


class OpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        self.client = openai.AsyncOpenAI(api_key=api_key)
        self.model = model
    
    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                **kwargs
            )
            return LLMResponse(
                content=response.choices[0].message.content,
                provider=LLMProvider.OPENAI,
                model=self.model,
                usage=response.usage.dict() if response.usage else None
            )
        except Exception as e:
            logger.error(f"OpenAI provider error: {e}")
            raise
    
    async def health_check(self) -> bool:
        try:
            await self.client.models.list()
            return True
        except:
            return False


class AnthropicProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model: str = "claude-3-haiku-20240307"):
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model
    
    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=kwargs.get("max_tokens", 1000),
                messages=[{"role": "user", "content": prompt}]
            )
            return LLMResponse(
                content=response.content[0].text,
                provider=LLMProvider.ANTHROPIC,
                model=self.model,
                usage={"input_tokens": response.usage.input_tokens, 
                      "output_tokens": response.usage.output_tokens}
            )
        except Exception as e:
            logger.error(f"Anthropic provider error: {e}")
            raise
    
    async def health_check(self) -> bool:
        try:
            # Anthropic doesn't have a direct health check, so we make a minimal request
            await self.client.messages.create(
                model=self.model,
                max_tokens=1,
                messages=[{"role": "user", "content": "test"}]
            )
            return True
        except:
            return False


class GoogleProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model: str = "gemini-pro"):
        genai.configure(api_key=api_key)
        self.model_name = model
        self.model = genai.GenerativeModel(model)
    
    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        try:
            response = await asyncio.to_thread(self.model.generate_content, prompt)
            return LLMResponse(
                content=response.text,
                provider=LLMProvider.GOOGLE,
                model=self.model_name
            )
        except Exception as e:
            logger.error(f"Google provider error: {e}")
            raise
    
    async def health_check(self) -> bool:
        try:
            await asyncio.to_thread(self.model.generate_content, "test")
            return True
        except:
            return False


class OllamaProvider(BaseLLMProvider):
    def __init__(self, host: str = "localhost", port: int = 11434, model: str = "gpt-oss:latest"):
        self.client = ollama.AsyncClient(host=f"http://{host}:{port}")
        self.model = model
    
    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        try:
            response = await self.client.generate(
                model=self.model,
                prompt=prompt,
                **kwargs
            )
            return LLMResponse(
                content=response["response"],
                provider=LLMProvider.OLLAMA,
                model=self.model
            )
        except Exception as e:
            logger.error(f"Ollama provider error: {e}")
            raise
    
    async def health_check(self) -> bool:
        try:
            await self.client.list()
            return True
        except:
            return False


class LLMProviderManager:
    """Manages multiple LLM providers with fallback chain"""
    
    def __init__(self, fallback_chain: Optional[List[str]] = None):
        self.providers: Dict[LLMProvider, BaseLLMProvider] = {}
        self.fallback_chain = fallback_chain or config.LLM_FALLBACK_CHAIN
        self._init_providers()
    
    def _init_providers(self):
        """Initialize available providers based on configuration"""
        if config.OPENAI_API_KEY:
            self.providers[LLMProvider.OPENAI] = OpenAIProvider(config.OPENAI_API_KEY)
        
        if config.ANTHROPIC_API_KEY:
            self.providers[LLMProvider.ANTHROPIC] = AnthropicProvider(config.ANTHROPIC_API_KEY)
        
        if config.GOOGLE_API_KEY:
            self.providers[LLMProvider.GOOGLE] = GoogleProvider(config.GOOGLE_API_KEY)
        
        # Ollama is always available
        self.providers[LLMProvider.OLLAMA] = OllamaProvider(
            host=config.OLLAMA_HOST,
            port=config.OLLAMA_PORT,
            model=config.OLLAMA_MODEL
        )
    
    async def generate(self, prompt: str, preferred_provider: Optional[LLMProvider] = None, 
                      allow_fallback: bool = True, **kwargs) -> LLMResponse:
        """Generate response with fallback chain"""
        
        # If preferred provider is specified and available, try it first
        if preferred_provider and preferred_provider in self.providers:
            try:
                return await self.providers[preferred_provider].generate(prompt, **kwargs)
            except Exception as e:
                logger.warning(f"Preferred provider {preferred_provider} failed: {e}")
                if not allow_fallback:
                    raise
        
        # Try fallback chain
        for provider_name in self.fallback_chain:
            provider_enum = LLMProvider(provider_name)
            if provider_enum in self.providers:
                try:
                    logger.info(f"Trying provider: {provider_name}")
                    return await self.providers[provider_enum].generate(prompt, **kwargs)
                except Exception as e:
                    logger.warning(f"Provider {provider_name} failed: {e}")
                    continue
        
        raise Exception("All LLM providers failed")
    
    async def health_check_all(self) -> Dict[LLMProvider, bool]:
        """Check health of all providers"""
        results = {}
        for provider_type, provider in self.providers.items():
            results[provider_type] = await provider.health_check()
        return results
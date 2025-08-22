"""
Shared configuration and utilities for ATLAS agents
"""
import os
from typing import Dict, List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class AtlasConfig(BaseSettings):
    """Global configuration for ATLAS system"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"  # Ignore extra fields from .env
    )
    
    # Vector database settings (MEM-01)
    QDRANT_HOST: str = "qdrant"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION_NAME: str = "atlas_memory"
    
    # Redis cache settings
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_TTL: int = 3600  # 1 hour default TTL
    SEMANTIC_SIMILARITY_THRESHOLD: float = 0.85
    
    # LLM Provider settings (CFG-01)
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    
    # Ollama settings (CFG-02)
    OLLAMA_HOST: str = "ollama"
    OLLAMA_PORT: int = 11434
    OLLAMA_MODEL: str = "gpt-oss:latest"
    ATLAS_LLM2_ALLOW_FALLBACK: bool = False
    
    # LLM fallback chain (CFG-01)
    LLM_FALLBACK_CHAIN: List[str] = ["ollama", "openai", "anthropic", "google"]
    
    # Linear API settings
    LINEAR_API_KEY: Optional[str] = None
    LINEAR_API_URL: str = "https://api.linear.app/graphql"
    
    # MCP Hub settings
    ATLAS_MCP_SERVERS: str = "playwright,automation,tts"
    
    # Monitoring
    PROMETHEUS_PORT: int = 8000


# Global config instance
config = AtlasConfig()
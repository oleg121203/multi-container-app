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
    
    # Phase 4: Agent Registry settings
    ATLAS_AGENT_REGISTRY_ENABLED: bool = True
    ATLAS_AGENT_REGISTRY_PATH: str = "./config/agents.json"
    ATLAS_AGENT_REGISTRY_PORT: int = 8500
    ATLAS_AGENT_REGISTRY_DISCOVERY_INTERVAL: int = 30
    ATLAS_AGENT_REGISTRY_HEALTH_TIMEOUT: int = 10
    ATLAS_AGENT_REGISTRY_STORAGE_BACKEND: str = "redis"
    
    # Team Constructor settings
    ATLAS_TEAM_CONSTRUCTOR_ENABLED: bool = True
    ATLAS_TEAM_MAX_SIZE: int = 5
    ATLAS_TEAM_FORMATION_TIMEOUT: int = 30
    ATLAS_TEAM_COORDINATION_MODE: str = "event_driven"


# Global config instance
config = AtlasConfig()
from setuptools import setup, find_packages

setup(
    name="atlas-agents",
    version="0.1.0",
    description="ATLAS Multi-Agent LLM System - Phase 2",
    packages=find_packages(),
    python_requires=">=3.11",
    install_requires=[
        "fastapi>=0.104.1",
        "uvicorn>=0.24.0",
        "pydantic>=2.5.0",
        "pydantic-settings>=2.10.1",
        "python-dotenv>=1.0.0",
        "qdrant-client>=1.7.0",
        "sentence-transformers>=2.2.2",
        "langchain>=0.1.0",
        "langchain-community>=0.0.10",
        "tiktoken>=0.5.2",
        "redis>=5.0.1",
        "hiredis>=2.2.3",
        "openai>=1.6.1",
        "anthropic>=0.8.1",
        "google-generativeai>=0.3.2",
        "ollama>=0.1.7",
        "pyautogen>=0.2.0",
        "autogen>=0.2.0",
        "gql>=3.4.1",
        "requests>=2.31.0",
        "httpx>=0.25.2",
        "prometheus-client>=0.19.0",
        "structlog>=23.2.0",
    ],
    extras_require={
        "test": [
            "pytest>=7.4.3",
            "pytest-asyncio>=0.21.1",
            "pytest-mock>=3.12.0",
            "coverage>=7.3.2",
            "pytest-cov>=4.1.0",
        ],
        "dev": [
            "black>=23.11.0",
            "ruff>=0.1.7",
            "mypy>=1.7.1",
        ]
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.11",
    ],
)
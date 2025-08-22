#!/bin/bash
set -e

# ATLAS Phase 3 Setup Script
# Sets up MCP Hub, Playwright automation, LLM3 security, and TTS/STT capabilities

echo "🚀 Setting up ATLAS Phase 3: MCP Hub, Security, and Automation"

# Check requirements
echo "🔍 Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    echo "❌ Docker is required but not installed"
    exit 1
fi

if ! command -v docker compose &> /dev/null; then
    echo "❌ Docker Compose is required but not installed"
    exit 1
fi

# Check environment file
if [ ! -f .env ]; then
    echo "📝 Creating .env file from example..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your API keys before running services"
else
    echo "✅ .env file found"
fi

# Validate compose file
echo "🔧 Validating Docker Compose configuration..."
docker compose config --quiet
echo "✅ Docker Compose configuration is valid"

# Create necessary directories
echo "📁 Creating required directories..."
mkdir -p logs/
mkdir -p data/screenshots/
mkdir -p data/audio/
mkdir -p config/falco/
echo "✅ Directories created"

# Pull base images (this can take a while)
echo "📦 Pulling required Docker images..."
docker compose pull qdrant redis ollama

# Build Phase 3 services
echo "🏗️  Building Phase 3 services..."
echo "   • Building LLM3 Security Agent..."
docker compose build llm3-agent

echo "   • Building Playwright MCP Server..."
docker compose build mcp-playwright

echo "✅ All Phase 3 services built successfully"

# Start Phase 2 infrastructure first
echo "🚀 Starting Phase 2 infrastructure..."
docker compose up -d qdrant redis ollama

# Wait for infrastructure to be ready
echo "⏳ Waiting for infrastructure services..."
sleep 10

# Check infrastructure health
echo "🔍 Checking infrastructure health..."
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if docker compose exec -T qdrant curl -f http://localhost:6333/health > /dev/null 2>&1 && \
       docker compose exec -T redis redis-cli ping > /dev/null 2>&1; then
        echo "✅ Infrastructure services are healthy"
        break
    fi
    
    attempt=$((attempt + 1))
    echo "   Attempt $attempt/$max_attempts - waiting for services..."
    sleep 5
done

if [ $attempt -eq $max_attempts ]; then
    echo "❌ Infrastructure services failed to start properly"
    echo "📋 Checking service logs..."
    docker compose logs qdrant redis ollama
    exit 1
fi

# Start LLM agents
echo "🧠 Starting LLM agents..."
docker compose up -d llm1-agent llm2-agent llm3-agent

# Start MCP services
echo "🔧 Starting MCP Hub services..."
docker compose up -d mcp-playwright mcp-tts coqui-tts mcp-stt

# Start Falco (without dependencies to avoid circular dependency)
echo "🛡️  Starting Falco security monitoring..."
docker compose up -d falco

# Wait for all services
echo "⏳ Waiting for all services to start..."
sleep 15

# Health check all services
echo "🔍 Performing health checks..."

services=("llm1-agent:8001" "llm2-agent:8002" "llm3-agent:8003" "mcp-playwright:4001" "mcp-tts:4004")

for service in "${services[@]}"; do
    IFS=':' read -r name port <<< "$service"
    
    max_attempts=10
    attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -f http://localhost:$port/health > /dev/null 2>&1; then
            echo "✅ $name is healthy"
            break
        fi
        
        attempt=$((attempt + 1))
        if [ $attempt -eq $max_attempts ]; then
            echo "⚠️  $name health check failed - may still be starting"
        else
            sleep 3
        fi
    done
done

# Show service status
echo ""
echo "📊 Phase 3 Service Status:"
echo "=========================="
docker compose ps

echo ""
echo "🎉 ATLAS Phase 3 setup complete!"
echo ""
echo "📋 Available services:"
echo "   • LLM1 Agent (UI + RAG):       http://localhost:8001"
echo "   • LLM2 Agent (Orchestrator):   http://localhost:8002" 
echo "   • LLM3 Agent (Security):       http://localhost:8003"
echo "   • Playwright MCP:              http://localhost:4001"
echo "   • TTS MCP:                     http://localhost:4004"
echo "   • STT MCP:                     http://localhost:8080"
echo "   • Qdrant (Vector DB):          http://localhost:6333"
echo "   • Redis (Cache):               redis://localhost:6379"
echo "   • Ollama (Local LLM):          http://localhost:11434"
echo ""
echo "🧪 Run the demo:"
echo "   python scripts/demo-phase3.py"
echo ""
echo "🧪 Run tests:"
echo "   pytest tests/test_phase3.py -v"
echo ""
echo "📜 View logs:"
echo "   docker compose logs -f [service-name]"
echo ""
echo "🛑 Stop all services:"
echo "   docker compose down"
echo ""

# Display important notes
echo "📝 Important Notes:"
echo "==================="
echo "• Make sure to configure API keys in .env file"
echo "• Falco requires privileged mode for security monitoring"
echo "• Playwright runs in isolated containers for security"
echo "• LLM3 auto-mitigation is disabled by default"
echo "• Voice features require additional provider setup"
echo ""

echo "✅ Phase 3 setup completed successfully!"
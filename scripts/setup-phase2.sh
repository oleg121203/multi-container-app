#!/bin/bash
# ATLAS Phase 2 Setup Script
# Transition from Phase 1 infrastructure to Phase 2 core agents

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "\n${BLUE}=== $1 ===${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_header "ATLAS Phase 2 Setup & Transition"

echo "🚀 Welcome to ATLAS Phase 2: Core Agents & RAG"
echo "This script will set up the Phase 2 environment and demonstrate the transition from Phase 1."
echo

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed or not available"
    exit 1
fi

# Check if docker compose is available
if ! command -v docker compose &> /dev/null; then
    print_error "Docker Compose is not installed or not available"
    exit 1
fi

print_header "Step 1: Environment Setup"

# Check for .env file
if [[ ! -f "$PROJECT_ROOT/.env" ]]; then
    print_warning ".env file not found. Creating from .env.example..."
    cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
    print_info "Please edit .env file with your API keys before proceeding"
    print_info "Required for Phase 2:"
    echo "  - OPENAI_API_KEY (for LLM1 user interface)"
    echo "  - LINEAR_API_KEY (for issue management)"
    echo "  - OLLAMA_MODEL=gpt-oss:latest (for LLM2 orchestrator)"
    echo
    read -p "Press Enter to continue after setting up .env file..."
fi

print_success "Environment configuration ready"

print_header "Step 2: Phase 2 Services Validation"

print_info "Validating Docker Compose configuration..."
cd "$PROJECT_ROOT"

if docker compose config --services > /dev/null 2>&1; then
    print_success "Docker Compose configuration is valid"
else
    print_error "Docker Compose configuration has errors"
    exit 1
fi

print_info "Phase 2 services to be deployed:"
docker compose config --services | grep -E "(qdrant|redis|ollama|llm1-agent|llm2-agent)" | while read service; do
    echo "  📦 $service"
done

print_header "Step 3: Starting Phase 2 Infrastructure"

print_info "Starting Phase 2 core services..."

# Start infrastructure services first
print_info "Starting vector database (Qdrant)..."
docker compose up -d qdrant

print_info "Starting cache layer (Redis)..."
docker compose up -d redis

print_info "Starting LLM service (Ollama)..."
docker compose up -d ollama

# Wait for services to be ready
print_info "Waiting for services to be ready..."
sleep 10

# Check service health
print_info "Checking service health..."

# Check Qdrant
if curl -s http://localhost:6333/health > /dev/null 2>&1; then
    print_success "Qdrant is ready"
else
    print_warning "Qdrant not yet ready (may need more time)"
fi

# Check Redis
if docker compose exec redis redis-cli ping > /dev/null 2>&1; then
    print_success "Redis is ready"
else
    print_warning "Redis not yet ready"
fi

# Check Ollama
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    print_success "Ollama is ready"
else
    print_warning "Ollama not yet ready (may need more time to download models)"
fi

print_header "Step 4: Starting Phase 2 Agents"

print_info "Building and starting LLM1 Agent (User Interface + RAG)..."
docker compose up -d --build llm1-agent

print_info "Building and starting LLM2 Agent (Orchestrator + Ollama)..."
docker compose up -d --build llm2-agent

print_info "Waiting for agents to be ready..."
sleep 15

# Check agent health
if curl -s http://localhost:8001/health > /dev/null 2>&1; then
    print_success "LLM1 Agent is ready"
else
    print_warning "LLM1 Agent not yet ready"
fi

if curl -s http://localhost:8002/health > /dev/null 2>&1; then
    print_success "LLM2 Agent is ready"
else
    print_warning "LLM2 Agent not yet ready"
fi

print_header "Step 5: Phase 2 Status Summary"

print_success "Phase 2 transition completed!"
echo
print_info "Available services:"
echo "📊 LLM1 Agent (User Interface + RAG): http://localhost:8001"
echo "🤖 LLM2 Agent (Orchestrator): http://localhost:8002"
echo "🔍 Qdrant (Vector Database): http://localhost:6333"
echo "⚡ Redis (Cache): localhost:6379"
echo "🧠 Ollama (Local LLM): http://localhost:11434"
echo

print_header "Step 6: Testing Phase 2 Functionality"

print_info "Testing LLM1 Agent health..."
if curl -s -X GET http://localhost:8001/health | grep -q "healthy"; then
    print_success "LLM1 Agent health check passed"
else
    print_warning "LLM1 Agent health check failed"
fi

print_info "Testing LLM2 Agent health..."
if curl -s -X GET http://localhost:8002/health | grep -q "healthy"; then
    print_success "LLM2 Agent health check passed"
else
    print_warning "LLM2 Agent health check failed"
fi

print_header "Next Steps"

echo "🎯 Phase 2 is now ready for use!"
echo
echo "Try these commands to test the system:"
echo
echo "1. Test LLM1 Agent (User Interface with RAG):"
echo "   curl -X POST http://localhost:8001/chat \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"message\": \"Hello, can you help me with a task?\"}'"
echo
echo "2. Test LLM2 Agent (Task Orchestrator):"
echo "   curl -X POST http://localhost:8002/process_task \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"description\": \"Create a new feature\", \"requester_id\": \"user123\", \"priority\": \"high\"}'"
echo
echo "3. Check Ollama models:"
echo "   curl http://localhost:11434/api/tags"
echo
echo "4. Monitor agent logs:"
echo "   docker compose logs llm1-agent"
echo "   docker compose logs llm2-agent"
echo

print_info "To proceed to Phase 3 (MCP Hub, Automation, Security), run:"
echo "   gh workflow run atlas-execution-plan.yml -f phase=phase3"
echo

print_success "ATLAS Phase 2 setup complete! 🚀"
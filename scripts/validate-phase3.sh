#!/bin/bash
set -e

# ATLAS Phase 3 Validation Script
# Comprehensive testing and validation of Phase 3 implementation

echo "🧪 ATLAS Phase 3 Validation & Testing Suite"
echo "==========================================="

# Configuration
VALIDATION_LOG="validation-results.log"
TEST_RESULTS_DIR="test-results"
TIMESTAMP=$(date '+%Y-%m-%d_%H-%M-%S')

# Create test results directory
mkdir -p $TEST_RESULTS_DIR

# Logging function
log_test() {
    local status=$1
    local test_name=$2
    local details=$3
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] $status: $test_name - $details" | tee -a $VALIDATION_LOG
}

log_success() {
    log_test "✅ PASS" "$1" "$2"
}

log_failure() {
    log_test "❌ FAIL" "$1" "$2"
}

log_warning() {
    log_test "⚠️  WARN" "$1" "$2"
}

log_info() {
    log_test "ℹ️  INFO" "$1" "$2"
}

# Initialize validation log
echo "ATLAS Phase 3 Validation Results - $TIMESTAMP" > $VALIDATION_LOG
echo "=============================================" >> $VALIDATION_LOG

echo ""
echo "🔍 Phase 1: Infrastructure Testing"
echo "==================================="

# Test 1: Docker and Docker Compose availability
echo "Testing Docker and Docker Compose..."
if command -v docker &> /dev/null && command -v docker compose &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    COMPOSE_VERSION=$(docker compose version --short 2>/dev/null || echo "unknown")
    log_success "Docker Infrastructure" "Docker: $DOCKER_VERSION, Compose: $COMPOSE_VERSION"
else
    log_failure "Docker Infrastructure" "Docker or Docker Compose not available"
    exit 1
fi

# Test 2: Docker Compose Configuration Validation
echo "Validating Docker Compose configuration..."
if docker compose config --quiet 2>/dev/null; then
    log_success "Docker Compose Config" "Configuration is valid"
else
    log_failure "Docker Compose Config" "Invalid configuration"
    exit 1
fi

# Test 3: Environment File Validation
echo "Checking environment configuration..."
if [ -f .env ]; then
    log_success "Environment File" ".env file exists"
    # Check key environment variables
    if grep -q "ATLAS_MCP_SERVERS" .env; then
        log_success "MCP Configuration" "MCP servers configured in .env"
    else
        log_warning "MCP Configuration" "ATLAS_MCP_SERVERS not found in .env"
    fi
else
    log_warning "Environment File" ".env file not found, using defaults"
fi

# Test 4: Required Directories
echo "Creating required directories..."
mkdir -p logs/ data/screenshots/ data/audio/ config/falco/
if [ -d "logs" ] && [ -d "data/screenshots" ] && [ -d "data/audio" ] && [ -d "config/falco" ]; then
    log_success "Directory Structure" "All required directories exist"
else
    log_failure "Directory Structure" "Failed to create required directories"
fi

echo ""
echo "🏗️  Phase 2: Service Architecture Testing"
echo "========================================"

# Test 5: Phase 3 Component Structure
echo "Validating Phase 3 component structure..."

EXPECTED_COMPONENTS=(
    "agents/mcp_hub"
    "agents/llm3"
    "agents/mcp_servers"
    "tests/test_phase3.py"
    "scripts/demo-phase3.py"
    "scripts/setup-phase3.sh"
)

for component in "${EXPECTED_COMPONENTS[@]}"; do
    if [ -e "$component" ]; then
        log_success "Component Structure" "$component exists"
    else
        log_failure "Component Structure" "$component missing"
    fi
done

# Test 6: Docker Service Definitions
echo "Validating Docker service definitions..."

EXPECTED_SERVICES=(
    "llm3-agent"
    "mcp-playwright"
    "mcp-tts"
    "coqui-tts"
    "mcp-stt"
    "falco"
)

for service in "${EXPECTED_SERVICES[@]}"; do
    if docker compose config --services | grep -q "^$service\$"; then
        log_success "Service Definition" "$service defined in compose.yaml"
    else
        log_failure "Service Definition" "$service not found in compose.yaml"
    fi
done

echo ""
echo "📋 Phase 3: Test Infrastructure Validation"
echo "========================================="

# Test 7: Test File Structure
echo "Checking test infrastructure..."

if [ -f "tests/test_phase3.py" ]; then
    log_success "Test Infrastructure" "Phase 3 tests exist"
    
    # Check test functions
    TEST_FUNCTIONS=$(grep -c "def test_" tests/test_phase3.py || echo "0")
    log_info "Test Coverage" "Found $TEST_FUNCTIONS test functions"
else
    log_failure "Test Infrastructure" "tests/test_phase3.py not found"
fi

if [ -f "scripts/demo-phase3.py" ]; then
    log_success "Demo Infrastructure" "Phase 3 demo script exists"
else
    log_failure "Demo Infrastructure" "scripts/demo-phase3.py not found"
fi

# Test 8: Python Dependencies Check
echo "Checking Python dependencies..."
if [ -f "agents/requirements.txt" ]; then
    log_success "Dependencies" "requirements.txt exists"
    
    # Count dependencies
    DEPS_COUNT=$(wc -l < agents/requirements.txt)
    log_info "Dependencies" "Found $DEPS_COUNT dependency entries"
else
    log_failure "Dependencies" "agents/requirements.txt not found"
fi

# Test 9: Configuration Files
echo "Checking configuration files..."

CONFIG_FILES=(
    "pytest.ini"
    ".gitignore"
    "PHASE3_SUMMARY.md"
)

for config_file in "${CONFIG_FILES[@]}"; do
    if [ -f "$config_file" ]; then
        log_success "Configuration" "$config_file exists"
    else
        log_warning "Configuration" "$config_file not found"
    fi
done

echo ""
echo "🔧 Phase 4: Component Validation"
echo "==============================="

# Test 10: MCP Hub Implementation
echo "Validating MCP Hub implementation..."
if [ -d "agents/mcp_hub" ]; then
    MCP_FILES=(
        "agents/mcp_hub/registry.py"
        "agents/mcp_hub/client.py"
    )
    
    for mcp_file in "${MCP_FILES[@]}"; do
        if [ -f "$mcp_file" ]; then
            log_success "MCP Hub" "$(basename $mcp_file) exists"
        else
            log_warning "MCP Hub" "$(basename $mcp_file) not found"
        fi
    done
else
    log_failure "MCP Hub" "MCP Hub directory not found"
fi

# Test 11: LLM3 Security Agent
echo "Validating LLM3 Security Agent..."
if [ -f "agents/llm3/agent.py" ]; then
    log_success "LLM3 Security" "LLM3 agent implementation exists"
    
    # Check for key security functions
    if grep -q "_process_security_event" agents/llm3/agent.py; then
        log_success "LLM3 Security" "Security event processing implemented"
    else
        log_warning "LLM3 Security" "Security event processing not found"
    fi
else
    log_failure "LLM3 Security" "agents/llm3/agent.py not found"
fi

# Test 12: MCP Server Implementation
echo "Validating MCP Server implementations..."
if [ -d "agents/mcp_servers" ]; then
    log_success "MCP Servers" "MCP servers directory exists"
    
    # Check for specific MCP servers
    if [ -d "agents/mcp_servers/playwright" ]; then
        log_success "MCP Servers" "Playwright MCP server exists"
    else
        log_warning "MCP Servers" "Playwright MCP server directory not found"
    fi
else
    log_failure "MCP Servers" "MCP servers directory not found"
fi

echo ""
echo "📊 Phase 5: Documentation and Summary"
echo "===================================="

# Test 13: Documentation Completeness
echo "Checking documentation..."

if [ -f "PHASE3_SUMMARY.md" ]; then
    log_success "Documentation" "Phase 3 summary exists"
    
    # Check for key sections
    SECTIONS=(
        "📊 Key Features Delivered"
        "🧪 Testing & Validation"
        "🏗️ Architecture Overview"
        "🚀 Next Steps: Phase 4"
    )
    
    for section in "${SECTIONS[@]}"; do
        if grep -q "$section" PHASE3_SUMMARY.md; then
            log_success "Documentation" "Section '$section' found"
        else
            log_warning "Documentation" "Section '$section' missing"
        fi
    done
else
    log_failure "Documentation" "PHASE3_SUMMARY.md not found"
fi

echo ""
echo "📈 Validation Summary"
echo "==================="

# Generate summary
PASSED=$(grep "✅ PASS" $VALIDATION_LOG | wc -l)
FAILED=$(grep "❌ FAIL" $VALIDATION_LOG | wc -l)
WARNINGS=$(grep "⚠️  WARN" $VALIDATION_LOG | wc -l)
TOTAL=$((PASSED + FAILED + WARNINGS))

echo "Total Tests: $TOTAL"
echo "Passed: $PASSED"
echo "Failed: $FAILED"
echo "Warnings: $WARNINGS"

# Copy validation log to test results
cp $VALIDATION_LOG "$TEST_RESULTS_DIR/validation-$TIMESTAMP.log"

if [ "$FAILED" -eq 0 ]; then
    echo ""
    echo "🎉 Phase 3 Infrastructure Validation: PASSED"
    echo "All critical tests passed. Ready for service testing."
    exit 0
else
    echo ""
    echo "❌ Phase 3 Infrastructure Validation: FAILED"
    echo "$FAILED critical tests failed. Please address issues before proceeding."
    exit 1
fi
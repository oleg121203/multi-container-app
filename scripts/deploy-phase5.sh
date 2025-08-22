#!/bin/bash

# ATLAS Phase 5 Production Deployment Script
# 
# This script deploys the enhanced ATLAS web interface with all Phase 5 features
# including voice capabilities, advanced team management, performance monitoring,
# and production-ready configurations.

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEPLOYMENT_ENV="${DEPLOYMENT_ENV:-production}"
WEB_PORT="${WEB_PORT:-8000}"
LOG_FILE="/tmp/atlas-phase5-deployment-$(date +%Y%m%d_%H%M%S).log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

# Error handling
handle_error() {
    log_error "Deployment failed at line $1"
    log_error "Check log file: $LOG_FILE"
    exit 1
}

trap 'handle_error $LINENO' ERR

print_banner() {
    echo "
🚀 ATLAS Phase 5 Production Deployment
======================================

Environment: $DEPLOYMENT_ENV
Web Port: $WEB_PORT
Log File: $LOG_FILE
Project Root: $PROJECT_ROOT

Phase 5 Features:
✨ Enhanced Web Interface with 3D Avatar
🎤 Voice Interaction (TTS/STT) 
👥 Advanced Team Management
📊 Real-time Performance Monitoring
🔄 Error Recovery and Resilience
📈 Advanced Analytics and Diagnostics
"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is required but not installed"
        exit 1
    fi
    
    # Check required Python packages
    if ! python3 -c "import fastapi, uvicorn, websockets" 2>/dev/null; then
        log_warning "Installing required Python packages..."
        pip3 install fastapi uvicorn websockets requests
    fi
    
    # Check project structure
    if [[ ! -f "$PROJECT_ROOT/web/api/server.py" ]]; then
        log_error "ATLAS web server not found at $PROJECT_ROOT/web/api/server.py"
        exit 1
    fi
    
    if [[ ! -f "$PROJECT_ROOT/web/frontend/index.html" ]]; then
        log_error "ATLAS frontend not found at $PROJECT_ROOT/web/frontend/index.html"
        exit 1
    fi
    
    log_success "Prerequisites check completed"
}

setup_environment() {
    log_info "Setting up environment..."
    
    # Create environment file if it doesn't exist
    ENV_FILE="$PROJECT_ROOT/.env"
    if [[ ! -f "$ENV_FILE" ]]; then
        log_info "Creating environment configuration..."
        cp "$PROJECT_ROOT/.env.example" "$ENV_FILE" 2>/dev/null || true
    fi
    
    # Set up Python path
    export PYTHONPATH="$PROJECT_ROOT${PYTHONPATH:+:$PYTHONPATH}"
    
    # Create logs directory
    mkdir -p "$PROJECT_ROOT/logs"
    
    log_success "Environment setup completed"
}

start_backend_services() {
    log_info "Starting ATLAS backend services..."
    
    # Start the web API server
    cd "$PROJECT_ROOT"
    
    log_info "Starting ATLAS Web Interface API on port $WEB_PORT..."
    
    # Kill any existing process on the port
    if lsof -ti:$WEB_PORT >/dev/null 2>&1; then
        log_warning "Killing existing process on port $WEB_PORT"
        kill -9 $(lsof -ti:$WEB_PORT) || true
        sleep 2
    fi
    
    # Start the server in background
    nohup python3 -c "
import sys
sys.path.insert(0, '.')
from web.api.server import app
import uvicorn
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info('Starting ATLAS Web Interface API Server...')
uvicorn.run(app, host='0.0.0.0', port=$WEB_PORT, log_level='info')
" > "$PROJECT_ROOT/logs/atlas-web-api.log" 2>&1 &
    
    WEB_PID=$!
    echo $WEB_PID > "$PROJECT_ROOT/logs/atlas-web-api.pid"
    
    # Wait for server to start
    log_info "Waiting for server to start..."
    sleep 5
    
    # Check if server is running
    if curl -s "http://localhost:$WEB_PORT/health" >/dev/null 2>&1; then
        log_success "ATLAS Web API started successfully (PID: $WEB_PID)"
    else
        log_error "Failed to start ATLAS Web API"
        exit 1
    fi
}

run_health_checks() {
    log_info "Running health checks..."
    
    # Test basic endpoints
    ENDPOINTS=(
        "/health"
        "/api/agents"
        "/api/system/status"
        "/api/metrics"
    )
    
    for endpoint in "${ENDPOINTS[@]}"; do
        if curl -s "http://localhost:$WEB_PORT$endpoint" >/dev/null 2>&1; then
            log_success "✓ $endpoint"
        else
            log_error "✗ $endpoint - Health check failed"
        fi
    done
    
    log_success "Health checks completed"
}

run_e2e_tests() {
    log_info "Running E2E tests..."
    
    if [[ -f "$PROJECT_ROOT/tests/test_e2e_phase5.py" ]]; then
        cd "$PROJECT_ROOT"
        
        # Install test dependencies if needed
        pip3 install websockets >/dev/null 2>&1 || true
        
        # Run E2E tests
        if python3 tests/test_e2e_phase5.py; then
            log_success "E2E tests passed"
        else
            log_warning "Some E2E tests failed - check test output"
        fi
    else
        log_warning "E2E tests not found, skipping..."
    fi
}

setup_monitoring() {
    log_info "Setting up monitoring and logging..."
    
    # Create monitoring script
    cat > "$PROJECT_ROOT/scripts/monitor-atlas.sh" << 'EOF'
#!/bin/bash
# ATLAS System Monitor

ATLAS_PID_FILE="logs/atlas-web-api.pid"
ATLAS_PORT="8000"

if [[ -f "$ATLAS_PID_FILE" ]]; then
    PID=$(cat "$ATLAS_PID_FILE")
    if ps -p $PID > /dev/null; then
        echo "✅ ATLAS Web API is running (PID: $PID)"
        
        # Check health endpoint
        if curl -s "http://localhost:$ATLAS_PORT/health" >/dev/null; then
            echo "✅ Health check passed"
        else
            echo "❌ Health check failed"
        fi
        
        # Show resource usage
        echo "📊 Resource Usage:"
        ps -p $PID -o pid,ppid,pcpu,pmem,time,comm
    else
        echo "❌ ATLAS Web API is not running"
    fi
else
    echo "❌ PID file not found - ATLAS may not be running"
fi
EOF
    
    chmod +x "$PROJECT_ROOT/scripts/monitor-atlas.sh"
    
    # Create stop script
    cat > "$PROJECT_ROOT/scripts/stop-atlas.sh" << 'EOF'
#!/bin/bash
# Stop ATLAS Services

ATLAS_PID_FILE="logs/atlas-web-api.pid"

if [[ -f "$ATLAS_PID_FILE" ]]; then
    PID=$(cat "$ATLAS_PID_FILE")
    if ps -p $PID > /dev/null; then
        echo "Stopping ATLAS Web API (PID: $PID)..."
        kill $PID
        sleep 2
        
        if ps -p $PID > /dev/null; then
            echo "Force killing ATLAS Web API..."
            kill -9 $PID
        fi
        
        rm "$ATLAS_PID_FILE"
        echo "✅ ATLAS Web API stopped"
    else
        echo "ATLAS Web API was not running"
        rm "$ATLAS_PID_FILE"
    fi
else
    echo "PID file not found - ATLAS may not be running"
fi
EOF
    
    chmod +x "$PROJECT_ROOT/scripts/stop-atlas.sh"
    
    log_success "Monitoring setup completed"
}

create_systemd_service() {
    if [[ "$DEPLOYMENT_ENV" == "production" ]] && command -v systemctl &> /dev/null; then
        log_info "Creating systemd service..."
        
        cat > "/tmp/atlas-web.service" << EOF
[Unit]
Description=ATLAS Web Interface API
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_ROOT
Environment=PYTHONPATH=$PROJECT_ROOT
ExecStart=/usr/bin/python3 -c "import sys; sys.path.insert(0, '.'); from web.api.server import app; import uvicorn; uvicorn.run(app, host='0.0.0.0', port=$WEB_PORT)"
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
        
        if sudo cp "/tmp/atlas-web.service" "/etc/systemd/system/" 2>/dev/null; then
            sudo systemctl daemon-reload
            sudo systemctl enable atlas-web
            log_success "Systemd service created and enabled"
        else
            log_warning "Could not create systemd service (requires sudo)"
        fi
    fi
}

print_deployment_info() {
    echo "
🎉 ATLAS Phase 5 Deployment Complete!
=====================================

📍 Access Points:
   Web Interface: http://localhost:$WEB_PORT
   API Documentation: http://localhost:$WEB_PORT/docs
   Health Check: http://localhost:$WEB_PORT/health

🚀 Phase 5 Features Available:
   ✨ Enhanced 3D Avatar Interface
   🎤 Voice Interaction (TTS/STT)
   👥 Advanced Team Management  
   📊 Real-time Performance Monitoring
   🔄 Automatic Error Recovery
   📈 Advanced Analytics Dashboard

🛠️  Management Commands:
   Monitor: ./scripts/monitor-atlas.sh
   Stop: ./scripts/stop-atlas.sh
   Logs: tail -f logs/atlas-web-api.log

📊 Deployment Log: $LOG_FILE

🔍 Quick Test:
   curl http://localhost:$WEB_PORT/health

Next Steps:
1. Open http://localhost:$WEB_PORT in your browser
2. Test voice features (click MIC button)
3. Create dynamic teams (click FORM TEAM)
4. Monitor performance in the metrics panel
5. Review logs for any issues

Happy orchestrating! 🤖
"
}

# Main deployment flow
main() {
    print_banner
    check_prerequisites
    setup_environment
    start_backend_services
    run_health_checks
    setup_monitoring
    create_systemd_service
    
    # Optional E2E tests (don't fail deployment if they fail)
    run_e2e_tests || log_warning "E2E tests had issues but deployment continues"
    
    print_deployment_info
    
    log_success "ATLAS Phase 5 deployment completed successfully!"
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
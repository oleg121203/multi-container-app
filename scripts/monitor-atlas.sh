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

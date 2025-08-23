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

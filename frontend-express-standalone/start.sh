#!/bin/bash

# MCP Hub Express Standalone - Quick Test Script

echo "🚀 Starting MCP Hub Express Standalone..."

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+ first."
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "❌ npm is not installed. Please install npm first."
    exit 1
fi

# Check if dependencies are installed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install dependencies"
        exit 1
    fi
fi

# Check if model file exists
if [ ! -f "models/DamagedHelmet.glb" ]; then
    echo "❌ Model file not found: models/DamagedHelmet.glb"
    echo "Please ensure the 3D model is copied to the models/ directory"
    exit 1
fi

# Start the server
echo "🌟 Starting Express server..."
node server.js &
SERVER_PID=$!

# Wait a moment for server to start
sleep 3

# Test server health
echo "🔍 Testing server health..."
curl -s http://localhost:3050/api/health > /dev/null
if [ $? -eq 0 ]; then
    echo "✅ Server is running successfully!"
    echo "🌐 Open http://localhost:3050 in your browser"
    echo "📊 Health endpoint: http://localhost:3050/api/health"
    echo "🤖 3D Model: http://localhost:3050/models/DamagedHelmet.glb"
    echo ""
    echo "Press Ctrl+C to stop the server"
    
    # Keep the script running to show server output
    wait $SERVER_PID
else
    echo "❌ Server failed to start properly"
    kill $SERVER_PID 2>/dev/null
    exit 1
fi

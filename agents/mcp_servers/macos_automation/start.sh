#!/bin/bash

# Clean up any existing X11 locks
rm -f /tmp/.X99-lock
rm -f /tmp/.X11-unix/X99

# Create Xauthority file
touch ~/.Xauthority

# Start Xvfb in background with no authentication
Xvfb :99 -screen 0 1024x768x24 -ac -nolisten tcp &
XVFB_PID=$!

# Wait for Xvfb to be ready
echo "Starting Xvfb..."
sleep 3

# Check if Xvfb is running
if ! kill -0 $XVFB_PID 2>/dev/null; then
    echo "ERROR: Xvfb failed to start"
    exit 1
fi

# Set display environment variable
export DISPLAY=:99

# Test X11 connection
echo "Testing X11 connection..."
xdpyinfo -display :99 > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "ERROR: Cannot connect to X11 display :99"
    exit 1
fi

echo "X11 display ready, starting Python server..."

# Start the Python server
exec python server.py

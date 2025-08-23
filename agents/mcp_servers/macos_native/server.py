#!/usr/bin/env python3
"""
MCP macOS Native Automation Server

Provides native macOS automation through AppleScript and Objective-C APIs.
"""

import os
import asyncio
import logging
import subprocess
import importlib
import json
from typing import List, Dict, Any, Optional

import mcp.types as types
from mcp.server import Server
import mcp.server.stdio
from fastapi import FastAPI
import uvicorn

# Optional macOS native frameworks (only on macOS). Use importlib to avoid static import errors.
try:
    Foundation = importlib.import_module("Foundation")  # type: ignore[assignment]
    AppKit = importlib.import_module("AppKit")  # type: ignore[assignment]
    ApplicationServices = importlib.import_module("ApplicationServices")  # type: ignore[assignment]
    NATIVE_APIS_AVAILABLE = True
except Exception:
    logging.warning("Native macOS APIs not available")
    Foundation = None  # type: ignore[assignment]
    AppKit = None  # type: ignore[assignment]
    ApplicationServices = None  # type: ignore[assignment]
    NATIVE_APIS_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
MCP_PORT = int(os.getenv("MCP_MACOS_NATIVE_PORT", 4008))
NATIVE_AUTOMATION = os.getenv("NATIVE_AUTOMATION", "true").lower() == "true"

# Initialize MCP server
app = Server("macos-native")

def run_applescript(script: str) -> str:
    """Execute AppleScript and return result"""
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"AppleScript error: {e.stderr}")

def run_shortcuts_command(shortcut_name: str, input_data: Optional[str] = None) -> str:
    """Run a Shortcuts command"""
    try:
        cmd = ["shortcuts", "run", shortcut_name]
        if input_data:
            cmd.extend(["--input-path", "-"])
        
        result = subprocess.run(
            cmd,
            input=input_data,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Shortcuts error: {e.stderr}")

@app.list_tools()
async def handle_list_tools() -> List[types.Tool]:
    """List available native automation tools"""
    tools = [
        types.Tool(
            name="applescript",
            description="Execute AppleScript code",
            inputSchema={
                "type": "object",
                "properties": {
                    "script": {
                        "type": "string",
                        "description": "AppleScript code to execute"
                    }
                },
                "required": ["script"]
            }
        ),
        types.Tool(
            name="shortcuts_run",
            description="Run a macOS Shortcuts shortcut",
            inputSchema={
                "type": "object",
                "properties": {
                    "shortcut_name": {
                        "type": "string",
                        "description": "Name of the shortcut to run"
                    },
                    "input_data": {
                        "type": "string",
                        "description": "Optional input data for the shortcut"
                    }
                },
                "required": ["shortcut_name"]
            }
        ),
        types.Tool(
            name="shortcuts_list",
            description="List available shortcuts",
            inputSchema={"type": "object", "properties": {}}
        ),
        types.Tool(
            name="notification_send",
            description="Send a native macOS notification",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Notification title"
                    },
                    "subtitle": {
                        "type": "string",
                        "description": "Notification subtitle"
                    },
                    "message": {
                        "type": "string",
                        "description": "Notification message"
                    },
                    "sound": {
                        "type": "string",
                        "description": "Notification sound name",
                        "default": "default"
                    }
                },
                "required": ["title", "message"]
            }
        ),
        types.Tool(
            name="app_launch",
            description="Launch a macOS application",
            inputSchema={
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "Name of the application to launch"
                    },
                    "wait_for_launch": {
                        "type": "boolean",
                        "description": "Wait for application to launch",
                        "default": True
                    }
                },
                "required": ["app_name"]
            }
        ),
        types.Tool(
            name="app_quit",
            description="Quit a macOS application",
            inputSchema={
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "Name of the application to quit"
                    },
                    "force": {
                        "type": "boolean",
                        "description": "Force quit if necessary",
                        "default": False
                    }
                },
                "required": ["app_name"]
            }
        ),
        types.Tool(
            name="app_list_running",
            description="List currently running applications",
            inputSchema={"type": "object", "properties": {}}
        ),
        types.Tool(
            name="clipboard_get",
            description="Get clipboard contents",
            inputSchema={"type": "object", "properties": {}}
        ),
        types.Tool(
            name="clipboard_set",
            description="Set clipboard contents",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to set in clipboard"
                    }
                },
                "required": ["text"]
            }
        ),
        types.Tool(
            name="volume_get",
            description="Get system volume level",
            inputSchema={"type": "object", "properties": {}}
        ),
        types.Tool(
            name="volume_set",
            description="Set system volume level",
            inputSchema={
                "type": "object",
                "properties": {
                    "volume": {
                        "type": "integer",
                        "description": "Volume level (0-100)",
                        "minimum": 0,
                        "maximum": 100
                    }
                },
                "required": ["volume"]
            }
        )
    ]
    
    return tools

@app.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Handle tool calls"""
    try:
        if name == "applescript":
            script = arguments["script"]
            result = run_applescript(script)
            return [types.TextContent(
                type="text",
                text=f"AppleScript executed successfully:\n{result}"
            )]
        
        elif name == "shortcuts_run":
            shortcut_name = arguments["shortcut_name"]
            input_data = arguments.get("input_data")
            result = run_shortcuts_command(shortcut_name, input_data)
            return [types.TextContent(
                type="text",
                text=f"Shortcut '{shortcut_name}' executed:\n{result}"
            )]
        
        elif name == "shortcuts_list":
            result = subprocess.run(
                ["shortcuts", "list"],
                capture_output=True,
                text=True,
                check=True
            )
            shortcuts = [line.strip() for line in result.stdout.split('\n') if line.strip()]
            return [types.TextContent(
                type="text",
                text=f"Available shortcuts ({len(shortcuts)}):\n" + "\n".join(f"- {s}" for s in shortcuts)
            )]
        
        elif name == "notification_send":
            title = arguments["title"]
            subtitle = arguments.get("subtitle", "")
            message = arguments["message"]
            sound = arguments.get("sound", "default")
            
            script = f'''
            display notification "{message}" with title "{title}"'''
            if subtitle:
                script += f''' subtitle "{subtitle}"'''
            if sound != "default":
                script += f''' sound name "{sound}"'''
            
            run_applescript(script)
            return [types.TextContent(
                type="text",
                text=f"Notification sent: {title}"
            )]
        
        elif name == "app_launch":
            app_name = arguments["app_name"]
            wait_for_launch = arguments.get("wait_for_launch", True)
            
            script = f'tell application "{app_name}" to activate'
            if wait_for_launch:
                script = f'tell application "{app_name}" to launch'
            
            run_applescript(script)
            return [types.TextContent(
                type="text",
                text=f"Application '{app_name}' launched"
            )]
        
        elif name == "app_quit":
            app_name = arguments["app_name"]
            force = arguments.get("force", False)
            
            if force:
                script = f'tell application "{app_name}" to quit without saving'
            else:
                script = f'tell application "{app_name}" to quit'
            
            try:
                run_applescript(script)
                return [types.TextContent(
                    type="text",
                    text=f"Application '{app_name}' quit"
                )]
            except RuntimeError as e:
                return [types.TextContent(
                    type="text",
                    text=f"Could not quit '{app_name}': {e}"
                )]
        
        elif name == "app_list_running":
            script = '''
            tell application "System Events"
                get name of every application process whose background only is false
            end tell
            '''
            result = run_applescript(script)
            apps = [app.strip() for app in result.split(',')]
            return [types.TextContent(
                type="text",
                text=f"Running applications ({len(apps)}):\n" + "\n".join(f"- {app}" for app in apps)
            )]
        
        elif name == "clipboard_get":
            script = 'the clipboard'
            result = run_applescript(script)
            return [types.TextContent(
                type="text",
                text=f"Clipboard contents:\n{result}"
            )]
        
        elif name == "clipboard_set":
            text = arguments["text"]
            script = f'set the clipboard to "{text}"'
            run_applescript(script)
            return [types.TextContent(
                type="text",
                text=f"Clipboard set to: {text[:100]}{'...' if len(text) > 100 else ''}"
            )]
        
        elif name == "volume_get":
            script = 'output volume of (get volume settings)'
            result = run_applescript(script)
            return [types.TextContent(
                type="text",
                text=f"Current volume: {result}%"
            )]
        
        elif name == "volume_set":
            volume = arguments["volume"]
            script = f'set volume output volume {volume}'
            run_applescript(script)
            return [types.TextContent(
                type="text",
                text=f"Volume set to: {volume}%"
            )]
        
        else:
            raise ValueError(f"Unknown tool: {name}")
    
    except Exception as e:
        logger.error(f"Error in tool {name}: {e}")
        return [types.TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]

# FastAPI health check endpoint
fastapi_app = FastAPI()

@fastapi_app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "macos-native-mcp",
        "native_automation": NATIVE_AUTOMATION,
        "native_apis_available": NATIVE_APIS_AVAILABLE,
        "platform": "darwin" if os.name == "posix" else "unknown"
    }

async def main():
    """Run the MCP server"""
    logger.info(f"Starting macOS Native MCP Server on port {MCP_PORT}")
    logger.info(f"Native automation: {NATIVE_AUTOMATION}")
    logger.info(f"Native APIs available: {NATIVE_APIS_AVAILABLE}")
    
    # Start FastAPI server for health checks
    config = uvicorn.Config(fastapi_app, host="0.0.0.0", port=MCP_PORT, log_level="info")
    server = uvicorn.Server(config)
    
    async def _run_mcp_stdio():
        # Correct usage of stdio server: use as async context manager and run the MCP app
        from mcp.server.stdio import stdio_server
        async with stdio_server() as (read, write):
            await app.run(read, write, app.create_initialization_options())
    
    # Run both servers
    await asyncio.gather(
        server.serve(),
        _run_mcp_stdio()
    )

if __name__ == "__main__":
    asyncio.run(main())

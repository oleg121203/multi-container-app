#!/usr/bin/env python3
"""
MCP macOS Automation Server

Provides GUI automation capabilities through PyAutoGUI with safety controls.
"""

import os
import asyncio
import logging
import time
from typing import List, Dict, Any, Tuple
import base64
from io import BytesIO

import mcp.types as types
from mcp.server import Server
import mcp.server.stdio
from fastapi import FastAPI
import uvicorn

try:
    import pyautogui
    import cv2
    import numpy as np
    from PIL import Image
    
    # Configure PyAutoGUI safety
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.1
    
except ImportError as e:
    logging.warning(f"Some automation libraries not available: {e}")
    pyautogui = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
MCP_PORT = int(os.getenv("MCP_MACOS_PORT", 4007))
AUTOMATION_MODE = os.getenv("AUTOMATION_MODE", "safe")  # safe, full
CLICK_DELAY = float(os.getenv("CLICK_DELAY", "0.1"))
MOVE_DURATION = float(os.getenv("MOVE_DURATION", "0.5"))

# Initialize MCP server
app = Server("macos-automation")

def validate_coordinates(x: int, y: int) -> Tuple[int, int]:
    """Validate and clamp coordinates to screen bounds"""
    if not pyautogui:
        raise RuntimeError("PyAutoGUI not available")
    
    screen_width, screen_height = pyautogui.size()
    x = max(0, min(x, screen_width - 1))
    y = max(0, min(y, screen_height - 1))
    return x, y

def safe_automation_check():
    """Check if automation is allowed and safe"""
    if not pyautogui:
        raise RuntimeError("GUI automation not available in this environment")
    
    if AUTOMATION_MODE == "safe":
        # Additional safety checks can be added here
        pass

@app.list_tools()
async def handle_list_tools() -> List[types.Tool]:
    """List available automation tools"""
    tools = [
        types.Tool(
            name="screenshot",
            description="Take a screenshot of the current screen",
            inputSchema={
                "type": "object",
                "properties": {
                    "region": {
                        "type": "object",
                        "description": "Region to capture (x, y, width, height)",
                        "properties": {
                            "x": {"type": "integer"},
                            "y": {"type": "integer"},
                            "width": {"type": "integer"},
                            "height": {"type": "integer"}
                        }
                    },
                    "return_base64": {
                        "type": "boolean",
                        "description": "Return image as base64 encoded string",
                        "default": False
                    }
                }
            }
        ),
        types.Tool(
            name="mouse_click",
            description="Click at specified coordinates",
            inputSchema={
                "type": "object",
                "properties": {
                    "x": {
                        "type": "integer",
                        "description": "X coordinate"
                    },
                    "y": {
                        "type": "integer",
                        "description": "Y coordinate"
                    },
                    "button": {
                        "type": "string",
                        "description": "Mouse button to click",
                        "enum": ["left", "right", "middle"],
                        "default": "left"
                    },
                    "clicks": {
                        "type": "integer",
                        "description": "Number of clicks",
                        "default": 1
                    }
                },
                "required": ["x", "y"]
            }
        ),
        types.Tool(
            name="mouse_move",
            description="Move mouse to specified coordinates",
            inputSchema={
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "X coordinate"},
                    "y": {"type": "integer", "description": "Y coordinate"},
                    "duration": {
                        "type": "number",
                        "description": "Movement duration in seconds",
                        "default": 0.5
                    }
                },
                "required": ["x", "y"]
            }
        ),
        types.Tool(
            name="key_press",
            description="Press keyboard keys",
            inputSchema={
                "type": "object",
                "properties": {
                    "keys": {
                        "type": "string",
                        "description": "Key or key combination to press (e.g., 'enter', 'cmd+c', 'shift+tab')"
                    },
                    "interval": {
                        "type": "number",
                        "description": "Interval between key presses",
                        "default": 0.1
                    }
                },
                "required": ["keys"]
            }
        ),
        types.Tool(
            name="type_text",
            description="Type text at current cursor position",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to type"
                    },
                    "interval": {
                        "type": "number",
                        "description": "Interval between characters",
                        "default": 0.01
                    }
                },
                "required": ["text"]
            }
        ),
        types.Tool(
            name="find_image",
            description="Find image on screen and return coordinates",
            inputSchema={
                "type": "object",
                "properties": {
                    "image_path": {
                        "type": "string",
                        "description": "Path to template image file"
                    },
                    "confidence": {
                        "type": "number",
                        "description": "Confidence threshold (0.0-1.0)",
                        "default": 0.8
                    },
                    "region": {
                        "type": "object",
                        "description": "Search region (x, y, width, height)",
                        "properties": {
                            "x": {"type": "integer"},
                            "y": {"type": "integer"},
                            "width": {"type": "integer"},
                            "height": {"type": "integer"}
                        }
                    }
                },
                "required": ["image_path"]
            }
        ),
        types.Tool(
            name="get_screen_size",
            description="Get screen dimensions",
            inputSchema={"type": "object", "properties": {}}
        ),
        types.Tool(
            name="get_mouse_position",
            description="Get current mouse coordinates",
            inputSchema={"type": "object", "properties": {}}
        )
    ]
    
    return tools

@app.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Handle tool calls"""
    try:
        safe_automation_check()
        
        if name == "screenshot":
            region = arguments.get("region")
            return_base64 = arguments.get("return_base64", False)
            
            if region:
                screenshot = pyautogui.screenshot(region=(
                    region["x"], region["y"], region["width"], region["height"]
                ))
            else:
                screenshot = pyautogui.screenshot()
            
            if return_base64:
                buffer = BytesIO()
                screenshot.save(buffer, format='PNG')
                img_base64 = base64.b64encode(buffer.getvalue()).decode()
                return [types.TextContent(
                    type="text",
                    text=f"Screenshot captured (base64): data:image/png;base64,{img_base64}"
                )]
            else:
                # Save to file
                screenshot_path = f"/tmp/screenshot_{int(time.time())}.png"
                screenshot.save(screenshot_path)
                return [types.TextContent(
                    type="text",
                    text=f"Screenshot saved to: {screenshot_path}\nSize: {screenshot.size}"
                )]
        
        elif name == "mouse_click":
            x = arguments["x"]
            y = arguments["y"]
            button = arguments.get("button", "left")
            clicks = arguments.get("clicks", 1)
            
            x, y = validate_coordinates(x, y)
            
            if button == "left":
                pyautogui.click(x, y, clicks=clicks)
            elif button == "right":
                pyautogui.rightClick(x, y)
            elif button == "middle":
                pyautogui.middleClick(x, y)
            
            time.sleep(CLICK_DELAY)
            
            return [types.TextContent(
                type="text",
                text=f"Clicked {button} button at ({x}, {y}) {clicks} times"
            )]
        
        elif name == "mouse_move":
            x = arguments["x"]
            y = arguments["y"]
            duration = arguments.get("duration", MOVE_DURATION)
            
            x, y = validate_coordinates(x, y)
            pyautogui.moveTo(x, y, duration=duration)
            
            return [types.TextContent(
                type="text",
                text=f"Moved mouse to ({x}, {y}) in {duration}s"
            )]
        
        elif name == "key_press":
            keys = arguments["keys"]
            interval = arguments.get("interval", 0.1)
            
            # Handle key combinations
            if '+' in keys:
                key_parts = [k.strip() for k in keys.split('+')]
                pyautogui.hotkey(*key_parts, interval=interval)
            else:
                pyautogui.press(keys)
            
            time.sleep(interval)
            
            return [types.TextContent(
                type="text",
                text=f"Pressed key(s): {keys}"
            )]
        
        elif name == "type_text":
            text = arguments["text"]
            interval = arguments.get("interval", 0.01)
            
            pyautogui.typewrite(text, interval=interval)
            
            return [types.TextContent(
                type="text",
                text=f"Typed text: '{text}' ({len(text)} characters)"
            )]
        
        elif name == "find_image":
            image_path = arguments["image_path"]
            confidence = arguments.get("confidence", 0.8)
            region = arguments.get("region")
            
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Image not found: {image_path}")
            
            try:
                if region:
                    location = pyautogui.locateOnScreen(
                        image_path,
                        confidence=confidence,
                        region=(region["x"], region["y"], region["width"], region["height"])
                    )
                else:
                    location = pyautogui.locateOnScreen(image_path, confidence=confidence)
                
                if location:
                    center = pyautogui.center(location)
                    return [types.TextContent(
                        type="text",
                        text=f"Image found at: {location}\nCenter: {center}"
                    )]
                else:
                    return [types.TextContent(
                        type="text",
                        text=f"Image not found with confidence {confidence}"
                    )]
            
            except pyautogui.ImageNotFoundException:
                return [types.TextContent(
                    type="text",
                    text=f"Image not found: {image_path}"
                )]
        
        elif name == "get_screen_size":
            width, height = pyautogui.size()
            return [types.TextContent(
                type="text",
                text=f"Screen size: {width} x {height}"
            )]
        
        elif name == "get_mouse_position":
            x, y = pyautogui.position()
            return [types.TextContent(
                type="text",
                text=f"Mouse position: ({x}, {y})"
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
        "service": "macos-automation-mcp",
        "automation_mode": AUTOMATION_MODE,
        "pyautogui_available": pyautogui is not None
    }

async def main():
    """Run the MCP server"""
    logger.info(f"Starting macOS Automation MCP Server on port {MCP_PORT}")
    logger.info(f"Automation mode: {AUTOMATION_MODE}")
    logger.info(f"PyAutoGUI available: {pyautogui is not None}")
    
    # Start FastAPI server for health checks
    config = uvicorn.Config(fastapi_app, host="0.0.0.0", port=MCP_PORT, log_level="info")
    server = uvicorn.Server(config)
    
    # Run both servers
    await asyncio.gather(
        server.serve(),
        mcp.server.stdio.stdio_server().serve()
    )

if __name__ == "__main__":
    asyncio.run(main())

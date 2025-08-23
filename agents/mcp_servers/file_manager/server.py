#!/usr/bin/env python3
"""
MCP File Manager Server

Provides secure file operations through MCP protocol with configurable access controls.
"""

import os
import asyncio
import logging
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import aiofiles
from pathvalidate import validate_filename, ValidationError

import mcp.types as types
from mcp.server import Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio
from fastapi import FastAPI, HTTPException
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
MCP_PORT = int(os.getenv("MCP_FILE_MANAGER_PORT", 4006))
ALLOWED_PATHS = os.getenv("ALLOWED_PATHS", "/workspace,/tmp").split(",")
MAX_FILE_SIZE = os.getenv("MAX_FILE_SIZE", "10MB")

# Convert size string to bytes
def parse_size(size_str: str) -> int:
    """Parse size string like '10MB' to bytes"""
    units = {'B': 1, 'KB': 1024, 'MB': 1024**2, 'GB': 1024**3}
    size_str = size_str.upper().strip()
    
    # Sort units by length (descending) to check longer units first
    for unit, multiplier in sorted(units.items(), key=lambda x: len(x[0]), reverse=True):
        if size_str.endswith(unit):
            number_part = size_str[:-len(unit)].strip()
            if number_part:  # Make sure we have a number part
                return int(number_part) * multiplier
    
    # If no unit found, assume bytes
    return int(size_str)

MAX_SIZE_BYTES = parse_size(MAX_FILE_SIZE)

# Initialize MCP server
app = Server("file-manager")

def is_path_allowed(file_path: str) -> bool:
    """Check if file path is within allowed directories"""
    abs_path = os.path.abspath(file_path)
    return any(abs_path.startswith(os.path.abspath(allowed)) for allowed in ALLOWED_PATHS)

def validate_file_operation(file_path: str, operation: str = "access") -> None:
    """Validate file operation is allowed"""
    if not is_path_allowed(file_path):
        raise ValueError(f"Access denied: {file_path} is outside allowed paths: {ALLOWED_PATHS}")
    
    if operation in ["write", "create"]:
        try:
            validate_filename(os.path.basename(file_path))
        except ValidationError as e:
            raise ValueError(f"Invalid filename: {e}")

@app.list_tools()
async def handle_list_tools() -> List[types.Tool]:
    """List available file management tools"""
    return [
        types.Tool(
            name="read_file",
            description="Read contents of a file",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to read"
                    },
                    "encoding": {
                        "type": "string",
                        "description": "File encoding (default: utf-8)",
                        "default": "utf-8"
                    }
                },
                "required": ["file_path"]
            }
        ),
        types.Tool(
            name="write_file",
            description="Write content to a file",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to write"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file"
                    },
                    "encoding": {
                        "type": "string",
                        "description": "File encoding (default: utf-8)",
                        "default": "utf-8"
                    },
                    "create_dirs": {
                        "type": "boolean",
                        "description": "Create parent directories if they don't exist",
                        "default": False
                    }
                },
                "required": ["file_path", "content"]
            }
        ),
        types.Tool(
            name="list_directory",
            description="List contents of a directory",
            inputSchema={
                "type": "object",
                "properties": {
                    "directory_path": {
                        "type": "string",
                        "description": "Path to the directory to list"
                    },
                    "show_hidden": {
                        "type": "boolean",
                        "description": "Include hidden files and directories",
                        "default": False
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "List directories recursively",
                        "default": False
                    }
                },
                "required": ["directory_path"]
            }
        ),
        types.Tool(
            name="create_directory",
            description="Create a new directory",
            inputSchema={
                "type": "object",
                "properties": {
                    "directory_path": {
                        "type": "string",
                        "description": "Path to the directory to create"
                    },
                    "parents": {
                        "type": "boolean",
                        "description": "Create parent directories if they don't exist",
                        "default": True
                    }
                },
                "required": ["directory_path"]
            }
        ),
        types.Tool(
            name="delete_file",
            description="Delete a file or directory",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file or directory to delete"
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "Delete directories recursively",
                        "default": False
                    }
                },
                "required": ["file_path"]
            }
        ),
        types.Tool(
            name="file_info",
            description="Get information about a file or directory",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file or directory"
                    }
                },
                "required": ["file_path"]
            }
        )
    ]

@app.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Handle tool calls"""
    try:
        if name == "read_file":
            file_path = arguments["file_path"]
            encoding = arguments.get("encoding", "utf-8")
            
            validate_file_operation(file_path, "read")
            
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            
            if os.path.getsize(file_path) > MAX_SIZE_BYTES:
                raise ValueError(f"File too large: {file_path} exceeds {MAX_FILE_SIZE}")
            
            async with aiofiles.open(file_path, 'r', encoding=encoding) as f:
                content = await f.read()
            
            return [types.TextContent(
                type="text",
                text=f"File: {file_path}\nSize: {os.path.getsize(file_path)} bytes\n\n{content}"
            )]
        
        elif name == "write_file":
            file_path = arguments["file_path"]
            content = arguments["content"]
            encoding = arguments.get("encoding", "utf-8")
            create_dirs = arguments.get("create_dirs", False)
            
            validate_file_operation(file_path, "write")
            
            if len(content.encode(encoding)) > MAX_SIZE_BYTES:
                raise ValueError(f"Content too large: exceeds {MAX_FILE_SIZE}")
            
            if create_dirs:
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            async with aiofiles.open(file_path, 'w', encoding=encoding) as f:
                await f.write(content)
            
            return [types.TextContent(
                type="text",
                text=f"Successfully wrote {len(content)} characters to {file_path}"
            )]
        
        elif name == "list_directory":
            directory_path = arguments["directory_path"]
            show_hidden = arguments.get("show_hidden", False)
            recursive = arguments.get("recursive", False)
            
            validate_file_operation(directory_path, "read")
            
            if not os.path.exists(directory_path):
                raise FileNotFoundError(f"Directory not found: {directory_path}")
            
            if not os.path.isdir(directory_path):
                raise ValueError(f"Not a directory: {directory_path}")
            
            def list_dir(path: str, level: int = 0) -> List[str]:
                items = []
                try:
                    for item in sorted(os.listdir(path)):
                        if not show_hidden and item.startswith('.'):
                            continue
                        
                        item_path = os.path.join(path, item)
                        indent = "  " * level
                        
                        if os.path.isdir(item_path):
                            items.append(f"{indent}{item}/")
                            if recursive and level < 5:  # Limit recursion depth
                                items.extend(list_dir(item_path, level + 1))
                        else:
                            size = os.path.getsize(item_path)
                            items.append(f"{indent}{item} ({size} bytes)")
                except PermissionError:
                    items.append(f"{indent}[Permission Denied]")
                
                return items
            
            items = list_dir(directory_path)
            content = f"Directory: {directory_path}\nTotal items: {len(items)}\n\n" + "\n".join(items)
            
            return [types.TextContent(type="text", text=content)]
        
        elif name == "create_directory":
            directory_path = arguments["directory_path"]
            parents = arguments.get("parents", True)
            
            validate_file_operation(directory_path, "create")
            
            if parents:
                os.makedirs(directory_path, exist_ok=True)
            else:
                os.mkdir(directory_path)
            
            return [types.TextContent(
                type="text",
                text=f"Successfully created directory: {directory_path}"
            )]
        
        elif name == "delete_file":
            file_path = arguments["file_path"]
            recursive = arguments.get("recursive", False)
            
            validate_file_operation(file_path, "delete")
            
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            
            if os.path.isdir(file_path):
                if recursive:
                    import shutil
                    shutil.rmtree(file_path)
                else:
                    os.rmdir(file_path)
            else:
                os.remove(file_path)
            
            return [types.TextContent(
                type="text",
                text=f"Successfully deleted: {file_path}"
            )]
        
        elif name == "file_info":
            file_path = arguments["file_path"]
            
            validate_file_operation(file_path, "read")
            
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            
            stat = os.stat(file_path)
            info = {
                "path": file_path,
                "exists": True,
                "is_file": os.path.isfile(file_path),
                "is_directory": os.path.isdir(file_path),
                "size": stat.st_size,
                "modified": stat.st_mtime,
                "created": stat.st_ctime,
                "permissions": oct(stat.st_mode)[-3:]
            }
            
            content = f"File Information: {file_path}\n"
            for key, value in info.items():
                content += f"{key}: {value}\n"
            
            return [types.TextContent(type="text", text=content)]
        
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
        "service": "file-manager-mcp",
        "allowed_paths": ALLOWED_PATHS,
        "max_file_size": MAX_FILE_SIZE
    }

async def main():
    """Main entry point"""
    logger.info(f"Starting File Manager MCP Server on port {MCP_PORT}")
    
    # Create FastAPI app for health check
    fastapi_app = FastAPI()
    
    @fastapi_app.get("/health")
    async def health():
        return {"status": "healthy", "service": "file-manager-mcp"}
    
    # Start uvicorn server
    import uvicorn
    config = uvicorn.Config(fastapi_app, host="0.0.0.0", port=MCP_PORT, log_level="info")
    server = uvicorn.Server(config)
    
    # For now, just run the FastAPI server (health check endpoint)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
MCP Kubernetes Management Server

Provides Kubernetes cluster management capabilities through kubectl and Python client.
"""

import os
import asyncio
import logging
import yaml
import json
import subprocess
from typing import List, Dict, Any, Optional
from pathlib import Path

import mcp.types as types
from mcp.server import Server
import mcp.server.stdio
from fastapi import FastAPI
import uvicorn

try:
    from kubernetes import client, config
    from kubernetes.client.rest import ApiException
    K8S_CLIENT_AVAILABLE = True
except ImportError:
    logging.warning("Kubernetes client not available")
    K8S_CLIENT_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
MCP_PORT = int(os.getenv("MCP_K8S_PORT", 4009))
KUBECONFIG_PATH = os.getenv("KUBECONFIG", os.path.expanduser("~/.kube/config"))
DEFAULT_NAMESPACE = os.getenv("K8S_NAMESPACE", "default")

# Initialize MCP server
app = Server("kubernetes")

def load_k8s_config():
    """Load Kubernetes configuration"""
    try:
        if K8S_CLIENT_AVAILABLE:
            if os.path.exists(KUBECONFIG_PATH):
                config.load_kube_config(config_file=KUBECONFIG_PATH)
                return True
            else:
                config.load_incluster_config()
                return True
    except Exception as e:
        logger.warning(f"Could not load Kubernetes config: {e}")
    return False

def run_kubectl(args: List[str], namespace: Optional[str] = None) -> str:
    """Run kubectl command and return output"""
    cmd = ["kubectl"]
    
    if namespace:
        cmd.extend(["-n", namespace])
    
    cmd.extend(args)
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"kubectl error: {e.stderr}")

def parse_yaml_resource(yaml_content: str) -> List[Dict[str, Any]]:
    """Parse YAML content into Kubernetes resources"""
    try:
        resources = list(yaml.safe_load_all(yaml_content))
        return [r for r in resources if r is not None]
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML: {e}")

@app.list_tools()
async def handle_list_tools() -> List[types.Tool]:
    """List available Kubernetes tools"""
    tools = [
        types.Tool(
            name="kubectl_apply",
            description="Apply Kubernetes resources from YAML",
            inputSchema={
                "type": "object",
                "properties": {
                    "yaml_content": {
                        "type": "string",
                        "description": "YAML content to apply"
                    },
                    "namespace": {
                        "type": "string",
                        "description": "Target namespace",
                        "default": DEFAULT_NAMESPACE
                    },
                    "dry_run": {
                        "type": "boolean",
                        "description": "Perform dry run",
                        "default": False
                    }
                },
                "required": ["yaml_content"]
            }
        ),
        types.Tool(
            name="kubectl_get",
            description="Get Kubernetes resources",
            inputSchema={
                "type": "object",
                "properties": {
                    "resource_type": {
                        "type": "string",
                        "description": "Resource type (pods, services, deployments, etc.)"
                    },
                    "name": {
                        "type": "string",
                        "description": "Resource name (optional)"
                    },
                    "namespace": {
                        "type": "string",
                        "description": "Namespace to query",
                        "default": DEFAULT_NAMESPACE
                    },
                    "output": {
                        "type": "string",
                        "description": "Output format",
                        "enum": ["yaml", "json", "wide", "name"],
                        "default": "yaml"
                    },
                    "all_namespaces": {
                        "type": "boolean",
                        "description": "Query all namespaces",
                        "default": False
                    }
                },
                "required": ["resource_type"]
            }
        ),
        types.Tool(
            name="kubectl_delete",
            description="Delete Kubernetes resources",
            inputSchema={
                "type": "object",
                "properties": {
                    "resource_type": {
                        "type": "string",
                        "description": "Resource type"
                    },
                    "name": {
                        "type": "string",
                        "description": "Resource name"
                    },
                    "namespace": {
                        "type": "string",
                        "description": "Namespace",
                        "default": DEFAULT_NAMESPACE
                    },
                    "force": {
                        "type": "boolean",
                        "description": "Force deletion",
                        "default": False
                    }
                },
                "required": ["resource_type", "name"]
            }
        ),
        types.Tool(
            name="kubectl_describe",
            description="Describe Kubernetes resources",
            inputSchema={
                "type": "object",
                "properties": {
                    "resource_type": {
                        "type": "string",
                        "description": "Resource type"
                    },
                    "name": {
                        "type": "string",
                        "description": "Resource name"
                    },
                    "namespace": {
                        "type": "string",
                        "description": "Namespace",
                        "default": DEFAULT_NAMESPACE
                    }
                },
                "required": ["resource_type", "name"]
            }
        ),
        types.Tool(
            name="kubectl_logs",
            description="Get pod logs",
            inputSchema={
                "type": "object",
                "properties": {
                    "pod_name": {
                        "type": "string",
                        "description": "Pod name"
                    },
                    "container": {
                        "type": "string",
                        "description": "Container name (for multi-container pods)"
                    },
                    "namespace": {
                        "type": "string",
                        "description": "Namespace",
                        "default": DEFAULT_NAMESPACE
                    },
                    "follow": {
                        "type": "boolean",
                        "description": "Follow logs",
                        "default": False
                    },
                    "tail": {
                        "type": "integer",
                        "description": "Number of lines to tail",
                        "default": 100
                    }
                },
                "required": ["pod_name"]
            }
        ),
        types.Tool(
            name="kubectl_exec",
            description="Execute command in pod",
            inputSchema={
                "type": "object",
                "properties": {
                    "pod_name": {
                        "type": "string",
                        "description": "Pod name"
                    },
                    "command": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Command to execute"
                    },
                    "container": {
                        "type": "string",
                        "description": "Container name (for multi-container pods)"
                    },
                    "namespace": {
                        "type": "string",
                        "description": "Namespace",
                        "default": DEFAULT_NAMESPACE
                    }
                },
                "required": ["pod_name", "command"]
            }
        ),
        types.Tool(
            name="cluster_info",
            description="Get cluster information",
            inputSchema={"type": "object", "properties": {}}
        ),
        types.Tool(
            name="namespaces_list",
            description="List all namespaces",
            inputSchema={"type": "object", "properties": {}}
        ),
        types.Tool(
            name="nodes_list",
            description="List cluster nodes",
            inputSchema={
                "type": "object",
                "properties": {
                    "output": {
                        "type": "string",
                        "description": "Output format",
                        "enum": ["yaml", "json", "wide"],
                        "default": "wide"
                    }
                }
            }
        ),
        types.Tool(
            name="resource_validate",
            description="Validate Kubernetes YAML resources",
            inputSchema={
                "type": "object",
                "properties": {
                    "yaml_content": {
                        "type": "string",
                        "description": "YAML content to validate"
                    }
                },
                "required": ["yaml_content"]
            }
        )
    ]
    
    return tools

@app.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Handle tool calls"""
    try:
        if name == "kubectl_apply":
            yaml_content = arguments["yaml_content"]
            namespace = arguments.get("namespace", DEFAULT_NAMESPACE)
            dry_run = arguments.get("dry_run", False)
            
            # Validate YAML first
            resources = parse_yaml_resource(yaml_content)
            if not resources:
                raise ValueError("No valid resources found in YAML")
            
            # Write to temp file
            temp_file = "/tmp/k8s_resource.yaml"
            with open(temp_file, 'w') as f:
                f.write(yaml_content)
            
            args = ["apply", "-f", temp_file]
            if dry_run:
                args.append("--dry-run=client")
            
            result = run_kubectl(args, namespace)
            
            # Clean up
            os.remove(temp_file)
            
            return [types.TextContent(
                type="text",
                text=f"Applied {len(resources)} resources:\n{result}"
            )]
        
        elif name == "kubectl_get":
            resource_type = arguments["resource_type"]
            name = arguments.get("name")
            namespace = arguments.get("namespace", DEFAULT_NAMESPACE)
            output = arguments.get("output", "yaml")
            all_namespaces = arguments.get("all_namespaces", False)
            
            args = ["get", resource_type]
            if name:
                args.append(name)
            if output != "wide":
                args.extend(["-o", output])
            if all_namespaces:
                args.append("--all-namespaces")
                namespace = None
            
            result = run_kubectl(args, namespace)
            
            return [types.TextContent(
                type="text",
                text=f"Resources ({resource_type}):\n{result}"
            )]
        
        elif name == "kubectl_delete":
            resource_type = arguments["resource_type"]
            name = arguments["name"]
            namespace = arguments.get("namespace", DEFAULT_NAMESPACE)
            force = arguments.get("force", False)
            
            args = ["delete", resource_type, name]
            if force:
                args.extend(["--force", "--grace-period=0"])
            
            result = run_kubectl(args, namespace)
            
            return [types.TextContent(
                type="text",
                text=f"Deleted {resource_type}/{name}:\n{result}"
            )]
        
        elif name == "kubectl_describe":
            resource_type = arguments["resource_type"]
            name = arguments["name"]
            namespace = arguments.get("namespace", DEFAULT_NAMESPACE)
            
            args = ["describe", resource_type, name]
            result = run_kubectl(args, namespace)
            
            return [types.TextContent(
                type="text",
                text=f"Description of {resource_type}/{name}:\n{result}"
            )]
        
        elif name == "kubectl_logs":
            pod_name = arguments["pod_name"]
            container = arguments.get("container")
            namespace = arguments.get("namespace", DEFAULT_NAMESPACE)
            follow = arguments.get("follow", False)
            tail = arguments.get("tail", 100)
            
            args = ["logs", pod_name, f"--tail={tail}"]
            if container:
                args.extend(["-c", container])
            if follow:
                args.append("-f")
            
            result = run_kubectl(args, namespace)
            
            return [types.TextContent(
                type="text",
                text=f"Logs from {pod_name}:\n{result}"
            )]
        
        elif name == "kubectl_exec":
            pod_name = arguments["pod_name"]
            command = arguments["command"]
            container = arguments.get("container")
            namespace = arguments.get("namespace", DEFAULT_NAMESPACE)
            
            args = ["exec", pod_name]
            if container:
                args.extend(["-c", container])
            args.append("--")
            args.extend(command)
            
            result = run_kubectl(args, namespace)
            
            return [types.TextContent(
                type="text",
                text=f"Command output from {pod_name}:\n{result}"
            )]
        
        elif name == "cluster_info":
            result = run_kubectl(["cluster-info"])
            
            return [types.TextContent(
                type="text",
                text=f"Cluster information:\n{result}"
            )]
        
        elif name == "namespaces_list":
            result = run_kubectl(["get", "namespaces"])
            
            return [types.TextContent(
                type="text",
                text=f"Namespaces:\n{result}"
            )]
        
        elif name == "nodes_list":
            output = arguments.get("output", "wide")
            
            args = ["get", "nodes"]
            if output != "wide":
                args.extend(["-o", output])
            
            result = run_kubectl(args)
            
            return [types.TextContent(
                type="text",
                text=f"Cluster nodes:\n{result}"
            )]
        
        elif name == "resource_validate":
            yaml_content = arguments["yaml_content"]
            
            try:
                resources = parse_yaml_resource(yaml_content)
                
                validation_results = []
                for i, resource in enumerate(resources):
                    if not resource:
                        continue
                    
                    # Basic validation
                    if "apiVersion" not in resource:
                        validation_results.append(f"Resource {i+1}: Missing apiVersion")
                    if "kind" not in resource:
                        validation_results.append(f"Resource {i+1}: Missing kind")
                    if "metadata" not in resource:
                        validation_results.append(f"Resource {i+1}: Missing metadata")
                    elif "name" not in resource.get("metadata", {}):
                        validation_results.append(f"Resource {i+1}: Missing metadata.name")
                
                if validation_results:
                    return [types.TextContent(
                        type="text",
                        text=f"Validation errors found:\n" + "\n".join(validation_results)
                    )]
                else:
                    return [types.TextContent(
                        type="text",
                        text=f"YAML validation successful. Found {len(resources)} valid resources."
                    )]
            
            except Exception as e:
                return [types.TextContent(
                    type="text",
                    text=f"Validation failed: {e}"
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
    k8s_configured = load_k8s_config()
    
    return {
        "status": "healthy",
        "service": "kubernetes-mcp",
        "k8s_client_available": K8S_CLIENT_AVAILABLE,
        "k8s_configured": k8s_configured,
        "kubeconfig_path": KUBECONFIG_PATH,
        "default_namespace": DEFAULT_NAMESPACE
    }

async def main():
    """Run the MCP server"""
    logger.info(f"Starting Kubernetes MCP Server on port {MCP_PORT}")
    logger.info(f"Kubeconfig path: {KUBECONFIG_PATH}")
    logger.info(f"Default namespace: {DEFAULT_NAMESPACE}")
    logger.info(f"K8s client available: {K8S_CLIENT_AVAILABLE}")
    
    # Load Kubernetes config
    k8s_configured = load_k8s_config()
    logger.info(f"Kubernetes configured: {k8s_configured}")
    
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

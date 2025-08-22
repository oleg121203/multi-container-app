"""
MCP Hub Registry - Service discovery and management for MCP servers

This module implements the MCP Hub registry that manages containerized tool servers
and provides service discovery for LLM agents.
"""

import os
import asyncio
import aiohttp
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import time
import json

logger = logging.getLogger(__name__)


class MCPServerStatus(Enum):
    """MCP Server status states"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    STARTING = "starting"


@dataclass
class MCPServerInfo:
    """Information about an MCP server"""
    name: str
    url: str
    status: MCPServerStatus
    capabilities: List[str]
    last_health_check: float
    auth_token: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class MCPRegistry:
    """Registry for MCP servers with health monitoring and service discovery"""
    
    def __init__(self):
        self.servers: Dict[str, MCPServerInfo] = {}
        self.health_check_interval = 30  # seconds
        self.health_check_timeout = 5   # seconds
        self._health_check_task = None
        self._session = None
    
    async def start(self):
        """Start the MCP registry and health monitoring"""
        logger.info("Starting MCP Hub Registry")
        
        # Create HTTP session
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.health_check_timeout)
        )
        
        # Discover MCP servers from environment
        await self._discover_servers_from_env()
        
        # Start health monitoring
        self._health_check_task = asyncio.create_task(self._health_monitor())
        
        logger.info(f"MCP Registry started with {len(self.servers)} servers")
    
    async def stop(self):
        """Stop the MCP registry"""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        if self._session:
            await self._session.close()
        
        logger.info("MCP Registry stopped")
    
    async def _discover_servers_from_env(self):
        """Discover MCP servers from environment variables"""
        # Get the list of servers from ATLAS_MCP_SERVERS
        servers_env = os.getenv('ATLAS_MCP_SERVERS', '')
        if not servers_env:
            logger.warning("No MCP servers configured in ATLAS_MCP_SERVERS")
            return
        
        server_names = [name.strip() for name in servers_env.split(',')]
        
        for server_name in server_names:
            if not server_name:
                continue
                
            # Get server URL
            url_env = f'ATLAS_MCP_{server_name.upper()}_URL'
            server_url = os.getenv(url_env)
            
            if not server_url:
                logger.warning(f"No URL configured for MCP server '{server_name}' (missing {url_env})")
                continue
            
            # Get optional auth token
            auth_env = f'ATLAS_MCP_{server_name.upper()}_AUTH_TOKEN'
            auth_token = os.getenv(auth_env)
            
            # Register the server
            server_info = MCPServerInfo(
                name=server_name,
                url=server_url,
                status=MCPServerStatus.UNKNOWN,
                capabilities=[],
                last_health_check=0,
                auth_token=auth_token
            )
            
            self.servers[server_name] = server_info
            logger.info(f"Registered MCP server: {server_name} at {server_url}")
    
    async def _health_monitor(self):
        """Background task for health monitoring"""
        while True:
            try:
                await self._check_all_servers_health()
                await asyncio.sleep(self.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitoring: {e}")
                await asyncio.sleep(5)  # Short delay before retry
    
    async def _check_all_servers_health(self):
        """Check health of all registered servers"""
        tasks = []
        for server_name in self.servers:
            task = asyncio.create_task(self._check_server_health(server_name))
            tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _check_server_health(self, server_name: str):
        """Check health of a specific server"""
        server = self.servers.get(server_name)
        if not server:
            return
        
        try:
            headers = {}
            if server.auth_token:
                headers['Authorization'] = f'Bearer {server.auth_token}'
            
            health_url = f"{server.url.rstrip('/')}/health"
            
            async with self._session.get(health_url, headers=headers) as response:
                if response.status == 200:
                    server.status = MCPServerStatus.HEALTHY
                    server.last_health_check = time.time()
                    
                    # Try to get capabilities
                    await self._update_server_capabilities(server_name)
                else:
                    server.status = MCPServerStatus.UNHEALTHY
                    
        except Exception as e:
            logger.debug(f"Health check failed for {server_name}: {e}")
            server.status = MCPServerStatus.UNHEALTHY
    
    async def _update_server_capabilities(self, server_name: str):
        """Update server capabilities"""
        server = self.servers.get(server_name)
        if not server:
            return
        
        try:
            headers = {}
            if server.auth_token:
                headers['Authorization'] = f'Bearer {server.auth_token}'
            
            capabilities_url = f"{server.url.rstrip('/')}/capabilities"
            
            async with self._session.get(capabilities_url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    server.capabilities = data.get('capabilities', [])
                    
        except Exception as e:
            logger.debug(f"Failed to get capabilities for {server_name}: {e}")
    
    def get_healthy_servers(self) -> List[MCPServerInfo]:
        """Get list of healthy servers"""
        return [
            server for server in self.servers.values()
            if server.status == MCPServerStatus.HEALTHY
        ]
    
    def get_server(self, name: str) -> Optional[MCPServerInfo]:
        """Get server by name"""
        return self.servers.get(name)
    
    def get_servers_by_capability(self, capability: str) -> List[MCPServerInfo]:
        """Get servers that have a specific capability"""
        return [
            server for server in self.get_healthy_servers()
            if capability in server.capabilities
        ]
    
    def get_registry_status(self) -> Dict[str, Any]:
        """Get registry status summary"""
        total_servers = len(self.servers)
        healthy_servers = len(self.get_healthy_servers())
        
        return {
            'total_servers': total_servers,
            'healthy_servers': healthy_servers,
            'servers': {
                name: {
                    'status': server.status.value,
                    'url': server.url,
                    'capabilities': server.capabilities,
                    'last_health_check': server.last_health_check
                }
                for name, server in self.servers.items()
            }
        }


# Global registry instance
mcp_registry = MCPRegistry()
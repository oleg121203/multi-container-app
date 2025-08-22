"""
MCP Client - Interface for LLM agents to interact with MCP servers

Provides a unified client interface for executing actions on MCP servers
with automatic server selection, fallback, and telemetry.
"""

import asyncio
import aiohttp
import logging
import time
import json
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum
import uuid

from .registry import mcp_registry, MCPServerInfo, MCPServerStatus

logger = logging.getLogger(__name__)


class MCPExecutionStatus(Enum):
    """Status of MCP action execution"""
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    NO_SERVER = "no_server"


@dataclass
class MCPExecutionResult:
    """Result of MCP action execution"""
    status: MCPExecutionStatus
    result: Any = None
    error: Optional[str] = None
    server_used: Optional[str] = None
    execution_time_ms: Optional[float] = None
    correlation_id: Optional[str] = None


class MCPClient:
    """Client for executing actions on MCP servers"""
    
    def __init__(self):
        self.session = None
        self.request_timeout = 30  # seconds
        self.retry_attempts = 2
        
    async def start(self):
        """Initialize the MCP client"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.request_timeout)
        )
        logger.info("MCP Client initialized")
    
    async def stop(self):
        """Stop the MCP client"""
        if self.session:
            await self.session.close()
        logger.info("MCP Client stopped")
    
    async def execute_action(
        self,
        action: str,
        args: Dict[str, Any],
        server_preference: Optional[str] = None,
        capability_required: Optional[str] = None
    ) -> MCPExecutionResult:
        """
        Execute an action on an MCP server
        
        Args:
            action: The action to execute
            args: Arguments for the action
            server_preference: Preferred server name (optional)
            capability_required: Required capability (optional)
        
        Returns:
            MCPExecutionResult with execution details
        """
        correlation_id = str(uuid.uuid4())
        start_time = time.time()
        
        logger.info(f"Executing MCP action: {action} [correlation_id: {correlation_id}]")
        
        # Select server
        server = await self._select_server(
            server_preference=server_preference,
            capability_required=capability_required,
            action=action
        )
        
        if not server:
            return MCPExecutionResult(
                status=MCPExecutionStatus.NO_SERVER,
                error="No suitable MCP server available",
                correlation_id=correlation_id
            )
        
        # Execute action with retry
        for attempt in range(self.retry_attempts):
            try:
                result = await self._execute_on_server(
                    server=server,
                    action=action,
                    args=args,
                    correlation_id=correlation_id
                )
                
                execution_time = (time.time() - start_time) * 1000
                
                return MCPExecutionResult(
                    status=MCPExecutionStatus.SUCCESS,
                    result=result,
                    server_used=server.name,
                    execution_time_ms=execution_time,
                    correlation_id=correlation_id
                )
                
            except asyncio.TimeoutError:
                logger.warning(f"Timeout executing {action} on {server.name} (attempt {attempt + 1})")
                if attempt == self.retry_attempts - 1:
                    execution_time = (time.time() - start_time) * 1000
                    return MCPExecutionResult(
                        status=MCPExecutionStatus.TIMEOUT,
                        error="Action execution timed out",
                        server_used=server.name,
                        execution_time_ms=execution_time,
                        correlation_id=correlation_id
                    )
                    
            except Exception as e:
                logger.error(f"Error executing {action} on {server.name}: {e}")
                if attempt == self.retry_attempts - 1:
                    execution_time = (time.time() - start_time) * 1000
                    return MCPExecutionResult(
                        status=MCPExecutionStatus.FAILED,
                        error=str(e),
                        server_used=server.name,
                        execution_time_ms=execution_time,
                        correlation_id=correlation_id
                    )
        
        # Should not reach here
        execution_time = (time.time() - start_time) * 1000
        return MCPExecutionResult(
            status=MCPExecutionStatus.FAILED,
            error="Unknown error",
            execution_time_ms=execution_time,
            correlation_id=correlation_id
        )
    
    async def _select_server(
        self,
        server_preference: Optional[str] = None,
        capability_required: Optional[str] = None,
        action: Optional[str] = None
    ) -> Optional[MCPServerInfo]:
        """Select the best server for the action"""
        
        # If specific server requested, use it if healthy
        if server_preference:
            server = mcp_registry.get_server(server_preference)
            if server and server.status == MCPServerStatus.HEALTHY:
                return server
            logger.warning(f"Preferred server {server_preference} not available")
        
        # If capability required, filter by capability
        if capability_required:
            servers = mcp_registry.get_servers_by_capability(capability_required)
        else:
            servers = mcp_registry.get_healthy_servers()
        
        if not servers:
            logger.warning("No healthy servers available")
            return None
        
        # Simple selection: first healthy server
        # TODO: Implement more sophisticated selection based on metrics
        return servers[0]
    
    async def _execute_on_server(
        self,
        server: MCPServerInfo,
        action: str,
        args: Dict[str, Any],
        correlation_id: str
    ) -> Any:
        """Execute action on a specific server"""
        
        execute_url = f"{server.url.rstrip('/')}/execute"
        
        headers = {
            'Content-Type': 'application/json',
            'X-Correlation-ID': correlation_id
        }
        
        if server.auth_token:
            headers['Authorization'] = f'Bearer {server.auth_token}'
        
        payload = {
            'action': action,
            'args': args,
            'correlation_id': correlation_id
        }
        
        async with self.session.post(execute_url, headers=headers, json=payload) as response:
            if response.status == 200:
                data = await response.json()
                return data.get('result')
            else:
                error_text = await response.text()
                raise Exception(f"Server returned {response.status}: {error_text}")
    
    async def get_available_capabilities(self) -> Dict[str, List[str]]:
        """Get capabilities from all healthy servers"""
        capabilities = {}
        
        for server in mcp_registry.get_healthy_servers():
            capabilities[server.name] = server.capabilities
        
        return capabilities
    
    async def ping_server(self, server_name: str) -> bool:
        """Ping a specific server to check if it's responsive"""
        server = mcp_registry.get_server(server_name)
        if not server:
            return False
        
        try:
            headers = {}
            if server.auth_token:
                headers['Authorization'] = f'Bearer {server.auth_token}'
            
            health_url = f"{server.url.rstrip('/')}/health"
            
            async with self.session.get(health_url, headers=headers) as response:
                return response.status == 200
                
        except Exception:
            return False


# Global client instance
mcp_client = MCPClient()
# ATLAS MCP Servers

This directory contains Model Context Protocol (MCP) servers that extend ATLAS capabilities with specialized tools and integrations.

## Available MCP Servers

### 1. Redis MCP Server (Official)
- **Image**: `ghcr.io/redis/mcp-redis:latest`
- **Port**: 4005
- **Purpose**: Enhanced Redis management and operations
- **Features**: Advanced Redis commands, data analysis, cluster management

### 2. File Manager MCP Server
- **Build**: `./agents/mcp_servers/file_manager`
- **Port**: 4006
- **Purpose**: Secure file operations with access controls
- **Features**:
  - Read/write files with size limits
  - Directory listing and creation
  - File validation and security checks
  - Configurable allowed paths

### 3. macOS Automation MCP Server
- **Build**: `./agents/mcp_servers/macos_automation`
- **Port**: 4007
- **Purpose**: GUI automation using PyAutoGUI
- **Features**:
  - Screenshot capture
  - Mouse click and movement
  - Keyboard input
  - Image recognition
  - Safety controls

### 4. macOS Native MCP Server
- **Build**: `./agents/mcp_servers/macos_native`
- **Port**: 4008
- **Purpose**: Native macOS automation via AppleScript
- **Features**:
  - AppleScript execution
  - Shortcuts integration
  - System notifications
  - Application control
  - Clipboard management
  - Volume control

### 5. Kubernetes MCP Server
- **Build**: `./agents/mcp_servers/kubernetes`
- **Port**: 4009
- **Purpose**: Kubernetes cluster management
- **Features**:
  - Resource CRUD operations
  - Pod logs and execution
  - Cluster information
  - YAML validation
  - Namespace management

## Configuration

### Environment Variables

Each MCP server supports specific environment variables:

#### File Manager
- `MCP_FILE_MANAGER_PORT`: Server port (default: 4006)
- `ALLOWED_PATHS`: Comma-separated allowed paths (default: "/workspace,/tmp")
- `MAX_FILE_SIZE`: Maximum file size (default: "10MB")

#### macOS Automation
- `MCP_MACOS_PORT`: Server port (default: 4007)
- `AUTOMATION_MODE`: Safety mode ("safe" or "full")
- `CLICK_DELAY`: Delay between clicks (default: 0.1)
- `MOVE_DURATION`: Mouse movement duration (default: 0.5)

#### macOS Native
- `MCP_MACOS_NATIVE_PORT`: Server port (default: 4008)
- `NATIVE_AUTOMATION`: Enable native automation (default: "true")

#### Kubernetes
- `MCP_K8S_PORT`: Server port (default: 4009)
- `KUBECONFIG`: Path to kubeconfig file
- `K8S_NAMESPACE`: Default namespace (default: "default")

#### Redis
- `REDIS_URL`: Redis connection URL
- `MCP_REDIS_PORT`: Server port (default: 4005)

## Usage in ATLAS

MCP servers are automatically discovered and integrated into ATLAS through environment variables:

```bash
ATLAS_MCP_REDIS_URL=http://mcp-redis:4005
ATLAS_MCP_FILE_MANAGER_URL=http://mcp-file-manager:4006
ATLAS_MCP_MAC_AUTOMATION_URL=http://mcp-macos-automation:4007
ATLAS_MCP_MAC_NATIVE_URL=http://mcp-macos-native:4008
ATLAS_MCP_KUBERNETES_URL=http://mcp-kubernetes:4009
```

## Health Checks

All MCP servers expose health check endpoints at `/health`:

```bash
curl http://localhost:4006/health  # File Manager
curl http://localhost:4007/health  # macOS Automation
curl http://localhost:4008/health  # macOS Native
curl http://localhost:4009/health  # Kubernetes
```

## Security Considerations

### File Manager
- Restricts access to configured allowed paths
- Validates filenames for security
- Enforces file size limits
- Sanitizes input paths

### macOS Servers
- Safety mode prevents dangerous operations
- Coordinate validation and clamping
- Rate limiting and delays
- Container isolation

### Kubernetes Server
- Respects RBAC permissions
- Validates YAML resources
- Namespace isolation
- Secure kubectl execution

## Development

### Adding New MCP Servers

1. Create directory: `./agents/mcp_servers/new_server/`
2. Add files:
   - `Dockerfile`
   - `requirements.txt`
   - `server.py`
3. Update `compose.yaml` with service definition
4. Add environment variables to ATLAS configuration
5. Update this README

### Local Testing

```bash
# Build and test individual server
cd agents/mcp_servers/file_manager
docker build -t mcp-file-manager .
docker run -p 4006:4006 mcp-file-manager

# Test with full stack
docker-compose up mcp-file-manager
```

## Troubleshooting

### Common Issues

1. **Port conflicts**: Ensure ports 4005-4009 are available
2. **Volume permissions**: Check Docker volume mounts
3. **macOS restrictions**: Enable accessibility permissions for GUI automation
4. **Kubernetes access**: Verify kubeconfig and cluster connectivity

### Logs

```bash
# View MCP server logs
docker-compose logs mcp-file-manager
docker-compose logs mcp-redis
docker-compose logs mcp-kubernetes

# Health check all services
docker-compose ps
```

## Integration Examples

### File Operations
```python
# Via ATLAS agent
file_content = await mcp_client.call_tool("read_file", {
    "file_path": "/workspace/data.txt"
})
```

### macOS Automation
```python
# Take screenshot
screenshot = await mcp_client.call_tool("screenshot", {
    "return_base64": True
})

# Send notification
await mcp_client.call_tool("notification_send", {
    "title": "ATLAS Notification",
    "message": "Task completed successfully"
})
```

### Kubernetes Management
```python
# Get pods
pods = await mcp_client.call_tool("kubectl_get", {
    "resource_type": "pods",
    "namespace": "atlas-system"
})

# Apply configuration
await mcp_client.call_tool("kubectl_apply", {
    "yaml_content": deployment_yaml,
    "namespace": "production"
})
```

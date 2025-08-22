# ATLAS Web Interface - User Guide

## Overview

The ATLAS Web Interface provides a comprehensive management dashboard for the multi-agent orchestration platform. Built with a hacker-themed design, it offers real-time monitoring, agent management, and dynamic team formation capabilities.

## Features

### 🤖 Agent Management
- **Real-time Status**: View live status of all registered agents
- **Capability Browsing**: Explore agent capabilities and specializations
- **Health Monitoring**: Track agent performance and availability

### 🛠 Dynamic Team Formation
- **Task-Based Assembly**: Create teams optimized for specific tasks
- **Human-in-the-Loop**: Approve team compositions before execution
- **Real-time Updates**: Monitor team formation and execution progress

### 📊 System Monitoring
- **Live Logs**: Real-time system logs with filtering capabilities
- **Performance Metrics**: Track active agents, teams formed, and tasks completed
- **Service Status**: Monitor all system components and their health

### 💬 Interactive Chat
- **Command Interface**: Execute system commands through chat
- **ATLAS Communication**: Direct interaction with the ATLAS system
- **Help System**: Built-in help and command reference

## Interface Layout

### Left Panel: SMART_CHAT_SYSTEM
- **Chat History**: Conversation with ATLAS and system messages
- **Agent List**: Overview of all active agents with capabilities
- **Control Buttons**: Send, Mic, TTS, and team formation controls

### Center Panel: ATLAS Avatar
- **3D Avatar**: Animated ATLAS representation (with Three.js fallback)
- **Status Indicator**: Real-time system status display
- **Team Visualization**: Current active team members and roles

### Right Panel: SYSTEM_LOGS
- **Live Logging**: Real-time system logs with level filtering
- **Performance Metrics**: Key system performance indicators
- **Uptime Tracking**: System availability monitoring

### Bottom: Status Bar
- **Service Indicators**: Health status of all system components
- **Connection Status**: WebSocket connection state

## Getting Started

### Prerequisites
- Python 3.11+ with dependencies installed
- Phase 4 ATLAS components (Agent Registry, Team Constructor)
- Web browser with JavaScript enabled

### Installation & Setup

1. **Install Dependencies**
   ```bash
   pip install -r agents/requirements.txt
   ```

2. **Start the Web Interface**
   ```bash
   cd web/api/
   python server.py
   ```

3. **Access the Interface**
   - Open your browser to `http://localhost:8000`
   - The interface will automatically connect to the backend

### Configuration

The web interface uses the existing ATLAS configuration system:

```python
# Agent Registry Path
ATLAS_AGENT_REGISTRY_PATH = "./config/agents.json"

# Team Formation Settings
ATLAS_TEAM_MAX_SIZE = 5
ATLAS_TEAM_FORMATION_TIMEOUT = 30

# Web Server Settings
WEB_INTERFACE_HOST = "0.0.0.0"
WEB_INTERFACE_PORT = 8000
```

## Usage Guide

### Viewing Agents

1. **Agent List**: Automatically loads all registered agents in the left panel
2. **Agent Details**: Click any agent card to view detailed information
3. **Capabilities**: View agent specializations and available tools

### Forming Teams

1. **Click "FORM TEAM"**: Opens the team formation dialog
2. **Describe Task**: Enter a detailed task description
3. **Review Proposal**: System analyzes requirements and suggests team composition
4. **Approve/Modify**: Confirm the team or request changes
5. **Monitor Progress**: Track team execution in real-time

### Using Chat Commands

- `status` - Show complete system status
- `agents` - List all registered agents
- `form team` - Open team formation dialog
- `help` - Display available commands
- `clear` - Clear chat history

### Monitoring System Health

- **Status Indicators**: Green = healthy, Red = issues
- **Log Levels**: Filter by INFO, WARN, ERROR
- **Metrics**: Track performance and usage statistics
- **Connection**: Monitor WebSocket connectivity

## API Reference

### Core Endpoints

- `GET /api/agents` - List all agents
- `POST /api/teams/form` - Create dynamic team
- `GET /api/system/status` - System health status
- `GET /api/metrics` - Performance metrics
- `WebSocket /ws` - Real-time communication

### Example API Usage

```bash
# Get agents
curl http://localhost:8000/api/agents

# Form team
curl -X POST http://localhost:8000/api/teams/form \
  -H "Content-Type: application/json" \
  -d '{"description": "Create a monitoring dashboard"}'

# Check system status  
curl http://localhost:8000/api/system/status
```

## Troubleshooting

### Common Issues

**WebSocket Connection Failed**
- Ensure the server is running on port 8000
- Check firewall settings
- Verify WebSocket support in your browser

**Agents Not Loading**
- Verify `config/agents.json` exists and is valid
- Check Agent Registry is initialized
- Review server logs for errors

**Team Formation Fails**
- Ensure agents are available (not busy)
- Check agent capabilities match task requirements
- Verify team constructor is properly configured

**3D Avatar Not Displaying**
- Three.js may be blocked by ad blockers
- Fallback ATLAS logo will display automatically
- No functionality is lost

### Log Analysis

Monitor the system logs panel for:
- **INFO**: Normal operations and status updates
- **WARN**: Non-critical issues and fallback activations
- **ERROR**: Critical issues requiring attention

### Performance Optimization

- **Browser**: Use Chrome/Firefox for best performance
- **Network**: Ensure stable connection for WebSocket
- **Resources**: Monitor memory usage during long sessions

## Security Considerations

### Development vs Production

**Development Mode** (current):
- CORS allows all origins
- WebSocket accepts all connections
- No authentication required

**Production Deployment** (recommended):
- Implement JWT/OAuth authentication
- Restrict CORS to specific domains
- Use HTTPS/WSS for encrypted communication
- Add rate limiting and request validation

### Best Practices

- Never expose API keys in the frontend
- Use environment variables for configuration
- Implement proper session management
- Regular security audits and updates

## Integration with ATLAS

The web interface seamlessly integrates with:

### Phase 4 Components
- **Agent Registry**: Real-time agent discovery and status
- **Team Constructor**: Dynamic team formation and management
- **Health Monitor**: Continuous system health tracking
- **Load Balancer**: Optimal agent workload distribution

### Backend APIs
- **FastAPI Server**: RESTful API for all operations
- **WebSocket**: Real-time bidirectional communication
- **Agent Communication**: Direct integration with agent endpoints

### Data Flow
```
User Interface → Web API → Agent Registry → Individual Agents
             ↑                        ↓
      WebSocket ←  Real-time Updates  ← Team Constructor
```

## Support & Development

### Getting Help
- Check the built-in help system (type `help` in chat)
- Review system logs for error details
- Consult the Phase 4 implementation documentation

### Contributing
- Follow the existing code style and patterns
- Add tests for new functionality
- Update documentation for interface changes
- Test across different browsers and screen sizes

### Future Enhancements
- Voice interface integration (TTS/STT)
- Advanced team management features
- Performance analytics and reporting
- Mobile-responsive design
- Multi-language support

---

**ATLAS Web Interface v1.0** - Multi-Agent Orchestration Platform
Built on Phase 4 Implementation - Agent Registry & Dynamic Teams
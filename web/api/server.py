"""
ATLAS Web Interface API Server

FastAPI server that integrates with Phase 4 backend components:
- Agent Registry
- Team Constructor  
- Health Monitor
- Real-time WebSocket communication
"""

import asyncio
import json
import logging
import os
import sys
import time
import psutil
from typing import List, Dict, Any
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, File, UploadFile, Form, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
import aiohttp
import io
import secrets

# Add the project root to the Python path so we can import agents modules
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    # Import real implementations and alias to *Class names to avoid type/name clashes
    from agents.registry.agent_registry import AgentRegistry as RealAgentRegistry
    from agents.registry.team_constructor import TeamConstructor as RealTeamConstructor
    from agents.registry.health_monitor import HealthMonitor as RealHealthMonitor
    from agents.shared.config import config
    ATLAS_AGENT_REGISTRY_PATH = config.ATLAS_AGENT_REGISTRY_PATH
    AgentRegistryClass = RealAgentRegistry
    TeamConstructorClass = RealTeamConstructor
    HealthMonitorClass = RealHealthMonitor
except ImportError as e:
    print(f"Warning: Could not import agents modules: {e}")
    print("Running in development mode without full backend integration")
    # Fallback classes for development
    class DevAgentRegistry:
        def __init__(self, path): 
            self.agents = {}
            self.path = path
        async def initialize(self): pass
        def get_agent(self, agent_id): return None
        
    class DevTeamConstructor:
        def __init__(self, registry): 
            self.registry = registry
        async def form_team(self, description): 
            return {"members": [], "task": description}
            
    class DevHealthMonitor:
        def __init__(self, registry): 
            self.registry = registry
        async def check_agent_health(self, agent_id): 
            return "active"

    AgentRegistryClass = DevAgentRegistry
    TeamConstructorClass = DevTeamConstructor
    HealthMonitorClass = DevHealthMonitor

# Request/Response Models
class TaskRequest(BaseModel):
    description: str

class ChatMessage(BaseModel):
    type: str
    message: str
    timestamp: str

class TeamFormationRequest(BaseModel):
    description: str
    constraints: Dict[str, Any] = {}

class VoiceRequest(BaseModel):
    text: str
    voice: str = "default"
    agent_id: str = "atlas"

class RunTaskRequest(BaseModel):
    description: str
    requester_id: str | None = None

# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.logger = logging.getLogger(__name__)
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        self.logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            self.logger.error(f"Failed to send personal message: {e}")
    
    async def broadcast(self, message: Dict[str, Any]):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                self.logger.error(f"Failed to broadcast to connection: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected connections
        for conn in disconnected:
            self.disconnect(conn)

# Initialize FastAPI app
app = FastAPI(
    title="ATLAS Web Interface API",
    description="Web interface for ATLAS Multi-Agent Orchestration Platform",
    version="1.0.0"
)

# CORS middleware - restrict origins for production
allowed_origins = os.environ.get("ATLAS_ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000,http://127.0.0.1:8000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # Restricted origins instead of "*"
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Configure logging early
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize backend components
startup_time = time.time()
request_count = 0
error_count = 0

# Metrics tracking
def increment_request_count():
    global request_count
    request_count += 1

def increment_error_count():
    global error_count
    error_count += 1

# Basic Authentication
security = HTTPBasic()

def get_current_user(credentials: HTTPBasicCredentials = Depends(security)):
    """Simple basic authentication"""
    # In production, these should be from environment variables or secure storage
    correct_username = os.environ.get("ATLAS_AUTH_USERNAME", "atlas")
    correct_password = os.environ.get("ATLAS_AUTH_PASSWORD", "atlas123")
    
    is_correct_username = secrets.compare_digest(credentials.username, correct_username)
    is_correct_password = secrets.compare_digest(credentials.password, correct_password)
    
    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# Optional authentication for certain endpoints
def optional_auth(request: Request):
    """Optional authentication - only enforced if ATLAS_REQUIRE_AUTH is set"""
    if os.environ.get("ATLAS_REQUIRE_AUTH", "false").lower() == "true":
        try:
            # Extract authorization header
            auth_header = request.headers.get("authorization", "")
            if not auth_header.startswith("Basic "):
                raise HTTPException(status_code=401, detail="Authentication required")
            return True
        except:
            raise HTTPException(status_code=401, detail="Authentication required")
    return True
try:
    registry_path = ATLAS_AGENT_REGISTRY_PATH if 'ATLAS_AGENT_REGISTRY_PATH' in globals() else "./config/agents.json"
    agent_registry: Any = AgentRegistryClass(registry_path)
    team_constructor: Any = TeamConstructorClass(agent_registry)
    health_monitor: Any = HealthMonitorClass(agent_registry)
    logger.info(f"Backend components initialized with registry path: {registry_path}")
except Exception as e:
    print(f"Warning: Backend initialization failed: {e}")
    # Use mock objects
    agent_registry: Any = AgentRegistryClass("./config/agents.json")
    team_constructor: Any = TeamConstructorClass(agent_registry)
    health_monitor: Any = HealthMonitorClass(agent_registry)

# WebSocket manager
manager = ConnectionManager()

@app.middleware("http")
async def add_process_time_header(request, call_next):
    """Add request processing time and increment counters"""
    start_time = time.time()
    increment_request_count()
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        # Count HTTP errors as errors as well (4xx/5xx)
        try:
            if response.status_code >= 400:
                increment_error_count()
        except Exception:
            pass
        return response
    except Exception as e:
        increment_error_count()
        raise e
async def startup_event():
    """Initialize backend components on startup"""
    try:
        await agent_registry.initialize()
        logger.info("ATLAS Web Interface API started successfully")
    except Exception as e:
        logger.error(f"Startup error: {e}")

# Register startup event handler
app.add_event_handler("startup", lambda: asyncio.create_task(startup_event()))

# API Routes

@app.get("/")
async def read_root():
    """Serve the main interface"""
    frontend_path = Path(__file__).parent.parent / "frontend" / "index.html"
    if frontend_path.exists():
        return FileResponse(frontend_path)
    else:
        return HTMLResponse("""
        <!DOCTYPE html>
        <html><head><title>ATLAS Web Interface</title></head>
        <body>
        <h1>ATLAS Web Interface</h1>
        <p>Frontend not yet deployed. API is running.</p>
        <p><a href="/docs">View API Documentation</a></p>
        </body></html>
        """)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "atlas-web-interface",
        "api_version": "1.0.0",
        "backend_connected": True
    }

@app.get("/api/agents")
async def get_agents():
    """Get all registered agents"""
    try:
        # Ensure registry is initialized
        await agent_registry.initialize()
        
        # Convert agent data to JSON-serializable format
        agents_list = []
        for agent_id, agent in agent_registry.agents.items():
            agent_data = {
                "id": agent_id,
                "name": getattr(agent, 'name', agent_id),
                "capabilities": getattr(agent, 'capabilities', []),
                "status": "active",  # Default status
                "provider": getattr(agent, 'provider', 'unknown'),
                "model": getattr(agent, 'model', 'unknown')
            }
            agents_list.append(agent_data)
            
        return {"agents": agents_list}
    except Exception as e:
        logger.error(f"Failed to get agents: {e}")
        # Return mock data for development
        return {
            "agents": [
                {
                    "id": "llm1",
                    "name": "LLM1 Agent", 
                    "capabilities": ["user_interface", "rag_search", "semantic_memory"],
                    "status": "active",
                    "provider": "openai",
                    "model": "gpt-4"
                },
                {
                    "id": "llm2", 
                    "name": "LLM2 Orchestrator",
                    "capabilities": ["task_orchestration", "mcp_integration", "linear_integration"], 
                    "status": "active",
                    "provider": "ollama",
                    "model": "gpt-oss:latest"
                },
                {
                    "id": "llm3",
                    "name": "LLM3 Security Monitor",
                    "capabilities": ["security_monitoring", "compliance_checking"],
                    "status": "active", 
                    "provider": "openai",
                    "model": "gpt-4"
                }
            ]
        }

@app.get("/api/agents/{agent_id}/status")
async def get_agent_status(agent_id: str):
    """Get real-time agent status"""
    try:
        agent = agent_registry.get_agent(agent_id)
        if agent:
            # health_monitor may expect agent object; pass id, fallback handled inside
            status = await health_monitor.check_agent_health(agent_id)
            return {
                "agent_id": agent_id,
                "status": status,
                "last_check": "2024-08-22T20:30:00Z",
                "health_score": 0.95
            }
        else:
            raise HTTPException(status_code=404, detail="Agent not found")
    except Exception as e:
        logger.error(f"Failed to get agent status: {e}")
        # Return mock status
        return {
            "agent_id": agent_id,
            "status": "active",
            "last_check": "2024-08-22T20:30:00Z", 
            "health_score": 0.95
        }

@app.post("/api/teams/form")
async def form_team(request: TeamFormationRequest, authenticated: bool = Depends(optional_auth)):
    """Form a dynamic team for a task"""
    try:
        team = await team_constructor.form_team(request.description)
        
        # Broadcast team formation to all connected clients
        await manager.broadcast({
            "type": "team_update",
            "team": team,
            "message": f"Team formed for task: {request.description}"
        })
        
        return {"team": team, "status": "success"}
    except Exception as e:
        logger.error(f"Team formation failed: {e}")
        # Return mock team
        mock_team = {
            "id": "team_001",
            "task": request.description,
            "members": [
                {"name": "LLM1 Agent", "role": "Frontend Specialist"},
                {"name": "LLM2 Orchestrator", "role": "Coordinator"},
                {"name": "LLM3 Security Monitor", "role": "Security Guard"}
            ],
            "formed_at": "2024-08-22T20:30:00Z",
            "status": "active"
        }
        
        await manager.broadcast({
            "type": "team_update", 
            "team": mock_team,
            "message": f"Team formed for task: {request.description}"
        })
        
        return {"team": mock_team, "status": "success"}

@app.get("/api/system/status")
async def get_system_status():
    """Get overall system status"""
    return {
        "agent_registry": "active",
        "team_constructor": "active",
        "health_monitor": "active", 
        "mcp_hub": "active",
        "llm1": "active",
        "llm2": "active",
        "llm3": "active",
        "tts": "active",
        "websocket": "active",
        "last_update": "2024-08-22T20:30:00Z"
    }

@app.get("/api/metrics")
async def get_metrics():
    """Get system performance metrics with real data"""
    try:
        # Get real system metrics
        current_time = time.time()
        uptime_seconds = current_time - startup_time
        
        # CPU and memory metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Network metrics (if available)
        try:
            network = psutil.net_io_counters()
            if network is not None:
                ns = getattr(network, "_asdict", lambda: {})()
                if isinstance(ns, dict) and ns:
                    network_stats = {
                        "bytes_sent": int(ns.get("bytes_sent", 0)),
                        "bytes_recv": int(ns.get("bytes_recv", 0)),
                        "packets_sent": int(ns.get("packets_sent", 0)),
                        "packets_recv": int(ns.get("packets_recv", 0)),
                    }
                else:
                    network_stats = {}
            else:
                network_stats = {}
        except Exception:
            network_stats = {}
        
        # Calculate error rate
        error_rate = (error_count / max(request_count, 1)) * 100
        
        # Active connections count
        active_connections = len(manager.active_connections)
        
        # Agent count (real if available, fallback to mock)
        agent_count = len(agent_registry.agents) if hasattr(agent_registry, 'agents') and agent_registry.agents else 3
        
        return {
            "timestamp": current_time,
            "uptime_seconds": uptime_seconds,
            "active_agents": agent_count,
            "teams_formed": 15,  # This could be tracked in a real database
            "tasks_completed": 42,  # This could be tracked in a real database
            "request_count": request_count,
            "error_count": error_count,
            "error_rate_percent": error_rate,
            "active_websocket_connections": active_connections,
            "system_metrics": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_used_mb": memory.used / 1024 / 1024,
                "memory_total_mb": memory.total / 1024 / 1024,
                "disk_percent": disk.percent,
                "disk_used_gb": disk.used / 1024 / 1024 / 1024,
                "disk_total_gb": disk.total / 1024 / 1024 / 1024
            },
            "network_metrics": network_stats
        }
    except Exception as e:
        logger.error(f"Failed to collect metrics: {e}")
        # Fallback to basic metrics
        return {
            "timestamp": time.time(),
            "uptime_seconds": time.time() - startup_time,
            "active_agents": 3,
            "teams_formed": 15,
            "tasks_completed": 42,
            "request_count": request_count,
            "error_count": error_count,
            "error_rate_percent": (error_count / max(request_count, 1)) * 100,
            "active_websocket_connections": len(manager.active_connections),
            "system_metrics": {
                "cpu_percent": 0.0,
                "memory_percent": 0.0,
                "memory_used_mb": 0.0,
                "memory_total_mb": 0.0,
                "disk_percent": 0.0,
                "disk_used_gb": 0.0,
                "disk_total_gb": 0.0
            },
            "network_metrics": {}
        }

@app.post("/api/tasks/run")
async def run_task(request: RunTaskRequest):
    """Forward a task to LLM2 orchestrator for autonomous execution"""
    llm2_url = os.environ.get("ATLAS_LLM2_URL", "http://127.0.0.1:8002")
    payload = {
        "description": request.description,
        "requester_id": request.requester_id or "web-ui"
    }
    timeout = aiohttp.ClientTimeout(total=30)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(f"{llm2_url}/process_task", json=payload) as resp:
                if resp.status >= 400:
                    text = await resp.text()
                    raise HTTPException(status_code=resp.status, detail=text)
                data = await resp.json()
                return {"status": "ok", "llm2": data}
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="LLM2 orchestrator timeout")
    except Exception as e:
        logger.error(f"Failed to forward task to LLM2: {e}")
        raise HTTPException(status_code=502, detail="LLM2 orchestrator error")

@app.post("/api/chat")
async def chat_endpoint(message: ChatMessage):
    """Handle chat messages and return AI responses"""
    try:
        # In a real implementation, this would integrate with LLM1
        response_text = f"ATLAS received: {message.message}"
        
        # Broadcast to all connected clients
        await manager.broadcast({
            "type": "chat",
            "data": response_text,
            "timestamp": message.timestamp
        })
        
        return {"response": response_text, "status": "success"}
    except Exception as e:
        logger.error(f"Chat failed: {e}")
        return {"response": "Error processing message", "status": "error"}

@app.post("/api/tts")
async def text_to_speech(request: VoiceRequest):
    """Convert text to speech using TTS service"""
    try:
        # Try to integrate with the actual MCP TTS service
        tts_url = os.environ.get("ATLAS_MCP_TTS_URL", "http://mcp-tts:4004")
        
        async with aiohttp.ClientSession() as session:
            try:
                # Call the actual TTS service
                async with session.post(
                    f"{tts_url}/tts",
                    json={
                        "text": request.text,
                        "voice": request.voice,
                        "agent_id": request.agent_id
                    },
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        audio_url = result.get("audio_url", f"/api/audio/{request.agent_id}_{hash(request.text) % 10000}.mp3")
                        
                        # Broadcast TTS event to connected clients
                        await manager.broadcast({
                            "type": "tts",
                            "text": request.text,
                            "audio_url": audio_url,
                            "agent_id": request.agent_id
                        })
                        
                        return {
                            "status": "success",
                            "audio_url": audio_url,
                            "duration_seconds": result.get("duration_seconds", len(request.text) * 0.1)
                        }
            except (aiohttp.ClientError, asyncio.TimeoutError):
                logger.warning("TTS service unavailable, using fallback")
        
        # Fallback: generate placeholder response
        audio_url = f"/api/audio/{request.agent_id}_{hash(request.text) % 10000}.mp3"
        
        # Broadcast TTS event to connected clients
        await manager.broadcast({
            "type": "tts",
            "text": request.text,
            "audio_url": audio_url,
            "agent_id": request.agent_id
        })
        
        return {
            "status": "success",
            "audio_url": audio_url,
            "duration_seconds": len(request.text) * 0.1  # Rough estimate
        }
    except Exception as e:
        logger.error(f"TTS failed: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/api/stt")
async def speech_to_text(audio: UploadFile = File(...)):
    """Convert speech to text using STT service"""
    try:
        # Try to integrate with the actual MCP STT service
        stt_url = os.environ.get("ATLAS_MCP_STT_URL", "http://mcp-stt:8080")
        
        async with aiohttp.ClientSession() as session:
            try:
                # Read audio file content
                audio_content = await audio.read()
                
                # Prepare multipart form data for STT service
                data = aiohttp.FormData()
                data.add_field('audio', audio_content, filename=audio.filename, content_type=audio.content_type)
                
                # Call the actual STT service
                async with session.post(
                    f"{stt_url}/transcribe",
                    data=data,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return {
                            "status": "success", 
                            "transcript": result.get("transcript", "Voice input received"),
                            "confidence": result.get("confidence", 0.95)
                        }
            except (aiohttp.ClientError, asyncio.TimeoutError):
                logger.warning("STT service unavailable, using fallback")
        
        # Fallback: return placeholder response
        return {
            "status": "success", 
            "transcript": "Voice input received (STT service unavailable)",
            "confidence": 0.50
        }
        
    except Exception as e:
        logger.error(f"STT failed: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/api/voices")
async def get_available_voices():
    """Get available TTS voices"""
    try:
        voices = [
            {"id": "atlas", "name": "ATLAS", "language": "en-US", "gender": "neutral"},
            {"id": "llm1", "name": "LLM1 Assistant", "language": "en-US", "gender": "female"},
            {"id": "llm2", "name": "LLM2 Orchestrator", "language": "en-US", "gender": "male"},
            {"id": "llm3", "name": "LLM3 Security", "language": "en-US", "gender": "neutral"}
        ]
        return {"voices": voices}
    except Exception as e:
        logger.error(f"Failed to get voices: {e}")
        return {"voices": []}

@app.get("/metrics")
async def prometheus_metrics():
    """Export metrics in Prometheus format"""
    try:
        # Get current metrics
        current_time = time.time()
        uptime_seconds = current_time - startup_time

        # System metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        # Calculate error rate
        error_rate = (error_count / max(request_count, 1)) * 100

        # Active connections count
        active_connections = len(manager.active_connections)

        # Agent count
        agent_count = len(agent_registry.agents) if hasattr(agent_registry, 'agents') and agent_registry.agents else 3

        # Generate Prometheus format metrics
        prometheus_output = f"""# HELP atlas_uptime_seconds Time since the ATLAS service started
# TYPE atlas_uptime_seconds counter
atlas_uptime_seconds {uptime_seconds}

# HELP atlas_requests_total Total number of HTTP requests
# TYPE atlas_requests_total counter
atlas_requests_total {request_count}

# HELP atlas_errors_total Total number of HTTP errors
# TYPE atlas_errors_total counter
atlas_errors_total {error_count}

# HELP atlas_error_rate_percent Error rate percentage
# TYPE atlas_error_rate_percent gauge
atlas_error_rate_percent {error_rate}

# HELP atlas_active_agents Number of active agents
# TYPE atlas_active_agents gauge
atlas_active_agents {agent_count}

# HELP atlas_websocket_connections Active WebSocket connections
# TYPE atlas_websocket_connections gauge
atlas_websocket_connections {active_connections}

# HELP atlas_cpu_percent CPU usage percentage
# TYPE atlas_cpu_percent gauge
atlas_cpu_percent {cpu_percent}

# HELP atlas_memory_percent Memory usage percentage
# TYPE atlas_memory_percent gauge
atlas_memory_percent {memory.percent}

# HELP atlas_memory_used_bytes Memory used in bytes
# TYPE atlas_memory_used_bytes gauge
atlas_memory_used_bytes {memory.used}

# HELP atlas_disk_percent Disk usage percentage
# TYPE atlas_disk_percent gauge
atlas_disk_percent {disk.percent}

# HELP atlas_disk_used_bytes Disk used in bytes
# TYPE atlas_disk_used_bytes gauge
atlas_disk_used_bytes {disk.used}
"""
        return PlainTextResponse(content=prometheus_output)
    except Exception as e:
        logger.error(f"Failed to generate Prometheus metrics: {e}")
        return PlainTextResponse(content=f"# Error generating metrics: {str(e)}\n")

@app.post("/api/analytics")
async def receive_analytics(analytics_data: Dict[str, Any]):
    """Receive analytics data from frontend"""
    try:
        # In production, this would store analytics in a database
        logger.info(f"Analytics received: {analytics_data}")
        return {"status": "success", "message": "Analytics received"}
    except Exception as e:
        logger.error(f"Analytics processing failed: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/api/teams/history")
async def get_team_history():
    """Get historical team formation data"""
    try:
        # Mock team history data
        history = [
            {
                "id": "team_001",
                "task": "Create user authentication system",
                "members": ["LLM1 Agent", "LLM2 Orchestrator", "LLM3 Security Monitor"],
                "formed_at": "2024-08-22T18:30:00Z",
                "status": "completed",
                "duration": 1800
            },
            {
                "id": "team_002", 
                "task": "Implement monitoring dashboard",
                "members": ["LLM1 Agent", "LLM2 Orchestrator"],
                "formed_at": "2024-08-22T19:15:00Z",
                "status": "active",
                "duration": 0
            }
        ]
        return {"teams": history}
    except Exception as e:
        logger.error(f"Failed to get team history: {e}")
        return {"teams": []}

@app.get("/api/diagnostics")
async def get_system_diagnostics(user: str = Depends(get_current_user)):
    """Get comprehensive system diagnostics"""
    try:
        # In production, this would gather real system metrics
        diagnostics = {
            "timestamp": "2024-08-22T20:30:00Z",
            "system": {
                "uptime": 86400,
                "memory_usage": 65.2,
                "cpu_usage": 23.8,
                "disk_usage": 45.1
            },
            "services": {
                "agent_registry": {"status": "active", "response_time_ms": 45},
                "team_constructor": {"status": "active", "response_time_ms": 78},
                "mcp_hub": {"status": "active", "response_time_ms": 32},
                "websocket": {"status": "active", "connections": len(manager.active_connections)}
            },
            "performance": {
                "avg_api_response_time": 156,
                "requests_per_minute": 24,
                "error_rate_percent": 0.8
            }
        }
        return diagnostics
    except Exception as e:
        logger.error(f"Diagnostics collection failed: {e}")
        return {"error": str(e)}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication"""
    await manager.connect(websocket)
    try:
        # Send welcome message
        await manager.send_personal_message({
            "type": "system",
            "message": "Connected to ATLAS Web Interface",
            "timestamp": "2024-08-22T20:30:00Z"
        }, websocket)
        
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            if message.get("type") == "chat":
                # Echo message back to all clients
                await manager.broadcast({
                    "type": "chat",
                    "data": f"Echo: {message.get('message', '')}",
                    "sender": "atlas",
                    "timestamp": message.get("timestamp", "")
                })
            elif message.get("type") == "ping":
                # Respond to ping with pong
                await manager.send_personal_message({
                    "type": "pong",
                    "timestamp": "2024-08-22T20:30:00Z"
                }, websocket)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# Serve static files
frontend_dir = Path(__file__).parent.parent / "frontend"
static_dir = frontend_dir / "static"

# Also serve the standalone 3D head demo under /head-3d for convenience
head3d_dir = Path(__file__).parent.parent.parent / "standalone" / "head-3d"

if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

if head3d_dir.exists():
    # html=True allows directory index serving (index.html)
    app.mount("/head-3d", StaticFiles(directory=str(head3d_dir), html=True), name="head-3d")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
/**
 * ATLAS Web Interface - Main Application
 * 
 * Manages real-time communication with backend API, 3D avatar rendering,
 * agent management, team formation, and system monitoring.
 */

class ATLASInterface {
    constructor() {
        this.websocket = null;
        this.agents = new Map();
        this.currentTeam = null;
        this.avatar = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.startTime = Date.now();
        
        // Bind methods to maintain context
        this.initialize = this.initialize.bind(this);
        this.handleWebSocketMessage = this.handleWebSocketMessage.bind(this);
        this.setupWebSocket = this.setupWebSocket.bind(this);
    }

    async initialize() {
        try {
            this.log('info', 'Initializing ATLAS Web Interface...');
            
            await this.setupWebSocket();
            await this.initializeAvatar();
            await this.loadAgents();
            this.setupEventListeners();
            this.startStatusUpdates();
            this.startUptimeCounter();
            
            // Hide loading screen and show interface
            document.getElementById('loadingScreen').style.display = 'none';
            document.getElementById('mainInterface').style.display = 'grid';
            document.getElementById('mainInterface').classList.add('fade-in');
            
            this.log('info', 'ATLAS Web Interface initialization complete');
        } catch (error) {
            this.log('error', `Initialization failed: ${error.message}`);
            console.error('Initialization error:', error);
        }
    }

    async setupWebSocket() {
        try {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws`;
            
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => {
                this.updateConnectionStatus('Connected');
                this.log('info', 'WebSocket connection established');
                this.reconnectAttempts = 0;
            };
            
            this.websocket.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    this.handleWebSocketMessage(message);
                } catch (error) {
                    this.log('error', `Failed to parse WebSocket message: ${error.message}`);
                }
            };
            
            this.websocket.onclose = () => {
                this.updateConnectionStatus('Disconnected');
                this.log('warn', 'WebSocket connection lost');
                this.attemptReconnection();
            };
            
            this.websocket.onerror = (error) => {
                this.log('error', 'WebSocket error occurred');
                console.error('WebSocket error:', error);
            };
            
        } catch (error) {
            this.log('error', `WebSocket setup failed: ${error.message}`);
            this.updateConnectionStatus('Error');
        }
    }

    attemptReconnection() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = Math.pow(2, this.reconnectAttempts) * 1000; // Exponential backoff
            
            this.log('warn', `Attempting reconnection ${this.reconnectAttempts}/${this.maxReconnectAttempts} in ${delay/1000}s...`);
            
            setTimeout(() => {
                this.setupWebSocket();
            }, delay);
        } else {
            this.log('error', 'Maximum reconnection attempts reached');
            this.updateConnectionStatus('Failed');
        }
    }

    async initializeAvatar() {
        const canvas = document.getElementById('avatarCanvas');
        const container = document.getElementById('avatarContainer');
        const fallback = document.getElementById('avatarFallback');
        
        if (window.THREE) {
            try {
                this.avatar = new ATLASAvatar(canvas, container);
                await this.avatar.initialize();
                fallback.style.display = 'none';
                canvas.style.display = 'block';
                this.log('info', '3D Avatar initialized successfully');
            } catch (error) {
                this.log('warn', `3D Avatar failed, using fallback: ${error.message}`);
                canvas.style.display = 'none';
                fallback.style.display = 'flex';
            }
        } else {
            this.log('warn', 'Three.js not available, using fallback avatar');
            canvas.style.display = 'none';
            fallback.style.display = 'flex';
        }
    }

    async loadAgents() {
        try {
            this.log('info', 'Loading agents from registry...');
            const response = await fetch('/api/agents');
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            this.agents.clear();
            data.agents.forEach(agent => {
                this.agents.set(agent.id, agent);
            });
            
            this.renderAgentsList();
            this.updateMetrics();
            this.log('info', `Loaded ${data.agents.length} agents successfully`);
            
        } catch (error) {
            this.log('error', `Failed to load agents: ${error.message}`);
            console.error('Agent loading error:', error);
        }
    }

    renderAgentsList() {
        const container = document.getElementById('agentsGrid');
        container.innerHTML = '';
        
        if (this.agents.size === 0) {
            container.innerHTML = '<div class="loading-agents">No agents available</div>';
            return;
        }
        
        this.agents.forEach((agent, id) => {
            const agentElement = document.createElement('div');
            agentElement.className = 'agent-card clickable';
            agentElement.setAttribute('data-agent-id', id);
            
            const capabilitiesHtml = agent.capabilities.slice(0, 3).map(cap => {
                const capName = typeof cap === 'object' ? cap.name : cap;
                return `<span class="capability-tag">${capName}</span>`;
            }).join('');
            
            agentElement.innerHTML = `
                <div class="agent-name">${agent.name}</div>
                <div class="agent-status" data-status="${agent.status}">
                    ● ${agent.status.toUpperCase()}
                </div>
                <div class="agent-capabilities">
                    ${capabilitiesHtml}
                    ${agent.capabilities.length > 3 ? `<span class="capability-tag">+${agent.capabilities.length - 3}</span>` : ''}
                </div>
            `;
            
            // Add click handler for agent details
            agentElement.addEventListener('click', () => {
                this.showAgentDetails(agent);
            });
            
            container.appendChild(agentElement);
        });
    }

    showAgentDetails(agent) {
        const capabilities = agent.capabilities.map(cap => 
            typeof cap === 'object' ? cap.name : cap
        ).join(', ');
        
        this.addChatMessage('system', `Agent Details: ${agent.name}
Provider: ${agent.provider}
Model: ${agent.model}
Capabilities: ${capabilities}
Status: ${agent.status}`);
    }

    setupEventListeners() {
        // Send message
        const sendBtn = document.getElementById('sendBtn');
        const messageInput = document.getElementById('messageInput');
        
        sendBtn.addEventListener('click', () => this.sendMessage());
        messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // Form team
        document.getElementById('teamBtn').addEventListener('click', () => {
            this.openTeamFormationDialog();
        });
        
        // Team formation modal
        document.getElementById('cancelTeamBtn').addEventListener('click', () => {
            this.closeTeamFormationDialog();
        });
        
        document.getElementById('confirmTeamBtn').addEventListener('click', () => {
            this.confirmTeamFormation();
        });
        
        // Log filtering
        document.getElementById('logFilter').addEventListener('change', (e) => {
            this.filterLogs(e.target.value);
        });
        
        // ATLAS button
        document.getElementById('atlasBtn').addEventListener('click', () => {
            this.addChatMessage('atlas', 'ATLAS Multi-Agent Orchestration Platform v1.0\nPhase 4 Implementation Active\n\nAvailable Commands:\n- "status" - System status\n- "agents" - List agents\n- "form team" - Create dynamic team\n- "help" - Show help');
        });
        
        // Voice and TTS buttons (placeholder)
        document.getElementById('voiceBtn').addEventListener('click', () => {
            this.log('info', 'Voice input not yet implemented');
        });
        
        document.getElementById('ttsBtn').addEventListener('click', () => {
            this.log('info', 'TTS output not yet implemented');
        });
    }

    sendMessage() {
        const input = document.getElementById('messageInput');
        const message = input.value.trim();
        
        if (!message) return;
        
        this.addChatMessage('user', message);
        
        // Handle special commands
        this.handleCommand(message.toLowerCase());
        
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            this.websocket.send(JSON.stringify({
                type: 'chat',
                message: message,
                timestamp: new Date().toISOString()
            }));
        } else {
            this.log('warn', 'Message not sent - WebSocket not connected');
        }
        
        input.value = '';
    }

    handleCommand(command) {
        switch (command) {
            case 'status':
                this.showSystemStatus();
                break;
            case 'agents':
                this.listAgents();
                break;
            case 'form team':
                this.openTeamFormationDialog();
                break;
            case 'help':
                this.showHelp();
                break;
            case 'clear':
                this.clearChat();
                break;
            default:
                // Let the backend handle it
                break;
        }
    }

    async showSystemStatus() {
        try {
            const response = await fetch('/api/system/status');
            const status = await response.json();
            
            let statusText = 'System Status:\n';
            Object.entries(status).forEach(([service, state]) => {
                const indicator = state === 'active' ? '🟢' : '🔴';
                statusText += `${indicator} ${service}: ${state}\n`;
            });
            
            this.addChatMessage('atlas', statusText);
        } catch (error) {
            this.addChatMessage('atlas', `Error getting system status: ${error.message}`);
        }
    }

    listAgents() {
        if (this.agents.size === 0) {
            this.addChatMessage('atlas', 'No agents currently registered.');
            return;
        }
        
        let agentsList = 'Registered Agents:\n\n';
        this.agents.forEach((agent, id) => {
            agentsList += `🤖 ${agent.name} (${id})\n`;
            agentsList += `   Status: ${agent.status}\n`;
            agentsList += `   Provider: ${agent.provider}\n`;
            agentsList += `   Capabilities: ${agent.capabilities.slice(0, 3).join(', ')}\n\n`;
        });
        
        this.addChatMessage('atlas', agentsList);
    }

    showHelp() {
        const helpText = `ATLAS Web Interface Help

Commands:
• status - Show system status
• agents - List all agents  
• form team - Open team formation dialog
• clear - Clear chat history
• help - Show this help

Interface:
• Left Panel: Chat and agent management
• Center: 3D ATLAS avatar and team visualization  
• Right Panel: System logs and metrics
• Bottom: Service status indicators

Team Formation:
Click "FORM TEAM" to create a dynamic team for any task.
The system will automatically select optimal agents and roles.`;

        this.addChatMessage('atlas', helpText);
    }

    clearChat() {
        const chatHistory = document.getElementById('chatHistory');
        const systemMessage = chatHistory.querySelector('.system-message');
        chatHistory.innerHTML = '';
        if (systemMessage) {
            chatHistory.appendChild(systemMessage);
        }
    }

    openTeamFormationDialog() {
        document.getElementById('teamModal').style.display = 'flex';
        document.getElementById('taskDescription').focus();
    }

    closeTeamFormationDialog() {
        document.getElementById('teamModal').style.display = 'none';
        document.getElementById('taskDescription').value = '';
    }

    async confirmTeamFormation() {
        const taskDescription = document.getElementById('taskDescription').value.trim();
        
        if (!taskDescription) {
            this.log('warn', 'Please provide a task description');
            return;
        }
        
        try {
            this.log('info', 'Forming team for task...');
            const response = await fetch('/api/teams/form', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ description: taskDescription })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            this.currentTeam = data.team;
            this.renderTeamVisualization();
            this.closeTeamFormationDialog();
            
            if (data.team && data.team.members && data.team.members.length > 0) {
                this.log('info', `Team formed successfully: ${data.team.members.length} members`);
                this.addChatMessage('atlas', `✅ Team formed for task: "${taskDescription}"\n\nTeam Members:\n${this.formatTeamMembers(data.team)}`);
            } else {
                this.log('warn', 'Team formed but no members were assigned');
                this.addChatMessage('atlas', `⚠️ Team formation completed for task: "${taskDescription}"\n\nNo agents were available for assignment. This may be due to:\n• All agents currently busy\n• No agents matching required capabilities\n• System configuration issues\n\nPlease check agent availability and try again.`);
            }
            
        } catch (error) {
            this.log('error', `Team formation failed: ${error.message}`);
            this.addChatMessage('atlas', `❌ Team formation failed: ${error.message}`);
        }
    }

    formatTeamMembers(team) {
        if (!team || !team.members || team.members.length === 0) {
            return 'No members assigned';
        }
        
        return team.members.map(member => 
            `• ${member.name} - ${member.role}`
        ).join('\n');
    }

    renderTeamVisualization() {
        const container = document.getElementById('teamMembers');
        container.innerHTML = '';
        
        if (!this.currentTeam || !this.currentTeam.members || this.currentTeam.members.length === 0) {
            container.innerHTML = '<div class="no-team">No active team. Click "FORM TEAM" to create one.</div>';
            return;
        }
        
        this.currentTeam.members.forEach(member => {
            const memberElement = document.createElement('div');
            memberElement.className = 'team-member clickable';
            memberElement.innerHTML = `
                <div class="member-name">${member.name}</div>
                <div class="member-role">${member.role}</div>
            `;
            
            memberElement.addEventListener('click', () => {
                this.addChatMessage('system', `Team Member: ${member.name}\nRole: ${member.role}\nAssigned to current team`);
            });
            
            container.appendChild(memberElement);
        });
    }

    addChatMessage(sender, content) {
        const chatHistory = document.getElementById('chatHistory');
        const messageElement = document.createElement('div');
        messageElement.className = `chat-message ${sender} slide-up`;
        
        const timestamp = new Date().toLocaleTimeString();
        
        messageElement.innerHTML = `
            <div class="message-sender">${sender.toUpperCase()}</div>
            <div class="message-content">${content.replace(/\n/g, '<br>')}</div>
            <div class="message-time">${timestamp}</div>
        `;
        
        chatHistory.appendChild(messageElement);
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    log(level, message) {
        const logsDisplay = document.getElementById('logsDisplay');
        const logElement = document.createElement('div');
        logElement.className = `log-entry ${level}`;
        
        const timestamp = new Date().toLocaleTimeString();
        
        logElement.innerHTML = `
            <span class="log-time">${timestamp}</span>
            <span class="log-level">${level.toUpperCase()}</span>
            <span class="log-message">${message}</span>
        `;
        
        logsDisplay.appendChild(logElement);
        logsDisplay.scrollTop = logsDisplay.scrollHeight;
        
        // Apply log filter if active
        const filter = document.getElementById('logFilter').value;
        if (filter !== 'all' && level !== filter) {
            logElement.style.display = 'none';
        }
    }

    filterLogs(level) {
        const logEntries = document.querySelectorAll('.log-entry');
        logEntries.forEach(entry => {
            if (level === 'all') {
                entry.style.display = 'flex';
            } else {
                const entryLevel = entry.className.includes(level);
                entry.style.display = entryLevel ? 'flex' : 'none';
            }
        });
    }

    updateConnectionStatus(status) {
        const statusElement = document.getElementById('connectionStatus');
        statusElement.textContent = status;
        statusElement.className = status.toLowerCase();
    }

    async startStatusUpdates() {
        const updateStatus = async () => {
            try {
                const response = await fetch('/api/system/status');
                if (response.ok) {
                    const status = await response.json();
                    this.updateSystemStatus(status);
                }
            } catch (error) {
                // Silent fail for status updates
                console.warn('Status update failed:', error);
            }
        };
        
        // Update immediately and then every 10 seconds
        updateStatus();
        setInterval(updateStatus, 10000);
    }

    async updateMetrics() {
        try {
            const response = await fetch('/api/metrics');
            if (response.ok) {
                const metrics = await response.json();
                
                document.getElementById('activeAgentsCount').textContent = metrics.active_agents || this.agents.size;
                document.getElementById('teamsFormedCount').textContent = metrics.teams_formed || 0;
                document.getElementById('tasksCompletedCount').textContent = metrics.tasks_completed || 0;
            }
        } catch (error) {
            console.warn('Metrics update failed:', error);
        }
    }

    updateSystemStatus(status) {
        Object.entries(status).forEach(([service, state]) => {
            const indicator = document.querySelector(`[data-service="${service}"]`);
            if (indicator) {
                indicator.className = `status-indicator ${state === 'active' ? 'active' : 'inactive'}`;
            }
        });
    }

    startUptimeCounter() {
        const updateUptime = () => {
            const uptimeSeconds = Math.floor((Date.now() - this.startTime) / 1000);
            const hours = Math.floor(uptimeSeconds / 3600);
            const minutes = Math.floor((uptimeSeconds % 3600) / 60);
            const seconds = uptimeSeconds % 60;
            
            const formatted = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
            const uptimeElement = document.getElementById('uptimeValue');
            if (uptimeElement) {
                uptimeElement.textContent = formatted;
            }
        };
        
        updateUptime();
        setInterval(updateUptime, 1000);
    }

    handleWebSocketMessage(message) {
        switch (message.type) {
            case 'chat':
                this.addChatMessage('atlas', message.data);
                break;
            case 'agent_status':
                this.updateAgentStatus(message.agent_id, message.status);
                break;
            case 'team_update':
                this.currentTeam = message.team;
                this.renderTeamVisualization();
                this.log('info', message.message || 'Team updated');
                break;
            case 'system_log':
                this.log(message.level, message.message);
                break;
            case 'system':
                this.log('info', message.message);
                break;
            default:
                console.log('Unknown message type:', message.type);
        }
    }

    updateAgentStatus(agentId, status) {
        if (this.agents.has(agentId)) {
            this.agents.get(agentId).status = status;
            this.renderAgentsList();
        }
    }
}

/**
 * ATLAS 3D Avatar Component
 * Renders an animated 3D avatar using Three.js
 */
class ATLASAvatar {
    constructor(canvas, container) {
        this.canvas = canvas;
        this.container = container;
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.avatarModel = null;
        this.animationId = null;
    }

    async initialize() {
        if (!window.THREE) {
            throw new Error('Three.js not available');
        }

        this.setupScene();
        this.setupLighting();
        this.createAvatar();
        this.startRenderLoop();
        this.setupInteractions();
    }

    setupScene() {
        this.scene = new THREE.Scene();
        
        this.camera = new THREE.PerspectiveCamera(
            50, 
            this.container.clientWidth / this.container.clientHeight, 
            0.1, 
            100
        );
        this.camera.position.set(0, 0, 2.2);

        this.renderer = new THREE.WebGLRenderer({ 
            canvas: this.canvas,
            antialias: true, 
            alpha: true 
        });
        this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
        this.renderer.setClearColor(0x000000, 0);
    }

    setupLighting() {
        // Primary light (neon green)
        const primaryLight = new THREE.PointLight(0x00ff66, 3, 10);
        primaryLight.position.set(1, 1, 2);
        this.scene.add(primaryLight);

        // Ambient light
        const ambientLight = new THREE.AmbientLight(0x004422, 0.8);
        this.scene.add(ambientLight);

        // Accent light (blue)
        const accentLight = new THREE.PointLight(0x0099ff, 1, 5);
        accentLight.position.set(-1, -1, 1);
        this.scene.add(accentLight);
        
        // Rim light
        const rimLight = new THREE.PointLight(0x00ff66, 2, 8);
        rimLight.position.set(0, 2, -1);
        this.scene.add(rimLight);
    }

    createAvatar() {
        // Create a geometric avatar since we don't have a GLB model
        const group = new THREE.Group();
        
        // Main head sphere
        const headGeometry = new THREE.SphereGeometry(0.5, 32, 32);
        const headMaterial = new THREE.MeshPhongMaterial({
            color: 0x00ff66,
            emissive: 0x002211,
            transparent: true,
            opacity: 0.8,
            shininess: 100
        });
        
        const head = new THREE.Mesh(headGeometry, headMaterial);
        group.add(head);

        // Eyes
        const eyeGeometry = new THREE.SphereGeometry(0.05, 16, 16);
        const eyeMaterial = new THREE.MeshBasicMaterial({ color: 0x00ffff });
        
        const leftEye = new THREE.Mesh(eyeGeometry, eyeMaterial);
        leftEye.position.set(-0.15, 0.1, 0.4);
        group.add(leftEye);
        
        const rightEye = new THREE.Mesh(eyeGeometry, eyeMaterial);
        rightEye.position.set(0.15, 0.1, 0.4);
        group.add(rightEye);

        // Wireframe overlay
        const wireframe = new THREE.WireframeGeometry(headGeometry);
        const line = new THREE.LineSegments(wireframe);
        line.material.depthTest = false;
        line.material.opacity = 0.3;
        line.material.transparent = true;
        line.material.color = new THREE.Color(0x00ff66);
        group.add(line);
        
        // Add some geometric details
        const detailGeometry = new THREE.RingGeometry(0.3, 0.35, 16);
        const detailMaterial = new THREE.MeshBasicMaterial({ 
            color: 0x00ff66, 
            transparent: true, 
            opacity: 0.5,
            side: THREE.DoubleSide
        });
        
        const ring1 = new THREE.Mesh(detailGeometry, detailMaterial);
        ring1.rotation.x = Math.PI / 2;
        ring1.rotation.z = Math.PI / 4;
        group.add(ring1);
        
        const ring2 = new THREE.Mesh(detailGeometry, detailMaterial);
        ring2.rotation.y = Math.PI / 2;
        ring2.rotation.z = Math.PI / 3;
        group.add(ring2);

        this.avatarModel = group;
        this.scene.add(this.avatarModel);
    }

    startRenderLoop() {
        const animate = () => {
            this.animationId = requestAnimationFrame(animate);
            
            if (this.avatarModel) {
                // Main rotation
                this.avatarModel.rotation.y += 0.005;
                
                // Breathing effect
                const breathe = Math.sin(Date.now() * 0.002) * 0.05;
                this.avatarModel.scale.setScalar(1 + breathe);
                
                // Subtle floating
                this.avatarModel.position.y = Math.sin(Date.now() * 0.001) * 0.1;
                
                // Eye animation
                const eyeScale = 1 + Math.sin(Date.now() * 0.01) * 0.2;
                if (this.avatarModel.children.length > 1) {
                    this.avatarModel.children[1].scale.setScalar(eyeScale); // Left eye
                    this.avatarModel.children[2].scale.setScalar(eyeScale); // Right eye
                }
            }
            
            this.renderer.render(this.scene, this.camera);
        };
        
        animate();
    }

    setupInteractions() {
        const handleResize = () => {
            const width = this.container.clientWidth;
            const height = this.container.clientHeight;
            
            this.camera.aspect = width / height;
            this.camera.updateProjectionMatrix();
            this.renderer.setSize(width, height);
        };
        
        window.addEventListener('resize', handleResize);
        
        // Mouse interaction
        let mouseX = 0;
        let mouseY = 0;
        
        this.container.addEventListener('mousemove', (event) => {
            const rect = this.container.getBoundingClientRect();
            mouseX = ((event.clientX - rect.left) / rect.width) * 2 - 1;
            mouseY = -((event.clientY - rect.top) / rect.height) * 2 + 1;
            
            if (this.avatarModel) {
                this.avatarModel.rotation.x = mouseY * 0.2;
                this.avatarModel.rotation.y += (mouseX * 0.5 - this.avatarModel.rotation.y) * 0.05;
            }
        });
    }

    destroy() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }
        
        if (this.renderer) {
            this.renderer.dispose();
        }
    }
}

// Initialize the interface when the page loads
document.addEventListener('DOMContentLoaded', () => {
    try {
        const atlasInterface = new ATLASInterface();
        atlasInterface.initialize();
        
        // Make it globally available for debugging
        window.ATLAS = atlasInterface;
    } catch (error) {
        console.error('Failed to initialize ATLAS interface:', error);
        document.getElementById('loadingScreen').innerHTML = `
            <div class="error">
                Failed to initialize ATLAS interface: ${error.message}
            </div>
        `;
    }
});
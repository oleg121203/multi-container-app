/**
 * ATLAS Enhanced Features - Phase 5 Production Enhancements
 * 
 * Adds advanced functionality for production deployment:
 * - Enhanced error handling and recovery
 * - Performance monitoring and optimization  
 * - Advanced team management
 * - Real-time metrics and analytics
 * - Voice interaction capabilities
 */

class ATLASEnhanced {
    constructor(baseInterface) {
        this.interface = baseInterface;
        this.performanceMetrics = {
            responseTime: [],
            errorRate: 0,
            apiCalls: 0,
            successfulCalls: 0
        };
        this.voiceEnabled = false;
        this.speechRecognition = null;
        this.speechSynthesis = null;
        
        this.initializeEnhancements();
    }

    async initializeEnhancements() {
        try {
            await this.setupVoiceCapabilities();
            this.setupPerformanceMonitoring();
            this.setupAdvancedTeamManagement();
            this.setupRealTimeAnalytics();
            this.setupErrorRecovery();
            
            console.log('ATLAS Enhanced features initialized successfully');
        } catch (error) {
            console.error('Enhanced features initialization failed:', error);
        }
    }

    // Voice Interaction Capabilities
    async setupVoiceCapabilities() {
        try {
            // Check for Speech Recognition support
            if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
                this.speechRecognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
                this.speechRecognition.continuous = false;
                this.speechRecognition.interimResults = false;
                this.speechRecognition.lang = 'en-US';
                
                this.speechRecognition.onresult = (event) => {
                    const transcript = event.results[0][0].transcript;
                    this.handleVoiceInput(transcript);
                };
                
                this.speechRecognition.onerror = (event) => {
                    console.error('Speech recognition error:', event.error);
                    this.interface.log('warn', `Voice recognition error: ${event.error}`);
                };
                
                this.voiceEnabled = true;
                this.interface.log('info', 'Voice recognition capabilities enabled');
            }

            // Check for Speech Synthesis support
            if ('speechSynthesis' in window) {
                this.speechSynthesis = window.speechSynthesis;
                this.interface.log('info', 'Text-to-speech capabilities enabled');
            }

            // Update UI buttons
            this.updateVoiceUI();
            
        } catch (error) {
            console.error('Voice setup failed:', error);
            this.interface.log('warn', 'Voice capabilities not available in this browser');
        }
    }

    updateVoiceUI() {
        const voiceBtn = document.getElementById('voiceBtn');
        const ttsBtn = document.getElementById('ttsBtn');
        
        if (voiceBtn && this.voiceEnabled) {
            voiceBtn.style.display = 'block';
            voiceBtn.addEventListener('click', () => this.startVoiceRecognition());
        }
        
        if (ttsBtn && this.speechSynthesis) {
            ttsBtn.style.display = 'block';
            ttsBtn.addEventListener('click', () => this.toggleTTS());
        }
    }

    startVoiceRecognition() {
        if (this.speechRecognition && this.voiceEnabled) {
            this.interface.log('info', 'Listening for voice input...');
            this.speechRecognition.start();
            
            // Visual feedback
            const voiceBtn = document.getElementById('voiceBtn');
            voiceBtn.textContent = 'LISTENING...';
            voiceBtn.style.color = '#ff4444';
            
            setTimeout(() => {
                voiceBtn.textContent = 'MIC';
                voiceBtn.style.color = '';
            }, 5000);
        }
    }

    handleVoiceInput(transcript) {
        this.interface.log('info', `Voice input received: "${transcript}"`);
        
        // Process voice commands
        if (transcript.toLowerCase().includes('form team')) {
            this.interface.openTeamFormationDialog();
        } else if (transcript.toLowerCase().includes('show agents')) {
            this.interface.listAgents();
        } else if (transcript.toLowerCase().includes('system status')) {
            this.interface.showSystemStatus();
        } else {
            // Send as regular chat message
            document.getElementById('messageInput').value = transcript;
            this.interface.sendMessage();
        }
    }

    speak(text) {
        if (this.speechSynthesis) {
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.rate = 0.8;
            utterance.pitch = 1.0;
            utterance.volume = 0.8;
            this.speechSynthesis.speak(utterance);
        }
    }

    toggleTTS() {
        const ttsBtn = document.getElementById('ttsBtn');
        if (this.speechSynthesis.speaking) {
            this.speechSynthesis.cancel();
            ttsBtn.textContent = 'TTS';
            this.interface.log('info', 'Text-to-speech stopped');
        } else {
            const lastMessage = document.querySelector('.chat-message:last-child .message-content');
            if (lastMessage) {
                this.speak(lastMessage.textContent);
                ttsBtn.textContent = 'STOP';
                this.interface.log('info', 'Text-to-speech started');
            }
        }
    }

    // Performance Monitoring
    setupPerformanceMonitoring() {
        // Override fetch to monitor API performance
        const originalFetch = window.fetch;
        window.fetch = async (...args) => {
            const startTime = performance.now();
            this.performanceMetrics.apiCalls++;
            
            try {
                const response = await originalFetch(...args);
                const endTime = performance.now();
                const responseTime = endTime - startTime;
                
                this.performanceMetrics.responseTime.push(responseTime);
                this.performanceMetrics.successfulCalls++;
                
                // Keep only last 100 response times
                if (this.performanceMetrics.responseTime.length > 100) {
                    this.performanceMetrics.responseTime.shift();
                }
                
                this.updatePerformanceMetrics();
                return response;
            } catch (error) {
                this.performanceMetrics.errorRate++;
                this.updatePerformanceMetrics();
                throw error;
            }
        };
    }

    updatePerformanceMetrics() {
        const avgResponseTime = this.performanceMetrics.responseTime.length > 0 
            ? this.performanceMetrics.responseTime.reduce((a, b) => a + b, 0) / this.performanceMetrics.responseTime.length 
            : 0;

        const errorRate = this.performanceMetrics.apiCalls > 0 
            ? (this.performanceMetrics.errorRate / this.performanceMetrics.apiCalls) * 100 
            : 0;

        // Update metrics display
        const metricsPanel = document.querySelector('.metrics-panel .metrics-grid');
        if (metricsPanel) {
            // Add performance metrics
            const performanceMetric = metricsPanel.querySelector('#performanceMetric') || document.createElement('div');
            performanceMetric.id = 'performanceMetric';
            performanceMetric.className = 'metric';
            performanceMetric.innerHTML = `
                <span class="metric-label">Avg Response Time</span>
                <span class="metric-value">${Math.round(avgResponseTime)}ms</span>
            `;
            
            const errorRateMetric = metricsPanel.querySelector('#errorRateMetric') || document.createElement('div');
            errorRateMetric.id = 'errorRateMetric';
            errorRateMetric.className = 'metric';
            errorRateMetric.innerHTML = `
                <span class="metric-label">Error Rate</span>
                <span class="metric-value">${errorRate.toFixed(1)}%</span>
            `;
            
            if (!metricsPanel.contains(performanceMetric)) {
                metricsPanel.appendChild(performanceMetric);
            }
            if (!metricsPanel.contains(errorRateMetric)) {
                metricsPanel.appendChild(errorRateMetric);
            }
        }
    }

    // Advanced Team Management
    setupAdvancedTeamManagement() {
        // Add team management capabilities
        this.teamHistory = [];
        this.activeTeams = new Map();
        
        // Override team formation to add history tracking
        const originalOpenTeamDialog = this.interface.openTeamFormationDialog;
        this.interface.openTeamFormationDialog = () => {
            this.showAdvancedTeamDialog();
        };
    }

    showAdvancedTeamDialog() {
        // Create enhanced team formation dialog
        const existingModal = document.getElementById('teamModal');
        if (existingModal) {
            existingModal.remove();
        }

        const modal = document.createElement('div');
        modal.id = 'teamModal';
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <h3>🤖 Form Dynamic Team</h3>
                <div class="form-section">
                    <label for="taskDescription">Task Description:</label>
                    <textarea id="taskDescription" rows="4" placeholder="Describe the task you want the team to work on..."></textarea>
                </div>
                
                <div class="form-section">
                    <label for="teamSize">Team Size:</label>
                    <select id="teamSize">
                        <option value="auto">Auto (Recommended)</option>
                        <option value="2">2 Agents</option>
                        <option value="3">3 Agents</option>
                        <option value="4">4 Agents</option>
                        <option value="5">5 Agents</option>
                    </select>
                </div>
                
                <div class="form-section">
                    <label for="teamPriority">Priority:</label>
                    <select id="teamPriority">
                        <option value="normal">Normal</option>
                        <option value="high">High</option>
                        <option value="urgent">Urgent</option>
                    </select>
                </div>
                
                <div class="form-section">
                    <h4>Recent Teams:</h4>
                    <div id="recentTeams" class="recent-teams">
                        ${this.teamHistory.slice(-3).map(team => `
                            <div class="recent-team" onclick="this.loadTeamTemplate('${team.id}')">
                                <span class="team-name">${team.task.substring(0, 30)}...</span>
                                <span class="team-members">${team.members.length} members</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
                
                <div class="modal-buttons">
                    <button class="btn" id="cancelTeamBtn">Cancel</button>
                    <button class="btn btn-atlas" id="confirmTeamBtn">Form Team</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
        modal.style.display = 'flex';

        // Event listeners
        document.getElementById('cancelTeamBtn').addEventListener('click', () => {
            modal.remove();
        });

        document.getElementById('confirmTeamBtn').addEventListener('click', () => {
            this.handleAdvancedTeamFormation();
        });

        document.getElementById('taskDescription').focus();
    }

    async handleAdvancedTeamFormation() {
        const description = document.getElementById('taskDescription').value;
        const teamSize = document.getElementById('teamSize').value;
        const priority = document.getElementById('teamPriority').value;

        if (!description.trim()) {
            this.interface.log('warn', 'Please provide a task description');
            return;
        }

        try {
            const response = await fetch('/api/teams/form', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    description,
                    constraints: {
                        teamSize: teamSize === 'auto' ? null : parseInt(teamSize),
                        priority
                    }
                })
            });

            const data = await response.json();
            
            // Add to team history
            this.teamHistory.push({
                id: `team_${Date.now()}`,
                task: description,
                members: data.team.members || [],
                formed_at: new Date().toISOString(),
                priority
            });

            this.interface.currentTeam = data.team;
            this.interface.renderTeamVisualization();
            this.interface.log('info', `Team formed successfully: ${data.team.members.length} members`);
            
            // Close modal
            document.getElementById('teamModal').remove();

            // Speak confirmation if TTS is available
            if (this.speechSynthesis) {
                this.speak(`Team formed successfully with ${data.team.members.length} members`);
            }

        } catch (error) {
            this.interface.log('error', `Team formation failed: ${error.message}`);
        }
    }

    // Real-time Analytics
    setupRealTimeAnalytics() {
        this.analytics = {
            pageViews: 1,
            interactions: 0,
            sessionStart: Date.now(),
            features: {
                voiceCommands: 0,
                teamsFormed: 0,
                agentInteractions: 0
            }
        };

        // Track interactions
        document.addEventListener('click', (event) => {
            if (event.target.matches('.btn, .agent-card, .team-member')) {
                this.analytics.interactions++;
                this.updateAnalyticsDashboard();
            }
        });

        // Send analytics periodically
        setInterval(() => {
            this.sendAnalytics();
        }, 60000); // Every minute
    }

    updateAnalyticsDashboard() {
        const sessionTime = Math.floor((Date.now() - this.analytics.sessionStart) / 1000);
        
        // Update session metrics in UI
        const sessionMetric = document.querySelector('#sessionMetric') || document.createElement('div');
        sessionMetric.id = 'sessionMetric';
        sessionMetric.className = 'metric';
        sessionMetric.innerHTML = `
            <span class="metric-label">Session Time</span>
            <span class="metric-value">${Math.floor(sessionTime / 60)}m ${sessionTime % 60}s</span>
        `;

        const interactionMetric = document.querySelector('#interactionMetric') || document.createElement('div');
        interactionMetric.id = 'interactionMetric';
        interactionMetric.className = 'metric';
        interactionMetric.innerHTML = `
            <span class="metric-label">Interactions</span>
            <span class="metric-value">${this.analytics.interactions}</span>
        `;

        const metricsPanel = document.querySelector('.metrics-panel .metrics-grid');
        if (metricsPanel) {
            if (!metricsPanel.contains(sessionMetric)) {
                metricsPanel.appendChild(sessionMetric);
            }
            if (!metricsPanel.contains(interactionMetric)) {
                metricsPanel.appendChild(interactionMetric);
            }
        }
    }

    async sendAnalytics() {
        try {
            await fetch('/api/analytics', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(this.analytics)
            });
        } catch (error) {
            console.warn('Analytics sending failed:', error);
        }
    }

    // Error Recovery
    setupErrorRecovery() {
        // Global error handler
        window.addEventListener('error', (event) => {
            this.handleGlobalError(event.error);
        });

        // Promise rejection handler
        window.addEventListener('unhandledrejection', (event) => {
            this.handleGlobalError(event.reason);
        });

        // Network error recovery
        this.setupNetworkRecovery();
    }

    handleGlobalError(error) {
        console.error('Global error caught:', error);
        this.interface.log('error', `System error: ${error.message}`);
        
        // Attempt recovery based on error type
        if (error.message.includes('fetch') || error.message.includes('network')) {
            this.attemptNetworkRecovery();
        } else if (error.message.includes('WebSocket')) {
            this.interface.attemptReconnection();
        }
    }

    setupNetworkRecovery() {
        // Monitor network status
        window.addEventListener('online', () => {
            this.interface.log('info', 'Network connection restored');
            this.interface.updateConnectionStatus('Connected');
        });

        window.addEventListener('offline', () => {
            this.interface.log('warn', 'Network connection lost');
            this.interface.updateConnectionStatus('Offline');
        });
    }

    attemptNetworkRecovery() {
        this.interface.log('info', 'Attempting network recovery...');
        
        // Retry after delay
        setTimeout(async () => {
            try {
                await fetch('/api/health');
                this.interface.log('info', 'Network recovery successful');
                await this.interface.loadAgents();
                this.interface.startStatusUpdates();
            } catch (error) {
                this.interface.log('warn', 'Network recovery failed, will retry...');
                setTimeout(() => this.attemptNetworkRecovery(), 10000);
            }
        }, 5000);
    }

    // Advanced Features Toggle
    toggleAdvancedMode() {
        const advancedFeatures = document.querySelector('.advanced-features');
        if (advancedFeatures) {
            advancedFeatures.style.display = advancedFeatures.style.display === 'none' ? 'block' : 'none';
        }
    }

    // Export functionality for debugging
    exportDiagnostics() {
        const diagnostics = {
            timestamp: new Date().toISOString(),
            performance: this.performanceMetrics,
            analytics: this.analytics,
            teamHistory: this.teamHistory,
            agents: Array.from(this.interface.agents.values()),
            currentTeam: this.interface.currentTeam,
            voiceEnabled: this.voiceEnabled,
            sessionUptime: Date.now() - this.analytics.sessionStart
        };

        const blob = new Blob([JSON.stringify(diagnostics, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `atlas-diagnostics-${Date.now()}.json`;
        a.click();
        
        URL.revokeObjectURL(url);
        this.interface.log('info', 'Diagnostics exported successfully');
    }
}

// Initialize enhanced features when the main interface is ready
document.addEventListener('DOMContentLoaded', () => {
    // Wait for main interface to initialize, then add enhancements
    setTimeout(() => {
        if (window.atlasInterface) {
            window.atlasEnhanced = new ATLASEnhanced(window.atlasInterface);
        }
    }, 2000);
});
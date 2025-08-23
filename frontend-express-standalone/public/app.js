class MCPHubApp {
    constructor() {
        this.currentMode = 'chat';
        this.chatMode = 'atlas';
        this.eyeTarget = 'center';
        this.lastMessageId = null;
        this.isLoading = false;
        this.isListening = false;
        this.isContinuousMode = false;
        this.ttsProvider = 'ukraine';
        this.voice = 'atlas';
        this.messages = [];
        this.head3D = null;
        this.recognition = null;
        
        this.API_BASE_URL = window.__CONFIG__?.API_BASE_URL || '/api';
        this.HEAD3D_ASSETS_URL = window.__CONFIG__?.HEAD3D_ASSETS_URL || '/assets';
        
        this.init();
    }

    init() {
        this.initElements();
        this.initEventListeners();
        this.initHead3D();
        this.initSpeechRecognition();
        this.addInitialMessage();
        this.checkConnectivity();
    }

    initElements() {
        // Navigation
        this.navPanel = document.getElementById('nav-panel');
        this.navButtons = document.querySelectorAll('.nav-button');
        
        // Chat
        this.chatContainer = document.getElementById('chat-container');
        this.chatMessages = document.getElementById('chat-messages');
        this.chatInput = document.getElementById('chat-input');
        this.sendButton = document.getElementById('send-button');
        this.voiceButton = document.getElementById('voice-button');
        this.modeButtons = document.querySelectorAll('.mode-button');
        
        // TTS Controls
        this.ttsProviderSelect = document.getElementById('tts-provider');
        this.ttsVoiceSelect = document.getElementById('tts-voice');
        this.continuousModeButton = document.getElementById('continuous-mode');
        
        // Connectivity
        this.connectivityBanner = document.getElementById('connectivity-banner');
        
        // Head3D
        this.head3dCanvas = document.getElementById('head3d-canvas');
        this.head3dStatus = document.getElementById('head3d-status');
    }

    initEventListeners() {
        // Navigation
        this.navButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const mode = e.target.dataset.mode;
                this.switchMode(mode);
            });
        });

        // Chat mode selection
        this.modeButtons.forEach(btn => {
            btn.addEventListener('click', (e) => {
                const mode = e.target.dataset.chatMode;
                this.switchChatMode(mode);
            });
        });

        // Chat input
        this.chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
            this.handleChatActivity('typing');
        });

        this.sendButton.addEventListener('click', () => this.sendMessage());
        this.voiceButton.addEventListener('click', () => this.toggleVoiceInput());

        // TTS controls
        this.ttsProviderSelect.addEventListener('change', (e) => {
            this.ttsProvider = e.target.value;
            this.updateVoiceOptions();
        });

        this.ttsVoiceSelect.addEventListener('change', (e) => {
            this.voice = e.target.value;
        });

        this.continuousModeButton.addEventListener('click', () => {
            this.toggleContinuousMode();
        });

        // Auto-hide navigation
        this.navPanel.addEventListener('mouseenter', () => {
            this.navPanel.classList.remove('hidden');
        });

        this.navPanel.addEventListener('mouseleave', () => {
            setTimeout(() => {
                this.navPanel.classList.add('hidden');
            }, 3500);
        });
    }

    initHead3D() {
        if (!this.head3dCanvas) return;

        this.head3D = new Head3DRenderer(this.head3dCanvas, {
            modelUrl: '/models/DamagedHelmet.glb',
            onModelLoaded: () => {
                this.head3dStatus.textContent = 'Модель завантажена';
            },
            onModelError: (error) => {
                this.head3dStatus.textContent = 'Помилка завантаження';
                console.error('Head3D error:', error);
            }
        });
    }

    initSpeechRecognition() {
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SpeechRecognition = window.webkitSpeechRecognition || window.SpeechRecognition;
            this.recognition = new SpeechRecognition();
            
            this.recognition.continuous = true;
            this.recognition.interimResults = true;
            this.recognition.lang = 'uk-UA';

            this.recognition.onstart = () => {
                this.isListening = true;
                this.voiceButton.classList.add('active');
                console.log('🎤 Голосовий ввід активовано');
            };

            this.recognition.onresult = (event) => {
                let finalTranscript = '';
                for (let i = event.resultIndex; i < event.results.length; i++) {
                    if (event.results[i].isFinal) {
                        finalTranscript += event.results[i][0].transcript;
                    }
                }
                
                if (finalTranscript) {
                    this.chatInput.value = finalTranscript;
                    if (this.isContinuousMode) {
                        this.sendMessage();
                    }
                }
            };

            this.recognition.onend = () => {
                this.isListening = false;
                this.voiceButton.classList.remove('active');
                if (this.isContinuousMode) {
                    setTimeout(() => {
                        this.recognition.start();
                    }, 1000);
                }
            };

            this.recognition.onerror = (event) => {
                console.error('Speech recognition error:', event.error);
                this.isListening = false;
                this.voiceButton.classList.remove('active');
            };
        } else {
            this.voiceButton.style.display = 'none';
        }
    }

    addInitialMessage() {
        const initialMessage = {
            id: '1',
            text: '🤖 Smart Chat System готова! Оберіть режим: Atlas (координація) або Grisha (живе спілкування)',
            sender: 'atlas',
            timestamp: new Date(),
            mode: 'atlas'
        };
        this.messages.push(initialMessage);
        this.renderMessages();
    }

    switchMode(mode) {
        this.currentMode = mode;
        this.navButtons.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.mode === mode);
        });

        // Show/hide appropriate containers
        if (mode === 'chat') {
            this.chatContainer.style.display = 'flex';
        } else {
            this.chatContainer.style.display = 'none';
            // TODO: Show dashboard or control panels
        }
    }

    switchChatMode(mode) {
        this.chatMode = mode;
        this.modeButtons.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.chatMode === mode);
        });
    }

    async sendMessage() {
        const text = this.chatInput.value.trim();
        if (!text || this.isLoading) return;

        // Add user message
        const userMessage = {
            id: Date.now().toString(),
            text: text,
            sender: 'user',
            timestamp: new Date(),
            mode: this.chatMode
        };

        this.messages.push(userMessage);
        this.chatInput.value = '';
        this.renderMessages();
        this.handleChatActivity('message', userMessage.id);

        // Show loading
        this.isLoading = true;
        this.sendButton.disabled = true;
        this.sendButton.innerHTML = '<span class="loading"></span>';

        try {
            const response = await fetch(`${this.API_BASE_URL}/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: text,
                    mode: this.chatMode,
                    history: this.messages.slice(-5) // Send last 5 messages for context
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();

            // Add Atlas response
            const atlasMessage = {
                id: data.id || Date.now().toString(),
                text: data.text || 'Немає відповіді',
                sender: this.chatMode === 'grisha' ? 'grisha' : 'atlas',
                timestamp: new Date(data.timestamp || Date.now()),
                mode: data.mode || this.chatMode
            };

            this.messages.push(atlasMessage);
            this.renderMessages();
            this.handleChatActivity('message', atlasMessage.id);

            // TTS if enabled
            if (data.text) {
                this.playTTS(data.text);
            }

        } catch (error) {
            console.error('Send message error:', error);
            const errorMessage = {
                id: Date.now().toString(),
                text: `❌ Помилка: ${error.message}. Переконайтеся, що сервер запущений.`,
                sender: 'atlas',
                timestamp: new Date(),
                mode: this.chatMode
            };
            this.messages.push(errorMessage);
            this.renderMessages();
            this.showConnectivityError();
        } finally {
            this.isLoading = false;
            this.sendButton.disabled = false;
            this.sendButton.textContent = 'Надіслати';
        }
    }

    async playTTS(text) {
        try {
            const response = await fetch(`${this.API_BASE_URL}/tts`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    text: text,
                    voice: this.voice,
                    provider: this.ttsProvider
                })
            });

            if (response.ok) {
                const data = await response.json();
                if (data.audioUrl) {
                    const audio = new Audio(data.audioUrl);
                    audio.play().catch(console.error);
                    
                    // Animate head during speech
                    if (this.head3D) {
                        this.head3D.startSpeechAnimation(audio);
                    }
                }
            }
        } catch (error) {
            console.error('TTS error:', error);
        }
    }

    toggleVoiceInput() {
        if (!this.recognition) return;

        if (this.isListening) {
            this.recognition.stop();
        } else {
            this.recognition.start();
        }
    }

    toggleContinuousMode() {
        this.isContinuousMode = !this.isContinuousMode;
        this.continuousModeButton.classList.toggle('active', this.isContinuousMode);
        
        if (this.isContinuousMode && this.recognition && !this.isListening) {
            this.recognition.start();
        }
    }

    updateVoiceOptions() {
        const voices = {
            ukraine: [
                { key: 'atlas', label: 'Atlas' },
                { key: 'dmytro', label: 'Dmytro' },
                { key: 'tetiana', label: 'Tetiana' },
                { key: 'mykyta', label: 'Mykyta' },
                { key: 'lada', label: 'Lada' },
                { key: 'oleksa', label: 'Oleksa' }
            ],
            coqui: [
                { key: 'atlas', label: 'Atlas (M)' },
                { key: 'aoede', label: 'Aoede (F)' },
                { key: 'kore', label: 'Kore (F)' },
                { key: 'uk_male', label: 'Taras (M)' },
                { key: 'uk_female', label: 'Olena (F)' },
                { key: 'xtts_v2_uk', label: 'XTTS v2' }
            ],
            gemini: [
                { key: 'Aoede', label: 'Aoede' },
                { key: 'Kore', label: 'Kore' }
            ]
        };

        const currentVoices = voices[this.ttsProvider] || voices.ukraine;
        this.ttsVoiceSelect.innerHTML = '';
        
        currentVoices.forEach(voice => {
            const option = document.createElement('option');
            option.value = voice.key;
            option.textContent = voice.label;
            this.ttsVoiceSelect.appendChild(option);
        });

        this.voice = currentVoices[0].key;
        this.ttsVoiceSelect.value = this.voice;
    }

    renderMessages() {
        this.chatMessages.innerHTML = '';
        
        this.messages.forEach(message => {
            const messageEl = document.createElement('div');
            messageEl.className = `message ${message.sender}`;
            messageEl.id = `message-${message.id}`;
            
            messageEl.innerHTML = `
                <div class="message-sender">${this.getSenderName(message.sender, message.mode)}</div>
                <div class="message-text">${message.text}</div>
                <div class="message-timestamp">${this.formatTime(message.timestamp)}</div>
            `;
            
            this.chatMessages.appendChild(messageEl);
        });

        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }

    getSenderName(sender, mode) {
        if (sender === 'user') return 'Ви';
        if (sender === 'grisha') return 'Grisha Live';
        if (mode === 'consulting') return 'Consulting Atlas';
        return 'Atlas System';
    }

    formatTime(timestamp) {
        const now = new Date();
        const time = new Date(timestamp);
        const diffMs = now - time;
        
        if (diffMs < 60000) return 'Зараз';
        if (diffMs < 3600000) return `${Math.floor(diffMs / 60000)} хв тому`;
        if (diffMs < 86400000) return time.toLocaleTimeString('uk-UA', { hour: '2-digit', minute: '2-digit' });
        return time.toLocaleDateString('uk-UA');
    }

    handleChatActivity(activity, messageId) {
        if (activity === 'typing') {
            this.eyeTarget = 'input';
            if (this.head3D) {
                this.head3D.setEyeTarget(0, 0.2, 0);
            }
            setTimeout(() => {
                this.eyeTarget = 'center';
                if (this.head3D) {
                    this.head3D.setEyeTarget(0, 0, 0);
                }
            }, 2000);
        } else if (activity === 'message' && messageId) {
            this.eyeTarget = 'message';
            this.lastMessageId = messageId;
            if (this.head3D) {
                this.head3D.setEyeTarget(0, -0.2, 0);
            }
            setTimeout(() => {
                this.eyeTarget = 'center';
                if (this.head3D) {
                    this.head3D.setEyeTarget(0, 0, 0);
                }
            }, 3000);
        }
    }

    async checkConnectivity() {
        try {
            const response = await fetch(`${this.API_BASE_URL}/health`);
            if (response.ok) {
                this.hideConnectivityError();
            } else {
                this.showConnectivityError();
            }
        } catch (error) {
            this.showConnectivityError();
        }

        // Check every 30 seconds
        setTimeout(() => this.checkConnectivity(), 30000);
    }

    showConnectivityError() {
        this.connectivityBanner.classList.add('show');
    }

    hideConnectivityError() {
        this.connectivityBanner.classList.remove('show');
    }
}

// Head3D Renderer Class
class Head3DRenderer {
    constructor(canvas, options = {}) {
        this.canvas = canvas;
        this.options = options;
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.head = null;
        this.eyeTarget = new THREE.Vector3(0, 0, 0);
        this.currentEyeTarget = new THREE.Vector3(0, 0, 0);
        this.intensity = 0.005;
        this.modelLoaded = false;
        
        this.init();
    }

    init() {
        // Initialize Three.js scene
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x000000);

        this.camera = new THREE.PerspectiveCamera(35, 1, 0.1, 100);
        this.camera.position.set(0, 0.4, 4);

        this.renderer = new THREE.WebGLRenderer({
            canvas: this.canvas,
            antialias: true,
        });

        // Create placeholder (wireframe icosahedron)
        const placeholderGeo = new THREE.IcosahedronGeometry(0.8, 2);
        const placeholderMat = new THREE.MeshBasicMaterial({
            color: 0x00ff66,
            wireframe: true,
        });
        const placeholder = new THREE.Mesh(placeholderGeo, placeholderMat);
        this.scene.add(placeholder);

        // Head group that will contain the loaded model
        this.head = new THREE.Group();
        this.scene.add(this.head);

        // Add lighting
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
        this.scene.add(ambientLight);
        const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
        dirLight.position.set(2, 4, 3);
        this.scene.add(dirLight);
        const fillLight = new THREE.PointLight(0x22ff88, 0.4);
        fillLight.position.set(-3, 1, 2);
        this.scene.add(fillLight);

        // Load model
        this.loadModel();

        // Start animation loop
        this.animate();

        // Handle resize
        this.handleResize();
        window.addEventListener('resize', () => this.handleResize());
    }

    loadModel() {
        const loader = new THREE.GLTFLoader();
        const modelUrl = this.options.modelUrl || '/models/DamagedHelmet.glb';
        
        loader.load(
            modelUrl,
            (gltf) => {
                // Clear existing children
                while (this.head.children.length) {
                    this.head.remove(this.head.children[0]);
                }
                
                const model = gltf.scene;
                
                // Center and scale the model
                const box = new THREE.Box3().setFromObject(model);
                const size = new THREE.Vector3();
                box.getSize(size);
                const center = new THREE.Vector3();
                box.getCenter(center);
                model.position.sub(center);
                const maxDim = Math.max(size.x, size.y, size.z);
                const scale = 2.0 / (maxDim || 1);
                model.scale.setScalar(scale);
                model.rotation.y = Math.PI;
                
                this.head.add(model);
                this.modelLoaded = true;
                
                if (this.options.onModelLoaded) {
                    this.options.onModelLoaded();
                }
            },
            undefined,
            (error) => {
                console.error('Failed to load GLB model:', error);
                if (this.options.onModelError) {
                    this.options.onModelError(error);
                }
            }
        );
    }

    animate() {
        if (!this.scene || !this.camera || !this.renderer) return;

        // Smooth eye tracking interpolation
        this.currentEyeTarget.lerp(this.eyeTarget, 0.05);

        // Apply rotation based on eye target
        this.head.rotation.y = this.currentEyeTarget.x * (0.3 + this.intensity * 10);
        this.head.rotation.x = -this.currentEyeTarget.y * (0.2 + this.intensity * 6);

        // Subtle breathing animation
        const time = Date.now() * 0.001;
        this.head.scale.setScalar(1 + Math.sin(time * 2) * (0.02 + this.intensity));
        this.head.rotation.z = Math.sin(time * 0.5) * 0.03;

        this.renderer.render(this.scene, this.camera);
        requestAnimationFrame(() => this.animate());
    }

    handleResize() {
        if (!this.canvas || !this.camera || !this.renderer) return;
        
        const width = this.canvas.clientWidth;
        const height = this.canvas.clientHeight;
        this.renderer.setSize(width, height, false);
        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
    }

    setEyeTarget(x, y, z) {
        this.eyeTarget.set(x, y, z);
    }

    startSpeechAnimation(audio) {
        if (!audio || !this.head) return;

        let animationId;
        const analyser = this.createAudioAnalyser(audio);
        
        const animateHead = () => {
            if (!analyser || audio.ended || audio.paused) {
                // Return to neutral
                this.head.scale.setScalar(1);
                this.head.rotation.set(0, 0, 0);
                return;
            }

            const dataArray = new Uint8Array(analyser.frequencyBinCount);
            analyser.getByteFrequencyData(dataArray);
            
            const overall = dataArray.reduce((sum, val) => sum + val, 0) / dataArray.length;
            const intensity = overall / 255;

            // Head movement based on audio
            this.head.scale.setScalar(1 + intensity * 0.15);
            
            // Subtle rotation
            this.head.rotation.y = Math.sin(Date.now() * 0.001) * intensity * 0.1;
            this.head.rotation.x = Math.cos(Date.now() * 0.0008) * intensity * 0.05;

            animationId = requestAnimationFrame(animateHead);
        };

        animateHead();

        audio.addEventListener('ended', () => {
            if (animationId) {
                cancelAnimationFrame(animationId);
            }
        });
    }

    createAudioAnalyser(audio) {
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const source = audioContext.createMediaElementSource(audio);
            const analyser = audioContext.createAnalyser();
            
            analyser.fftSize = 256;
            source.connect(analyser);
            analyser.connect(audioContext.destination);
            
            return analyser;
        } catch (error) {
            console.error('Failed to create audio analyser:', error);
            return null;
        }
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.mcpHubApp = new MCPHubApp();
});

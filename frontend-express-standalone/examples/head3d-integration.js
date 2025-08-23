// Three.js 3D Head Integration Example
// Повний приклад інтеграції 3D голови з анімацією для будь-якого проекту

import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';

// ==============================================
// 3D HEAD CLASS
// ==============================================

export class Head3DManager {
  constructor(canvas, options = {}) {
    this.canvas = canvas;
    this.options = {
      modelUrl: '/models/DamagedHelmet.glb',
      eyeTracking: true,
      audioReactive: true,
      breathing: true,
      ...options
    };
    
    this.scene = null;
    this.camera = null;
    this.renderer = null;
    this.head = null;
    this.mixer = null;
    
    this.eyeTarget = new THREE.Vector3(0, 0, 0);
    this.currentEyeTarget = new THREE.Vector3(0, 0, 0);
    
    this.audioContext = null;
    this.analyser = null;
    this.animationId = null;
    
    this.init();
  }

  // Ініціалізація Three.js сцени
  init() {
    // Scene
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x000000);

    // Camera
    this.camera = new THREE.PerspectiveCamera(35, 1, 0.1, 100);
    this.camera.position.set(0, 0.4, 4);

    // Renderer
    this.renderer = new THREE.WebGLRenderer({
      canvas: this.canvas,
      antialias: true,
    });

    // Lighting
    this.setupLighting();

    // Load model
    this.loadModel();

    // Start animation loop
    this.animate();

    // Handle resize
    this.handleResize();
  }

  // Налаштування освітлення
  setupLighting() {
    // Ambient light
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    this.scene.add(ambientLight);

    // Directional light
    const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
    dirLight.position.set(2, 4, 3);
    this.scene.add(dirLight);

    // Fill light (зелений для hacker теми)
    const fillLight = new THREE.PointLight(0x22ff88, 0.4);
    fillLight.position.set(-3, 1, 2);
    this.scene.add(fillLight);
  }

  // Завантаження 3D моделі
  async loadModel() {
    const loader = new GLTFLoader();
    
    try {
      const gltf = await new Promise((resolve, reject) => {
        loader.load(this.options.modelUrl, resolve, undefined, reject);
      });

      // Create head group
      this.head = new THREE.Group();
      this.scene.add(this.head);

      // Process model
      const model = gltf.scene;
      
      // Center and scale model
      const box = new THREE.Box3().setFromObject(model);
      const size = new THREE.Vector3();
      const center = new THREE.Vector3();
      
      box.getSize(size);
      box.getCenter(center);
      
      model.position.sub(center);
      
      const maxDim = Math.max(size.x, size.y, size.z);
      const scale = 2.0 / (maxDim || 1);
      model.scale.setScalar(scale);
      model.rotation.y = Math.PI;
      
      this.head.add(model);

      // Setup animations if available
      if (gltf.animations && gltf.animations.length > 0) {
        this.mixer = new THREE.AnimationMixer(model);
        gltf.animations.forEach(clip => {
          this.mixer.clipAction(clip).play();
        });
      }

      console.log('✅ 3D Head model loaded successfully');
      
      // Trigger loaded event
      this.canvas.dispatchEvent(new CustomEvent('modelLoaded', { 
        detail: { model: this.head } 
      }));
      
    } catch (error) {
      console.error('❌ Failed to load 3D model:', error);
      
      // Create fallback wireframe
      this.createFallbackModel();
    }
  }

  // Створення резервної моделі (wireframe)
  createFallbackModel() {
    const geometry = new THREE.IcosahedronGeometry(0.8, 2);
    const material = new THREE.MeshBasicMaterial({
      color: 0x00ff66,
      wireframe: true,
    });
    
    this.head = new THREE.Mesh(geometry, material);
    this.scene.add(this.head);
    
    console.log('🔄 Using fallback wireframe model');
  }

  // Eye tracking
  setEyeTarget(target) {
    if (!this.options.eyeTracking || !this.head) return;
    
    switch (target) {
      case 'center':
        this.eyeTarget.set(0, 0, 0);
        break;
      case 'input':
        this.eyeTarget.set(-0.3, -0.2, 0);
        break;
      case 'message':
        this.eyeTarget.set(0.3, 0.1, 0);
        break;
      default:
        if (typeof target === 'object') {
          this.eyeTarget.copy(target);
        }
    }
  }

  // Аудіо-реактивна анімація
  setupAudioAnalysis(audioElement) {
    if (!this.options.audioReactive) return;
    
    try {
      this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
      this.analyser = this.audioContext.createAnalyser();
      this.analyser.fftSize = 256;
      
      const source = this.audioContext.createMediaElementSource(audioElement);
      source.connect(this.analyser);
      this.analyser.connect(this.audioContext.destination);
      
      console.log('🎵 Audio analysis setup complete');
    } catch (error) {
      console.warn('⚠️ Audio analysis setup failed:', error);
    }
  }

  // Анімація під час TTS
  animateForTTS(audioElement) {
    if (!this.head || !audioElement) return;
    
    this.setupAudioAnalysis(audioElement);
    
    const animate = () => {
      if (!this.analyser || audioElement.paused || audioElement.ended) {
        // Повернення до нейтральної позиції
        if (this.head) {
          this.head.scale.setScalar(1);
          this.head.rotation.set(0, 0, 0);
          
          // Reset jaw and eyes if they exist
          this.resetFacialFeatures();
        }
        return;
      }
      
      const dataArray = new Uint8Array(this.analyser.frequencyBinCount);
      this.analyser.getByteFrequencyData(dataArray);
      
      // Calculate intensity
      const overall = dataArray.reduce((a, b) => a + b) / dataArray.length;
      const lowFreq = dataArray.slice(0, 32).reduce((a, b) => a + b) / 32;
      const midFreq = dataArray.slice(32, 128).reduce((a, b) => a + b) / 96;
      const highFreq = dataArray.slice(128).reduce((a, b) => a + b) / 128;
      
      const intensity = overall / 255;
      
      // Head scaling and movement
      this.head.scale.setScalar(1 + intensity * 0.15);
      
      // Find facial features
      const jaw = this.findMeshByName(['jaw', 'mouth']);
      const eyes = this.findMeshByName(['eye', 'eyes']);
      
      // Jaw movement (speech simulation)
      if (jaw) {
        const jawIntensity = midFreq / 255;
        jaw.rotation.x = -jawIntensity * 0.3;
      }
      
      // Eye blinking
      if (eyes && Math.random() < 0.02) {
        const blinkIntensity = highFreq / 255;
        eyes.scale.y = Math.max(0.1, 1 - blinkIntensity * 0.8);
        setTimeout(() => {
          if (eyes) eyes.scale.y = 1;
        }, 100);
      }
      
      // Subtle head rotation
      this.head.rotation.y = Math.sin(Date.now() * 0.001) * intensity * 0.1;
      this.head.rotation.x = Math.cos(Date.now() * 0.0008) * intensity * 0.05;
      
      requestAnimationFrame(animate);
    };
    
    audioElement.addEventListener('play', animate);
  }

  // Знаходження mesh за іменем
  findMeshByName(names) {
    if (!this.head) return null;
    
    let found = null;
    this.head.traverse((child) => {
      if (child.isMesh && names.some(name => 
        child.name.toLowerCase().includes(name.toLowerCase())
      )) {
        found = child;
      }
    });
    
    return found;
  }

  // Скидання рис обличчя
  resetFacialFeatures() {
    const jaw = this.findMeshByName(['jaw', 'mouth']);
    const eyes = this.findMeshByName(['eye', 'eyes']);
    
    if (jaw) jaw.rotation.x = 0;
    if (eyes) eyes.scale.y = 1;
  }

  // Основний цикл анімації
  animate() {
    if (!this.scene || !this.camera || !this.renderer) return;
    
    // Update mixer
    if (this.mixer) {
      this.mixer.update(0.016); // ~60fps
    }
    
    // Eye tracking
    if (this.head && this.options.eyeTracking) {
      this.currentEyeTarget.lerp(this.eyeTarget, 0.05);
      this.head.rotation.y = this.currentEyeTarget.x * 0.3;
      this.head.rotation.x = -this.currentEyeTarget.y * 0.2;
    }
    
    // Breathing animation
    if (this.head && this.options.breathing) {
      const time = Date.now() * 0.001;
      const breathScale = 1 + Math.sin(time * 2) * 0.02;
      this.head.scale.setScalar(breathScale);
      this.head.rotation.z = Math.sin(time * 0.5) * 0.03;
    }
    
    this.renderer.render(this.scene, this.camera);
    this.animationId = requestAnimationFrame(() => this.animate());
  }

  // Обробка зміни розміру
  handleResize() {
    const resize = () => {
      if (!this.canvas || !this.renderer || !this.camera) return;
      
      const width = this.canvas.clientWidth;
      const height = this.canvas.clientHeight;
      
      this.renderer.setSize(width, height, false);
      this.camera.aspect = width / height;
      this.camera.updateProjectionMatrix();
    };
    
    window.addEventListener('resize', resize);
    resize(); // Initial resize
  }

  // Очищення ресурсів
  dispose() {
    if (this.animationId) {
      cancelAnimationFrame(this.animationId);
    }
    
    if (this.renderer) {
      this.renderer.dispose();
    }
    
    if (this.audioContext) {
      this.audioContext.close();
    }
    
    // Dispose geometries and materials
    this.scene?.traverse((child) => {
      if (child.geometry) child.geometry.dispose();
      if (child.material) {
        if (Array.isArray(child.material)) {
          child.material.forEach(material => material.dispose());
        } else {
          child.material.dispose();
        }
      }
    });
  }
}

// ==============================================
// UTILITY FUNCTIONS
// ==============================================

// Простий wrapper для швидкого використання
export function createHead3D(canvasSelector, options = {}) {
  const canvas = typeof canvasSelector === 'string' 
    ? document.querySelector(canvasSelector) 
    : canvasSelector;
    
  if (!canvas) {
    throw new Error('Canvas element not found');
  }
  
  return new Head3DManager(canvas, options);
}

// Функція для тестування TTS анімації
export async function testTTSAnimation(head3d, text = "Привіт, це тест") {
  try {
    // Створення тестового аудіо
    const audioUrl = await generateTTSAudio(text);
    const audio = new Audio(audioUrl);
    
    // Запуск анімації
    head3d.animateForTTS(audio);
    
    // Відтворення аудіо
    await audio.play();
    
    console.log('🎭 TTS animation test completed');
  } catch (error) {
    console.error('❌ TTS animation test failed:', error);
  }
}

// Заглушка для TTS (замініть на реальний API виклик)
async function generateTTSAudio(text) {
  // Тут має бути виклик до вашого TTS API
  // Наприклад: return await fetch('/api/tts', { ... })
  
  // Для демо повертаємо пустий audio URL
  return 'data:audio/wav;base64,';
}

// ==============================================
// EXAMPLE USAGE
// ==============================================

/*
// HTML
<canvas id="head3d-canvas" width="400" height="400"></canvas>

// JavaScript
import { createHead3D, testTTSAnimation } from './head3d-integration.js';

// Створення 3D голови
const head3d = createHead3D('#head3d-canvas', {
  modelUrl: '/models/DamagedHelmet.glb',
  eyeTracking: true,
  audioReactive: true,
  breathing: true
});

// Eye tracking
head3d.setEyeTarget('input'); // або 'center', 'message'

// Тест TTS анімації
testTTSAnimation(head3d, "Привіт, це тест української мови");

// Очищення при відході зі сторінки
window.addEventListener('beforeunload', () => {
  head3d.dispose();
});
*/

export default Head3DManager;

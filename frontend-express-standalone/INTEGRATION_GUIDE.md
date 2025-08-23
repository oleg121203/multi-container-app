# 🚀 MCP Hub - Універсальний гід інтеграції

## 📋 Огляд системи

MCP Hub - це комплексна система орхестрації AI з українською мовою, що включає:
- 10 MCP серверів (порти 3001-3009)  
- 3D візуалізація голови з анімацією
- Українське розпізнавання мови та TTS
- Автоматизація macOS через AppleScript
- Браузерна автоматизація через Playwright
- Frontend інтерфейси (React + Express)

## 🏗️ Архітектура системи

```
┌─────────────────────────────────────────────────────────────┐
│                    MCP Hub Ecosystem                        │
├─────────────────────────────────────────────────────────────┤
│ Frontend Interfaces:                                        │
│ ├── frontend-hacker/ (React + Vite, port 8080)            │
│ ├── frontend-express-standalone/ (Express, port 3010)      │
│ └── standalone/head-3d/ (Vanilla JS, port 8099)           │
├─────────────────────────────────────────────────────────────┤
│ MCP Servers:                                               │
│ ├── 3001: Playwright MCP (browser automation)             │
│ ├── 3002: Atlas Coordinator (Ukrainian AI)                │
│ ├── 3003: MCP Orchestrator (job management)               │
│ ├── 3004: Atlas 2 Visual (visual context)                 │
│ ├── 3005: Context MCP (context management)                │
│ ├── 3006: macOS Automator MCP (AppleScript/JXA)           │
│ ├── 3007: Streaming TTS (text-to-speech)                  │
│ ├── 3008: Linux Automator Bridge                          │
│ └── 3009: Atlas Coordination Controller                   │
├─────────────────────────────────────────────────────────────┤
│ Core Services:                                             │
│ ├── Ukrainian Language Processing                          │
│ ├── 3D Head Animation (Three.js)                          │
│ ├── Audio Analysis & TTS                                  │
│ └── System Automation                                      │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Швидкий старт

### 1. Встановлення залежностей
```bash
cd /path/to/mcp-hub
npm ci  # НІКОЛИ НЕ СКАСОВУЙТЕ - 40 секунд
```

### 2. Збірка frontend-hacker
```bash
cd frontend-hacker
npm ci && npm run build  # 11 секунд
cd ..
```

### 3. Запуск системи
```bash
./start.sh  # Запуск всіх серверів - 19 секунд
```

### 4. Перевірка статусу
```bash
./status.sh  # Перевірка всіх компонентів
```

## 🔧 Інтеграція нових компонентів

### A. Додавання нового MCP сервера

1. **Створіть сервер файл:**
```javascript
// server/mcp-servers/my-new-server.js
import express from 'express';
import cors from 'cors';

const app = express();
const PORT = process.env.PORT || 3010;  // Наступний вільний порт

app.use(cors());
app.use(express.json());

// Health endpoint (обов'язковий)
app.get('/health', (req, res) => {
  res.json({
    ok: true,
    service: 'my-new-server',
    tools: ['tool1', 'tool2'],  // Список доступних інструментів
    time: new Date().toISOString()
  });
});

// Ваші endpoint-и тут
app.post('/api/my-action', (req, res) => {
  // Логіка сервера
  res.json({ result: 'success' });
});

app.listen(PORT, () => {
  console.log(`[my-new-server] Running on port ${PORT}`);
});

export default app;
```

2. **Додайте до ecosystem.config.js:**
```javascript
// config/ecosystem.config.js
{
  name: "my-new-server",
  script: "server/mcp-servers/my-new-server.js",
  env: {
    PORT: 3010,
    NODE_ENV: "production"
  }
}
```

3. **Оновіть start.sh:**
```bash
# Додайте до start.sh
echo "🚀 Starting My New Server..."
node server/mcp-servers/my-new-server.js &
echo $! > logs/my-new-server.pid
```

### B. Додавання нового Frontend

1. **Створіть папку:**
```bash
mkdir frontend-my-app
cd frontend-my-app
```

2. **Базова структура Express:**
```javascript
// app.js
import express from 'express';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT || 3011;

app.use(express.static('public'));
app.use(express.json());

// API для зв'язку з MCP серверами
app.get('/api/health', async (req, res) => {
  try {
    // Перевірка MCP серверів
    const mcpServers = [
      'http://localhost:3001/health',
      'http://localhost:3002/health',
      // ... інші сервери
    ];
    
    const results = await Promise.allSettled(
      mcpServers.map(url => fetch(url).then(r => r.json()))
    );
    
    res.json({ mcp_servers: results });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.listen(PORT, () => {
  console.log(`Frontend running on http://localhost:${PORT}`);
});
```

### C. Інтеграція з українською мовою

```javascript
// Приклад використання Atlas Coordinator
async function processUkrainianCommand(message) {
  try {
    const response = await fetch('http://localhost:3002/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: message,  // "відкрий мені програму мюсік"
        history: []
      })
    });
    
    const result = await response.json();
    
    if (result.needsOrchestration) {
      // Команда потребує виконання
      console.log('Action type:', result.type);  // "open_app"
      console.log('Confidence:', result.confidence);
      console.log('Response:', result.response);
      
      // Передайте до orchestrator для виконання
      await executeCommand(result);
    }
    
    return result;
  } catch (error) {
    console.error('Ukrainian processing error:', error);
  }
}
```

### D. Додавання 3D компонентів

```javascript
// Інтеграція з Head3D
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';

class Head3DIntegration {
  constructor(canvas) {
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(35, 1, 0.1, 100);
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
    
    this.loadModel('/models/DamagedHelmet.glb');
  }
  
  async loadModel(url) {
    const loader = new GLTFLoader();
    try {
      const gltf = await new Promise((resolve, reject) => {
        loader.load(url, resolve, undefined, reject);
      });
      
      this.head = gltf.scene;
      this.scene.add(this.head);
      console.log('3D Head model loaded successfully');
    } catch (error) {
      console.error('Failed to load 3D model:', error);
    }
  }
  
  // Анімація під час TTS
  animateForTTS(audioElement) {
    const audioContext = new AudioContext();
    const analyser = audioContext.createAnalyser();
    const source = audioContext.createMediaElementSource(audioElement);
    
    source.connect(analyser);
    analyser.connect(audioContext.destination);
    
    const animate = () => {
      const dataArray = new Uint8Array(analyser.frequencyBinCount);
      analyser.getByteFrequencyData(dataArray);
      
      const intensity = dataArray.reduce((a, b) => a + b) / dataArray.length / 255;
      
      if (this.head) {
        this.head.scale.setScalar(1 + intensity * 0.15);
        this.head.rotation.y = Math.sin(Date.now() * 0.001) * intensity * 0.1;
      }
      
      if (!audioElement.paused && !audioElement.ended) {
        requestAnimationFrame(animate);
      }
    };
    
    audioElement.addEventListener('play', animate);
  }
}
```

## 🔌 API Endpoints

### Основні MCP сервери:

| Сервер | Порт | Health Check | Основна функція |
|--------|------|-------------|----------------|
| Playwright MCP | 3001 | `/health` | Браузерна автоматизація |
| Atlas Coordinator | 3002 | `/health` | Українська обробка мови |
| MCP Orchestrator | 3003 | `/health` | Управління завданнями |
| Atlas 2 Visual | 3004 | `/health` | Візуальний контекст |
| Context MCP | 3005 | `/health` | Управління контекстом |
| macOS Automator | 3006 | `/health` | AppleScript автоматизація |
| Streaming TTS | 3007 | `/health` | Потоковий TTS |
| Linux Automator | 3008 | `/health` | Linux автоматизація |
| Atlas Controller | 3009 | `/health` | Контроль координації |

### Ключові API виклики:

```javascript
// Ukrainian language processing
POST http://localhost:3002/chat
{
  "message": "відкрий мені програму мюсік",
  "history": []
}

// Browser automation
POST http://localhost:3001/navigate
{
  "url": "https://example.com"
}

// Job creation
POST http://localhost:3003/jobs/start
{
  "message": "test task",
  "autoFillDefaults": true
}

// TTS streaming
POST http://localhost:3007/tts
{
  "text": "Привіт, це тест",
  "voice": "uk_female"
}

// macOS automation
POST http://localhost:3006/execute
{
  "script": "tell application \"Music\" to play",
  "type": "applescript"
}
```

## 🌐 Frontend інтеграція

### React компоненти (frontend-hacker):
```jsx
import { Head3D } from './components/Head3D';
import { HackerChat } from './components/HackerChat';

function App() {
  return (
    <div className="app">
      <Head3D eyeTarget="center" />
      <HackerChat />
    </div>
  );
}
```

### Express інтеграція (цей проект):
```javascript
// Подивіться app.js в цій папці для повного прикладу
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.post('/api/chat', async (req, res) => {
  const { message } = req.body;
  
  // Передача до Atlas Coordinator
  const response = await fetch('http://localhost:3002/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, history: [] })
  });
  
  res.json(await response.json());
});
```

## 🎯 Тестування інтеграції

### 1. Перевірка MCP серверів:
```bash
# Тест всіх health endpoints
for port in 3001 3002 3003 3004 3005 3006 3007 3008 3009; do
  echo "Testing port $port..."
  curl -s http://localhost:$port/health | jq .
done
```

### 2. Тест української мови:
```bash
curl -X POST http://localhost:3002/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "відкрий мені програму мюсік", "history": []}'
```

### 3. Тест 3D моделі:
```bash
curl -I http://localhost:8099/assets/models/robot-head/DamagedHelmet.glb
```

### 4. Тест браузерної автоматизації:
```bash
curl -X POST http://localhost:3001/navigate \
  -H "Content-Type: application/json" \
  -d '{"url": "https://google.com"}'
```

## 🔧 Налаштування середовища

### Основні змінні .env:
```bash
# API Keys
GEMINI_API_KEY=your_gemini_key
OPENAI_API_KEY=your_openai_key

# Ports configuration
PLAYWRIGHT_MCP_PORT=3001
ATLAS_COORDINATOR_PORT=3002
MCP_ORCHESTRATOR_PORT=3003
HEAD_3D_PORT=8099
FRONTEND_HACKER_PORT=8080

# TTS Configuration  
TTS_VOICE=uk_female
TTS_RATE=1.0
TTS_VOLUME=0.8

# Ukrainian language settings
DEFAULT_LANGUAGE=uk
ENABLE_UKRAINIAN_TTS=true
UKRAINIAN_MODEL_PATH=./models/ukrainian
```

## 📝 Логування та діагностика

### Перевірка логів:
```bash
# Основні логи системи
tail -f logs/*.log

# Конкретний сервер
tail -f logs/atlas-coordinator.log
tail -f logs/playwright-mcp.log
tail -f logs/macos-automator-mcp.log
```

### Діагностика проблем:
```bash
# Перевірка портів
lsof -i :3001-3010

# Статус процесів
ps aux | grep node

# Перевірка мережі
netstat -an | grep LISTEN | grep 300
```

## 🚨 Найчастіші проблеми

### 1. Порти зайняті:
```bash
# Знайти процес на порту
lsof -ti:3001
# Вбити процес
kill -9 $(lsof -ti:3001)
```

### 2. Модель голови не завантажується:
```bash
# Перевірити файл моделі
ls -la frontend-hacker/public/models/robot-head/
# Перевірити доступ
curl -I http://localhost:8099/assets/models/robot-head/DamagedHelmet.glb
```

### 3. Українська мова не працює:
```bash
# Перевірити Atlas Coordinator
curl http://localhost:3002/health
# Тест обробки
curl -X POST http://localhost:3002/chat -d '{"message":"тест","history":[]}'
```

## 📚 Додаткові ресурси

- **Документація MCP**: [docs/](../docs/)
- **Приклади інтеграції**: [examples/](./examples/)
- **Конфігурація портів**: [docs/PORT_CONFIGURATION.md](../docs/PORT_CONFIGURATION.md)
- **Налаштування TTS**: [docs/TTS_V2_SOLUTION.md](../docs/TTS_V2_SOLUTION.md)
- **macOS автоматизація**: [docs/MACOS_AUTOMATOR_INTEGRATION.md](../docs/MACOS_AUTOMATOR_INTEGRATION.md)

## 🎉 Готові приклади

Цей проект (frontend-express-standalone) є повним прикладом інтеграції з:
- ✅ Express.js сервером
- ✅ 3D анімацією голови
- ✅ Українською мовною підтримкою  
- ✅ Інтеграцією з усіма MCP серверами
- ✅ Готовими API endpoints
- ✅ Демо інтерфейсом

Запустіть `npm start` в цій папці для демонстрації!

---
**Підтримка**: Для питань та проблем створіть issue в репозиторії або перевірте логи системи.

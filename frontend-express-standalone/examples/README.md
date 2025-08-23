# 📚 MCP Hub - Приклади інтеграції

Ця папка містить готові приклади для інтеграції з екосистемою MCP Hub.

## 📁 Файли

### 🚀 `mcp-integration-example.js`
Повний Express.js сервер з усіма API endpoints для роботи з MCP Hub:
- ✅ Українська обробка мови
- ✅ Браузерна автоматизація  
- ✅ macOS автоматизація
- ✅ Text-to-Speech
- ✅ Управління завданнями
- ✅ Health checks
- ✅ Демо endpoints

**Використання:**
```bash
node mcp-integration-example.js
# Відкрийте http://localhost:3011
```

### ⚛️ `react-mcp-hook.js`
React Hook (`useMCPHub`) для інтеграції з усіма MCP серверами:
- ✅ Автоматичні health checks
- ✅ Українські команди
- ✅ Браузерна автоматизація
- ✅ TTS генерація
- ✅ macOS скрипти
- ✅ Управління завданнями

**Використання:**
```jsx
import { useMCPHub, MCPHubDemo } from './react-mcp-hook.js';

function App() {
  const { processUkrainian, browserAction, generateTTS } = useMCPHub();
  
  return <MCPHubDemo />;
}
```

### 🎭 `head3d-integration.js`
Three.js клас для 3D анімації голови:
- ✅ Завантаження GLB моделей
- ✅ Eye tracking
- ✅ Аудіо-реактивна анімація
- ✅ TTS синхронізація
- ✅ Fallback wireframe
- ✅ Breathing анімація

**Використання:**
```javascript
import { createHead3D } from './head3d-integration.js';

const head3d = createHead3D('#canvas', {
  modelUrl: '/models/DamagedHelmet.glb',
  eyeTracking: true,
  audioReactive: true
});

head3d.setEyeTarget('input');
```

## 🔧 Швидкий старт

### 1. Express Integration
```bash
# Скопіюйте mcp-integration-example.js у ваш проект
cp mcp-integration-example.js your-project/server.js

# Встановіть залежності
npm install express cors node-fetch

# Запустіть
node server.js
```

### 2. React Integration
```bash
# Скопіюйте react-mcp-hook.js у ваш React проект
cp react-mcp-hook.js src/hooks/useMCPHub.js

# Використовуйте у компонентах
import { useMCPHub } from './hooks/useMCPHub';
```

### 3. 3D Head Integration
```bash
# Скопіюйте head3d-integration.js
cp head3d-integration.js src/components/Head3D.js

# Встановіть Three.js
npm install three

# Додайте canvas в HTML
<canvas id="head3d-canvas"></canvas>
```

## 🌐 API Endpoints

### Основні MCP сервери:
- `3001` - Playwright MCP (браузер)
- `3002` - Atlas Coordinator (українська)
- `3003` - MCP Orchestrator (завдання)
- `3004` - Atlas 2 Visual (візуальний контекст)
- `3005` - Context MCP (контекст)
- `3006` - macOS Automator (AppleScript)
- `3007` - Streaming TTS (мова)
- `3008` - Linux Automator (Linux)
- `3009` - Atlas Controller (координація)

### Приклади API викликів:

```javascript
// Українська команда
POST http://localhost:3002/chat
{
  "message": "відкрий мені програму мюсік",
  "history": []
}

// Браузерна навігація  
POST http://localhost:3001/navigate
{
  "url": "https://google.com"
}

// TTS генерація
POST http://localhost:3007/tts
{
  "text": "Привіт світ",
  "voice": "uk_female"
}

// macOS автоматизація
POST http://localhost:3006/execute
{
  "script": "tell application \"Music\" to play",
  "type": "applescript"
}
```

## 🎯 Демо команди

### Тест української мови:
```bash
curl -X POST http://localhost:3002/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "відкрий мені програму мюсік", "history": []}'
```

### Тест браузера:
```bash
curl -X POST http://localhost:3001/navigate \
  -H "Content-Type: application/json" \
  -d '{"url": "https://google.com"}'
```

### Тест 3D моделі:
```bash
curl -I http://localhost:8099/assets/models/robot-head/DamagedHelmet.glb
```

## 🔍 Діагностика

### Перевірка всіх серверів:
```bash
for port in 3001 3002 3003 3004 3005 3006 3007 3008 3009; do
  echo "Testing port $port..."
  curl -s http://localhost:$port/health | jq .
done
```

### Перевірка портів:
```bash
lsof -i :3001-3010
```

### Логи:
```bash
tail -f ../logs/*.log
```

## 📋 Чекліст інтеграції

- [ ] MCP Hub система запущена (`../start.sh`)
- [ ] Всі сервери онлайн (перевірте health endpoints)
- [ ] 3D модель доступна (`/models/DamagedHelmet.glb`)
- [ ] API ключі налаштовані (`.env`)
- [ ] Порти вільні (3001-3009)
- [ ] Three.js встановлено (для 3D)
- [ ] Express.js встановлено (для серверу)

## 🚨 Найчастіші проблеми

### CORS помилки:
```javascript
app.use(cors({
  origin: ['http://localhost:3000', 'http://localhost:8080'],
  credentials: true
}));
```

### Модель не завантажується:
```javascript
// Перевірте шлях до моделі
const modelUrl = '/models/DamagedHelmet.glb';
// Або абсолютний URL
const modelUrl = 'http://localhost:8099/assets/models/robot-head/DamagedHelmet.glb';
```

### MCP сервер недоступний:
```bash
# Перевірте чи запущена система
../status.sh

# Перевірте конкретний порт
curl http://localhost:3002/health
```

## 📖 Додаткова документація

- [Головний гід інтеграції](../INTEGRATION_GUIDE.md)
- [Конфігурація портів](../../docs/PORT_CONFIGURATION.md)  
- [TTS налаштування](../../docs/TTS_V2_SOLUTION.md)
- [macOS автоматизація](../../docs/MACOS_AUTOMATOR_INTEGRATION.md)

---
**Підтримка**: Перевірте логи системи або створіть issue в репозиторії для допомоги.

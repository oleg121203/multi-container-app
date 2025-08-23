# 🎭 MCP Hub - Express Frontend (Standalone)

Самостійний Express.js додаток з повною копією функціональності MCP Hub в одній папці. Включає в себе всі компоненти для створення власних інтерфейсів з інтеграцією до системи MCP Hub.

## ✨ Особливості

- 🎭 **3D анімація голови** - Three.js + GLB модель з аудіо-реактивністю
- 🇺🇦 **Українська мова** - Повна підтримка TTS + розпізнавання команд  
- 🤖 **MCP інтеграція** - Підключення до всіх 9 MCP серверів
- 🌐 **Express.js сервер** - Готовий backend з API endpoints
- 📱 **Responsive дизайн** - Адаптивний під різні екрани
- 🔧 **Готовий до деплою** - Всі файли в одній папці
- 📚 **Повна документація** - Приклади інтеграції та API
- 🧪 **Тестовий набір** - Автоматичні тести всіх компонентів

## 🚀 Швидкий старт

```bash
# Встановити залежності
npm install

# Запустити сервер
npm start

# Або в режимі розробки
npm run dev
```

Сервер запуститься на `http://localhost:3050`

## 📁 Структура проекту

```
frontend-express-standalone/
├── server.js              # Express сервер
├── package.json           # Залежності
├── models/                # 3D моделі
│   └── DamagedHelmet.glb  # Модель голови робота
├── assets/                # Статичні ресурси
├── public/                # Веб-інтерфейс
│   ├── index.html         # Головна сторінка
│   └── app.js            # JavaScript додаток
└── README.md             # Ця інструкція
```

## ✨ Особливості

### 🤖 3D Голова
- Завантажується модель `DamagedHelmet.glb` з локального файлу
- Eye tracking: реагує на активність чату
- Анімація під час TTS (Text-to-Speech)
- Зелений каркасний плейсхолдер під час завантаження

### 💬 Чат Система
- Три режими: Atlas, Grisha, Consulting
- Голосовий ввід (WebSpeech API)
- Безперервний режим розпізнавання мови
- TTS підтримка (мок-реалізація)

### 🎨 Hacker-стиль інтерфейс
- Зелений неон на чорному фоні
- Шрифт JetBrains Mono
- Мінімалістичний дизайн без рамок
- Автоматичне приховування навігації

## 🔧 API Endpoints

Сервер надає наступні ендпоінти:

- `GET /api/health` - Статус сервера
- `POST /api/chat` - Надсилання повідомлень
- `POST /api/tts` - Генерація TTS (мок)
- `GET /config.js` - Конфігурація клієнта
- `GET /models/*` - 3D моделі
- `GET /assets/*` - Статичні ресурси

## 🔌 Інтеграція з основною системою MCP Hub

### Варіант 1: Proxy через основний сервер

У файлі `server/orchestrators/mcp-orchestrator.js` додайте проксі:

```javascript
// Проксі для standalone frontend
app.use('/standalone', express.static(path.join(__dirname, '../../frontend-express-standalone/public')));

app.get('/standalone/config.js', (req, res) => {
  res.type('application/javascript');
  res.send(`
    window.__CONFIG__ = {
      API_BASE_URL: 'http://localhost:3002/api',
      HEAD3D_ASSETS_URL: 'http://localhost:8099/assets',
      ENVIRONMENT: 'integrated'
    };
  `);
});
```

### Варіант 2: Окремий порт з CORS

Запустіть standalone сервер на порту 3050 та налаштуйте CORS для основної системи:

```javascript
// У основному сервері
app.use(cors({
  origin: ['http://localhost:3050', 'http://localhost:8080'],
  credentials: false
}));
```

### Варіант 3: Заміна frontend-hacker

1. Зупиніть основну систему: `./stop.sh`
2. Замініть вміст `frontend-hacker/` на цей проект
3. Оновіть `start.sh` для запуску Express замість Vite

## 🛠️ Налаштування

### Конфігурація сервера

Змініть порт у `server.js`:

```javascript
const PORT = process.env.PORT || 3050;
```

### Підключення до реального API

Оновіть ендпоінти у `server.js`:

```javascript
// Замість мок-відповідей
app.post('/api/chat', async (req, res) => {
  try {
    const response = await fetch('http://localhost:3002/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req.body)
    });
    const data = await response.json();
    res.json(data);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});
```

### Додавання нових моделей

1. Помістіть `.glb` файли у папку `models/`
2. Оновіть `loadModel()` у `public/app.js`
3. Додайте селектор моделей у `index.html`

## 🐛 Налагодження

### Проблеми з завантаженням моделі

1. Перевірте наявність файлу: `ls -la models/DamagedHelmet.glb`
2. Перевірте права доступу: `chmod 644 models/*`
3. Перевірте консоль браузера для помилок CORS/404

### Проблеми з голосовим вводом

1. Переконайтеся, що сайт відкрито через HTTPS або localhost
2. Дайте дозвіл на використання мікрофона
3. Перевірте підтримку WebSpeech API у браузері

### Проблеми з API

1. Перевірте статус сервера: `curl http://localhost:3050/api/health`
2. Перевірте логи сервера в терміналі
3. Перевірте Network tab у Developer Tools

## 📦 Деплой

### Docker (рекомендовано)

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
EXPOSE 3050
CMD ["npm", "start"]
```

### PM2

```bash
npm install -g pm2
pm2 start server.js --name "mcp-hub-standalone"
pm2 save
```

### Systemd

```ini
[Unit]
Description=MCP Hub Standalone Frontend
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/frontend-express-standalone
ExecStart=/usr/bin/node server.js
Restart=always

[Install]
WantedBy=multi-user.target
```

## 🔄 Оновлення з основної системи

Для синхронізації з основним проектом:

```bash
# Копіювати оновлені компоненти
cp ../frontend-hacker/src/components/HackerChat.tsx ./src/
cp ../frontend-hacker/src/components/Head3D.tsx ./src/

# Конвертувати React → Vanilla JS
# (потребує ручної адаптації)
```

## 📞 Підтримка

При виникненні проблем:

1. Перевірте логи сервера
2. Відкрийте Developer Tools у браузері
3. Перевірте конфігурацію у `/config.js`
4. Переконайтеся, що всі файли моделей присутні

## 🎯 Версія

- **Версія:** 1.0.0
- **Базований на:** MCP Hub Frontend Hacker v1.0.0
- **Останнє оновлення:** Серпень 2025
- **Сумісність:** Node.js 18+, сучасні браузери

---

*Цей проект є автономною копією MCP Hub Frontend і може працювати незалежно від основної системи.*

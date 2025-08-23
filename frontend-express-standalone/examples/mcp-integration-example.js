// Приклад інтеграції з MCP Hub для створення нового frontend
// Цей файл показує, як підключити новий інтерфейс до системи

import express from 'express';
import cors from 'cors';
import fetch from 'node-fetch';

const app = express();
const PORT = process.env.PORT || 3011;

app.use(cors());
app.use(express.json());
app.use(express.static('public'));

// ==============================================
// MCP HUB API INTEGRATION
// ==============================================

// Список всіх MCP серверів
const MCP_SERVERS = {
  playwright: 'http://localhost:3001',
  atlas: 'http://localhost:3002', 
  orchestrator: 'http://localhost:3003',
  atlas2: 'http://localhost:3004',
  context: 'http://localhost:3005',
  macos: 'http://localhost:3006',
  tts: 'http://localhost:3007',
  linux: 'http://localhost:3008',
  controller: 'http://localhost:3009'
};

// ==============================================
// UKRAINIAN LANGUAGE PROCESSING
// ==============================================

// Обробка української мови через Atlas Coordinator
app.post('/api/ukrainian', async (req, res) => {
  try {
    const { message, history = [] } = req.body;
    
    const response = await fetch(`${MCP_SERVERS.atlas}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, history })
    });
    
    const result = await response.json();
    
    if (result.needsOrchestration) {
      console.log(`🇺🇦 Ukrainian command detected: ${result.type}`);
      console.log(`📝 Confidence: ${result.confidence}`);
      console.log(`💬 Response: ${result.response}`);
      
      // Опційно: передати до orchestrator для виконання
      if (result.confidence > 0.8) {
        await executeCommand(result);
      }
    }
    
    res.json(result);
  } catch (error) {
    console.error('Ukrainian processing error:', error);
    res.status(500).json({ error: error.message });
  }
});

// ==============================================
// BROWSER AUTOMATION
// ==============================================

// Автоматизація браузера через Playwright MCP
app.post('/api/browser/:action', async (req, res) => {
  try {
    const { action } = req.params;
    const data = req.body;
    
    const response = await fetch(`${MCP_SERVERS.playwright}/${action}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    
    const result = await response.json();
    res.json(result);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// ==============================================
// MACOS AUTOMATION
// ==============================================

// Автоматизація macOS через AppleScript
app.post('/api/macos/execute', async (req, res) => {
  try {
    const { script, type = 'applescript' } = req.body;
    
    const response = await fetch(`${MCP_SERVERS.macos}/execute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ script, type })
    });
    
    const result = await response.json();
    res.json(result);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// ==============================================
// TEXT-TO-SPEECH
// ==============================================

// Потоковий TTS
app.post('/api/tts', async (req, res) => {
  try {
    const { text, voice = 'uk_female', rate = 1.0 } = req.body;
    
    const response = await fetch(`${MCP_SERVERS.tts}/tts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, voice, rate })
    });
    
    if (response.headers.get('content-type')?.includes('audio')) {
      // Streaming audio response
      res.set({
        'Content-Type': 'audio/wav',
        'Content-Disposition': 'inline; filename="tts.wav"'
      });
      response.body.pipe(res);
    } else {
      const result = await response.json();
      res.json(result);
    }
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// ==============================================
// JOB ORCHESTRATION
// ==============================================

// Створення нового завдання
app.post('/api/jobs/create', async (req, res) => {
  try {
    const { message, autoFillDefaults = true } = req.body;
    
    const response = await fetch(`${MCP_SERVERS.orchestrator}/jobs/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, autoFillDefaults })
    });
    
    const result = await response.json();
    res.json(result);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Отримання статусу завдання
app.get('/api/jobs/:jobId', async (req, res) => {
  try {
    const { jobId } = req.params;
    
    const response = await fetch(`${MCP_SERVERS.orchestrator}/jobs/${jobId}`);
    const result = await response.json();
    res.json(result);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// ==============================================
// HEALTH CHECKS
// ==============================================

// Перевірка статусу всіх MCP серверів
app.get('/api/health', async (req, res) => {
  try {
    const healthChecks = await Promise.allSettled(
      Object.entries(MCP_SERVERS).map(async ([name, url]) => {
        const response = await fetch(`${url}/health`, { 
          timeout: 5000 
        });
        const data = await response.json();
        return { name, url, status: 'ok', data };
      })
    );
    
    const results = healthChecks.map((check, index) => {
      const name = Object.keys(MCP_SERVERS)[index];
      if (check.status === 'fulfilled') {
        return check.value;
      } else {
        return { 
          name, 
          url: Object.values(MCP_SERVERS)[index], 
          status: 'error', 
          error: check.reason.message 
        };
      }
    });
    
    res.json({ servers: results });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// ==============================================
// HELPER FUNCTIONS
// ==============================================

// Виконання команди через orchestrator
async function executeCommand(command) {
  try {
    const response = await fetch(`${MCP_SERVERS.orchestrator}/execute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(command)
    });
    
    return await response.json();
  } catch (error) {
    console.error('Command execution error:', error);
    return { error: error.message };
  }
}

// ==============================================
// DEMO ENDPOINTS
// ==============================================

// Демо української команди
app.get('/demo/ukrainian', async (req, res) => {
  const testCommand = "відкрий мені програму мюсік";
  
  try {
    const response = await fetch(`${MCP_SERVERS.atlas}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        message: testCommand, 
        history: [] 
      })
    });
    
    const result = await response.json();
    res.json({
      demo: true,
      testCommand,
      result
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Демо браузерної автоматизації
app.get('/demo/browser', async (req, res) => {
  try {
    const response = await fetch(`${MCP_SERVERS.playwright}/navigate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: 'https://google.com' })
    });
    
    const result = await response.json();
    res.json({
      demo: true,
      action: 'navigate to google.com',
      result
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// ==============================================
// SERVER STARTUP
// ==============================================

app.get('/', (req, res) => {
  res.send(`
    <h1>🚀 MCP Hub Integration Example</h1>
    <h2>Available endpoints:</h2>
    <ul>
      <li><a href="/api/health">Health Check</a></li>
      <li><a href="/demo/ukrainian">Demo Ukrainian</a></li>
      <li><a href="/demo/browser">Demo Browser</a></li>
    </ul>
    
    <h2>API Documentation:</h2>
    <ul>
      <li>POST /api/ukrainian - Process Ukrainian commands</li>
      <li>POST /api/browser/:action - Browser automation</li>
      <li>POST /api/macos/execute - macOS automation</li>
      <li>POST /api/tts - Text-to-speech</li>
      <li>POST /api/jobs/create - Create job</li>
      <li>GET /api/jobs/:jobId - Get job status</li>
    </ul>
  `);
});

app.listen(PORT, () => {
  console.log(`🚀 MCP Hub Integration Example running on port ${PORT}`);
  console.log(`📖 Documentation: http://localhost:${PORT}`);
  console.log(`🔍 Health check: http://localhost:${PORT}/api/health`);
});

export default app;

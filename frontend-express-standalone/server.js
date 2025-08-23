import express from 'express';
import cors from 'cors';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT || 3050;

// Middleware
app.use(cors());
app.use(express.json({ limit: '50mb' }));
app.use(express.static(path.join(__dirname, 'public')));

// API Endpoints (мок-версії для демонстрації)
app.get('/api/health', (req, res) => {
  res.json({ 
    status: 'ok', 
    service: 'frontend-express-standalone',
    timestamp: new Date().toISOString() 
  });
});

// Chat API endpoint (мок)
app.post('/api/chat', (req, res) => {
  const { message, mode } = req.body;
  
  // Симуляція відповіді Atlas
  setTimeout(() => {
    res.json({
      id: Date.now().toString(),
      text: `Привіт! Ви написали: "${message}". Це мок-відповідь від ${mode || 'Atlas'} системи.`,
      timestamp: new Date().toISOString(),
      mode: mode || 'atlas-1'
    });
  }, 500 + Math.random() * 1000);
});

// TTS API endpoint (мок)
app.post('/api/tts', (req, res) => {
  const { text, voice } = req.body;
  
  // Симуляція генерації TTS
  res.json({
    success: true,
    message: 'TTS generated successfully',
    audioUrl: '/assets/demo-audio.wav', // мок-файл
    voice: voice || 'uk_female'
  });
});

// Serve models
app.use('/models', express.static(path.join(__dirname, 'models')));

// Serve assets
app.use('/assets', express.static(path.join(__dirname, 'assets')));

// Config endpoint
app.get('/config.js', (req, res) => {
  res.type('application/javascript');
  res.send(`
    window.__CONFIG__ = {
      API_BASE_URL: 'http://localhost:${PORT}/api',
      HEAD3D_ASSETS_URL: 'http://localhost:${PORT}/assets',
      ENVIRONMENT: 'standalone'
    };
  `);
});

// Catch-all для SPA
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.listen(PORT, () => {
  console.log(`🚀 Frontend Express Standalone Server running on http://localhost:${PORT}`);
  console.log(`📊 Health endpoint: http://localhost:${PORT}/api/health`);
  console.log(`🤖 3D Head model: http://localhost:${PORT}/models/DamagedHelmet.glb`);
  console.log(`⚙️  Config: http://localhost:${PORT}/config.js`);
});

import { test, expect } from '@playwright/test';

test.describe('ATLAS API Integration E2E Tests', () => {
  const baseURL = 'http://localhost:8000';

  test('should test voice API endpoints', async ({ request }) => {
    // Test TTS API
    const ttsResponse = await request.post('/api/tts', {
      data: {
        text: 'Hello from Playwright E2E test',
        voice: 'atlas',
        agent_id: 'atlas'
      }
    });
    
    expect(ttsResponse.status()).toBe(200);
    const ttsData = await ttsResponse.json();
    expect(ttsData.status).toBe('success');
    expect(ttsData.audio_url).toBeTruthy();
  });

  test('should test STT API endpoint', async ({ request }) => {
    // Create a simple audio blob for testing
    // Note: In a real test, you'd use actual audio data
    const audioData = new Uint8Array([0, 1, 2, 3, 4, 5]); // Dummy audio data
    
    const formData = new FormData();
    formData.append('audio', new Blob([audioData], { type: 'audio/wav' }), 'test.wav');
    
    const sttResponse = await request.post('/api/stt', {
      multipart: {
        audio: {
          name: 'test.wav',
          mimeType: 'audio/wav',
          buffer: Buffer.from(audioData)
        }
      }
    });
    
    expect(sttResponse.status()).toBe(200);
    const sttData = await sttResponse.json();
    expect(sttData.status).toBe('success');
    expect(sttData.transcript).toBeTruthy();
  });

  test('should test agents API', async ({ request }) => {
    const response = await request.get('/api/agents');
    expect(response.status()).toBe(200);
    
    const data = await response.json();
    expect(data.agents).toBeDefined();
    expect(Array.isArray(data.agents)).toBe(true);
    expect(data.agents.length).toBeGreaterThan(0);
    
    // Check agent structure
    const firstAgent = data.agents[0];
    expect(firstAgent.id).toBeTruthy();
    expect(firstAgent.name).toBeTruthy();
    expect(firstAgent.status).toBeTruthy();
  });

  test('should test team formation API', async ({ request }) => {
    const teamRequest = {
      description: 'Playwright E2E test team',
      constraints: {
        priority: 'normal'
      }
    };
    
    const response = await request.post('/api/teams/form', {
      data: teamRequest
    });
    
    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(data.status).toBe('success');
    expect(data.team).toBeDefined();
    expect(data.team.members).toBeDefined();
  });

  test('should test system status API', async ({ request }) => {
    const response = await request.get('/api/system/status');
    expect(response.status()).toBe(200);
    
    const data = await response.json();
    expect(typeof data).toBe('object');
    expect(Object.keys(data).length).toBeGreaterThan(0);
  });

  test('should test metrics API', async ({ request }) => {
    const response = await request.get('/api/metrics');
    expect(response.status()).toBe(200);
    
    const data = await response.json();
    expect(data.active_agents).toBeDefined();
    expect(data.teams_formed).toBeDefined();
    expect(data.tasks_completed).toBeDefined();
    expect(typeof data.active_agents).toBe('number');
  });

  test('should test voices API', async ({ request }) => {
    const response = await request.get('/api/voices');
    expect(response.status()).toBe(200);
    
    const data = await response.json();
    expect(data.voices).toBeDefined();
    expect(Array.isArray(data.voices)).toBe(true);
    expect(data.voices.length).toBeGreaterThan(0);
    
    // Check voice structure
    const firstVoice = data.voices[0];
    expect(firstVoice.id).toBeTruthy();
    expect(firstVoice.name).toBeTruthy();
    expect(firstVoice.language).toBeTruthy();
  });

  test('should test chat API', async ({ request }) => {
    const chatMessage = {
      type: 'chat',
      message: 'Hello from Playwright E2E test',
      timestamp: new Date().toISOString()
    };
    
    const response = await request.post('/api/chat', {
      data: chatMessage
    });
    
    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(data.status).toBe('success');
    expect(data.response).toBeTruthy();
  });

  test('should test health endpoint', async ({ request }) => {
    const response = await request.get('/health');
    expect(response.status()).toBe(200);
    
    const data = await response.json();
    expect(data.status).toBe('healthy');
    expect(data.service).toBeTruthy();
    expect(data.api_version).toBeTruthy();
  });

  test('should test analytics endpoint', async ({ request }) => {
    const analyticsData = {
      pageViews: 1,
      interactions: 5,
      sessionStart: Date.now(),
      features: {
        voiceCommands: 2,
        teamsFormed: 1,
        agentInteractions: 3
      }
    };
    
    const response = await request.post('/api/analytics', {
      data: analyticsData
    });
    
    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(data.status).toBe('success');
  });

  test('should test diagnostics endpoint', async ({ request }) => {
    const response = await request.get('/api/diagnostics');
    expect(response.status()).toBe(200);
    
    const data = await response.json();
    expect(data.timestamp).toBeTruthy();
    expect(data.system).toBeDefined();
    expect(data.services).toBeDefined();
    expect(data.performance).toBeDefined();
  });
});
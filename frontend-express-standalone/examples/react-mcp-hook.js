// React Hook приклад для інтеграції з MCP Hub
// Використовуйте цей hook у ваших React компонентах

import { useState, useEffect, useCallback } from 'react';

// ==============================================
// MCP HUB REACT HOOK
// ==============================================

export const useMCPHub = () => {
  const [servers, setServers] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // MCP Server URLs
  const MCP_ENDPOINTS = {
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

  // Перевірка здоров'я всіх серверів
  const checkHealth = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const healthChecks = await Promise.allSettled(
        Object.entries(MCP_ENDPOINTS).map(async ([name, url]) => {
          const response = await fetch(`${url}/health`);
          const data = await response.json();
          return { name, status: 'ok', data };
        })
      );
      
      const serverStatus = {};
      healthChecks.forEach((check, index) => {
        const name = Object.keys(MCP_ENDPOINTS)[index];
        if (check.status === 'fulfilled') {
          serverStatus[name] = check.value;
        } else {
          serverStatus[name] = { 
            name, 
            status: 'error', 
            error: check.reason?.message 
          };
        }
      });
      
      setServers(serverStatus);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  // Обробка українських команд
  const processUkrainian = useCallback(async (message, history = []) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${MCP_ENDPOINTS.atlas}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, history })
      });
      
      const result = await response.json();
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  // Браузерна автоматизація
  const browserAction = useCallback(async (action, data = {}) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${MCP_ENDPOINTS.playwright}/${action}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
      
      const result = await response.json();
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  // TTS генерація
  const generateTTS = useCallback(async (text, voice = 'uk_female') => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${MCP_ENDPOINTS.tts}/tts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, voice })
      });
      
      if (response.headers.get('content-type')?.includes('audio')) {
        const audioBlob = await response.blob();
        const audioUrl = URL.createObjectURL(audioBlob);
        return { audioUrl, blob: audioBlob };
      } else {
        const result = await response.json();
        return result;
      }
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  // macOS автоматизація
  const macOSExecute = useCallback(async (script, type = 'applescript') => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${MCP_ENDPOINTS.macos}/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ script, type })
      });
      
      const result = await response.json();
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  // Створення завдання
  const createJob = useCallback(async (message, autoFillDefaults = true) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${MCP_ENDPOINTS.orchestrator}/jobs/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, autoFillDefaults })
      });
      
      const result = await response.json();
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  // Автоматична перевірка при завантаженні
  useEffect(() => {
    checkHealth();
  }, [checkHealth]);

  return {
    // Стан
    servers,
    loading,
    error,
    
    // Методи
    checkHealth,
    processUkrainian,
    browserAction,
    generateTTS,
    macOSExecute,
    createJob,
    
    // Утиліти
    isServerOnline: (serverName) => servers[serverName]?.status === 'ok',
    getServerData: (serverName) => servers[serverName]?.data,
  };
};

// ==============================================
// EXAMPLE REACT COMPONENT
// ==============================================

export const MCPHubDemo = () => {
  const {
    servers,
    loading,
    error,
    checkHealth,
    processUkrainian,
    browserAction,
    generateTTS,
    isServerOnline
  } = useMCPHub();

  const [message, setMessage] = useState('');
  const [response, setResponse] = useState(null);

  const handleUkrainianTest = async () => {
    try {
      const result = await processUkrainian("відкрий мені програму мюсік");
      setResponse(result);
    } catch (err) {
      console.error('Ukrainian test failed:', err);
    }
  };

  const handleBrowserTest = async () => {
    try {
      const result = await browserAction('navigate', { url: 'https://google.com' });
      setResponse(result);
    } catch (err) {
      console.error('Browser test failed:', err);
    }
  };

  const handleTTSTest = async () => {
    try {
      const result = await generateTTS("Привіт, це тест українського TTS");
      if (result.audioUrl) {
        const audio = new Audio(result.audioUrl);
        audio.play();
      }
      setResponse(result);
    } catch (err) {
      console.error('TTS test failed:', err);
    }
  };

  return (
    <div style={{ padding: '20px', fontFamily: 'monospace' }}>
      <h1>🚀 MCP Hub React Integration</h1>
      
      {/* Server Status */}
      <div style={{ marginBottom: '20px' }}>
        <h2>Server Status:</h2>
        <button onClick={checkHealth} disabled={loading}>
          {loading ? 'Checking...' : 'Refresh Status'}
        </button>
        
        <div style={{ marginTop: '10px' }}>
          {Object.entries(servers).map(([name, status]) => (
            <div key={name} style={{ 
              color: isServerOnline(name) ? 'green' : 'red',
              marginBottom: '5px'
            }}>
              {name}: {status.status}
              {status.data?.tools && ` (${status.data.tools.length} tools)`}
            </div>
          ))}
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div style={{ color: 'red', marginBottom: '20px' }}>
          Error: {error}
        </div>
      )}

      {/* Test Buttons */}
      <div style={{ marginBottom: '20px' }}>
        <h2>Tests:</h2>
        <button onClick={handleUkrainianTest} disabled={loading || !isServerOnline('atlas')}>
          Test Ukrainian ("відкрий мені програму мюсік")
        </button>
        
        <button onClick={handleBrowserTest} disabled={loading || !isServerOnline('playwright')}>
          Test Browser (Navigate to Google)
        </button>
        
        <button onClick={handleTTSTest} disabled={loading || !isServerOnline('tts')}>
          Test Ukrainian TTS
        </button>
      </div>

      {/* Custom Message */}
      <div style={{ marginBottom: '20px' }}>
        <h2>Custom Ukrainian Command:</h2>
        <input
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Введіть українську команду..."
          style={{ width: '300px', marginRight: '10px' }}
        />
        <button 
          onClick={() => processUkrainian(message).then(setResponse)}
          disabled={loading || !message || !isServerOnline('atlas')}
        >
          Process
        </button>
      </div>

      {/* Response Display */}
      {response && (
        <div style={{ marginTop: '20px' }}>
          <h2>Response:</h2>
          <pre style={{ 
            background: '#f5f5f5', 
            padding: '10px', 
            overflow: 'auto',
            maxHeight: '300px'
          }}>
            {JSON.stringify(response, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
};

export default useMCPHub;

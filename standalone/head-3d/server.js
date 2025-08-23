/* Simple Express static server for 3D head demo */
const express = require('express');
const path = require('path');

const app = express();
const PORT = process.env.HEAD3D_PORT || 8080;

// Basic health endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'healthy', service: 'head-3d', port: PORT });
});

// Serve this folder statically (index.html at root)
const staticDir = __dirname;
app.use(express.static(staticDir, { index: 'index.html', extensions: ['html'] }));

// Fallback to index.html for root
app.get('/', (req, res) => {
  res.sendFile(path.join(staticDir, 'index.html'));
});

app.listen(PORT, () => {
  console.log(`Head-3D server listening on http://0.0.0.0:${PORT}`);
});

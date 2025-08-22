// Minimal standalone server for the 3D Head demo
import "dotenv/config";
import express from "express";
import cors from "cors";
import path from "path";
import fs from "fs";
import dotenv from "dotenv";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT || 8099;

app.use(express.json({ limit: "2mb" }));
// Allow cross-origin access from local dev UIs
// Allow all dev origins (localhost, 127.0.0.1, container IPs). No credentials are used.
app.use(cors());

// Paths
const demoRoot = path.resolve(__dirname, "../../standalone/head-3d");
// Serve assets from standard frontend folder
const activeAssets = path.resolve(__dirname, "../../frontend/public");
const archivedAssets = path.resolve(
  __dirname,
  "../../archive/frontend-face/public"
);
const assetsRoot = fs.existsSync(activeAssets) ? activeAssets : archivedAssets;

// Optionally load config/environment.env (without overriding existing vars)
try {
  const envPath = path.resolve(__dirname, "../../config/environment.env");
  if (fs.existsSync(envPath)) {
    dotenv.config({ path: envPath, override: false });
  }
} catch {}

// Basic health endpoint
app.get("/health", (_req, res) => {
  res.json({
    ok: true,
    service: "head-3d-demo",
    assetsRoot: "/assets",
    time: new Date().toISOString(),
  });
});

// Expose config (for dev/demo only; this leaks the key to client)
app.get("/config.js", (_req, res) => {
  const cfg = {
    GEMINI_API_KEY: process.env.GEMINI_API_KEY || "",
    GOOGLE_API_KEY: process.env.GOOGLE_API_KEY || "",
    GENAI_API_KEY: process.env.GENAI_API_KEY || "",
  };
  res.setHeader("Content-Type", "application/javascript; charset=utf-8");
  res.setHeader("Cache-Control", "no-store");
  res.send(`window.__CONFIG__ = ${JSON.stringify(cfg)};`);
});

// Simple server-side TTS proxy to reduce client rate-limit issues
app.post("/tts", async (req, res) => {
  try {
    const { text, voice = "Kore" } = req.body || {};
    if (!text || typeof text !== "string") {
      return res.status(400).json({ error: "Missing text" });
    }

    const apiKey =
      process.env.GEMINI_API_KEY ||
      process.env.GOOGLE_API_KEY ||
      process.env.GENAI_API_KEY ||
      "";
    if (!apiKey) {
      return res.status(500).json({ error: "No API key configured on server" });
    }

    const MAX_RETRIES = 3;
    const RETRY_DELAY = 1000;
    const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

    const payload = {
      contents: [{ parts: [{ text }] }],
      generationConfig: {
        responseModalities: ["AUDIO"],
        speechConfig: {
          voiceConfig: { prebuiltVoiceConfig: { voiceName: voice } },
        },
      },
      model: "gemini-2.5-flash-preview-tts",
    };

    let lastErr;
    for (let i = 0; i <= MAX_RETRIES; i++) {
      const resp = await fetch(
        `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent?key=${apiKey}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        }
      );
      if (resp.ok) {
        const js = await resp.json();
        const part = js?.candidates?.[0]?.content?.parts?.[0];
        const data = part?.inlineData?.data;
        const mimeType = part?.inlineData?.mimeType || "audio/wav";
        if (!data) {
          return res.status(502).json({ error: "No audio data in response" });
        }
        return res.json({ mimeType, audioContent: data });
      }
      lastErr = new Error(`Upstream status ${resp.status}`);
      if (
        [429, 500, 502, 503, 504, 408].includes(resp.status) &&
        i < MAX_RETRIES
      ) {
        await sleep(RETRY_DELAY * Math.pow(2, i));
        continue;
      }
      break;
    }
    return res.status(502).json({ error: lastErr?.message || "TTS failed" });
  } catch (e) {
    return res
      .status(500)
      .json({ error: e instanceof Error ? e.message : String(e) });
  }
});

// Serve static assets from frontend/public under /assets
app.use(
  "/assets",
  express.static(assetsRoot, { fallthrough: true, maxAge: "1d" })
);

// Serve the demo static files at /
app.use("/", express.static(demoRoot, { fallthrough: true }));

// Root index
app.get("/", (_req, res) => {
  res.sendFile(path.join(demoRoot, "index.html"));
});

app.listen(PORT, () => {
  console.log(`[head-3d] Server running at http://localhost:${PORT}`);
  console.log(`[head-3d] Health:        http://localhost:${PORT}/health`);
  console.log(`[head-3d] Assets root:   http://localhost:${PORT}/assets/`);
  console.log(
    `[head-3d] Example GLB:   http://localhost:${PORT}/assets/models/robot-head/<your-model>.glb`
  );
});

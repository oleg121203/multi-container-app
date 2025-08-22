// Minimal client to render 3D head or fallback image; layout matches hacker theme

const elStage = document.getElementById('head3D');
const logs = document.getElementById('logsList');

function log(lvl, msg){
  const row = document.createElement('div');
  row.className = 'log';
  const lvlSpan = document.createElement('span');
  lvlSpan.className = 'lvl lvl-' + (lvl || 'INFO');
  lvlSpan.textContent = (lvl || 'INFO').padEnd(4, ' ');
  const time = document.createElement('span');
  time.className = 'time';
  time.textContent = new Date().toLocaleTimeString();
  const text = document.createElement('span');
  text.className = 'text';
  text.textContent = ' ' + msg;
  row.append(lvlSpan, time, text);
  logs?.appendChild(row);
  logs?.scrollTo({ top: logs.scrollHeight });
}

function getModelUrl(){
  // Priority: window.HEAD_MODEL_URL -> data-model attribute -> null
  if (window.HEAD_MODEL_URL && typeof window.HEAD_MODEL_URL === 'string') return window.HEAD_MODEL_URL;
  const data = elStage?.getAttribute('data-model');
  return data && data.includes('<your-model>') ? null : data;
}

async function init(){
  const url = getModelUrl();
  if (!window.THREE || !THREE.GLTFLoader) {
    log('WARN', 'three.js or GLTFLoader not loaded, using fallback image.');
    return;
  }
  if (!url) {
    log('INFO', 'No model URL configured, showing fallback.');
    return;
  }

  try {
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(50, elStage.clientWidth / elStage.clientHeight, 0.1, 100);
    camera.position.set(0, 0, 2.2);
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(elStage.clientWidth, elStage.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    elStage.appendChild(renderer.domElement);

    const light = new THREE.PointLight(0x00ff66, 3, 10);
    light.position.set(1, 1, 2);
    scene.add(light);

    const ambient = new THREE.AmbientLight(0x004422, 0.8);
    scene.add(ambient);

    const loader = new THREE.GLTFLoader();
    loader.load(url, (gltf) => {
      const root = gltf.scene;
      root.rotation.y = Math.PI; // face forward depending on asset orientation
      scene.add(root);
      log('INFO', 'Model loaded: ' + url);
      animate();

      function animate(){
        requestAnimationFrame(animate);
        root.rotation.y += 0.002;
        renderer.render(scene, camera);
      }
    }, undefined, (err) => {
      log('ERR', 'Failed to load model: ' + err.message);
    });

    window.addEventListener('resize', () => {
      const w = elStage.clientWidth, h = elStage.clientHeight;
      renderer.setSize(w, h);
      camera.aspect = w / h; camera.updateProjectionMatrix();
    });
  } catch (e) {
    log('ERR', e.message || String(e));
  }
}

// Seed demo logs to resemble the screenshot
['ERROR [VOICE] Atlas coordinator initialized',
 'WARN  [ATLAS] Playwright MCP server running',
 'WARN  [ORCHESTRATOR] Atlas coordinator initialized',
 'INFO  [TTS] Voice recognition ready']
  .forEach(m => log((m.match(/^(ERROR|WARN|INFO)/)||[])[1], m));

init();

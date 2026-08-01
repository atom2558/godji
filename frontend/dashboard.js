let ws = null;
let captureInterval = null;
let isStreaming = false;

const wsUrlInput = document.getElementById('wsUrlInput');
const connectBtn = document.getElementById('connectBtn');
const toggleVisionBtn = document.getElementById('toggleVisionBtn');
const toggleOverlayBtn = document.getElementById('toggleOverlayBtn');
const cliCommandInput = document.getElementById('cliCommandInput');
const runCliBtn = document.getElementById('runCliBtn');
const logBox = document.getElementById('logBox');
const statusBadge = document.getElementById('statusBadge');
const statusText = document.getElementById('statusText');
const clearLogBtn = document.getElementById('clearLogBtn');

function log(message, type = 'info') {
  const time = new Date().toLocaleTimeString();
  const div = document.createElement('div');
  div.className = `log-item ${type}`;
  div.innerText = `[${time}] ${message}`;
  logBox.appendChild(div);
  logBox.scrollTop = logBox.scrollHeight;
}

clearLogBtn.addEventListener('click', () => {
  logBox.innerHTML = '';
});

// Connect to Backend WebSocket Server
connectBtn.addEventListener('click', () => {
  const url = wsUrlInput.value.trim();
  if (!url) return;

  if (ws) {
    ws.close();
  }

  log(`Connecting to WebSocket server: ${url}...`, 'info');
  
  try {
    ws = new WebSocket(url);

    ws.onopen = () => {
      statusBadge.className = 'status-badge';
      statusText.innerText = 'Connected';
      log('Connected to AI Godji Backend successfully!', 'success');
      connectBtn.innerText = 'Disconnect';
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === 'hud_update') {
          // Send HUD data to Electron main process to render on transparent canvas
          window.godjiAPI.sendDrawHUD(msg.data);
          if (msg.data.subtitles) {
            log(`🐉 Godji: ${msg.data.subtitles}`, 'success');
          }
        } else if (msg.type === 'cli_result') {
          log(`🚀 CLI [${msg.tool_name}] Result: ${JSON.stringify(msg.result)}`, 'success');
        } else if (msg.type === 'skip') {
          // Heartbeat skipped
        }
      } catch (err) {
        log(`Error parsing server message: ${err}`, 'error');
      }
    };

    ws.onerror = (err) => {
      log(`WebSocket error: ${err}`, 'error');
    };

    ws.onclose = () => {
      statusBadge.className = 'status-badge offline';
      statusText.innerText = 'Disconnected';
      log('WebSocket connection closed.', 'warning');
      connectBtn.innerText = 'Connect Backend';
      stopStreaming();
    };
  } catch (err) {
    log(`Failed to create WebSocket: ${err}`, 'error');
  }
});

// Toggle Real-time Screen Vision Stream
toggleVisionBtn.addEventListener('click', () => {
  if (isStreaming) {
    stopStreaming();
  } else {
    startStreaming();
  }
});

function startStreaming() {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    log('Please connect to Backend WebSocket server first!', 'warning');
    return;
  }

  isStreaming = true;
  toggleVisionBtn.innerText = '⏸️ Pause Vision Stream';
  toggleVisionBtn.className = 'btn btn-danger';
  log('Started Real-time Screen Vision stream (1 frame/sec)...', 'info');

  // Capture screen frame every 1000ms
  captureInterval = setInterval(async () => {
    if (!isStreaming || ws.readyState !== WebSocket.OPEN) return;

    const base64Frame = await window.godjiAPI.captureScreen();
    if (base64Frame) {
      ws.send(JSON.stringify({
        type: 'frame',
        image: base64Frame
      }));
    }
  }, 1000);
}

function stopStreaming() {
  isStreaming = false;
  if (captureInterval) {
    clearInterval(captureInterval);
    captureInterval = null;
  }
  toggleVisionBtn.innerText = '▶️ Start Real-time Vision';
  toggleVisionBtn.className = 'btn btn-primary';
  log('Paused Screen Vision stream.', 'info');
}

// Toggle Overlay HUD Visibility
let isOverlayVisible = true;
toggleOverlayBtn.addEventListener('click', () => {
  isOverlayVisible = !isOverlayVisible;
  window.godjiAPI.toggleOverlay(isOverlayVisible);
  log(`Toggled HUD Overlay: ${isOverlayVisible ? 'Visible' : 'Hidden'}`, 'info');
});

// Run Manual CLI Command
runCliBtn.addEventListener('click', () => {
  const cmd = cliCommandInput.value.trim();
  if (!cmd) return;

  if (!ws || ws.readyState !== WebSocket.OPEN) {
    log('Please connect to Backend WebSocket server first!', 'warning');
    return;
  }

  log(`Executing CLI command: "${cmd}"...`, 'info');
  ws.send(JSON.stringify({
    type: 'cli',
    tool_name: 'execute_command',
    tool_args: { command: cmd }
  }));
  cliCommandInput.value = '';
});

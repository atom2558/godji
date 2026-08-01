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
        } else if (msg.type === 'chat_reply') {
          log(`🐉 Godji: ${msg.reply}`, 'success');
          speakText(msg.reply);
          if (msg.cli_command) {
            log(`⚡ Godji สั่งรันคำสั่ง: ${msg.cli_command}`, 'warning');
          }
          if (msg.cli_output) {
            log(`💻 CLI Output: ${JSON.stringify(msg.cli_output)}`, 'info');
          }
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

// Chat & Voice Controller
const chatInput = document.getElementById('chatInput');
const sendChatBtn = document.getElementById('sendChatBtn');
const micBtn = document.getElementById('micBtn');
const ttsToggleBtn = document.getElementById('ttsToggleBtn');

let isTTSEnabled = true;
let isRecording = false;
let mediaRecorder = null;
let audioChunks = [];

if (micBtn) {
  micBtn.addEventListener('click', async () => {
    if (isRecording) {
      stopRecording();
    } else {
      await startRecording();
    }
  });
}

async function startRecording() {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    log('โปรดเชื่อมต่อ Backend WebSocket ก่อนใช้ไมโครโฟน!', 'warning');
    return;
  }

  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    audioChunks = [];

    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) audioChunks.push(event.data);
    };

    mediaRecorder.onstop = async () => {
      const mimeType = mediaRecorder.mimeType || 'audio/webm';
      const audioBlob = new Blob(audioChunks, { type: mimeType });
      const reader = new FileReader();
      reader.readAsDataURL(audioBlob);
      reader.onloadend = async () => {
        const base64Audio = reader.result.split(',')[1];
        const base64Frame = await window.godjiAPI.captureScreen();
        
        log('🎙️ ส่งเสียงอัดของคุณไปให้ Gemini 2.5 Flash ประมวลผล...', 'info');
        ws.send(JSON.stringify({
          type: 'voice_chat',
          audio: base64Audio,
          mime_type: mimeType,
          image: base64Frame
        }));
      };
      stream.getTracks().forEach(track => track.stop());
    };

    mediaRecorder.start();
    isRecording = true;
    micBtn.style.background = '#ef4444';
    micBtn.innerText = '🛑';
    log('🎙️ กำลังอัดเสียง... พูดเสร็จแล้วกดปุ่ม 🛑 อีกครั้งเพื่อส่งหา Godji ครับ', 'info');
  } catch (err) {
    log(`⚠️ ไม่สามารถเปิดไมโครโฟนได้: ${err.message}`, 'error');
  }
}

function stopRecording() {
  if (mediaRecorder && isRecording) {
    mediaRecorder.stop();
    isRecording = false;
    micBtn.style.background = '#ec4899';
    micBtn.innerText = '🎙️';
  }
}

if (ttsToggleBtn) {
  ttsToggleBtn.addEventListener('click', () => {
    isTTSEnabled = !isTTSEnabled;
    ttsToggleBtn.style.background = isTTSEnabled ? '#10b981' : '#64748b';
    log(`🔊 เสียงตอบกลับ: ${isTTSEnabled ? 'เปิด' : 'ปิด'}`, 'info');
  });
}

function speakText(text) {
  if (!isTTSEnabled || !('speechSynthesis' in window)) return;
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = 'th-TH';
  utterance.rate = 1.0;
  window.speechSynthesis.speak(utterance);
}

async function sendChatMessage(msgText) {
  const text = msgText || (chatInput ? chatInput.value.trim() : '');
  if (!text) return;

  if (!ws || ws.readyState !== WebSocket.OPEN) {
    log('โปรดเชื่อมต่อ Backend WebSocket ก่อนส่งข้อความ!', 'warning');
    return;
  }

  log(`💬 คุณ: ${text}`, 'info');

  const base64Frame = await window.godjiAPI.captureScreen();

  ws.send(JSON.stringify({
    type: 'chat',
    message: text,
    image: base64Frame
  }));

  if (chatInput) chatInput.value = '';
}

if (sendChatBtn) {
  sendChatBtn.addEventListener('click', () => sendChatMessage());
}
if (chatInput) {
  chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendChatMessage();
  });
}


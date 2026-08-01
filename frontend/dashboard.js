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
          // Vision Stream updates HUD silently - NO TTS here!
        } else if (msg.type === 'cli_result') {
          log(`🚀 CLI [${msg.tool_name}] Result: ${JSON.stringify(msg.result)}`, 'success');
        } else if (msg.type === 'chat_reply') {
          if (msg.reply) {
            log(`🐉 Godji: ${msg.reply}`, 'success');
            speakText(msg.reply);
          }
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
  log('Started Real-time Screen Vision stream (1 frame per 4.5 sec - Free Tier safe)...', 'info');

  // Capture screen frame every 4500ms (13 requests/min to strictly respect Gemini Free Tier 15 RPM limit)
  captureInterval = setInterval(async () => {
    if (!isStreaming || ws.readyState !== WebSocket.OPEN) return;

    const base64Frame = await window.godjiAPI.captureScreen();
    if (base64Frame) {
      ws.send(JSON.stringify({
        type: 'frame',
        image: base64Frame
      }));
    }
  }, 4500);
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
let audioContext = null;
let silenceTimer = null;
let animFrameId = null;

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
    
    // Set up Web Audio API VAD (Voice Activity Detection)
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const analyser = audioContext.createAnalyser();
    analyser.fftSize = 512;
    const source = audioContext.createMediaStreamSource(stream);
    source.connect(analyser);

    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    mediaRecorder = new MediaRecorder(stream);
    audioChunks = [];

    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) audioChunks.push(event.data);
    };

    mediaRecorder.onstop = async () => {
      if (animFrameId) cancelAnimationFrame(animFrameId);
      if (silenceTimer) clearTimeout(silenceTimer);
      if (audioContext && audioContext.state !== 'closed') audioContext.close();

      const mimeType = mediaRecorder.mimeType || 'audio/webm';
      const audioBlob = new Blob(audioChunks, { type: mimeType });
      
      if (audioBlob.size < 1000) {
        log('⚠️ เสียงสั้นเกินไป ไม่ถูกส่ง', 'warning');
        stream.getTracks().forEach(track => track.stop());
        return;
      }

      const reader = new FileReader();
      reader.readAsDataURL(audioBlob);
      reader.onloadend = async () => {
        const base64Audio = reader.result.split(',')[1];
        // ONLY capture screen if Vision Stream is ACTIVE (isStreaming === true)
        const base64Frame = isStreaming ? await window.godjiAPI.captureScreen() : null;
        
        log('🎙️ ส่งเสียงของคุณไปให้ AI Godji ประมวลผล...', 'info');
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
    micBtn.innerText = '🎙️ (กำลังฟัง...)';
    log('🎙️ เริ่มฟังเสียง... เมื่อพูดจบและเงียบเสียง ระบบจะส่งให้อัตโนมัติครับ', 'info');

    let hasSpoken = false;
    const SILENCE_THRESHOLD = 15;
    const SILENCE_TIMEOUT = 1200; // 1.2s silence to auto-send

    function checkSilence() {
      if (!isRecording) return;
      analyser.getByteFrequencyData(dataArray);
      let sum = 0;
      for (let i = 0; i < bufferLength; i++) sum += dataArray[i];
      let average = sum / bufferLength;

      if (average > SILENCE_THRESHOLD) {
        hasSpoken = true;
        if (silenceTimer) {
          clearTimeout(silenceTimer);
          silenceTimer = null;
        }
      } else if (hasSpoken && !silenceTimer) {
        silenceTimer = setTimeout(() => {
          log('🎙️ เงียบเสียงแล้ว หยุดอัดและส่งให้อัตโนมัติ...', 'info');
          stopRecording();
        }, SILENCE_TIMEOUT);
      }

      animFrameId = requestAnimationFrame(checkSilence);
    }

    checkSilence();

  } catch (err) {
    log(`⚠️ ไม่สามารถเปิดไมโครโฟนได้: ${err.message}`, 'error');
  }
}

function stopRecording() {
  if (mediaRecorder && isRecording) {
    isRecording = false;
    mediaRecorder.stop();
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
  if (!isTTSEnabled || !('speechSynthesis' in window) || !text) return;
  
  // Clean raw JSON or markdown symbols if present
  let cleanText = text.replace(/```[\s\S]*?```/g, '').replace(/[\{\}\[\]\*\_\#]/g, '').strip?.() || text;
  if (!cleanText.trim()) return;

  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(cleanText);
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

  // ONLY capture screen if Vision Stream is ACTIVE (isStreaming === true)
  const base64Frame = isStreaming ? await window.godjiAPI.captureScreen() : null;

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



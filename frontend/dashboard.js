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
          if (msg.transcribed_text) {
            log(`🎙️ เสียงถูกแปลงเป็นข้อความ: "${msg.transcribed_text}"`, 'info');
          }
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
        } else if (msg.type === 'request_screen_snapshot') {
          log('📸 AI Godji ร้องขอภาพหน้าจอเพิ่มเติมเพื่อวิเคราะห์... ถ่ายภาพ 1 ช็อตส่งทันที', 'info');
          try {
            const base64Frame = await window.godjiAPI.captureScreen();
            ws.send(JSON.stringify({
              type: 'chat',
              message: msg.prompt || "ช่วยวิเคราะห์ภาพหน้าจอนี้แล้วตอบคำถามให้ด้วยครับ",
              image: base64Frame
            }));
          } catch (err) {
            console.warn("Screen capture request failed:", err);
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
      log('WebSocket connection closed. Retrying in 2 seconds...', 'warning');
      connectBtn.innerText = 'Connect Backend';
      
      // Auto-reconnect loop
      setTimeout(() => {
        if (!ws || ws.readyState === WebSocket.CLOSED) {
          connectBtn.click();
        }
      }, 2000);
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
let micStream = null;
let audioContext = null;
let scriptProcessor = null;
let pcmBuffers = [];
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

function encodeWAV(samples, sampleRate = 16000) {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);

  const writeString = (v, o, str) => {
    for (let i = 0; i < str.length; i++) v.setUint8(o + i, str.charCodeAt(i));
  };

  writeString(view, 0, 'RIFF');
  view.setUint32(4, 36 + samples.length * 2, true);
  writeString(view, 8, 'WAVE');
  writeString(view, 12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); // PCM format
  view.setUint16(22, 1, true); // Mono
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true); // 16-bit
  writeString(view, 36, 'data');
  view.setUint32(40, samples.length * 2, true);

  let offset = 44;
  for (let i = 0; i < samples.length; i++) {
    let s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
    offset += 2;
  }

  return new Blob([view], { type: 'audio/wav' });
}

async function startRecording() {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    log('โปรดเชื่อมต่อ Backend WebSocket ก่อนใช้ไมโครโฟน!', 'warning');
    return;
  }

  try {
    micStream = await navigator.mediaDevices.getUserMedia({ 
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true
      } 
    });
    
    audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
    const source = audioContext.createMediaStreamSource(micStream);

    pcmBuffers = [];
    scriptProcessor = audioContext.createScriptProcessor(4096, 1, 1);
    scriptProcessor.onaudioprocess = (e) => {
      if (!isRecording) return;
      const inputData = e.inputBuffer.getChannelData(0);
      pcmBuffers.push(new Float32Array(inputData));
    };

    source.connect(scriptProcessor);
    scriptProcessor.connect(audioContext.destination);

    const analyser = audioContext.createAnalyser();
    analyser.fftSize = 512;
    source.connect(analyser);

    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    isRecording = true;
    micBtn.style.background = '#ef4444';
    micBtn.innerText = '🎙️ (กำลังฟัง...)';
    log('🎙️ เริ่มฟังเสียง... เมื่อพูดจบระบบจะส่งให้อัตโนมัติครับ', 'info');

    let hasSpoken = false;
    let consecutiveVoiceFrames = 0;
    const VOICE_THRESHOLD = 15.0; // Energy threshold above PC fan static
    const SILENCE_TIMEOUT = 1200; // 1.2s silence after speech

    function checkSilence() {
      if (!isRecording) return;
      analyser.getByteFrequencyData(dataArray);

      // Focus strictly on human voice frequency range (80Hz - 3400Hz, FFT bins 2 to 45)
      let voiceSum = 0;
      for (let i = 2; i < 45; i++) {
        voiceSum += dataArray[i];
      }
      let voiceEnergy = voiceSum / 43.0;

      if (voiceEnergy > VOICE_THRESHOLD) {
        consecutiveVoiceFrames++;
        if (consecutiveVoiceFrames >= 4) { // Requires ~0.4s continuous real human speech
          hasSpoken = true;
          if (silenceTimer) {
            clearTimeout(silenceTimer);
            silenceTimer = null;
          }
        }
      } else {
        consecutiveVoiceFrames = 0;
        if (hasSpoken && !silenceTimer) {
          silenceTimer = setTimeout(() => {
            log('🎙️ พูดจบและเงียบเสียงแล้ว... ส่งไฟล์เสียงไปให้ AI Godji ทันที!', 'info');
            stopRecording();
          }, SILENCE_TIMEOUT);
        }
      }

      animFrameId = requestAnimationFrame(checkSilence);
    }

    checkSilence();

  } catch (err) {
    log(`⚠️ ไม่สามารถเปิดไมโครโฟนได้: ${err.message}`, 'error');
  }
}

function stopRecording() {
  if (!isRecording) return;
  isRecording = false;

  micBtn.style.background = '#ec4899';
  micBtn.innerText = '🎙️';

  if (animFrameId) cancelAnimationFrame(animFrameId);
  if (silenceTimer) clearTimeout(silenceTimer);

  let totalLen = 0;
  for (let b of pcmBuffers) totalLen += b.length;
  
  if (totalLen < 16000 * 0.3) {
    log('⚠️ เสียงสั้นเกินไป ไม่ถูกส่ง', 'warning');
    if (micStream) micStream.getTracks().forEach(t => t.stop());
    if (audioContext && audioContext.state !== 'closed') audioContext.close();
    return;
  }

  let samples = new Float32Array(totalLen);
  let offset = 0;
  for (let b of pcmBuffers) {
    samples.set(b, offset);
    offset += b.length;
  }

  const wavBlob = encodeWAV(samples, 16000);
  const reader = new FileReader();
  reader.readAsDataURL(wavBlob);
  reader.onloadend = async () => {
    const base64Audio = reader.result.split(',')[1];
    
    // ONLY capture screen screenshot if Real-time Vision Stream is ACTIVE (isStreaming === true)
    let base64Frame = isStreaming ? await window.godjiAPI.captureScreen() : null;
    
    log('🎙️ ส่งไฟล์เสียง WAV ไปให้ AI Godji ถอดความ...', 'info');
    ws.send(JSON.stringify({
      type: 'voice_chat',
      audio: base64Audio,
      mime_type: 'audio/wav',
      image: base64Frame
    }));

    if (micStream) micStream.getTracks().forEach(t => t.stop());
    if (audioContext && audioContext.state !== 'closed') audioContext.close();
  };
}

const VISION_INTENT_KEYWORDS = [
  "ดูหน้าจอ", "มองหน้าจอ", "ดูจอ", "มองจอ", "หน้าจอผม", "หน้าจอฉัน", 
  "ช่วยดู", "ดูภาพ", "มองภาพ", "หน้าจอนี้", "เห็นอะไร", "อ่านหน้าจอ",
  "look at screen", "see screen", "on my screen", "look at my screen"
];

function isVisionIntent(text) {
  if (!text) return false;
  const lower = text.toLowerCase();
  return VISION_INTENT_KEYWORDS.some(kw => lower.includes(kw));
}

let isContinuousVoice = true; // Active by default for continuous handsfree listening
const continuousVoiceBtn = document.getElementById('continuousVoiceBtn');

if (continuousVoiceBtn) {
  continuousVoiceBtn.style.background = '#10b981';
  continuousVoiceBtn.innerText = '🔄 โหมดคุยต่อเนื่อง (Handsfree ADA V2): เปิดอยู่';

  continuousVoiceBtn.addEventListener('click', async () => {
    isContinuousVoice = !isContinuousVoice;
    if (isContinuousVoice) {
      continuousVoiceBtn.style.background = '#10b981';
      continuousVoiceBtn.innerText = '🔄 โหมดคุยต่อเนื่อง (Handsfree ADA V2): เปิดอยู่';
      log('🔄 เปิดโหมดคุยต่อเนื่อง (Handsfree ADA V2) - เมื่อ AI พูดจบ ระบบจะเริ่มฟังให้อัตโนมัติครับ', 'success');
      await startRecording();
    } else {
      continuousVoiceBtn.style.background = '#3b82f6';
      continuousVoiceBtn.innerText = '🔄 โหมดคุยต่อเนื่อง (Handsfree ADA V2): ปิด';
      log('🔄 ปิดโหมดคุยต่อเนื่องเรียบร้อยแล้ว', 'info');
      stopRecording();
    }
  });
}

function speakText(text) {
  if (!text) {
    if (isContinuousVoice) {
      setTimeout(async () => {
        if (isContinuousVoice && !isRecording) await startRecording();
      }, 500);
    }
    return;
  }
  
  // Clean raw JSON or markdown symbols if present
  let cleanText = text.replace(/```[\s\S]*?```/g, '').replace(/[\{\}\[\]\*\_\#]/g, '').trim() || text;

  let hasResumed = false;
  const autoResumeMic = async () => {
    if (hasResumed) return;
    hasResumed = true;
    if (isContinuousVoice && !isRecording) {
      log('🎙️ AI พูดจบแล้ว... เปิดไมค์ฟังเสียงต่อเนื่องอัตโนมัติ', 'info');
      await startRecording();
    }
  };

  if (!isTTSEnabled || !('speechSynthesis' in window) || !cleanText) {
    if (isContinuousVoice) {
      setTimeout(autoResumeMic, 800);
    }
    return;
  }

  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(cleanText);
  utterance.lang = 'th-TH';
  utterance.rate = 1.0;

  utterance.onend = autoResumeMic;
  utterance.onerror = autoResumeMic;

  window.speechSynthesis.speak(utterance);

  // Watchdog Timer Fallback: Guarantee mic re-opens even if Chrome SpeechSynthesis event drops
  const estimatedTimeMs = Math.max(2000, cleanText.length * 160);
  setTimeout(autoResumeMic, estimatedTimeMs + 500);
}

async function sendChatMessage(msgText) {
  const text = msgText || (chatInput ? chatInput.value.trim() : '');
  if (!text) return;

  if (!ws || ws.readyState !== WebSocket.OPEN) {
    log('โปรดเชื่อมต่อ Backend WebSocket ก่อนส่งข้อความ!', 'warning');
    return;
  }

  log(`💬 คุณ: ${text}`, 'info');

  // Capture screen snapshot if screen sharing is active OR if user explicitly asks AI to look at screen!
  let base64Frame = null;
  if (isStreaming || isVisionIntent(text)) {
    if (!isStreaming) {
      log('📸 ถ่ายภาพหน้าจอ 1 ช็อตส่งให้ AI Godji วิเคราะห์ทันที...', 'info');
    }
    base64Frame = await window.godjiAPI.captureScreen();
  }

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

// Auto-Connect and Auto-Start Settings on Launch (Persistent Retry Loop)
function autoInit() {
  const tryConnect = () => {
    if (ws && ws.readyState === WebSocket.OPEN) return;
    
    if (wsUrlInput && !wsUrlInput.value.includes('127.0.0.1') && !wsUrlInput.value.includes('render.com')) {
      wsUrlInput.value = 'ws://127.0.0.1:8000/ws/live';
    }
    
    if (connectBtn) {
      connectBtn.click();
    }
  };

  // Immediate attempt
  setTimeout(tryConnect, 400);

  // Persistent retry loop every 1.5s until Python backend finishes startup and connects!
  const initInterval = setInterval(() => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      clearInterval(initInterval);
    } else {
      tryConnect();
    }
  }, 1500);
}

if (document.readyState === 'loading') {
  window.addEventListener('DOMContentLoaded', autoInit);
} else {
  autoInit();
}



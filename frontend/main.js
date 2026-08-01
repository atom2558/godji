const { app, BrowserWindow, ipcMain, desktopCapturer, screen } = require('electron');
const path = require('path');
const { spawn, exec } = require('child_process');

let dashboardWindow = null;
let overlayWindow = null;
let pyBackendProcess = null;

function autoStartPythonBackend() {
  // Clear any existing process on port 8000 then start Python Backend
  const killCmd = process.platform === 'win32'
    ? 'for /f "tokens=5" %a in (\'netstat -aon ^| findstr :8000\') do taskkill /f /pid %a 2>nul'
    : 'fuser -k 8000/tcp';

  exec(killCmd, () => {
    const backendDir = path.join(__dirname, '..', 'backend');
    console.log('[Electron] Launching Python Backend from:', backendDir);
    
    pyBackendProcess = spawn('python', ['-m', 'uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', '8000'], {
      cwd: backendDir,
      shell: true
    });

    pyBackendProcess.stdout.on('data', (data) => {
      console.log(`[Python Backend] ${data}`);
    });

    pyBackendProcess.stderr.on('data', (data) => {
      console.error(`[Python Backend Err] ${data}`);
    });
  });
}

function createWindows() {
  const primaryDisplay = screen.getPrimaryDisplay();
  const { width, height } = primaryDisplay.bounds;

  // 1. Create Control Dashboard Window
  dashboardWindow = new BrowserWindow({
    width: 950,
    height: 680,
    title: '🐉 AI Godji Control Dashboard',
    backgroundColor: '#0f172a',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
    }
  });

  dashboardWindow.loadFile('dashboard.html');

  // 2. Create Fullscreen Transparent Screen HUD Overlay Window
  overlayWindow = new BrowserWindow({
    x: 0,
    y: 0,
    width: width,
    height: height,
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    skipTaskbar: true,
    hasShadow: false,
    resizable: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
    }
  });

  // Make window click-through so user can interact with games/apps underneath
  overlayWindow.setIgnoreMouseEvents(true, { forward: true });
  overlayWindow.loadFile('overlay.html');

  dashboardWindow.on('closed', () => {
    if (overlayWindow) overlayWindow.close();
    if (pyBackendProcess) pyBackendProcess.kill();
    app.quit();
  });
}

app.whenReady().then(() => {
  autoStartPythonBackend();
  createWindows();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindows();
  });
});

app.on('window-all-closed', () => {
  if (pyBackendProcess) pyBackendProcess.kill();
  if (process.platform !== 'darwin') app.quit();
});

// IPC Handler: Capture High-Quality Desktop Screen Frame for Computer Vision
ipcMain.handle('capture-screen', async () => {
  try {
    const sources = await desktopCapturer.getSources({
      types: ['screen'],
      thumbnailSize: { width: 1280, height: 720 }
    });

    if (sources.length > 0) {
      const primarySource = sources[0];
      const imagePng = primarySource.thumbnail.toPNG();
      return imagePng.toString('base64');
    }
    return null;
  } catch (error) {
    console.error('[Electron] Error capturing screen:', error);
    return null;
  }
});

// IPC Relay: Receive HUD Bounding Box Data from Dashboard and forward to Transparent Overlay Window
ipcMain.on('draw-hud', (event, hudData) => {
  if (overlayWindow && !overlayWindow.isDestroyed()) {
    overlayWindow.webContents.send('render-hud-boxes', hudData);
  }
});

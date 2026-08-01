const { app, BrowserWindow, ipcMain, desktopCapturer, screen } = require('electron');
const path = require('path');

let dashboardWindow = null;
let overlayWindow = null;

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
    app.quit();
  });
}

app.whenReady().then(() => {
  createWindows();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindows();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

// IPC Handler: Desktop Screen Frame Capture
ipcMain.handle('capture-screen', async () => {
  try {
    const sources = await desktopCapturer.getSources({
      types: ['screen'],
      thumbnailSize: { width: 1280, height: 720 }
    });
    if (sources.length > 0) {
      return sources[0].thumbnail.toJPEG(80).toString('base64');
    }
    return null;
  } catch (error) {
    console.error('Error capturing desktop screen:', error);
    return null;
  }
});

// IPC Handler: Relay HUD draw commands to Overlay Window
ipcMain.on('draw-hud', (event, hudData) => {
  if (overlayWindow && !overlayWindow.isDestroyed()) {
    overlayWindow.webContents.send('render-hud-data', hudData);
  }
});

// IPC Handler: Toggle Overlay Visibility
ipcMain.on('toggle-overlay', (event, visible) => {
  if (overlayWindow && !overlayWindow.isDestroyed()) {
    if (visible) overlayWindow.show();
    else overlayWindow.hide();
  }
});

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('godjiAPI', {
  captureScreen: () => ipcRenderer.invoke('capture-screen'),
  sendDrawHUD: (hudData) => ipcRenderer.send('draw-hud', hudData),
  onRenderHUD: (callback) => ipcRenderer.on('render-hud-data', (event, data) => callback(data)),
  toggleOverlay: (visible) => ipcRenderer.send('toggle-overlay', visible)
});

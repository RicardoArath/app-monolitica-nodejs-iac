/**
 * main.js – Proceso principal de Electron
 * ----------------------------------------
 * • Crea la ventana del catálogo.
 * • Provee un handler IPC para hacer fetch de XML desde cualquier URL.
 */

const electron = require('electron');
const path = require('path');

const app = electron.app;
const BrowserWindow = electron.BrowserWindow;
const ipcMain = electron.ipcMain;

// ── Ventana principal ───────────────────────────────────────────────────
function createWindow() {
  const win = new BrowserWindow({
    width:  1320,
    height: 850,
    minWidth: 800,
    minHeight: 600,
    title: 'Librería en Línea – Catálogo',
    backgroundColor: '#0f172a',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  win.loadFile(path.join(__dirname, 'renderer', 'index.html'));
}

// ── IPC: fetch XML desde una URL ────────────────────────────────────────
ipcMain.handle('fetch-xml', async (_event, url) => {
  try {
    const { net } = electron;
    const response = await net.fetch(url);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    const text = await response.text();
    return { ok: true, data: text };
  } catch (err) {
    return { ok: false, error: err.message };
  }
});

// ── Lifecycle ───────────────────────────────────────────────────────────
app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  app.quit();
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});

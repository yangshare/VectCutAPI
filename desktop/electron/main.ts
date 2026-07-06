import { app, BrowserWindow, ipcMain } from 'electron';
import { join } from 'path';
import { registerDialogHandlers } from './ipc/dialog';
import { registerMediaProbeHandlers } from './ipc/mediaProbe';
import { registerJianyingHandlers } from './ipc/jianyingDir';
import { registerPackerHandlers } from './ipc/packer';
import { registerConfigStoreHandlers } from './ipc/configStore';

let mainWindow: BrowserWindow | null = null;

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 960,
    minHeight: 640,
    title: 'VectCut 模板套版',
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  const rendererUrl = app.isPackaged ? undefined : process.env.ELECTRON_RENDERER_URL;
  if (rendererUrl) {
    mainWindow.loadURL(rendererUrl);
  } else {
    mainWindow.loadFile(join(__dirname, '../renderer/index.html'));
  }
}

function registerIpcHandlers(): void {
  registerDialogHandlers(ipcMain);
  registerMediaProbeHandlers(ipcMain);
  registerJianyingHandlers(ipcMain);
  registerPackerHandlers(ipcMain);
  registerConfigStoreHandlers(ipcMain);
}

app.whenReady().then(() => {
  registerIpcHandlers();
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

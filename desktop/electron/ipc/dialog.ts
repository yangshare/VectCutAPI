import { dialog } from 'electron';
import { readFile, stat } from 'fs/promises';
import { extname } from 'path';
import type { IpcMain } from 'electron';

export const VIDEO_EXTS = ['mp4', 'mov', 'avi', 'mkv', 'flv'];
export const AUDIO_EXTS = ['mp3', 'wav', 'aac', 'm4a', 'flac'];
export const IMAGE_EXTS = ['jpg', 'jpeg', 'png', 'webp', 'bmp'];

export async function pickFile(name: string, extensions: string[]): Promise<string | null> {
  const result = await dialog.showOpenDialog({
    title: `选择${name}`,
    properties: ['openFile'],
    filters: [{ name, extensions }],
  });

  return result.canceled || result.filePaths.length === 0 ? null : result.filePaths[0];
}

export async function readZipFile(
  filePath: string,
  maxBytes = 100 * 1024 * 1024,
): Promise<Buffer> {
  if (typeof filePath !== 'string' || filePath.trim() === '') {
    throw new Error('ZIP 文件路径不能为空');
  }

  if (extname(filePath).toLowerCase() !== '.zip') {
    throw new Error('仅支持 .zip 文件');
  }

  let fileStat;
  try {
    fileStat = await stat(filePath);
  } catch (error) {
    if (isNodeError(error) && error.code === 'ENOENT') {
      throw new Error(`ZIP 文件不存在：${filePath}`);
    }
    throw error;
  }

  if (!fileStat.isFile()) {
    throw new Error(`ZIP 路径不是文件：${filePath}`);
  }

  if (fileStat.size > maxBytes) {
    throw new Error('ZIP 文件过大');
  }

  return readFile(filePath);
}

export function registerDialogHandlers(ipcMain: IpcMain): void {
  ipcMain.handle('dialog:selectVideoFile', () => pickFile('视频', VIDEO_EXTS));
  ipcMain.handle('dialog:selectAudioFile', () => pickFile('音频', AUDIO_EXTS));
  ipcMain.handle('dialog:selectImageFile', () => pickFile('图片', IMAGE_EXTS));
  ipcMain.handle('dialog:selectSrtFile', () => pickFile('SRT 字幕', ['srt', 'txt']));
  ipcMain.handle('dialog:selectTemplateFolder', async () => {
    const result = await dialog.showOpenDialog({
      title: '选择母版草稿文件夹',
      properties: ['openDirectory'],
    });

    return result.canceled || result.filePaths.length === 0 ? null : result.filePaths[0];
  });
  ipcMain.handle('file:readZip', (_event, filePath: string) => readZipFile(filePath));
}

function isNodeError(error: unknown): error is NodeJS.ErrnoException {
  return error instanceof Error && 'code' in error;
}

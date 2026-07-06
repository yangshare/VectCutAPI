import { dialog } from 'electron';
import { lstat, readFile, stat, writeFile } from 'fs/promises';
import { extname } from 'path';
import type { IpcMain } from 'electron';

export const VIDEO_EXTS = ['mp4', 'mov', 'avi', 'mkv', 'flv'];
export const AUDIO_EXTS = ['mp3', 'wav', 'aac', 'm4a', 'flac'];
export const IMAGE_EXTS = ['jpg', 'jpeg', 'png', 'webp', 'bmp'];
const MAX_ZIP_BYTES = 100 * 1024 * 1024;
const authorizedZipSavePaths = new Set<string>();

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
  maxBytes = MAX_ZIP_BYTES,
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

export async function selectDraftSavePath(suggestedName: string): Promise<string | null> {
  if (typeof suggestedName !== 'string' || suggestedName.trim() === '') {
    throw new Error('草稿文件名不能为空');
  }

  const defaultPath = normalizeZipFileName(suggestedName);
  const result = await dialog.showSaveDialog({
    title: '保存草稿 ZIP',
    defaultPath,
    filters: [{ name: 'ZIP 文件', extensions: ['zip'] }],
  });

  if (result.canceled || !result.filePath) {
    return null;
  }

  authorizedZipSavePaths.add(result.filePath);
  return result.filePath;
}

export async function selectJianyingDraftDir(): Promise<string | null> {
  const result = await dialog.showOpenDialog({
    title: '选择剪映草稿根目录',
    properties: ['openDirectory'],
  });

  return result.canceled || result.filePaths.length === 0 ? null : result.filePaths[0];
}

export async function writeZipFile(
  savePath: string,
  data: ArrayBuffer | Uint8Array,
  maxBytes = MAX_ZIP_BYTES,
): Promise<void> {
  if (typeof savePath !== 'string' || savePath.trim() === '') {
    throw new Error('ZIP 保存路径不能为空');
  }

  if (extname(savePath).toLowerCase() !== '.zip') {
    throw new Error('仅支持 .zip 文件');
  }

  if (!(data instanceof ArrayBuffer) && !(data instanceof Uint8Array)) {
    throw new Error('ZIP 数据无效');
  }

  const bytes = data instanceof Uint8Array
    ? Buffer.from(data)
    : Buffer.from(data);

  if (bytes.byteLength > maxBytes) {
    throw new Error('ZIP 文件过大');
  }

  if (!authorizedZipSavePaths.has(savePath)) {
    throw new Error('ZIP 保存路径未授权');
  }

  authorizedZipSavePaths.delete(savePath);

  try {
    let savePathStat;
    try {
      savePathStat = await lstat(savePath);
    } catch (error) {
      if (!isNodeError(error) || error.code !== 'ENOENT') {
        throw error;
      }
    }

    if (savePathStat?.isSymbolicLink()) {
      throw new Error('ZIP 保存路径不能是符号链接');
    }

    await writeFile(savePath, bytes);
  } catch (error) {
    throw error;
  }
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
  ipcMain.handle('dialog:selectJianyingDraftDir', () => selectJianyingDraftDir());
  ipcMain.handle('dialog:selectDraftSavePath', (_event, suggestedName: string) =>
    selectDraftSavePath(suggestedName));
  ipcMain.handle('file:readZip', (_event, filePath: string) => readZipFile(filePath));
  ipcMain.handle('file:writeZip', (_event, savePath: string, data: ArrayBuffer | Uint8Array) =>
    writeZipFile(savePath, data));
}

function isNodeError(error: unknown): error is NodeJS.ErrnoException {
  return error instanceof Error && 'code' in error;
}

function normalizeZipFileName(value: string): string {
  const raw = typeof value === 'string' ? value.trim() : '';
  const leafName = raw.split(/[\\/]+/).filter(Boolean).pop() || 'draft';
  const safeName = leafName === '..' || leafName === '.' ? 'draft' : leafName;
  return extname(safeName).toLowerCase() === '.zip' ? safeName : `${safeName}.zip`;
}

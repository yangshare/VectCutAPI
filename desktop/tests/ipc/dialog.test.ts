import { mkdir, mkdtemp, rm, writeFile } from 'fs/promises';
import os from 'os';
import { join } from 'path';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { showOpenDialogMock } = vi.hoisted(() => ({
  showOpenDialogMock: vi.fn(),
}));

vi.mock('electron', () => ({
  dialog: {
    showOpenDialog: showOpenDialogMock,
  },
}));

import { readZipFile, registerDialogHandlers } from '../../electron/ipc/dialog';

type Handler = (_event?: unknown, ...args: unknown[]) => unknown;

function createFakeIpcMain() {
  const handlers = new Map<string, Handler>();

  return {
    ipcMain: {
      handle: vi.fn((channel: string, handler: Handler) => {
        handlers.set(channel, handler);
      }),
    },
    handlers,
  };
}

describe('registerDialogHandlers', () => {
  beforeEach(() => {
    showOpenDialogMock.mockReset();
  });

  it('registers file and folder dialog channels', () => {
    const { ipcMain } = createFakeIpcMain();

    registerDialogHandlers(ipcMain as never);

    expect(ipcMain.handle).toHaveBeenCalledTimes(6);
    expect(ipcMain.handle.mock.calls.map(([channel]) => channel)).toEqual([
      'dialog:selectVideoFile',
      'dialog:selectAudioFile',
      'dialog:selectImageFile',
      'dialog:selectSrtFile',
      'dialog:selectTemplateFolder',
      'file:readZip',
    ]);
  });

  it.each([
    ['dialog:selectVideoFile', '视频', ['mp4', 'mov', 'avi', 'mkv', 'flv']],
    ['dialog:selectAudioFile', '音频', ['mp3', 'wav', 'aac', 'm4a', 'flac']],
    ['dialog:selectImageFile', '图片', ['jpg', 'jpeg', 'png', 'webp', 'bmp']],
    ['dialog:selectSrtFile', 'SRT 字幕', ['srt', 'txt']],
  ])('opens %s with the expected file filter', async (channel, name, extensions) => {
    const { ipcMain, handlers } = createFakeIpcMain();
    const selectedPath = join(os.tmpdir(), 'selected-file');
    showOpenDialogMock.mockResolvedValue({ canceled: false, filePaths: [selectedPath] });
    registerDialogHandlers(ipcMain as never);

    await expect(handlers.get(channel)?.()).resolves.toBe(selectedPath);

    expect(showOpenDialogMock).toHaveBeenCalledWith({
      title: `选择${name}`,
      properties: ['openFile'],
      filters: [{ name, extensions }],
    });
  });

  it('returns null when a file dialog is canceled', async () => {
    const { ipcMain, handlers } = createFakeIpcMain();
    showOpenDialogMock.mockResolvedValue({ canceled: true, filePaths: [] });
    registerDialogHandlers(ipcMain as never);

    await expect(handlers.get('dialog:selectVideoFile')?.()).resolves.toBeNull();
  });

  it('opens the template folder dialog and returns the first selected folder', async () => {
    const { ipcMain, handlers } = createFakeIpcMain();
    const selectedPath = join(os.tmpdir(), 'template-folder');
    showOpenDialogMock.mockResolvedValue({ canceled: false, filePaths: [selectedPath] });
    registerDialogHandlers(ipcMain as never);

    await expect(handlers.get('dialog:selectTemplateFolder')?.()).resolves.toBe(selectedPath);

    expect(showOpenDialogMock).toHaveBeenCalledWith({
      title: '选择母版草稿文件夹',
      properties: ['openDirectory'],
    });
  });

  it('returns null when the template folder dialog has no selection', async () => {
    const { ipcMain, handlers } = createFakeIpcMain();
    showOpenDialogMock.mockResolvedValue({ canceled: false, filePaths: [] });
    registerDialogHandlers(ipcMain as never);

    await expect(handlers.get('dialog:selectTemplateFolder')?.()).resolves.toBeNull();
  });
});

describe('readZipFile', () => {
  let tempDir: string;

  beforeEach(async () => {
    tempDir = await mkdtemp(join(os.tmpdir(), 'dialog-read-zip-'));
  });

  afterEach(async () => {
    await rm(tempDir, { recursive: true, force: true });
  });

  it.each(['', '   ', null, { path: 'draft.zip' }])(
    'rejects an invalid zip path before reading %#',
    async (filePath) => {
      await expect(readZipFile(filePath as unknown as string)).rejects.toThrow(
        'ZIP 文件路径不能为空',
      );
    },
  );

  it('rejects a non-existent zip file with a clear message', async () => {
    const filePath = join(tempDir, 'missing.zip');

    await expect(readZipFile(filePath)).rejects.toThrow(`ZIP 文件不存在：${filePath}`);
  });

  it('rejects a directory path', async () => {
    const filePath = join(tempDir, 'draft.zip');
    await mkdir(filePath);

    await expect(readZipFile(filePath)).rejects.toThrow(`ZIP 路径不是文件：${filePath}`);
  });

  it('rejects a non-zip file before reading', async () => {
    const filePath = join(tempDir, 'draft.txt');
    await writeFile(filePath, 'not a zip');

    await expect(readZipFile(filePath)).rejects.toThrow('仅支持 .zip 文件');
  });

  it('rejects files larger than the size limit', async () => {
    const filePath = join(tempDir, 'draft.zip');
    await writeFile(filePath, Buffer.from([1, 2, 3, 4]));

    await expect(readZipFile(filePath, 3)).rejects.toThrow('ZIP 文件过大');
  });

  it('returns a Buffer for a valid zip file', async () => {
    const filePath = join(tempDir, 'draft.zip');
    await writeFile(filePath, Buffer.from([0x50, 0x4b, 1, 2]));

    const result = await readZipFile(filePath);

    expect(Buffer.isBuffer(result)).toBe(true);
    expect([...result]).toEqual([0x50, 0x4b, 1, 2]);
  });

  it('routes file:readZip through the zip reader', async () => {
    const { ipcMain, handlers } = createFakeIpcMain();
    const filePath = join(tempDir, 'draft.zip');
    await writeFile(filePath, Buffer.from([0x50, 0x4b]));
    registerDialogHandlers(ipcMain as never);

    const result = await handlers.get('file:readZip')?.(undefined, filePath);

    expect(Buffer.isBuffer(result)).toBe(true);
    expect([...Buffer.from(result as Buffer)]).toEqual([0x50, 0x4b]);
  });
});

import { mkdir, mkdtemp, readFile, rm, symlink, writeFile } from 'fs/promises';
import os from 'os';
import { join } from 'path';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const { showOpenDialogMock, showSaveDialogMock } = vi.hoisted(() => ({
  showOpenDialogMock: vi.fn(),
  showSaveDialogMock: vi.fn(),
}));

vi.mock('electron', () => ({
  dialog: {
    showOpenDialog: showOpenDialogMock,
    showSaveDialog: showSaveDialogMock,
  },
}));

import {
  readZipFile,
  registerDialogHandlers,
  selectJianyingDraftDir,
  selectDraftSavePath,
  writeZipFile,
} from '../../electron/ipc/dialog';

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
    showSaveDialogMock.mockReset();
  });

  it('registers file and folder dialog channels', () => {
    const { ipcMain } = createFakeIpcMain();

    registerDialogHandlers(ipcMain as never);

    expect(ipcMain.handle).toHaveBeenCalledTimes(9);
    expect(ipcMain.handle.mock.calls.map(([channel]) => channel)).toEqual([
      'dialog:selectVideoFile',
      'dialog:selectAudioFile',
      'dialog:selectImageFile',
      'dialog:selectSrtFile',
      'dialog:selectTemplateFolder',
      'dialog:selectJianyingDraftDir',
      'dialog:selectDraftSavePath',
      'file:readZip',
      'file:writeZip',
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

  it('opens the Jianying draft root dialog with a clear title', async () => {
    const { ipcMain, handlers } = createFakeIpcMain();
    const selectedPath = join(os.tmpdir(), 'jianying-draft-root');
    showOpenDialogMock.mockResolvedValue({ canceled: false, filePaths: [selectedPath] });
    registerDialogHandlers(ipcMain as never);

    await expect(handlers.get('dialog:selectJianyingDraftDir')?.()).resolves.toBe(selectedPath);

    expect(showOpenDialogMock).toHaveBeenCalledWith({
      title: '选择剪映草稿根目录',
      properties: ['openDirectory'],
    });
  });

  it('returns null when the Jianying draft root dialog is canceled', async () => {
    showOpenDialogMock.mockResolvedValue({ canceled: true, filePaths: [] });

    await expect(selectJianyingDraftDir()).resolves.toBeNull();
  });

  it('opens the draft save dialog with a sanitized zip filename and authorizes the selected path', async () => {
    const { ipcMain, handlers } = createFakeIpcMain();
    const savePath = join(os.tmpdir(), 'selected-draft.zip');
    showSaveDialogMock.mockResolvedValue({ canceled: false, filePath: savePath });
    registerDialogHandlers(ipcMain as never);

    await expect(handlers.get('dialog:selectDraftSavePath')?.(undefined, '..\\bad/name')).resolves
      .toBe(savePath);

    expect(showSaveDialogMock).toHaveBeenCalledWith({
      title: '保存草稿 ZIP',
      defaultPath: 'name.zip',
      filters: [{ name: 'ZIP 文件', extensions: ['zip'] }],
    });
  });

  it('returns null when the draft save dialog is canceled', async () => {
    const { ipcMain, handlers } = createFakeIpcMain();
    showSaveDialogMock.mockResolvedValue({ canceled: true });
    registerDialogHandlers(ipcMain as never);

    await expect(handlers.get('dialog:selectDraftSavePath')?.(undefined, 'draft')).resolves
      .toBeNull();
  });

  it.each(['', '   ', null])('rejects an invalid suggested draft name %#', async (suggestedName) => {
    await expect(selectDraftSavePath(suggestedName as unknown as string)).rejects.toThrow(
      '草稿文件名不能为空',
    );
    expect(showSaveDialogMock).not.toHaveBeenCalled();
  });
});

describe('writeZipFile', () => {
  let tempDir: string;

  beforeEach(async () => {
    tempDir = await mkdtemp(join(os.tmpdir(), 'dialog-write-zip-'));
  });

  afterEach(async () => {
    await rm(tempDir, { recursive: true, force: true });
  });

  it('rejects unauthorized save paths', async () => {
    const filePath = join(tempDir, 'draft.zip');
    const data = new Uint8Array([0x50, 0x4b, 1, 2]).buffer;

    await expect(writeZipFile(filePath, data)).rejects.toThrow('ZIP 保存路径未授权');
  });

  it('writes ArrayBuffer zip data after save dialog authorization and consumes the authorization', async () => {
    const filePath = join(tempDir, 'draft.zip');
    const data = new Uint8Array([0x50, 0x4b, 1, 2]).buffer;
    showSaveDialogMock.mockResolvedValue({ canceled: false, filePath });

    await selectDraftSavePath('draft.zip');
    await writeZipFile(filePath, data);

    await expect(readFile(filePath)).resolves.toEqual(Buffer.from([0x50, 0x4b, 1, 2]));
    await expect(writeZipFile(filePath, data)).rejects.toThrow('ZIP 保存路径未授权');
  });

  it.each(['', '   ', null, { path: 'draft.zip' }])(
    'rejects an invalid save path before writing %#',
    async (savePath) => {
      await expect(writeZipFile(savePath as unknown as string, new ArrayBuffer(0))).rejects.toThrow(
        'ZIP 保存路径不能为空',
      );
    },
  );

  it('rejects a non-zip save path before writing', async () => {
    const filePath = join(tempDir, 'draft.txt');

    await expect(writeZipFile(filePath, new ArrayBuffer(0))).rejects.toThrow('仅支持 .zip 文件');
  });

  it('rejects data larger than the size limit', async () => {
    const filePath = join(tempDir, 'draft.zip');

    await expect(writeZipFile(filePath, new Uint8Array([1, 2, 3, 4]), 3)).rejects.toThrow(
      'ZIP 文件过大',
    );
  });

  it.each([null, 'zip', { bytes: [1, 2] }])('rejects invalid zip data %#', async (data) => {
    const filePath = join(tempDir, 'draft.zip');

    await expect(writeZipFile(filePath, data as never)).rejects.toThrow('ZIP 数据无效');
  });

  it('rejects symbolic link save paths and consumes the authorization', async () => {
    const realPath = join(tempDir, 'real.zip');
    const linkPath = join(tempDir, 'link.zip');
    await writeFile(realPath, Buffer.from([]));
    await symlink(realPath, linkPath);
    showSaveDialogMock.mockResolvedValue({ canceled: false, filePath: linkPath });

    await selectDraftSavePath('link.zip');
    await expect(writeZipFile(linkPath, new ArrayBuffer(0))).rejects.toThrow(
      'ZIP 保存路径不能是符号链接',
    );
    await expect(writeZipFile(linkPath, new ArrayBuffer(0))).rejects.toThrow(
      'ZIP 保存路径未授权',
    );
  });

  it('routes file:writeZip through the zip writer', async () => {
    const { ipcMain, handlers } = createFakeIpcMain();
    const filePath = join(tempDir, 'draft.zip');
    const data = new Uint8Array([0x50, 0x4b]).buffer;
    showSaveDialogMock.mockResolvedValue({ canceled: false, filePath });
    registerDialogHandlers(ipcMain as never);

    await handlers.get('dialog:selectDraftSavePath')?.(undefined, 'draft.zip');
    await handlers.get('file:writeZip')?.(undefined, filePath, data);

    await expect(readFile(filePath)).resolves.toEqual(Buffer.from([0x50, 0x4b]));
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

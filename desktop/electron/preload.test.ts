import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { beforeEach, describe, expect, test, vi } from 'vitest';

const electronMock = vi.hoisted(() => ({
  exposeInMainWorld: vi.fn(),
  invoke: vi.fn(),
}));

vi.mock('electron', () => ({
  contextBridge: {
    exposeInMainWorld: electronMock.exposeInMainWorld,
  },
  ipcRenderer: {
    invoke: electronMock.invoke,
  },
}));

describe('preload controlled IPC API', () => {
  const ipcCases = [
    {
      method: 'selectVideoFile',
      args: [],
      expectedInvokeArgs: ['dialog:selectVideoFile'],
    },
    {
      method: 'selectAudioFile',
      args: [],
      expectedInvokeArgs: ['dialog:selectAudioFile'],
    },
    {
      method: 'selectImageFile',
      args: [],
      expectedInvokeArgs: ['dialog:selectImageFile'],
    },
    {
      method: 'selectSrtFile',
      args: [],
      expectedInvokeArgs: ['dialog:selectSrtFile'],
    },
    {
      method: 'selectTemplateFolder',
      args: [],
      expectedInvokeArgs: ['dialog:selectTemplateFolder'],
    },
    {
      method: 'selectJianyingDraftDir',
      args: [],
      expectedInvokeArgs: ['dialog:selectJianyingDraftDir'],
    },
    {
      method: 'selectDraftSavePath',
      args: ['draft-name'],
      expectedInvokeArgs: ['dialog:selectDraftSavePath', 'draft-name'],
    },
    {
      method: 'probeMedia',
      args: ['C:/media/video.mp4'],
      expectedInvokeArgs: ['mediaProbe:probe', 'C:/media/video.mp4'],
    },
    {
      method: 'detectJianyingDraftDir',
      args: [],
      expectedInvokeArgs: ['jianying:detectDraftDir'],
    },
    {
      method: 'detectJianyingVersion',
      args: [],
      expectedInvokeArgs: ['jianying:detectVersion'],
    },
    {
      method: 'importDraftToJianying',
      args: ['C:/drafts/import.zip'],
      expectedInvokeArgs: ['jianying:importDraft', 'C:/drafts/import.zip'],
    },
    {
      method: 'packTemplateFolder',
      args: ['C:/templates/template-a'],
      expectedInvokeArgs: ['packer:pack', 'C:/templates/template-a'],
    },
    {
      method: 'readZipFile',
      args: ['C:/templates/template-a.zip'],
      expectedInvokeArgs: ['file:readZip', 'C:/templates/template-a.zip'],
    },
    {
      method: 'readTextFile',
      args: ['C:/subtitles/intro.srt'],
      expectedInvokeArgs: ['file:readText', 'C:/subtitles/intro.srt'],
    },
    {
      method: 'writeZipFile',
      args: ['C:/downloads/draft.zip', new ArrayBuffer(2)],
      expectedInvokeArgs: ['file:writeZip', 'C:/downloads/draft.zip', new ArrayBuffer(2)],
    },
    {
      method: 'getUserConfig',
      args: [],
      expectedInvokeArgs: ['config:get'],
    },
    {
      method: 'setUserConfig',
      args: [{ serverUrl: 'http://localhost:8000' }],
      expectedInvokeArgs: ['config:set', { serverUrl: 'http://localhost:8000' }],
    },
  ];

  beforeEach(() => {
    vi.resetModules();
    electronMock.exposeInMainWorld.mockClear();
    electronMock.invoke.mockReset();
  });

  test('exposes only the vectcut API surface', async () => {
    await import('./preload');

    expect(electronMock.exposeInMainWorld).toHaveBeenCalledOnce();
    const [name, api] = electronMock.exposeInMainWorld.mock.calls[0];

    expect(name).toBe('vectcut');
    expect(Object.keys(api).sort()).toEqual([
      'detectJianyingDraftDir',
      'detectJianyingVersion',
      'getUserConfig',
      'importDraftToJianying',
      'packTemplateFolder',
      'probeMedia',
      'readTextFile',
      'readZipFile',
      'selectAudioFile',
      'selectImageFile',
      'selectJianyingDraftDir',
      'selectSrtFile',
      'selectTemplateFolder',
      'selectVideoFile',
      'setUserConfig',
      'selectDraftSavePath',
      'writeZipFile',
    ].sort());
    expect(api).not.toHaveProperty('ipcRenderer');
  });

  test.each(ipcCases)('$method routes to the expected IPC channel', async ({ method, args, expectedInvokeArgs }) => {
    electronMock.invoke.mockResolvedValue(new ArrayBuffer(0));
    await import('./preload');
    const [, api] = electronMock.exposeInMainWorld.mock.calls[0];

    await api[method](...args);

    expect(electronMock.invoke).toHaveBeenCalledOnce();
    expect(electronMock.invoke).toHaveBeenCalledWith(...expectedInvokeArgs);
  });

  test('converts file:readZip byte data to ArrayBuffer before exposing it', async () => {
    electronMock.invoke.mockResolvedValue(new Uint8Array([1, 2, 3, 4]).subarray(1, 3));
    await import('./preload');
    const [, api] = electronMock.exposeInMainWorld.mock.calls[0];

    const result = await api.readZipFile('C:/templates/template-a.zip');

    expect(result).toBeInstanceOf(ArrayBuffer);
    expect(Array.from(new Uint8Array(result))).toEqual([2, 3]);
    expect(electronMock.invoke).toHaveBeenCalledWith('file:readZip', 'C:/templates/template-a.zip');
  });

  test('rejects oversized zip writes before invoking IPC', async () => {
    await import('./preload');
    const [, api] = electronMock.exposeInMainWorld.mock.calls[0];
    const oversized = new ArrayBuffer(100 * 1024 * 1024 + 1);

    await expect(api.writeZipFile('C:/downloads/draft.zip', oversized)).rejects.toThrow(
      'ZIP 文件过大',
    );
    expect(electronMock.invoke).not.toHaveBeenCalled();
  });

  test('renderer global types depend on shared types, not electron preload', () => {
    const globalTypes = readFileSync(resolve(__dirname, '../src/global.d.ts'), 'utf8');

    expect(globalTypes).toContain("from './types'");
    expect(globalTypes).not.toContain('../electron/preload');
  });
});

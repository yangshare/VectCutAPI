import { contextBridge, ipcRenderer } from 'electron';
import type {
  VectCutApi,
  ProbeResult,
  UserConfig,
} from '../src/types';

const MAX_ZIP_BYTES = 100 * 1024 * 1024;

const toArrayBuffer = (value: ArrayBuffer | Uint8Array): ArrayBuffer => {
  if (value instanceof ArrayBuffer) {
    return value;
  }

  const buffer = new ArrayBuffer(value.byteLength);
  new Uint8Array(buffer).set(value);
  return buffer;
};

const api: VectCutApi = {
  // 文件/文件夹选择（dialog.ts）
  selectVideoFile: () => ipcRenderer.invoke('dialog:selectVideoFile') as Promise<string | null>,
  selectVideoFiles: () => ipcRenderer.invoke('dialog:selectVideoFiles') as Promise<string[]>,
  selectVideoDirectory: () => ipcRenderer.invoke('dialog:selectVideoDirectory') as Promise<{
    directory: string;
    files: string[];
  } | null>,
  selectAudioFile: () => ipcRenderer.invoke('dialog:selectAudioFile') as Promise<string | null>,
  selectImageFile: () => ipcRenderer.invoke('dialog:selectImageFile') as Promise<string | null>,
  selectSrtFile: () => ipcRenderer.invoke('dialog:selectSrtFile') as Promise<string | null>,
  selectTemplateFolder: () => ipcRenderer.invoke('dialog:selectTemplateFolder') as Promise<string | null>,
  selectJianyingDraftDir: () =>
    ipcRenderer.invoke('dialog:selectJianyingDraftDir') as Promise<string | null>,
  selectDraftSavePath: (suggestedName: string) =>
    ipcRenderer.invoke('dialog:selectDraftSavePath', suggestedName) as Promise<string | null>,

  // 媒体探测（mediaProbe.ts）
  probeMedia: (filePath: string) =>
    ipcRenderer.invoke('mediaProbe:probe', filePath) as Promise<ProbeResult>,

  // 剪映目录（jianyingDir.ts）
  detectJianyingDraftDir: () =>
    ipcRenderer.invoke('jianying:detectDraftDir') as Promise<string | null>,
  detectJianyingVersion: () =>
    ipcRenderer.invoke('jianying:detectVersion') as Promise<string | null>,
  importDraftToJianying: (zipPath: string) =>
    ipcRenderer.invoke('jianying:importDraft', zipPath) as Promise<{ draftDir: string }>,

  // 母版打包（packer.ts）
  packTemplateFolder: (folderPath: string) =>
    ipcRenderer.invoke('packer:pack', folderPath) as Promise<{ zipPath: string; sizeMB: number }>,
  readDraftContentFile: async (folderPath: string) => {
    const result = await ipcRenderer.invoke('packer:readDraftContent', folderPath) as {
      filePath: string;
      bytes: ArrayBuffer | Uint8Array;
      sizeMB: number;
    };
    return {
      ...result,
      bytes: toArrayBuffer(result.bytes),
    };
  },

  // 主进程 handler 负责 zip 扩展名、大小和路径来源校验。
  readZipFile: async (filePath: string) =>
    toArrayBuffer(await ipcRenderer.invoke('file:readZip', filePath) as ArrayBuffer | Uint8Array),
  readTextFile: (filePath: string) =>
    ipcRenderer.invoke('file:readText', filePath) as Promise<string>,
  writeZipFile: (savePath: string, data: ArrayBuffer) => {
    if (data.byteLength > MAX_ZIP_BYTES) {
      return Promise.reject(new Error('ZIP 文件过大'));
    }
    return ipcRenderer.invoke('file:writeZip', savePath, data) as Promise<void>;
  },

  // 配置存储（configStore.ts）
  getUserConfig: () => ipcRenderer.invoke('config:get') as Promise<UserConfig>,
  setUserConfig: (config: Partial<UserConfig>) =>
    ipcRenderer.invoke('config:set', config) as Promise<UserConfig>,
};

contextBridge.exposeInMainWorld('vectcut', api);

export type { VectCutApi } from '../src/types';

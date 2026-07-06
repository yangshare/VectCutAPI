import { contextBridge, ipcRenderer } from 'electron';
import type {
  VectCutApi,
  ProbeResult,
  UserConfig,
} from '../src/types';

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
  selectAudioFile: () => ipcRenderer.invoke('dialog:selectAudioFile') as Promise<string | null>,
  selectImageFile: () => ipcRenderer.invoke('dialog:selectImageFile') as Promise<string | null>,
  selectSrtFile: () => ipcRenderer.invoke('dialog:selectSrtFile') as Promise<string | null>,
  selectTemplateFolder: () => ipcRenderer.invoke('dialog:selectTemplateFolder') as Promise<string | null>,

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

  // 主进程 handler 负责 zip 扩展名、大小和路径来源校验。
  readZipFile: async (filePath: string) =>
    toArrayBuffer(await ipcRenderer.invoke('file:readZip', filePath) as ArrayBuffer | Uint8Array),

  // 配置存储（configStore.ts）
  getUserConfig: () => ipcRenderer.invoke('config:get') as Promise<UserConfig>,
  setUserConfig: (config: Partial<UserConfig>) =>
    ipcRenderer.invoke('config:set', config) as Promise<void>,
};

contextBridge.exposeInMainWorld('vectcut', api);

export type { VectCutApi } from '../src/types';

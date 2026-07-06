import { contextBridge } from 'electron';

const api = {
  // 任务 2 填充
};

contextBridge.exposeInMainWorld('vectcut', api);

export type VectCutApi = typeof api;

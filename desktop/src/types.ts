/** 槽位（后端 import_template 返回） */
export interface Slot {
  slot_id: string;
  type: 'video' | 'audio' | 'bgm' | 'subtitle';
  track_name: string;
  segment_index: number;
}

/** 素材元数据（客户端采集，提交云端） */
export interface MaterialMetadata {
  slot_id: string;
  path: string;       // 用户本地绝对路径
  duration?: number;  // 秒（视频/音频）
  width?: number;     // 图片/视频宽度
  height?: number;    // 图片/视频高度
}

/** 字幕元数据 */
export interface SubtitleMetadata {
  slot_id: string;
  srt_content: string;
}

/** 封面标题元数据 */
export interface CoverTitleMetadata {
  slot_id: string;
  text: string;
}

/** 槽位配置（保存到云端） */
export interface SlotMapping {
  slot_id: string;
  type: Slot['type'];
  track_name: string;
  segment_index: number;
}

/** 后端统一响应信封 */
export interface ApiEnvelope<T> {
  success: boolean;
  output: T | null;
  error: { code: string; message: string; details?: Record<string, unknown> } | string | null;
}

/** 媒体探测结果（IPC 返回） */
export interface ProbeResult {
  duration: number;
  width?: number;
  height?: number;
}

/** 用户配置（持久化到 ~/.vectcut/config.json） */
export interface UserConfig {
  serverUrl?: string;
  jianyingDraftDir?: string;
}

/** 受控 preload API（渲染进程公开契约） */
export interface VectCutApi {
  selectVideoFile: () => Promise<string | null>;
  selectAudioFile: () => Promise<string | null>;
  selectImageFile: () => Promise<string | null>;
  selectSrtFile: () => Promise<string | null>;
  selectTemplateFolder: () => Promise<string | null>;
  selectJianyingDraftDir: () => Promise<string | null>;
  selectDraftSavePath: (suggestedName: string) => Promise<string | null>;
  probeMedia: (filePath: string) => Promise<ProbeResult>;
  detectJianyingDraftDir: () => Promise<string | null>;
  detectJianyingVersion: () => Promise<string | null>;
  importDraftToJianying: (zipPath: string) => Promise<{ draftDir: string }>;
  packTemplateFolder: (folderPath: string) => Promise<{ zipPath: string; sizeMB: number }>;
  readZipFile: (filePath: string) => Promise<ArrayBuffer>;
  writeZipFile: (savePath: string, data: ArrayBuffer) => Promise<void>;
  getUserConfig: () => Promise<UserConfig>;
  setUserConfig: (config: Partial<UserConfig>) => Promise<UserConfig>;
}

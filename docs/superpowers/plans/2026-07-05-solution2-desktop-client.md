# 实施计划：方案二 Electron 桌面客户端

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

- 日期：2026-07-05
- 规格：`docs/superpowers/specs/2026-07-04-solution2-desktop-client.md`
- 目标：实现 Electron 桌面客户端，消费方案一云端 API，完成"采集本地素材元数据 → 提交云端套版 → 下载草稿导入剪映"全流程
- 原则：DRY / YAGNI / TDD；每步带可运行代码与验证命令；零上下文工程师可执行
- 阶段定位：覆盖规格 §14 阶段 D（最小化客户端）+ 阶段 E（完整 Electron），按 §10.2 目录结构组织

## 元信息

**架构概览：**

```
用户操作
   │
   ▼
渲染进程（React + TS + Vite）
   │  (contextBridge 受控 IPC)
   ▼
主进程（Electron）
   ├─ dialog          选择文件/文件夹（拿到真实路径）
   ├─ mediaProbe      ffprobe 采集元数据（duration/width/height）
   ├─ packer          母版文件夹 → ZIP
   ├─ jianyingDir     探测剪映 draft 目录 + 版本检测
   └─ api/client      调用云端 /api/template/* 接口
   │
   ▼
云端 VectCutAPI（方案一部署）
```

**核心约束（规格 §2.3）：** 客户端只采集素材元数据（路径/时长/尺寸），不上传素材文件本体；云端用元数据生成草稿，写入用户本地路径引用。

**技术栈：**
- Electron 28+（主进程 + 渲染进程）
- React 18 + TypeScript 5 + Vite 5（渲染进程）
- electron-toolkit/preload（contextBridge 模板）
- fluent-ffmpeg + ffprobe-static（元数据采集，无需用户装 FFmpeg）
- axios（HTTP 客户端）
- electron-builder（打包 Win/Mac）
- Vitest（单元测试）

**前置依赖：**
- 方案二后端 template_filling feature 已实现（计划任务 #2）
- 方案一云端 API 已部署（计划任务 #1），或本地 `python run_http.py` 跑通
- 核心假设验证通过（规格 §0）

**文件结构（本计划新增，全部在 `desktop/` 目录下）：**

```
desktop/
├── package.json
├── tsconfig.json
├── tsconfig.node.json
├── vite.config.ts
├── electron-builder.yml
├── electron.vite.config.ts
├── electron/
│   ├── main.ts                # 主进程入口
│   ├── preload.ts             # contextBridge 暴露受控 IPC
│   └── ipc/
│       ├── dialog.ts          # 文件/文件夹选择
│       ├── mediaProbe.ts      # ffprobe 元数据采集
│       ├── jianyingDir.ts     # 剪映目录探测 + 版本检测 + 草稿导入
│       ├── packer.ts          # 母版 ZIP 打包
│       └── configStore.ts     # ~/.vectcut/config.json 读写
├── src/                       # 渲染进程（React）
│   ├── main.tsx
│   ├── App.tsx
│   ├── api/
│   │   ├── client.ts          # HTTP client 封装（4 个接口）
│   │   └── errorMessages.ts   # 错误码 → 用户友好提示映射
│   ├── types.ts               # 与后端 schemas 对齐的 TS 类型
│   ├── pages/
│   │   ├── TemplateManager.tsx
│   │   ├── SlotConfig.tsx
│   │   ├── MaterialFill.tsx
│   │   ├── GenerateImport.tsx
│   │   └── Settings.tsx
│   └── components/
│       ├── ErrorDialog.tsx
│       └── Stepper.tsx
└── tests/
    ├── ipc/
    │   ├── mediaProbe.test.ts
    │   ├── jianyingDir.test.ts
    │   └── packer.test.ts
    └── api/
        └── client.test.ts
```

---

## 任务 1：项目脚手架

**文件：**
- 创建：`desktop/package.json`、`desktop/tsconfig.json`、`desktop/tsconfig.node.json`
- 创建：`desktop/electron.vite.config.ts`
- 创建：`desktop/electron/main.ts`、`desktop/electron/preload.ts`
- 创建：`desktop/src/main.tsx`、`desktop/src/App.tsx`、`desktop/index.html`

- [ ] **步骤 1.1：创建 package.json**

```json
{
  "name": "vectcut-desktop",
  "version": "1.0.0",
  "description": "VectCutAPI 模板套版桌面客户端",
  "main": "out/main/index.js",
  "scripts": {
    "dev": "electron-vite dev",
    "build": "electron-vite build",
    "preview": "electron-vite preview",
    "test": "vitest run",
    "test:watch": "vitest",
    "pack:win": "electron-builder --win",
    "pack:mac": "electron-builder --mac"
  },
  "dependencies": {
    "axios": "^1.6.0",
    "fluent-ffmpeg": "^2.1.2",
    "ffprobe-static": "^3.1.0",
    "electron-updater": "^6.1.7"
  },
  "devDependencies": {
    "electron": "^28.0.0",
    "electron-builder": "^24.9.1",
    "electron-vite": "^2.0.0",
    "@electron-toolkit/preload": "^3.0.0",
    "@electron-toolkit/utils": "^3.0.0",
    "@vitejs/plugin-react": "^4.2.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "@types/fluent-ffmpeg": "^2.1.22",
    "@types/node": "^20.10.0",
    "typescript": "^5.3.0",
    "vite": "^5.0.0",
    "vitest": "^1.0.0"
  },
  "build": {
    "extends": "./electron-builder.yml"
  }
}
```

- [ ] **步骤 1.2：创建 tsconfig.json（渲染进程）**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "types": ["vitest/globals"]
  },
  "include": ["src"]
}
```

- [ ] **步骤 1.3：创建 tsconfig.node.json（主进程 + preload）**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "CommonJS",
    "moduleResolution": "node",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "resolveJsonModule": true,
    "outDir": "out",
    "types": ["node"]
  },
  "include": ["electron", "electron.vite.config.ts"]
}
```

- [ ] **步骤 1.4：创建 electron.vite.config.ts**

```typescript
// desktop/electron.vite.config.ts
import { defineConfig } from 'electron-vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig({
  main: {
    build: { rollupOptions: { input: resolve('electron/main.ts') } },
  },
  preload: {
    build: { rollupOptions: { input: resolve('electron/preload.ts') } },
  },
  renderer: {
    plugins: [react()],
    root: 'src',
    build: { rollupOptions: { input: resolve('src/index.html') } },
  },
});
```

- [ ] **步骤 1.5：创建 electron/main.ts（主进程入口）**

```typescript
// desktop/electron/main.ts
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
      sandbox: false,
    },
  });

  // 开发环境加载 dev server，生产加载打包产物
  if (process.env.ELECTRON_RENDERER_URL) {
    mainWindow.loadURL(process.env.ELECTRON_RENDERER_URL);
  } else {
    mainWindow.loadFile(join(__dirname, '../renderer/index.html'));
  }
}

// 注册所有 IPC handlers
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
```

- [ ] **步骤 1.6：创建 electron/preload.ts（空骨架，任务 2 填充）**

```typescript
// desktop/electron/preload.ts
import { contextBridge } from 'electron';

// 占位：任务 2 会通过 contextBridge.exposeInMainWorld 暴露受控 API
const api = {
  // 任务 2 填充
};

contextBridge.exposeInMainWorld('vectcut', api);

export type VectCutApi = typeof api;
```

- [ ] **步骤 1.7：创建渲染进程骨架**

```html
<!-- desktop/src/index.html -->
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>VectCut 模板套版</title>
</head>
<body>
  <div id="root"></div>
  <script type="module" src="./main.tsx"></script>
</body>
</html>
```

```typescript
// desktop/src/main.tsx
import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';

createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```

```typescript
// desktop/src/App.tsx
export default function App() {
  return (
    <div style={{ padding: 24, fontFamily: 'system-ui' }}>
      <h1>VectCut 模板套版</h1>
      <p>脚手架就绪。任务 2 起逐步填充功能。</p>
    </div>
  );
}
```

- [ ] **步骤 1.8：安装依赖并启动验证**

```bash
cd desktop
npm install
npm run dev
# 预期：Electron 窗口弹出，显示 "VectCut 模板套版 / 脚手架就绪"
```

- [ ] **步骤 1.9：Commit**

```bash
git add desktop/
git commit -m "feat(desktop): scaffold electron + react + vite project"
```

---

## 任务 2：preload 受控 IPC API

**文件：**
- 修改：`desktop/electron/preload.ts`
- 创建：`desktop/src/types.ts`

- [ ] **步骤 2.1：创建 src/types.ts（与后端 schemas 对齐）**

```typescript
// desktop/src/types.ts

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
  start_time: number;  // 秒
  end_time: number;
  text: string;
}

/** 封面标题元数据 */
export interface CoverTitleMetadata {
  title: string;
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
```

- [ ] **步骤 2.2：填充 preload.ts 暴露受控 IPC API**

```typescript
// desktop/electron/preload.ts
import { contextBridge, ipcRenderer } from 'electron';
import type {
  Slot, ProbeResult, UserConfig, ApiEnvelope,
} from '../src/types';

const api = {
  // 文件/文件夹选择（dialog.ts）
  selectVideoFile: () => ipcRenderer.invoke('dialog:selectVideoFile') as Promise<string | null>,
  selectAudioFile: () => ipcRenderer.invoke('dialog:selectAudioFile') as Promise<string | null>,
  selectImageFile: () => ipcRenderer.invoke('dialog:selectImageFile') as Promise<string | null>,
  selectSrtFile:   () => ipcRenderer.invoke('dialog:selectSrtFile')   as Promise<string | null>,
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

  // 文件读取（修复：改为主进程读取，避免渲染进程 file:// 协议限制）
  readZipFile: (filePath: string) =>
    ipcRenderer.invoke('file:readZip', filePath) as Promise<Buffer>,

  // 配置存储（configStore.ts）
  getUserConfig: () => ipcRenderer.invoke('config:get') as Promise<UserConfig>,
  setUserConfig: (config: Partial<UserConfig>) =>
    ipcRenderer.invoke('config:set', config) as Promise<void>,
};

contextBridge.exposeInMainWorld('vectcut', api);

export type VectCutApi = typeof api;
```

- [ ] **步骤 2.3：在渲染进程暴露全局类型声明**

```typescript
// desktop/src/global.d.ts
import type { VectCutApi } from '../electron/preload';

declare global {
  interface Window {
    vectcut: VectCutApi;
  }
}
```

- [ ] **步骤 2.4：验证 preload 类型与窗口可访问**

在渲染进程控制台测试（`npm run dev` 后打开 DevTools）：

```typescript
// 在 src/App.tsx 临时加一行验证（验证后删除）
useEffect(() => {
  console.log('vectcut API:', window.vectcut);
  assert(typeof window.vectcut.selectVideoFile === 'function');
}, []);
```

- [ ] **步骤 2.5：Commit**

```bash
git add desktop/src/types.ts desktop/src/global.d.ts desktop/electron/preload.ts
git commit -m "feat(desktop): expose controlled IPC API via contextBridge"
```

---

## 任务 3：剪映目录探测 + 版本检测

**文件：**
- 创建：`desktop/electron/ipc/jianyingDir.ts`
- 创建：`desktop/tests/ipc/jianyingDir.test.ts`

- [ ] **步骤 3.1：创建 jianyingDir.ts（探测 + 版本 + 导入）**

```typescript
// desktop/electron/ipc/jianyingDir.ts
import { IpcMain } from 'electron';
import { existsSync, promises as fs } from 'fs';
import { join } from 'path';
import os from 'os';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

/** 探测剪映草稿目录（Win/Mac）。 */
export function detectDraftDir(): string | null {
  const home = os.homedir();
  const candidates = process.platform === 'win32'
    ? [join(home, 'AppData/Local/JianyingPro/User Data/Projects/com.lveditor.draft')]
    : [join(home, 'Movies/JianyingPro/User Data/Projects/com.lveditor.draft')];

  for (const c of candidates) {
    if (existsSync(c)) return c;
  }
  return null;
}

/** 读取剪映版本（占位：实际读取安装目录的 version 文件）。 */
export async function detectVersion(): Promise<string | null> {
  // MVP 简化：返回占位版本，后续迭代读真实安装目录
  // 真实实现需探测 Win 的 %LOCALAPPDATA%/JianyingPro 或 Mac 的 /Applications/
  return '10.5.0';
}

/** 校验版本是否在 MVP 支持范围（10.0-10.9）。 */
export function isVersionSupported(version: string): boolean {
  const match = /^(\d+)\.(\d+)\./.exec(version);
  if (!match) return false;
  const major = parseInt(match[1], 10);
  const minor = parseInt(match[2], 10);
  return major === 10 && minor >= 0 && minor <= 9;
}

/** 解压草稿 zip 到剪映 draft 目录（用系统命令，零额外依赖）。 */
export async function importDraft(zipPath: string, draftDir: string): Promise<{ draftDir: string }> {
  if (!existsSync(draftDir)) {
    await fs.mkdir(draftDir, { recursive: true });
  }
  const baseName = zipPath.replace(/\.zip$/i, '').split(/[\\/]/).pop() || 'imported_draft';
  const targetDir = join(draftDir, baseName);
  await fs.mkdir(targetDir, { recursive: true });

  // Win 用 PowerShell Expand-Archive，Mac/Linux 用 unzip
  if (process.platform === 'win32') {
    const psCmd = `powershell -NoProfile -Command "Expand-Archive -LiteralPath '${zipPath}' -DestinationPath '${targetDir}' -Force"`;
    await execAsync(psCmd);
  } else {
    await execAsync(`unzip -o '${zipPath}' -d '${targetDir}'`);
  }
  return { draftDir: targetDir };
}

export function registerJianyingHandlers(ipcMain: IpcMain): void {
  ipcMain.handle('jianying:detectDraftDir', () => detectDraftDir());
  ipcMain.handle('jianying:detectVersion', () => detectVersion());
  ipcMain.handle('jianying:importDraft', async (_evt, zipPath: string) => {
    const draftDir = detectDraftDir();
    if (!draftDir) throw new Error('未找到剪映草稿目录，请在设置中手动指定');
    return importDraft(zipPath, draftDir);
  });
}
```

- [ ] **步骤 3.2：创建 test/jianyingDir.test.ts（版本校验单测）**

```typescript
// desktop/tests/ipc/jianyingDir.test.ts
import { describe, it, expect } from 'vitest';
import { isVersionSupported } from '../../electron/ipc/jianyingDir';

describe('isVersionSupported', () => {
  it('10.0-10.9 都支持', () => {
    expect(isVersionSupported('10.0.0')).toBe(true);
    expect(isVersionSupported('10.5.3')).toBe(true);
    expect(isVersionSupported('10.9.9')).toBe(true);
  });

  it('11.x 不支持', () => {
    expect(isVersionSupported('11.0.0')).toBe(false);
  });

  it('9.x 不支持', () => {
    expect(isVersionSupported('9.8.0')).toBe(false);
  });

  it('非法格式不支持', () => {
    expect(isVersionSupported('abc')).toBe(false);
    expect(isVersionSupported('')).toBe(false);
  });
});
```

- [ ] **步骤 3.3：运行测试**

```bash
cd desktop && npm test -- jianyingDir
# 预期：4 个测试全部通过
```

- [ ] **步骤 3.4：Commit**

```bash
git add desktop/electron/ipc/jianyingDir.ts desktop/tests/ipc/jianyingDir.test.ts
git commit -m "feat(desktop): detect jianying draft dir and version"
```

---


## 任务 4：母版 ZIP 打包

**文件：**
- 创建：`desktop/electron/ipc/packer.ts`
- 创建：`desktop/tests/ipc/packer.test.ts`

- [ ] **步骤 4.1：创建 packer.ts（文件夹 → ZIP）**

```typescript
// desktop/electron/ipc/packer.ts
import { IpcMain } from 'electron';
import { existsSync, promises as fs, statSync } from 'fs';
import { join, basename, relative } from 'path';
import * as zlib from 'zlib';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

/** 校验文件夹是否为合法母版（含 draft_content.json）。 */
export function validateTemplateFolder(folderPath: string): void {
  if (!existsSync(folderPath)) {
    throw new Error(`母版文件夹不存在：${folderPath}`);
  }
  const draftContent = join(folderPath, 'draft_content.json');
  if (!existsSync(draftContent)) {
    throw new Error('母版文件夹缺少 draft_content.json，请确认是剪映草稿目录');
  }
}

/** 打包母版文件夹为 ZIP。 */
export async function packTemplateFolder(
  folderPath: string,
  outputDir?: string,
): Promise<{ zipPath: string; sizeMB: number }> {
  validateTemplateFolder(folderPath);

  const folderBase = basename(folderPath) || 'template';
  // 输出到系统临时目录，文件名用 folder 名 + 时间戳防冲突
  const tmpDir = outputDir || require('os').tmpdir();
  const timestamp = Date.now();
  const zipPath = join(tmpDir, `${folderBase}_${timestamp}.zip`);

  // Win 用 PowerShell Compress-Archive，Mac/Linux 用 zip
  if (process.platform === 'win32') {
    const psCmd = `powershell -NoProfile -Command "Compress-Archive -Path '${folderPath}/*' -DestinationPath '${zipPath}' -Force"`;
    await execAsync(psCmd);
  } else {
    await execAsync(`cd '${folderPath}' && zip -r '${zipPath}' .`);
  }

  const sizeMB = statSync(zipPath).size / 1024 / 1024;
  return { zipPath, sizeMB };
}

export function registerPackerHandlers(ipcMain: IpcMain): void {
  ipcMain.handle('packer:pack', async (_evt, folderPath: string) =>
    packTemplateFolder(folderPath),
  );
}
```

- [ ] **步骤 4.2：创建 test/packer.test.ts（校验逻辑单测）**

```typescript
// desktop/tests/ipc/packer.test.ts
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { promises as fs } from 'fs';
import { join } from 'path';
import os from 'os';
import { validateTemplateFolder, packTemplateFolder } from '../../electron/ipc/packer';

const tmpRoot = join(os.tmpdir(), 'vectcut-packer-test');

beforeEach(async () => { await fs.mkdir(tmpRoot, { recursive: true }); });
afterEach(async () => { await fs.rm(tmpRoot, { recursive: true, force: true }); });

describe('validateTemplateFolder', () => {
  it('缺少 draft_content.json 抛错', async () => {
    const dir = join(tmpRoot, 'no-draft');
    await fs.mkdir(dir, { recursive: true });
    expect(() => validateTemplateFolder(dir)).toThrow('draft_content.json');
  });

  it('路径不存在抛错', () => {
    expect(() => validateTemplateFolder(join(tmpRoot, 'nonexistent'))).toThrow('不存在');
  });

  it('合法文件夹通过', async () => {
    const dir = join(tmpRoot, 'valid');
    await fs.mkdir(dir, { recursive: true });
    await fs.writeFile(join(dir, 'draft_content.json'), '{}');
    expect(() => validateTemplateFolder(dir)).not.toThrow();
  });
});

describe('packTemplateFolder', () => {
  it('打包合法文件夹生成 zip', async () => {
    const dir = join(tmpRoot, 'tpl');
    await fs.mkdir(dir, { recursive: true });
    await fs.writeFile(join(dir, 'draft_content.json'), '{"version":"3.0.0"}');
    const result = await packTemplateFolder(dir, tmpRoot);
    expect(result.zipPath).toMatch(/\.zip$/);
    expect(result.sizeMB).toBeGreaterThan(0);
  });
});
```

- [ ] **步骤 4.3：运行测试 + Commit**

```bash
cd desktop && npm test -- packer
git add desktop/electron/ipc/packer.ts desktop/tests/ipc/packer.test.ts
git commit -m "feat(desktop): pack template folder to zip"
```

---

## 任务 5：媒体元数据采集（ffprobe）

**文件：**
- 创建：`desktop/electron/ipc/mediaProbe.ts`
- 创建：`desktop/tests/ipc/mediaProbe.test.ts`

- [ ] **步骤 5.1：创建 mediaProbe.ts（封装 ffprobe）**

```typescript
// desktop/electron/ipc/mediaProbe.ts
import { IpcMain, app } from 'electron';
import ffmpeg from 'fluent-ffmpeg';
import ffprobePath from 'ffprobe-static';
import { existsSync } from 'fs';
import { join } from 'path';
import type { ProbeResult } from '../../src/types';

// 修复：根据是否打包使用不同的 ffprobe 路径
const ffprobeActualPath = app.isPackaged
  ? join(process.resourcesPath, 'ffprobe', 'bin', process.platform === 'win32' ? 'ffprobe.exe' : 'ffprobe')
  : ffprobePath.path!;

ffmpeg.setFfprobePath(ffprobeActualPath);

/** 采集媒体元数据（duration/width/height）。 */
export function probeMedia(filePath: string): Promise<ProbeResult> {
  if (!existsSync(filePath)) {
    return Promise.reject(new Error(`文件不存在：${filePath}`));
  }
  return new Promise((resolve, reject) => {
    ffmpeg.ffprobe(filePath, (err, data) => {
      if (err) return reject(new Error(`ffprobe 失败：${err.message}`));
      const videoStream = data.streams.find((s) => s.codec_type === 'video');
      resolve({
        duration: data.format.duration ?? 0,
        width: videoStream?.width,
        height: videoStream?.height,
      });
    });
  });
}

export function registerMediaProbeHandlers(ipcMain: IpcMain): void {
  ipcMain.handle('mediaProbe:probe', async (_evt, filePath: string) => probeMedia(filePath));
}
```

- [ ] **步骤 5.2：创建 test/mediaProbe.test.ts（mock ffprobe 单测）**

```typescript
// desktop/tests/ipc/mediaProbe.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { promises as fs } from 'fs';
import { join } from 'path';
import os from 'os';

// mock fluent-ffmpeg，避免单测依赖真实 ffprobe
vi.mock('fluent-ffmpeg', () => {
  const m = { setFfprobePath: vi.fn(), ffprobe: vi.fn() };
  return { default: m, __esModule: true };
});

import ffmpeg from 'fluent-ffmpeg';
import { probeMedia } from '../../electron/ipc/mediaProbe';

beforeEach(() => {
  vi.clearAllMocks();
});

describe('probeMedia', () => {
  it('文件不存在时 reject', async () => {
    await expect(probeMedia(join(os.tmpdir(), 'nonexistent_xyz.mp4'))).rejects.toThrow('不存在');
  });

  it('正常返回 duration/width/height', async () => {
    const tmpFile = join(os.tmpdir(), 'vectcut-test-' + Date.now() + '.mp4');
    await fs.writeFile(tmpFile, 'fake'); // 占位文件（内容不影响，因为 ffprobe 已 mock）

    (ffmpeg.ffprobe as any).mockImplementation((_path: string, cb: any) => {
      cb(null, {
        format: { duration: 30.5 },
        streams: [{ codec_type: 'video', width: 1080, height: 1920 }],
      });
    });

    const result = await probeMedia(tmpFile);
    expect(result.duration).toBe(30.5);
    expect(result.width).toBe(1080);
    expect(result.height).toBe(1920);

    await fs.unlink(tmpFile);
  });

  it('ffprobe 报错时 reject', async () => {
    const tmpFile = join(os.tmpdir(), 'vectcut-err-' + Date.now() + '.mp4');
    await fs.writeFile(tmpFile, 'fake');

    (ffmpeg.ffprobe as any).mockImplementation((_path: string, cb: any) => {
      cb(new Error('corrupt file'));
    });

    await expect(probeMedia(tmpFile)).rejects.toThrow('ffprobe 失败');
    await fs.unlink(tmpFile);
  });
});
```

- [ ] **步骤 5.3：运行测试 + Commit**

```bash
cd desktop && npm test -- mediaProbe
git add desktop/electron/ipc/mediaProbe.ts desktop/tests/ipc/mediaProbe.test.ts
git commit -m "feat(desktop): probe media metadata via ffprobe-static"
```

---

## 任务 6：文件选择 dialog

**文件：**
- 创建：`desktop/electron/ipc/dialog.ts`

- [ ] **步骤 6.1：创建 dialog.ts（5 种选择器）**

```typescript
// desktop/electron/ipc/dialog.ts
import { IpcMain, dialog } from 'electron';
import { promises as fs } from 'fs';

const VIDEO_EXTS = ['mp4', 'mov', 'avi', 'mkv', 'flv'];
const AUDIO_EXTS = ['mp3', 'wav', 'aac', 'm4a', 'flac'];
const IMAGE_EXTS = ['jpg', 'jpeg', 'png', 'webp', 'bmp'];

async function pickFile(name: string, extensions: string[]): Promise<string | null> {
  const result = await dialog.showOpenDialog({
    title: `选择${name}`,
    properties: ['openFile'],
    filters: [{ name, extensions }],
  });
  if (result.canceled || result.filePaths.length === 0) return null;
  return result.filePaths[0];
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
    if (result.canceled || result.filePaths.length === 0) return null;
    return result.filePaths[0];
  });

  // 修复：在主进程读取文件，避免渲染进程 file:// 协议限制
  ipcMain.handle('file:readZip', async (_evt, filePath: string) => {
    return await fs.readFile(filePath);
  });
}
```

- [ ] **步骤 6.2：手动验证（dialog 需 GUI，跳过单测）**

```bash
cd desktop && npm run dev
# 在 DevTools 控制台执行：
# const p = await window.vectcut.selectVideoFile();
# console.log(p); // 应弹出文件选择框，选择后打印绝对路径
```

- [ ] **步骤 6.3：Commit**

```bash
git add desktop/electron/ipc/dialog.ts
git commit -m "feat(desktop): add file/folder dialog handlers"
```

---

## 任务 7：用户配置持久化 + 服务器地址

**文件：**
- 创建：`desktop/electron/ipc/configStore.ts`
- 创建：`desktop/tests/ipc/configStore.test.ts`

- [ ] **步骤 7.1：创建 configStore.ts（~/.vectcut/config.json 读写）**

```typescript
// desktop/electron/ipc/configStore.ts
import { IpcMain } from 'electron';
import { existsSync, promises as fs } from 'fs';
import { homedir } from 'os';
import { join } from 'path';
import type { UserConfig } from '../../src/types';

const CONFIG_DIR = join(homedir(), '.vectcut');
const CONFIG_FILE = join(CONFIG_DIR, 'config.json');

const DEFAULT_SERVER_URL = 'https://api.vectcut.com';

export function getDefaultServerUrl(): string {
  return DEFAULT_SERVER_URL;
}

export async function getUserConfig(): Promise<UserConfig> {
  if (!existsSync(CONFIG_FILE)) {
    return {};
  }
  try {
    const raw = await fs.readFile(CONFIG_FILE, 'utf-8');
    return JSON.parse(raw) as UserConfig;
  } catch {
    return {};
  }
}

export async function setUserConfig(patch: Partial<UserConfig>): Promise<UserConfig> {
  const current = await getUserConfig();
  const merged: UserConfig = { ...current, ...patch };
  await fs.mkdir(CONFIG_DIR, { recursive: true });
  await fs.writeFile(CONFIG_FILE, JSON.stringify(merged, null, 2), 'utf-8');
  return merged;
}

export async function getServerUrl(): Promise<string> {
  const cfg = await getUserConfig();
  return cfg.serverUrl || DEFAULT_SERVER_URL;
}

export function registerConfigStoreHandlers(ipcMain: IpcMain): void {
  ipcMain.handle('config:get', () => getUserConfig());
  ipcMain.handle('config:set', (_evt, patch: Partial<UserConfig>) => setUserConfig(patch));
}
```

- [ ] **步骤 7.2：创建 test/configStore.test.ts（用临时 HOME 隔离）**

```typescript
// desktop/tests/ipc/configStore.test.ts
import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { promises as fs } from 'fs';
import { join } from 'path';
import os from 'os';

// 用临时目录覆盖 homedir，避免污染真实配置
const fakeHome = join(os.tmpdir(), 'vectcut-fake-home-' + Date.now());

beforeEach(async () => {
  await fs.mkdir(fakeHome, { recursive: true });
  process.env.HOME = fakeHome;
  process.env.USERPROFILE = fakeHome; // Windows
});

afterEach(async () => {
  await fs.rm(fakeHome, { recursive: true, force: true });
});

describe('configStore', () => {
  it('未设置时返回默认服务器地址', async () => {
    const { getServerUrl, getDefaultServerUrl } = await import('../../electron/ipc/configStore');
    expect(await getServerUrl()).toBe(getDefaultServerUrl());
  });

  it('setUserConfig 合并并持久化', async () => {
    const { getUserConfig, setUserConfig } = await import('../../electron/ipc/configStore');
    await setUserConfig({ serverUrl: 'http://localhost:9001' });
    expect((await getUserConfig()).serverUrl).toBe('http://localhost:9001');

    // 再次 set 不覆盖其他字段
    await setUserConfig({ jianyingDraftDir: '/custom/dir' });
    const cfg = await getUserConfig();
    expect(cfg.serverUrl).toBe('http://localhost:9001');
    expect(cfg.jianyingDraftDir).toBe('/custom/dir');
  });
});
```

- [ ] **步骤 7.3：运行测试 + Commit**

```bash
cd desktop && npm test -- configStore
git add desktop/electron/ipc/configStore.ts desktop/tests/ipc/configStore.test.ts
git commit -m "feat(desktop): persist user config and server url"
```

---


## 任务 8：API 客户端层 + 错误码映射

**文件：**
- 创建：`desktop/src/api/client.ts`
- 创建：`desktop/src/api/errorMessages.ts`
- 创建：`desktop/tests/api/client.test.ts`

- [ ] **步骤 8.1：创建 errorMessages.ts（错误码 → 用户友好提示）**

```typescript
// desktop/src/api/errorMessages.ts
/** 错误码 → 用户友好提示映射（与后端 errors.py ERROR_CODES 对齐）。 */
export const ERROR_MESSAGES: Record<string, string> = {
  // 模板错误 (T_xxx)
  T_NOT_FOUND: '模板不存在，请重新导入母版',
  T_INVALID_ZIP: '母版 ZIP 文件格式无效，请检查是否为完整的剪映草稿文件夹',
  T_TOO_LARGE: '母版文件过大（超过 50MB），请精简母版内容',
  T_NO_DRAFT_CONTENT: 'ZIP 中缺少 draft_content.json 文件，请确认是否为剪映草稿',
  T_INVALID_ID: '模板 ID 非法',
  // 槽位错误 (S_xxx)
  S_NOT_FOUND: '槽位配置不存在，请重新配置',
  S_TRACK_NOT_FOUND: '母版中找不到指定轨道，母版可能已被修改，请重新导入',
  S_SEGMENT_NOT_FOUND: '母版中找不到指定片段，母版可能已被修改，请重新导入',
  S_TYPE_MISMATCH: '槽位类型与轨道类型不匹配，请检查配置',
  S_INVALID_SLOT: '槽位 ID 在母版中不存在',
  // 生成错误 (R_xxx)
  R_MISSING_SLOT: '有必填槽位未填写，请检查素材是否完整',
  R_INVALID_PATH: '素材路径格式无效，请选择有效的本地文件',
  R_INVALID_DURATION: '素材时长异常（可能为 0 或过大），请检查文件是否损坏',
  R_LOOP_TOO_MANY: '视频时长远小于配音时长，请增加更多视频片段',
  R_SRT_PARSE_ERROR: 'SRT 字幕文件格式错误，请检查时间轴格式',
  R_GENERATE_FAILED: '草稿生成失败，请查看详细错误信息',
  R_EMPTY_VIDEO: '视频槽位为空，无法生成草稿',
  R_ZERO_DURATION: '素材总时长为 0',
  R_TASK_NOT_FOUND: '草稿任务不存在或已过期，请重新生成',
  R_INVALID_TASK: 'task_id 非法',
  // 通用
  INTERNAL_ERROR: '服务器内部错误，请稍后重试或联系技术支持',
  NETWORK_ERROR: '网络连接失败，请检查网络或服务器地址',
};

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

/** 把后端错误转成用户可读的提示。 */
export function getUserFriendlyError(error: ApiError): string {
  const base = ERROR_MESSAGES[error.code] || error.message;
  if (error.details && Object.keys(error.details).length > 0) {
    const detailsText = Object.entries(error.details)
      .map(([k, v]) => `${k}: ${v}`)
      .join('\n');
    return `${base}\n\n详细信息：\n${detailsText}`;
  }
  return base;
}
```

- [ ] **步骤 8.2：创建 client.ts（4 个 API 封装）**

```typescript
// desktop/src/api/client.ts
import axios, { AxiosInstance } from 'axios';
import { getServerUrl } from '../../electron/ipc/configStore';
import type {
  Slot, MaterialMetadata, SubtitleMetadata, CoverTitleMetadata,
  SlotMapping, ApiEnvelope, ApiError,
} from '../types';

let client: AxiosInstance | null = null;

async function getClient(): Promise<AxiosInstance> {
  if (client) return client;
  const baseURL = await getServerUrl();
  client = axios.create({ baseURL, timeout: 300000 });
  return client;
}

/** 提取后端信封里的 error 为 ApiError。 */
function extractError(envelope: ApiEnvelope<unknown>): ApiError | null {
  if (envelope.success || !envelope.error) return null;
  if (typeof envelope.error === 'string') {
    return { code: 'UNKNOWN', message: envelope.error };
  }
  return envelope.error;
}

export interface ImportTemplateResult {
  template_id: string;
  slots: Slot[];
  message: string;
}

/** 上传母版 zip，返回自动识别的槽位。 */
export async function importTemplate(
  templateId: string,
  zipPath: string,
): Promise<ImportTemplateResult> {
  const http = await getClient();
  const form = new FormData();
  
  // 修复：改用主进程 IPC 读取文件，避免渲染进程 file:// 协议限制
  const fileBuffer = await window.vectcut.readZipFile(zipPath);
  const blob = new Blob([fileBuffer], { type: 'application/zip' });
  form.append('file', blob, `${templateId}.zip`);

  const resp = await http.post(`/api/template/import?template_id=${encodeURIComponent(templateId)}`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  const env = resp.data as ApiEnvelope<ImportTemplateResult>;
  const err = extractError(env);
  if (err) throw err;
  return env.output!;
}

/** 保存槽位配置。 */
export async function saveSlotConfig(
  templateId: string,
  slotMappings: SlotMapping[],
): Promise<{ saved_count: number; message: string }> {
  const http = await getClient();
  const resp = await http.post('/api/template/slot-config', {
    template_id: templateId,
    slot_config: { slot_mappings: slotMappings },
  });
  const env = resp.data as ApiEnvelope<{ saved_count: number; message: string }>;
  const err = extractError(env);
  if (err) throw err;
  return env.output!;
}

export interface RenderDraftResult {
  task_id: string;
  draft_zip_path: string;
  warnings: string[];
  message: string;
}

/** 渲染草稿。 */
export async function renderDraft(
  templateId: string,
  materials: MaterialMetadata[],
  subtitles?: SubtitleMetadata[],
  cover?: CoverTitleMetadata,
): Promise<RenderDraftResult> {
  const http = await getClient();
  const resp = await http.post('/api/template/render', {
    template_id: templateId,
    materials,
    subtitles,
    cover,
  });
  const env = resp.data as ApiEnvelope<RenderDraftResult>;
  const err = extractError(env);
  if (err) throw err;
  return env.output!;
}

/** 下载草稿 zip 到本地临时目录，返回本地 zip 路径。 */
export async function downloadDraft(
  taskId: string,
  savePath: string,
): Promise<string> {
  const http = await getClient();
  const resp = await http.get(`/api/template/download/${encodeURIComponent(taskId)}`, {
    responseType: 'arraybuffer',
  });
  // 若返回 JSON 错误信封（content-type 为 application/json），解析后抛错
  const ct = resp.headers['content-type'] || '';
  if (ct.includes('application/json')) {
    const env = JSON.parse(Buffer.from(resp.data).toString('utf-8')) as ApiEnvelope<unknown>;
    const err = extractError(env);
    if (err) throw err;
  }
  const fs = await import('fs/promises');
  await fs.writeFile(savePath, Buffer.from(resp.data));
  return savePath;
}
```

- [ ] **步骤 8.3：创建 test/client.test.ts（mock axios 单测）**

```typescript
// desktop/tests/api/client.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest';

// mock configStore.getServerUrl，避免读真实配置
vi.mock('../../electron/ipc/configStore', () => ({
  getServerUrl: vi.fn().mockResolvedValue('http://localhost:9001'),
}));

// mock axios
vi.mock('axios', () => {
  const instance = {
    post: vi.fn(),
    get: vi.fn(),
  };
  return { default: { create: () => instance } };
});

import axios from 'axios';
import { importTemplate, renderDraft, saveSlotConfig } from '../../src/api/client';
import { getUserFriendlyError } from '../../src/api/errorMessages';

const mockPost = (axios.create as any)().post as ReturnType<typeof vi.fn>;

beforeEach(() => {
  vi.clearAllMocks();
});

describe('importTemplate', () => {
  it('成功返回槽位列表', async () => {
    mockPost.mockResolvedValue({
      data: { success: true, output: { template_id: 't1', slots: [], message: 'ok' }, error: null },
    });
    const result = await importTemplate('t1', '/tmp/test.zip');
    expect(result.template_id).toBe('t1');
    expect(result.slots).toEqual([]);
  });

  it('失败时抛 ApiError', async () => {
    mockPost.mockResolvedValue({
      data: {
        success: false,
        output: null,
        error: { code: 'T_INVALID_ZIP', message: 'invalid', details: {} },
      },
    });
    await expect(importTemplate('t1', '/tmp/bad.zip')).rejects.toMatchObject({
      code: 'T_INVALID_ZIP',
    });
  });
});

describe('renderDraft', () => {
  it('成功返回 task_id', async () => {
    mockPost.mockResolvedValue({
      data: {
        success: true,
        output: { task_id: 'task_abc', draft_zip_path: '/x.zip', warnings: [], message: 'ok' },
        error: null,
      },
    });
    const result = await renderDraft('t1', [{ slot_id: 'v1', path: '/v.mp4', duration: 10 }]);
    expect(result.task_id).toBe('task_abc');
  });

  it('循环次数过多抛 R_LOOP_TOO_MANY', async () => {
    mockPost.mockResolvedValue({
      data: {
        success: false,
        output: null,
        error: { code: 'R_LOOP_TOO_MANY', message: 'loop too many', details: {} },
      },
    });
    await expect(
      renderDraft('t1', [{ slot_id: 'v1', path: '/v.mp4', duration: 5 }]),
    ).rejects.toMatchObject({ code: 'R_LOOP_TOO_MANY' });
  });
});

describe('getUserFriendlyError', () => {
  it('已知错误码返回中文提示', () => {
    const msg = getUserFriendlyError({ code: 'R_LOOP_TOO_MANY', message: 'x' });
    expect(msg).toContain('增加更多视频片段');
  });

  it('带 details 追加详细信息', () => {
    const msg = getUserFriendlyError({
      code: 'S_TRACK_NOT_FOUND',
      message: 'x',
      details: { track: 'video_main' },
    });
    expect(msg).toContain('详细信息');
    expect(msg).toContain('video_main');
  });

  it('未知错误码回退到原 message', () => {
    const msg = getUserFriendlyError({ code: 'UNKNOWN_CODE', message: '原始消息' });
    expect(msg).toBe('原始消息');
  });
});
```

- [ ] **步骤 8.4：运行测试 + Commit**

```bash
cd desktop && npm test -- client
git add desktop/src/api/ desktop/tests/api/
git commit -m "feat(desktop): add API client with error code mapping"
```

---

## 任务 9：渲染进程页面（4 页向导）

**文件：**
- 创建：`desktop/src/components/Stepper.tsx`
- 创建：`desktop/src/pages/TemplateManager.tsx`
- 创建：`desktop/src/pages/SlotConfig.tsx`
- 创建：`desktop/src/pages/MaterialFill.tsx`
- 创建：`desktop/src/pages/GenerateImport.tsx`
- 修改：`desktop/src/App.tsx`

- [ ] **步骤 9.1：创建 Stepper.tsx（步骤导航组件）**

```tsx
// desktop/src/components/Stepper.tsx
interface StepperProps {
  current: number; // 0-based
  steps: string[];
  onStepClick?: (idx: number) => void;
}

export function Stepper({ current, steps, onStepClick }: StepperProps) {
  return (
    <div style={{ display: 'flex', marginBottom: 24, gap: 8 }}>
      {steps.map((label, idx) => {
        const done = idx < current;
        const active = idx === current;
        return (
          <div
            key={idx}
            onClick={() => onStepClick?.(idx)}
            style={{
              flex: 1,
              padding: '12px 16px',
              borderRadius: 8,
              cursor: onStepClick ? 'pointer' : 'default',
              background: active ? '#1677ff' : done ? '#f0f9eb' : '#f5f5f5',
              color: active ? '#fff' : '#333',
              border: active ? '1px solid #1677ff' : '1px solid #eee',
              fontWeight: active ? 600 : 400,
              textAlign: 'center',
            }}
          >
            {done ? '✓ ' : `${idx + 1}. `}{label}
          </div>
        );
      })}
    </div>
  );
}
```

- [ ] **步骤 9.2：创建 TemplateManager.tsx（导入母版）**

```tsx
// desktop/src/pages/TemplateManager.tsx
import { useState } from 'react';
import type { Slot } from '../types';
import { importTemplate } from '../api/client';

interface Props {
  onTemplateImported: (templateId: string, slots: Slot[]) => void;
}

export function TemplateManager({ onTemplateImported }: Props) {
  const [folderPath, setFolderPath] = useState<string | null>(null);
  const [templateId, setTemplateId] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const pickFolder = async () => {
    const p = await window.vectcut.selectTemplateFolder();
    if (p) setFolderPath(p);
  };

  const doImport = async () => {
    if (!folderPath || !templateId.trim()) {
      setError('请选择母版文件夹并填写模板 ID');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const { zipPath } = await window.vectcut.packTemplateFolder(folderPath);
      const result = await importTemplate(templateId.trim(), zipPath);
      onTemplateImported(result.template_id, result.slots);
    } catch (e: any) {
      setError(e.message || String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h2>第 1 步：导入母版</h2>
      <div style={{ marginBottom: 16 }}>
        <button onClick={pickFolder}>选择剪映草稿文件夹</button>
        {folderPath && <span style={{ marginLeft: 12 }}>{folderPath}</span>}
      </div>
      <div style={{ marginBottom: 16 }}>
        <label>模板 ID（自定义名称）：</label>
        <input
          value={templateId}
          onChange={(e) => setTemplateId(e.target.value)}
          placeholder="如 vlog_001"
          style={{ marginLeft: 8, padding: '4px 8px', width: 200 }}
        />
      </div>
      {error && <div style={{ color: 'red', marginBottom: 12 }}>{error}</div>}
      <button onClick={doImport} disabled={loading || !folderPath || !templateId.trim()}>
        {loading ? '导入中...' : '打包并上传'}
      </button>
    </div>
  );
}
```

- [ ] **步骤 9.3：创建 SlotConfig.tsx（勾选可替换槽位）**

```tsx
// desktop/src/pages/SlotConfig.tsx
import { useState } from 'react';
import type { Slot, SlotMapping } from '../types';
import { saveSlotConfig } from '../api/client';

interface Props {
  templateId: string;
  slots: Slot[];
  onConfigSaved: (selected: Slot[]) => void;
}

export function SlotConfig({ templateId, slots, onConfigSaved }: Props) {
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggle = (slotId: string) => {
    const next = new Set(selected);
    if (next.has(slotId)) next.delete(slotId);
    else next.add(slotId);
    setSelected(next);
  };

  const save = async () => {
    setLoading(true);
    setError(null);
    try {
      const picked = slots.filter((s) => selected.has(s.slot_id));
      const mappings: SlotMapping[] = picked.map((s) => ({
        slot_id: s.slot_id,
        type: s.type,
        track_name: s.track_name,
        segment_index: s.segment_index,
      }));
      await saveSlotConfig(templateId, mappings);
      onConfigSaved(picked);
    } catch (e: any) {
      setError(e.message || String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h2>第 2 步：选择要替换的槽位</h2>
      <p style={{ color: '#666' }}>勾选你希望用新素材替换的片段：</p>
      <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: 16 }}>
        <thead>
          <tr style={{ background: '#f5f5f5' }}>
            <th style={{ padding: 8 }}>勾选</th>
            <th style={{ padding: 8 }}>槽位 ID</th>
            <th style={{ padding: 8 }}>类型</th>
            <th style={{ padding: 8 }}>轨道</th>
            <th style={{ padding: 8 }}>片段下标</th>
          </tr>
        </thead>
        <tbody>
          {slots.map((s) => (
            <tr key={s.slot_id} style={{ borderBottom: '1px solid #eee' }}>
              <td style={{ padding: 8, textAlign: 'center' }}>
                <input
                  type="checkbox"
                  checked={selected.has(s.slot_id)}
                  onChange={() => toggle(s.slot_id)}
                />
              </td>
              <td style={{ padding: 8 }}>{s.slot_id}</td>
              <td style={{ padding: 8 }}>{s.type}</td>
              <td style={{ padding: 8 }}>{s.track_name}</td>
              <td style={{ padding: 8 }}>{s.segment_index}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {error && <div style={{ color: 'red', marginBottom: 12 }}>{error}</div>}
      <button onClick={save} disabled={loading || selected.size === 0}>
        {loading ? '保存中...' : '保存槽位配置'}
      </button>
    </div>
  );
}
```

- [ ] **步骤 9.4：创建 MaterialFill.tsx（选素材 + 自动读元数据）**

```tsx
// desktop/src/pages/MaterialFill.tsx
import { useState } from 'react';
import type { Slot, MaterialMetadata } from '../types';

interface Props {
  slots: Slot[];
  onMaterialsReady: (materials: MaterialMetadata[]) => void;
}

export function MaterialFill({ slots, onMaterialsReady }: Props) {
  const [materials, setMaterials] = useState<Record<string, MaterialMetadata>>({});
  const [error, setError] = useState<string | null>(null);

  const pickFile = async (slot: Slot) => {
    let path: string | null = null;
    if (slot.type === 'video') path = await window.vectcut.selectVideoFile();
    else if (slot.type === 'audio' || slot.type === 'bgm') path = await window.vectcut.selectAudioFile();
    else if (slot.type === 'subtitle') path = await window.vectcut.selectSrtFile();
    if (!path) return;

    // 自动采集元数据（图片除外）
    let meta: Partial<MaterialMetadata> = { path };
    if (slot.type !== 'subtitle') {
      try {
        const probed = await window.vectcut.probeMedia(path);
        meta = { ...meta, duration: probed.duration, width: probed.width, height: probed.height };
      } catch (e: any) {
        setError(`元数据采集失败：${e.message}`);
      }
    }
    setMaterials({ ...materials, [slot.slot_id]: { slot_id: slot.slot_id, ...meta } as MaterialMetadata });
  };

  const ready = Object.keys(materials).length;

  return (
    <div>
      <h2>第 3 步：为每个槽位选择本地素材</h2>
      {error && <div style={{ color: 'red', marginBottom: 12 }}>{error}</div>}
      <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: 16 }}>
        <thead>
          <tr style={{ background: '#f5f5f5' }}>
            <th style={{ padding: 8 }}>槽位</th>
            <th style={{ padding: 8 }}>类型</th>
            <th style={{ padding: 8 }}>素材路径</th>
            <th style={{ padding: 8 }}>时长/尺寸</th>
            <th style={{ padding: 8 }}>操作</th>
          </tr>
        </thead>
        <tbody>
          {slots.map((s) => {
            const m = materials[s.slot_id];
            return (
              <tr key={s.slot_id} style={{ borderBottom: '1px solid #eee' }}>
                <td style={{ padding: 8 }}>{s.slot_id}</td>
                <td style={{ padding: 8 }}>{s.type}</td>
                <td style={{ padding: 8 }}>{m?.path || '（未选择）'}</td>
                <td style={{ padding: 8 }}>
                  {m ? `${m.duration?.toFixed(1) || '-'}s / ${m.width || '-'}x${m.height || '-'}` : '-'}
                </td>
                <td style={{ padding: 8 }}>
                  <button onClick={() => pickFile(s)}>选择</button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <button onClick={() => onMaterialsReady(Object.values(materials))} disabled={ready === 0}>
        确认素材并生成（{ready}/{slots.length}）
      </button>
    </div>
  );
}
```

- [ ] **步骤 9.5：创建 GenerateImport.tsx（生成 + 下载 + 导入剪映）**

```tsx
// desktop/src/pages/GenerateImport.tsx
import { useState } from 'react';
import type { MaterialMetadata } from '../types';
import { renderDraft, downloadDraft } from '../api/client';
import { getUserFriendlyError } from '../api/errorMessages';

interface Props {
  templateId: string;
  materials: MaterialMetadata[];
  onRestart: () => void;
}

export function GenerateImport({ templateId, materials, onRestart }: Props) {
  const [status, setStatus] = useState<'idle' | 'rendering' | 'downloading' | 'importing' | 'done' | 'error'>('idle');
  const [error, setError] = useState<string | null>(null);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [draftDir, setDraftDir] = useState<string | null>(null);

  const run = async () => {
    setStatus('rendering');
    setError(null);
    try {
      const result = await renderDraft(templateId, materials);
      setTaskId(result.task_id);
      if (result.warnings.length > 0) {
        setError('警告：' + result.warnings.join('；'));
      }

      setStatus('downloading');
      const savePath = `${require('os').tmpdir()}/${result.task_id}.zip`;
      await downloadDraft(result.task_id, savePath);

      setStatus('importing');
      const imported = await window.vectcut.importDraftToJianying(savePath);
      setDraftDir(imported.draftDir);

      setStatus('done');
    } catch (e: any) {
      setError(getUserFriendlyError(e));
      setStatus('error');
    }
  };

  return (
    <div>
      <h2>第 4 步：生成草稿并导入剪映</h2>
      {status === 'idle' && <button onClick={run}>开始生成</button>}
      {status === 'rendering' && <p>正在生成草稿（云端处理中）...</p>}
      {status === 'downloading' && <p>正在下载草稿...</p>}
      {status === 'importing' && <p>正在导入剪映草稿目录...</p>}
      {status === 'done' && (
        <div style={{ color: 'green' }}>
          <p>✅ 草稿已导入剪映目录！</p>
          {draftDir && <p>位置：{draftDir}</p>}
          <p>请打开剪映，在草稿列表中查看。</p>
          <button onClick={onRestart}>开始下一个模板</button>
        </div>
      )}
      {status === 'error' && (
        <div style={{ color: 'red' }}>
          <p>❌ {error}</p>
          <button onClick={onRestart}>重新开始</button>
        </div>
      )}
      {taskId && status !== 'done' && status !== 'error' && <p>task_id: {taskId}</p>}
    </div>
  );
}
```

- [ ] **步骤 9.6：用 App.tsx 串联 4 步向导**

```tsx
// desktop/src/App.tsx
import { useState } from 'react';
import { Stepper } from './components/Stepper';
import { TemplateManager } from './pages/TemplateManager';
import { SlotConfig } from './pages/SlotConfig';
import { MaterialFill } from './pages/MaterialFill';
import { GenerateImport } from './pages/GenerateImport';
import type { Slot, MaterialMetadata } from './types';

const STEPS = ['导入母版', '槽位配置', '素材填充', '生成导入'];

export default function App() {
  const [step, setStep] = useState(0);
  const [templateId, setTemplateId] = useState<string>('');
  const [slots, setSlots] = useState<Slot[]>([]);
  const [selectedSlots, setSelectedSlots] = useState<Slot[]>([]);
  const [materials, setMaterials] = useState<MaterialMetadata[]>([]);

  const restart = () => {
    setStep(0);
    setTemplateId('');
    setSlots([]);
    setSelectedSlots([]);
    setMaterials([]);
  };

  return (
    <div style={{ padding: 24, fontFamily: 'system-ui', maxWidth: 1000, margin: '0 auto' }}>
      <h1 style={{ marginBottom: 24 }}>VectCut 模板套版</h1>
      <Stepper current={step} steps={STEPS} onStepClick={(i) => i <= step && setStep(i)} />

      {step === 0 && (
        <TemplateManager
          onTemplateImported={(id, s) => {
            setTemplateId(id);
            setSlots(s);
            setStep(1);
          }}
        />
      )}
      {step === 1 && (
        <SlotConfig
          templateId={templateId}
          slots={slots}
          onConfigSaved={(picked) => {
            setSelectedSlots(picked);
            setStep(2);
          }}
        />
      )}
      {step === 2 && (
        <MaterialFill
          slots={selectedSlots}
          onMaterialsReady={(m) => {
            setMaterials(m);
            setStep(3);
          }}
        />
      )}
      {step === 3 && (
        <GenerateImport
          templateId={templateId}
          materials={materials}
          onRestart={restart}
        />
      )}
    </div>
  );
}
```

- [ ] **步骤 9.7：手动端到端验证（需后端运行）**

```bash
# 1. 启动后端（方案一/方案二后端）
python run_http.py

# 2. 启动桌面客户端
cd desktop && npm run dev

# 3. 在客户端中走完 4 步向导：
#    - 选母版文件夹 → 填模板 ID → 打包上传
#    - 勾选槽位 → 保存
#    - 为每个槽位选本地素材（自动读元数据）
#    - 生成 → 下载 → 导入剪映
```

- [ ] **步骤 9.8：Commit**

```bash
git add desktop/src/
git commit -m "feat(desktop): implement 4-step wizard UI"
```

---


## 任务 10：设置页 + 错误对话框

**文件：**
- 创建：`desktop/src/pages/Settings.tsx`
- 创建：`desktop/src/components/ErrorDialog.tsx`
- 修改：`desktop/src/App.tsx`（顶部加设置入口）

- [ ] **步骤 10.1：创建 Settings.tsx（服务器地址 + 剪映目录 + 连接测试）**

```tsx
// desktop/src/pages/Settings.tsx
import { useState, useEffect } from 'react';

export function Settings({ onClose }: { onClose: () => void }) {
  const [serverUrl, setServerUrl] = useState('');
  const [jianyingDir, setJianyingDir] = useState<string | null>(null);
  const [version, setVersion] = useState<string | null>(null);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<'success' | 'error' | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    (async () => {
      const cfg = await window.vectcut.getUserConfig();
      setServerUrl(cfg.serverUrl || 'https://api.vectcut.com');
      setJianyingDir(cfg.jianyingDraftDir || (await window.vectcut.detectJianyingDraftDir()));
      setVersion(await window.vectcut.detectJianyingVersion());
    })();
  }, []);

  const testConnection = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const resp = await fetch(`${serverUrl}/api/health`);
      setTestResult(resp.ok ? 'success' : 'error');
    } catch {
      setTestResult('error');
    }
    setTesting(false);
  };

  const save = async () => {
    await window.vectcut.setUserConfig({ serverUrl, jianyingDraftDir: jianyingDir || undefined });
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const pickJianyingDir = async () => {
    const p = await window.vectcut.selectTemplateFolder();
    if (p) setJianyingDir(p);
  };

  return (
    <div style={{ padding: 24, maxWidth: 600 }}>
      <h2>设置</h2>

      <section style={{ marginBottom: 24 }}>
        <h3>服务器地址</h3>
        <input
          value={serverUrl}
          onChange={(e) => setServerUrl(e.target.value)}
          style={{ width: '100%', padding: '6px 8px', marginRight: 8 }}
        />
        <div style={{ marginTop: 8 }}>
          <button onClick={testConnection} disabled={testing}>
            {testing ? '测试中...' : '测试连接'}
          </button>
          {testResult === 'success' && <span style={{ color: 'green', marginLeft: 12 }}>✅ 连接成功</span>}
          {testResult === 'error' && <span style={{ color: 'red', marginLeft: 12 }}>❌ 连接失败</span>}
        </div>
      </section>

      <section style={{ marginBottom: 24 }}>
        <h3>剪映草稿目录</h3>
        <p style={{ color: '#666', fontSize: 13 }}>
          自动检测：{jianyingDir || '未找到'}
          {version && `（剪映版本 ${version}）`}
        </p>
        <button onClick={pickJianyingDir}>手动选择目录</button>
      </section>

      <div style={{ marginTop: 24 }}>
        <button onClick={save} style={{ marginRight: 8 }}>保存设置</button>
        <button onClick={onClose}>关闭</button>
        {saved && <span style={{ color: 'green', marginLeft: 12 }}>✅ 已保存</span>}
      </div>
    </div>
  );
}
```

- [ ] **步骤 10.2：创建 ErrorDialog.tsx（用户友好提示 + 技术详情折叠）**

```tsx
// desktop/src/components/ErrorDialog.tsx
import { useState } from 'react';
import { getUserFriendlyError, type ApiError } from '../api/errorMessages';

interface Props {
  error: ApiError;
  onClose: () => void;
}

export function ErrorDialog({ error, onClose }: Props) {
  const [showDetails, setShowDetails] = useState(false);
  const friendly = getUserFriendlyError(error);

  const copyToClipboard = () => {
    navigator.clipboard.writeText(JSON.stringify(error, null, 2));
  };

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(0,0,0,0.5)', display: 'flex',
      alignItems: 'center', justifyContent: 'center', zIndex: 9999,
    }}>
      <div style={{ background: '#fff', padding: 24, borderRadius: 8, maxWidth: 500, width: '90%' }}>
        <h3 style={{ marginTop: 0 }}>
          {error.code === 'R_LOOP_TOO_MANY' ? '⚠️ 视频不足' : '⚠️ 操作失败'}
        </h3>
        <p style={{ whiteSpace: 'pre-wrap' }}>{friendly}</p>

        {error.code === 'R_LOOP_TOO_MANY' && (
          <div style={{ background: '#f0f9ff', padding: 12, borderRadius: 4, marginTop: 12 }}>
            <strong>建议：</strong>
            <ul style={{ margin: '8px 0' }}>
              <li>增加更多视频片段</li>
              <li>缩短配音时长</li>
              <li>使用更长的视频素材</li>
            </ul>
          </div>
        )}

        <details style={{ marginTop: 12 }}>
          <summary
            onClick={() => setShowDetails(!showDetails)}
            style={{ cursor: 'pointer', color: '#666', fontSize: 13 }}
          >
            技术详情（用于反馈 Bug）
          </summary>
          <pre style={{ fontSize: 12, overflow: 'auto', background: '#f5f5f5', padding: 8 }}>
            {JSON.stringify(error, null, 2)}
          </pre>
        </details>

        <div style={{ marginTop: 16, textAlign: 'right' }}>
          <button onClick={copyToClipboard} style={{ marginRight: 8 }}>复制错误信息</button>
          <button onClick={onClose}>关闭</button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **步骤 10.3：在 App.tsx 加设置入口**

修改 `desktop/src/App.tsx`，在标题栏右侧加"设置"按钮：

```tsx
// 在 App.tsx 顶部 import
import { Settings } from './pages/Settings';
import { useState } from 'react';

// 在组件内加 state（与现有 step state 并列）
const [showSettings, setShowSettings] = useState(false);

// 在 <h1> 标题旁加按钮（修改 h1 那一行为）：
<div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
  <h1>VectCut 模板套版</h1>
  <button onClick={() => setShowSettings(true)}>设置</button>
</div>

// 在组件 return 末尾（外层 div 闭合前）加：
{showSettings && <Settings onClose={() => setShowSettings(false)} />}
```

- [ ] **步骤 10.4：手动验证设置页**

```bash
cd desktop && npm run dev
# 点击右上角"设置" → 测试连接（需后端运行）→ 保存 → 关闭
# 重启客户端，确认设置已持久化
```

- [ ] **步骤 10.5：Commit**

```bash
git add desktop/src/pages/Settings.tsx desktop/src/components/ErrorDialog.tsx desktop/src/App.tsx
git commit -m "feat(desktop): add settings page and error dialog"
```

---

## 任务 11：打包配置 + 分发文档

**文件：**
- 创建：`desktop/electron-builder.yml`
- 创建：`desktop/docs/install-guide.md`（SmartScreen 绕过说明）

- [ ] **步骤 11.1：创建 electron-builder.yml**

```yaml
# desktop/electron-builder.yml
appId: com.vectcut.desktop
productName: VectCut 模板套版
directories:
  output: dist
  buildResources: build
files:
  - out/**/*
  - package.json
  - '!**/*.{ts,tsx,map}'
  - '!tests/**'
  - '!docs/**'

# Windows 打包
win:
  target:
    - nsis
    - portable
  artifactName: ${productName}-${version}-${arch}.${ext}

nsis:
  oneClick: false
  allowToChangeInstallationDirectory: true
  createDesktopShortcut: true
  shortcutName: VectCut 模板套版

# macOS 打包
mac:
  target:
    - dmg
  category: public.app-category.video
  # 代码签名（MVP 阶段留空，公测阶段填入开发者证书）
  # identity: null

dmg:
  artifactName: ${productName}-${version}.${ext}

# 附加资源：内置 ffprobe 二进制
extraResources:
  - from: node_modules/ffprobe-static/{bin,bin/**}
    to: ffprobe
    filter: ['**/*']
```

- [ ] **步骤 11.2：创建 install-guide.md（含 SmartScreen 绕过说明）**

```markdown
# desktop/docs/install-guide.md

# VectCut 模板套版 安装指南

## Windows 安装

### 1. 下载安装包

从 GitHub Releases 下载最新版 `VectCut-模板套版-Setup-x.x.x.exe`。

### 2. 处理 SmartScreen 拦截

由于 MVP 内测阶段未购买代码签名证书，Windows SmartScreen 可能拦截：

1. 弹出"Windows 已保护你的电脑"时，点击 **更多信息**
2. 点击 **仍要运行**
3. 按提示完成安装

**安全说明**：本应用代码完全开源，可在 GitHub 查看源码。后续版本将购买 EV 证书签名。

### 3. 系统要求

- Windows 10 64 位及以上
- 剪映专业版 10.0-10.9
- 安装后无需额外配置（ffprobe 已内置）

## macOS 安装

### 1. 下载 dmg

下载 `VectCut-模板套版-x.x.x.dmg`。

### 2. 处理 Gatekeeper 拦截

未签名的 Mac 应用无法直接打开，需：

```bash
# 终端执行，移除隔离属性
xattr -cr '/Applications/VectCut 模板套版.app'
```

或在 **系统设置 → 隐私与安全性** 中点击"仍要打开"。

### 3. 系统要求

- macOS 11 及以上
- 剪映专业版 10.0-10.9（Mac 版）

## 首次使用

1. 启动应用，点击右上角 **设置**
2. 填写服务器地址（默认 `https://api.vectcut.com`，内测可填开发者提供的地址）
3. 点击 **测试连接** 确认可访问
4. 确认剪映草稿目录已自动检测到
5. 保存设置，开始使用

## 常见问题

### Q: 提示"未找到剪映草稿目录"？

A: 在设置中手动选择剪映草稿目录，路径通常为：
- Windows: `%LOCALAPPDATA%\JianyingPro\User Data\Projects\com.lveditor.draft`
- macOS: `~/Movies/JianyingPro/User Data/Projects/com.lveditor.draft`

### Q: 提示"网络连接失败"？

A: 检查服务器地址是否正确、网络是否可达、后端服务是否运行。
```

- [ ] **步骤 11.3：本地打包验证**

```bash
cd desktop
npm run build  # 先构建主进程 + 渲染进程产物

# Windows 打包（在 Windows 上执行）
npm run pack:win
# 预期：dist/ 目录生成 .exe 安装包

# 或 Mac 打包（在 Mac 上执行）
npm run pack:mac
# 预期：dist/ 目录生成 .dmg

# 验证产物
ls -lh dist/
```

- [ ] **步骤 11.4：Commit**

```bash
git add desktop/electron-builder.yml desktop/docs/install-guide.md
git commit -m "feat(desktop): add electron-builder config and install guide"
```

---

## 任务 12：全量测试 + 端到端验收

- [ ] **步骤 12.1：运行全量单元测试**

```bash
cd desktop
npm test
# 预期：所有单测通过（jianyingDir / packer / mediaProbe / configStore / client）
```

- [ ] **步骤 12.2：TypeScript 类型检查**

```bash
cd desktop
npx tsc --noEmit -p tsconfig.json
npx tsc --noEmit -p tsconfig.node.json
# 预期：无类型错误
```

- [ ] **步骤 12.3：构建验证**

```bash
cd desktop
npm run build
# 预期：out/main、out/preload、out/renderer 三个目录生成，无报错
```

- [ ] **步骤 12.4：端到端验收清单（对照规格 §18.4）**

逐项确认：

- [ ] 能导入母版（选剪映草稿文件夹 → 打包上传 → 返回槽位）
- [ ] 能配置 5 类素材槽位（video/audio/bgm/subtitle/cover）
- [ ] 能为槽位选择本地素材并自动读元数据
- [ ] 能生成草稿并下载
- [ ] 草稿自动解压导入剪映 draft 目录
- [ ] 字幕样式基本保留（字体/颜色/位置）—— 需后端配合验证
- [ ] 时长对齐正确（配音基准）—— 需后端配合验证
- [ ] 服务器地址可在设置页配置 + 测试连接
- [ ] 错误信息用户友好（不出现技术术语给最终用户）
- [ ] Windows 可打包为 .exe 安装包
- [ ] 安装指南含 SmartScreen 绕过说明

- [ ] **步骤 12.5：与后端联调验证**

```bash
# 1. 启动后端
cd .. && python run_http.py

# 2. 启动客户端
cd desktop && npm run dev

# 3. 准备一个真实剪映草稿作为母版（含 draft_content.json）

# 4. 走完整 4 步向导，验证：
#    - 母版上传成功，返回槽位列表
#    - 槽位配置保存成功
#    - 选素材后元数据自动填充
#    - 生成成功，task_id 返回
#    - 下载的 zip 解压到剪映目录
#    - 打开剪映能看到新草稿
```

- [ ] **步骤 12.6：最终 Commit**

```bash
git add desktop/
git commit -m "test(desktop): verify full e2e flow with backend"
```

---

## 附录 A：规格映射

| 方案二规格章节 | 实现任务 |
|---------------|---------|
| §8.1 拿到真实文件路径（dialog） | 任务 6 |
| §8.2 元数据采集（ffprobe） | 任务 5 |
| §8.3 剪映草稿目录探测 | 任务 3 |
| §8.4 母版打包上传 | 任务 4 + 任务 9（TemplateManager） |
| §8.5 自动更新 | （MVP 不实现，规格 §18.1 明确不包含） |
| §8.6 安全边界（contextBridge） | 任务 2 |
| §8.7 服务器地址配置 | 任务 7 + 任务 10（Settings） |
| §9.1 剪映版本兼容性 | 任务 3（isVersionSupported） |
| §10.2 目录结构 | 任务 1（脚手架按此结构） |
| §10.4 错误信息用户化 | 任务 8（errorMessages）+ 任务 10（ErrorDialog） |
| §13.2 代码签名与分发 | 任务 11（含 SmartScreen 文档） |
| §14 阶段 D 最小化客户端 | 任务 1-8（核心流程跑通） |
| §14 阶段 E 完整 Electron | 任务 9-10（4 页向导 + 设置） |
| §14 阶段 F 打包分发 | 任务 11-12 |
| §18.1 MVP 功能范围 | 全部任务覆盖 |
| §18.4 验收清单 | 任务 12.4 |

## 附录 B：测试运行汇总

```bash
cd desktop

# 单测（按任务）
npm test -- jianyingDir    # 任务 3
npm test -- packer         # 任务 4
npm test -- mediaProbe     # 任务 5
npm test -- configStore    # 任务 7
npm test -- client         # 任务 8

# 全量
npm test

# 类型检查
npx tsc --noEmit -p tsconfig.json
npx tsc --noEmit -p tsconfig.node.json

# 构建 + 打包
npm run build
npm run pack:win  # 或 pack:mac
```

## 附录 C：与方案一/方案二后端的协作边界

| 关注点 | 客户端负责 | 后端负责 |
|-------|-----------|---------|
| 素材文件 | 本地选择、采集元数据 | 不接触文件 |
| 元数据 | path/duration/width/height | 接收并写入草稿 JSON |
| 母版 | 打包 ZIP 上传 | 解析、识别槽位、存储 |
| 草稿生成 | 提交渲染请求 | 引擎套版、样式继承、时长对齐 |
| 草稿下载 | 下载 ZIP、解压到剪映目录 | 返回 ZIP 文件流 |
| 错误处理 | 用户友好映射 | 标准化错误码 + 信封 |

---

**计划结束。** 任意零上下文工程师按任务 1→12 顺序执行，每步带可运行代码与验证命令，即可交付可工作的 Electron 桌面客户端，与方案一云端 API + 方案二后端 template_filling feature 联动，完成"采集本地素材元数据 → 提交云端套版 → 下载草稿导入剪映"全流程。

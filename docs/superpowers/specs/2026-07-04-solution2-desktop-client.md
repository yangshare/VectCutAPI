# 方案二：Electron 桌面客户端 + 云端元数据套版

- 日期：2026-07-04
- 状态：待评审（已采纳客户端形态 = 桌面客户端）
- 范围：基于 VectCutAPI 的「模板套版」后端 feature + Electron 桌面客户端
- 核心思路：**素材不上传云端，只传元数据（路径/大小/时长）；桌面客户端拿真实路径，云端用元数据生成草稿**

## 1. 方案目标

给创作者一个桌面操作入口，把"拷贝母版 → 替换 5 类素材 → 检查导出"的手工流程自动化。

**与方案一的关系**：方案一是把现有 API Docker 化部署（基础设施）；方案二是在云端 API 之上，新增「模板套版」feature 和桌面客户端（业务应用）。两者组合落地：方案一提供云端 API，方案二消费它。

**与同事原 Tauri 方案的区别**：原方案让引擎在用户本地跑（Python 子进程），违背"核心能力在云端"。本方案让引擎在云端跑，桌面客户端只做"采集 + 提交 + 下载导入"——既满足运营对核心能力的掌控，又解决了浏览器拿不到本地路径的硬伤。

## 2. 核心设计理念：素材不上传，只传元数据

### 2.1 关键洞察

创作者的素材（视频、配音、BGM、封面图）是**本地大文件**（几十 MB 到几 GB）。全部上传到云端会面临：存储成本爆炸、上传耗时长、隐私顾虑、运营负担（文件服务器/CDN/清理）。

### 2.2 剪映草稿的工作原理

剪映草稿文件（`draft_content.json`）里，**素材引用的是本地绝对路径**，而不是素材本身：

```jsonc
{
  "type": "video",
  "material": {
    "path": "E:/素材/本期/video1.mp4",   // ← 本地绝对路径
    "duration": 12500000,                  // ← 时长（微秒）
    "width": 1080,
    "height": 1920
  }
}
```

剪映打开草稿时，根据这个路径**从用户本地加载素材到轨道**。因此——

> 云端生成草稿时，**根本不需要拿到素材文件本身**，只需要知道素材在用户本地的绝对路径、时长、尺寸。

### 2.3 元数据套版模式

```
用户本地素材（大文件，不出本地）
        │
        │ 桌面客户端采集元数据
        ↓
┌───────────────────────────┐
│  Electron 桌面客户端       │   拿真实路径 + 读时长/尺寸
└───────────────┬───────────┘
                │ HTTPS（只传 JSON + SRT 文本，几 KB）
┌───────────────▼───────────┐
│  云端 API（方案一部署）     │   用元数据生成 draft_content.json
│  · 不接触素材文件本身       │
└───────────────┬───────────┘
                │ 下载 ZIP（草稿 JSON，KB 级）
┌───────────────▼───────────┐
│  桌面客户端自动导入         │   解压 → 复制到剪映草稿目录
└───────────────┬───────────┘
                ↓
        剪映打开 → 从本地路径加载素材
```

### 2.4 元数据采集清单

| 素材类型 | 需要的元数据 | 采集方式（客户端 Node 端） |
|----------|-------------|--------------------------|
| **video** | 本地绝对路径、时长、宽×高 | ffprobe 读文件头 |
| **audio（配音）** | 本地绝对路径、时长 | ffprobe |
| **bgm** | 本地绝对路径、时长 | ffprobe |
| **cover_image** | 本地绝对路径、宽×高 | 图片尺寸读取 |
| **subtitle** | SRT 文件内容（文本+时间轴） | 读文件文本（纯文本，KB 级） |
| **cover_title** | 标题文字字符串 | 用户输入 |

SRT 是纯文本小文件，**直接随请求传内容**；其余音视频图片**只传路径和元数据**。

## 3. 架构设计

```
┌──────────────────────────────────────────────────────────────┐
│  Electron 桌面客户端                                          │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ 渲染进程（React + TypeScript + Vite）                   │  │
│  │  · 模板管理页 · 槽位配置页 · 素材填充页 · 生成下载页     │  │
│  └───────────────────────┬────────────────────────────────┘  │
│                          │ IPC                                 │
│  ┌───────────────────────▼────────────────────────────────┐  │
│  │ 主进程（Node.js）                                       │  │
│  │  · dialog：文件/文件夹选择 → 真实绝对路径               │  │
│  │  · ffprobe：素材元数据采集（时长/尺寸）                 │  │
│  │  · 剪映草稿目录探测（Win/Mac 自动定位）                 │  │
│  │  · 母版草稿扫描 + ZIP 打包上传                          │  │
│  │  · 草稿 ZIP 下载 + 解压 + 自动复制到剪映目录            │  │
│  │  · electron-updater：自动更新                           │  │
│  └───────────────────────┬────────────────────────────────┘  │
└──────────────────────────┼───────────────────────────────────┘
                           │ HTTPS（JSON + SRT 文本，几 KB）
┌──────────────────────────▼───────────────────────────────────┐
│  云端服务（复用方案一的 Docker 部署）                          │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ FastAPI（现有接口 + 新增 template_filling feature）      │  │
│  │   · import_template     导入母版（ZIP 上传，母版小）     │  │
│  │   · save_slot_config    保存槽位配置                     │  │
│  │   · render_draft        元数据套版生成草稿               │  │
│  │   · download_draft      下载草稿 ZIP                     │  │
│  └────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ pyJianYingDraft 引擎                                    │  │
│  │   · 用元数据（路径+时长）生成 draft_content.json         │  │
│  │   · 不需要素材文件本身                                   │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

### 3.1 关键边界

- **桌面客户端持有**：真实文件路径、元数据、剪映目录访问能力、自动更新。
- **云端持有**：母版草稿（ZIP，几 MB）、槽位配置（JSON）、SRT 文本、生成的草稿 JSON。**不持有任何用户素材文件**。
- **核心能力在云端**：母版解析、槽位识别、套版生成、字幕样式继承、5 类素材替换逻辑——全部在服务端，运营完全掌控。

## 4. 数据模型

存 JSON 文件，不存库（与项目现状一致）。

### 4.1 模板（Template）

```jsonc
{
  "template_id": "tpl_001",
  "name": "口播视频母版",
  "master_draft_zip": "master_tpl_001.zip",   // 客户端打包上传的母版 ZIP
  "profile": "jianying_pro_10",
  "created_at": "2026-07-04T10:00:00Z"
}
```

### 4.2 槽位配置（SlotConfig）

```jsonc
{
  "template_id": "tpl_001",
  "slots": [
    {"slot_id": "v1", "name": "主视频1", "type": "video",    "track": "video_main", "segment_index": 0},
    {"slot_id": "v2", "name": "主视频2", "type": "video",    "track": "video_main", "segment_index": 1},
    {"slot_id": "au", "name": "配音",    "type": "audio",    "track": "audio_main", "segment_index": 0},
    {"slot_id": "bg", "name": "BGM",     "type": "bgm",      "track": "bgm",        "segment_index": 0},
    {"slot_id": "st", "name": "字幕",    "type": "subtitle"},
    {"slot_id": "ci", "name": "封面图",  "type": "cover_image"},
    {"slot_id": "ct", "name": "封面标题","type": "cover_title"}
  ]
}
```

### 4.3 套版请求（RenderRequest）

```jsonc
{
  "template_id": "tpl_001",
  "slot_values": {
    "v1": {
      "path": "E:/素材/本期/video1.mp4",      // ← 用户本地绝对路径（写入草稿）
      "duration": 125.4,                       // ← 时长（秒，客户端 ffprobe 采集）
      "width": 1080,
      "height": 1920
    },
    "v2": {"path": "E:/素材/本期/video2.mp4", "duration": 88.2, "width": 1080, "height": 1920},
    "au": {"path": "E:/素材/本期/dubbing.mp3", "duration": 210.5},
    "bg": {"path": "E:/素材/本期/bgm.mp3", "duration": 180.0},
    "st": {
      "srt_content": "1\n00:00:01,000 --> 00:00:03,500\n大家好...\n..."  // ← SRT 文本直接传
    },
    "ci": {"path": "E:/素材/本期/cover.jpg", "width": 1080, "height": 1920},
    "ct": {"text": "第5期：如何快速套版"}
  },
  "output_draft_name": "第5期如何快速套版"
}
```

**请求体大小**：几 KB（路径 + 元数据 + SRT 文本），相比上传几百 MB 素材，**节省 5 个数量级**。

## 5. 工作流

| 步骤 | 客户端页面 | 用户动作 | 端 |
|------|-----------|----------|-----|
| ① 导入母版 | 模板管理 | 用户手动选母版草稿文件夹 → 命名 | 客户端打包 + 云端解析 |
| ② 配槽位 | 槽位配置 | 勾选可替换片段 + 起名 | 云端保存 |
| ③ 填素材 | 素材填充 | 选本地文件 → 客户端自动读元数据 + 拿真实路径 | 客户端 |
| ④ 一键生成 | 生成下载 | 点"生成" → 传元数据 → 云端生成 → 下载 ZIP | 云端生成 + 客户端下载 |
| ⑤ 导入剪映 | — | 客户端自动解压复制到剪映草稿目录 → 提示打开剪映 | 客户端 |

配一次槽位（②），之后每期只做 ③④⑤。换新模板才回到 ①②。

## 6. 后端 API（template_filling feature）

复用项目现有 service/router/schemas 三件套分层。统一响应外壳 `{success, output, error}`。

### 6.1 POST /api/template/import — 上传并解析母版

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| file | File（ZIP） | 是 | 客户端打包的母版草稿文件夹 |
| name | string | 是 | 模板名 |
| profile | string | 否 | 默认 `jianying_pro_10` |

行为：解压 ZIP → 加载 `Script_file` → 遍历轨道 → 返回按类型分组的可替换片段候选清单。

返回：`template_id` + 片段清单（供客户端勾选成槽位）。

### 6.2 POST /api/template/slot/config — 保存槽位配置

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| template_id | string | 是 | |
| slots | Slot[] | 是 | 槽位数组 |

行为：校验 slot 的 track/segment_index 在母版中存在、type 与轨道类型兼容；持久化 SlotConfig JSON。

### 6.3 POST /api/template/render — 元数据套版生成

入参：`RenderRequest`（§4.3，只含路径+元数据+SRT 文本）。

行为见 §7。

返回：`{ draft_id, download_url }`。

### 6.4 GET /api/template/download/:draft_id — 下载草稿 ZIP

返回：生成的 `dfd_xxx` 文件夹打包成 ZIP（含 `draft_content.json`，KB 级）。

## 7. render_draft 内部流程

> **⭐ 时长模型（核心产品决策）**：以**配音时长为基准**。作品总时长 = 配音时长（口播视频的配音是讲述主干）。
> - **视频**：多段按槽位顺序拼接，总时长对齐配音时长——超出配音时长的末段截断，不足则**循环最后一段视频填满**配音时长。
> - **BGM**：截断到配音时长；BGM 短于配音时循环铺满。
> - **字幕**：用新 SRT 时间轴，天然落在配音时长内。
> - 槽位若无配音，回退到"视频总时长为基准"。

### 7.1 总流程

```
1. 校验：RenderRequest 的元数据完整性（path 非空、duration 合理）
2. duplicate_as_template(母版, 临时副本)            ← 引擎现成
3. 遍历 slot_values，按 type 分派替换（见 7.2）
4. 副本.save() → 生成 dfd_ 文件夹（draft_content.json）
5. 打包成 ZIP，返回 download_url
```

**关键**：服务端全程**不接触素材文件本身**，只用元数据生成 `draft_content.json` 里的 `material.path/duration/width/height` 字段。

### 7.2 5 类素材替换行为

| type | 替换行为 | 所需元数据 |
|------|----------|-----------|
| **video** | 写入 `material.path`、`duration`、`width/height`；重算 `source_timerange`/`target_timerange` | path、duration、width、height |
| **audio（配音）** | 同 video（音频无宽高） | path、duration |
| **bgm** | 写入音频素材路径 + duration；**按配音时长截断**（短于配音时循环铺满） | path、duration |
| **subtitle** | 整轨重建：解析 SRT 文本 → 套用母版首个字幕片段样式 → 逐句生成 | srt_content |
| **cover_image** | 写入封面图路径 + 尺寸 | path、width、height |
| **cover_title** | 改封面标题文本，保留样式 | text |

### 7.3 关键约束

- **替换顺序**：先 audio（配音）锁定基准时长 → video/bgm 对齐配音时长 → subtitle（新 SRT）→ cover。
- 字幕用新 SRT 时间轴（配音驱动画面节奏，母版字幕时间轴会错位）。
- 草稿里的 `material.path` 必须是用户本地路径（请求里传什么就写什么）。

## 8. 桌面客户端实现要点

### 8.1 拿到真实文件路径（解决 Web 硬伤）

主进程用 `dialog` 选择文件/文件夹，返回真实绝对路径：

```typescript
// 主进程：选视频文件
const result = await dialog.showOpenDialog({
  properties: ['openFile'],
  filters: [{ name: '视频', extensions: ['mp4', 'mov', 'avi', 'mkv'] }],
});
const realPath = result.filePaths[0];   // "E:/素材/本期/video1.mp4" —— 真实路径
```

### 8.2 元数据采集（ffprobe）

主进程内置 `ffprobe-static`（无需用户装 FFmpeg），用 `fluent-ffmpeg` 读元数据：

```typescript
import ffmpeg from 'fluent-ffmpeg';
import ffprobePath from 'ffprobe-static';

ffmpeg.setFfprobePath(ffprobePath.path);

async function probeMedia(filePath: string) {
  return new Promise((resolve, reject) => {
    ffmpeg.ffprobe(filePath, (err, data) => {
      if (err) return reject(err);
      const v = data.streams.find(s => s.codec_type === 'video');
      resolve({
        duration: data.format.duration,        // 秒
        width: v?.width,
        height: v?.height,
      });
    });
  });
}
```

### 8.3 剪映草稿目录探测

客户端自动定位剪映草稿目录（可手动覆盖）：

```typescript
import { app } from 'electron';
import path from 'path';
import os from 'os';

function detectJianyingDraftDir(): string | null {
  const home = os.homedir();
  const candidates = process.platform === 'win32'
    ? [path.join(home, 'AppData/Local/JianyingPro/User Data/Projects/com.lveditor.draft')]
    : [path.join(home, 'Movies/JianyingPro/User Data/Projects/com.lveditor.draft')];
  // 校验存在性，返回第一个存在的，否则 null（让用户手动选）
}
```

草稿下载后：客户端解压并复制到该目录，打开剪映即可见（§5 步骤⑤）。

### 8.4 母版打包上传

用户选母版 `dfd_*` 文件夹后，客户端打成 ZIP 上传到 `/api/template/import`。

### 8.5 自动更新

`electron-updater` + GitHub Release / 静态服务器托管安装包，实现灰度更新。

### 8.6 安全边界

- 渲染进程不开 `nodeIntegration`，通过 `preload.js` + `contextBridge` 暴露受控 IPC API。
- 主进程校验所有 IPC 入参，避免路径遍历风险。

## 9. 为什么桌面客户端解决了 Web 的硬伤

| 问题（纯 Web） | 桌面客户端解法 |
|----------------|---------------|
| 浏览器拿不到真实路径（`C:\fakepath\`） | Electron `dialog` 返回真实绝对路径，写入草稿后剪映能加载 |
| 无法自动定位剪映草稿目录 | Node.js 文件系统访问，自动探测 Win/Mac 路径 |
| 母版需用户手动打 ZIP | 客户端自动扫描草稿目录 + 自动打包 |
| 草稿下载需手动解压到剪映目录 | 客户端自动解压 + 复制 + 提示打开剪映 |

**核心能力仍在云端**：客户端只是"采集器 + 下载器"，套版逻辑、引擎、样式继承全在服务端。

## 10. 目录结构

### 10.1 后端（遵循现有 features 分层）

```
vectcut/features/template_filling/
  __init__.py
  service.py          # import_template / save_slot_config / render_draft
  schemas.py          # Pydantic 模型（Template/Slot/RenderRequest）
  router.py           # 4 个路由
  slot_resolver.py    # slot → 引擎 segment 的解析与校验
  style_extractor.py  # 字幕/封面样式提取
  storage.py          # Template/SlotConfig/草稿 ZIP 存取
tests/features/template_filling/
  test_service.py
  test_service_golden.py
  fixtures/
    sample_master_draft/   # 合成测试母版
```

### 10.2 桌面客户端（仓库内新增 `desktop/`）

```
desktop/
  electron/
    main.ts                # 主进程入口
    preload.ts             # contextBridge 暴露受控 IPC
    ipc/
      dialog.ts            # 文件/文件夹选择
      mediaProbe.ts        # ffprobe 元数据采集
      jianyingDir.ts       # 剪映目录探测 + 草稿导入
      packer.ts            # 母版 ZIP 打包
      updater.ts           # 自动更新
  src/                     # 渲染进程（React + TS + Vite）
    pages/
      TemplateManager.tsx   # ① 扫描剪映目录选母版 + 模板列表
      SlotConfig.tsx        # ② 勾选片段配命名槽位
      MaterialFill.tsx      # ③ 选素材 + 自动读元数据
      GenerateImport.tsx    # ④ 生成 ⑤ 自动导入剪映
    api/client.ts           # HTTP client 封装
    types.ts                # 与后端 schemas 对齐的 TS 类型
  electron-builder.yml      # Win/Mac 打包配置
  package.json
```

## 11. 测试策略

复用项目现有 `tests/golden/` 黄金测试模式。

- **黄金测试（防回归）**：固定母版 + 固定元数据（路径+时长）+ 固定 SRT → 生成的 `draft_content.json` 逐字等于基线。
- **feature 单测**：直接调 `service.render_draft()`，断言草稿里 `material.path` 等于请求传入的路径、字幕样式等于母版首片段、封面图引用已改。
- **边界测试**：① 视频时长变化的时间轴重算；② 槽位留空保留母版；③ 字幕样式继承完整性；④ 母版无封面走注入。
- **客户端单测**：元数据采集函数（mock ffprobe）、剪映目录探测、ZIP 打包/解压。

## 12. 方案优势

| 优势 | 说明 |
|------|------|
| **存储成本归零** | 云端不存素材，只存母版（几 MB）和草稿 JSON（KB 级） |
| **带宽成本极低** | 请求只传元数据，响应只传 JSON，单次几 KB |
| **用户隐私好** | 素材不出本地，创作者安心 |
| **生成速度快** | 无需上传等待，元数据传完即生成 |
| **核心能力在云端** | 母版解析、套版逻辑、样式继承全在服务端，运营完全掌控 |
| **用户体验顺** | 自动扫描草稿目录、自动读元数据、自动导入剪映，一键到底 |
| **可商业化** | 云端可加鉴权/计费/多租户，客户端只是入口 |

## 13. 风险与应对

| 风险 | 等级 | 应对 |
|------|------|------|
| **用户素材路径变动**（移动/重命名） | 中 | 生成前客户端校验路径存在性；剪映打开失败时给排查指引 |
| **跨平台路径格式**（Win/Mac） | 中 | 客户端探测 OS，草稿按用户系统格式写路径 |
| **元数据采集不准** | 低 | ffprobe 精度足够；必要时云端 ffprobe 复核（仍不存文件） |
| **剪映目录探测失败**（自定义安装路径） | 低 | 客户端让用户手动指定一次，记忆配置 |
| **客户端分发与更新** | 低 | electron-updater + GitHub Release，灰度推送 |
| **母版 ZIP 体积** | 低 | 母版草稿目录通常几 MB（含缩略图），可接受 |
| **代码签名/杀软误报** | 低 | 后续申请代码签名证书；MVP 可先不签 |

## 14. 阶段划分（每阶段可独立验证）

| 阶段 | 内容 | 风险 |
|------|------|------|
| **A 后端 feature 骨架** | `template_filling` 包 + schemas + storage + import/save_slot_config 两接口 + 单测 | 低 |
| **B render_draft 核心** | duplicate + 5 类替换 + 字幕样式继承 + golden 基线 | 高（字幕样式继承是难点） |
| **C 错误处理 + 边界** | 异常映射 + 槽位留空 + 时长策略覆盖 | 中 |
| **D 桌面客户端** | Electron 主进程（dialog/probe/剪映目录/打包/导入）+ 四个 React 页面 | 中 |
| **E 端到端打磨** | 真实母版联调、生成后剪映打开验证、自动更新 | 中 |

每阶段结束跑 golden + 全量测试，绿了即可 review。

## 15. 已确认的产品决策

1. **时长基准 = 配音时长**：视频、BGM 一律对齐配音时长（口播视频配音为主干）。详见 §7 时长模型。
2. **BGM 策略**：截断到配音时长；BGM 短于配音时循环铺满。
3. **视频对齐策略**：多段拼接对齐配音时长，超出末段截断、不足时循环最后一段视频填满配音时长。
4. **母版上传方式**：用户手动选母版草稿文件夹（客户端不自动扫描剪映目录）。
5. **草稿导入剪映**：生成后客户端自动复制到剪映草稿目录。
6. **客户端分发渠道**：GitHub Release。

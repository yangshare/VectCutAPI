# 剪映模板套版桌面平台 设计规格

- 日期：2026-07-04
- 状态：待评审
- 范围：在 VectCutAPI 之上新增「模板套版」后端 feature + Tauri 桌面应用

## 1. 背景与目标

VectCutAPI 当前应用层（`vectcut/features`）只暴露「从零增量构建」的剪辑 API（`add_video`/`add_text`/…），适合 AI Agent 编排。但底层引擎 `pyJianYingDraft` **已经具备模板套版能力**（`Draft_folder.duplicate_as_template`、`ImportedMediaTrack.process_timerange`、`Shrink_mode`/`Extend_mode`），应用层尚未暴露。

本平台面向一类高频人工场景：**创作者在剪映里把一个"母版草稿"的样式（字幕字体/字号/位置、封面标题字体/大小/位置、转场、特效）调到满意后，希望每期只换内容素材（视频、配音、BGM、字幕、封面图、封面标题），一键得到一份新草稿，打开剪映检查后导出。**

目标：把这套引擎能力包成一个桌面 GUI 工具，让上述"拷贝母版 → 替换 5 类素材"的手工流程自动化，且**样式 100% 继承母版**（所见即所得）。

## 2. 用户场景（来自澄清）

- 日常：单次套版为主（一次填一组素材 → 生成 1 个新草稿），非批量生产。
- 工作流：拷贝母版草稿 → 用剪映替换 封面图/封面标题/字幕/视频/配音/BGM → 检查导出。本平台自动化这一过程。
- 保留：字幕的字体/字号/位置/颜色/描边；封面标题的大小/位置/字体。
- 替换：视频轨道全部视频、配音轨道全部配音、BGM、字幕（每期一份新 SRT）、封面图、封面标题文字。
- 字幕来源：每期一份完整 SRT 文件（文字 + 时间轴都有）。
- 剪映版本：国内剪映（profile = `jianying_pro_10`）。
- 落地：生成的草稿自动复制到剪映草稿目录，打开剪映即可见。

## 3. 范围与非目标

**范围内**：
- 后端新增 `template_filling` feature（3 个 HTTP 接口）。
- Tauri 桌面应用（React + TypeScript 前端，三个页面）。
- 5 类素材替换：video / audio(配音) / bgm / subtitle / cover_image / cover_title。
- 字幕整轨重建（新 SRT + 继承母版字幕样式）。
- 生成草稿自动复制到剪映草稿目录。

**非目标（YAGNI）**：
- 不做批量套版（清单导入/CSV/任务队列）——用户明确单次套版为主。
- 不做素材库管理——素材是本地文件路径，每次填入，不入库。
- 不修改 `pyJianYingDraft` 引擎内部（只读约束继承自 2026-07-02 架构设计）。
- 不做参数化样式生成（思路 B，见 §11 否决方案）——样式由母版承载。
- MVP 不做 Python 环境冻结/打包（开发态假设宿主机已装 Python 3.10+ 与 vectcut 依赖）；一键冻结安装包列为后续阶段。

## 4. 整体架构

```
┌──────────────────────────────────────────────────────────┐
│  Tauri 桌面应用                                            │
│  ┌────────────────────────────────────────────────────┐  │
│  │  渲染进程（React + TypeScript + Vite）               │  │
│  │  · 模板管理页 · 槽位配置页 · 套版生成页               │  │
│  └───────────────────────┬────────────────────────────┘  │
│                          │ HTTP → localhost:9001           │
│  ┌───────────────────────▼────────────────────────────┐  │
│  │  主进程（Rust，tauri-plugin-shell）                  │  │
│  │  · 启动 & 守护 Python FastAPI 子进程                  │  │
│  │  · 应用退出时关闭子进程                               │  │
│  └───────────────────────┬────────────────────────────┘  │
└──────────────────────────┼───────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────┐
│  Python FastAPI（复用现有 vectcut/server/http）            │
│  ＋ 新增 feature：vectcut/features/template_filling/      │
│    · import_template    导入母版，解析轨道与可替换片段       │
│    · save_slot_config   保存"命名槽位"配置                  │
│    · render_draft       复制母版→替换素材→写草稿→入剪映目录  │
└──────────────────────────┬───────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────┐
│  pyJianYingDraft 引擎（只读，能力已具备）                   │
│    Draft_folder.duplicate_as_template   复制母版           │
│    ImportedMediaTrack.process_timerange 替换音视频          │
│    Script_file.save → draft_content.json                  │
└──────────────────────────┬───────────────────────────────┘
                           │ 复制 dfd_ 文件夹
                    ┌──────▼───────┐
                    │ 剪映草稿目录   │ ← 打开剪映即可见
                    └──────────────┘
```

**关键边界**：
- 桌面应用是现有 FastAPI 的 GUI 外壳 + 一个新 feature；后端引擎零修改。
- Tauri 主进程只做子进程生命周期管理；所有剪辑逻辑走 HTTP 到 FastAPI，不在 Rust 侧重写。
- `template_filling` 遵循项目现有 `features/*` 分层（`service.py` 纯业务 + `schemas.py` + `router.py`），与 2026-07-02 架构 refactor 设计一致。

## 5. 数据模型

三个 JSON 对象，存文件不存库（与项目现状一致）。存储根目录：`<user_data>/vectcut_templates/`（Tauri app data 目录）。

### 5.1 模板（Template）

```jsonc
{
  "template_id": "tpl_001",
  "name": "口播视频母版",
  "source_draft_path": "D:/我的母版/口播模板",      // 剪映母版草稿文件夹
  "profile": "jianying_pro_10",                     // 国内剪映
  "jianying_draft_dir": "C:/Users/.../com.lveditor.draft",  // 生成草稿的复制目标
  "created_at": "2026-07-04T10:00:00Z"
}
```

### 5.2 槽位配置（SlotConfig）

每个模板一份，定义"哪些位置可换"。

```jsonc
{
  "template_id": "tpl_001",
  "slots": [
    {"slot_id": "v1", "name": "主视频1", "type": "video",    "track": "video_main", "segment_index": 0},
    {"slot_id": "v2", "name": "主视频2", "type": "video",    "track": "video_main", "segment_index": 1},
    {"slot_id": "au", "name": "配音",    "type": "audio",    "track": "audio_main", "segment_index": 0},
    {"slot_id": "bg", "name": "BGM",     "type": "bgm",      "track": "bgm",        "segment_index": 0},
    {"slot_id": "st", "name": "字幕",    "type": "subtitle", "track": "subtitle"},   // 整轨，无 segment_index
    {"slot_id": "ci", "name": "封面图",  "type": "cover_image"},
    {"slot_id": "ct", "name": "封面标题","type": "cover_title"}
  ]
}
```

**slot.type 枚举**：`video` | `audio` | `bgm` | `subtitle` | `cover_image` | `cover_title`。

### 5.3 套版项目（FillProject）

每次套版填一份，用完即弃（可存历史记录，非必须）。

```jsonc
{
  "project_id": "prj_20260704_1",
  "template_id": "tpl_001",
  "slot_values": {
    "v1": "E:/素材/本期/video1.mp4",
    "v2": "E:/素材/本期/video2.mp4",
    "au": "E:/素材/本期/dubbing.mp3",
    "bg": "E:/素材/本期/bgm.mp3",
    "st": "E:/素材/本期/caption.srt",
    "ci": "E:/素材/本期/cover.jpg",
    "ct": "第5期：如何快速套版"
  },
  "output_draft_name": "第5期如何快速套版"
}
```

`slot_values` 的值：`video/audio/bgm/cover_image` 为本地文件绝对路径；`subtitle` 为 SRT 文件路径；`cover_title` 为字符串。允许某个槽位留空（不填则保留母版原素材）。

## 6. 工作流

| 步骤 | 前端页面 | 用户动作 | 后端动作 |
|------|----------|----------|----------|
| ① 导入母版 | 模板管理 | 选母版草稿文件夹，命名模板 | `import_template`：加载母版，遍历轨道，返回结构化片段清单 |
| ② 配槽位 | 槽位配置 | 勾选要换的片段 + 起名（命名槽位） | `save_slot_config`：存 SlotConfig JSON |
| ③ 填素材 | 套版生成 | 给每个槽位填本期素材路径/标题文字 | （纯前端，校验文件存在性） |
| ④ 一键生成 | 套版生成 | 点"生成" | `render_draft`：复制母版 → 替换 5 类素材 → 写草稿 → 复制到剪映目录 |

配一次槽位（②），之后每期只做 ③④。换新模板才回到 ①②。

## 7. 后端 API（template_filling feature）

复用项目现有 service/router/schemas 三件套分层。路由挂到现有 FastAPI app（`vectcut/server/http`），统一响应外壳 `{success, output, error}`。

### 7.1 POST /import_template

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| source_draft_path | string | 是 | 母版草稿文件夹绝对路径 |
| name | string | 是 | 模板名 |
| profile | string | 否 | 默认取 config 的 `draft_profile` |
| jianying_draft_dir | string | 否 | 默认取剪映默认草稿目录 |

行为：`Draft_folder(source_draft_path).load_template(...)` 加载母版 `Script_file`；遍历 `tracks`，对 `video`/`audio` 轨道列出每个 segment（含时间轴位置、当前素材名），识别字幕轨道，识别封面 composition/素材。生成 `template_id` 并持久化 Template。

返回：`template_id` + 按类型分组的可替换片段候选清单（供前端勾选成槽位）。

### 7.2 POST /save_slot_config

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| template_id | string | 是 | |
| slots | Slot[] | 是 | 槽位数组 |

行为：校验每个 slot 的 `track`/`segment_index` 在母版中存在、`type` 与轨道类型兼容（如 `video` 只能绑 video 轨道片段）；持久化 SlotConfig JSON。

### 7.3 POST /render_draft

入参：FillProject（§5.3）。

行为：见 §8。

返回：`{ output_draft_name, copied_to_jianying: true/false, error_detail? }`。

## 8. render_draft 内部流程与 5 类素材替换行为

### 8.1 总流程

```
1. 校验：FillProject 的每个 slot_value 文件存在；output_draft_name 合法
2. duplicate_as_template(母版, 临时副本)            ← 引擎现成
3. 遍历 slot_values，按 type 分派替换（见 8.2）
4. 副本.save() → 生成 dfd_ 文件夹（draft_content.json）
5. 复制到 template.jianying_draft_dir/<output_draft_name>
6. 返回草稿名 + 复制结果
```

### 8.2 5 类素材替换行为

| type | 替换行为 | 引擎能力 | 时长不匹配默认策略 |
|------|----------|----------|--------------------|
| **video** | 替换该 segment 的视频素材文件，重算 `source_timerange` | `ImportedMediaTrack.process_timerange` | `Extend_mode.push_tail`（更长→后推后续片段；更短→片段缩短留空，剪映里微调）+ `Shrink_mode.cut_tail` |
| **audio**（配音） | 同 video | 同上 | 同上 |
| **bgm** | 替换 BGM 音频素材文件 | 音频素材替换 | 截断到 video 轨道替换后的总时长（槽位配置可选 `loop` 改为循环） |
| **subtitle** | **整轨重建**：清空母版字幕轨道所有片段 → 用新 SRT 解析 → 套用母版首个字幕片段的样式 → 逐句生成新片段 | `add_subtitle` 的 SRT 解析 + 母版样式提取（§9.1） | 无（SRT 自带时间轴） |
| **cover_image** | 替换封面图：定位母版封面素材（composition 引用链），替换图片文件引用；母版无封面时用 `add_cover` 注入 | 复用现成 `add_cover` 方案（commit 63a69d8） | 无 |
| **cover_title** | 改封面标题文字：定位封面标题文本片段，修改 text 内容，保留样式 | 文本片段 text 字段改写 | 无 |

允许槽位留空（`slot_values` 缺该 key）：跳过替换，保留母版原素材。

### 8.3 render_draft 的关键约束

- 替换顺序：先处理 video/audio/bgm（可能改变总时长），再处理 subtitle（用新 SRT，不依赖母版时间轴），最后 cover。
- 字幕必须用新 SRT 而非继承母版字幕时间轴——因为 video push_tail 会改变画面节奏，母版字幕时间轴必然错位。

## 9. 关键技术难点

### 9.1 字幕样式继承

母版字幕片段的样式散落在 `text_content`/`text_style`（含字体、字号、颜色、描边、阴影、背景、字号比例、坐标变换 `clip.transform`/`clip.scale` 等）多个字段。实现要点：

- 从母版字幕轨道**首个**字幕片段提取完整样式快照（深拷贝 `text_style` + `clip`）。
- 新 SRT 每一句生成片段时，套用该样式快照，仅覆盖 `text` 内容与 `target_timerange`（来自 SRT 时间轴）。
- 用 golden test 锁定：固定母版 + 固定 SRT → 生成的字幕片段样式字段逐字等于母版首片段样式。

### 9.2 视频 push_tail 连锁

`process_timerange` 的 `push_tail` 会后推后续所有片段起始时间。当多段 video 都替换且时长变化时，需保证按 `segment_index` 顺序替换，让 push_tail 的累积位移正确传递。实现要点：槽位按 `segment_index` 升序处理；每次替换后该轨道后续片段的 `start` 已被引擎正确后移。

### 9.3 封面替换的两种形态

母版可能：① 已有封面 composition（剪映 6.x 引用链）→ 改其中的图片资源 ID 与标题文字；② 无封面 → 调 `add_cover` 注入。`render_draft` 先探测母版是否含封面素材，分派两条路径。

## 10. 错误处理

复用项目现有 `vectcut/core/errors.py` 异常体系，新增以下领域异常，HTTP/MCP 双映射遵循现有约定：

| 异常 | 触发 | HTTP | MCP |
|------|------|------|-----|
| `TemplateNotFound` | 母版草稿路径不存在 | 404 | -32001 |
| `InvalidTemplate` | 路径不是有效剪映草稿（缺 draft_content.json） | 422 | -32002 |
| `SlotConfigInvalid` | 槽位 track/segment_index 不存在，或 type 与轨道不兼容 | 422 | -32002 |
| `MaterialMissing` | slot_value 指定的素材文件不存在 | 404 | -32001 |
| `RenderError` | 引擎替换失败（如时长策略 `ExtensionFailed`） | 500 | -32003 |
| `JianyingDirNotWritable` | 剪映草稿目录不可写/不存在 | 500 | -32003 |

前端：每个错误映射为可读提示 + 建议动作（如"素材文件不存在：E:/xxx.mp4，请检查路径"）。

## 11. 测试策略（TDD）

复用项目现有 `tests/golden/` 黄金测试模式（见 2026-07-02 设计 §7）。

- **黄金测试（防回归）**：用一份小型真实母版草稿 fixture + 一组测试素材 + 一份测试 SRT，记录 `render_draft` 生成的 `draft_content.json` 为基线。后续任何改动必须复现同样的 draft 输出。
- **feature 单元测试**：直接调 `service.render_draft()`，断言草稿状态——video 片段素材已替换、字幕样式等于母版首片段、封面图引用已改。
- **边界测试**：①视频变长/变短的 push_tail/cut_tail；②槽位留空保留母版素材；③字幕样式提取完整性；④母版无封面时走 add_cover 注入。
- **HTTP 层**：FastAPI TestClient 验路由接线 + 错误码映射。
- **前端组件测试**：槽位勾选 UI、文件存在性校验、生成结果展示。

测试 fixture（小型合成母版 + 公版素材，避免依赖真实剪映）放在 `tests/features/template_filling/fixtures/`。

## 12. 目录结构与新增代码位置

后端（遵循现有 features 分层）：

```
vectcut/features/template_filling/
  __init__.py
  service.py          # import_template / save_slot_config / render_draft
  schemas.py          # Pydantic 请求/响应模型（Template/Slot/FillProject）
  router.py           # 3 个 POST 路由
  slot_resolver.py    # slot → 引擎 segment 的解析与校验
  style_extractor.py  # 字幕/封面样式提取
  storage.py          # Template/SlotConfig JSON 读写
tests/features/template_filling/
  test_service.py
  test_service_golden.py
  fixtures/
    sample_master_draft/   # 合成测试母版草稿
    sample_assets/          # 测试用视频/音频/SRT/封面
```

桌面应用（仓库内新增 `desktop/`）：

```
desktop/
  src-tauri/            # Rust 主进程：spawn & 守护 FastAPI 子进程
    src/main.rs
    tauri.conf.json
  src/                  # React + TS + Vite
    pages/
      TemplateManager.tsx   # ① 导入母版 + 模板列表
      SlotConfig.tsx        # ② 勾选片段配命名槽位
      FillGenerate.tsx      # ③ 填素材 ④ 一键生成
    api/client.ts           # HTTP client 封装
    types.ts                # 与后端 schemas 对齐的 TS 类型
```

## 13. 阶段划分（每阶段可独立验证）

| 阶段 | 内容 | 风险 |
|------|------|------|
| **A 后端 feature 骨架** | `template_filling` 包 + schemas + storage + import_template/save_slot_config 两接口 + 单测 | 低 |
| **B render_draft 核心** | duplicate + 5 类替换 + 字幕样式继承 + golden 基线 | 高（字幕样式继承是难点） |
| **C 错误处理 + 边界** | 6 类异常 + 槽位留空 + 时长策略覆盖 + 复制到剪映目录 | 中 |
| **D Tauri 外壳** | Rust spawn FastAPI + 三个 React 页面 + 文件选择/校验 | 中 |
| **E 端到端打磨** | 真实母版联调、生成后剪映打开验证、异常提示文案 | 中 |

每阶段结束跑 golden + 全量测试，绿了即可 review。

## 14. 否决的方案

- **思路 B 参数化生成（从零构建 + 样式参数预设）**：要求在平台里用参数重新描述剪映样式系统（字体/字号/位置/颜色/描边/阴影/动画…），繁琐且无法 100% 复现剪映里的视觉效果。母版草稿是样式最忠实的载体，故采用思路 A（模板替换）。详见 brainstorming 记录。

## 15. 待用户评审确认的开放点

1. **BGM 时长策略**：默认"截断到 video 轨道替换后的总时长"，是否需要"循环"选项？（已设计为槽位配置可选 `loop`，确认即可）
2. **视频时长不匹配默认策略**：`push_tail` + `cut_tail`（更长后推、更短留空）。是否接受"更短留空需剪映里微调"，还是希望"更短时自动贴合下一片段不留空"？
3. **前端框架**：默认 React + TS + Vite，可换 Svelte/Vue，不影响后端。
4. **Python 打包**：MVP 假设宿主机已装 Python 与 vectcut 依赖（开发态）；一键冻结安装包列为后续阶段，确认推迟是否可接受。

# Task 12 全量测试与端到端验收报告

## 基本信息

- **任务：** Solution2 Task 12，全量测试 + 端到端验收。
- **基线提交：** `70992cba0a99295ad627e582da4ba818abc1c5e4`。
- **执行日期：** 2026-07-06；Windows 打包复验：2026-07-07。
- **执行范围：** `desktop` 自动化测试、TypeScript 类型检查、构建产物检查、Windows 打包尝试，以及端到端人工联调清单记录。
- **结论口径：** 没有真实后端、剪映专业版和真实样例草稿参与的项目，统一标记为“未执行/需人工联调”，不视为端到端通过。

## 自动化验证记录

| 序号 | 验证项 | 命令或检查 | 当前状态 | 结果 |
| --- | --- | --- | --- | --- |
| 1 | TDD 红灯验证 | `npm test -- e2e-verification` | 已执行 | 新增报告前失败，原因是 `desktop/docs/e2e-verification.md` 不存在，符合预期。 |
| 2 | 验收报告测试 | `npm test -- e2e-verification` | 已执行 | 3/3 通过。 |
| 3 | 全量测试 | `npm test` | 已执行 | 15 个测试文件、161 个测试通过。 |
| 4 | Renderer TypeScript 类型检查 | `npx tsc --noEmit -p tsconfig.json` | 已执行 | 通过；已在 `src/raw.d.ts` 为 `*.tsx?raw` 导入补充 `*?raw` 声明。 |
| 5 | Node/Electron TypeScript 类型检查 | `npx tsc --noEmit -p tsconfig.node.json` | 已执行 | 通过；已将 Node/Electron 类型检查切换为 `module: "ESNext"`、`moduleResolution: "bundler"`，并补充 `ffprobe-static` 声明。 |
| 6 | 构建验证 | `npm run build` | 已执行 | 通过，electron-vite 成功构建 main、preload、renderer。 |
| 7 | 构建输出目录检查 | `out/main`、`out/preload`、`out/renderer` | 已执行 | 三个目录均存在。 |
| 8 | Electron 依赖收敛 | `npm install --offline --save-dev electron@29.4.6` | 已执行 | 使用 npm 缓存中的 `electron-29.4.6.tgz` 和 `%LOCALAPPDATA%\electron\Cache\electron-v29.4.6-win32-x64.zip`，将 Electron 从 43.0.0 收敛到满足 Electron 28+ 要求的 29.4.6；`node_modules/electron/dist/electron.exe` 已生成。 |
| 9 | Windows 打包验证 | `npm run pack:win` | 已执行 | 通过，生成 `dist/VectCut 模板套版-Setup-1.0.0-x64.exe` 和 `dist/VectCut 模板套版-Portable-1.0.0-x64.exe`。 |
| 10 | Diff 空白检查 | `git diff --check -- package.json package-lock.json docs/e2e-verification.md` | 已执行 | 无空白错误；Git 仅提示这些文本文件下次触碰时会进行 LF/CRLF 转换。 |
| 11 | 工作树检查 | `git status --short` | 已执行 | 工作树已有任务 A/B 未提交改动；本轮 Windows 打包复验改动限定在 `package.json`、`package-lock.json` 和 `docs/e2e-verification.md`。 |

## Task 12 端到端验收清单

| 验收项 | 状态 | 说明 |
| --- | --- | --- |
| 能导入母版（选剪映草稿文件夹 → 打包上传 → 返回槽位） | 未执行/需人工联调 | 缺失条件：真实运行中的后端、包含 `draft_content.json` 的真实剪映草稿、剪映专业版客户端。 |
| 能配置 5 类素材槽位（video/audio/bgm/subtitle/cover） | 未执行/需人工联调 | 缺失条件：真实母版上传后由后端返回槽位列表，并在客户端完成配置保存。 |
| 能为槽位选择本地素材并自动读元数据 | 未执行/需人工联调 | 缺失条件：本地视频、音频、字幕、封面素材，以及可运行客户端窗口。 |
| 能生成草稿并下载 | 未执行/需人工联调 | 缺失条件：后端生成任务、任务轮询接口和下载接口可用。 |
| 草稿自动解压导入剪映 draft 目录 | 未执行/需人工联调 | 缺失条件：本机剪映草稿目录可写，并能观察生成目录。 |
| 字幕样式基本保留（字体/颜色/位置） | 未执行/需人工联调 | 缺失条件：后端生成草稿后，在剪映中打开并人工比对字幕样式。 |
| 时长对齐正确（配音基准） | 未执行/需人工联调 | 缺失条件：包含配音基准的真实用例，以及后端生成结果。 |
| 服务器地址可在设置页配置 + 测试连接 | 未执行/需人工联调 | 缺失条件：客户端开发窗口和可访问的后端服务。 |
| 错误信息用户友好（不出现技术术语给最终用户） | 未执行/需人工联调 | 缺失条件：人工触发网络失败、素材缺失、后端失败等路径并检查 UI 文案。 |
| Windows 可打包为 .exe 安装包 | 已执行 | 2026-07-07 复验通过，`npm run pack:win` 生成安装包 `dist/VectCut 模板套版-Setup-1.0.0-x64.exe` 和便携版 `dist/VectCut 模板套版-Portable-1.0.0-x64.exe`。 |
| 安装指南含 SmartScreen 绕过说明 | 已自动化覆盖 | `desktop/tests/packaging-config.test.ts` 检查 `desktop/docs/install-guide.md` 包含 SmartScreen、更多信息、仍要运行等说明。 |

## 规格 §18.4 MVP 验收清单

### 功能验收

| 验收项 | 状态 | 说明 |
| --- | --- | --- |
| 能导入 3 种不同风格的母版（口播/Vlog/教程） | 未执行/需人工联调 | 缺失条件：3 个真实剪映草稿母版和后端上传解析环境。 |
| 能配置 5 类素材槽位（video/audio/bgm/subtitle/cover） | 未执行/需人工联调 | 需以后端返回的槽位数据为准。 |
| 能生成草稿并在剪映中打开 | 未执行/需人工联调 | 需完成后端生成、客户端下载、自动解压和剪映打开验证。 |
| 字幕样式基本保留（字体/颜色/位置） | 未执行/需人工联调 | 需在剪映中人工比对。 |
| 时长对齐正确（配音基准） | 未执行/需人工联调 | 需后端配合验证。 |

### 质量验收

| 验收项 | 状态 | 说明 |
| --- | --- | --- |
| 核心假设验证报告完成（§0） | 未执行/需人工联调 | 本任务只记录 Task 12 桌面端验收，不补写规格 §0 报告。 |
| Golden 测试通过（至少 3 个固定用例） | 未执行/需人工联调 | 缺失条件：固定母版、素材和后端生成结果。 |
| 边界情况测试通过（§7.0 定义的场景） | 未执行/需人工联调 | 缺失条件：规格 §7.0 对应样例和人工/自动化执行环境。 |
| 错误信息用户可理解（不出现技术术语） | 未执行/需人工联调 | 需在 UI 中触发失败路径检查。 |

### 文档验收

| 验收项 | 状态 | 说明 |
| --- | --- | --- |
| 母版制作指南（§16） | 未执行/需人工联调 | 未在本任务范围内新增。 |
| 不支持特性清单（§17） | 未执行/需人工联调 | 未在本任务范围内新增。 |
| 用户使用文档（快速开始 + 常见问题） | 部分自动化覆盖 | `desktop/docs/install-guide.md` 覆盖首次使用、服务端配置和常见问题。 |
| 内测用户反馈收集表 | 未执行/需人工联调 | 未在本任务范围内新增。 |

## 后端联调步骤

真实端到端验收需要按以下步骤执行：

```bash
# 1. 启动后端
cd ..
python run_http.py

# 2. 启动客户端
cd desktop
npm run dev
```

随后准备一个真实剪映草稿作为母版，草稿目录内必须包含 `draft_content.json`。在客户端走完整 4 步向导：

1. 导入母版：选择剪映草稿文件夹，打包上传，确认后端返回槽位列表。
2. 配置槽位：保存 video、audio、bgm、subtitle、cover 五类槽位配置。
3. 填充素材：为槽位选择本地素材，确认元数据自动填充。
4. 生成并导入：生成草稿，确认返回 `task_id`，下载 zip，自动解压到剪映 draft 目录，并在剪映专业版中看到新草稿。

人工验收时还需要检查：

- 字幕样式基本保留：字体、颜色、位置。
- 时长对齐正确：以配音为基准。
- 失败路径错误信息面向最终用户，不暴露堆栈、内部异常名或技术术语。

## 未执行/需人工联调项目

以下项目不能仅凭当前自动化命令判定通过：

- 后端 `python run_http.py` 是否在本机成功启动，并能完成上传、生成、轮询、下载接口链路。
- 客户端 `npm run dev` 的真实 Electron 窗口交互。
- 真实剪映草稿导入、生成草稿在剪映专业版内打开。
- 字幕样式保留和配音基准时长对齐。
- 3 种风格母版（口播/Vlog/教程）、Golden 测试和边界情况测试。

缺失条件补齐后，请按“后端联调步骤”逐项重新验收，并把结果补充回本报告。

## 2026-07-07 本机真实母版验证记录

### 输入

- 母版目录：`D:\Program Files (x86)\JianyingPro Drafts\@模板【双楠】`
- 素材目录：`G:\剪映剪辑\小说素材\素材`
- 剪映草稿根目录：`D:\Program Files (x86)\JianyingPro Drafts`

### 自动化与构建验证

| 验证项 | 命令 | 结果 |
| --- | --- | --- |
| 桌面单测 | `cd desktop && npm test` | 15 个测试文件、199 个测试通过。 |
| 桌面类型检查 | `cd desktop && npx tsc --noEmit -p tsconfig.json && npx tsc --noEmit -p tsconfig.node.json` | 通过。 |
| 桌面构建 | `cd desktop && npm run build` | 通过，生成 `out/main`、`out/preload`、`out/renderer`。 |
| packer/mediaProbe/jianyingDir 单测 | `cd desktop && npm test -- packer mediaProbe jianyingDir` | 3 个测试文件、56 个测试通过。 |
| 后端相关测试 | `python -m pytest tests/features/template_filling/test_service_integration.py tests/core/test_pyjianying_assumptions.py -q` | 14 个通过、3 个跳过。 |

### 本机文件与素材验证

| 验证项 | 结果 |
| --- | --- |
| 母版目录存在 | 通过，目录根下存在 `draft_content.json`。 |
| 母版体积 | 70 个文件，总大小约 398.87MB。 |
| 客户端同类打包产物 | `Compress-Archive` 生成 ZIP 约 227.16MB。 |
| 素材目录存在 | 通过。 |
| 素材类型统计 | 发现视频、图片、音频；未发现 `.srt`，仅发现 1 个 `.txt`。 |
| ffprobe 视频探测 | `merged_video_0min_batch5.mp4` 可探测，1080x1920，0.084s。 |
| ffprobe BGM 探测 | `12 NOT AT ONE.m4a` 可探测，约 39.997s。 |
| ffprobe 封面图探测 | `微信图片_20251001143228_55808_1.jpg` 可探测，570x687。 |

### 真实母版导入链路验证

| 验证项 | 结果 | 证据 |
| --- | --- | --- |
| 直接读取当前 `draft_content.json` | 失败 | `pyJianYingDraft.Script_file.load_template` 报 `JSONDecodeError: Extra data: line 1 column 2 (char 1)`。 |
| 解密当前 `draft_content.json` | 通过 | `python scripts\jy_decrypt.py ...` 返回 `ok=True`，明文 139628 字节，合法 JSON。 |
| 明文哈希对比 | 通过 | 解密结果与 `tests/golden/shuangnan.plain.json` SHA256 均为 `8a305cab99f3208142a4072207accba3dfe128d91afbae85f20031cbba66d9a5`。 |
| HTTP 导入密文 ZIP | 失败 | `/api/template/import` 返回 `T_INVALID_ZIP`，reason 为 `Extra data: line 1 column 2 (char 1)`。 |
| HTTP 导入明文 ZIP | 部分通过 | 返回成功，但只扫描出 1 个槽位：`subtitle__0`。 |
| 槽位类型覆盖 | 失败 | 实际只有 `subtitle`，未识别出 video/audio/bgm/cover。 |
| 保存明文槽位配置 | 通过 | `/api/template/slot-config` 返回成功，`slot_count=1`。 |
| 渲染明文槽位 | 失败 | `/api/template/render` 返回 `S_INVALID_SLOT`，原因是槽位 `track_name` 为空字符串。 |

### 当前结论

这份真实母版目前不能完成桌面端“导入母版 → 配置 5 类槽位 → 填素材 → 生成并导入剪映”的端到端验收。阻塞点按执行顺序为：

1. 当前母版打包后约 227.16MB，超过桌面 `readZipFile` 的 100MB 上限，也超过后端默认 `max_template_zip_mb=50`。
2. 当前 `draft_content.json` 是剪映加密格式，后端导入链路不会自动解密，上传后会返回 `T_INVALID_ZIP`。
3. 即使先用本机 `videoeditor.dll` 解密成明文，现有槽位扫描只能识别出 1 个顶层 `subtitle` 槽位；该母版的主要内容位于嵌套 composition/draft 结构中。
4. 该唯一 `subtitle` 槽位的 `track_name` 为空，保存配置后渲染阶段会被 `S_INVALID_SLOT` 拦截。

### 后续修复清单

- 桌面端与后端上传大小限制需要统一配置；至少要能覆盖本机 227MB 级真实母版，或在 UI 中提前给出明确错误。
- 后端导入真实剪映 8.9/10.x 母版前，需要支持加密 `draft_content.json` 的解密，或要求用户先导出/提供明文草稿。
- `template_filling` 槽位扫描需要支持嵌套 `materials.drafts[].draft.tracks`，不能只扫描顶层 `tracks/imported_tracks`。
- 槽位扫描遇到空轨道名时需要生成稳定可解析的 track 标识，避免 `track_name=""` 通过导入但在渲染阶段失败。
- 需要准备真实 `.srt` 字幕文件，或在桌面端允许用 `.txt` 作为字幕输入时明确转换/校验为 SRT。

## 2026-07-07 本机真实母版验证记录：书亦青黛

### 输入

- 母版目录：`D:\Program Files (x86)\JianyingPro Drafts\书亦青黛`
- 素材目录：`G:\剪映剪辑\小说素材\素材`
- 剪映草稿根目录：`D:\Program Files (x86)\JianyingPro Drafts`

### 本机文件与格式验证

| 验证项 | 结果 |
| --- | --- |
| 母版目录存在 | 通过，目录根下存在 `draft_content.json`。 |
| 母版体积 | 77 个文件，总大小约 415.51MB。 |
| 客户端同类打包产物 | `Compress-Archive` 生成 ZIP 约 238.86MB。 |
| 直接读取当前 `draft_content.json` | 失败，`pyJianYingDraft.Script_file.load_template` 报 `JSONDecodeError: Extra data: line 1 column 2 (char 1)`。 |
| 解密当前 `draft_content.json` | 通过，`python scripts\jy_decrypt.py ...` 返回 `ok=True`，明文 2445670 字节，合法 JSON。 |

### 明文槽位扫描

| 验证项 | 结果 |
| --- | --- |
| pyJianYingDraft 加载明文 | 通过。 |
| 顶层轨道统计 | `tracks=0`、`imported_tracks=11`。 |
| 槽位数量 | 37 个槽位。 |
| 槽位类型 | `video=35`、`subtitle=1`、`audio=1`。 |
| BGM/cover 槽位 | 未识别出 `bgm`、`cover_image`、`cover_title`。 |
| 空轨道名 | 37/37 个槽位的 `track_name` 都是空字符串。 |

### HTTP 链路验证

| 验证项 | 结果 | 证据 |
| --- | --- | --- |
| HTTP 导入密文 ZIP | 失败 | `/api/template/import` 返回 `T_INVALID_ZIP`，reason 为 `Extra data: line 1 column 2 (char 1)`。 |
| HTTP 导入明文 ZIP | 部分通过 | 返回成功，扫描出 37 个槽位：35 video、1 subtitle、1 audio。 |
| 保存明文槽位配置 | 通过 | `/api/template/slot-config` 返回成功，`slot_count=37`。 |
| 渲染明文槽位 | 失败 | `/api/template/render` 返回 `S_INVALID_SLOT`，原因是第一个 video 槽位 `track_name` 为空字符串。 |

### 当前结论

`书亦青黛` 比 `@模板【双楠】` 更接近现有扫描模型：解密后可以识别出 video/audio/subtitle 槽位。但它仍不能完成端到端验收：

1. 实际打包 ZIP 约 238.86MB，超过桌面 `readZipFile` 的 100MB 上限，也超过后端默认 `max_template_zip_mb=50`。
2. 当前 `draft_content.json` 是剪映加密格式，后端不会自动解密，直接上传会返回 `T_INVALID_ZIP`。
3. 解密后虽然能扫描 37 个槽位，但所有槽位 `track_name` 都为空，保存配置后渲染阶段会返回 `S_INVALID_SLOT`。
4. 当前扫描结果仍不覆盖 5 类槽位；缺少 `bgm`、`cover_image`、`cover_title`。

### 后续修复清单增量

- 槽位解析不能依赖非空 `track.name`；真实剪映模板常见空轨道名，需要使用轨道 id、轨道序号或其它稳定定位信息。
- `slot_resolver.resolve_slot_to_track` 需要支持空轨道名场景，或导入阶段就生成可回查的内部轨道标识。
- 需要区分普通 `audio` 与 `bgm` 的真实模板判定策略；该母版有 1 个 audio 但未被归类为 bgm。
- 若要验证 5 类槽位，还需要 cover 槽位扫描/配置/渲染实现，而不是依赖当前自动扫描结果。

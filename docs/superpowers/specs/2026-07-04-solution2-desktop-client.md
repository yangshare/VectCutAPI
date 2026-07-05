# 方案二：Electron 桌面客户端 + 云端元数据套版

- 日期：2026-07-04
- 最后更新：2026-07-05（补充核心假设验证、MVP 范围、风险强化）
- 状态：待评审（已采纳客户端形态 = 桌面客户端）
- 范围：基于 VectCutAPI 的「模板套版」后端 feature + Electron 桌面客户端
- 核心思路：**素材不上传云端，只传元数据（路径/大小/时长）；桌面客户端拿真实路径，云端用元数据生成草稿**

## 0. 核心假设验证（开发前必做）⚠️

**在投入完整开发前，必须验证以下关键假设。如果验证失败，需及时调整方案。**

### 0.1 验证目标

| 假设 | 验证方法 | 通过标准 | 风险等级 |
|------|---------|---------|---------|
| **pyJianYingDraft 生成的草稿剪映可打开** | 手动修改 draft_content.json 中的素材路径并保存，剪映打开验证 | 剪映能正常打开草稿并加载修改后的素材 | 🔴 极高 |
| **字幕样式可完整继承** | 提取母版字幕样式 → 应用到新 SRT → 剪映打开验证样式保留 | 字体、大小、颜色、位置、描边至少 90% 保留 | 🔴 高 |
| **多段视频拼接时间轴正确** | 2 段视频拼接对齐配音时长 → 剪映打开验证无跳帧/重叠 | 视频衔接流畅，时间轴与配音完全对齐 | 🟡 中 |
| **循环填充策略可用** | 视频 30 秒、配音 60 秒 → 循环视频至 60 秒 → 剪映验证 | 循环播放自然，无明显接缝 | 🟡 中 |
| **跨版本兼容性** | 用剪映 10.0 生成母版 → 10.5 打开生成草稿 | 草稿能正常打开，样式无丢失 | 🟡 中 |

### 0.2 验证脚本（Python 原型）

```python
# verify_core_assumptions.py
from pyJianYingDraft import Script_file
import shutil

def verify_path_replacement():
    """验证假设 1：修改素材路径后剪映可打开"""
    # 1. 加载真实母版
    master = Script_file.load("path/to/master_draft")
    
    # 2. 复制为临时草稿
    test_draft = master.duplicate_as_template()
    
    # 3. 修改第一个视频片段的路径为另一个本地视频
    video_track = test_draft.Script.get_track_by_type("video")[0]
    video_segment = video_track.get_segments()[0]
    video_segment.material.path = "E:/测试素材/test_video.mp4"  # 真实存在的文件
    video_segment.material.duration = 10_000_000  # 10 秒（微秒）
    
    # 4. 保存
    output_path = test_draft.save("./验证草稿_路径替换")
    
    print(f"✅ 草稿已生成：{output_path}")
    print("📋 请手动打开剪映，导入此草稿，验证：")
    print("   1. 草稿能正常打开（无报错）")
    print("   2. 视频能正常加载（显示画面）")
    print("   3. 播放流畅（无卡顿/黑屏）")
    
    return output_path

def verify_subtitle_style():
    """验证假设 2：字幕样式继承"""
    master = Script_file.load("path/to/master_with_subtitles")
    
    # 提取母版首个字幕样式
    subtitle_track = master.Script.get_track_by_type("text")[0]
    template_segment = subtitle_track.get_segments()[0]
    style = {
        "font": template_segment.text.font,
        "font_size": template_segment.text.font_size,
        "color": template_segment.text.color,
        "alignment": template_segment.text.alignment,
        "border": template_segment.text.border,
        # ... 其他样式属性
    }
    
    # 解析新 SRT
    srt_content = "1\n00:00:01,000 --> 00:00:03,000\n测试字幕"
    # ... 应用样式到新字幕段
    
    print("📋 请验证生成的字幕样式是否与母版一致")
    
# 运行验证
if __name__ == "__main__":
    print("🔍 开始核心假设验证...")
    verify_path_replacement()
    verify_subtitle_style()
```

### 0.3 验证报告模板

完成验证后，创建 `docs/superpowers/specs/2026-07-05-core-assumptions-verification-report.md`，记录：

```markdown
## 验证结果

| 假设 | 结果 | 备注 |
|------|------|------|
| pyJianYingDraft 生成的草稿剪映可打开 | ✅ 通过 / ❌ 失败 | |
| 字幕样式可完整继承 | ✅ 通过 / ⚠️ 部分通过 / ❌ 失败 | 列出不支持的样式 |
| 多段视频拼接时间轴正确 | ✅ 通过 / ❌ 失败 | |
| 循环填充策略可用 | ✅ 通过 / ❌ 失败 | |
| 跨版本兼容性 | ✅ 通过 / ❌ 失败 | 测试的版本号 |

## 发现的问题与调整方案

### 问题 1：字幕动画效果丢失
**现象**：母版字幕有渐入动画，生成草稿后动画消失
**影响**：中等（不影响基本功能，但用户体验下降）
**应对**：MVP 不支持字幕动画，在文档中明确说明

### 问题 2：...
```

**⚠️ 如果关键假设验证失败，立即停止后续开发，调整方案或技术路线。**

---

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

### 7.0 时长对齐边界情况处理

| 场景 | 处理策略 | 验证标准 |
|------|---------|---------|
| **视频总时长 < 配音时长** | 循环最后一段视频填满配音时长 | 循环次数 < 10 次 |
| **最后一段视频 < 2 秒** | ⚠️ 警告用户"视频过短，建议增加视频长度"，但仍允许生成 | 生成时在响应中添加 `warnings` 字段 |
| **视频循环次数 > 10** | ❌ 拒绝生成，返回错误："视频时长不足配音时长，请增加视频片段" | 在校验阶段检测 |
| **无配音槽位** | 回退到"视频总时长为基准"，BGM 对齐视频时长（截断或循环） | BGM 时间轴与视频结束时刻对齐 |
| **无配音 + 有 BGM** | BGM 时长为基准，视频循环至 BGM 时长 | 同样检测循环次数 < 10 |
| **配音/视频/BGM 都为空** | ❌ 拒绝生成，返回错误："至少需要填充一个音视频槽位" | 在校验阶段检测 |
| **BGM < 10 秒且需循环** | ⚠️ 警告用户"BGM 过短，循环可能不自然" | 生成时添加 `warnings` 字段 |

**循环填充算法**（视频不足时）：

```python
def calculate_loop_fill(segments: List[Segment], target_duration: float) -> List[Segment]:
    """计算视频循环填充策略"""
    total_duration = sum(seg.duration for seg in segments)
    
    if total_duration >= target_duration:
        # 截断最后一段
        return truncate_to_duration(segments, target_duration)
    
    gap = target_duration - total_duration
    last_segment = segments[-1]
    
    # 检查最后一段时长
    if last_segment.duration < 2.0:
        # 警告：最后一段过短
        warnings.append(f"最后一段视频仅 {last_segment.duration:.1f} 秒，循环可能不自然")
    
    # 计算需要循环的次数
    loop_count = math.ceil(gap / last_segment.duration)
    
    if loop_count > 10:
        raise ValueError(
            f"视频时长 {total_duration:.1f}s 远小于配音时长 {target_duration:.1f}s，"
            f"需循环最后一段 {loop_count} 次。请增加更多视频片段。"
        )
    
    # 生成循环片段
    result = segments.copy()
    for i in range(loop_count):
        loop_seg = last_segment.clone()
        loop_seg.target_timerange.start = result[-1].target_timerange.end
        loop_seg.target_timerange.end = loop_seg.target_timerange.start + last_segment.duration
        result.append(loop_seg)
        
        if sum(s.duration for s in result) >= target_duration:
            # 截断最后一个循环片段
            result[-1].target_timerange.end = target_duration * 1_000_000
            break
    
    return result
```

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

| type | 替换行为 | 所需元数据 | 支持的样式/特性 |
|------|----------|-----------|----------------|
| **video** | 写入 `material.path`、`duration`、`width/height`；重算 `source_timerange`/`target_timerange` | path、duration、width、height | 保留母版转场、滤镜 |
| **audio（配音）** | 同 video（音频无宽高） | path、duration | 保留母版音量包络 |
| **bgm** | 写入音频素材路径 + duration；**按配音时长截断**（短于配音时循环铺满） | path、duration | 保留母版音量包络 |
| **subtitle** | 整轨重建：解析 SRT 文本 → 套用母版首个字幕片段样式 → 逐句生成 | srt_content | **见 §7.2.1 字幕样式继承** |
| **cover_image** | 写入封面图路径 + 尺寸 | path、width、height | 保留母版位置、裁剪方式 |
| **cover_title** | 改封面标题文本，保留样式 | text | 保留字体、大小、颜色、位置 |

#### 7.2.1 字幕样式继承详细说明

**可继承的样式属性**（MVP 1.0 支持）：

```python
SUPPORTED_SUBTITLE_STYLES = {
    "font_family": "字体名称（需用户系统已安装）",
    "font_size": "字号（px）",
    "color": "文字颜色（RGBA）",
    "alignment": "对齐方式（居中/左/右）",
    "position": "屏幕位置（x, y 坐标）",
    "border_width": "描边宽度",
    "border_color": "描边颜色",
    "background_alpha": "背景透明度",
    "line_spacing": "行间距",
}
```

**不支持的样式特性**（MVP 1.0 不支持，后续迭代）：

- ❌ 字幕动画效果（渐入/渐出/弹跳等）
- ❌ 字幕特效（发光/阴影/3D 旋转）
- ❌ 关键帧动画（位置/大小变化）
- ❌ 多样式混排（同一句话不同颜色）
- ❌ 自定义字体嵌入（需用户系统已安装字体）

**样式继承策略**：

1. **母版有多个字幕片段** → 提取首个字幕片段的样式作为模板
2. **母版字幕为空** → 使用默认样式（黑体/36px/白色/居中/底部）
3. **母版字幕使用自定义字体** → 检测用户系统是否安装，未安装则：
   - Windows：回退到"微软雅黑"
   - Mac：回退到"PingFang SC"
   - 在响应 `warnings` 中提示用户

**字幕重建流程**：

```python
def rebuild_subtitle_track(master_style, new_srt_content, base_duration):
    """重建字幕轨道"""
    # 1. 解析新 SRT
    subtitles = parse_srt(new_srt_content)
    
    # 2. 校验时间轴在基准时长内
    for sub in subtitles:
        if sub.end_time > base_duration:
            warnings.append(f"字幕 '{sub.text}' 结束时间超出配音时长，已截断")
            sub.end_time = base_duration
    
    # 3. 应用母版样式
    segments = []
    for sub in subtitles:
        seg = create_text_segment(
            text=sub.text,
            start=sub.start_time,
            end=sub.end_time,
            style=master_style,  # 套用母版样式
        )
        segments.append(seg)
    
    return segments
```

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

### 8.7 服务器地址配置

**MVP 方案**（硬编码 + 可覆盖）：

```typescript
// src/config/server.ts
const DEFAULT_SERVER_URL = 'https://api.vectcut.com';  // 默认指向你部署的服务器

export function getServerUrl(): string {
  // 1. 优先读取用户配置
  const userConfig = loadUserConfig();  // 从 ~/.vectcut/config.json 读取
  if (userConfig?.serverUrl) {
    return userConfig.serverUrl;
  }
  
  // 2. 回退到默认地址
  return DEFAULT_SERVER_URL;
}

export function setServerUrl(url: string): void {
  const config = loadUserConfig() || {};
  config.serverUrl = url;
  saveUserConfig(config);
}
```

**设置页面**（后续迭代）：

```tsx
// src/pages/Settings.tsx
function ServerSettings() {
  const [serverUrl, setServerUrl] = useState(getServerUrl());
  const [testing, setTesting] = useState(false);
  const [status, setStatus] = useState<'success' | 'error' | null>(null);
  
  const testConnection = async () => {
    setTesting(true);
    try {
      const res = await fetch(`${serverUrl}/api/health`);
      setStatus(res.ok ? 'success' : 'error');
    } catch {
      setStatus('error');
    }
    setTesting(false);
  };
  
  return (
    <div>
      <label>服务器地址</label>
      <input value={serverUrl} onChange={e => setServerUrl(e.target.value)} />
      <button onClick={testConnection} disabled={testing}>
        {testing ? '测试中...' : '测试连接'}
      </button>
      {status === 'success' && <span>✅ 连接成功</span>}
      {status === 'error' && <span>❌ 连接失败，请检查地址</span>}
    </div>
  );
}
```

**本地开发模式**：

```typescript
// .env.development
VITE_SERVER_URL=http://localhost:9001

// .env.production
VITE_SERVER_URL=https://api.vectcut.com
```

## 9. 为什么桌面客户端解决了 Web 的硬伤

| 问题（纯 Web） | 桌面客户端解法 |
|----------------|---------------|
| 浏览器拿不到真实路径（`C:\fakepath\`） | Electron `dialog` 返回真实绝对路径，写入草稿后剪映能加载 |
| 无法自动定位剪映草稿目录 | Node.js 文件系统访问，自动探测 Win/Mac 路径 |
| 母版需用户手动打 ZIP | 客户端自动扫描草稿目录 + 自动打包 |
| 草稿下载需手动解压到剪映目录 | 客户端自动解压 + 复制 + 提示打开剪映 |

**核心能力仍在云端**：客户端只是"采集器 + 下载器"，套版逻辑、引擎、样式继承全在服务端。

### 9.1 剪映版本兼容性策略

**MVP 1.0 版本支持**：

- ✅ **剪映专业版 10.0 - 10.9**（Windows/Mac）
- ❌ 剪映移动版（不支持草稿导入）
- ❌ CapCut 国际版（草稿格式差异）

**版本检测机制**：

```typescript
// 客户端启动时检测剪映版本
async function detectJianyingVersion(): Promise<string | null> {
  const jianyingPath = detectJianyingInstallPath();
  if (!jianyingPath) return null;
  
  // 读取版本信息（不同 OS 方法不同）
  const version = await readVersionFile(jianyingPath);
  return version;  // 例如 "10.5.0"
}

function isVersionSupported(version: string): boolean {
  const major = parseInt(version.split('.')[0]);
  const minor = parseInt(version.split('.')[1]);
  
  return major === 10 && minor >= 0 && minor <= 9;
}

// 启动时检查
const version = await detectJianyingVersion();
if (version && !isVersionSupported(version)) {
  showWarning(
    `检测到剪映版本 ${version}，本工具当前仅支持 10.0-10.9 版本。\n` +
    `生成的草稿可能无法正常打开，建议升级/降级剪映。`
  );
}
```

**profile 字段映射**：

```python
# vectcut/core/config.py
SUPPORTED_PROFILES = {
    "jianying_pro_10": {
        "version_range": "10.0-10.9",
        "draft_format_version": "2.9.0",  # draft_content.json 的 format_version
        "features": ["subtitle_style", "cover_image", "transition"],
    },
    # 后续扩展
    "jianying_pro_11": {
        "version_range": "11.0+",
        "draft_format_version": "3.0.0",
        "features": ["subtitle_style", "cover_image", "transition", "keyframe_animation"],
    }
}
```

**跨版本升级策略**：

1. **监控草稿格式变化**：剪映每次大版本更新后，手动测试草稿格式是否兼容
2. **渐进式支持**：新版本剪映发布后，创建对应 profile，通过配置开关
3. **降级提示**：如果用户剪映版本过新，提示"该版本暂未支持，请关注更新"
4. **社区反馈**：鼓励用户报告新版本兼容性问题，快速迭代

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
| **核心假设未验证**（pyJianYingDraft 生成草稿剪映无法识别） | 🔴 极高 | §0 核心假设验证必须在开发前完成；失败则调整技术路线 |
| **字幕样式继承不完整**（动画/特效丢失） | 🔴 高 | §7.2.1 明确 MVP 只支持基础样式；§17 列出不支持特性清单 |
| **剪映版本升级导致格式变化** | 🟡 中 | §9.1 版本检测机制；监控剪映更新，及时适配新 profile |
| **用户素材路径变动**（移动/重命名） | 🟡 中 | ① 生成前客户端校验路径存在性；② 生成时记录文件 MD5（见下方增强方案）；③ 提供"路径修复工具"（后续迭代） |
| **跨平台路径格式**（Win/Mac） | 🟡 中 | 客户端探测 OS，草稿按用户系统格式写路径；生成时验证路径格式合法性 |
| **元数据采集不准** | 低 | ffprobe 精度足够；边界情况单测覆盖（0 字节文件、损坏文件） |
| **剪映目录探测失败**（自定义安装路径） | 低 | 客户端让用户手动指定一次，记忆配置到 `~/.vectcut/config.json` |
| **客户端分发与更新** | 低 | electron-updater + GitHub Release，灰度推送；§13.1 代码签名策略 |
| **母版 ZIP 体积** | 低 | 母版草稿目录通常几 MB（含缩略图），限制 50MB；服务端校验 |
| **代码签名/杀软误报** | 低 | §13.1 详细说明 |

### 13.1 素材路径变动增强方案（后续迭代）

**问题场景**：
1. 用户生成草稿时素材在 `E:/素材/第5期/video.mp4`
2. 几天后移动到 `D:/归档/2026-07/video.mp4`
3. 打开剪映时报错"素材文件不存在"

**增强方案**（非 MVP，后续迭代）：

```typescript
// 生成草稿时记录素材元信息
interface MaterialRecord {
  slotId: string;
  originalPath: string;
  fileName: string;
  fileSizeMB: number;
  md5Hash: string;  // 文件哈希，用于检索
  createdAt: string;
}

// 保存到 ~/.vectcut/materials-history.json
async function recordMaterial(path: string, slotId: string) {
  const stats = await fs.stat(path);
  const hash = await calculateMD5(path);
  
  const record: MaterialRecord = {
    slotId,
    originalPath: path,
    fileName: basename(path),
    fileSizeMB: stats.size / 1024 / 1024,
    md5Hash: hash,
    createdAt: new Date().toISOString(),
  };
  
  saveMaterialRecord(record);
}

// 路径修复工具（客户端菜单 → 工具 → 修复草稿路径）
async function repairDraftPaths(draftPath: string) {
  const draft = loadDraft(draftPath);
  const missingPaths = findMissingMaterialPaths(draft);
  
  for (const path of missingPaths) {
    const record = findMaterialRecord(path);  // 从历史记录查找
    
    // 尝试智能搜索
    const candidates = await searchFileByHash(record.md5Hash, [
      'E:/', 'D:/', 'C:/Users/用户名/Videos'  // 常见路径
    ]);
    
    if (candidates.length === 1) {
      // 自动修复
      updateDraftPath(draft, path, candidates[0]);
    } else if (candidates.length > 1) {
      // 让用户选择
      const choice = await showPathSelector(candidates);
      updateDraftPath(draft, path, choice);
    } else {
      // 手动选择文件
      const newPath = await dialog.showOpenDialog({
        title: `找不到素材：${record.fileName}，请手动选择`,
        filters: [{name: '视频', extensions: ['mp4', 'mov']}]
      });
      updateDraftPath(draft, path, newPath);
    }
  }
  
  saveDraft(draft);
}
```

### 13.2 代码签名与分发策略

**Windows 代码签名**：

| 阶段 | 策略 | 成本 | 用户体验 |
|------|------|------|---------|
| **MVP 内测**（< 50 人） | 不签名，提供"如何绕过 SmartScreen"文档 | ¥0 | 较差，需手动"仍要运行" |
| **公测**（50-500 人） | 购买 EV 代码签名证书（1 年） | ¥3000-5000 | 良好，无拦截 |
| **正式发布** | EV 证书 + 累积信誉 | ¥3000-5000/年 | 优秀 |

**Mac 代码签名**：

- 必须有 Apple Developer 账号（$99/年）
- 使用 `electron-builder` 自动签名 + 公证（notarize）
- 不签名的 Mac 应用无法在 macOS 10.15+ 上打开（Gatekeeper 强制）

**MVP 绕过 SmartScreen 指南**（给内测用户）：

```markdown
## Windows 安装提示"Windows 已保护你的电脑"

这是因为应用尚未购买代码签名证书。请按以下步骤继续安装：

1. 点击"更多信息"
2. 点击"仍要运行"
3. 安装完成后，应用可正常使用

**安全说明**：本应用代码完全开源，可在 GitHub 查看源码。后续版本将购买证书签名。
```

## 14. 阶段划分（每阶段可独立验证）

| 阶段 | 内容 | 风险 | 验收标准 |
|------|------|------|---------|
| **阶段 0：核心假设验证** ⚠️ | §0 定义的 5 个假设验证 + 验证报告 | 🔴 极高 | 所有假设通过或有明确降级方案；写出验证报告 |
| **阶段 A：后端 feature 骨架** | `template_filling` 包 + schemas + storage + import/save_slot_config 两接口 + 单测 | 低 | 能导入母版、保存槽位配置；单测通过 |
| **阶段 B：render_draft 核心** | duplicate + 5 类替换 + 字幕样式继承 + golden 基线 | 🔴 高 | 能生成完整草稿；golden 测试通过；手动剪映打开验证 |
| **阶段 C：错误处理 + 边界** | 异常映射 + 槽位留空 + 时长策略覆盖（§7.0 边界情况） | 中 | 边界情况测试全通过；错误信息用户友好 |
| **阶段 D：最小化客户端** | 命令行工具或简化 Electron（单页面） | 中 | 能完成完整流程（导入母版 → 填素材 → 生成 → 剪映打开） |
| **阶段 E：完整桌面客户端** | 四个 React 页面 + 自动探测剪映目录 + 自动导入 | 中 | 用户体验完整；可给外部用户试用 |
| **阶段 F：打磨与分发** | 自动更新 + 错误诊断 + 使用文档 + 打包签名 | 低 | 可公开发布 |

**关键调整**：
1. **阶段 0 是前置必做**：验证失败则停止或调整方案
2. **阶段 D 简化为最小化客户端**：不直接做完整 Electron，先用命令行/简易 GUI 验证完整流程
3. **阶段 E 才是完整 Electron**：积累真实反馈后再投入完整 UI 开发

每阶段结束跑 golden + 全量测试，绿了即可 review。

### 14.1 阶段 0 验证时间表（建议 3-5 天）

| 天数 | 任务 | 产出 |
|------|------|------|
| **Day 1** | 编写验证脚本（§0.2），准备 3 个测试母版 | `verify_core_assumptions.py` |
| **Day 2** | 运行验证 1-3（路径替换、字幕样式、时长对齐） | 3 个测试草稿 + 手动剪映验证 |
| **Day 3** | 运行验证 4-5（循环填充、版本兼容性） | 2 个测试草稿 + 手动剪映验证 |
| **Day 4** | 整理验证结果，写验证报告 | `2026-07-05-core-assumptions-verification-report.md` |
| **Day 5** | Review 验证报告，决策是否继续 | Go/No-Go 决策 |

**Go 条件**（至少满足）：
- ✅ 验证 1（路径替换）必须通过
- ✅ 验证 2（字幕样式）至少部分通过（基础样式可继承）
- ✅ 验证 3-5 中至少 2 个通过

**No-Go 触发条件**：
- ❌ 验证 1 失败：剪映无法识别 pyJianYingDraft 生成的草稿
- ❌ 验证 2 完全失败：任何字幕样式都无法继承

### 14.2 阶段 D 最小化客户端方案选择

**方案对比**：

| 方案 | 开发时间 | 优点 | 缺点 | 建议 |
|------|---------|------|------|------|
| **命令行工具**（Python） | 2-3 天 | 最快验证流程；无 UI 复杂度 | 用户体验差；无法给非技术用户 | ✅ 内部验证首选 |
| **简化 Electron**（单页面） | 5-7 天 | 可给外部用户；验证核心交互 | 仍需 Electron 配置 | ✅ 有外部测试用户时 |
| **完整 Electron** | 15-20 天 | 完整体验 | 时间成本高；过早投入 UI | ❌ 阶段 E 再做 |

**命令行工具示例**：

```bash
# 安装
pip install vectcut-cli

# 使用
vectcut import-template ~/Movies/JianyingPro/Draft/dfd_xxx --name "口播模板"
vectcut config-slots template_001  # 交互式配置槽位
vectcut fill template_001 \
  --video1 ~/素材/video1.mp4 \
  --audio ~/素材/dubbing.mp3 \
  --bgm ~/素材/bgm.mp3 \
  --subtitle ~/素材/subtitle.srt \
  --output "第5期"
  
# 输出
✅ 草稿已生成：~/Movies/JianyingPro/Draft/dfd_第5期_20260705
📋 打开剪映即可看到新草稿
```

## 15. 已确认的产品决策

1. **时长基准 = 配音时长**：视频、BGM 一律对齐配音时长（口播视频配音为主干）。详见 §7 时长模型。
2. **BGM 策略**：截断到配音时长；BGM 短于配音时循环铺满。
3. **视频对齐策略**：多段拼接对齐配音时长，超出末段截断、不足时循环最后一段视频填满配音时长。循环次数限制 ≤ 10 次（§7.0）。
4. **母版上传方式**：用户手动选母版草稿文件夹（客户端不自动扫描剪映目录）。
5. **草稿导入剪映**：生成后客户端自动复制到剪映草稿目录。
6. **客户端分发渠道**：GitHub Release。
7. **支持剪映版本**：MVP 1.0 仅支持剪映专业版 10.0-10.9（§9.1）。
8. **字幕样式继承范围**：MVP 1.0 仅支持基础样式（字体/大小/颜色/位置/描边），不支持动画/特效（§7.2.1）。
9. **开发前必做核心假设验证**：§0 定义的验证必须通过才能继续（§14）。

---

## 16. 母版制作指南

**为什么需要指南**：不是所有剪映草稿都适合做模板。本指南帮助用户制作"可套版"的母版。

### 16.1 适合做模板的母版特征

✅ **推荐的母版结构**：

```
口播视频母版（典型）
├── 视频轨（主轨）
│   ├── 片段 1：开场视频（5 秒）
│   ├── 片段 2：主内容视频 1（30 秒）
│   ├── 片段 3：主内容视频 2（40 秒）
│   └── 片段 4：结尾视频（10 秒）
├── 音频轨（配音）
│   └── 片段 1：完整配音（85 秒，覆盖全视频）
├── 音乐轨（BGM）
│   └── 片段 1：背景音乐（85 秒）
├── 字幕轨
│   ├── 片段 1：第一句字幕（样式模板来源）
│   ├── 片段 2：第二句字幕
│   └── ...
└── 其他轨道
    ├── 贴纸（LOGO 水印）
    ├── 转场效果
    └── 滤镜
```

**关键原则**：
- 主视频轨不超过 10 段（避免槽位配置复杂）
- 配音为单段完整音频（不要拼接多段）
- BGM 为单段（不要多首歌曲拼接）
- 字幕使用系统自带字体（微软雅黑/PingFang SC）

### 16.2 支持的母版特性

| 特性 | 是否保留 | 说明 |
|------|---------|------|
| **转场效果** | ✅ 保留 | 视频片段间的转场（淡入淡出/擦除等）会保留 |
| **滤镜** | ✅ 保留 | 整轨或片段滤镜会保留 |
| **音量包络** | ✅ 保留 | 配音/BGM 的音量曲线会保留 |
| **贴纸/水印** | ✅ 保留 | 固定位置的贴纸（LOGO/角标）会保留 |
| **封面图** | ✅ 可替换 | 封面图片和标题文字可替换 |
| **字幕基础样式** | ✅ 可继承 | 字体、大小、颜色、位置、描边 |

### 16.3 不支持的母版特性（§17）

| 特性 | 状态 | 影响 | 应对 |
|------|------|------|------|
| **关键帧动画** | ❌ 不保留 | 素材位置/大小/旋转动画会丢失 | 母版避免使用关键帧 |
| **字幕动画** | ❌ 不保留 | 字幕渐入/弹跳/打字机效果会丢失 | 使用静态字幕 |
| **绿幕抠图** | ❌ 不保留 | 抠图参数会丢失 | 母版避免使用绿幕 |
| **变速效果** | ❌ 不保留 | 视频加速/慢动作会丢失 | 母版使用原速视频 |
| **画中画** | ⚠️ 部分支持 | 仅主轨可替换，画中画轨无法替换 | MVP 建议避免 |
| **蒙版** | ❌ 不保留 | 蒙版效果会丢失 | 母版避免使用蒙版 |
| **自定义字体** | ⚠️ 条件支持 | 用户电脑需已安装该字体 | 使用系统字体更稳定 |

### 16.4 母版制作最佳实践

**步骤 1：规划结构**

```
确定你的内容模板：
- 开场 5 秒（片头动画/LOGO）
- 主体内容（2-3 段视频，每段 20-40 秒）
- 结尾 5 秒（关注提示/片尾）
```

**步骤 2：制作母版草稿**

1. 在剪映中新建项目，导入占位素材（任意视频/音频）
2. 添加转场、滤镜、贴纸等固定元素
3. 添加字幕（第一句使用你想要的样式）
4. 保存草稿，命名清晰（例如"口播模板_v1"）

**步骤 3：验证母版**

在本工具中导入母版，检查：
- ✅ 视频/音频/字幕片段都能正确识别
- ✅ 槽位数量合理（不超过 10 个）
- ✅ 第一句字幕样式是你想要的

**步骤 4：配置槽位**

给每个可替换的片段命名：
- "开场视频" / "主视频1" / "主视频2" / "结尾视频"
- "配音" / "BGM"
- "字幕" / "封面图" / "封面标题"

### 16.5 常见问题

**Q：母版里的视频时长和配音时长不一致怎么办？**
A：没关系。套版时会以配音时长为基准，自动调整视频。

**Q：我想保留母版的开场和结尾，只替换中间怎么办？**
A：配置槽位时只勾选中间的片段，开场/结尾不勾选即可保留。

**Q：字幕样式很复杂（多种颜色/大小），能支持吗？**
A：MVP 1.0 只继承第一句字幕的样式，应用到全部新字幕。复杂样式暂不支持。

---

## 17. 不支持的特性清单（MVP 1.0）

**此清单用于设定用户预期，避免过度承诺。**

### 17.1 母版特性限制

| 特性 | 状态 | 说明 |
|------|------|------|
| 关键帧动画 | ❌ | 位置/大小/旋转/透明度动画会丢失 |
| 字幕动画 | ❌ | 渐入/渐出/弹跳/打字机/滚动效果会丢失 |
| 字幕特效 | ❌ | 发光/阴影/3D 旋转/描边动画会丢失 |
| 绿幕抠图 | ❌ | 抠图参数会丢失，显示原始视频 |
| 变速效果 | ❌ | 加速/慢动作会丢失，恢复原速 |
| 画中画轨 | ⚠️ | 仅主视频轨可替换，画中画轨保留母版内容 |
| 蒙版效果 | ❌ | 蒙版会丢失 |
| 曲线变速 | ❌ | 变速曲线会丢失 |
| 混合模式 | ❌ | 叠加/正片叠底等混合模式会丢失 |

### 17.2 字幕限制

| 限制 | 说明 |
|------|------|
| 多样式混排 | 同一句话不同颜色/大小不支持 |
| 自定义字体 | 需用户电脑已安装；未安装会回退到系统字体 |
| 字幕模板 | 不支持剪映字幕模板（需手动配置样式） |
| 竖排文字 | 不支持，仅支持横排 |
| 字幕路径动画 | 不支持字幕沿路径移动 |

### 17.3 素材限制

| 限制 | 说明 |
|------|------|
| 视频编码 | 建议 H.264/H.265；其他编码可能不兼容 |
| 音频格式 | 建议 MP3/AAC/WAV；其他格式可能不兼容 |
| 图片格式 | 建议 JPG/PNG；GIF 动图不支持 |
| 4K 视频 | 支持，但生成速度较慢 |
| 超长视频 | 单段视频建议 < 30 分钟 |

### 17.4 版本限制

| 限制 | 说明 |
|------|------|
| 剪映版本 | 仅支持剪映专业版 10.0-10.9（Win/Mac） |
| 移动版 | 不支持剪映移动版 |
| CapCut | 不支持 CapCut 国际版 |

### 17.5 后续迭代计划

**优先级高**（下一版本）：
- ✅ 支持画中画轨替换
- ✅ 支持剪映 11.x 版本
- ✅ 字幕样式继承优化（多样式支持）

**优先级中**（2-3 个版本后）：
- ⚠️ 保留关键帧动画
- ⚠️ 保留字幕动画
- ⚠️ 路径修复工具

**优先级低**（待评估）：
- ⚠️ 绿幕抠图支持
- ⚠️ 变速效果支持

---

## 18. MVP 范围定义

**MVP 1.0 目标**：验证核心价值 —— "元数据套版 + 桌面客户端"可行，能给 10-20 个种子用户使用。

### 18.1 MVP 1.0 功能范围

| 功能模块 | 包含 | 不包含 |
|---------|------|--------|
| **母版管理** | ✅ 导入母版 ZIP<br>✅ 查看母版列表 | ❌ 母版编辑<br>❌ 母版分享 |
| **槽位配置** | ✅ 手动勾选可替换片段<br>✅ 给槽位命名 | ❌ 自动识别槽位<br>❌ 槽位模板 |
| **素材填充** | ✅ 选择本地文件<br>✅ 自动读取元数据 | ❌ 素材库管理<br>❌ 历史素材记忆 |
| **生成草稿** | ✅ 5 类素材替换<br>✅ 基础字幕样式继承<br>✅ 时长对齐（配音基准） | ❌ 批量生成<br>❌ 自定义时长策略 |
| **剪映导入** | ✅ 自动复制到剪映目录 | ❌ 自动打开剪映<br>❌ 导入历史记录 |
| **错误处理** | ✅ 基础错误提示<br>✅ 路径校验 | ❌ 详细诊断模式<br>❌ 路径修复工具 |
| **客户端形态** | ✅ 命令行工具 OR 简化 Electron | ❌ 完整四页面 Electron<br>❌ 自动更新 |

### 18.2 MVP 1.0 技术约束

- **支持系统**：Windows 10+ / macOS 11+
- **支持剪映**：剪映专业版 10.0-10.9
- **部署方式**：本地开发环境（不上云）
- **用户规模**：10-20 人内测
- **数据存储**：JSON 文件（不用数据库）

### 18.3 MVP 1.0 成功标准

| 指标 | 目标 |
|------|------|
| **核心流程成功率** | ≥ 80%（导入母版 → 生成草稿 → 剪映打开） |
| **草稿生成时间** | ≤ 10 秒（不含素材上传） |
| **字幕样式保留度** | ≥ 70%（基础样式：字体/大小/颜色/位置） |
| **用户满意度** | ≥ 4/5 分（内测问卷） |
| **严重 Bug** | 0 个（阻断核心流程的 Bug） |

### 18.4 MVP 1.0 验收清单

**功能验收**：
- [ ] 能导入 3 种不同风格的母版（口播/Vlog/教程）
- [ ] 能配置 5 类素材槽位（video/audio/bgm/subtitle/cover）
- [ ] 能生成草稿并在剪映中打开
- [ ] 字幕样式基本保留（字体/颜色/位置）
- [ ] 时长对齐正确（配音基准）

**质量验收**：
- [ ] 核心假设验证报告完成（§0）
- [ ] Golden 测试通过（至少 3 个固定用例）
- [ ] 边界情况测试通过（§7.0 定义的场景）
- [ ] 错误信息用户可理解（不出现技术术语）

**文档验收**：
- [ ] 母版制作指南（§16）
- [ ] 不支持特性清单（§17）
- [ ] 用户使用文档（快速开始 + 常见问题）
- [ ] 内测用户反馈收集表

### 18.5 MVP 1.0 之后

**MVP 1.5**（30-50 人公测）：
- 完整 Electron 客户端（四页面）
- 自动更新
- 错误诊断模式
- Docker 云端部署

**MVP 2.0**（公开发布）：
- 代码签名
- 剪映 11.x 支持
- 画中画轨支持
- 路径修复工具
- 用户系统（可选）

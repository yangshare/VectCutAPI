# VectCutAPI 完整 API 参考

> **实现状态说明**
>
> 本文档同时反映「现状」与「产品愿景」。每个接口标注实现状态：
>
> - ✅ **已实现** — 当前代码已提供，可直接调用
> - 🔲 **规划中（未实现）** — 产品路线图中的接口，代码尚未提供
>
> 状态依据：`vectcut/server/http/__init__.py`（HTTP 路由挂载）与 `vectcut/server/mcp/registry.py`（MCP 工具注册表）。HTTP 与 MCP 是双入口，两边的工具集**并不完全对称**（详见文末「MCP 工具清单」）。
>
> **HTTP 路由实现总览**：14 个 POST + 1 个统一 GET 入口 `/metadata/{kind}` + 12 个 GET 别名 = 共 27 个路由。响应统一为 `200 + {success, output, error}` 外壳。

## HTTP API 端点

### 核心操作

#### POST /create_draft ✅

创建新的视频草稿项目。

**请求参数:**

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| width | int | 否 | 视频宽度，默认 1080 |
| height | int | 否 | 视频高度，默认 1920 |
| draft_folder | string | 否 | 草稿文件夹路径 |

**常用分辨率:**
- `1080 x 1920` - 竖屏 (短视频/TikTok)
- `1920 x 1080` - 横屏 (YouTube)
- `1080 x 1080` - 方形 (Instagram)

**响应示例:**

```json
{
  "success": true,
  "output": {
    "draft_id": "draft_1234567890",
    "draft_folder": "dfd_xxxxx"
  }
}
```

---

#### POST /save_draft ✅

保存草稿项目并生成下载链接。

**请求参数:**

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| draft_id | string | 是 | 草稿 ID |
| draft_folder | string | 否 | 草稿文件夹路径 |

**响应示例:**

```json
{
  "success": true,
  "output": {
    "draft_url": "https://example.com/draft/downloader?id=xxx",
    "draft_folder": "dfd_xxxxx",
    "message": "草稿已保存"
  }
}
```

---

#### POST /query_draft_status ✅

查询草稿状态。

**请求参数:**

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| task_id | string | 是 | 任务 ID |

---

#### POST /query_script ✅

查询草稿脚本内容。

**请求参数:**

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| draft_id | string | 是 | 草稿 ID |

---

#### POST /generate_draft_url ✅

为已保存的草稿生成下载链接。与 `/save_draft` 的区别：`/save_draft` 会触发保存动作并附带返回链接，`/generate_draft_url` 只针对已存在的草稿生成 URL，不重新保存。

**请求参数:**

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| draft_id | string | 是 | 草稿 ID |

**响应示例:**

```json
{
  "success": true,
  "output": {
    "draft_url": "https://example.com/draft/downloader?id=xxx"
  }
}
```

---

#### POST /add_cover ✅

为已保存的草稿添加封面图与封面文字。

**重要说明:**
- 必须先调用 `/save_draft` 保存草稿后再调用本接口
- 封面注入直接修改磁盘上的 `draft_info.json` 文件
- 基于剪映 6.x 国内版验证通过的 composition 引用链方案

**请求参数:**

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| draft_id | string | 是 | 草稿 ID |
| cover_url | string | 是 | 封面图片 URL (本地或远程) |
| cover_text | string | 否 | 封面文字（可选） |
| draft_folder | string | 否 | 草稿文件夹路径 |

**响应示例:**

```json
{
  "success": true,
  "output": {
    "draft_id": "draft_1234567890",
    "draft_url": "https://example.com/draft/downloader?id=xxx"
  }
}
```

**使用示例:**

```python
# 1. 先创建并保存草稿
draft = requests.post("http://localhost:9001/create_draft", json={
    "width": 1080,
    "height": 1920
}).json()
draft_id = draft["output"]["draft_id"]

# 2. 添加视频等素材...

# 3. 保存草稿
requests.post("http://localhost:9001/save_draft", json={
    "draft_id": draft_id
})

# 4. 添加封面（必须在保存后）
requests.post("http://localhost:9001/add_cover", json={
    "draft_id": draft_id,
    "cover_url": "https://example.com/cover.jpg",
    "cover_text": "我的视频封面"
})
```

---

### 素材添加

#### POST /add_video ✅

添加视频轨道到草稿。

**请求参数:**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| draft_id | string | 必需 | 草稿 ID |
| video_url | string | 必需 | 视频 URL (本地或远程) |
| start | float | 0 | 视频片段开始时间(秒) |
| end | float | 0 | 视频片段结束时间(秒) |
| target_start | float | 0 | 在时间轴上的开始时间 |
| speed | float | 1.0 | 播放速度 |
| volume | float | 1.0 | 音量 (0.0-1.0) |
| scale_x | float | 1.0 | 水平缩放 |
| scale_y | float | 1.0 | 垂直缩放 |
| transform_x | float | 0 | 水平位置偏移 |
| transform_y | float | 0 | 垂直位置偏移 |
| track_name | string | "video_main" | 轨道名称 |
| relative_index | int | 0 | 相对索引 |
| duration | float | - | 持续时间 |
| transition | string | - | 转场类型 |
| transition_duration | float | 0.5 | 转场时长(秒) |
| mask_type | string | - | 蒙版类型 |
| mask_center_x | float | 0.5 | 蒙版中心 X |
| mask_center_y | float | 0.5 | 蒙版中心 Y |
| mask_size | float | 1.0 | 蒙版大小 |
| mask_rotation | float | 0.0 | 蒙版旋转角度 |
| mask_feather | float | 0.0 | 蒙版羽化度 |
| mask_invert | bool | False | 是否反转蒙版 |
| background_blur | int | - | 背景模糊级别(1-4) |

**转场类型 (transition):**

> ⚠️ 枚举值为**中文**（`Transition_type`，共 361 个成员）。传英文（如 `fade_in`、`wipe_left`）会触发 `Unsupported transition type`。

- `叠化` - 最常用转场（基础混合）
- `万花筒`、`中心旋转`、`三屏放大`
- `上移` / `下滑` / `左移` / `右移`
- 完整列表见 `/get_transition_types` 或 `/metadata/transition`

**蒙版类型 (mask_type):**

> ⚠️ 枚举值为**中文**（`Mask_type`，共 6 个成员）。传英文（如 `circle`、`rect`）会触发 `Unsupported mask type`。

- `圆形` / `矩形` / `线性` / `星形` / `爱心` / `镜面`
- 完整列表见 `/get_mask_types` 或 `/metadata/mask`

**示例:**

```python
# 添加带「叠化」转场的视频
requests.post("http://localhost:9001/add_video", json={
    "draft_id": draft_id,
    "video_url": "https://example.com/video.mp4",
    "start": 5,
    "end": 15,
    "target_start": 0,
    "transition": "叠化",
    "transition_duration": 0.8,
    "volume": 0.7
})
```

---

#### POST /add_audio ✅

添加音频轨道到草稿。

**请求参数:**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| draft_id | string | 必需 | 草稿 ID |
| audio_url | string | 必需 | 音频 URL |
| start | float | 0 | 音频片段开始时间 |
| end | float | None | 音频片段结束时间 |
| target_start | float | 0 | 在时间轴上的开始时间 |
| speed | float | 1.0 | 播放速度 |
| volume | float | 1.0 | 音量 (0.0-1.0) |
| track_name | string | "audio_main" | 轨道名称 |
| duration | float | None | 持续时间 |
| effect_type | string | - | 音频特效类型 |
| effect_params | list | - | 音频特效参数 |
| width | int | 1080 | 项目宽度 |
| height | int | 1920 | 项目高度 |

**音频特效类型 (effect_type):**

> ⚠️ 枚举值为**中文**，按三类子枚举遍历匹配（`resolve_audio_effect` 自动跨子类型查找）：

- **人声/音色特效** (`Tone_effect_type`，57 个)：如 `TVB女声`、`侠客`、`做作夹子音`
- **场景特效** (`Audio_scene_effect_type`，41 个)：如 `Autotune`、`下雨`、`低保真`、`人声增强`
- **语音转歌曲** (`Speech_to_song_type`，6 个)：如 `Lofi`、`嘻哈`、`爵士`、`节奏蓝调`

完整列表见 `/get_audio_effect_types`（或 `/metadata/audio_effect`）。`effect_params` 为 `List[Optional[float]]`。

---

#### POST /add_image ✅

添加图片素材到草稿。

**请求参数:**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| draft_id | string | 必需 | 草稿 ID |
| image_url | string | 必需 | 图片 URL |
| start | float | 0 | 开始时间 |
| end | float | 3.0 | 结束时间 |
| transform_x | float | 0 | 水平位置偏移 |
| transform_y | float | 0 | 垂直位置偏移 |
| scale_x | float | 1.0 | 水平缩放 |
| scale_y | float | 1.0 | 垂直缩放 |
| track_name | string | "image_main" | 轨道名称 |
| relative_index | int | 0 | 相对索引 |
| animation | string | - | 组合动画（`Group_animation_type`，中文枚举） |
| animation_duration | float | 0.5 | 组合动画时长(秒) |
| intro_animation | string | - | 入场动画（`Intro_type`，中文枚举） |
| intro_animation_duration | float | 0.5 | 入场动画时长(秒) |
| outro_animation | string | - | 出场动画（`Outro_type`，中文枚举） |
| outro_animation_duration | float | 0.5 | 出场动画时长(秒) |
| combo_animation | string | - | 组合动画（备用字段） |
| transition | string | - | 转场（`Transition_type`，中文枚举） |
| transition_duration | float | 0.5 | 转场时长(秒) |
| mask_type | string | - | 蒙版（`Mask_type`，中文枚举） |
| mask_center_x / mask_center_y | float | 0.0 | 蒙版中心 |
| mask_size | float | 0.5 | 蒙版大小 |
| mask_rotation | float | 0.0 | 蒙版旋转 |
| mask_feather | float | 0.0 | 蒙版羽化 |
| mask_invert | bool | False | 是否反转蒙版 |
| background_blur | int | - | 背景模糊级别(1-4) |

---

#### POST /add_text ✅

添加文字元素到草稿。

**请求参数:**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| draft_id | string | 必需 | 草稿 ID |
| text | string | 必需 | 文字内容 |
| start | float | 0 | 开始时间 |
| end | float | 5 | 结束时间 |
| font | string | "文轩体" | 字体（`Font_type` 枚举名，可选） |
| font_size | float | 8.0 | 字体大小 |
| font_color | string | "#FF0000" | 字体颜色 (HEX) |
| font_alpha | float | 1.0 | 字体透明度 (0.0-1.0) |
| vertical | bool | False | 是否竖排 |
| transform_x | float | 0 | 水平位置偏移 |
| transform_y | float | 0 | 垂直位置偏移 |
| border_color | string | "#000000" | 描边颜色 |
| border_width | float | 0.0 | 描边宽度（>0 启用） |
| border_alpha | float | 1.0 | 描边透明度 |
| background_color | string | "#000000" | 背景颜色 |
| background_alpha | float | 0.0 | 背景透明度（>0 启用） |
| background_style | int | 0 | 背景样式 |
| background_round_radius | float | 0.0 | 背景圆角半径 |
| background_width | float | 0.14 | 背景宽度 |
| background_height | float | 0.14 | 背景高度 |
| background_horizontal_offset | float | 0.5 | 背景水平偏移 |
| background_vertical_offset | float | 0.5 | 背景垂直偏移 |
| shadow_enabled | bool | False | 是否启用阴影 |
| shadow_alpha | float | 0.9 | 阴影透明度 |
| shadow_angle | float | -45.0 | 阴影角度 |
| shadow_color | string | "#000000" | 阴影颜色 |
| shadow_distance | float | 5.0 | 阴影距离 |
| shadow_smoothing | float | 0.15 | 阴影平滑度 |
| intro_animation | string | - | 入场动画（中文枚举，见下方） |
| intro_duration | float | 0.5 | 入场动画时长(秒) |
| outro_animation | string | - | 出场动画（中文枚举，见下方） |
| outro_duration | float | 0.5 | 出场动画时长(秒) |
| text_styles | array | - | 多样式文字（`List[TextStyleRangeSpec]`，见示例） |
| track_name | string | "text_main" | 轨道名称 |
| width | int | 1080 | 项目宽度 |
| height | int | 1920 | 项目高度 |
| fixed_width | float | -1 | 固定宽度（>0 启用，按比例） |
| fixed_height | float | -1 | 固定高度（>0 启用，按比例） |

**文字动画类型 (intro_animation/outro_animation):**

> ⚠️ 枚举值为**中文**（`Text_intro` 144 个 / `Text_outro` 97 个成员）。传英文会触发 `Unsupported ... animation type`。

- 入场：`乱码故障`、`二段缩放`、`倒数`、`兔子弹跳`、`冰雪飘动`
- 出场：`发光闪出`、`叠影并出`、`右上弹出`、`向上擦除`
- 完整列表见 `/get_text_intro_types`、`/get_text_outro_types`（或 `/metadata/text_intro`、`/metadata/text_outro`）

**多样式文字示例:**

> ⚠️ `text_styles` 每项是 `TextStyleRangeSpec`，颜色/字号等样式需嵌套在 `style` 字段内（`TextStyleSpec`）。直接用 `font_color` 会被忽略，且当 `style` 为 `None` 时访问 `.alpha` 会抛 `'NoneType' object has no attribute 'alpha'`。

```python
requests.post("http://localhost:9001/add_text", json={
    "draft_id": draft_id,
    "text": "多彩文字效果展示",
    "start": 2,
    "end": 8,
    "font_size": 42,
    "text_styles": [
        {"start": 0, "end": 2, "style": {"color": "#FF6B6B"}},
        {"start": 2, "end": 4, "style": {"color": "#4ECDC4"}},
        {"start": 4, "end": 6, "style": {"color": "#45B7D1"}}
    ]
})
```

---

#### POST /add_subtitle ✅

导入 SRT 字幕文件到草稿。

**请求参数:**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| draft_id | string | 必需 | 草稿 ID |
| srt | string | 必需 | SRT 内容，支持三种来源：HTTP(S) URL / 本地文件路径 / 内联 SRT 文本 |
| font | string | "思源粗宋" | 字体（可选） |
| font_size | float | 5.0 | 字体大小 |
| font_color | string | "#FFFFFF" | 字体颜色 (HEX) |
| alpha | float | 1.0 | 字体透明度 |
| bold / italic / underline | bool | False | 加粗/斜体/下划线 |
| vertical | bool | False | 是否竖排 |
| border_color | string | "#000000" | 描边颜色 |
| border_width | float | 0.0 | 描边宽度（>0 启用） |
| border_alpha | float | 1.0 | 描边透明度 |
| background_color | string | "#000000" | 背景颜色 |
| background_style | int | 0 | 背景样式 |
| background_alpha | float | 0.0 | 背景透明度（>0 启用） |
| transform_x | float | 0.0 | 水平位置偏移 |
| transform_y | float | -0.8 | 垂直位置偏移 |
| scale_x / scale_y | float | 1.0 | 水平/垂直缩放 |
| rotation | float | 0.0 | 旋转角度 |
| time_offset | float | 0.0 | 时间偏移(秒) |
| track_name | string | "subtitle" | 轨道名称 |

**SRT 文件格式:**

```srt
1
00:00:00,000 --> 00:00:03,000
这是第一句字幕

2
00:00:03,000 --> 00:00:06,000
这是第二句字幕
```

---

#### POST /add_sticker ✅

添加贴纸到草稿。

**请求参数:**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| draft_id | string | 必需 | 草稿 ID |
| sticker_id | string | 必需 | 贴纸资源 ID（对应引擎 `resource_id`） |
| start | float | 0 | 开始时间 |
| end | float | 5.0 | 结束时间 |
| transform_x | float | 0 | 水平位置偏移 |
| transform_y | float | 0 | 垂直位置偏移 |
| scale_x | float | 1.0 | 水平缩放 |
| scale_y | float | 1.0 | 垂直缩放 |
| rotation | float | 0.0 | 旋转角度 |
| alpha | float | 1.0 | 透明度 |
| flip_horizontal | bool | False | 水平翻转 |
| flip_vertical | bool | False | 垂直翻转 |
| track_name | string | "sticker_main" | 轨道名称 |
| relative_index | int | 0 | 相对索引 |

---

#### POST /add_effect ✅

添加视频特效到草稿。

**请求参数:**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| draft_id | string | 必需 | 草稿 ID |
| effect_type | string | 必需 | 特效类型（中文枚举，见下方） |
| effect_category | string | "scene" | 特效类别：`"scene"`(场景) / `"character"`(角色)，须与 effect_type 匹配 |
| start | float | 0 | 开始时间 |
| end | float | 3.0 | 结束时间 |
| track_name | string | "effect_01" | 轨道名称 |
| params | list | - | 特效参数（`List[Optional[float]]`） |

**特效类型分类:**

> ⚠️ `effect_type` 枚举值为**中文**，且按 `effect_category` 分两套枚举（须匹配类别）：

- **场景特效** (`effect_category="scene"`，`Video_scene_effect_type`，909 个成员)：如 `DV录制框`、`DV界面`、`Ins描边`、`Bling飘落`
- **角色特效** (`effect_category="character"`，`Video_character_effect_type`，226 个成员)：如 `主体冲破屏幕`、`九尾狐`、`X瞬移`、`BOOM`

完整列表见 `/get_video_scene_effect_types`、`/get_video_character_effect_types`（或 `/metadata/video_scene_effect`、`/metadata/video_character_effect`）。

---

#### POST /add_video_keyframe ✅

添加关键帧动画到视频轨道。

**请求参数:**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| draft_id | string | 必需 | 草稿 ID |
| track_name | string | "video_main" | 轨道名称 |
| property_types | list | 必需 | 批量模式：属性类型列表（与 times/values 等长，按位置 zip） |
| times | list | 必需 | 批量模式：关键帧时间点列表 |
| values | list | 必需 | 批量模式：属性值列表（**每项单值字符串**，如 `"1.0"`，非复合 `"1.0,1.0,1.0"`） |
| property_type | string | "alpha" | 单关键帧模式：属性类型 |
| time | float | 0.0 | 单关键帧模式：时间点 |
| value | string | "1.0" | 单关键帧模式：属性值 |

> 批量模式与单关键帧模式二选一：传 `property_types`/`times`/`values` 走批量，否则回退到 `property_type`/`time`/`value`。

**支持的属性类型 (Keyframe_property):**
- `scale_x` / `scale_y` / `uniform_scale` - 缩放
- `position_x` / `position_y` - 位置（范围 -10~10）
- `rotation` - 旋转（可选 `deg` 后缀，如 `"45deg"`）
- `alpha` / `volume` - 透明度/音量（可选 `%` 后缀，如 `"80%"`）
- `brightness` / `contrast` / `saturation` - 亮度/对比度/饱和度（前缀 `+`/`-`）

**示例:**

```python
# 在 t=0/2/4 分别为 scale_x / scale_y / alpha 打关键帧
requests.post("http://localhost:9001/add_video_keyframe", json={
    "draft_id": draft_id,
    "track_name": "video_main",
    "property_types": ["scale_x", "scale_y", "alpha"],
    "times": [0, 2, 4],
    "values": ["1.0", "1.2", "0.8"]
})
```

---

### 查询接口 (GET)

#### GET /metadata/{kind} ✅

元数据查询的**统一入口**，按 `kind` 返回对应枚举列表。支持的 `kind` 取值与下方 12 个旧别名一一对应：

| kind | 等价旧别名 |
|------|------------|
| `intro_animation` | `/get_intro_animation_types` |
| `outro_animation` | `/get_outro_animation_types` |
| `combo_animation` | `/get_combo_animation_types` |
| `transition` | `/get_transition_types` |
| `mask` | `/get_mask_types` |
| `audio_effect` | `/get_audio_effect_types` |
| `font` | `/get_font_types` |
| `text_intro` | `/get_text_intro_types` |
| `text_outro` | `/get_text_outro_types` |
| `text_loop_anim` | `/get_text_loop_anim_types` |
| `video_scene_effect` | `/get_video_scene_effect_types` |
| `video_character_effect` | `/get_video_character_effect_types` |

以下 12 个具名接口为旧别名（与 `/metadata/{kind}` 返回结果逐字一致），保留用于向后兼容：

#### GET /get_intro_animation_types ✅

获取视频入场动画类型列表。

#### GET /get_outro_animation_types ✅

获取视频出场动画类型列表。

#### GET /get_combo_animation_types ✅

获取组合动画类型列表。

#### GET /get_transition_types ✅

获取转场效果类型列表。

#### GET /get_mask_types ✅

获取蒙版类型列表。

#### GET /get_audio_effect_types ✅

获取音频特效类型列表。

#### GET /get_font_types ✅

获取字体类型列表。

#### GET /get_text_intro_types ✅

获取文字入场动画列表。

#### GET /get_text_outro_types ✅

获取文字出场动画列表。

#### GET /get_text_loop_anim_types ✅

获取文字循环动画列表。

#### GET /get_video_scene_effect_types ✅

获取场景特效类型列表。

#### GET /get_video_character_effect_types ✅

获取角色特效类型列表。

---

### 文件上传 🔲 规划中（未实现）

> 以下 4 个接口属于产品路线图，当前代码尚未提供。服务器侧无对应路由实现；客户端 SDK（`vectcut_client.py`）中已有 `/get_duration` 的调用代码，但服务端路由缺失。

#### POST /upload_video 🔲

上传视频文件到服务器。

#### POST /upload_image 🔲

上传图片文件到服务器。

#### GET /list_uploads 🔲

列出已上传的文件。

#### DELETE /delete_upload/<filename> 🔲

删除指定的上传文件。

---

### 高级功能 🔲 规划中（未实现）

> 以下接口属于产品路线图，当前代码尚未提供。
> 注：HTTP 侧无 `/get_duration` 路由；但 **MCP 侧已提供等价的 `get_video_duration` 工具**（详见文末 MCP 清单）。

#### POST /get_duration 🔲

获取媒体文件时长。

**请求参数:**

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| media_url | string | 是 | 媒体 URL |

#### POST /export_to_capcut 🔲

将草稿导出到剪映/CapCut。

#### POST /export_draft_to_video 🔲

将草稿导出为视频文件。

#### GET /export_status 🔲

查询导出状态。

#### POST /execute_workflow 🔲

执行预定义的工作流。

---

## 错误响应

所有 API 端点在出错时返回统一格式：

```json
{
  "success": false,
  "output": "",
  "error": "错误描述信息"
}
```

常见错误:
- 缺少必需参数
- 视频/音频 URL 无效
- 草稿 ID 不存在
- 文件格式不支持

---

## MCP 工具清单 ✅

VectCutAPI 提供 HTTP 与 MCP 双入口，共用 `features.*.service` 业务层。MCP 工具注册表位于 `vectcut/server/mcp/registry.py`，共 **13 个工具**，`inputSchema` 从对应 Pydantic 请求模型自动生成。

| MCP 工具 | 对应 HTTP 路由 | 说明 |
|----------|----------------|------|
| `create_draft` | `/create_draft` ✅ | 创建新的 VectCut 草稿 |
| `add_video` | `/add_video` ✅ | 添加视频，支持转场、蒙版、背景模糊等 |
| `add_audio` | `/add_audio` ✅ | 添加音频，支持音效处理 |
| `add_image` | `/add_image` ✅ | 添加图片，支持动画、转场、蒙版等 |
| `add_text` | `/add_text` ✅ | 添加文本，支持多样式、阴影、背景 |
| `add_subtitle` | `/add_subtitle` ✅ | 添加字幕，支持 SRT 文件和样式 |
| `add_effect` | `/add_effect` ✅ | 添加特效 |
| `add_sticker` | `/add_sticker` ✅ | 添加贴纸 |
| `add_video_keyframe` | `/add_video_keyframe` ✅ | 添加关键帧动画 |
| `add_cover` | `/add_cover` ✅ | 为已保存的草稿添加封面图与封面文字 |
| `get_video_duration` | `/get_duration` 🔲（HTTP 侧未实现） | 获取视频时长 |
| `save_draft` | `/save_draft` ✅ | 保存草稿 |
| `generate_draft_url` | `/generate_draft_url` ✅ | 生成草稿下载链接 |

### 双入口不对称说明

两入口工具集**并非完全对称**，使用时需注意：

- **MCP 独有、HTTP 无对应路由**：`get_video_duration`
- **HTTP 独有、MCP 未暴露**：`query_script`、`query_draft_status`、全部元数据查询接口（`/metadata/{kind}` 及 12 个别名）

不对称的原因：MCP 面向 AI Agent 的「编排/创作」场景，重写轻读；HTTP 面向更完整的服务能力，含状态查询与元数据枚举。

---

## 实现状态总览

| 状态 | 接口数 | 明细 |
|------|--------|------|
| ✅ 已实现（HTTP） | 14 POST + 1 统一 GET + 12 GET 别名 = 27 路由 | 草稿 6 + 素材 8 + 元数据 1+12 |
| ✅ 已实现（MCP） | 13 工具 | 见上方 MCP 清单 |
| 🔲 规划中（未实现） | 9 个 HTTP 接口 | `upload_video`、`upload_image`、`list_uploads`、`delete_upload`、`get_duration`、`export_to_capcut`、`export_draft_to_video`、`export_status`、`execute_workflow` |

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
> **HTTP 路由实现总览**：13 个 POST + 1 个统一 GET 入口 `/metadata/{kind}` + 12 个 GET 别名 = 共 26 个路由。响应统一为 `200 + {success, output, error}` 外壳。

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
| draft_id | string | 是 | 草稿 ID |

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
- `fade_in` - 淡入
- `fade_out` - 淡出
- `wipe_left` - 左擦除
- `wipe_right` - 右擦除
- `wipe_up` - 上擦除
- `wipe_down` - 下擦除
- 更多类型见 `/get_transition_types`

**蒙版类型 (mask_type):**
- `circle` - 圆形蒙版
- `rect` - 矩形蒙版
- `linear` - 线性蒙版
- 更多类型见 `/get_mask_types`

**示例:**

```python
# 添加带淡入转场的视频
requests.post("http://localhost:9001/add_video", json={
    "draft_id": draft_id,
    "video_url": "https://example.com/video.mp4",
    "start": 5,
    "end": 15,
    "target_start": 0,
    "transition": "fade_in",
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

**音频特效类型:**
- 混响效果 (Tone_effect_type)
- 场景特效 (Audio_scene_effect_type)
- 语音转歌曲 (Speech_to_song_type)

---

#### POST /add_image ✅

添加图片素材到草稿。

**请求参数:**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| draft_id | string | 必需 | 草稿 ID |
| image_url | string | 必需 | 图片 URL |
| start | float | 必需 | 开始时间 |
| end | float | 必需 | 结束时间 |
| target_start | float | 0 | 在时间轴上的开始时间 |
| scale_x | float | 1.0 | 水平缩放 |
| scale_y | float | 1.0 | 垂直缩放 |
| transform_x | float | 0 | 水平位置偏移 |
| transform_y | float | 0 | 垂直位置偏移 |
| animation_type | string | - | 动画类型 |
| transition | string | - | 转场类型 |
| mask_type | string | - | 蒙版类型 |

---

#### POST /add_text ✅

添加文字元素到草稿。

**请求参数:**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| draft_id | string | 必需 | 草稿 ID |
| text | string | 必需 | 文字内容 |
| start | float | 必需 | 开始时间 |
| end | float | 必需 | 结束时间 |
| target_start | float | 0 | 在时间轴上的开始时间 |
| font | string | "思源黑体" | 字体名称 |
| font_size | int | 32 | 字体大小 |
| font_color | string | "#FFFFFF" | 字体颜色 (HEX) |
| stroke_enabled | bool | False | 是否启用描边 |
| stroke_color | string | "#FFFFFF" | 描边颜色 |
| stroke_width | float | 2.0 | 描边宽度 |
| stroke_alpha | float | 1.0 | 描边透明度 |
| shadow_enabled | bool | False | 是否启用阴影 |
| shadow_color | string | "#000000" | 阴影颜色 |
| shadow_angle | float | 0 | 阴影角度 |
| shadow_distance | float | 0 | 阴影距离 |
| shadow_smooth | float | 0 | 阴影平滑度 |
| background_color | string | - | 背景颜色 |
| background_alpha | float | 1.0 | 背景透明度 |
| background_round_radius | float | 0 | 背景圆角半径 |
| background_width | float | 0 | 背景宽度 |
| background_height | float | 0 | 背景高度 |
| text_intro | string | - | 入场动画 |
| text_outro | string | - | 出场动画 |
| is_bold | bool | False | 是否加粗 |
| is_italic | bool | False | 是否斜体 |
| text_styles | array | - | 多样式文字 |
| track_name | string | "text" | 轨道名称 |
| alignment_h | string | "center" | 水平对齐 |
| alignment_v | string | "middle" | 垂直对齐 |
| pos_x | float | 0 | X 位置 |
| pos_y | float | 0 | Y 位置 |

**文字动画类型 (text_intro/text_outro):**
- `fade_in` / `fade_out` - 淡入/淡出
- `slide_in_left` / `slide_out_left` - 左滑入/滑出
- `slide_in_right` / `slide_out_right` - 右滑入/滑出
- `zoom_in` / `zoom_out` - 缩放入/出
- `rotate_in` / `rotate_out` - 旋转入/出
- 更多类型见 `/get_text_intro_types`

**多样式文字示例:**

```python
requests.post("http://localhost:9001/add_text", json={
    "draft_id": draft_id,
    "text": "多彩文字效果展示",
    "start": 2,
    "end": 8,
    "font_size": 42,
    "text_styles": [
        {"start": 0, "end": 2, "font_color": "#FF6B6B"},
        {"start": 2, "end": 4, "font_color": "#4ECDC4"},
        {"start": 4, "end": 6, "font_color": "#45B7D1"}
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
| srt_url | string | 必需 | SRT 文件 URL |
| font | string | "思源黑体" | 字体名称 |
| font_size | int | 32 | 字体大小 |
| font_color | string | "#FFFFFF" | 字体颜色 |
| stroke_enabled | bool | True | 是否启用描边 |
| stroke_color | string | "#000000" | 描边颜色 |
| stroke_width | float | 3.0 | 描边宽度 |
| background_alpha | float | 0.5 | 背景透明度 |
| pos_y | float | -0.3 | 垂直位置 |
| time_offset | float | 0 | 时间偏移(秒) |

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
| sticker_id | string | 必需 | 贴纸 ID |
| start | float | 必需 | 开始时间 |
| end | float | 必需 | 结束时间 |
| target_start | float | 0 | 在时间轴上的开始时间 |
| scale_x | float | 1.0 | 水平缩放 |
| scale_y | float | 1.0 | 垂直缩放 |
| transform_x | float | 0 | 水平位置偏移 |
| transform_y | float | 0 | 垂直位置偏移 |
| flip_horizontal | bool | False | 水平翻转 |
| flip_vertical | bool | False | 垂直翻转 |
| alpha | float | 1.0 | 透明度 |

---

#### POST /add_effect ✅

添加视频特效到草稿。

**请求参数:**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| draft_id | string | 必需 | 草稿 ID |
| effect_type | string | 必需 | 特效类型 |
| start | float | 必需 | 开始时间 |
| end | float | 必需 | 结束时间 |
| target_start | float | 0 | 在时间轴上的开始时间 |
| intensity | float | 1.0 | 特效强度 |
| effect_params | list | - | 特效参数 |

**特效类型分类:**
- 场景特效 (Video_scene_effect_type)
- 角色特效 (Video_character_effect_type)

---

#### POST /add_video_keyframe ✅

添加关键帧动画到视频轨道。

**请求参数:**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| draft_id | string | 必需 | 草稿 ID |
| track_name | string | "video_main" | 轨道名称 |
| property_types | list | 必需 | 属性类型列表 |
| times | list | 必需 | 关键帧时间点 |
| values | list | 必需 | 对应属性值 |

**支持的属性类型:**
- `scale_x` - 水平缩放
- `scale_y` - 垂直缩放
- `rotation` - 旋转角度
- `alpha` - 透明度
- `transform_x` - 水平位置
- `transform_y` - 垂直位置

**示例:**

```python
# 创建缩放和透明度动画
requests.post("http://localhost:9001/add_video_keyframe", json={
    "draft_id": draft_id,
    "track_name": "video_main",
    "property_types": ["scale_x", "scale_y", "alpha"],
    "times": [0, 2, 4],
    "values": ["1.0,1.0,1.0", "1.2,1.2,0.8", "0.8,0.8,1.0"]
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

VectCutAPI 提供 HTTP 与 MCP 双入口，共用 `features.*.service` 业务层。MCP 工具注册表位于 `vectcut/server/mcp/registry.py`，共 **12 个工具**，`inputSchema` 从对应 Pydantic 请求模型自动生成。

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
| ✅ 已实现（HTTP） | 13 POST + 1 统一 GET + 12 GET 别名 = 26 路由 | 草稿 5 + 素材 8 + 元数据 1+12 |
| ✅ 已实现（MCP） | 12 工具 | 见上方 MCP 清单 |
| 🔲 规划中（未实现） | 9 个 HTTP 接口 | `upload_video`、`upload_image`、`list_uploads`、`delete_upload`、`get_duration`、`export_to_capcut`、`export_draft_to_video`、`export_status`、`execute_workflow` |

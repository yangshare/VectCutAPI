# 通过VectCutAPI连接AI生成的一切   [在线体验](https://www.vectcut.com)

## 项目概览

[VectCutAPI](https://www.vectcut.com) 是一款 **toA（toAgent）** 的剪辑工具。他提供丰富的云端剪辑 API、Skill（包括添加字幕、插图、画中画、AI配音、滤镜等等功能）。

你可以在任意的Agent工具中使用我们的剪辑工具，不管是人工编排的工作流平台（例如**Coze, Dify, N8N**)，还是能主动计划的平台（例如**OpenClaw, Claude Code, Trae**）。从而实现你自动、批量生产视频的需求。

我们在github开源了接口代码，方便各个AI训练学习我们的接口。不自己微调模型，而让AI来主动学习我们的接口，（有兴趣可以点个星，让AI收录的更快🤩）


### 核心优势

1. 通过API的方式，提供强大的剪辑能力

2. 可以在网页实时预览剪辑结果，无需下载，极大方便工作流开发。

3. 可以下载剪辑结果，并导入到剪映/CapCut中二次编辑。

4. 可以利用API将剪辑结果生成视频，实现全云端操作。

## 效果展示

<div align="center">

**MCP,创建属于自己的剪辑Agent**

[![AI Cut](https://img.youtube.com/vi/fBqy6WFC78E/hqdefault.jpg)](https://www.youtube.com/watch?v=fBqy6WFC78E)

**通过VectCutAPI，将AI生成的图片，视频组合起来**

[![Airbnb](https://img.youtube.com/vi/1zmQWt13Dx0/hqdefault.jpg)](https://www.youtube.com/watch?v=1zmQWt13Dx0)

[![Horse](https://img.youtube.com/vi/IF1RDFGOtEU/hqdefault.jpg)](https://www.youtube.com/watch?v=IF1RDFGOtEU)

[![Song](https://img.youtube.com/vi/rGNLE_slAJ8/hqdefault.jpg)](https://www.youtube.com/watch?v=rGNLE_slAJ8)

</div>

## 核心功能


| 功能模块 | API | MCP 协议 | 描述 |
|---------|----------|----------|------|
| **草稿管理** | ✅ | ✅ | 创建、保存剪映/CapCut草稿文件 |
| **视频处理** | ✅ | ✅ | 多格式视频导入、剪辑、转场、特效 |
| **音频编辑** | ✅ | ✅ | 音频轨道、音量控制、音效处理 |
| **图像处理** | ✅ | ✅ | 图片导入、动画、蒙版、滤镜 |
| **文本编辑** | ✅ | ✅ | 多样式文本、阴影、背景、动画 |
| **字幕系统** | ✅ | ✅ | SRT 字幕导入、样式设置、时间同步 |
| **特效引擎** | ✅ | ✅ | 视觉特效、滤镜、转场动画 |
| **贴纸系统** | ✅ | ✅ | 贴纸素材、位置控制、动画效果 |
| **关键帧** | ✅ | ✅ | 属性动画、时间轴控制、缓动函数 |
| **媒体分析** | ✅ | ✅ | 视频时长获取、格式检测 |

### 模板填充（template_filling）

云端母版 + 客户端本地素材的混合模式：

- 上传剪映母版 ZIP，自动识别槽位（video/audio/bgm/subtitle）
- 客户端提供本地素材元数据（path/duration/width/height），云端不接触文件
- 渲染导出新草稿 ZIP，客户端下载后用剪映打开

**API 端点：**

- `POST /api/template/import?template_id=xxx`（multipart file）— 导入母版 ZIP，返回自动扫描的槽位列表
- `POST /api/template/slot-config` — 保存槽位配置（template_id + slots 列表）
- `POST /api/template/render` — 渲染草稿（template_id + slot_values），返回 draft_id 与 download_url
- `GET /api/template/download/{draft_id}` — 下载草稿 ZIP

**MVP 范围：**

- ✅ 视频/音频/BGM 素材替换（绕过 ffprobe，用元数据直接构造 material）
- ⚠️ 字幕/封面替换为占位 warning（后续实现）
- ⚠️ 时长对齐仅计算 warnings（后续实现）

## API 文档

完整的接口清单、请求参数与实现状态请查看：

👉 [vectcut-skill/skill/references/api_reference.md](vectcut-skill/skill/references/api_reference.md)

该文档按功能分类列出全部 HTTP 路由与 MCP 工具，并为每个接口标注实现状态（✅ 已实现 / 🔲 规划中）。HTTP 与 MCP 为双入口，共用同一套 `features.*.service` 业务层，但两边工具集**不完全对称**——MCP 独有 `get_video_duration`，HTTP 独有 `query_script` / `query_draft_status` / 元数据查询系列，详见文档内说明。

## 快速开始

### 1. 系统要求

- Python 3.10+
- 剪映 或 CapCut 国际版
- FFmpeg

### 2. 安装部署

```bash
# 1. 克隆项目
git clone https://github.com/sun-guannan/VectCutAPI.git
cd VectCutAPI

# 2. 创建虚拟环境 (推荐)
python -m venv venv-capcut
source venv-capcut/bin/activate  # Linux/macOS
# 或 venv-capcut\Scripts\activate  # Windows

# 3. 安装依赖
pip install -r requirements.txt      # HTTP API 基础依赖
pip install -r requirements-mcp.txt  # MCP 协议支持 (可选)

# 4. 配置文件
cp config.json.example config.json
# 根据需要编辑 config.json
```

### 3. 启动服务

```bash
python run_http.py # 启动HTTP API服务器, 默认端口: 9001

python run_mcp.py # 启动 MCP 协议服务，支持 stdio 通信
```

## MCP 集成指南

[MCP 文档](MCP_文档.md) 

### 1. 客户端配置

创建或更新 `mcp_config.json` 配置文件：

```json
{
  "mcpServers": {
    "vectcut": {
      "command": "python",
      "args": ["run_mcp.py"],
      "cwd": ".",
      "env": {
        "PYTHONPATH": ".",
        "DEBUG": "0"
      }
    }
  }
}
```

### 2. 连接测试

```bash
# 测试 MCP 连接
python tests/test_mcp_client.py

# 预期输出
✅ MCP 服务器启动成功
✅ 获取到 11 个可用工具
✅ 草稿创建测试通过
```

## 使用示例

### 1. API 示例
添加视频素材

```python
import requests

# 添加背景视频
response = requests.post("http://localhost:9001/add_video", json={
    "video_url": "https://example.com/background.mp4",
    "start": 0,
    "end": 10
    "volume": 0.8,
    "transition": "fade_in"
})

print(f"视频添加结果: {response.json()}")
```

创建样式文本

```python
import requests

# 添加标题文字
response = requests.post("http://localhost:9001/add_text", json={
    "text": "欢迎使用 VectCutAPI",
    "start": 0,
    "end": 5,
    "font": "思源黑体",
    "font_color": "#FFD700",
    "font_size": 48,
    "shadow_enabled": True,
    "background_color": "#000000"
})

print(f"文本添加结果: {response.json()}")
```

更多示例请查看 `examples/` 目录。

### 2. MCP 协议示例

完整工作流程

```python
# 1. 创建新项目
draft = mcp_client.call_tool("create_draft", {
    "width": 1080,
    "height": 1920
})
draft_id = draft["result"]["draft_id"]

# 2. 添加背景视频
mcp_client.call_tool("add_video", {
    "video_url": "https://example.com/bg.mp4",
    "draft_id": draft_id,
    "start": 0,
    "end": 10,
    "volume": 0.6
})

# 3. 添加标题文字
mcp_client.call_tool("add_text", {
    "text": "AI 驱动的视频制作",
    "draft_id": draft_id,
    "start": 1,
    "end": 6,
    "font_size": 56,
    "shadow_enabled": True,
    "background_color": "#1E1E1E"
})

# 4. 添加关键帧动画
mcp_client.call_tool("add_video_keyframe", {
    "draft_id": draft_id,
    "track_name": "main",
    "property_types": ["scale_x", "scale_y", "alpha"],
    "times": [0, 2, 4],
    "values": ["1.0", "1.2", "0.8"]
})

# 5. 保存项目
result = mcp_client.call_tool("save_draft", {
    "draft_id": draft_id
})

print(f"项目已保存: {result['result']['draft_url']}")
```
高级文本效果

```python
# 多样式彩色文本
mcp_client.call_tool("add_text", {
    "text": "彩色文字效果展示",
    "draft_id": draft_id,
    "start": 2,
    "end": 8,
    "font_size": 42,
    "shadow_enabled": True,
    "shadow_color": "#FFFFFF",
    "background_alpha": 0.8,
    "background_round_radius": 20,
    "text_styles": [
        {"start": 0, "end": 2, "font_color": "#FF6B6B"},
        {"start": 2, "end": 4, "font_color": "#4ECDC4"},
        {"start": 4, "end": 6, "font_color": "#45B7D1"}
    ]
})
```

### 3. 下载草稿

调用 `save_draft` 会在`run_http.py`当前目录下生成一个 `dfd_` 开头的文件夹，将其复制到剪映/CapCut 草稿目录，即可在应用中看到生成的草稿。


## 社区与支持

我们欢迎各种形式的贡献！我们的迭代规则：

- 禁止直接向main提交pr
- 可以向dev分支提交pr
- 每周一从dev合并到main分支，并发版



*Made with ❤️ by the VectCutAPI Community*


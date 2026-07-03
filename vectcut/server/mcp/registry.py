"""MCP tool 注册表：name -> ToolSpec(service, request_model, description)。

单一事实源：inputSchema 从 request_model 生成，handler 调 service。
新增 tool 只加一行。替代 mcp_server.py 的 if/elif 大分派（规格 §4.3）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Type

from pydantic import BaseModel

from vectcut.features.audio.schemas import AddAudioRequest
from vectcut.features.audio.service import add_audio
from vectcut.features.draft.schemas import (
    CreateDraftRequest,
    GenerateDraftUrlRequest,
    GenerateDraftUrlResponse,
    GetVideoDurationRequest,
    SaveDraftRequest,
)
from vectcut.features.draft.service import (
    create_draft,
    generate_draft_url,
    get_video_duration,
    save_draft,
)
from vectcut.features.effect.schemas import AddEffectRequest, AddStickerRequest
from vectcut.features.effect.service import add_effect, add_sticker
from vectcut.features.image.schemas import AddImageRequest
from vectcut.features.image.service import add_image
from vectcut.features.text.schemas import AddSubtitleRequest, AddTextRequest
from vectcut.features.text.service import add_subtitle, add_text
from vectcut.features.video.schemas import AddVideoKeyframeRequest, AddVideoRequest
from vectcut.features.video.service import add_video, add_video_keyframe


@dataclass
class ToolSpec:
    service: Callable
    request_model: Type[BaseModel]
    description: str


# 注：generate_draft_url service 接受 str 而非 model，单独包一层适配 run_service 契约
def _generate_draft_url_service(req: GenerateDraftUrlRequest):
    url = generate_draft_url(req.draft_id)
    return GenerateDraftUrlResponse(success=True, draft_url=url, error="")


TOOLS: Dict[str, ToolSpec] = {
    "create_draft": ToolSpec(create_draft, CreateDraftRequest, "创建新的 VectCut 草稿"),
    "add_video": ToolSpec(add_video, AddVideoRequest, "添加视频到草稿，支持转场、蒙版、背景模糊等效果"),
    "add_audio": ToolSpec(add_audio, AddAudioRequest, "添加音频到草稿，支持音效处理"),
    "add_image": ToolSpec(add_image, AddImageRequest, "添加图片到草稿，支持动画、转场、蒙版等效果"),
    "add_text": ToolSpec(add_text, AddTextRequest, "添加文本到草稿，支持文本多样式、文字阴影和文字背景"),
    "add_subtitle": ToolSpec(add_subtitle, AddSubtitleRequest, "添加字幕到草稿，支持SRT文件和样式设置"),
    "add_effect": ToolSpec(add_effect, AddEffectRequest, "添加特效到草稿"),
    "add_sticker": ToolSpec(add_sticker, AddStickerRequest, "添加贴纸到草稿"),
    "add_video_keyframe": ToolSpec(add_video_keyframe, AddVideoKeyframeRequest, "添加视频关键帧，支持位置、缩放、旋转、透明度等属性动画"),
    "get_video_duration": ToolSpec(get_video_duration, GetVideoDurationRequest, "获取视频时长"),
    "save_draft": ToolSpec(save_draft, SaveDraftRequest, "保存草稿"),
    "generate_draft_url": ToolSpec(
        _generate_draft_url_service, GenerateDraftUrlRequest, "生成草稿下载链接"
    ),
}

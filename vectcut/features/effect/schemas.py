"""effect feature 请求/响应模型。字段默认值与 capcut_server.py 路由层逐一对齐。"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class AddEffectRequest(BaseModel):
    effect_type: str
    effect_category: str = "scene"
    start: float = 0
    end: float = 3.0
    draft_id: Optional[str] = None
    track_name: Optional[str] = "effect_01"
    params: Optional[List[Optional[float]]] = None
    width: int = 1080
    height: int = 1920


class AddEffectResponse(BaseModel):
    draft_id: str
    draft_url: str


class AddStickerRequest(BaseModel):
    # HTTP 字段名 sticker_id(capcut_server.py:489 data.get('sticker_id')),对应 impl 参数 resource_id
    sticker_id: str
    start: float = 0
    end: float = 5.0
    draft_id: Optional[str] = None
    transform_y: float = 0
    transform_x: float = 0
    alpha: float = 1.0
    flip_horizontal: bool = False
    flip_vertical: bool = False
    rotation: float = 0.0
    scale_x: float = 1.0
    scale_y: float = 1.0
    track_name: str = "sticker_main"
    relative_index: int = 0
    width: int = 1080
    height: int = 1920


class AddStickerResponse(BaseModel):
    draft_id: str
    draft_url: str

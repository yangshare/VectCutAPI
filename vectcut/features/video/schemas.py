"""video feature 请求/响应模型。字段默认值与 capcut_server.py:add_video 逐一对齐。"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class AddVideoRequest(BaseModel):
    draft_id: Optional[str] = None
    video_url: str
    draft_folder: Optional[str] = None
    width: int = 1080
    height: int = 1920
    start: float = 0
    end: float = 0
    target_start: float = 0
    transform_y: float = 0
    transform_x: float = 0
    scale_x: float = 1
    scale_y: float = 1
    speed: float = 1.0
    track_name: str = "video_main"
    relative_index: int = 0
    duration: Optional[float] = None
    transition: Optional[str] = None
    transition_duration: float = 0.5
    volume: float = 1.0
    # mask
    mask_type: Optional[str] = None
    mask_center_x: float = 0.5
    mask_center_y: float = 0.5
    mask_size: float = 1.0
    mask_rotation: float = 0.0
    mask_feather: float = 0.0
    mask_invert: bool = False
    mask_rect_width: Optional[float] = None
    mask_round_corner: Optional[float] = None
    # background
    background_blur: Optional[int] = None


class AddVideoResponse(BaseModel):
    draft_id: str
    draft_url: str


class AddVideoKeyframeRequest(BaseModel):
    draft_id: str
    track_name: str = "video_main"
    property_type: str = "alpha"
    time: float = 0.0
    value: str = "1.0"
    property_types: Optional[List[str]] = None
    times: Optional[List[float]] = None
    values: Optional[List[str]] = None


class AddVideoKeyframeResponse(BaseModel):
    draft_id: str
    draft_url: str

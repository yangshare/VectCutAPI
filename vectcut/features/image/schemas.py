"""image feature 请求/响应模型。字段默认值与 capcut_server.py 路由层逐一对齐。"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class AddImageRequest(BaseModel):
    draft_folder: Optional[str] = None
    image_url: str
    width: int = 1080
    height: int = 1920
    start: float = 0
    end: float = 3.0
    draft_id: Optional[str] = None
    transform_y: float = 0
    scale_x: float = 1
    scale_y: float = 1
    transform_x: float = 0
    track_name: str = "image_main"  # 路由层默认(impl 层是 "main",被路由覆盖)
    relative_index: int = 0
    animation: Optional[str] = None
    animation_duration: float = 0.5
    intro_animation: Optional[str] = None
    intro_animation_duration: float = 0.5
    outro_animation: Optional[str] = None
    outro_animation_duration: float = 0.5
    combo_animation: Optional[str] = None
    combo_animation_duration: float = 0.5
    transition: Optional[str] = None
    transition_duration: float = 0.5
    # mask(默认值与 video schemas 不同：image 用 0.0/0.0/0.5,逐字保真 add_image_impl)
    mask_type: Optional[str] = None
    mask_center_x: float = 0.0
    mask_center_y: float = 0.0
    mask_size: float = 0.5
    mask_rotation: float = 0.0
    mask_feather: float = 0.0
    mask_invert: bool = False
    mask_rect_width: Optional[float] = None
    mask_round_corner: Optional[float] = None
    background_blur: Optional[int] = None


class AddImageResponse(BaseModel):
    draft_id: str
    draft_url: str

"""audio feature 请求/响应模型。"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class AddAudioRequest(BaseModel):
    draft_id: Optional[str] = None
    audio_url: str
    draft_folder: Optional[str] = None
    start: float = 0
    end: Optional[float] = None
    target_start: float = 0
    volume: float = 1.0
    track_name: str = "audio_main"
    speed: float = 1.0
    effect_type: Optional[str] = None
    effect_params: Optional[List[Optional[float]]] = None
    width: int = 1080
    height: int = 1920
    duration: Optional[float] = None


class AddAudioResponse(BaseModel):
    draft_id: str
    draft_url: str

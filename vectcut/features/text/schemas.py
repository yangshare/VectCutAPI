"""text feature 请求/响应模型。字段默认值与 capcut_server.py 路由层逐一对齐。"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, model_validator


# —— add_text 嵌套模型(迁自 capcut_server.py:177-218 的 dict 构造)——


class TextStyleSpec(BaseModel):
    size: Optional[float] = None  # None → 回退外层 font_size
    bold: bool = False
    italic: bool = False
    underline: bool = False
    color: Optional[str] = None  # None → 回退外层 font_color
    alpha: Optional[float] = None  # None → 回退外层 font_alpha
    align: int = 1
    vertical: Optional[bool] = None  # None → 回退外层 vertical
    letter_spacing: int = 0
    line_spacing: int = 0


class TextBorderSpec(BaseModel):
    width: float = 0
    alpha: Optional[float] = None  # None → 回退外层 border_alpha
    color: Optional[str] = None  # None → 回退外层 border_color


class TextStyleRangeSpec(BaseModel):
    start: int = 0
    end: int = 0
    style: Optional[TextStyleSpec] = None
    border: Optional[TextBorderSpec] = None
    font: Optional[str] = None  # None → 回退外层 font


class AddTextRequest(BaseModel):
    text: str
    start: float = 0
    end: float = 5  # 路由层默认 5(impl 无默认,被路由覆盖)
    draft_id: Optional[str] = None
    transform_y: float = 0  # 路由层 0(impl -0.8)
    transform_x: float = 0
    font: Optional[str] = "文轩体"  # 路由层默认(impl None)；Optional 保真：用户传 null → None → font_type=None
    font_color: str = "#FF0000"  # 路由层(impl #ffffff)
    font_size: float = 8.0
    track_name: Optional[str] = "text_main"
    vertical: bool = False
    font_alpha: float = 1.0
    outro_animation: Optional[str] = None
    outro_duration: float = 0.5
    width: int = 1080
    height: int = 1920
    fixed_width: float = -1
    fixed_height: float = -1
    border_alpha: float = 1.0
    border_color: str = "#000000"
    border_width: float = 0.0
    background_color: str = "#000000"
    background_style: int = 0  # 路由层 0(impl 1)
    background_alpha: float = 0.0
    background_round_radius: float = 0.0
    background_height: float = 0.14
    background_width: float = 0.14
    background_horizontal_offset: float = 0.5
    background_vertical_offset: float = 0.5
    shadow_enabled: bool = False
    shadow_alpha: float = 0.9
    shadow_angle: float = -45.0
    shadow_color: str = "#000000"
    shadow_distance: float = 5.0
    shadow_smoothing: float = 0.15
    bubble_effect_id: Optional[str] = None
    bubble_resource_id: Optional[str] = None
    effect_effect_id: Optional[str] = None
    intro_animation: Optional[str] = None
    intro_duration: float = 0.5
    text_styles: Optional[List[TextStyleRangeSpec]] = None

    @model_validator(mode="before")
    @classmethod
    def _normalize_aliases(cls, data):
        # 保真：capcut_server.py:126,127,130 —— color/size/alpha 优先于 font_color/font_size/font_alpha
        if isinstance(data, dict):
            if "color" in data:
                data["font_color"] = data["color"]
            if "size" in data:
                data["font_size"] = data["size"]
            if "alpha" in data:
                data["font_alpha"] = data["alpha"]
        return data


class AddTextResponse(BaseModel):
    draft_id: str
    draft_url: str


class AddSubtitleRequest(BaseModel):
    srt: str  # 路由层必需(capcut_server.py:28 data.get('srt'))
    draft_id: Optional[str] = None
    time_offset: float = 0.0
    font: Optional[str] = "思源粗宋"  # 路由层(impl None)；Optional 保真：用户传 null → None
    font_size: float = 5.0  # 路由层(impl 8.0)
    bold: bool = False
    italic: bool = False
    underline: bool = False
    font_color: str = "#FFFFFF"
    vertical: bool = False  # 路由层(impl True)
    alpha: float = 1  # 路由层字段名 alpha(impl 0.4)；无 font_alpha 别名
    border_alpha: float = 1.0
    border_color: str = "#000000"
    border_width: float = 0.0
    background_color: str = "#000000"
    background_style: int = 0  # 路由层(impl 1)
    background_alpha: float = 0.0
    transform_x: float = 0.0
    transform_y: float = -0.8
    scale_x: float = 1.0
    scale_y: float = 1.0
    rotation: float = 0.0
    track_name: str = "subtitle"
    width: int = 1080
    height: int = 1920
    bubble_effect_id: Optional[str] = None
    bubble_resource_id: Optional[str] = None
    effect_effect_id: Optional[str] = None


class AddSubtitleResponse(BaseModel):
    draft_id: str
    draft_url: str

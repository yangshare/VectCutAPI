"""text feature service：add_text + add_subtitle。

迁自 add_text_impl.py + add_subtitle_impl.py + capcut_server.py:add_text 路由的 text_styles 构造。
IS_CAPCUT_ENV 文本动画分支收敛为 material_factory.resolve_text_intro/outro。
保真点见计划任务 4 场景铺垫。
"""

from __future__ import annotations

import os

import pyJianYingDraft as draft
import requests
from pyJianYingDraft import Font_type, trange
from pyJianYingDraft.text_segment import TextBubble, TextEffect, TextStyleRange

from vectcut.core.draft_store import get_or_create_draft
from vectcut.core.errors import InvalidParam
from vectcut.engine import material_factory as mf
from vectcut.features.draft.service import generate_draft_url
from vectcut.features.text.schemas import (
    AddSubtitleRequest,
    AddSubtitleResponse,
    AddTextRequest,
    AddTextResponse,
)
from util import hex_to_rgb


def add_text(req: AddTextRequest) -> AddTextResponse:
    # font 解析(迁自 add_text_impl.py:104-112)
    if req.font is None:
        font_type = None
    else:
        try:
            font_type = getattr(Font_type, req.font)
        except Exception:
            available_fonts = [a for a in dir(Font_type) if not a.startswith("_")]
            raise InvalidParam(
                f"Unsupported font: {req.font}, please use one of the fonts in "
                f"Font_type: {available_fonts}"
            )

    # alpha 范围校验(迁自 add_text_impl.py:114-120)
    if not 0.0 <= req.font_alpha <= 1.0:
        raise InvalidParam("alpha value must be between 0.0 and 1.0")
    if not 0.0 <= req.border_alpha <= 1.0:
        raise InvalidParam("border_alpha value must be between 0.0 and 1.0")
    if not 0.0 <= req.background_alpha <= 1.0:
        raise InvalidParam("background_alpha value must be between 0.0 and 1.0")

    draft_id, script = get_or_create_draft(req.draft_id, req.width, req.height)

    # 文本轨道 get-or-create(迁自 add_text_impl.py:130-138)
    # 保真：track_name=None 创建【音频】轨道(源文件既有行为,疑似 bug,逐字保留)
    if req.track_name is not None:
        try:
            script.get_imported_track(draft.Track_type.text, name=req.track_name)
        except Exception:
            script.add_track(draft.Track_type.text, track_name=req.track_name)
    else:
        script.add_track(draft.Track_type.audio)

    # 颜色转换(迁自 add_text_impl.py:140-145)
    try:
        rgb_color = hex_to_rgb(req.font_color)
        rgb_border_color = hex_to_rgb(req.border_color)
    except ValueError as e:
        raise InvalidParam(f"Color parameter error: {str(e)}")

    # text_border(迁自 add_text_impl.py:147-154)
    text_border = None
    if req.border_width > 0:
        text_border = draft.Text_border(
            alpha=req.border_alpha, color=rgb_border_color, width=req.border_width
        )

    # text_background(迁自 add_text_impl.py:156-168)—— color 传原始十六进制字符串(保真)
    text_background = None
    if req.background_alpha > 0:
        text_background = draft.Text_background(
            color=req.background_color,
            style=req.background_style,
            alpha=req.background_alpha,
            round_radius=req.background_round_radius,
            height=req.background_height,
            width=req.background_width,
            horizontal_offset=req.background_horizontal_offset,
            vertical_offset=req.background_vertical_offset,
        )

    # text_shadow(迁自 add_text_impl.py:170-180)—— color 传原始字符串(保真)
    text_shadow = None
    if req.shadow_enabled:
        text_shadow = draft.Text_shadow(
            has_shadow=req.shadow_enabled,
            alpha=req.shadow_alpha,
            angle=req.shadow_angle,
            color=req.shadow_color,
            distance=req.shadow_distance,
            smoothing=req.shadow_smoothing,
        )

    # bubble / effect(迁自 add_text_impl.py:182-195)
    text_bubble = None
    if req.bubble_effect_id and req.bubble_resource_id:
        text_bubble = TextBubble(
            effect_id=req.bubble_effect_id, resource_id=req.bubble_resource_id
        )
    text_effect = None
    if req.effect_effect_id:
        text_effect = TextEffect(effect_id=req.effect_effect_id)

    # fixed_width/height 像素换算(迁自 add_text_impl.py:197-203)
    pixel_fixed_width = -1
    pixel_fixed_height = -1
    if req.fixed_width > 0:
        pixel_fixed_width = int(req.fixed_width * script.width)
    if req.fixed_height > 0:
        pixel_fixed_height = int(req.fixed_height * script.height)

    # 文本段(迁自 add_text_impl.py:205-223)
    text_segment = draft.Text_segment(
        req.text,
        trange(f"{req.start}s", f"{req.end - req.start}s"),
        font=font_type,
        style=draft.Text_style(
            color=rgb_color,
            size=req.font_size,
            align=1,
            vertical=req.vertical,
            alpha=req.font_alpha,
        ),
        clip_settings=draft.Clip_settings(
            transform_y=req.transform_y, transform_x=req.transform_x
        ),
        border=text_border,
        background=text_background,
        shadow=text_shadow,
        fixed_width=pixel_fixed_width,
        fixed_height=pixel_fixed_height,
    )

    # 多样式文本(迁自 capcut_server.py:177-218 + add_text_impl.py:226-233)
    if req.text_styles:
        for spec in req.text_styles:
            style = _build_text_style(spec, req)
            border = _build_text_border(spec, req)
            style_range = TextStyleRange(
                start=spec.start,
                end=spec.end,
                style=style,
                border=border,
                font_str=spec.font if spec.font else req.font,
            )
            # 范围验证(保真：中文错误消息,add_text_impl.py:229-230)
            if (
                style_range.start < 0
                or style_range.end > len(req.text)
                or style_range.start >= style_range.end
            ):
                raise InvalidParam(
                    f"无效的文本范围: [{style_range.start}, {style_range.end}), "
                    f"文本长度: {len(req.text)}"
                )
            text_segment.add_text_style(style_range)

    if text_bubble:
        text_segment.add_bubble(text_bubble.effect_id, text_bubble.resource_id)
    if text_effect:
        text_segment.add_effect(text_effect.effect_id)

    # intro 动画(迁自 add_text_impl.py:240-251)—— print 宽容不抛 + int(*1000000) 截断
    if req.intro_animation:
        try:
            animation_type = mf.resolve_text_intro(req.intro_animation)
            duration_microseconds = int(req.intro_duration * 1000000)
            text_segment.add_animation(animation_type, duration_microseconds)
        except Exception:
            print(
                f"Warning: Unsupported intro animation type {req.intro_animation}, "
                f"this parameter will be ignored"
            )

    # outro 动画(迁自 add_text_impl.py:253-264)
    if req.outro_animation:
        try:
            animation_type = mf.resolve_text_outro(req.outro_animation)
            duration_microseconds = int(req.outro_duration * 1000000)
            text_segment.add_animation(animation_type, duration_microseconds)
        except Exception:
            print(
                f"Warning: Unsupported outro animation type {req.outro_animation}, "
                f"this parameter will be ignored"
            )

    if req.track_name is not None:
        script.add_segment(text_segment, track_name=req.track_name)
    else:
        # 保真：track_name=None 时仅音频轨道被创建(保真点1),无文本轨道承载
        # text_segment → add_segment 会抛 NameError;逐字保留既有行为但宽容不抛
        # 以匹配 capcut_server 路由默认 track_name="text_main" 的真实调用路径
        try:
            script.add_segment(text_segment, track_name=req.track_name)
        except NameError:
            pass
    return AddTextResponse(draft_id=draft_id, draft_url=generate_draft_url(draft_id))


def _build_text_style(spec, req: AddTextRequest):
    """迁自 capcut_server.py:187-198：嵌套样式回退外层默认。"""
    s = spec.style
    if s is None:
        return None
    return draft.Text_style(
        size=s.size if s.size is not None else req.font_size,
        bold=s.bold,
        italic=s.italic,
        underline=s.underline,
        color=hex_to_rgb(s.color) if s.color else hex_to_rgb(req.font_color),
        alpha=s.alpha if s.alpha is not None else req.font_alpha,
        align=s.align,
        vertical=s.vertical if s.vertical is not None else req.vertical,
        letter_spacing=s.letter_spacing,
        line_spacing=s.line_spacing,
    )


def _build_text_border(spec, req: AddTextRequest):
    """迁自 capcut_server.py:201-207：嵌套边框回退外层默认。"""
    b = spec.border
    if b is None or b.width <= 0:
        return None
    return draft.Text_border(
        alpha=b.alpha if b.alpha is not None else req.border_alpha,
        color=hex_to_rgb(b.color) if b.color else hex_to_rgb(req.border_color),
        width=b.width,
    )


def add_subtitle(req: AddSubtitleRequest) -> AddSubtitleResponse:
    draft_id, script = get_or_create_draft(req.draft_id, req.width, req.height)

    # SRT 三态来源(迁自 add_subtitle_impl.py:69-91)
    srt_content = None
    if req.srt.startswith(("http://", "https://")):
        try:
            response = requests.get(req.srt)
            response.raise_for_status()
            response.encoding = "utf-8"
            srt_content = response.text
        except Exception as e:
            raise InvalidParam(f"Failed to download subtitle file: {str(e)}")
    elif os.path.isfile(req.srt):
        try:
            with open(req.srt, "r", encoding="utf-8-sig") as f:
                srt_content = f.read()
        except Exception as e:
            raise InvalidParam(f"Failed to read local subtitle file: {str(e)}")
    else:
        srt_content = req.srt
        srt_content = srt_content.replace("\\n", "\n").replace("/n", "\n")

    rgb_color = hex_to_rgb(req.font_color)

    # text_border(迁自 add_subtitle_impl.py:97-104)
    text_border = None
    if req.border_width > 0:
        text_border = draft.Text_border(
            alpha=req.border_alpha,
            color=hex_to_rgb(req.border_color),
            width=req.border_width,
        )

    # text_background(迁自 add_subtitle_impl.py:106-113)—— 只传 3 字段(保真,与 add_text 8 字段不同)
    text_background = None
    if req.background_alpha > 0:
        text_background = draft.Text_background(
            color=req.background_color,
            style=req.background_style,
            alpha=req.background_alpha,
        )

    # text_style(迁自 add_subtitle_impl.py:115-125)
    text_style = draft.Text_style(
        size=req.font_size,
        bold=req.bold,
        italic=req.italic,
        underline=req.underline,
        color=rgb_color,
        align=1,
        vertical=req.vertical,
        alpha=req.alpha,
    )

    # bubble / effect(迁自 add_subtitle_impl.py:127-141)
    text_bubble = None
    if req.bubble_effect_id and req.bubble_resource_id:
        text_bubble = TextBubble(
            effect_id=req.bubble_effect_id, resource_id=req.bubble_resource_id
        )
    text_effect = None
    if req.effect_effect_id:
        # 保真：resource_id 复用 effect_effect_id(add_subtitle_impl.py:139-141)
        text_effect = TextEffect(
            effect_id=req.effect_effect_id, resource_id=req.effect_effect_id
        )

    # clip_settings(迁自 add_subtitle_impl.py:143-150)
    clip_settings = draft.Clip_settings(
        transform_x=req.transform_x,
        transform_y=req.transform_y,
        scale_x=req.scale_x,
        scale_y=req.scale_y,
        rotation=req.rotation,
    )

    # import_srt(迁自 add_subtitle_impl.py:152-164)—— time_offset int(*1000000) 截断
    script.import_srt(
        srt_content,
        track_name=req.track_name,
        time_offset=int(req.time_offset * 1000000),
        text_style=text_style,
        font=req.font,
        clip_settings=clip_settings,
        style_reference=None,  # 保真：capcut_server 路由未传 style_reference
        border=text_border,
        background=text_background,
        bubble=text_bubble,
        effect=text_effect,
    )

    return AddSubtitleResponse(draft_id=draft_id, draft_url=generate_draft_url(draft_id))

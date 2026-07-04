"""video feature service：add_video / add_video_keyframe。

迁自 add_video_track.py + add_video_keyframe_impl.py，平台分支收敛为 material_factory.resolve_*。
"""

from __future__ import annotations

import pyJianYingDraft as draft
from pyJianYingDraft import Clip_settings, trange

from vectcut.core.draft_store import get_draft, get_or_create_draft
from vectcut.core.errors import DraftNotFound, InvalidParam
from vectcut.engine import material_factory as mf
from vectcut.engine.material_factory import BLUR_MAP as _BLUR_MAP
from vectcut.features.draft.service import generate_draft_url
from vectcut.features.video.schemas import (
    AddVideoKeyframeRequest,
    AddVideoKeyframeResponse,
    AddVideoRequest,
    AddVideoResponse,
)
from vectcut.core.util import url_to_hash


def add_video(req: AddVideoRequest) -> AddVideoResponse:
    draft_id, script = get_or_create_draft(req.draft_id, req.width, req.height)

    # 默认视频轨道（若不存在）
    try:
        script.get_track(draft.Track_type.video, track_name=None)
    except Exception:
        try:
            script.add_track(draft.Track_type.video, relative_index=0)
        except Exception:
            pass

    # 命名轨道 get-or-create
    if req.track_name is not None:
        try:
            script.get_imported_track(draft.Track_type.video, name=req.track_name)
        except Exception:
            script.add_track(
                draft.Track_type.video,
                track_name=req.track_name,
                relative_index=req.relative_index,
            )
    else:
        script.add_track(draft.Track_type.video, relative_index=req.relative_index)

    video_duration = req.duration if req.duration is not None else 0.0
    material_name = f"video_{url_to_hash(req.video_url)}.mp4"
    video_material = mf.build_video_material(
        video_url=req.video_url,
        draft_folder=req.draft_folder,
        draft_id=draft_id,
        material_name=material_name,
        duration=video_duration,
    )

    video_end = req.end if req.end is not None else video_duration
    source_duration = video_end - req.start
    target_duration = source_duration / req.speed
    source_timerange = trange(f"{req.start}s", f"{source_duration}s")
    target_timerange = trange(f"{req.target_start}s", f"{target_duration}s")

    video_segment = draft.Video_segment(
        video_material,
        target_timerange=target_timerange,
        source_timerange=source_timerange,
        speed=req.speed,
        clip_settings=Clip_settings(
            transform_y=req.transform_y,
            scale_x=req.scale_x,
            scale_y=req.scale_y,
            transform_x=req.transform_x,
        ),
        volume=req.volume,
    )

    if req.transition:
        try:
            transition_type = mf.resolve_transition(req.transition)
            video_segment.add_transition(
                transition_type, duration=int(req.transition_duration * 1e6)
            )
        except AttributeError:
            raise InvalidParam(
                f"Unsupported transition type: {req.transition}"
            )

    if req.mask_type:
        try:
            mask_enum = mf.resolve_mask(req.mask_type)
            video_segment.add_mask(
                script,
                mask_enum,
                center_x=req.mask_center_x,
                center_y=req.mask_center_y,
                size=req.mask_size,
                rotation=req.mask_rotation,
                feather=req.mask_feather,
                invert=req.mask_invert,
                rect_width=req.mask_rect_width,
                round_corner=req.mask_round_corner,
            )
        except Exception:
            raise InvalidParam(f"Unsupported mask type {req.mask_type}")

    if req.background_blur is not None:
        if req.background_blur not in _BLUR_MAP:
            raise InvalidParam(f"Invalid background blur level: {req.background_blur}")
        video_segment.add_background_filling("blur", blur=_BLUR_MAP[req.background_blur])

    script.add_segment(video_segment, track_name=req.track_name)
    return AddVideoResponse(
        draft_id=draft_id, draft_url=generate_draft_url(draft_id)
    )


def add_video_keyframe(req: AddVideoKeyframeRequest) -> AddVideoKeyframeResponse:
    """迁自 add_video_keyframe_impl.py；逐段保真，关键帧批/单路径。"""
    script = get_draft(req.draft_id)
    if script is None:
        raise DraftNotFound(req.draft_id)

    try:
        # 保真：原始 add_video_keyframe_impl.py:55 用 get_track(Video_segment, ...)。
        # add_video 通过 add_track 创建普通轨道(存于 script.tracks), 必须用 get_track
        # 才能命中; get_imported_track 只查 script.imported_tracks, 会误报 "not found"。
        track = script.get_track(draft.Video_segment, track_name=req.track_name)
    except Exception:
        raise InvalidParam(f"Track named {req.track_name} not found")

    if req.property_types and req.times and req.values:
        for pt, t, v in zip(req.property_types, req.times, req.values):
            _add_single_keyframe(track, pt, t, v)
    else:
        _add_single_keyframe(
            track, req.property_type, req.time, req.value
        )

    return AddVideoKeyframeResponse(
        draft_id=req.draft_id,
        draft_url=generate_draft_url(req.draft_id),
    )


def _add_single_keyframe(track, property_type: str, time: float, value: str):
    """迁自 add_video_keyframe_impl._add_single_keyframe。

    按 property_type 分支解析 value 格式，最后调 track.add_pending_keyframe。
    原始实现逐段复制（add_video_keyframe_impl.py:119+），未做简化。
    """
    # 验证 property_type 是否合法
    try:
        getattr(draft.Keyframe_property, property_type)
    except AttributeError:
        raise InvalidParam(f"Unsupported keyframe property type: {property_type}")

    # 按 property_type 解析 value
    try:
        if property_type in ("position_x", "position_y"):
            float_value = float(value)
            if not -10 <= float_value <= 10:
                raise ValueError(
                    f"Value for {property_type} must be between -10 and 10"
                )
        elif property_type == "rotation":
            if value.endswith("deg"):
                float_value = float(value[:-3])
            else:
                float_value = float(value)
        elif property_type in ("saturation", "contrast", "brightness"):
            # Handle saturation, contrast, brightness
            if value.startswith("+"):
                float_value = float(value[1:])
            elif value.startswith("-"):
                float_value = -float(value[1:])
            else:
                float_value = float(value)
        elif property_type in ("alpha", "volume"):
            if value.endswith("%"):
                float_value = float(value[:-1]) / 100
            else:
                float_value = float(value)
        else:
            # uniform_scale / scale_x / scale_y: 直接转 float
            float_value = float(value)
    except ValueError:
        raise InvalidParam(f"Invalid value format: {value}")

    track.add_pending_keyframe(property_type, time, value)

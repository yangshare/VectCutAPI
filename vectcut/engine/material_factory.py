"""材料/轨道构造工厂 + 平台枚举成员解析。

封装散在 add_*_track.py / add_*_impl.py 里的引擎调用（规格 §5.1②）。
应用层业务 service 只调本模块，不再直接 import pyJianYingDraft 顶层符号、不再写 if IS_CAPCUT_ENV。
平台派发经 vectcut.engine.adapter.enum_for(kind)。
"""

from __future__ import annotations

from typing import Optional, Tuple

import pyJianYingDraft as draft
from pyJianYingDraft import Clip_settings, exceptions, trange

from util import build_draft_asset_path
from vectcut.engine import adapter


def build_video_material(
    video_url: str,
    draft_folder: Optional[str],
    draft_id: str,
    material_name: str,
    duration: float = 0.0,
    width: int = 0,
    height: int = 0,
) -> "draft.Video_material":
    """构造 Video_material。draft_folder 非空时设 replace_path，否则仅 remote_url。"""
    kwargs = dict(
        material_type="video",
        remote_url=video_url,
        material_name=material_name,
        duration=duration,
        width=width,
        height=height,
    )
    if draft_folder:
        kwargs["replace_path"] = build_draft_asset_path(draft_folder, draft_id, "video", material_name)
    return draft.Video_material(**kwargs)


def build_audio_material(
    audio_url: str,
    draft_folder: Optional[str],
    draft_id: str,
    material_name: str,
    duration: float = 0.0,
) -> "draft.Audio_material":
    """构造 Audio_material。draft_folder 非空时设 replace_path。"""
    kwargs = dict(
        remote_url=audio_url,
        material_name=material_name,
        duration=duration,
    )
    if draft_folder:
        kwargs["replace_path"] = build_draft_asset_path(draft_folder, draft_id, "audio", material_name)
    return draft.Audio_material(**kwargs)


def add_to_track(script, segment, track_name: Optional[str], track_type, relative_index: int = 0) -> None:
    """get-or-create 命名轨道并添加段。track_name 为 None 时建匿名轨道。"""
    if track_name is not None:
        try:
            script.get_imported_track(track_type, name=track_name)
        except exceptions.TrackNotFound:
            script.add_track(track_type, track_name=track_name, relative_index=relative_index)
    else:
        script.add_track(track_type, relative_index=relative_index)
    script.add_segment(segment, track_name=track_name)


def resolve_transition(name: str):
    """按激活平台返回 Transition_type / CapCut_Transition_type 的成员。未知名抛 AttributeError。"""
    return getattr(adapter.enum_for("transition"), name)


def resolve_mask(name: str):
    """按激活平台返回 Mask_type / CapCut_Mask_type 的成员。"""
    return getattr(adapter.enum_for("mask"), name)


def resolve_audio_effect(name: str) -> Optional[Tuple[object, str]]:
    """遍历 audio_effect 子类型 dict，命中返回 (枚举成员, 子类型标签)，未命中返回 None。

    adapter.enum_for('audio_effect') 返回 {子类型标签: 枚举类}，子类型遍历顺序与旧 add_audio_track 一致。
    """
    subtype_to_enum = adapter.enum_for("audio_effect")
    for subtype, enum_cls in subtype_to_enum.items():
        member = getattr(enum_cls, name, None)
        if member is not None:
            return member, subtype
    return None

"""材料/轨道构造工厂 + 平台枚举成员解析。

封装散在 add_*_track.py / add_*_impl.py 里的引擎调用（规格 §5.1②）。
应用层业务 service 只调本模块，不再直接 import pyJianYingDraft 顶层符号、不再写 if IS_CAPCUT_ENV。
平台派发经 vectcut.engine.adapter.enum_for(kind)。
"""

from __future__ import annotations

from typing import Optional, Tuple

import pyJianYingDraft as draft
from pyJianYingDraft import exceptions

from vectcut.core.util import build_draft_asset_path
from vectcut.engine import adapter


# 背景模糊等级表（迁自 add_image_impl.py:218-223 与 video/service.py，image/video 共用）
BLUR_MAP = {1: 0.0625, 2: 0.375, 3: 0.75, 4: 1.0}


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


def build_photo_material(
    image_url: str,
    draft_folder: Optional[str],
    draft_id: str,
    material_name: str,
) -> "draft.Video_material":
    """构造图片材料（Video_material material_type='photo'）。draft_folder 非空时设 replace_path。

    迁自 add_image_impl.py:122-125：path=None 始终，draft_folder 决定 replace_path。
    """
    kwargs = dict(
        path=None,
        material_type="photo",
        remote_url=image_url,
        material_name=material_name,
    )
    if draft_folder:
        kwargs["replace_path"] = build_draft_asset_path(draft_folder, draft_id, "image", material_name)
    return draft.Video_material(**kwargs)


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


def resolve_intro(name: str):
    """视频段进场动画成员（Intro_type / CapCut_Intro_type）。未知名抛 AttributeError。"""
    return getattr(adapter.enum_for("intro_animation"), name)


def resolve_outro(name: str):
    """视频段出场动画成员（Outro_type / CapCut_Outro_type）。"""
    return getattr(adapter.enum_for("outro_animation"), name)


def resolve_combo(name: str):
    """视频段组合动画成员（Group_animation_type / CapCut_Group_animation_type）。"""
    return getattr(adapter.enum_for("combo_animation"), name)


def resolve_text_intro(name: str):
    """文本段进场动画成员（Text_intro / CapCut_Text_intro）。"""
    return getattr(adapter.enum_for("text_intro"), name)


def resolve_text_outro(name: str):
    """文本段出场动画成员（Text_outro / CapCut_Text_outro）。"""
    return getattr(adapter.enum_for("text_outro"), name)


def resolve_video_effect(category: str, name: str):
    """场景/人物特效成员。category ∈ {'scene','character'}，未知名抛 AttributeError。

    迁自 add_effect_impl.py:43-68 的 IS_CAPCUT_ENV 分支：
      scene     → video_scene_effect     (Video_scene_effect_type / CapCut_Video_scene_effect_type)
      character → video_character_effect (Video_character_effect_type / CapCut_Video_character_effect_type)
    未知 category 抛 KeyError（与 enum_for 未知 kind 一致），由 service 转 InvalidParam。
    """
    kind = {"scene": "video_scene_effect", "character": "video_character_effect"}.get(category)
    if kind is None:
        raise KeyError(category)
    return getattr(adapter.enum_for(kind), name)


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

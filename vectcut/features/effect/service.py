"""effect feature service：add_effect + add_sticker。

迁自 add_effect_impl.py + add_sticker_impl.py。
- add_effect：IS_CAPCUT_ENV 四分支收敛为 material_factory.resolve_video_effect；params[::-1] 反转保真。
- add_sticker：无平台分支,Sticker_segment + Clip_settings。
"""

from __future__ import annotations

import pyJianYingDraft as draft
from pyJianYingDraft import Clip_settings, exceptions, trange

from vectcut.core.draft_store import get_or_create_draft
from vectcut.core.errors import InvalidParam
from vectcut.engine import material_factory as mf
from vectcut.features.draft.service import generate_draft_url
from vectcut.features.effect.schemas import (
    AddEffectRequest,
    AddEffectResponse,
    AddStickerRequest,
    AddStickerResponse,
)


def add_effect(req: AddEffectRequest) -> AddEffectResponse:
    draft_id, script = get_or_create_draft(req.draft_id, req.width, req.height)

    # 解析场景/人物特效(迁自 add_effect_impl.py:43-68 的 IS_CAPCUT_ENV 分支)
    try:
        effect_enum = mf.resolve_video_effect(req.effect_category, req.effect_type)
    except (AttributeError, KeyError):
        # 保真：原 impl 未知类型 raise ValueError(f"Unknown {category} effect type: {type}")
        raise InvalidParam(
            f"Unknown {req.effect_category} effect type: {req.effect_type}"
        )

    # get-or-create 命名特效轨道(迁自 add_effect_impl.py:73-82)
    if req.track_name is not None:
        try:
            script.get_imported_track(draft.Track_type.effect, name=req.track_name)
        except exceptions.TrackNotFound:
            script.add_track(draft.Track_type.effect, track_name=req.track_name)
    else:
        script.add_track(draft.Track_type.effect)

    # 保真：params 反转(add_effect_impl.py:85 params=params[::-1])；None 守卫见计划偏差说明
    duration = req.end - req.start
    t_range = trange(f"{req.start}s", f"{duration}s")
    reversed_params = req.params[::-1] if req.params is not None else None
    script.add_effect(effect_enum, t_range, params=reversed_params, track_name=req.track_name)

    return AddEffectResponse(draft_id=draft_id, draft_url=generate_draft_url(draft_id))


def add_sticker(req: AddStickerRequest) -> AddStickerResponse:
    draft_id, script = get_or_create_draft(req.draft_id, req.width, req.height)

    # get-or-create 命名贴纸轨道(迁自 add_sticker_impl.py:53-62)
    if req.track_name is not None:
        try:
            script.get_imported_track(draft.Track_type.sticker, name=req.track_name)
        except exceptions.TrackNotFound:
            script.add_track(
                draft.Track_type.sticker,
                track_name=req.track_name,
                relative_index=req.relative_index,
            )
    else:
        script.add_track(draft.Track_type.sticker, relative_index=req.relative_index)

    # 贴纸段(迁自 add_sticker_impl.py:64-78)
    sticker_segment = draft.Sticker_segment(
        req.sticker_id,
        trange(f"{req.start}s", f"{req.end - req.start}s"),
        clip_settings=Clip_settings(
            transform_y=req.transform_y,
            transform_x=req.transform_x,
            alpha=req.alpha,
            flip_horizontal=req.flip_horizontal,
            flip_vertical=req.flip_vertical,
            rotation=req.rotation,
            scale_x=req.scale_x,
            scale_y=req.scale_y,
        ),
    )

    script.add_segment(sticker_segment, track_name=req.track_name)
    return AddStickerResponse(draft_id=draft_id, draft_url=generate_draft_url(draft_id))

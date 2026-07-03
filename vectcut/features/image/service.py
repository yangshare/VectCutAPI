"""image feature service：add_image。

迁自 add_image_impl.py。5 处 IS_CAPCUT_ENV 分支(进/出/组动画、转场、掩膜)
收敛为 material_factory.resolve_*。保真点见计划任务 3 场景铺垫。
"""

from __future__ import annotations

import pyJianYingDraft as draft
from pyJianYingDraft import Clip_settings, exceptions, trange

from vectcut.core.draft_store import get_or_create_draft
from vectcut.core.errors import InvalidParam
from vectcut.engine import material_factory as mf
from vectcut.engine.material_factory import BLUR_MAP
from vectcut.features.draft.service import generate_draft_url
from vectcut.features.image.schemas import AddImageRequest, AddImageResponse
from util import url_to_hash


def add_image(req: AddImageRequest) -> AddImageResponse:
    draft_id, script = get_or_create_draft(req.draft_id, req.width, req.height)

    # 检查默认视频轨道(迁自 add_image_impl.py:91-98,保留 TrackNotFound + NameError 双分支)
    try:
        script.get_track(draft.Track_type.video, track_name=None)
    except exceptions.TrackNotFound:
        script.add_track(draft.Track_type.video, relative_index=0)
    except NameError:
        # 多视频轨道时 get_track 抛 NameError,什么都不做
        pass

    # get-or-create 命名视频轨道(迁自 add_image_impl.py:100-109)
    if req.track_name is not None:
        try:
            script.get_imported_track(draft.Track_type.video, name=req.track_name)
        except exceptions.TrackNotFound:
            script.add_track(
                draft.Track_type.video,
                track_name=req.track_name,
                relative_index=req.relative_index,
            )
    else:
        script.add_track(draft.Track_type.video, relative_index=req.relative_index)

    # 图片材料(迁自 add_image_impl.py:111-125)
    material_name = f"image_{url_to_hash(req.image_url)}.png"
    # draft_image_path 仅用于 print 副作用(原 impl 亦如此),不传入材料构造
    # build_photo_material 内部据 draft_folder 自行 build_draft_asset_path
    draft_image_path = None
    if req.draft_folder:
        from util import build_draft_asset_path
        draft_image_path = build_draft_asset_path(req.draft_folder, draft_id, "image", material_name)
        print("replace_path:", draft_image_path)

    image_material = mf.build_photo_material(
        image_url=req.image_url,
        draft_folder=req.draft_folder,
        draft_id=draft_id,
        material_name=material_name,
    )

    # 图片段(迁自 add_image_impl.py:127-143)
    duration = req.end - req.start
    target_timerange = trange(f"{req.start}s", f"{duration}s")
    source_timerange = trange(f"{0}s", f"{duration}s")
    image_segment = draft.Video_segment(
        image_material,
        target_timerange=target_timerange,
        source_timerange=source_timerange,
        clip_settings=Clip_settings(
            transform_y=req.transform_y,
            scale_x=req.scale_x,
            scale_y=req.scale_y,
            transform_x=req.transform_x,
        ),
    )

    # 进场动画(迁自 add_image_impl.py:145-156)：intro_animation 优先于 animation
    intro_anim = req.intro_animation if req.intro_animation is not None else req.animation
    intro_dur = (
        req.intro_animation_duration
        if req.intro_animation_duration is not None
        else req.animation_duration
    )
    if intro_anim:
        try:
            animation_type = mf.resolve_intro(intro_anim)
            image_segment.add_animation(animation_type, intro_dur * 1e6)  # float *1e6 保真
        except AttributeError:
            raise InvalidParam(
                f"Warning: Unsupported entrance animation type {intro_anim}, this parameter will be ignored"
            )

    # 出场动画(迁自 add_image_impl.py:158-167)
    if req.outro_animation:
        try:
            outro_type = mf.resolve_outro(req.outro_animation)
            image_segment.add_animation(outro_type, req.outro_animation_duration * 1e6)  # float *1e6 保真
        except AttributeError:
            raise InvalidParam(
                f"Warning: Unsupported exit animation type {req.outro_animation}, this parameter will be ignored"
            )

    # 组合动画(迁自 add_image_impl.py:169-178)
    if req.combo_animation:
        try:
            combo_type = mf.resolve_combo(req.combo_animation)
            image_segment.add_animation(combo_type, req.combo_animation_duration * 1e6)  # float *1e6 保真
        except AttributeError:
            raise InvalidParam(
                f"Warning: Unsupported combo animation type {req.combo_animation}, this parameter will be ignored"
            )

    # 转场(迁自 add_image_impl.py:180-191)：duration 用 int(*1000000) 整型截断(与动画 *1e6 不同)
    if req.transition:
        try:
            transition_type = mf.resolve_transition(req.transition)
            duration_microseconds = (
                int(req.transition_duration * 1000000)
                if req.transition_duration is not None
                else None
            )
            image_segment.add_transition(transition_type, duration=duration_microseconds)
        except AttributeError:
            raise InvalidParam(
                f"Warning: Unsupported transition type {req.transition}, this parameter will be ignored"
            )

    # 掩膜(迁自 add_image_impl.py:193-213)：裸 except 保真
    if req.mask_type:
        try:
            mask_type_enum = mf.resolve_mask(req.mask_type)
            image_segment.add_mask(
                script,
                mask_type_enum,
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
            raise InvalidParam(
                f"Unsupported mask type {req.mask_type}, supported types include: "
                "Linear, Mirror, Circle, Rectangle, Heart, Star"
            )

    # 背景模糊(迁自 add_image_impl.py:215-230)
    if req.background_blur is not None:
        if req.background_blur not in BLUR_MAP:
            raise InvalidParam(
                f"Invalid background blur level {req.background_blur}, valid values are 1-4"
            )
        image_segment.add_background_filling("blur", blur=BLUR_MAP[req.background_blur])

    script.add_segment(image_segment, track_name=req.track_name)
    return AddImageResponse(draft_id=draft_id, draft_url=generate_draft_url(draft_id))

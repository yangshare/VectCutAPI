"""audio feature service：add_audio。迁自 add_audio_track.py，effect 派发经 material_factory.resolve_audio_effect。"""

from __future__ import annotations

import pyJianYingDraft as draft
from pyJianYingDraft import trange

from vectcut.core.draft_store import get_or_create_draft
from vectcut.engine import material_factory as mf
from vectcut.features.audio.schemas import AddAudioRequest, AddAudioResponse
from vectcut.features.draft.service import generate_draft_url
from util import url_to_hash


def add_audio(req: AddAudioRequest) -> AddAudioResponse:
    draft_id, script = get_or_create_draft(req.draft_id, req.width, req.height)

    # get-or-create 命名音频轨道
    if req.track_name is not None:
        try:
            script.get_imported_track(draft.Track_type.audio, name=req.track_name)
        except Exception:
            script.add_track(draft.Track_type.audio, track_name=req.track_name)
    else:
        script.add_track(draft.Track_type.audio)

    audio_duration = req.duration if req.duration is not None else 0.0
    material_name = f"audio_{url_to_hash(req.audio_url)}.mp3"
    audio_material = mf.build_audio_material(
        audio_url=req.audio_url,
        draft_folder=req.draft_folder,
        draft_id=draft_id,
        material_name=material_name,
        duration=audio_duration,
    )

    audio_end = req.end if req.end is not None else audio_duration
    seg_duration = audio_end - req.start
    audio_segment = draft.Audio_segment(
        audio_material,
        target_timerange=trange(f"{req.target_start}s", f"{seg_duration}s"),
        source_timerange=trange(f"{req.start}s", f"{seg_duration}s"),
        speed=req.speed,
        volume=req.volume,
    )

    if req.effect_type:
        resolved = mf.resolve_audio_effect(req.effect_type)
        if resolved is not None:
            member, _subtype = resolved
            audio_segment.add_effect(member, req.effect_params)
        # 未命中：旧实现 print warning 并跳过，这里保持同样不抛

    script.add_segment(audio_segment, track_name=req.track_name)
    return AddAudioResponse(draft_id=draft_id, draft_url=generate_draft_url(draft_id))

"""material_factory 单测：材料构造 + 轨道 get-or-create + 平台枚举成员解析。"""
import pytest

from vectcut.engine import material_factory as mf


def test_build_video_material_without_draft_folder_uses_remote_url():
    m = mf.build_video_material(
        video_url="https://example.com/v.mp4",
        draft_folder=None,
        draft_id="dfd_1",
        material_name="video_abc.mp4",
        duration=3.0,
    )
    assert m.remote_url == "https://example.com/v.mp4"
    assert m.material_name == "video_abc.mp4"
    assert m.duration == 3_000_000  # 引擎存微秒：3.0s -> 3_000_000


def test_build_video_material_with_draft_folder_sets_replace_path():
    m = mf.build_video_material(
        video_url="https://example.com/v.mp4",
        draft_folder="/tmp/drafts",
        draft_id="dfd_1",
        material_name="video_abc.mp4",
        duration=3.0,
    )
    assert m.replace_path is not None
    assert "video_abc.mp4" in m.replace_path


def test_build_audio_material_basic():
    m = mf.build_audio_material(
        audio_url="https://example.com/a.mp3",
        draft_folder=None,
        draft_id="dfd_1",
        material_name="audio_xyz.mp3",
        duration=2.0,
    )
    assert m.remote_url == "https://example.com/a.mp3"
    assert m.material_name == "audio_xyz.mp3"


def test_resolve_transition_uses_active_platform(monkeypatch):
    """resolve_transition 经 adapter.enum_for('transition')，按平台取成员。"""
    from pyJianYingDraft.metadata.transition_meta import Transition_type
    from pyJianYingDraft.metadata.capcut_transition_meta import CapCut_Transition_type

    monkeypatch.setattr(mf.adapter, "active_platform", lambda: "jianying")
    member = mf.resolve_transition(list(Transition_type.__members__)[0])
    assert member in Transition_type.__members__.values()

    monkeypatch.setattr(mf.adapter, "active_platform", lambda: "capcut")
    member = mf.resolve_transition(list(CapCut_Transition_type.__members__)[0])
    assert member in CapCut_Transition_type.__members__.values()


def test_resolve_transition_unknown_name_raises_attr_error(monkeypatch):
    monkeypatch.setattr(mf.adapter, "active_platform", lambda: "jianying")
    with pytest.raises(AttributeError):
        mf.resolve_transition("DEFINITELY_NOT_A_TRANSITION")


def test_resolve_mask_uses_active_platform(monkeypatch):
    from pyJianYingDraft.metadata.mask_meta import Mask_type

    monkeypatch.setattr(mf.adapter, "active_platform", lambda: "jianying")
    member = mf.resolve_mask(list(Mask_type.__members__)[0])
    assert member in Mask_type.__members__.values()


def test_resolve_audio_effect_searches_all_subtypes(monkeypatch):
    """audio_effect 返回 {子类型: 枚举} dict，resolve_audio_effect 遍历子类型命中。"""
    from pyJianYingDraft.metadata.audio_effect_meta import Tone_effect_type

    monkeypatch.setattr(mf.adapter, "active_platform", lambda: "jianying")
    first_name = list(Tone_effect_type.__members__)[0]
    member, subtype = mf.resolve_audio_effect(first_name)
    assert member in Tone_effect_type.__members__.values()
    assert subtype == "Tone"


def test_resolve_audio_effect_unknown_returns_none(monkeypatch):
    monkeypatch.setattr(mf.adapter, "active_platform", lambda: "jianying")
    assert mf.resolve_audio_effect("NOPE") is None


def test_add_to_track_creates_track_if_missing():
    import pyJianYingDraft as draft
    from vectcut.core import draft_store

    draft_store.DRAFT_CACHE.clear()
    _, script = draft_store.get_or_create_draft(None, 1080, 1920)
    material = mf.build_video_material("https://e.com/v.mp4", None, "x", "v.mp4", 1.0)
    seg = draft.Video_segment(material, target_timerange=draft.trange("0s", "1s"), source_timerange=draft.trange("0s", "1s"))
    mf.add_to_track(script, seg, track_name="video_main", track_type=draft.Track_type.video, relative_index=0)
    assert len(script.materials.videos) == 1

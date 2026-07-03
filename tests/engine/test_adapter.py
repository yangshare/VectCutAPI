import pytest


def test_active_platform_reflects_config_profile(monkeypatch):
    """active_platform() 读 draft_store.get_active_profile().is_capcut_env。"""
    from vectcut.engine import adapter
    from vectcut.core import draft_store

    class FakeProfile:
        is_capcut_env = True

    monkeypatch.setattr(draft_store, "get_active_profile", lambda: FakeProfile())
    assert adapter.active_platform() == "capcut"

    class FakeProfile2:
        is_capcut_env = False

    monkeypatch.setattr(draft_store, "get_active_profile", lambda: FakeProfile2())
    assert adapter.active_platform() == "jianying"


def test_enum_for_simple_kind_returns_platform_enum(monkeypatch):
    from vectcut.engine import adapter
    from pyJianYingDraft.metadata.animation_meta import Intro_type
    from pyJianYingDraft.metadata.capcut_animation_meta import CapCut_Intro_type

    monkeypatch.setattr(adapter, "active_platform", lambda: "capcut")
    assert adapter.enum_for("intro_animation") is CapCut_Intro_type

    monkeypatch.setattr(adapter, "active_platform", lambda: "jianying")
    assert adapter.enum_for("intro_animation") is Intro_type


def test_enum_for_font_has_no_capcut_variant_returns_same_on_both_platforms(monkeypatch):
    from vectcut.engine import adapter
    from pyJianYingDraft.metadata.font_meta import Font_type

    monkeypatch.setattr(adapter, "active_platform", lambda: "capcut")
    assert adapter.enum_for("font") is Font_type

    monkeypatch.setattr(adapter, "active_platform", lambda: "jianying")
    assert adapter.enum_for("font") is Font_type


def test_enum_for_audio_effect_returns_subtype_dict(monkeypatch):
    from vectcut.engine import adapter

    monkeypatch.setattr(adapter, "active_platform", lambda: "capcut")
    cap = adapter.enum_for("audio_effect")
    assert list(cap.keys()) == ["Voice_filters", "Voice_characters", "Speech_to_song"]

    monkeypatch.setattr(adapter, "active_platform", lambda: "jianying")
    jy = adapter.enum_for("audio_effect")
    assert list(jy.keys()) == ["Tone", "Audio_scene", "Speech_to_song"]


def test_enum_for_unknown_kind_raises():
    from vectcut.engine import adapter

    with pytest.raises(KeyError):
        adapter.enum_for("nope_kind")

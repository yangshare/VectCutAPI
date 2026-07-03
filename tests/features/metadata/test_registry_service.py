import pytest


def test_list_metadata_simple_kind_returns_name_only_items(monkeypatch):
    from vectcut.features.metadata import service
    from pyJianYingDraft.metadata.animation_meta import Intro_type

    items = service.list_metadata("intro_animation", enum=Intro_type)
    assert items and all(set(i.keys()) == {"name"} for i in items)
    assert all(i["name"] for i in items)


def test_list_metadata_audio_effect_rich_shape_with_params(monkeypatch):
    from vectcut.features.metadata import service
    from pyJianYingDraft.metadata.audio_effect_meta import (
        Tone_effect_type,
        Audio_scene_effect_type,
        Speech_to_song_type,
    )

    items = service.list_metadata(
        "audio_effect",
        enum={
            "Tone": Tone_effect_type,
            "Audio_scene": Audio_scene_effect_type,
            "Speech_to_song": Speech_to_song_type,
        },
    )
    tone_items = [i for i in items if i["type"] == "Tone"]
    assert tone_items, "Tone 子类型应被展开"
    sample = tone_items[0]
    assert set(sample.keys()) == {"name", "type", "params"}
    if sample["params"]:
        p = sample["params"][0]
        assert set(p.keys()) == {"name", "default_value", "min_value", "max_value"}


def test_list_metadata_unknown_kind_raises_invalid_param():
    from vectcut.features.metadata import service
    from vectcut.core.errors import InvalidParam

    with pytest.raises(InvalidParam):
        service.list_metadata("nope")


def test_list_metadata_default_uses_adapter_enum_for(monkeypatch):
    """不传 enum 时，service 走 adapter.enum_for(kind)。"""
    from vectcut.features.metadata import service
    from vectcut.engine import adapter
    from pyJianYingDraft.metadata.font_meta import Font_type

    monkeypatch.setattr(adapter, "enum_for", lambda kind: Font_type)
    items = service.list_metadata("font")
    assert items and all(set(i.keys()) == {"name"} for i in items)


def test_registry_covers_all_11_kinds():
    from vectcut.features.metadata.registry import META_KINDS

    expected = {
        "intro_animation",
        "outro_animation",
        "combo_animation",
        "transition",
        "mask",
        "audio_effect",
        "font",
        "text_intro",
        "text_outro",
        "text_loop_anim",
        "video_scene_effect",
        "video_character_effect",
    }
    assert set(META_KINDS.keys()) == expected

import pyJianYingDraft as draft

from vectcut.core.draft_store import DRAFT_CACHE


def _fresh():
    DRAFT_CACHE.clear()


def test_add_text_creates_text_segment_with_named_track():
    from vectcut.features.text.schemas import AddTextRequest
    from vectcut.features.text.service import add_text

    _fresh()
    req = AddTextRequest(text="hello", start=0, end=2.0)
    resp = add_text(req)
    assert resp.draft_id.startswith("dfd_cat_")


def test_add_text_track_name_none_creates_audio_track_not_text():
    """保真：track_name=None 时创建音频轨道(add_text_impl.py:138 既有行为)。"""
    from vectcut.features.text.schemas import AddTextRequest
    from vectcut.features.text.service import add_text

    _fresh()
    req = AddTextRequest(text="hello", start=0, end=2.0, track_name=None)
    add_text(req)
    # 验证存在音频轨道(而非文本轨道)
    script = next(iter(DRAFT_CACHE.values()))
    # add_track(audio) 会将 'audio' 作为键加入 script.tracks
    assert "audio" in script.tracks
    # 无文本轨道(因 track_name=None, path 不会建 text track)
    text_tracks = [k for k, t in script.tracks.items() if t.track_type == draft.Track_type.text]
    assert len(text_tracks) == 0


def test_add_text_unknown_intro_animation_prints_warning_does_not_raise(capsys):
    """保真：未知动画 print warning 后跳过,不 raise(与 add_image 严格策略不同)。"""
    from vectcut.features.text.schemas import AddTextRequest
    from vectcut.features.text.service import add_text

    _fresh()
    req = AddTextRequest(text="hello", start=0, end=2.0, intro_animation="__no_such_anim__")
    add_text(req)  # 不应抛
    out = capsys.readouterr().out
    assert "Unsupported intro animation type" in out


def test_add_text_intro_duration_uses_int_truncation(monkeypatch):
    """保真：动画时长 int(intro_duration*1000000) 整型截断(非 *1e6)。
    monkeypatch resolve_text_intro 跳过真实枚举解析,隔离验证整型截断。"""
    captured = {}
    from vectcut.features.text.schemas import AddTextRequest
    from vectcut.features.text import service

    _fresh()
    req = AddTextRequest(text="hello", start=0, end=2.0, intro_animation="Soft", intro_duration=0.7)
    monkeypatch.setattr(service.mf, "resolve_text_intro", lambda name: object())

    def _spy(self, anim_type, duration):
        captured["duration"] = duration
        return None

    monkeypatch.setattr(draft.Text_segment, "add_animation", _spy)
    service.add_text(req)
    assert captured["duration"] == int(0.7 * 1000000)


def test_add_text_invalid_text_style_range_raises_with_chinese_message():
    import pytest
    from vectcut.core.errors import InvalidParam
    from vectcut.features.text.schemas import AddTextRequest, TextStyleRangeSpec
    from vectcut.features.text.service import add_text

    _fresh()
    req = AddTextRequest(
        text="ab", start=0, end=2.0,
        text_styles=[TextStyleRangeSpec(start=0, end=99)],  # end > len(text)
    )
    with pytest.raises(InvalidParam) as exc:
        add_text(req)
    assert "无效的文本范围" in str(exc.value)


def test_add_text_unknown_font_raises_invalid_param():
    import pytest
    from vectcut.core.errors import InvalidParam
    from vectcut.features.text.schemas import AddTextRequest
    from vectcut.features.text.service import add_text

    _fresh()
    req = AddTextRequest(text="ab", start=0, end=2.0, font="__no_such_font__")
    with pytest.raises(InvalidParam) as exc:
        add_text(req)
    assert "Unsupported font" in str(exc.value)


def test_add_subtitle_pure_text_replaces_escape_sequences():
    """保真：纯文本 SRT 内容 replace('\\n','\\n').replace('/n','\\n') 后 import_srt。"""
    captured = {}
    from vectcut.features.text.schemas import AddSubtitleRequest
    from vectcut.features.text import service

    _fresh()
    req = AddSubtitleRequest(srt="1\\n00:00:01 --> 00:00:02\\nHello/nWorld")

    def _spy(self, srt_content, *args, **kwargs):
        captured["content"] = srt_content
        return None

    from unittest.mock import patch
    with patch.object(draft.Script_file, "import_srt", _spy):
        service.add_subtitle(req)
    # \\n 与 /n 都应被替换为真实换行
    assert "\\n" not in captured["content"].replace("\n", "")  # 反斜杠+n 已转真换行
    assert "\n" in captured["content"]


def test_add_subtitle_text_effect_reuses_effect_id_as_resource_id(monkeypatch):
    """保真：TextEffect(effect_id=x, resource_id=x) resource_id 复用(add_subtitle_impl.py:139-141)。"""
    from vectcut.features.text.schemas import AddSubtitleRequest
    from vectcut.features.text import service
    from pyJianYingDraft.text_segment import TextEffect

    _fresh()
    captured = {}
    orig_init = TextEffect.__init__

    def spy(self, *args, **kwargs):
        captured["kwargs"] = kwargs
        return orig_init(self, *args, **kwargs)

    monkeypatch.setattr(TextEffect, "__init__", spy)
    req = AddSubtitleRequest(srt="text", effect_effect_id="eff_123")
    from unittest.mock import patch
    with patch.object(draft.Script_file, "import_srt", lambda self, *a, **k: None):
        service.add_subtitle(req)
    assert captured["kwargs"].get("resource_id") == "eff_123"
    assert captured["kwargs"].get("effect_id") == "eff_123"

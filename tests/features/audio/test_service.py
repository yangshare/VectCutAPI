import pytest

from vectcut.core import draft_store


@pytest.fixture(autouse=True)
def _clean_cache():
    draft_store.DRAFT_CACHE.clear()
    yield
    draft_store.DRAFT_CACHE.clear()


def test_add_audio_creates_audio_segment():
    from vectcut.features.audio import service
    from vectcut.features.audio.schemas import AddAudioRequest

    resp = service.add_audio(AddAudioRequest(audio_url="https://example.com/a.mp3"))
    script = draft_store.get_draft(resp.draft_id)
    assert len(script.materials.audios) == 1
    assert script.materials.audios[0].remote_url == "https://example.com/a.mp3"


def test_add_audio_with_effect_resolves_via_adapter(monkeypatch):
    from vectcut.features.audio import service
    from vectcut.features.audio.schemas import AddAudioRequest
    from vectcut.engine import material_factory

    captured = {}
    def fake_resolve(name):
        captured["name"] = name
        class _M: pass
        return _M(), "Tone"
    monkeypatch.setattr(material_factory, "resolve_audio_effect", fake_resolve)
    import pyJianYingDraft as draft
    orig = draft.Audio_segment
    class FakeSeg(orig):
        def add_effect(self, *a, **kw): captured["added"] = True
    monkeypatch.setattr(draft, "Audio_segment", FakeSeg)

    service.add_audio(AddAudioRequest(
        audio_url="https://e.com/a.mp3",
        effect_type="SomeEffect",
        effect_params=[0.5],
    ))
    assert captured.get("name") == "SomeEffect"

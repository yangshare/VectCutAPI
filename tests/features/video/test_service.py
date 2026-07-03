import pytest

from vectcut.core import draft_store


@pytest.fixture(autouse=True)
def _clean_cache():
    draft_store.DRAFT_CACHE.clear()
    yield
    draft_store.DRAFT_CACHE.clear()


def test_add_video_creates_video_segment_in_draft():
    from vectcut.features.video import service
    from vectcut.features.video.schemas import AddVideoRequest

    resp = service.add_video(AddVideoRequest(video_url="https://example.com/v.mp4"))
    assert resp.draft_id.startswith("dfd_cat_")
    script = draft_store.get_draft(resp.draft_id)
    assert script is not None
    assert len(script.materials.videos) == 1
    assert script.materials.videos[0].remote_url == "https://example.com/v.mp4"


def test_add_video_with_transition_resolves_via_adapter(monkeypatch):
    from vectcut.features.video import service
    from vectcut.features.video.schemas import AddVideoRequest
    from vectcut.engine import material_factory

    called = {}
    def fake_resolve(name):
        called["name"] = name
        class _M:
            pass
        return _M()
    monkeypatch.setattr(material_factory, "resolve_transition", fake_resolve)
    # transition add_transition 会调引擎；mock segment.add_transition
    import pyJianYingDraft as draft
    orig_seg = draft.Video_segment
    class FakeSeg(orig_seg):
        def add_transition(self, *a, **kw):
            called["added"] = True
    monkeypatch.setattr(draft, "Video_segment", FakeSeg)

    service.add_video(AddVideoRequest(video_url="https://e.com/v.mp4", transition="Fade"))
    assert called.get("name") == "Fade"


def test_add_video_unknown_transition_raises(monkeypatch):
    from vectcut.features.video import service
    from vectcut.features.video.schemas import AddVideoRequest
    from vectcut.core.errors import InvalidParam
    from vectcut.engine import material_factory

    monkeypatch.setattr(material_factory, "resolve_transition", lambda name: (_ for _ in ()).throw(AttributeError(name)))
    with pytest.raises(InvalidParam):
        service.add_video(AddVideoRequest(video_url="https://e.com/v.mp4", transition="NOPE"))

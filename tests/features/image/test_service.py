import pyJianYingDraft as draft
from vectcut.core.draft_store import DRAFT_CACHE


def _fresh_draft():
    DRAFT_CACHE.clear()


def test_add_image_creates_photo_segment_with_named_track():
    from vectcut.features.image.schemas import AddImageRequest
    from vectcut.features.image import service
    _fresh_draft()
    req = AddImageRequest(
        image_url="https://example.com/a.png",
        start=0,
        end=2.0,
    )
    resp = service.add_image(req)
    assert resp.draft_id.startswith("dfd_cat_")


def test_add_image_intro_animation_takes_priority_over_animation(monkeypatch):
    """保真：intro_animation 非 None 时优先于 animation(向后兼容)。
    monkeypatch resolve_intro 跳过真实枚举解析,隔离验证优先级与 *1e6 时长。
    """
    captured = {}
    from vectcut.features.image.schemas import AddImageRequest
    from vectcut.features.image import service
    _fresh_draft()
    req = AddImageRequest(
        image_url="https://example.com/a.png",
        animation="Fade In",
        animation_duration=0.3,
        intro_animation="Zoom In",
        intro_animation_duration=0.7,
    )
    monkeypatch.setattr(service.mf, "resolve_intro", lambda name: object())

    def _spy(self, anim_type, duration):
        captured.setdefault("calls", []).append((anim_type, duration))
        return None

    monkeypatch.setattr(draft.Video_segment, "add_animation", _spy)
    service.add_image(req)
    # 第一条 add_animation 调用应是 intro(duration=0.7*1e6 float)
    assert captured["calls"][0][1] == 0.7 * 1e6


def test_add_image_unknown_mask_raises_invalid_param_with_fidelity_message():
    import pytest
    from vectcut.core.errors import InvalidParam
    from vectcut.features.image.schemas import AddImageRequest
    from vectcut.features.image.service import add_image
    _fresh_draft()
    req = AddImageRequest(
        image_url="https://example.com/a.png",
        mask_type="__no_such_mask__",
    )
    with pytest.raises(InvalidParam) as exc:
        add_image(req)
    assert "Unsupported mask type" in str(exc.value)
    assert "Linear, Mirror, Circle, Rectangle, Heart, Star" in str(exc.value)


def test_add_image_invalid_blur_level_raises():
    import pytest
    from vectcut.core.errors import InvalidParam
    from vectcut.features.image.schemas import AddImageRequest
    from vectcut.features.image.service import add_image
    _fresh_draft()
    req = AddImageRequest(
        image_url="https://example.com/a.png",
        background_blur=9,
    )
    with pytest.raises(InvalidParam):
        add_image(req)


def test_add_image_transition_duration_uses_int_truncation(monkeypatch):
    """保真：转场时长 int(transition_duration*1000000)(整型截断),与动画 *1e6(float)不同。
    monkeypatch resolve_transition 跳过真实枚举解析,隔离验证整型截断。
    """
    captured = {}
    from vectcut.features.image.schemas import AddImageRequest
    from vectcut.features.image import service
    _fresh_draft()
    req = AddImageRequest(
        image_url="https://example.com/a.png",
        transition="Dissolve",
        transition_duration=0.7,
    )
    monkeypatch.setattr(service.mf, "resolve_transition", lambda name: object())

    def _spy(self, transition_type, duration=None):
        captured["duration"] = duration
        return None

    monkeypatch.setattr(draft.Video_segment, "add_transition", _spy)
    service.add_image(req)
    assert captured["duration"] == int(0.7 * 1000000)  # 整型,非 0.7e6

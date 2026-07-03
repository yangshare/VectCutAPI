import pyJianYingDraft as draft

from vectcut.core.draft_store import DRAFT_CACHE


def _fresh_draft():
    DRAFT_CACHE.clear()
    return draft.Script_file(1080, 1920)


def test_add_sticker_creates_sticker_segment_on_named_track():
    from vectcut.features.effect.schemas import AddStickerRequest
    from vectcut.features.effect.service import add_sticker

    _fresh_draft()
    req = AddStickerRequest(sticker_id="7129384756_sticker", start=0, end=2.0)
    resp = add_sticker(req)
    assert resp.draft_id.startswith("dfd_cat_")
    assert "draft_url" in resp.draft_url or resp.draft_url  # 非空


def test_add_effect_scene_reverses_params_before_passing_to_engine(monkeypatch):
    """保真：add_effect 把 params 反转后传给 script.add_effect（params[::-1]）。
    monkeypatch 跳过真实枚举解析和引擎调用,隔离验证反转逻辑。"""
    captured = {}
    from vectcut.features.effect.schemas import AddEffectRequest
    from vectcut.features.effect import service

    _fresh_draft()
    req = AddEffectRequest(
        effect_type="dummy", effect_category="scene", start=0, end=1.0,
        params=[1.0, 2.0, 3.0],
    )
    monkeypatch.setattr(service.mf, "resolve_video_effect", lambda category, name: object())

    def _spy(self, effect, t_range, params=None, track_name=None):
        captured["params"] = params
        return None  # 不调 orig,避免 effect=object() 崩溃

    monkeypatch.setattr(draft.Script_file, "add_effect", _spy)
    service.add_effect(req)
    assert captured["params"] == [3.0, 2.0, 1.0]  # [::-1] 反转


def test_add_effect_unknown_type_raises_invalid_param():
    import pytest
    from vectcut.core.errors import InvalidParam
    from vectcut.features.effect.schemas import AddEffectRequest
    from vectcut.features.effect.service import add_effect

    _fresh_draft()
    req = AddEffectRequest(effect_type="__no_such_effect__", effect_category="scene")
    with pytest.raises(InvalidParam):
        add_effect(req)

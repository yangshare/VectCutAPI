"""effect feature FastAPI router 测试。"""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from vectcut.features.effect.router import router
from vectcut.server.http.app import _wire_exception_handlers


def _client() -> TestClient:
    app = FastAPI()
    _wire_exception_handlers(app)
    app.include_router(router)
    return TestClient(app)


def test_add_effect_route_missing_type_returns_error():
    resp = _client().post("/add_effect", json={})
    body = resp.json()
    assert body["success"] is False
    assert "effect_type" in body["error"]


def test_add_sticker_route_missing_id_returns_error():
    resp = _client().post("/add_sticker", json={})
    body = resp.json()
    assert body["success"] is False
    assert "sticker_id" in body["error"]


def test_add_effect_route_success_envelope(monkeypatch):
    from vectcut.features.effect import service
    from vectcut.features.effect.schemas import AddEffectResponse

    # monkeypatch service,只验路由成功 envelope 外壳(不依赖真实特效枚举成员名)
    monkeypatch.setattr(
        service, "add_effect",
        lambda req: AddEffectResponse(draft_id="dfd_cat_x", draft_url="http://x"),
    )
    resp = _client().post("/add_effect", json={"effect_type": "dummy", "effect_category": "scene"})
    body = resp.json()
    assert body["success"] is True
    assert body["output"]["draft_id"] == "dfd_cat_x"
    assert body["error"] == ""

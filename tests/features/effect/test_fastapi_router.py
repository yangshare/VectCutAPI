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

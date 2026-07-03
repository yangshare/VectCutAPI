"""text feature FastAPI router 测试。"""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from vectcut.core import draft_store
from vectcut.features.text.router import router
from vectcut.server.http.app import _wire_exception_handlers


def _client() -> TestClient:
    app = FastAPI()
    _wire_exception_handlers(app)
    app.include_router(router)
    return TestClient(app)


def test_add_text_route_missing_text_returns_error():
    resp = _client().post("/add_text", json={"start": 0, "end": 1})
    body = resp.json()
    assert body["success"] is False


def test_add_text_route_success():
    draft_store.DRAFT_CACHE.clear()
    resp = _client().post(
        "/add_text", json={"text": "hello", "start": 0, "end": 1}
    )
    body = resp.json()
    assert body["success"] is True
    assert body["output"]["draft_id"].startswith("dfd_cat_")


def test_add_subtitle_route_missing_srt_returns_error():
    resp = _client().post("/add_subtitle", json={})
    body = resp.json()
    assert body["success"] is False
    assert "srt" in body["error"]


def test_add_text_route_color_alias_maps_to_font_color():
    # color 别名应被归一化为 font_color
    draft_store.DRAFT_CACHE.clear()
    resp = _client().post(
        "/add_text", json={"text": "hi", "start": 0, "end": 1, "color": "#00FF00"}
    )
    body = resp.json()
    assert body["success"] is True

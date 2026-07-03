"""image feature FastAPI router 测试。"""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from vectcut.core import draft_store
from vectcut.features.image.router import router
from vectcut.server.http.app import _wire_exception_handlers


def _client() -> TestClient:
    app = FastAPI()
    _wire_exception_handlers(app)
    app.include_router(router)
    return TestClient(app)


def test_add_image_route_missing_url_returns_error():
    resp = _client().post("/add_image", json={})
    body = resp.json()
    assert body["success"] is False
    assert "image_url" in body["error"]


def test_add_image_route_success():
    draft_store.DRAFT_CACHE.clear()
    resp = _client().post(
        "/add_image",
        json={"image_url": "https://example.com/i.png", "start": 0, "end": 1},
    )
    body = resp.json()
    assert body["success"] is True
    assert body["output"]["draft_id"].startswith("dfd_cat_")

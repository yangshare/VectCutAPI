"""video feature FastAPI router 测试。"""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from vectcut.core import draft_store
from vectcut.features.video.router import router
from vectcut.server.http.app import _wire_exception_handlers


def _client() -> TestClient:
    app = FastAPI()
    _wire_exception_handlers(app)
    app.include_router(router)
    return TestClient(app)


def test_add_video_route_missing_video_url_returns_error():
    resp = _client().post("/add_video", json={})
    body = resp.json()
    assert body["success"] is False
    assert "video_url" in body["error"]


def test_add_video_route_success():
    draft_store.DRAFT_CACHE.clear()
    resp = _client().post("/add_video", json={"video_url": "https://example.com/v.mp4"})
    body = resp.json()
    assert body["success"] is True
    assert body["output"]["draft_id"].startswith("dfd_cat_")


def test_add_video_keyframe_route_missing_draft_id():
    resp = _client().post("/add_video_keyframe", json={})
    body = resp.json()
    assert body["success"] is False

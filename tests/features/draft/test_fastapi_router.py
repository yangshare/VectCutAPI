"""draft feature FastAPI router 测试（独立挂载，不经全局 app）。"""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from vectcut.core import draft_store
from vectcut.features.draft.router import router
from vectcut.server.http.app import _wire_exception_handlers


def _client() -> TestClient:
    app = FastAPI()
    _wire_exception_handlers(app)
    app.include_router(router)
    return TestClient(app)


def test_create_draft_route_returns_envelope():
    draft_store.DRAFT_CACHE.clear()
    resp = _client().post("/create_draft", json={})
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["output"]["draft_id"].startswith("dfd_cat_")
    assert "draft_url" in body["output"]
    assert body["error"] == ""


def test_save_draft_route_missing_draft_id_returns_error_envelope():
    resp = _client().post("/save_draft", json={})
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert "draft_id" in body["error"]


def test_query_script_route_missing_returns_error():
    resp = _client().post("/query_script", json={"draft_id": "missing"})
    assert resp.status_code == 200
    assert resp.json()["success"] is False


def test_query_draft_status_route_not_found():
    resp = _client().post("/query_draft_status", json={"task_id": "nope"})
    body = resp.json()
    assert body["success"] is True
    assert body["output"]["status"] == "not_found"


def test_generate_draft_url_route():
    resp = _client().post("/generate_draft_url", json={"draft_id": "dfd_1"})
    body = resp.json()
    assert body["success"] is True
    assert "dfd_1" in body["output"]["draft_url"]


def test_get_video_duration_service_returns_envelope_dict():
    """MCP 用的 get_video_duration service：返回 {success,output,error} 结构（迁自 _save_engine）。"""
    from vectcut.features.draft import service
    from vectcut.features.draft.schemas import GetVideoDurationRequest

    resp = service.get_video_duration(GetVideoDurationRequest(video_url="https://example.com/nope.mp4"))
    result = resp.model_dump()
    # ffprobe 失败时 success=False；只要结构正确即可（真实 ffprobe 由黄金/集成测试覆盖）
    assert set(result.keys()) >= {"success", "output", "error"}

"""router 冒烟测试：验证 4 个端点路由注册正确（不 404）。

不验证业务成功路径——只确认 prefix=/api/template 路由可达。
"""
from fastapi.testclient import TestClient

from vectcut.server.http import app

client = TestClient(app)


def test_import_endpoint_registered():
    # 不传 file 会 422（FastAPI 参数校验），但不是 404 → 路由存在
    resp = client.post("/api/template/import?template_id=t1")
    assert resp.status_code != 404


def test_slot_config_endpoint_registered():
    resp = client.post("/api/template/slot-config", json={})
    assert resp.status_code != 404
    # 空 body 应返回 envelope_err（校验失败）
    data = resp.json()
    assert data["success"] is False


def test_render_endpoint_registered():
    resp = client.post("/api/template/render", json={})
    assert resp.status_code != 404
    data = resp.json()
    assert data["success"] is False


def test_download_endpoint_registered():
    resp = client.get("/api/template/download/draft_nonexistent")
    assert resp.status_code != 404
    data = resp.json()
    assert data["success"] is False

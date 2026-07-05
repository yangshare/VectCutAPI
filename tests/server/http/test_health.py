"""健康检查端点测试。"""
from datetime import datetime
import importlib

from fastapi.testclient import TestClient

from vectcut.server.http import app

app_module = importlib.import_module("vectcut.server.http.app")


def test_health_endpoint(monkeypatch):
    """GET /api/health 返回 200 + healthy 状态。"""
    monkeypatch.setattr(app_module, "__version__", "9.9.9-test", raising=False)
    client = TestClient(app)
    resp = client.get("/api/health")

    assert resp.status_code == 200
    data = resp.json()
    assert set(data) == {"status", "timestamp", "version"}
    assert data["status"] == "healthy"
    assert data["version"] == "9.9.9-test"
    datetime.fromisoformat(data["timestamp"])

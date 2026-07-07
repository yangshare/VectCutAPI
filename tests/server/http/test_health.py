"""健康检查端点测试。"""
from datetime import datetime
import importlib

from fastapi.testclient import TestClient

from vectcut.server.http import app

app_module = importlib.import_module("vectcut.server.http.app")


def _assert_healthy_response(resp):
    assert resp.status_code == 200
    data = resp.json()
    assert set(data) == {"status", "timestamp", "version"}
    assert data["status"] == "healthy"
    assert data["version"] == "9.9.9-test"
    datetime.fromisoformat(data["timestamp"])


def test_api_health_endpoint(monkeypatch):
    """GET /api/health 返回 200 + healthy 状态。"""
    monkeypatch.setattr(app_module, "__version__", "9.9.9-test", raising=False)
    client = TestClient(app)
    _assert_healthy_response(client.get("/api/health"))


def test_root_health_endpoint_alias(monkeypatch):
    """GET /health 与 /api/health 返回同一健康检查形状。"""
    monkeypatch.setattr(app_module, "__version__", "9.9.9-test", raising=False)
    client = TestClient(app)
    _assert_healthy_response(client.get("/health"))


def test_create_app_compatibility_factory_returns_configured_app(monkeypatch):
    """create_app 兼容计划中的 TestClient(create_app()) 用法。"""
    monkeypatch.setattr(app_module, "__version__", "9.9.9-test", raising=False)
    client = TestClient(app_module.create_app())
    _assert_healthy_response(client.get("/health"))
    _assert_healthy_response(client.get("/api/health"))

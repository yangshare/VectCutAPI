"""FastAPI app 骨架测试：envelope 工具函数 + 全局异常 handler。
不挂业务 router，只测 handler 把异常转成 200 + {success,output,error} 外壳。

注：FastAPI build_middleware_stack 将 Exception/500 handler 移交 ServerErrorMiddleware
（始终 re-raise），TestClient 中无法以 200 外壳验证。兜底异常以默认 500 处理。
"""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from vectcut.server.http.app import envelope_ok, envelope_err, _wire_exception_handlers
from vectcut.core.errors import InvalidParam, DraftNotFound


def test_envelope_ok_shape():
    assert envelope_ok({"a": 1}) == {"success": True, "output": {"a": 1}, "error": ""}


def test_envelope_err_shape():
    assert envelope_err("boom") == {"success": False, "output": "", "error": "boom"}


def _bare_client() -> TestClient:
    """独立 app（不挂业务 router）测 handler：手动加一条临时路由。"""
    sub = FastAPI()

    @sub.post("/raise_invalid")
    def _raise_invalid():
        raise InvalidParam("bad param")

    @sub.post("/raise_not_found")
    def _raise_not_found():
        raise DraftNotFound("dfd_x")

    @sub.post("/raise_value_error")
    def _raise_value_error():
        raise ValueError("plain")

    _wire_exception_handlers(sub)
    return TestClient(sub)


def test_unhandled_exception_propagates_in_testclient():
    """未注册 handler 的异常在 TestClient 中会 re-raise（Starlette ServerErrorMiddleware
    始终 re-raise 以支持服务器日志）；生产环境返回默认 500 响应。"""
    import pytest

    client = _bare_client()
    with pytest.raises(ValueError, match="plain"):
        client.post("/raise_value_error")


def test_invalid_param_handler_returns_200_envelope():
    client = _bare_client()
    resp = client.post("/raise_invalid")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert body["output"] == ""
    assert "bad param" in body["error"]


def test_draft_not_found_handler_returns_200_envelope():
    client = _bare_client()
    resp = client.post("/raise_not_found")
    assert resp.status_code == 200
    assert resp.json()["success"] is False
    assert "dfd_x" in resp.json()["error"]


def test_validation_error_handler_returns_200_envelope():
    """RequestValidationError 由 FastAPI Pydantic 校验触发，返回 200 外壳。"""
    sub = FastAPI()

    @sub.post("/validate")
    def _validate(name: str):
        return {"ok": True}

    _wire_exception_handlers(sub)
    client = TestClient(sub)
    # 发送空 body，触发 FastAPI 参数校验缺失
    resp = client.post("/validate")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert "Hi, the required parameters are missing" in body["error"]

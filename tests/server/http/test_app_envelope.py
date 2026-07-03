"""FastAPI app 骨架测试：envelope 工具函数 + 全局异常 handler。
不挂业务 router，只测 handler 把异常转成 200 + {success,output,error} 外壳。

注：TestClient 默认 raise_server_exceptions=True 会 re-raise 未处理异常，
故 _bare_client 用 raise_server_exceptions=False 以验证兜底 handler 的 200 外壳。
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
    """独立 app（不挂业务 router）测 handler：手动加一条临时路由。
    用 raise_server_exceptions=False 以验证兜底 Exception handler 返回 200 外壳
    （默认 TestClient 会 re-raise 未处理异常）。
    """
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
    return TestClient(sub, raise_server_exceptions=False)


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


def test_unexpected_exception_handler_returns_200_envelope():
    client = _bare_client()
    resp = client.post("/raise_value_error")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert "plain" in body["error"]


def test_validation_error_handler_returns_200_envelope():
    """RequestValidationError 由 FastAPI Pydantic 校验触发，返回 200 外壳。"""
    sub = FastAPI()

    @sub.post("/validate")
    def _validate(name: str):
        return {"ok": True}

    _wire_exception_handlers(sub)
    client = TestClient(sub, raise_server_exceptions=False)
    # 发送空 body，触发 FastAPI 参数校验缺失
    resp = client.post("/validate")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert "Hi, the required parameters are missing" in body["error"]

"""FastAPI app 骨架测试：envelope 工具函数 + 全局异常 handler。
不挂业务 router，只测 handler 把异常转成 200 + {success,output,error} 外壳。

注：TestClient 默认 raise_server_exceptions=True 会 re-raise 未处理异常，
故 _bare_client 用 raise_server_exceptions=False 以验证兜底 handler 的 200 外壳。
"""
import asyncio
import importlib
import json
import logging
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from vectcut.server.http.app import (
    _TemplateImportBodyLimitMiddleware,
    _wire_exception_handlers,
    envelope_err,
    envelope_ok,
)
from vectcut.core.errors import InvalidParam, DraftNotFound

http_app_module = importlib.import_module("vectcut.server.http.app")


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
    assert body["output"] is None
    assert body["error"]["code"] == "INVALID_PARAM"
    assert "bad param" in body["error"]["message"]
    assert body["error"]["details"] == {}


def test_draft_not_found_handler_returns_200_envelope():
    client = _bare_client()
    resp = client.post("/raise_not_found")
    assert resp.status_code == 200
    assert resp.json()["success"] is False
    assert resp.json()["error"]["code"] == "DRAFT_NOT_FOUND"
    assert "dfd_x" in resp.json()["error"]["message"]


def test_unexpected_exception_handler_returns_200_envelope():
    client = _bare_client()
    resp = client.post("/raise_value_error")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INTERNAL_ERROR"
    assert body["error"]["message"] == "服务器内部错误"
    assert body["error"]["details"] == {}
    assert "plain" not in str(body["error"])


def test_unexpected_exception_handler_logs_sanitized_error_without_raw_traceback(caplog):
    sub = FastAPI()
    secret_message = (
        "boom token=SECRET_TOKEN_123456 "
        "/home/alice/private/file.mp4 "
        "https://cdn.example.com/token/SECRET_URL_PATH/video.mp4 "
        "https://cdn.example.com/video.mp4?credential=SECRET_QUERY"
    )

    @sub.post("/raise_sensitive")
    def _raise_sensitive():
        raise RuntimeError(secret_message)

    _wire_exception_handlers(sub)
    client = TestClient(sub, raise_server_exceptions=False)

    with caplog.at_level(logging.ERROR, logger="vectcut.server.http"):
        resp = client.post("/raise_sensitive")

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INTERNAL_ERROR"

    logs = caplog.text
    assert "Unhandled HTTP error:" in logs
    assert "token=***" in logs
    assert "***" in logs
    assert "SECRET_TOKEN_123456" not in logs
    assert "SECRET_URL_PATH" not in logs
    assert "SECRET_QUERY" not in logs
    assert "/home/alice/private/file.mp4" not in logs
    assert "/home/alice/private" not in logs


def test_unexpected_exception_handler_survives_sanitizer_placeholder_collision():
    sub = FastAPI()

    @sub.post("/raise_placeholder_collision")
    def _raise_placeholder_collision():
        raise RuntimeError("__VECTCUT_URL_0__ __VECTCUT_PATH_0__")

    _wire_exception_handlers(sub)
    client = TestClient(sub, raise_server_exceptions=False)

    resp = client.post("/raise_placeholder_collision")

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INTERNAL_ERROR"
    assert body["error"]["message"] == "服务器内部错误"
    assert body["error"]["details"] == {}


def test_validation_error_handler_returns_200_envelope():
    """RequestValidationError 由 FastAPI Pydantic 校验触发，返回结构化 200 外壳。"""
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
    assert body["error"]["code"] == "INVALID_PARAM"
    assert body["error"]["message"] == "参数校验失败"
    assert body["error"]["details"]["errors"]


def test_template_import_body_limit_streams_without_prebuffering(monkeypatch):
    """无 Content-Length 超限时应通过 receive wrapper 流式计数，而不是先预读缓存。"""
    monkeypatch.setattr(
        http_app_module,
        "load_config",
        lambda: SimpleNamespace(max_template_zip_mb=0),
        raising=False,
    )
    app_entered = False
    receive_count = 0
    sent_messages = []
    chunks = [b"a", b"b" * (1024 * 1024), b"c"]

    async def _downstream_app(scope, receive, send):
        nonlocal app_entered
        app_entered = True
        while True:
            message = await receive()
            if message["type"] != "http.request" or not message.get("more_body", False):
                break
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b'{"ok":true}'})

    middleware = _TemplateImportBodyLimitMiddleware(_downstream_app)
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/template/import",
        "raw_path": b"/api/template/import",
        "query_string": b"template_id=t1",
        "headers": [(b"content-type", b"multipart/form-data; boundary=x")],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }

    async def _receive():
        nonlocal receive_count
        receive_count += 1
        if chunks:
            return {
                "type": "http.request",
                "body": chunks.pop(0),
                "more_body": bool(chunks),
            }
        return {"type": "http.request", "body": b"", "more_body": False}

    async def _send(message):
        sent_messages.append(message)

    asyncio.run(middleware(scope, _receive, _send))

    body = b"".join(
        m.get("body", b"") for m in sent_messages if m["type"] == "http.response.body"
    )
    data = json.loads(body.decode("utf-8"))
    assert app_entered is True
    assert receive_count == 2
    assert chunks == [b"c"]
    assert data["success"] is False
    assert data["error"]["code"] == "T_TOO_LARGE"

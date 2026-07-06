"""FastAPI app + 全局异常 handler。

保真约束：所有路由响应体恒为 200 + {success, output, error}（与现有 Flask
flask_router.py 外壳逐字一致，黄金测试 assert status_code==200 是硬约束）。
规格 §4.4 的语义状态码（422/404）列为本阶段非目标。

注意：本文件不 import 任何 feature router（避免循环依赖）。
router 挂载由 vectcut/server/http/__init__.py 在 app 创建后执行。
_wire_exception_handlers 保留在此处，供 feature router 测试 import。
"""
from __future__ import annotations

from datetime import datetime
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from vectcut import __version__
from vectcut.core.config import load_config
from vectcut.core.errors import VectCutError
from vectcut.core.logger import sanitize_exception
from vectcut.server._helpers import envelope_err, envelope_ok  # noqa: F401

_MULTIPART_OVERHEAD_BYTES = 1024 * 1024
_logger = logging.getLogger("vectcut.server.http")


class _BodyLimitExceeded(Exception):
    def __init__(self, received_bytes: int):
        super().__init__("template import request body too large")
        self.received_bytes = received_bytes


def _too_large_payload(
    *,
    max_bytes: int,
    max_content_length: int,
    max_template_zip_mb: int,
    content_length: int | None = None,
    received_bytes: int | None = None,
) -> dict:
    details = {
        "max_bytes": max_bytes,
        "max_content_length": max_content_length,
        "max_template_zip_mb": max_template_zip_mb,
    }
    if content_length is not None:
        details["content_length"] = content_length
    if received_bytes is not None:
        details["received_bytes"] = received_bytes
    return envelope_err(
        {
            "code": "T_TOO_LARGE",
            "message": "模板 ZIP 超过大小限制",
            "details": details,
        }
    )


class _TemplateImportBodyLimitMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if (
            scope.get("type") != "http"
            or scope.get("method") != "POST"
            or scope.get("path") != "/api/template/import"
        ):
            await self.app(scope, receive, send)
            return

        cfg = load_config()
        max_bytes = int(cfg.max_template_zip_mb) * 1024 * 1024
        max_content_length = max_bytes + _MULTIPART_OVERHEAD_BYTES
        headers = {
            key.lower(): value
            for key, value in scope.get("headers", [])
        }
        raw_content_length = headers.get(b"content-length")
        if raw_content_length:
            try:
                content_length = int(raw_content_length.decode("latin1"))
            except ValueError:
                content_length = None
            if content_length is not None and content_length > max_content_length:
                response = JSONResponse(
                    status_code=200,
                    content=_too_large_payload(
                        content_length=content_length,
                        max_bytes=max_bytes,
                        max_content_length=max_content_length,
                        max_template_zip_mb=cfg.max_template_zip_mb,
                    ),
                )
                await response(scope, receive, send)
                return

        received_bytes = 0
        request_complete = False
        response_messages = []

        async def _limited_receive():
            nonlocal received_bytes, request_complete
            message = await receive()
            if message.get("type") != "http.request":
                return message
            received_bytes += len(message.get("body", b""))
            request_complete = not message.get("more_body", False)
            if received_bytes > max_content_length:
                raise _BodyLimitExceeded(received_bytes)
            return message

        async def _buffering_send(message):
            response_messages.append(message)

        async def _send_too_large(received: int):
            response = JSONResponse(
                status_code=200,
                content=_too_large_payload(
                    received_bytes=received,
                    max_bytes=max_bytes,
                    max_content_length=max_content_length,
                    max_template_zip_mb=cfg.max_template_zip_mb,
                ),
            )
            await response(scope, receive, send)

        try:
            await self.app(scope, _limited_receive, _buffering_send)
        except _BodyLimitExceeded as exc:
            await _send_too_large(exc.received_bytes)
            return

        try:
            while not request_complete:
                message = await _limited_receive()
                if message.get("type") != "http.request":
                    break
        except _BodyLimitExceeded as exc:
            await _send_too_large(exc.received_bytes)
            return

        for message in response_messages:
            await send(message)


def _wire_exception_handlers(app: FastAPI) -> FastAPI:
    """把 VectCutError / ValidationError / 兜底异常统一转成 200 外壳。

    抽成函数以便测试在独立 sub-app 上复用同一套 handler。
    返回 app 以便链式调用。
    """

    app.add_middleware(_TemplateImportBodyLimitMiddleware)

    @app.exception_handler(VectCutError)
    async def _vectcut_error_handler(_req: Request, exc: VectCutError):
        return JSONResponse(status_code=200, content=envelope_err(exc))

    @app.exception_handler(RequestValidationError)
    async def _validation_error_handler(_req: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=200,
            content=envelope_err(
                {
                    "code": "INVALID_PARAM",
                    "message": "参数校验失败",
                    "details": {"errors": exc.errors()},
                }
            ),
        )

    @app.exception_handler(Exception)
    async def _unexpected_error_handler(_req: Request, exc: Exception):
        _logger.error("Unhandled HTTP error: %s", sanitize_exception(exc))
        return JSONResponse(
            status_code=200,
            content=envelope_err(
                {
                    "code": "INTERNAL_ERROR",
                    "message": "服务器内部错误",
                    "details": {},
                }
            ),
        )

    return app


app = _wire_exception_handlers(FastAPI(title="VectCutAPI"))


@app.get("/api/health")
@app.get("/health")
async def health_check():
    """健康检查端点（供 Docker HEALTHCHECK 与 Nginx 探活）。

    返回 200 + {status, timestamp, version}。
    不走统一信封，方便 Docker/Nginx 直接判断状态码。
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": __version__,
    }

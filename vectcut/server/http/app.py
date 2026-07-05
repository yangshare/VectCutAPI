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

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from vectcut import __version__
from vectcut.core.errors import VectCutError
from vectcut.server._helpers import envelope_err, envelope_ok  # noqa: F401


def _wire_exception_handlers(app: FastAPI) -> FastAPI:
    """把 VectCutError / ValidationError / 兜底异常统一转成 200 外壳。

    抽成函数以便测试在独立 sub-app 上复用同一套 handler。
    返回 app 以便链式调用。
    """

    @app.exception_handler(VectCutError)
    async def _vectcut_error_handler(_req: Request, exc: VectCutError):
        return JSONResponse(status_code=200, content=envelope_err(str(exc)))

    @app.exception_handler(RequestValidationError)
    async def _validation_error_handler(_req: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=200,
            content=envelope_err(f"Hi, the required parameters are missing. {exc}"),
        )

    @app.exception_handler(Exception)
    async def _unexpected_error_handler(_req: Request, exc: Exception):
        return JSONResponse(status_code=200, content=envelope_err(str(exc)))

    return app


app = _wire_exception_handlers(FastAPI(title="VectCutAPI"))


@app.get("/api/health")
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

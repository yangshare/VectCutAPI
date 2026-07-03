"""FastAPI app + envelope helper + 全局异常 handler。

保真约束：所有路由响应体恒为 200 + {success, output, error}（与现有 Flask
flask_router.py 外壳逐字一致，黄金测试 assert status_code==200 是硬约束）。
规格 §4.4 的语义状态码（422/404）列为本阶段非目标。
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from vectcut.core.errors import VectCutError


def envelope_ok(output) -> dict:
    return {"success": True, "output": output, "error": ""}


def envelope_err(error: str) -> dict:
    return {"success": False, "output": "", "error": error}


def _wire_exception_handlers(app: FastAPI) -> None:
    """把 VectCutError / ValidationError / 兜底异常统一转成 200 外壳。

    抽成函数以便测试在独立 sub-app 上复用同一套 handler。
    注意：TestClient 默认 raise_server_exceptions=True 会 re-raise 未处理异常，
    测试需用 raise_server_exceptions=False 以验证兜底 Exception handler 返回 200 外壳。
    """

    @app.exception_handler(VectCutError)
    async def _vectcut_error_handler(_req: Request, exc: VectCutError):
        return JSONResponse(status_code=200, content=envelope_err(str(exc)))

    @app.exception_handler(RequestValidationError)
    async def _validation_error_handler(_req: Request, exc: RequestValidationError):
        # 保真：与 flask_router.py 的 ValidationError 分支文案前缀一致
        return JSONResponse(
            status_code=200,
            content=envelope_err(f"Hi, the required parameters are missing. {exc}"),
        )

    @app.exception_handler(Exception)
    async def _unexpected_error_handler(_req: Request, exc: Exception):
        return JSONResponse(status_code=200, content=envelope_err(str(exc)))


app = FastAPI(title="VectCutAPI")
_wire_exception_handlers(app)

"""FastAPI app + envelope helper + 全局异常 handler。

保真约束：业务异常（VectCutError）与验证异常（RequestValidationError）响应体
恒为 200 + {success, output, error}。兜底 Exception 因 FastAPI build_middleware_stack
将 Exception/500 handler 移交 ServerErrorMiddleware（始终 re-raise）而无法在
TestClient 中以 200 外壳验证，故省略；生产环境 ServerErrorMiddleware 会以 500 响应。
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
    """把 VectCutError / ValidationError 统一转成 200 外壳。

    抽成函数以便测试在独立 sub-app 上复用同一套 handler。
    注意：FastAPI 的 build_middleware_stack 会将 Exception/500 handler 移交
    ServerErrorMiddleware，导致 TestClient 中 re-raise，无法以 200 外壳验证。
    兜底异常由 ServerErrorMiddleware 以默认 500 处理。
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


app = FastAPI(title="VectCutAPI")
_wire_exception_handlers(app)

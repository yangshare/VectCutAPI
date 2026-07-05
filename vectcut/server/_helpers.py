"""HTTP 层共享辅助函数（envelope）。

放此目录以打破 app.py ↔ feature router 之间的循环 import：
  router.py → import _helpers（不经过 vectcut.server.http 包）
  app.py    → 不再被 router 导入
"""
from __future__ import annotations

from vectcut.core.errors import VectCutError


def envelope_ok(output) -> dict:
    return {"success": True, "output": output, "error": ""}


def envelope_err(error: str | dict | VectCutError) -> dict:
    if isinstance(error, VectCutError):
        return {
            "success": False,
            "output": None,
            "error": {
                "code": error.code,
                "message": str(error),
                "details": getattr(error, "details", {}) or {},
            },
        }
    if isinstance(error, dict):
        return {"success": False, "output": None, "error": error}
    return {"success": False, "output": "", "error": error}

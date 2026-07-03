"""统一业务异常基类 + 错误码。

阶段 1 只需 InvalidParam（metadata service 用）。DraftNotFound / EngineError /
MediaDownloadError 在阶段 2-4 引入对应 feature 时按需添加（YAGNI）。
错误码与 HTTP/JSON-RPC 映射见规格 §4.4 表。
"""

from __future__ import annotations


class VectCutError(Exception):
    """业务异常基类。子类声明 code（字符串错误码）与 http_status。"""

    code: str = "VECTCUT_ERROR"
    http_status: int = 500


class InvalidParam(VectCutError):
    """参数非法（未知 kind、end<=start 等）。HTTP 422 / JSON-RPC -32002。"""

    code = "INVALID_PARAM"
    http_status = 422
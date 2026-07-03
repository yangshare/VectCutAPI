"""text feature FastAPI router：/add_text + /add_subtitle。

保真：响应体与 flask_router.py 逐字一致（含 ValidationError 自定义前缀）。
使用 model_validate() 手动校验，AddTextRequest 的 model_validator(mode="before)
别名归一化在 model_validate() 内自动执行。
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import ValidationError

from vectcut.core.errors import VectCutError
from vectcut.features.text import service
from vectcut.features.text.schemas import AddSubtitleRequest, AddTextRequest
from vectcut.server._helpers import envelope_ok, envelope_err

router = APIRouter()


@router.post("/add_text")
def add_text(body: dict):
    try:
        req = AddTextRequest.model_validate(body)
    except ValidationError as e:
        # 保真：capcut_server.py:228 错误消息(含尾随空格)
        return envelope_err(
            f"Hi, the required parameters 'text', 'start' or 'end' are missing. {e}"
        )
    try:
        resp = service.add_text(req)
        return envelope_ok({"draft_id": resp.draft_id, "draft_url": resp.draft_url})
    except VectCutError as e:
        return envelope_err(
            f"Error occurred while processing text: {e}. You can click "
            f"the link below for help: "
        )


@router.post("/add_subtitle")
def add_subtitle(body: dict):
    try:
        req = AddSubtitleRequest.model_validate(body)
    except ValidationError as e:
        # 保真：capcut_server.py:69 错误消息
        return envelope_err(f"Hi, the required parameters 'srt' are missing. {e}")
    try:
        resp = service.add_subtitle(req)
        return envelope_ok({"draft_id": resp.draft_id, "draft_url": resp.draft_url})
    except VectCutError as e:
        return envelope_err(f"Error occurred while processing subtitle: {e}.")

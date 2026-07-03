"""effect feature FastAPI router：/add_effect + /add_sticker。

保真：响应体与 flask_router.py 逐字一致（VectCutError 文案末尾含一个空格）。
使用 model_validate() 手动校验。
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import ValidationError

from vectcut.core.errors import VectCutError
from vectcut.features.effect import service
from vectcut.features.effect.schemas import AddEffectRequest, AddStickerRequest
from vectcut.server._helpers import envelope_ok, envelope_err

router = APIRouter()


@router.post("/add_effect")
def add_effect(body: dict):
    try:
        req = AddEffectRequest.model_validate(body)
    except ValidationError as e:
        return envelope_err(f"Hi, the required parameters are missing. {e}")
    try:
        resp = service.add_effect(req)
        return envelope_ok({"draft_id": resp.draft_id, "draft_url": resp.draft_url})
    except VectCutError as e:
        # 保真：capcut_server.py:481 error_message 末尾含一个空格
        return envelope_err(f"Error occurred while adding effect: {e}. ")


@router.post("/add_sticker")
def add_sticker(body: dict):
    try:
        req = AddStickerRequest.model_validate(body)
    except ValidationError as e:
        return envelope_err(f"Hi, the required parameters are missing. {e}")
    try:
        resp = service.add_sticker(req)
        return envelope_ok({"draft_id": resp.draft_id, "draft_url": resp.draft_url})
    except VectCutError as e:
        # 保真：capcut_server.py:544 error_message 末尾含一个空格
        return envelope_err(f"Error occurred while adding sticker: {e}. ")

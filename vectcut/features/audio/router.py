"""audio feature FastAPI router：/add_audio。

保真：响应体与 flask_router.py 逐字一致。
使用 model_validate() 手动校验。
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import ValidationError

from vectcut.core.errors import VectCutError
from vectcut.features.audio import service
from vectcut.features.audio.schemas import AddAudioRequest
from vectcut.server._helpers import envelope_ok, envelope_err

router = APIRouter()


@router.post("/add_audio")
def add_audio(body: dict):
    try:
        req = AddAudioRequest.model_validate(body)
    except ValidationError as e:
        return envelope_err(f"Hi, the required parameters are missing. {e}")
    try:
        resp = service.add_audio(req)
        return envelope_ok({"draft_id": resp.draft_id, "draft_url": resp.draft_url})
    except VectCutError as e:
        return envelope_err(f"Error occurred while processing audio: {e}.")

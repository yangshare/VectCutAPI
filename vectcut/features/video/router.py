"""video feature FastAPI router：/add_video + /add_video_keyframe。

保真：响应体与 flask_router.py 逐字一致。
使用 model_validate() 手动校验，与 Flask 版异常路径文案对齐。
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import ValidationError

from vectcut.core.errors import VectCutError
from vectcut.features.video import service
from vectcut.features.video.schemas import AddVideoKeyframeRequest, AddVideoRequest
from vectcut.server._helpers import envelope_ok, envelope_err

router = APIRouter()


@router.post("/add_video")
def add_video(body: dict):
    try:
        req = AddVideoRequest.model_validate(body)
    except ValidationError as e:
        return envelope_err(f"Hi, the required parameters are missing. {e}")
    try:
        resp = service.add_video(req)
        return envelope_ok({"draft_id": resp.draft_id, "draft_url": resp.draft_url})
    except VectCutError as e:
        return envelope_err(f"Error occurred while processing video: {e}.")


@router.post("/add_video_keyframe")
def add_video_keyframe(body: dict):
    try:
        req = AddVideoKeyframeRequest.model_validate(body)
    except ValidationError as e:
        return envelope_err(f"Hi, the required parameters are missing. {e}")
    try:
        resp = service.add_video_keyframe(req)
        return envelope_ok({"draft_id": resp.draft_id, "draft_url": resp.draft_url})
    except VectCutError as e:
        return envelope_err(f"Error occurred while adding keyframe: {e}.")

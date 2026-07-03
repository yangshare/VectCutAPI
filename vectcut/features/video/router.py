"""video feature FastAPI router：/add_video + /add_video_keyframe。

保真：响应体与 flask_router.py 逐字一致。
Pydantic 自动校验替代手写 data.get()；缺字段由全局 RequestValidationError
handler 转 200 外壳（文案前缀与 Flask 版一致）。
"""
from __future__ import annotations

from fastapi import APIRouter

from vectcut.features.video import service
from vectcut.features.video.schemas import AddVideoKeyframeRequest, AddVideoRequest
from vectcut.server.http.app import envelope_ok

router = APIRouter()


@router.post("/add_video")
def add_video(req: AddVideoRequest):
    resp = service.add_video(req)
    return envelope_ok({"draft_id": resp.draft_id, "draft_url": resp.draft_url})


@router.post("/add_video_keyframe")
def add_video_keyframe(req: AddVideoKeyframeRequest):
    resp = service.add_video_keyframe(req)
    return envelope_ok({"draft_id": resp.draft_id, "draft_url": resp.draft_url})

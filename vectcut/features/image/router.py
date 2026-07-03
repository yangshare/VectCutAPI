"""image feature FastAPI router：/add_image。"""
from __future__ import annotations

from fastapi import APIRouter

from vectcut.features.image import service
from vectcut.features.image.schemas import AddImageRequest
from vectcut.server.http.app import envelope_ok

router = APIRouter()


@router.post("/add_image")
def add_image(req: AddImageRequest):
    resp = service.add_image(req)
    return envelope_ok({"draft_id": resp.draft_id, "draft_url": resp.draft_url})

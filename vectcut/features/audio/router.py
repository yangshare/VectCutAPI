"""audio feature FastAPI router：/add_audio。"""
from __future__ import annotations

from fastapi import APIRouter

from vectcut.features.audio import service
from vectcut.features.audio.schemas import AddAudioRequest
from vectcut.server.http.app import envelope_ok

router = APIRouter()


@router.post("/add_audio")
def add_audio(req: AddAudioRequest):
    resp = service.add_audio(req)
    return envelope_ok({"draft_id": resp.draft_id, "draft_url": resp.draft_url})

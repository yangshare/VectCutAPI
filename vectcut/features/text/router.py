"""text feature FastAPI router：/add_text + /add_subtitle。"""
from __future__ import annotations

from fastapi import APIRouter

from vectcut.features.text import service
from vectcut.features.text.schemas import AddSubtitleRequest, AddTextRequest
from vectcut.server.http.app import envelope_ok

router = APIRouter()


@router.post("/add_text")
def add_text(req: AddTextRequest):
    resp = service.add_text(req)
    return envelope_ok({"draft_id": resp.draft_id, "draft_url": resp.draft_url})


@router.post("/add_subtitle")
def add_subtitle(req: AddSubtitleRequest):
    resp = service.add_subtitle(req)
    return envelope_ok({"draft_id": resp.draft_id, "draft_url": resp.draft_url})

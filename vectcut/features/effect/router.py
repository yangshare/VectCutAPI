"""effect feature FastAPI router：/add_effect + /add_sticker。"""
from __future__ import annotations

from fastapi import APIRouter

from vectcut.features.effect import service
from vectcut.features.effect.schemas import AddEffectRequest, AddStickerRequest
from vectcut.server.http.app import envelope_ok

router = APIRouter()


@router.post("/add_effect")
def add_effect(req: AddEffectRequest):
    resp = service.add_effect(req)
    return envelope_ok({"draft_id": resp.draft_id, "draft_url": resp.draft_url})


@router.post("/add_sticker")
def add_sticker(req: AddStickerRequest):
    resp = service.add_sticker(req)
    return envelope_ok({"draft_id": resp.draft_id, "draft_url": resp.draft_url})

"""draft feature FastAPI router：5 路由薄接线。

保真：响应体与 flask_router.py 逐字一致（200 + {success,output,error}）。
异常由全局 handler 兜底，本文件只调 service。
"""
from __future__ import annotations

from fastapi import APIRouter

from vectcut.features.draft import service
from vectcut.features.draft.schemas import (
    CreateDraftRequest,
    GenerateDraftUrlRequest,
    QueryDraftStatusRequest,
    QueryScriptRequest,
    SaveDraftRequest,
)
from vectcut.server.http.app import envelope_ok

router = APIRouter()


@router.post("/create_draft")
def create_draft(req: CreateDraftRequest):
    resp = service.create_draft(req)
    return envelope_ok({"draft_id": resp.draft_id, "draft_url": resp.draft_url})


@router.post("/save_draft")
def save_draft(req: SaveDraftRequest):
    resp = service.save_draft(req)
    return envelope_ok({"draft_url": resp.draft_url} if resp.draft_url else {})


@router.post("/query_script")
def query_script(req: QueryScriptRequest):
    resp = service.query_script(req)
    return envelope_ok(resp.output)


@router.post("/query_draft_status")
def query_draft_status(req: QueryDraftStatusRequest):
    resp = service.query_task_status(req)
    return envelope_ok(resp.output)


@router.post("/generate_draft_url")
def generate_draft_url(req: GenerateDraftUrlRequest):
    url = service.generate_draft_url(req.draft_id)
    return envelope_ok({"draft_url": url})

"""draft feature FastAPI router：5 路由薄接线。

保真：响应体与 flask_router.py 逐字一致（200 + {success,output,error}）。
使用 model_validate() 手动校验，与 Flask 版 model_validate() 异常路径文案对齐。
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import ValidationError

from vectcut.features.draft import service
from vectcut.features.draft.schemas import (
    AddCoverRequest,
    CreateDraftRequest,
    GenerateDraftUrlRequest,
    QueryDraftStatusRequest,
    QueryScriptRequest,
    SaveDraftRequest,
)
from vectcut.server._helpers import envelope_ok, envelope_err

router = APIRouter()


@router.post("/create_draft")
def create_draft(body: dict):
    try:
        req = CreateDraftRequest.model_validate(body)
    except ValidationError as e:
        return envelope_err(str(e))
    resp = service.create_draft(req)
    return envelope_ok({"draft_id": resp.draft_id, "draft_url": resp.draft_url})


@router.post("/save_draft")
def save_draft(body: dict):
    try:
        req = SaveDraftRequest.model_validate(body)
    except ValidationError as e:
        return envelope_err(f"Error occurred while saving draft: {e}. ")
    resp = service.save_draft(req)
    return envelope_ok({"draft_url": resp.draft_url} if resp.draft_url else {})


@router.post("/query_script")
def query_script(body: dict):
    try:
        req = QueryScriptRequest.model_validate(body)
    except ValidationError as e:
        return envelope_err(f"Error occurred while querying script: {e}")
    resp = service.query_script(req)
    return envelope_ok(resp.output)


@router.post("/query_draft_status")
def query_draft_status(body: dict):
    try:
        req = QueryDraftStatusRequest.model_validate(body)
    except ValidationError as e:
        return envelope_err(f"Error occurred while querying task status: {e}")
    resp = service.query_task_status(req)
    return envelope_ok(resp.output)


@router.post("/generate_draft_url")
def generate_draft_url(body: dict):
    try:
        req = GenerateDraftUrlRequest.model_validate(body)
    except ValidationError as e:
        return envelope_err(f"Error occurred while generating draft url: {e}")
    url = service.generate_draft_url(req.draft_id)
    return envelope_ok({"draft_url": url})


@router.post("/add_cover")
def add_cover(body: dict):
    try:
        req = AddCoverRequest.model_validate(body)
    except ValidationError as e:
        return envelope_err(f"Hi, the required parameters are missing. {e}")
    resp = service.add_cover(req)
    return envelope_ok({"draft_id": resp.draft_id, "draft_url": resp.draft_url})

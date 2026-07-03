"""draft feature Flask Blueprint：5 路由薄接线，统一 {success,output,error} 外壳。

阶段 4 迁 FastAPI 时，同一 service 接到 FastAPI router，本文件替换。
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from vectcut.core.errors import VectCutError
from vectcut.features.draft import service
from vectcut.features.draft.schemas import (
    CreateDraftRequest,
    GenerateDraftUrlRequest,
    QueryDraftStatusRequest,
    QueryScriptRequest,
    SaveDraftRequest,
)

bp = Blueprint("draft", __name__)


def _ok(output):
    return jsonify({"success": True, "output": output, "error": ""})


def _err(e: VectCutError):
    return jsonify({"success": False, "output": "", "error": str(e)})


@bp.post("/create_draft")
def create_draft():
    try:
        req = CreateDraftRequest.model_validate(request.get_json() or {})
        resp = service.create_draft(req)
        return _ok({"draft_id": resp.draft_id, "draft_url": resp.draft_url})
    except VectCutError as e:
        return _err(e)


@bp.post("/save_draft")
def save_draft():
    try:
        req = SaveDraftRequest.model_validate(request.get_json() or {})
        resp = service.save_draft(req)
        return _ok({"draft_url": resp.draft_url} if resp.draft_url else {})
    except VectCutError as e:
        return _err(e)
    except Exception as e:
        return jsonify({"success": False, "output": "", "error": f"Error occurred while saving draft: {e}. "})


@bp.post("/query_script")
def query_script():
    try:
        req = QueryScriptRequest.model_validate(request.get_json() or {})
        resp = service.query_script(req)
        return _ok(resp.output)
    except VectCutError as e:
        return _err(e)


@bp.post("/query_draft_status")
def query_draft_status():
    try:
        req = QueryDraftStatusRequest.model_validate(request.get_json() or {})
        resp = service.query_task_status(req)
        return _ok(resp.output)
    except VectCutError as e:
        return _err(e)
    except Exception as e:
        return jsonify({"success": False, "output": "", "error": f"Error occurred while querying task status: {e}."})


@bp.post("/generate_draft_url")
def generate_draft_url():
    try:
        req = GenerateDraftUrlRequest.model_validate(request.get_json() or {})
        url = service.generate_draft_url(req.draft_id)
        return _ok({"draft_url": url})
    except VectCutError as e:
        return _err(e)
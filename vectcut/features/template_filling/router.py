"""template_filling FastAPI 路由层。

4 个端点（统一 /api/template 前缀）：
  POST /api/template/import            导入母版 ZIP（legacy）
  POST /api/template/import-draft-content 导入单个 draft_content.json
  POST /api/template/slot-config       保存槽位配置
  POST /api/template/render            渲染草稿
  GET  /api/template/download/{draft_id}  下载草稿 ZIP

与 service.download_draft 返回的 download_url=/api/template/download/{draft_id}
保持一致（service 的 download_url 与本 router 的实际路径对齐）。
"""
from __future__ import annotations

import os
import tempfile

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import ValidationError

from vectcut.core.config import load_config
from vectcut.core.errors import VectCutError
from vectcut.core.errors import make_error
from vectcut.features.template_filling import service, storage
from vectcut.features.template_filling.schemas import (
    RenderDraftRequest,
    SaveSlotConfigRequest,
)
from vectcut.server._helpers import envelope_err, envelope_ok

router = APIRouter(prefix="/api/template", tags=["template-filling"])

_UPLOAD_CHUNK_SIZE = 1024 * 1024
_MULTIPART_OVERHEAD_BYTES = 1024 * 1024


def _get_content_length(request: Request | None) -> int | None:
    if request is None:
        return None
    raw = request.headers.get("content-length") or request.headers.get("Content-Length")
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


@router.post("/import")
async def import_template(
    request: Request,
    template_id: str,
    file: UploadFile = File(...),
):
    """导入母版 ZIP。template_id 为 query 参数，file 为上传的 zip。"""
    # 校验文件名
    if not file.filename or not file.filename.lower().endswith(".zip"):
        return envelope_err(make_error("T_INVALID_ZIP"))

    cfg = load_config()
    max_bytes = int(cfg.max_template_zip_mb) * 1024 * 1024
    content_length = _get_content_length(request)
    content_length_limit = max_bytes + _MULTIPART_OVERHEAD_BYTES
    if content_length is not None and content_length > content_length_limit:
        return envelope_err(
            make_error(
                "T_TOO_LARGE",
                details={
                    "content_length": content_length,
                    "max_bytes": max_bytes,
                    "max_content_length": content_length_limit,
                    "max_template_zip_mb": cfg.max_template_zip_mb,
                },
            )
        )

    temp_dir = getattr(cfg, "temp_folder", "") or None
    if temp_dir:
        os.makedirs(temp_dir, exist_ok=True)

    tmp_path = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".zip", dir=temp_dir) as tmp:
            tmp_path = tmp.name
            bytes_written = 0
            while True:
                chunk = await file.read(_UPLOAD_CHUNK_SIZE)
                if not chunk:
                    break
                bytes_written += len(chunk)
                if bytes_written > max_bytes:
                    return envelope_err(
                        make_error(
                            "T_TOO_LARGE",
                            details={
                                "max_template_zip_mb": cfg.max_template_zip_mb,
                            },
                        )
                    )
                tmp.write(chunk)

        resp = service.import_template(template_id, tmp_path)
        return envelope_ok(resp.model_dump())
    except VectCutError as e:
        return envelope_err(e)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


@router.post("/import-draft-content")
async def import_draft_content(
    request: Request,
    template_id: str,
    file: UploadFile = File(...),
):
    """导入单个 draft_content.json。template_id 为 query 参数。"""
    if not file.filename or file.filename.lower() != "draft_content.json":
        return envelope_err(make_error("T_INVALID_DRAFT_CONTENT"))

    cfg = load_config()
    max_mb = int(getattr(cfg, "max_draft_content_mb", 20))
    max_bytes = max_mb * 1024 * 1024
    content_length = _get_content_length(request)
    content_length_limit = max_bytes + _MULTIPART_OVERHEAD_BYTES
    if content_length is not None and content_length > content_length_limit:
        return envelope_err(
            make_error(
                "T_DRAFT_CONTENT_TOO_LARGE",
                details={
                    "content_length": content_length,
                    "max_bytes": max_bytes,
                    "max_content_length": content_length_limit,
                    "max_draft_content_mb": max_mb,
                },
            )
        )

    try:
        chunks: list[bytes] = []
        bytes_read = 0
        while True:
            chunk = await file.read(_UPLOAD_CHUNK_SIZE)
            if not chunk:
                break
            bytes_read += len(chunk)
            if bytes_read > max_bytes:
                return envelope_err(
                    make_error(
                        "T_DRAFT_CONTENT_TOO_LARGE",
                        details={"max_draft_content_mb": max_mb},
                    )
                )
            chunks.append(chunk)

        resp = service.import_draft_content(template_id, b"".join(chunks))
        return envelope_ok(resp.model_dump())
    except VectCutError as e:
        return envelope_err(e)


@router.post("/slot-config")
def save_slot_config(body: dict):
    """保存槽位配置。body 为 SaveSlotConfigRequest。"""
    try:
        req = SaveSlotConfigRequest.model_validate(body)
    except ValidationError as e:
        return envelope_err(
            make_error(
                "S_INVALID_SLOT",
                "参数校验失败",
                details={"validation_error": str(e)},
            )
        )
    try:
        resp = service.save_slot_config(req.template_id, req)
        return envelope_ok(resp.model_dump())
    except VectCutError as e:
        return envelope_err(e)


@router.post("/render")
def render_draft(body: dict):
    """渲染草稿。body 为 RenderDraftRequest。"""
    try:
        req = RenderDraftRequest.model_validate(body)
    except ValidationError as e:
        return envelope_err(
            make_error(
                "R_INVALID_TASK",
                "参数校验失败",
                details={"validation_error": str(e)},
            )
        )
    try:
        resp = service.render_draft(req.template_id, req)
        return envelope_ok(resp.model_dump())
    except VectCutError as e:
        return envelope_err(e)


@router.get("/download/{draft_id}")
def download_draft(draft_id: str):
    """下载草稿 ZIP，返回 FileResponse。

    service.download_draft 已做存在性校验并返回 DownloadDraftResponse；
    此处再查一次 storage 拿到物理 zip 路径用于 FileResponse。
    """
    try:
        service.download_draft(draft_id)
        zip_path = storage.get_generated_draft_zip_path(draft_id)
        if not zip_path:
            return envelope_err(
                make_error("R_TASK_NOT_FOUND", details={"draft_id": draft_id})
            )
        return FileResponse(
            path=zip_path,
            media_type="application/zip",
            filename=f"{draft_id}.zip",
        )
    except VectCutError as e:
        return envelope_err(e)

"""template_filling FastAPI 路由层。

4 个端点（统一 /api/template 前缀）：
  POST /api/template/import            导入母版 ZIP
  POST /api/template/slot-config       保存槽位配置
  POST /api/template/render            渲染草稿
  GET  /api/template/download/{draft_id}  下载草稿 ZIP

与 service.download_draft 返回的 download_url=/api/template/download/{draft_id}
保持一致（service 的 download_url 与本 router 的实际路径对齐）。
"""
from __future__ import annotations

import os
import tempfile

from fastapi import APIRouter, File, UploadFile
from fastapi.responses import FileResponse
from pydantic import ValidationError

from vectcut.core.errors import VectCutError
from vectcut.features.template_filling import service, storage
from vectcut.features.template_filling.schemas import (
    RenderDraftRequest,
    SaveSlotConfigRequest,
)
from vectcut.server._helpers import envelope_err, envelope_ok

router = APIRouter(prefix="/api/template", tags=["template-filling"])


@router.post("/import")
async def import_template(template_id: str, file: UploadFile = File(...)):
    """导入母版 ZIP。template_id 为 query 参数，file 为上传的 zip。"""
    # 校验文件名
    if not file.filename or not file.filename.lower().endswith(".zip"):
        return envelope_err("仅支持 .zip 文件")
    # 保存到临时文件
    content = await file.read()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        resp = service.import_template(template_id, tmp_path)
        return envelope_ok(resp.model_dump())
    except VectCutError as e:
        return envelope_err(str(e))
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@router.post("/slot-config")
def save_slot_config(body: dict):
    """保存槽位配置。body 为 SaveSlotConfigRequest。"""
    try:
        req = SaveSlotConfigRequest.model_validate(body)
    except ValidationError as e:
        return envelope_err(f"参数校验失败: {e}")
    try:
        resp = service.save_slot_config(req.template_id, req)
        return envelope_ok(resp.model_dump())
    except VectCutError as e:
        return envelope_err(str(e))


@router.post("/render")
def render_draft(body: dict):
    """渲染草稿。body 为 RenderDraftRequest。"""
    try:
        req = RenderDraftRequest.model_validate(body)
    except ValidationError as e:
        return envelope_err(f"参数校验失败: {e}")
    try:
        resp = service.render_draft(req.template_id, req)
        return envelope_ok(resp.model_dump())
    except VectCutError as e:
        return envelope_err(str(e))


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
            return envelope_err(f"草稿 {draft_id} 文件不存在")
        return FileResponse(
            path=zip_path,
            media_type="application/zip",
            filename=f"{draft_id}.zip",
        )
    except VectCutError as e:
        return envelope_err(str(e))

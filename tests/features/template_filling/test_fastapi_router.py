"""template_filling HTTP 契约测试：TestClient 驱动 4 个端点。

策略：mock service 层（import_template / save_slot_config / render_draft /
download_draft），不依赖真实 pyJianYingDraft，仅验证 HTTP 层的 envelope
契约（成功路径、参数校验失败、非 zip 文件、未找到资源等错误分支）。
"""

from __future__ import annotations

import io
import zipfile

import pytest
from fastapi.testclient import TestClient

from vectcut.features.template_filling import service, storage
from vectcut.features.template_filling.schemas import ImportTemplateResponse
from vectcut.server.http import app

client = TestClient(app)


# ─── POST /api/template/import ───────────────────────────────────────────────


def test_import_endpoint_success(monkeypatch):
    """成功路径：mock service.import_template 返回 ImportTemplateResponse。"""
    fake_resp = ImportTemplateResponse(
        template_id="t1",
        slots=[{"slot_id": "v1", "type": "video"}],
        message="ok",
    )
    monkeypatch.setattr(service, "import_template", lambda tid, path: fake_resp)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("draft_content.json", "{}")
    buf.seek(0)

    resp = client.post(
        "/api/template/import?template_id=t1",
        files={"file": ("t.zip", buf, "application/zip")},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["error"] == ""
    assert data["output"]["template_id"] == "t1"
    assert data["output"]["slots"][0]["slot_id"] == "v1"


def test_import_endpoint_rejects_non_zip():
    """非 .zip 文件 → envelope_err（含 zip 字样）。"""
    resp = client.post(
        "/api/template/import?template_id=t1",
        files={"file": ("t.txt", io.BytesIO(b"x"), "text/plain")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert "zip" in data["error"]


def test_import_endpoint_template_error(monkeypatch):
    """service 抛 TemplateError → envelope_err 走全局 handler。"""
    from vectcut.core.errors import TemplateError

    def _raise(template_id, path):
        raise TemplateError("非法 template_id")

    monkeypatch.setattr(service, "import_template", _raise)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("draft_content.json", "{}")
    buf.seek(0)

    resp = client.post(
        "/api/template/import?template_id=t1",
        files={"file": ("t.zip", buf, "application/zip")},
    )
    data = resp.json()
    assert data["success"] is False
    assert "非法" in data["error"]


# ─── POST /api/template/slot-config ──────────────────────────────────────────


def test_slot_config_endpoint_validation_error():
    """空 body → 参数校验失败 → envelope_err。"""
    resp = client.post("/api/template/slot-config", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False


def test_slot_config_endpoint_success(monkeypatch):
    """成功路径：mock service.save_slot_config。"""
    from vectcut.features.template_filling.schemas import SaveSlotConfigResponse

    fake_resp = SaveSlotConfigResponse(
        template_id="t1", slot_count=1, message="ok",
    )
    monkeypatch.setattr(service, "save_slot_config", lambda tid, req: fake_resp)

    body = {
        "template_id": "t1",
        "slots": [
            {
                "slot_id": "video_main_0", "name": "v",
                "type": "video", "track_name": "main", "segment_index": 0,
            }
        ],
    }
    resp = client.post("/api/template/slot-config", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["output"]["slot_count"] == 1


# ─── POST /api/template/render ───────────────────────────────────────────────


def test_render_endpoint_validation_error():
    """空 body → 参数校验失败 → envelope_err。"""
    resp = client.post("/api/template/render", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False


def test_render_endpoint_success(monkeypatch):
    """成功路径：mock service.render_draft 返回 RenderDraftResponse。"""
    from vectcut.features.template_filling.schemas import RenderDraftResponse

    fake_resp = RenderDraftResponse(
        draft_id="draft_abc",
        download_url="/api/template/download/draft_abc",
        warnings=[],
    )
    monkeypatch.setattr(service, "render_draft", lambda tid, req: fake_resp)

    body = {
        "template_id": "t1",
        "slot_values": {"video_main_0": {"path": "/v.mp4", "duration": 5.0}},
        "output_draft_name": "out",
    }
    resp = client.post("/api/template/render", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["output"]["draft_id"] == "draft_abc"
    assert data["output"]["download_url"].endswith("/draft_abc")


# ─── GET /api/template/download/{draft_id} ───────────────────────────────────


def test_download_endpoint_not_found(monkeypatch):
    """draft 不存在 → envelope_err（mock service.download_draft 抛 RenderError）。"""
    from vectcut.core.errors import RenderError

    def _raise(draft_id):
        raise RenderError(f"草稿 {draft_id} 不存在")

    monkeypatch.setattr(service, "download_draft", _raise)

    resp = client.get("/api/template/download/draft_xxx")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert data["error"]["code"] == "RENDER_ERROR"
    assert "不存在" in data["error"]["message"]


def test_download_endpoint_success(monkeypatch, tmp_path):
    """成功路径：mock service.download_draft + storage.get_generated_draft_zip_path
    返回真实文件，FileResponse 返回 zip。"""
    from vectcut.features.template_filling.schemas import DownloadDraftResponse

    fake_resp = DownloadDraftResponse(
        draft_id="d1",
        download_url="/api/template/download/d1",
        message="ready",
    )
    monkeypatch.setattr(service, "download_draft", lambda did: fake_resp)

    zip_path = tmp_path / "d1.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("draft_content.json", "{}")
    monkeypatch.setattr(
        storage, "get_generated_draft_zip_path", lambda did: str(zip_path)
    )

    resp = client.get("/api/template/download/d1")
    assert resp.status_code == 200
    # FileResponse 的 media_type
    assert "application/zip" in resp.headers.get("content-type", "")

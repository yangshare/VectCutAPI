"""template_filling HTTP 契约测试：TestClient 驱动 4 个端点。

策略：mock service 层（import_template / save_slot_config / render_draft /
download_draft），不依赖真实 pyJianYingDraft，仅验证 HTTP 层的 envelope
契约（成功路径、参数校验失败、非 zip 文件、未找到资源等错误分支）。
"""

from __future__ import annotations

import asyncio
import importlib
import io
import inspect
import json
from types import SimpleNamespace
import zipfile

import pytest
from fastapi.testclient import TestClient

from vectcut.core.errors import make_error
from vectcut.features.template_filling import router, service, storage
from vectcut.features.template_filling.schemas import ImportTemplateResponse
from vectcut.server.http import app

http_app_module = importlib.import_module("vectcut.server.http.app")

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
    """非 .zip 文件 → 结构化 T_INVALID_ZIP。"""
    resp = client.post(
        "/api/template/import?template_id=t1",
        files={"file": ("t.txt", io.BytesIO(b"x"), "text/plain")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert data["error"]["code"] == "T_INVALID_ZIP"


def test_import_endpoint_template_error(monkeypatch):
    """service 抛 VectCutError → 保留结构化错误码。"""

    def _raise(template_id, path):
        raise make_error("T_INVALID_ID", details={"template_id": template_id})

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
    assert data["error"]["code"] == "T_INVALID_ID"
    assert data["error"]["details"] == {"template_id": "t1"}


def test_import_endpoint_content_length_middleware_rejects_before_multipart_parse(
    monkeypatch,
):
    """超大 Content-Length 应在 multipart 解析前被 middleware 拦截。"""
    monkeypatch.setattr(
        http_app_module,
        "load_config",
        lambda: SimpleNamespace(max_template_zip_mb=1),
        raising=False,
    )

    resp = client.post(
        "/api/template/import?template_id=t1",
        content=b"not multipart",
        headers={
            "content-type": "multipart/form-data; boundary=x",
            "content-length": str((2 * 1024 * 1024) + 1),
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert data["error"]["code"] == "T_TOO_LARGE"


def test_import_endpoint_chunked_body_middleware_rejects_before_handler(monkeypatch):
    """无 Content-Length 的分段 body 超限时也应由 ASGI middleware 拦截。"""
    monkeypatch.setattr(
        http_app_module,
        "load_config",
        lambda: SimpleNamespace(max_template_zip_mb=0),
        raising=False,
    )
    chunks = [b"x" * (1024 * 1024), b"x"]
    sent_messages = []

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/template/import",
        "raw_path": b"/api/template/import",
        "query_string": b"template_id=t1",
        "headers": [(b"content-type", b"multipart/form-data; boundary=x")],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }

    async def _receive():
        if chunks:
            return {
                "type": "http.request",
                "body": chunks.pop(0),
                "more_body": bool(chunks),
            }
        return {"type": "http.request", "body": b"", "more_body": False}

    async def _send(message):
        sent_messages.append(message)

    asyncio.run(app(scope, _receive, _send))

    status = next(m["status"] for m in sent_messages if m["type"] == "http.response.start")
    body = b"".join(
        m.get("body", b"") for m in sent_messages if m["type"] == "http.response.body"
    )
    data = json.loads(body.decode("utf-8"))
    assert status == 200
    assert data["success"] is False
    assert data["error"]["code"] == "T_TOO_LARGE"


def test_import_endpoint_missing_file_validation_returns_structured_error():
    """缺 file 的 RequestValidationError 也应返回结构化 error.code。"""
    resp = client.post("/api/template/import?template_id=t1", data={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_PARAM"
    assert data["error"]["details"]["errors"]


def test_import_endpoint_missing_template_id_validation_returns_structured_error():
    """缺 template_id 的 RequestValidationError 也应返回结构化 error.code。"""
    resp = client.post(
        "/api/template/import",
        files={"file": ("t.zip", io.BytesIO(b"PK\x03\x04"), "application/zip")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert data["error"]["code"] == "INVALID_PARAM"
    assert data["error"]["details"]["errors"]


# ─── POST /api/template/import-draft-content ────────────────────────────────


def test_import_draft_content_endpoint_success(monkeypatch):
    """成功路径：上传 draft_content.json bytes，不走 ZIP。"""
    captured: dict[str, object] = {}
    fake_resp = ImportTemplateResponse(
        template_id="t1",
        slots=[{"slot_id": "video_track0_seg0", "type": "video"}],
        message="ok",
    )

    def _import(template_id, content):
        captured["template_id"] = template_id
        captured["content"] = content
        return fake_resp

    monkeypatch.setattr(service, "import_draft_content", _import)
    monkeypatch.setattr(
        router,
        "load_config",
        lambda: SimpleNamespace(max_draft_content_mb=20),
        raising=False,
    )

    resp = client.post(
        "/api/template/import-draft-content?template_id=t1",
        files={"file": ("draft_content.json", io.BytesIO(b'{"tracks":[]}'), "application/json")},
    )

    data = resp.json()
    assert data["success"] is True
    assert captured == {"template_id": "t1", "content": b'{"tracks":[]}'}
    assert data["output"]["slots"][0]["slot_id"] == "video_track0_seg0"


def test_import_draft_content_endpoint_rejects_wrong_filename():
    """新接口只接收 draft_content.json。"""
    resp = client.post(
        "/api/template/import-draft-content?template_id=t1",
        files={"file": ("template.zip", io.BytesIO(b"PK\x03\x04"), "application/zip")},
    )

    data = resp.json()
    assert data["success"] is False
    assert data["error"]["code"] == "T_INVALID_DRAFT_CONTENT"


def test_import_draft_content_content_length_middleware_uses_draft_limit(monkeypatch):
    """新 draft_content 接口应按 max_draft_content_mb 在 multipart 解析前拦截。"""
    monkeypatch.setattr(
        http_app_module,
        "load_config",
        lambda: SimpleNamespace(max_template_zip_mb=50, max_draft_content_mb=1),
        raising=False,
    )

    resp = client.post(
        "/api/template/import-draft-content?template_id=t1",
        content=b"not multipart",
        headers={
            "content-type": "multipart/form-data; boundary=x",
            "content-length": str((2 * 1024 * 1024) + 1),
        },
    )

    data = resp.json()
    assert data["success"] is False
    assert data["error"]["code"] == "T_DRAFT_CONTENT_TOO_LARGE"


class _ChunkOnlyUpload:
    """Test double that fails if router reads the entire upload in one call."""

    filename = "template.zip"

    def __init__(self, payload: bytes):
        self._stream = io.BytesIO(payload)
        self.one_shot_reads = 0
        self.bounded_reads = 0

    async def read(self, size: int = -1) -> bytes:
        if size < 0:
            self.one_shot_reads += 1
            raise AssertionError("upload must be read in bounded chunks")
        self.bounded_reads += 1
        return self._stream.read(size)


class _RequestWithHeaders:
    def __init__(self, headers: dict[str, str] | None = None):
        self.headers = headers or {}


def test_import_template_reads_upload_in_chunks(monkeypatch):
    """上传保存应分块读取，不能依赖一次性 file.read()。"""
    fake_resp = ImportTemplateResponse(template_id="t1", slots=[], message="ok")

    def _import(template_id, path):
        assert template_id == "t1"
        assert open(path, "rb").read() == b"PK\x03\x04chunked"
        return fake_resp

    monkeypatch.setattr(service, "import_template", _import)
    monkeypatch.setattr(
        router, "load_config", lambda: SimpleNamespace(max_template_zip_mb=1), raising=False
    )

    upload = _ChunkOnlyUpload(b"PK\x03\x04chunked")
    data = asyncio.run(router.import_template(_RequestWithHeaders(), "t1", upload))

    assert data["success"] is True
    assert upload.one_shot_reads == 0


def test_import_template_rejects_oversized_content_length_before_read(monkeypatch):
    """Content-Length 已超限时应直接返回 T_TOO_LARGE，不读取 UploadFile。"""
    assert "request" in inspect.signature(router.import_template).parameters
    monkeypatch.setattr(
        router,
        "load_config",
        lambda: SimpleNamespace(max_template_zip_mb=1, temp_folder=""),
        raising=False,
    )
    upload = _ChunkOnlyUpload(b"x")

    data = asyncio.run(
        router.import_template(
            _RequestWithHeaders({"content-length": str((2 * 1024 * 1024) + 1)}),
            "t1",
            upload,
        )
    )

    assert data["success"] is False
    assert data["error"]["code"] == "T_TOO_LARGE"
    assert upload.one_shot_reads == 0


def test_import_template_allows_reasonable_multipart_content_length_overhead(monkeypatch):
    """Content-Length 在 multipart 合理开销内时不应提前拒绝。"""
    fake_resp = ImportTemplateResponse(template_id="t1", slots=[], message="ok")
    monkeypatch.setattr(service, "import_template", lambda tid, path: fake_resp)
    monkeypatch.setattr(
        router,
        "load_config",
        lambda: SimpleNamespace(max_template_zip_mb=1, temp_folder=""),
        raising=False,
    )
    upload = _ChunkOnlyUpload(b"PK\x03\x04ok")

    data = asyncio.run(
        router.import_template(
            _RequestWithHeaders({"content-length": str(1024 * 1024 + 512)}),
            "t1",
            upload,
        )
    )

    assert data["success"] is True
    assert upload.bounded_reads > 0


def test_import_template_rejects_clearly_oversized_content_length_before_read(monkeypatch):
    """Content-Length 明显超过 ZIP 上限和 multipart 开销时才提前拒绝。"""
    monkeypatch.setattr(
        router,
        "load_config",
        lambda: SimpleNamespace(max_template_zip_mb=1, temp_folder=""),
        raising=False,
    )
    upload = _ChunkOnlyUpload(b"PK\x03\x04ok")

    data = asyncio.run(
        router.import_template(
            _RequestWithHeaders({"content-length": str((2 * 1024 * 1024) + 1)}),
            "t1",
            upload,
        )
    )

    assert data["success"] is False
    assert data["error"]["code"] == "T_TOO_LARGE"
    assert upload.bounded_reads == 0


def test_import_template_rejects_oversized_upload_with_code(monkeypatch):
    """超过 Settings.max_template_zip_mb 时返回 T_TOO_LARGE 且不调用 service。"""
    called = False

    def _import(template_id, path):
        nonlocal called
        called = True
        return ImportTemplateResponse(template_id=template_id, slots=[], message="bad")

    monkeypatch.setattr(service, "import_template", _import)
    monkeypatch.setattr(
        router, "load_config", lambda: SimpleNamespace(max_template_zip_mb=0), raising=False
    )

    data = asyncio.run(
        router.import_template(_RequestWithHeaders(), "t1", _ChunkOnlyUpload(b"x"))
    )

    assert data["success"] is False
    assert data["error"]["code"] == "T_TOO_LARGE"
    assert called is False


def test_import_template_removes_temp_file_after_success(monkeypatch, tmp_path):
    """正常导入后应删除临时上传文件。"""
    temp_path = tmp_path / "success.zip"
    saved_path = {}

    class _NamedTemp:
        name = str(temp_path)

        def __enter__(self):
            self.file = open(temp_path, "wb")
            return self.file

        def __exit__(self, exc_type, exc, tb):
            self.file.close()

    def _import(template_id, path):
        saved_path["value"] = path
        assert temp_path.exists()
        return ImportTemplateResponse(template_id=template_id, slots=[], message="ok")

    monkeypatch.setattr(router.tempfile, "NamedTemporaryFile", lambda **kwargs: _NamedTemp())
    monkeypatch.setattr(router, "load_config", lambda: SimpleNamespace(max_template_zip_mb=1, temp_folder=""))
    monkeypatch.setattr(service, "import_template", _import)

    data = asyncio.run(
        router.import_template(
            _RequestWithHeaders(), "t1", _ChunkOnlyUpload(b"PK\x03\x04ok")
        )
    )

    assert data["success"] is True
    assert saved_path["value"] == str(temp_path)
    assert not temp_path.exists()


def test_import_template_removes_temp_file_after_business_error(monkeypatch, tmp_path):
    """service 抛业务异常时也应删除临时上传文件。"""
    temp_path = tmp_path / "error.zip"

    class _NamedTemp:
        name = str(temp_path)

        def __enter__(self):
            self.file = open(temp_path, "wb")
            return self.file

        def __exit__(self, exc_type, exc, tb):
            self.file.close()

    def _raise(template_id, path):
        assert temp_path.exists()
        raise make_error("T_INVALID_ID")

    monkeypatch.setattr(router.tempfile, "NamedTemporaryFile", lambda **kwargs: _NamedTemp())
    monkeypatch.setattr(router, "load_config", lambda: SimpleNamespace(max_template_zip_mb=1, temp_folder=""))
    monkeypatch.setattr(service, "import_template", _raise)

    data = asyncio.run(
        router.import_template(
            _RequestWithHeaders(), "t1", _ChunkOnlyUpload(b"PK\x03\x04bad")
        )
    )

    assert data["success"] is False
    assert data["error"]["code"] == "T_INVALID_ID"
    assert not temp_path.exists()


# ─── POST /api/template/slot-config ──────────────────────────────────────────


def test_slot_config_endpoint_validation_error():
    """空 body → 参数校验失败 → envelope_err。"""
    resp = client.post("/api/template/slot-config", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert data["error"]["code"] == "S_INVALID_SLOT"


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


def test_slot_config_endpoint_preserves_vectcut_error_code(monkeypatch):
    """slot-config 捕获 VectCutError 时不能退化成字符串。"""

    def _raise(template_id, req):
        raise make_error("S_INVALID_SLOT", details={"slot_id": "missing_slot"})

    monkeypatch.setattr(service, "save_slot_config", _raise)

    body = {
        "template_id": "t1",
        "slots": [
            {
                "slot_id": "missing_slot", "name": "v",
                "type": "video", "track_name": "main", "segment_index": 0,
            }
        ],
    }
    resp = client.post("/api/template/slot-config", json=body)
    data = resp.json()
    assert data["success"] is False
    assert data["error"]["code"] == "S_INVALID_SLOT"
    assert data["error"]["details"] == {"slot_id": "missing_slot"}


# ─── POST /api/template/render ───────────────────────────────────────────────


def test_render_endpoint_validation_error():
    """空 body → 参数校验失败 → envelope_err。"""
    resp = client.post("/api/template/render", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert data["error"]["code"] == "R_INVALID_TASK"


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


def test_render_endpoint_preserves_vectcut_error_code(monkeypatch):
    """render 捕获 VectCutError 时不能退化成字符串。"""

    def _raise(template_id, req):
        raise make_error("S_NOT_FOUND", details={"template_id": template_id})

    monkeypatch.setattr(service, "render_draft", _raise)

    body = {
        "template_id": "t1",
        "slot_values": {"video_main_0": {"path": "/v.mp4", "duration": 5.0}},
        "output_draft_name": "out",
    }
    resp = client.post("/api/template/render", json=body)
    data = resp.json()
    assert data["success"] is False
    assert data["error"]["code"] == "S_NOT_FOUND"
    assert data["error"]["details"] == {"template_id": "t1"}


# ─── GET /api/template/download/{draft_id} ───────────────────────────────────


def test_download_endpoint_not_found_returns_structured_task_code(monkeypatch):
    """draft 不存在 → FastAPI envelope 保留 R_TASK_NOT_FOUND。"""
    monkeypatch.setattr(storage, "get_generated_draft_zip_path", lambda did: None)

    resp = client.get("/api/template/download/draft_xxx")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert data["error"]["code"] == "R_TASK_NOT_FOUND"
    assert "不存在" in data["error"]["message"]


def test_download_endpoint_missing_zip_after_service_check_returns_task_code(monkeypatch):
    """service 首次通过但二次查找 ZIP 丢失时仍返回 R_TASK_NOT_FOUND。"""
    from vectcut.features.template_filling.schemas import DownloadDraftResponse

    monkeypatch.setattr(
        service,
        "download_draft",
        lambda did: DownloadDraftResponse(
            draft_id=did,
            download_url=f"/api/template/download/{did}",
            message="ready",
        ),
    )
    monkeypatch.setattr(storage, "get_generated_draft_zip_path", lambda did: None)

    resp = client.get("/api/template/download/draft_race")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert data["error"]["code"] == "R_TASK_NOT_FOUND"
    assert data["error"]["details"] == {"draft_id": "draft_race"}


def test_download_endpoint_invalid_draft_id_returns_structured_task_code():
    """FastAPI 可路由的非法 draft_id → R_INVALID_TASK。"""
    resp = client.get("/api/template/download/bad.id")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert data["error"]["code"] == "R_INVALID_TASK"


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

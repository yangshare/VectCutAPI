"""service.py 单元测试：覆盖 template_filling 业务编排层。

策略：mock 掉 pyJianYingDraft 的 Script_file.load_template 及 storage 侧调用，
聚焦于流程编排与错误分支，不依赖真实剪映 draft JSON。
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List
import threading
import zipfile

import pytest

from vectcut.core.errors import RenderError, SlotError, TemplateError
from vectcut.features.template_filling import service
from vectcut.features.template_filling.schemas import (
    DownloadDraftResponse,
    ImportTemplateResponse,
    RenderDraftResponse,
    SaveSlotConfigResponse,
    SlotConfig,
)


# ─── 公共 fixture：fake storage + fake config ───────────────────────────────


@pytest.fixture
def fake_storage(monkeypatch, tmp_path: Path):
    """把 service 内引用的 storage 模块函数全部替换为内存版。"""
    cfg = SimpleNamespace(
        template_folder=str(tmp_path / "templates"),
        template_config_folder=str(tmp_path / "template_configs"),
        generated_draft_folder=str(tmp_path / "generated_drafts"),
    )
    monkeypatch.setattr(
        "vectcut.features.template_filling.service.load_config", lambda: cfg
    )

    # 模板解包目录字典（template_id → extract_dir 路径）
    state: Dict[str, Any] = {
        "templates": {},  # template_id → extract_dir
        "slots": {},  # template_id → list[dict]
        "drafts": {},  # draft_id → zip_path
    }

    def _extract(template_id: str, uploaded_zip_path: str) -> str:
        extract_dir = Path(cfg.template_folder) / template_id
        extract_dir.mkdir(parents=True, exist_ok=True)
        # 写一个最小 draft_content.json，让 get_template_draft_content_path 通过
        (extract_dir / "draft_content.json").write_text("{}", encoding="utf-8")
        state["templates"][template_id] = str(extract_dir)
        return str(extract_dir)

    def _stage(template_id: str, uploaded_zip_path: str):
        extract_dir = Path(cfg.template_folder) / f"{template_id}.staged"
        extract_dir.mkdir(parents=True, exist_ok=True)
        (extract_dir / "draft_content.json").write_text("{}", encoding="utf-8")
        return SimpleNamespace(template_id=template_id, extract_dir=extract_dir)

    def _commit(stage) -> str:
        final_dir = Path(cfg.template_folder) / stage.template_id
        final_dir.mkdir(parents=True, exist_ok=True)
        (final_dir / "draft_content.json").write_text("{}", encoding="utf-8")
        state["templates"][stage.template_id] = str(final_dir)
        return str(final_dir)

    def _cleanup(stage) -> None:
        return None

    def _get_draft_content_path(template_id: str) -> str:
        extract_dir = state["templates"].get(template_id)
        if not extract_dir:
            raise TemplateError(f"模板 {template_id} 缺少 draft_content.json")
        return str(Path(extract_dir) / "draft_content.json")

    def _get_draft_content_path_from_dir(template_id: str, extract_dir) -> str:
        return str(Path(extract_dir) / "draft_content.json")

    def _save_slot_config(template_id: str, slots: list) -> None:
        state["slots"][template_id] = list(slots)

    def _load_slot_config(template_id: str) -> list:
        if template_id not in state["slots"]:
            raise SlotError(f"模板 {template_id} 的槽位配置不存在")
        return state["slots"][template_id]

    def _save_generated_draft_zip(draft_id: str, draft_folder_path: str) -> str:
        zip_path = Path(cfg.generated_draft_folder) / f"{draft_id}.zip"
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        zip_path.write_bytes(b"PK\x03\x04dummy")
        state["drafts"][draft_id] = str(zip_path)
        return str(zip_path)

    def _get_generated_draft_zip_path(draft_id: str):
        return state["drafts"].get(draft_id)

    @contextmanager
    def _template_lock(_template_id: str, timeout_seconds: float = 30.0):
        yield

    monkeypatch.setattr(service.storage, "extract_template_zip", _extract)
    monkeypatch.setattr(service.storage, "stage_extract_template_zip", _stage)
    monkeypatch.setattr(service.storage, "commit_staged_template", _commit)
    monkeypatch.setattr(service.storage, "cleanup_staged_template", _cleanup)
    monkeypatch.setattr(
        service.storage, "template_lock", _template_lock, raising=False
    )
    monkeypatch.setattr(
        service.storage, "get_template_draft_content_path", _get_draft_content_path
    )
    monkeypatch.setattr(
        service.storage,
        "get_template_draft_content_path_from_dir",
        _get_draft_content_path_from_dir,
    )
    monkeypatch.setattr(service.storage, "save_slot_config", _save_slot_config)
    monkeypatch.setattr(service.storage, "load_slot_config", _load_slot_config)
    monkeypatch.setattr(
        service.storage, "save_generated_draft_zip", _save_generated_draft_zip
    )
    monkeypatch.setattr(
        service.storage, "get_generated_draft_zip_path", _get_generated_draft_zip_path
    )
    return state


# ─── fake script 工厂：构造有 tracks/segments 的 mock 母版 ──────────────────


class _FakeTrackType:
    """模拟 Track_type 枚举（仅用作 .name 属性）。"""
    def __init__(self, name: str):
        self.name = name


def _make_track(track_type, name: str, seg_count: int = 1) -> SimpleNamespace:
    segs = [SimpleNamespace(target_timerange=SimpleNamespace(duration=1_000_000))
            for _ in range(seg_count)]
    return SimpleNamespace(
        name=name,
        track_type=track_type,
        segments=segs,
    )


def _make_fake_script(
    tracks: List[SimpleNamespace],
    *,
    replace_material_by_seg: Any = None,
) -> SimpleNamespace:
    """构造一个 mock 的 Script_file，包含 dump + 可选的 replace_material_by_seg。"""

    def _dump(path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text("{}", encoding="utf-8")

    def _get_imported_track(_track_type, name=None):
        for track in tracks:
            if track.name == name:
                return track
        raise KeyError(f"未找到轨道: {name}")

    return SimpleNamespace(
        tracks=tracks,
        dump=_dump,
        get_imported_track=_get_imported_track,
        replace_material_by_seg=replace_material_by_seg or (lambda *a, **k: None),
    )


# 默认 tracks：一条 video + 一条 audio(bgm) + 一条 text
_DEFAULT_TRACKS = [
    _make_track(_FakeTrackType("video"), "main_video", seg_count=1),
    _make_track(_FakeTrackType("audio"), "bgm_track", seg_count=1),
    _make_track(_FakeTrackType("text"), "subtitle_track", seg_count=1),
]


@pytest.fixture
def fake_draft_module(monkeypatch):
    """mock service 内的 draft 模块（pyJianYingDraft as draft）。

    返回 calls 字典记录 load_template / dump 调用。
    """
    calls: Dict[str, Any] = {"load_template_args": [], "dump_args": []}

    def _load_template(json_path: str):
        calls["load_template_args"].append(json_path)
        return _make_fake_script(_DEFAULT_TRACKS)

    monkeypatch.setattr(service.draft.Script_file, "load_template", _load_template)
    return calls


# ─── import_template ───────────────────────────────────────────────────────


def test_import_template_invalid_id(fake_storage, tmp_path: Path):
    """非法 template_id → T_INVALID_ID。"""
    zip_path = tmp_path / "src.zip"
    zip_path.write_bytes(b"PK\x03\x04")

    with pytest.raises(TemplateError, match="非法") as exc:
        service.import_template("invalid id with space", str(zip_path))
    assert exc.value.code == "T_INVALID_ID"


def test_import_template_success(fake_storage, fake_draft_module, tmp_path: Path):
    """合法 template_id → 调用 extract + load_template，返回 ImportTemplateResponse。"""
    zip_path = tmp_path / "src.zip"
    zip_path.write_bytes(b"PK\x03\x04")

    resp = service.import_template("tpl_001", str(zip_path))

    assert isinstance(resp, ImportTemplateResponse)
    assert resp.template_id == "tpl_001"
    assert resp.message  # 非空
    # 应当扫描出 3 个轨道 × 1 段 = 3 个槽位
    slot_types = {s["type"] for s in resp.slots}
    assert "video" in slot_types
    assert "bgm" in slot_types  # track name 含 "bgm"
    assert "subtitle" in slot_types
    # load_template 被调用过
    assert len(fake_draft_module["load_template_args"]) == 1


def _write_template_zip(zip_path: Path, content: bytes | None = b"{}") -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        if content is not None:
            zf.writestr("draft_content.json", content)


def _seed_existing_template_storage(tmp_path: Path, monkeypatch):
    cfg = SimpleNamespace(
        template_folder=str(tmp_path / "templates"),
        template_config_folder=str(tmp_path / "template_configs"),
        generated_draft_folder=str(tmp_path / "generated_drafts"),
        max_template_zip_mb=50,
    )
    monkeypatch.setattr(service.storage, "load_config", lambda: cfg)

    template_id = "tpl_existing"
    extract_dir = Path(cfg.template_folder) / template_id
    extract_dir.mkdir(parents=True, exist_ok=True)
    (extract_dir / "draft_content.json").write_text('{"old": true}', encoding="utf-8")
    stored_zip = Path(cfg.template_folder) / f"{template_id}.zip"
    _write_template_zip(stored_zip, b'{"old": true}')
    return cfg, template_id, extract_dir, stored_zip, stored_zip.read_bytes()


def test_import_template_semantic_failure_preserves_existing_template_without_draft(
    tmp_path: Path, monkeypatch
):
    """合法 ZIP 但缺 draft_content/draft_info 时不得替换已有模板。"""
    _cfg, template_id, extract_dir, stored_zip, old_zip = _seed_existing_template_storage(
        tmp_path, monkeypatch
    )
    bad_zip = tmp_path / "missing_draft.zip"
    _write_template_zip(bad_zip, content=None)

    with pytest.raises(TemplateError) as exc:
        service.import_template(template_id, str(bad_zip))

    assert exc.value.code == "T_NO_DRAFT_CONTENT"
    assert (extract_dir / "draft_content.json").read_text(encoding="utf-8") == '{"old": true}'
    assert stored_zip.read_bytes() == old_zip


def test_import_template_rejects_draft_info_only_and_preserves_existing_template(
    tmp_path: Path, monkeypatch
):
    """模板导入语义校验必须严格要求 draft_content.json。"""
    _cfg, template_id, extract_dir, stored_zip, old_zip = _seed_existing_template_storage(
        tmp_path, monkeypatch
    )
    draft_info_only_zip = tmp_path / "draft_info_only.zip"
    with zipfile.ZipFile(draft_info_only_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("draft_info.json", b'{"new": true}')

    monkeypatch.setattr(
        service.draft.Script_file,
        "load_template",
        lambda _path: _make_fake_script(_DEFAULT_TRACKS),
    )

    with pytest.raises(TemplateError) as exc:
        service.import_template(template_id, str(draft_info_only_zip))

    assert exc.value.code == "T_NO_DRAFT_CONTENT"
    assert (extract_dir / "draft_content.json").read_text(encoding="utf-8") == '{"old": true}'
    assert stored_zip.read_bytes() == old_zip


def test_import_template_load_failure_preserves_existing_template(
    tmp_path: Path, monkeypatch
):
    """draft_content 存在但 load_template 失败时应结构化失败且不得替换已有模板。"""
    _cfg, template_id, extract_dir, stored_zip, old_zip = _seed_existing_template_storage(
        tmp_path, monkeypatch
    )
    bad_zip = tmp_path / "bad_draft.zip"
    _write_template_zip(bad_zip, b'{"bad": true}')

    def _raise(_path: str):
        raise RuntimeError(
            "cannot load draft token=SECRET_TOKEN_123456 /home/alice/private/draft"
        )

    monkeypatch.setattr(service.draft.Script_file, "load_template", _raise)

    with pytest.raises(TemplateError) as exc:
        service.import_template(template_id, str(bad_zip))

    assert exc.value.code == "T_INVALID_ZIP"
    assert exc.value.details["template_id"] == template_id
    assert "cannot load draft" in exc.value.details["reason"]
    assert "SECRET_TOKEN_123456" not in exc.value.details["reason"]
    assert "/home/alice/private/draft" not in exc.value.details["reason"]
    assert (extract_dir / "draft_content.json").read_text(encoding="utf-8") == '{"old": true}'
    assert stored_zip.read_bytes() == old_zip


def test_import_template_scan_failure_preserves_existing_template(
    tmp_path: Path, monkeypatch
):
    """load 后扫描槽位失败也应映射为结构化 T_INVALID_ZIP，且不得提交 staging。"""
    _cfg, template_id, extract_dir, stored_zip, old_zip = _seed_existing_template_storage(
        tmp_path, monkeypatch
    )
    bad_zip = tmp_path / "bad_scan.zip"
    _write_template_zip(bad_zip, b'{"bad": true}')

    class _BadScript:
        @property
        def tracks(self):
            raise RuntimeError("scan failed credential=SECRET_CREDENTIAL")

    monkeypatch.setattr(
        service.draft.Script_file,
        "load_template",
        lambda _path: _BadScript(),
    )

    with pytest.raises(TemplateError) as exc:
        service.import_template(template_id, str(bad_zip))

    assert exc.value.code == "T_INVALID_ZIP"
    assert exc.value.details["template_id"] == template_id
    assert "scan failed" in exc.value.details["reason"]
    assert "SECRET_CREDENTIAL" not in exc.value.details["reason"]
    assert (extract_dir / "draft_content.json").read_text(encoding="utf-8") == '{"old": true}'
    assert stored_zip.read_bytes() == old_zip


# ─── save_slot_config ──────────────────────────────────────────────────────


def test_save_slot_config_template_not_imported(fake_storage):
    """模板未导入 → T_NO_DRAFT_CONTENT。"""
    from vectcut.features.template_filling.schemas import SaveSlotConfigRequest

    req = SaveSlotConfigRequest(
        template_id="missing_tpl",
        slots=[SlotConfig(slot_id="video_main_0", name="v",
                          type="video", track_name="main", segment_index=0)],
    )
    with pytest.raises(TemplateError) as exc:
        service.save_slot_config("missing_tpl", req)
    assert exc.value.code == "T_NO_DRAFT_CONTENT"


def test_save_slot_config_invalid_slot(fake_storage, fake_draft_module, tmp_path: Path):
    """slot_id 不存在于母版扫描结果 → S_INVALID_SLOT。"""
    # 先导入一个模板建立 state
    zip_path = tmp_path / "src.zip"
    zip_path.write_bytes(b"PK\x03\x04")
    service.import_template("tpl_x", str(zip_path))

    from vectcut.features.template_filling.schemas import SaveSlotConfigRequest

    req = SaveSlotConfigRequest(
        template_id="tpl_x",
        slots=[SlotConfig(slot_id="not_exist_slot", name="x",
                          type="video", track_name="nope", segment_index=0)],
    )
    with pytest.raises(SlotError, match="不存在") as exc:
        service.save_slot_config("tpl_x", req)
    assert exc.value.code == "S_INVALID_SLOT"
    assert exc.value.details["slot_id"] == "not_exist_slot"


def test_save_slot_config_success(fake_storage, fake_draft_module, tmp_path: Path):
    """正常保存 → 调用 storage.save_slot_config，返回响应。"""
    zip_path = tmp_path / "src.zip"
    zip_path.write_bytes(b"PK\x03\x04")
    service.import_template("tpl_y", str(zip_path))

    from vectcut.features.template_filling.schemas import SaveSlotConfigRequest

    req = SaveSlotConfigRequest(
        template_id="tpl_y",
        slots=[SlotConfig(
            slot_id="video_main_video_0",
            name="主视频", type="video",
            track_name="main_video", segment_index=0,
        )],
    )
    resp = service.save_slot_config("tpl_y", req)

    assert isinstance(resp, SaveSlotConfigResponse)
    assert resp.template_id == "tpl_y"
    assert resp.slot_count == 1
    # state 中应当保存
    assert "tpl_y" in fake_storage["slots"]


@pytest.mark.parametrize("operation", ["render_draft", "save_slot_config"])
def test_template_read_operations_wait_for_import_template_lock(
    fake_storage,
    fake_draft_module,
    monkeypatch,
    tmp_path: Path,
    operation: str,
):
    """同 template_id import 持锁提交时，render/save-slot 不得进入模板读取区。"""
    template_id = "tpl_lock"
    existing_dir = tmp_path / "existing_tpl"
    existing_dir.mkdir(parents=True)
    (existing_dir / "draft_content.json").write_text("{}", encoding="utf-8")
    fake_storage["templates"][template_id] = str(existing_dir)
    fake_storage["slots"][template_id] = [
        {
            "slot_id": "video_main_video_0",
            "type": "video",
            "track_name": "main_video",
            "segment_index": 0,
            "required": False,
        }
    ]

    mutex = threading.Lock()
    import_in_commit = threading.Event()
    blocked_on_lock = threading.Event()
    release_import = threading.Event()
    read_entered = threading.Event()

    @contextmanager
    def _template_lock(_template_id: str, timeout_seconds: float = 30.0):
        acquired = mutex.acquire(blocking=False)
        if not acquired:
            blocked_on_lock.set()
            mutex.acquire()
        try:
            yield
        finally:
            mutex.release()

    def _commit_with_pause(stage) -> str:
        import_in_commit.set()
        assert release_import.wait(2)
        final_dir = tmp_path / f"{stage.template_id}_final"
        final_dir.mkdir(parents=True, exist_ok=True)
        (final_dir / "draft_content.json").write_text("{}", encoding="utf-8")
        fake_storage["templates"][stage.template_id] = str(final_dir)
        return str(final_dir)

    def _get_draft_content_path(template_id_arg: str) -> str:
        read_entered.set()
        return str(Path(fake_storage["templates"][template_id_arg]) / "draft_content.json")

    monkeypatch.setattr(service.storage, "template_lock", _template_lock, raising=False)
    monkeypatch.setattr(service.storage, "commit_staged_template", _commit_with_pause)
    monkeypatch.setattr(
        service.storage, "get_template_draft_content_path", _get_draft_content_path
    )

    import_zip = tmp_path / "src.zip"
    import_zip.write_bytes(b"PK\x03\x04")
    import_errors: list[BaseException] = []
    worker_errors: list[BaseException] = []

    def _run_import():
        try:
            service.import_template(template_id, str(import_zip))
        except BaseException as exc:
            import_errors.append(exc)

    def _run_worker():
        try:
            if operation == "render_draft":
                from vectcut.features.template_filling.schemas import RenderDraftRequest

                req = RenderDraftRequest(
                    template_id=template_id,
                    slot_values={},
                    output_draft_name="out",
                )
                service.render_draft(template_id, req)
            else:
                from vectcut.features.template_filling.schemas import SaveSlotConfigRequest

                req = SaveSlotConfigRequest(
                    template_id=template_id,
                    slots=[
                        SlotConfig(
                            slot_id="video_main_video_0",
                            name="主视频",
                            type="video",
                            track_name="main_video",
                            segment_index=0,
                        )
                    ],
                )
                service.save_slot_config(template_id, req)
        except BaseException as exc:
            worker_errors.append(exc)

    import_thread = threading.Thread(target=_run_import)
    import_thread.start()
    assert import_in_commit.wait(2)

    worker_thread = threading.Thread(target=_run_worker)
    worker_thread.start()
    assert blocked_on_lock.wait(2)
    assert not read_entered.is_set()

    release_import.set()
    import_thread.join(2)
    worker_thread.join(2)

    assert not import_thread.is_alive()
    assert not worker_thread.is_alive()
    assert import_errors == []
    assert worker_errors == []


# ─── download_draft ────────────────────────────────────────────────────────


def test_download_draft_not_found(fake_storage):
    """storage 返回 None → R_TASK_NOT_FOUND。"""
    with pytest.raises(RenderError, match="不存在") as exc:
        service.download_draft("draft_unknown")
    assert exc.value.code == "R_TASK_NOT_FOUND"


def test_download_draft_empty_id(fake_storage):
    """空 draft_id → R_INVALID_TASK。"""
    with pytest.raises(RenderError) as exc:
        service.download_draft("")
    assert exc.value.code == "R_INVALID_TASK"


def test_download_draft_success(fake_storage):
    """storage 返回路径 → 返回 DownloadDraftResponse，download_url 为相对路径。"""
    fake_storage["drafts"]["d1"] = "/some/path/d1.zip"

    resp = service.download_draft("d1")

    assert isinstance(resp, DownloadDraftResponse)
    assert resp.draft_id == "d1"
    assert resp.download_url == "/api/template/download/d1"
    assert resp.message


# ─── render_draft ──────────────────────────────────────────────────────────


def test_render_draft_template_not_imported(fake_storage, fake_draft_module):
    """模板未导入 → T_NO_DRAFT_CONTENT。"""
    from vectcut.features.template_filling.schemas import RenderDraftRequest

    req = RenderDraftRequest(
        template_id="missing",
        slot_values={},
        output_draft_name="out",
    )
    with pytest.raises(TemplateError) as exc:
        service.render_draft("missing", req)
    assert exc.value.code == "T_NO_DRAFT_CONTENT"


def test_render_draft_no_slot_config(fake_storage, fake_draft_module, tmp_path: Path):
    """模板已导入但未保存槽位配置 → S_NOT_FOUND。"""
    zip_path = tmp_path / "src.zip"
    zip_path.write_bytes(b"PK\x03\x04")
    service.import_template("tpl_r1", str(zip_path))

    from vectcut.features.template_filling.schemas import RenderDraftRequest

    req = RenderDraftRequest(
        template_id="tpl_r1",
        slot_values={},
        output_draft_name="out",
    )
    with pytest.raises(SlotError) as exc:
        service.render_draft("tpl_r1", req)
    assert exc.value.code == "S_NOT_FOUND"


def test_render_draft_duplicate_slot_id_is_structured(
    fake_storage, fake_draft_module, tmp_path: Path
):
    """重复 slot_id 不能静默覆盖，应返回 S_INVALID_SLOT。"""
    zip_path = tmp_path / "src.zip"
    zip_path.write_bytes(b"PK\x03\x04")
    service.import_template("tpl_duplicate_slot", str(zip_path))

    fake_storage["slots"]["tpl_duplicate_slot"] = [
        {
            "slot_id": "video_main_video_0",
            "type": "video",
            "track_name": "main_video",
            "segment_index": 0,
            "required": False,
        },
        {
            "slot_id": "video_main_video_0",
            "type": "video",
            "track_name": "main_video",
            "segment_index": 0,
            "required": False,
        },
    ]

    from vectcut.features.template_filling.schemas import RenderDraftRequest

    req = RenderDraftRequest(
        template_id="tpl_duplicate_slot",
        slot_values={},
        output_draft_name="out",
    )

    with pytest.raises(SlotError) as exc:
        service.render_draft("tpl_duplicate_slot", req)
    assert exc.value.code == "S_INVALID_SLOT"
    assert exc.value.details["slot_id"] == "video_main_video_0"
    assert exc.value.details["first_index"] == 0
    assert exc.value.details["duplicate_index"] == 1


def test_render_draft_unknown_slot(fake_storage, fake_draft_module, tmp_path: Path):
    """slot_values 含未配置的 slot_id → S_INVALID_SLOT。"""
    zip_path = tmp_path / "src.zip"
    zip_path.write_bytes(b"PK\x03\x04")
    service.import_template("tpl_r2", str(zip_path))

    # 手动注入一个槽位配置
    fake_storage["slots"]["tpl_r2"] = [
        {"slot_id": "video_main_video_0", "type": "video",
         "track_name": "main_video", "segment_index": 0}
    ]

    from vectcut.features.template_filling.schemas import RenderDraftRequest

    req = RenderDraftRequest(
        template_id="tpl_r2",
        slot_values={"unknown_slot": {"path": "/x.mp4", "duration": 1.0,
                                      "width": 100, "height": 100}},
        output_draft_name="out",
    )
    with pytest.raises(SlotError, match="未在配置中") as exc:
        service.render_draft("tpl_r2", req)
    assert exc.value.code == "S_INVALID_SLOT"
    assert exc.value.details["slot_id"] == "unknown_slot"


@pytest.mark.parametrize(
    ("slot_type", "slot_id", "slot_value", "expected_code"),
    [
        (
            "video",
            "video_main_video_0",
            {"path": "/v.mp4", "width": 1920, "height": 1080},
            "R_INVALID_DURATION",
        ),
        (
            "video",
            "video_main_video_0",
            {"path": "/v.mp4", "duration": 5.0, "height": 1080},
            "R_INVALID_PATH",
        ),
        (
            "video",
            "video_main_video_0",
            {"duration": 5.0, "width": 1920, "height": 1080},
            "R_INVALID_PATH",
        ),
        (
            "audio",
            "audio_bgm_track_0",
            {"path": "/a.mp3"},
            "R_INVALID_DURATION",
        ),
    ],
)
def test_render_draft_invalid_material_metadata_is_structured(
    fake_storage,
    fake_draft_module,
    tmp_path: Path,
    slot_type,
    slot_id,
    slot_value,
    expected_code,
):
    """render 主路径素材 metadata 缺字段应返回结构化 R_*，不能冒出 KeyError。"""
    zip_path = tmp_path / "src.zip"
    zip_path.write_bytes(b"PK\x03\x04")
    service.import_template("tpl_bad_metadata", str(zip_path))

    track_name = "main_video" if slot_type == "video" else "bgm_track"
    fake_storage["slots"]["tpl_bad_metadata"] = [
        {
            "slot_id": slot_id,
            "type": slot_type,
            "track_name": track_name,
            "segment_index": 0,
        }
    ]

    from vectcut.features.template_filling.schemas import RenderDraftRequest

    req = RenderDraftRequest(
        template_id="tpl_bad_metadata",
        slot_values={slot_id: slot_value},
        output_draft_name="out",
    )

    with pytest.raises(RenderError) as exc:
        service.render_draft("tpl_bad_metadata", req)
    assert exc.value.code == expected_code


def test_render_draft_non_dict_slot_value_is_structured(
    fake_storage,
    fake_draft_module,
    tmp_path: Path,
):
    """render 主路径 slot value 非 dict 应返回结构化 R_*，不能冒出 AttributeError。"""
    zip_path = tmp_path / "src.zip"
    zip_path.write_bytes(b"PK\x03\x04")
    service.import_template("tpl_non_dict_metadata", str(zip_path))

    fake_storage["slots"]["tpl_non_dict_metadata"] = [
        {
            "slot_id": "video_main_video_0",
            "type": "video",
            "track_name": "main_video",
            "segment_index": 0,
        }
    ]

    from vectcut.features.template_filling.schemas import RenderDraftRequest

    req = RenderDraftRequest(
        template_id="tpl_non_dict_metadata",
        slot_values={"video_main_video_0": "not-a-dict"},
        output_draft_name="out",
    )

    with pytest.raises(RenderError) as exc:
        service.render_draft("tpl_non_dict_metadata", req)
    assert exc.value.code == "R_INVALID_PATH"
    assert exc.value.details["metadata_type"] == "str"


def test_render_draft_missing_required_slot_is_structured(
    fake_storage, fake_draft_module, tmp_path: Path
):
    """required 槽位缺少 slot_values 时应返回 R_MISSING_SLOT。"""
    zip_path = tmp_path / "src.zip"
    zip_path.write_bytes(b"PK\x03\x04")
    service.import_template("tpl_required_missing", str(zip_path))

    fake_storage["slots"]["tpl_required_missing"] = [
        {
            "slot_id": "video_main_video_0",
            "type": "video",
            "track_name": "main_video",
            "segment_index": 0,
            "required": True,
        }
    ]

    from vectcut.features.template_filling.schemas import RenderDraftRequest

    req = RenderDraftRequest(
        template_id="tpl_required_missing",
        slot_values={},
        output_draft_name="out",
    )

    with pytest.raises(RenderError) as exc:
        service.render_draft("tpl_required_missing", req)
    assert exc.value.code == "R_MISSING_SLOT"
    assert exc.value.details["template_id"] == "tpl_required_missing"
    assert exc.value.details["missing_slot_ids"] == ["video_main_video_0"]


def test_render_draft_missing_optional_slot_is_allowed(
    fake_storage, fake_draft_module, tmp_path: Path
):
    """required=False 的槽位缺值时允许继续生成草稿。"""
    zip_path = tmp_path / "src.zip"
    zip_path.write_bytes(b"PK\x03\x04")
    service.import_template("tpl_optional_missing", str(zip_path))

    fake_storage["slots"]["tpl_optional_missing"] = [
        {
            "slot_id": "video_main_video_0",
            "type": "video",
            "track_name": "main_video",
            "segment_index": 0,
            "required": False,
        }
    ]

    from vectcut.features.template_filling.schemas import RenderDraftRequest

    req = RenderDraftRequest(
        template_id="tpl_optional_missing",
        slot_values={},
        output_draft_name="out",
    )

    resp = service.render_draft("tpl_optional_missing", req)
    assert isinstance(resp, RenderDraftResponse)
    assert resp.draft_id in fake_storage["drafts"]


@pytest.mark.parametrize(
    ("slot_update", "expected_code"),
    [
        ({"type": "custom"}, "S_INVALID_SLOT"),
        ({"track_name": "missing_track"}, "S_TRACK_NOT_FOUND"),
        ({"segment_index": 99}, "S_SEGMENT_NOT_FOUND"),
    ],
)
def test_render_draft_validates_optional_slot_config_even_when_value_missing(
    fake_storage,
    fake_draft_module,
    tmp_path: Path,
    slot_update: dict,
    expected_code: str,
):
    """optional 槽位即使未传值，配置本身非法也不能被隐藏。"""
    zip_path = tmp_path / "src.zip"
    zip_path.write_bytes(b"PK\x03\x04")
    service.import_template("tpl_optional_invalid", str(zip_path))

    slot = {
        "slot_id": "video_main_video_0",
        "type": "video",
        "track_name": "main_video",
        "segment_index": 0,
        "required": False,
    }
    slot.update(slot_update)
    fake_storage["slots"]["tpl_optional_invalid"] = [slot]

    from vectcut.features.template_filling.schemas import RenderDraftRequest

    req = RenderDraftRequest(
        template_id="tpl_optional_invalid",
        slot_values={},
        output_draft_name="out",
    )

    with pytest.raises(SlotError) as exc:
        service.render_draft("tpl_optional_invalid", req)
    assert exc.value.code == expected_code


def test_render_draft_slot_config_missing_slot_id_is_structured(
    fake_storage, fake_draft_module, tmp_path: Path
):
    """slot config 缺 slot_id → S_INVALID_SLOT，而不是 KeyError。"""
    zip_path = tmp_path / "src.zip"
    zip_path.write_bytes(b"PK\x03\x04")
    service.import_template("tpl_missing_slot_id", str(zip_path))

    fake_storage["slots"]["tpl_missing_slot_id"] = [
        {"type": "video", "track_name": "main_video", "segment_index": 0}
    ]

    from vectcut.features.template_filling.schemas import RenderDraftRequest

    req = RenderDraftRequest(
        template_id="tpl_missing_slot_id",
        slot_values={},
        output_draft_name="out",
    )

    with pytest.raises(SlotError) as exc:
        service.render_draft("tpl_missing_slot_id", req)
    assert exc.value.code == "S_INVALID_SLOT"


def test_render_draft_slot_config_missing_type_is_structured(
    fake_storage, fake_draft_module, tmp_path: Path
):
    """slot config 缺 type → S_INVALID_SLOT，而不是 KeyError。"""
    zip_path = tmp_path / "src.zip"
    zip_path.write_bytes(b"PK\x03\x04")
    service.import_template("tpl_missing_type", str(zip_path))

    fake_storage["slots"]["tpl_missing_type"] = [
        {
            "slot_id": "video_main_video_0",
            "track_name": "main_video",
            "segment_index": 0,
        }
    ]

    from vectcut.features.template_filling.schemas import RenderDraftRequest

    req = RenderDraftRequest(
        template_id="tpl_missing_type",
        slot_values={
            "video_main_video_0": {
                "path": "/v.mp4",
                "duration": 5.0,
                "width": 1920,
                "height": 1080,
            }
        },
        output_draft_name="out",
    )

    with pytest.raises(SlotError) as exc:
        service.render_draft("tpl_missing_type", req)
    assert exc.value.code == "S_INVALID_SLOT"


def test_render_draft_slot_config_unknown_type_is_structured(
    fake_storage, fake_draft_module, tmp_path: Path
):
    """未知 slot type → S_INVALID_SLOT，不能静默成功生成草稿。"""
    zip_path = tmp_path / "src.zip"
    zip_path.write_bytes(b"PK\x03\x04")
    service.import_template("tpl_unknown_type", str(zip_path))

    fake_storage["slots"]["tpl_unknown_type"] = [
        {
            "slot_id": "custom_slot_0",
            "type": "custom",
            "track_name": "main_video",
            "segment_index": 0,
        }
    ]

    from vectcut.features.template_filling.schemas import RenderDraftRequest

    req = RenderDraftRequest(
        template_id="tpl_unknown_type",
        slot_values={"custom_slot_0": {"path": "/v.mp4"}},
        output_draft_name="out",
    )

    with pytest.raises(SlotError) as exc:
        service.render_draft("tpl_unknown_type", req)
    assert exc.value.code == "S_INVALID_SLOT"


def test_render_draft_segment_index_out_of_range_is_structured(
    fake_storage, fake_draft_module, monkeypatch, tmp_path: Path
):
    """slot config 的 segment_index 越界 → S_SEGMENT_NOT_FOUND。"""
    zip_path = tmp_path / "src.zip"
    zip_path.write_bytes(b"PK\x03\x04")
    service.import_template("tpl_bad_seg", str(zip_path))

    fake_storage["slots"]["tpl_bad_seg"] = [
        {
            "slot_id": "video_main_video_0",
            "type": "video",
            "track_name": "main_video",
            "segment_index": 3,
        }
    ]

    fake_track = SimpleNamespace(
        name="main_video",
        segments=[SimpleNamespace()],
    )
    monkeypatch.setattr(
        service.slot_resolver, "resolve_slot_to_track", lambda script, slot: fake_track
    )
    monkeypatch.setattr(
        service.material_builder,
        "build_video_material_from_metadata",
        lambda value: SimpleNamespace(material_id="m1"),
    )

    def _load_with_index_error(path: str):
        return _make_fake_script(
            [],
            replace_material_by_seg=lambda t, i, m: (_ for _ in ()).throw(
                IndexError("list index out of range")
            ),
        )

    monkeypatch.setattr(service.draft.Script_file, "load_template", _load_with_index_error)

    from vectcut.features.template_filling.schemas import RenderDraftRequest

    req = RenderDraftRequest(
        template_id="tpl_bad_seg",
        slot_values={
            "video_main_video_0": {
                "path": "/v.mp4",
                "duration": 5.0,
                "width": 1920,
                "height": 1080,
            }
        },
        output_draft_name="out",
    )

    with pytest.raises(SlotError) as exc:
        service.render_draft("tpl_bad_seg", req)
    assert exc.value.code == "S_SEGMENT_NOT_FOUND"
    assert exc.value.details["slot_id"] == "video_main_video_0"


@pytest.mark.parametrize(
    ("slot_update", "expected_code"),
    [
        ({}, "S_INVALID_SLOT"),
        ({"segment_index": None}, "S_INVALID_SLOT"),
        ({"segment_index": ""}, "S_INVALID_SLOT"),
        ({"segment_index": "abc"}, "S_INVALID_SLOT"),
        ({"segment_index": 1.5}, "S_INVALID_SLOT"),
        ({"segment_index": -1}, "S_SEGMENT_NOT_FOUND"),
        ({"segment_index": 99}, "S_SEGMENT_NOT_FOUND"),
    ],
)
def test_render_draft_invalid_segment_index_is_structured(
    fake_storage,
    fake_draft_module,
    monkeypatch,
    tmp_path: Path,
    slot_update: dict,
    expected_code: str,
):
    """segment_index 缺失/类型错误/越界都必须返回结构化 S_* 错误。"""
    zip_path = tmp_path / "src.zip"
    zip_path.write_bytes(b"PK\x03\x04")
    service.import_template("tpl_bad_index", str(zip_path))

    slot = {
        "slot_id": "video_main_video_0",
        "type": "video",
        "track_name": "main_video",
        "segment_index": 0,
    }
    if slot_update:
        slot.update(slot_update)
    else:
        slot.pop("segment_index")
    fake_storage["slots"]["tpl_bad_index"] = [slot]

    fake_track = SimpleNamespace(name="main_video", segments=[SimpleNamespace()])
    monkeypatch.setattr(
        service.slot_resolver, "resolve_slot_to_track", lambda script, slot: fake_track
    )
    monkeypatch.setattr(
        service.material_builder,
        "build_video_material_from_metadata",
        lambda value: SimpleNamespace(material_id="m1"),
    )

    from vectcut.features.template_filling.schemas import RenderDraftRequest

    req = RenderDraftRequest(
        template_id="tpl_bad_index",
        slot_values={
            "video_main_video_0": {
                "path": "/v.mp4",
                "duration": 5.0,
                "width": 1920,
                "height": 1080,
            }
        },
        output_draft_name="out",
    )

    with pytest.raises(SlotError) as exc:
        service.render_draft("tpl_bad_index", req)
    assert exc.value.code == expected_code


def test_render_draft_video_slot_success(
    fake_storage, fake_draft_module, monkeypatch, tmp_path: Path
):
    """video 槽位替换成功：mock slot_resolver + material_builder + replace_material_by_seg。"""
    zip_path = tmp_path / "src.zip"
    zip_path.write_bytes(b"PK\x03\x04")
    service.import_template("tpl_r3", str(zip_path))

    fake_storage["slots"]["tpl_r3"] = [
        {"slot_id": "video_main_video_0", "type": "video",
         "track_name": "main_video", "segment_index": 0}
    ]

    # mock slot_resolver 返回 fake track
    fake_track = SimpleNamespace(name="main_video", segments=[SimpleNamespace()])
    monkeypatch.setattr(
        service.slot_resolver, "resolve_slot_to_track", lambda script, slot: fake_track
    )
    # mock material_builder
    fake_mat = SimpleNamespace(material_id="m1")
    monkeypatch.setattr(
        service.material_builder,
        "build_video_material_from_metadata",
        lambda value: fake_mat,
    )
    monkeypatch.setattr(
        service.material_builder,
        "build_audio_material_from_metadata",
        lambda value: fake_mat,
    )
    # mock script.replace_material_by_seg — 通过自定义 load_template 返回带记录的 script
    replace_calls: List[Any] = []

    def _load_with_replace(path: str):
        return _make_fake_script(
            [],
            replace_material_by_seg=lambda t, i, m: replace_calls.append((t, i, m)),
        )

    monkeypatch.setattr(service.draft.Script_file, "load_template", _load_with_replace)

    from vectcut.features.template_filling.schemas import RenderDraftRequest

    req = RenderDraftRequest(
        template_id="tpl_r3",
        slot_values={"video_main_video_0": {
            "path": "/v.mp4", "duration": 5.0, "width": 1920, "height": 1080,
        }},
        output_draft_name="out",
    )
    resp = service.render_draft("tpl_r3", req)

    assert isinstance(resp, RenderDraftResponse)
    assert resp.draft_id.startswith("draft_")
    assert resp.download_url == f"/api/template/download/{resp.draft_id}"
    assert len(replace_calls) == 1
    # state 中应当有 zip
    assert resp.draft_id in fake_storage["drafts"]


def test_render_draft_subtitle_skip_with_warning(
    fake_storage, fake_draft_module, tmp_path: Path
):
    """subtitle 槽位：MVP 跳过替换，加入 warning。"""
    zip_path = tmp_path / "src.zip"
    zip_path.write_bytes(b"PK\x03\x04")
    service.import_template("tpl_r4", str(zip_path))

    fake_storage["slots"]["tpl_r4"] = [
        {"slot_id": "subtitle_sub_0", "type": "subtitle",
         "track_name": "subtitle_track", "segment_index": 0}
    ]

    from vectcut.features.template_filling.schemas import RenderDraftRequest

    req = RenderDraftRequest(
        template_id="tpl_r4",
        slot_values={"subtitle_sub_0": {"slot_id": "subtitle_sub_0",
                                         "srt_content": "1\n00:00:01,000 --> 00:00:02,000\nhi\n"}},
        output_draft_name="out",
    )
    resp = service.render_draft("tpl_r4", req)

    assert isinstance(resp, RenderDraftResponse)
    assert any("字幕" in w for w in resp.warnings)
    assert resp.draft_id in fake_storage["drafts"]


@pytest.mark.parametrize(
    ("slot_update", "expected_code"),
    [
        ({"track_name": None}, "S_INVALID_SLOT"),
        ({}, "S_INVALID_SLOT"),
        ({"segment_index": 99}, "S_SEGMENT_NOT_FOUND"),
    ],
)
def test_render_draft_validates_subtitle_slot_config_before_warning(
    fake_storage,
    fake_draft_module,
    tmp_path: Path,
    slot_update: dict,
    expected_code: str,
):
    """subtitle 虽暂不替换，也必须先校验 track_name 和 segment_index。"""
    zip_path = tmp_path / "src.zip"
    zip_path.write_bytes(b"PK\x03\x04")
    service.import_template("tpl_subtitle_invalid", str(zip_path))

    slot = {
        "slot_id": "subtitle_sub_0",
        "type": "subtitle",
        "track_name": "subtitle_track",
        "segment_index": 0,
    }
    if slot_update:
        slot.update(slot_update)
    else:
        slot.pop("segment_index")
    fake_storage["slots"]["tpl_subtitle_invalid"] = [slot]

    from vectcut.features.template_filling.schemas import RenderDraftRequest

    req = RenderDraftRequest(
        template_id="tpl_subtitle_invalid",
        slot_values={
            "subtitle_sub_0": {
                "slot_id": "subtitle_sub_0",
                "srt_content": "1\n00:00:01,000 --> 00:00:02,000\nhi\n",
            }
        },
        output_draft_name="out",
    )

    with pytest.raises(SlotError) as exc:
        service.render_draft("tpl_subtitle_invalid", req)
    assert exc.value.code == expected_code


def test_render_draft_cover_slot_skip_with_warning(
    fake_storage, fake_draft_module, tmp_path: Path
):
    """cover_image / cover_title 槽位：MVP 跳过替换，加入 warning。"""
    zip_path = tmp_path / "src.zip"
    zip_path.write_bytes(b"PK\x03\x04")
    service.import_template("tpl_r5", str(zip_path))

    fake_storage["slots"]["tpl_r5"] = [
        {"slot_id": "cover_img_0", "type": "cover_image",
         "track_name": "main_video", "segment_index": 0}
    ]

    from vectcut.features.template_filling.schemas import RenderDraftRequest

    req = RenderDraftRequest(
        template_id="tpl_r5",
        slot_values={"cover_img_0": {"slot_id": "cover_img_0", "text": "x"}},
        output_draft_name="out",
    )
    resp = service.render_draft("tpl_r5", req)
    assert any("封面" in w for w in resp.warnings)


@pytest.mark.parametrize(
    ("slot", "expected_code"),
    [
        (
            {
                "slot_id": "cover_img_0",
                "type": "cover_image",
                "track_name": "missing_video",
                "segment_index": 0,
            },
            "S_TRACK_NOT_FOUND",
        ),
        (
            {
                "slot_id": "cover_img_0",
                "type": "cover_image",
                "track_name": "main_video",
                "segment_index": 99,
            },
            "S_SEGMENT_NOT_FOUND",
        ),
        (
            {
                "slot_id": "cover_title_0",
                "type": "cover_title",
                "track_name": "subtitle_track",
                "segment_index": -1,
            },
            "S_SEGMENT_NOT_FOUND",
        ),
    ],
)
def test_render_draft_validates_cover_track_and_segment_before_warning(
    fake_storage,
    fake_draft_module,
    tmp_path: Path,
    slot: dict,
    expected_code: str,
):
    """cover 槽位 warning 前也必须校验轨道存在和 segment_index 越界。"""
    zip_path = tmp_path / "src.zip"
    zip_path.write_bytes(b"PK\x03\x04")
    service.import_template("tpl_cover_bounds", str(zip_path))
    fake_storage["slots"]["tpl_cover_bounds"] = [slot]

    from vectcut.features.template_filling.schemas import RenderDraftRequest

    req = RenderDraftRequest(
        template_id="tpl_cover_bounds",
        slot_values={slot["slot_id"]: {"slot_id": slot["slot_id"], "text": "x"}},
        output_draft_name="out",
    )

    with pytest.raises(SlotError) as exc:
        service.render_draft("tpl_cover_bounds", req)
    assert exc.value.code == expected_code


@pytest.mark.parametrize("slot_type", ["cover_image", "cover_title"])
@pytest.mark.parametrize("missing_key", ["track_name", "segment_index"])
def test_render_draft_validates_cover_slot_config_before_warning(
    fake_storage,
    fake_draft_module,
    tmp_path: Path,
    slot_type: str,
    missing_key: str,
):
    """cover 槽位虽暂不替换，也必须先校验基础 slot config。"""
    zip_path = tmp_path / "src.zip"
    zip_path.write_bytes(b"PK\x03\x04")
    service.import_template("tpl_cover_invalid", str(zip_path))

    slot = {
        "slot_id": f"{slot_type}_0",
        "type": slot_type,
        "track_name": "cover",
        "segment_index": 0,
    }
    slot.pop(missing_key)
    fake_storage["slots"]["tpl_cover_invalid"] = [slot]

    from vectcut.features.template_filling.schemas import RenderDraftRequest

    req = RenderDraftRequest(
        template_id="tpl_cover_invalid",
        slot_values={slot["slot_id"]: {"slot_id": slot["slot_id"], "text": "x"}},
        output_draft_name="out",
    )

    with pytest.raises(SlotError) as exc:
        service.render_draft("tpl_cover_invalid", req)
    assert exc.value.code == "S_INVALID_SLOT"


# ─── _scan_slots_from_template ─────────────────────────────────────────────


def test_scan_slots_classifies_track_types():
    """直接验证 _scan_slots_from_template 的轨道分类逻辑。"""
    tracks = [
        _make_track(_FakeTrackType("video"), "main_video", seg_count=2),
        _make_track(_FakeTrackType("audio"), "bgm_track", seg_count=1),
        _make_track(_FakeTrackType("audio"), "voiceover", seg_count=1),
        _make_track(_FakeTrackType("text"), "lyrics", seg_count=1),
        _make_track(_FakeTrackType("sticker"), "skip_me", seg_count=1),
    ]
    script = _make_fake_script(tracks)

    slots = service._scan_slots_from_template(script)

    types = [s["type"] for s in slots]
    # video × 2 seg + bgm(bgm_track) × 1 + audio(voiceover) × 1 + subtitle(lyrics) × 1 = 5
    assert types.count("video") == 2
    assert types.count("bgm") == 1
    assert types.count("audio") == 1
    assert types.count("subtitle") == 1
    # sticker 类型应当被跳过
    assert "sticker" not in types

    # slot_id 格式
    video_slot = next(s for s in slots if s["type"] == "video")
    assert video_slot["slot_id"] == "video_main_video_0"
    assert video_slot["segment_index"] == 0
    assert video_slot["name"] == "video槽位0"

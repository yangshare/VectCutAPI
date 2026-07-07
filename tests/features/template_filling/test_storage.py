"""storage.py 单元测试：覆盖 template_filling 文件存取层。

monkeypatch storage 模块绑定的 load_config 引用，让三个目录指向 tmp_path 子目录。
"""

from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from vectcut.core.errors import SlotError, TemplateError, VectCutError
from vectcut.features.template_filling import storage


# ─── 公共 fixture：把 storage.load_config 替换成返回 tmp 目录的 fake ─────────


@pytest.fixture
def fake_cfg(tmp_path: Path, monkeypatch):
    cfg = SimpleNamespace(
        template_folder=str(tmp_path / "templates"),
        template_config_folder=str(tmp_path / "template_configs"),
        generated_draft_folder=str(tmp_path / "generated_drafts"),
        max_template_zip_mb=50,
    )
    monkeypatch.setattr(
        "vectcut.features.template_filling.storage.load_config",
        lambda: cfg,
    )
    return cfg


# ─── save_template_zip ─────────────────────────────────────────────────────


def test_save_template_zip(fake_cfg, tmp_path: Path):
    src = tmp_path / "src.zip"
    src.write_bytes(b"PK\x03\x04dummy")

    stored = storage.save_template_zip("t1", str(src))

    assert Path(stored) == Path(fake_cfg.template_folder) / "t1.zip"
    assert Path(stored).is_file()
    assert Path(stored).read_bytes() == src.read_bytes()


# ─── extract_template_zip ──────────────────────────────────────────────────


def _make_zip_with_file(zip_path: Path, inner_name: str, content: bytes) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(inner_name, content)


def test_extract_template_zip(fake_cfg, tmp_path: Path):
    src_zip = tmp_path / "src.zip"
    _make_zip_with_file(src_zip, "draft_content.json", b'{"k":1}')

    extracted = storage.extract_template_zip("t2", str(src_zip))

    assert Path(extracted) == Path(fake_cfg.template_folder) / "t2"
    assert (Path(extracted) / "draft_content.json").read_bytes() == b'{"k":1}'
    # 同步保留 zip 副本
    assert (Path(fake_cfg.template_folder) / "t2.zip").is_file()


def test_extract_template_zip_overwrites_existing(fake_cfg, tmp_path: Path):
    src_zip = tmp_path / "src.zip"
    _make_zip_with_file(src_zip, "draft_content.json", b'{"new":1}')

    extract_dir = Path(fake_cfg.template_folder) / "t3"
    extract_dir.mkdir(parents=True)
    (extract_dir / "stale.txt").write_text("old", encoding="utf-8")

    extracted = storage.extract_template_zip("t3", str(src_zip))

    # 旧文件被清理
    assert not (extract_dir / "stale.txt").exists()
    assert (extract_dir / "draft_content.json").read_bytes() == b'{"new":1}'


def test_extract_template_zip_rejects_oversized_uncompressed_entry(
    fake_cfg, tmp_path: Path, monkeypatch
):
    """ZIP 解压前应按 uncompressed file_size 拦截超限 entry。"""
    fake_cfg.max_template_zip_mb = 0
    src_zip = tmp_path / "tiny.zip"
    src_zip.write_bytes(b"fake zip")
    extracted = False

    class _FakeZipFile:
        def __init__(self, path):
            self.path = path

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def infolist(self):
            return [
                SimpleNamespace(
                    filename="draft_content.json",
                    file_size=1,
                    is_dir=lambda: False,
                )
            ]

        def extractall(self, target):
            nonlocal extracted
            extracted = True

    monkeypatch.setattr(storage.zipfile, "ZipFile", _FakeZipFile)

    with pytest.raises(TemplateError) as exc:
        storage.extract_template_zip("t_big", str(src_zip))

    assert exc.value.code == "T_TOO_LARGE"
    assert extracted is False
    assert not (Path(fake_cfg.template_folder) / "t_big").exists()


def test_extract_template_zip_rejects_path_traversal_entry(fake_cfg, tmp_path: Path):
    """真实 ZIP 中的 ../ 路径穿越应被拒绝，且不得写到外部。"""
    src_zip = tmp_path / "traversal.zip"
    evil_path = Path(fake_cfg.template_folder) / "evil.txt"
    _make_zip_with_file(src_zip, "../evil.txt", b"evil")

    with pytest.raises(TemplateError) as exc:
        storage.extract_template_zip("t_traversal", str(src_zip))

    assert exc.value.code == "T_INVALID_ZIP"
    assert not evil_path.exists()
    assert not (Path(fake_cfg.template_folder) / "t_traversal").exists()


def test_extract_template_zip_rejects_absolute_path_entry(fake_cfg, tmp_path: Path):
    """真实 ZIP 中的绝对路径 entry 应被拒绝。"""
    src_zip = tmp_path / "absolute.zip"
    _make_zip_with_file(src_zip, "/tmp/evil.txt", b"evil")

    with pytest.raises(TemplateError) as exc:
        storage.extract_template_zip("t_absolute", str(src_zip))

    assert exc.value.code == "T_INVALID_ZIP"
    assert not (Path(fake_cfg.template_folder) / "t_absolute").exists()


@pytest.mark.parametrize("inner_name", ["C:/evil.txt", r"C:\evil.txt"])
def test_extract_template_zip_rejects_windows_absolute_path_entry(
    fake_cfg, tmp_path: Path, inner_name
):
    """ZIP entry 中的 Windows 绝对路径在 Linux/Docker 下也应被拒绝。"""
    src_zip = tmp_path / "windows_absolute.zip"
    _make_zip_with_file(src_zip, inner_name, b"evil")

    with pytest.raises(TemplateError) as exc:
        storage.extract_template_zip("t_windows_absolute", str(src_zip))

    assert exc.value.code == "T_INVALID_ZIP"
    template_root = Path(fake_cfg.template_folder)
    assert not (template_root / "t_windows_absolute").exists()
    assert not (template_root / "t_windows_absolute.zip").exists()
    assert not any(
        path.name.startswith("t_windows_absolute.tmp-")
        for path in template_root.glob("t_windows_absolute.tmp-*")
    )


def test_extract_template_zip_rejects_total_uncompressed_size(fake_cfg, tmp_path: Path):
    """多个小 entry 的展开总量超过上限时应拒绝。"""
    fake_cfg.max_template_zip_mb = 0
    src_zip = tmp_path / "total.zip"
    with zipfile.ZipFile(src_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("a.txt", b"a")
        zf.writestr("b.txt", b"b")

    with pytest.raises(TemplateError) as exc:
        storage.extract_template_zip("t_total", str(src_zip))

    assert exc.value.code == "T_TOO_LARGE"
    assert not (Path(fake_cfg.template_folder) / "t_total").exists()


def test_extract_template_zip_rejects_too_many_files(fake_cfg, tmp_path: Path, monkeypatch):
    """文件数量超过上限时应拒绝。"""
    monkeypatch.setattr(storage, "_MAX_TEMPLATE_ZIP_FILES", 1)
    src_zip = tmp_path / "many.zip"
    with zipfile.ZipFile(src_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("a.txt", b"a")
        zf.writestr("b.txt", b"b")

    with pytest.raises(TemplateError) as exc:
        storage.extract_template_zip("t_many", str(src_zip))

    assert exc.value.code == "T_TOO_LARGE"
    assert not (Path(fake_cfg.template_folder) / "t_many").exists()


def test_extract_template_zip_cleans_extract_dir_after_bad_zip(fake_cfg, tmp_path: Path):
    """BadZipFile 后应清理解包目录。"""
    src_zip = tmp_path / "bad.zip"
    src_zip.write_bytes(b"not a zip")

    with pytest.raises(TemplateError) as exc:
        storage.extract_template_zip("t_bad", str(src_zip))

    assert exc.value.code == "T_INVALID_ZIP"
    assert not (Path(fake_cfg.template_folder) / "t_bad").exists()


def _seed_existing_template(fake_cfg, template_id: str) -> tuple[Path, Path]:
    extract_dir = Path(fake_cfg.template_folder) / template_id
    extract_dir.mkdir(parents=True, exist_ok=True)
    (extract_dir / "draft_content.json").write_text('{"old": true}', encoding="utf-8")
    stored_zip = Path(fake_cfg.template_folder) / f"{template_id}.zip"
    _make_zip_with_file(stored_zip, "draft_content.json", b'{"old": true}')
    return extract_dir, stored_zip


@pytest.mark.parametrize(
    "bad_zip_kind, expected_code",
    [
        ("bad_zip", "T_INVALID_ZIP"),
        ("path_traversal", "T_INVALID_ZIP"),
        ("too_large", "T_TOO_LARGE"),
    ],
)
def test_extract_template_zip_failure_preserves_existing_template(
    fake_cfg, tmp_path: Path, bad_zip_kind, expected_code
):
    """坏 ZIP / 非法 entry / 超限失败时不得覆盖或删除已有模板。"""
    template_id = "t_existing"
    extract_dir, stored_zip = _seed_existing_template(fake_cfg, template_id)
    old_zip_bytes = stored_zip.read_bytes()

    src_zip = tmp_path / f"bad_{expected_code}.zip"
    if bad_zip_kind == "bad_zip":
        src_zip.write_bytes(b"not a zip")
    elif bad_zip_kind == "path_traversal":
        _make_zip_with_file(src_zip, "../evil.txt", b"evil")
    else:
        fake_cfg.max_template_zip_mb = 0
        with zipfile.ZipFile(src_zip, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("draft_content.json", b"x")

    with pytest.raises(TemplateError) as exc:
        storage.extract_template_zip(template_id, str(src_zip))

    assert exc.value.code == expected_code
    assert (extract_dir / "draft_content.json").read_text(encoding="utf-8") == '{"old": true}'
    assert stored_zip.read_bytes() == old_zip_bytes


def test_commit_staged_template_rolls_back_when_zip_replace_fails(
    fake_cfg, tmp_path: Path, monkeypatch
):
    """正式 zip 替换失败时应恢复旧目录和旧 zip，不留下半提交的新模板。"""
    template_id = "t_commit_rollback"
    template_root = Path(fake_cfg.template_folder)
    final_dir = template_root / template_id
    final_zip = template_root / f"{template_id}.zip"
    final_dir.mkdir(parents=True)
    (final_dir / "draft_content.json").write_text('{"old": true}', encoding="utf-8")
    _make_zip_with_file(final_zip, "draft_content.json", b'{"old": true}')
    old_zip_bytes = final_zip.read_bytes()

    staging_dir = template_root / f"{template_id}.tmp-stage"
    staging_zip = template_root / f"{template_id}.tmp-stage.zip"
    staging_dir.mkdir(parents=True)
    (staging_dir / "draft_content.json").write_text('{"new": true}', encoding="utf-8")
    _make_zip_with_file(staging_zip, "draft_content.json", b'{"new": true}')
    stage = storage.StagedTemplateZip(
        template_id=template_id,
        extract_dir=staging_dir,
        zip_path=staging_zip,
        final_extract_dir=final_dir,
        final_zip_path=final_zip,
    )

    def _fail_zip_replace(src, dst):
        if Path(src) == staging_zip and Path(dst) == final_zip:
            raise OSError("zip replace failed")
        return original_replace(src, dst)

    original_replace = storage.os.replace
    monkeypatch.setattr(storage.os, "replace", _fail_zip_replace)

    with pytest.raises(OSError, match="zip replace failed"):
        storage.commit_staged_template(stage)

    assert (final_dir / "draft_content.json").read_text(encoding="utf-8") == '{"old": true}'
    assert final_zip.read_bytes() == old_zip_bytes


@pytest.mark.parametrize("failure_point", ["backup_dir", "backup_zip"])
def test_commit_staged_template_preserves_existing_when_backup_fails(
    fake_cfg, tmp_path: Path, monkeypatch, failure_point: str
):
    """旧模板备份阶段失败时不得删除尚未成功备份的正式目录或 zip。"""
    template_id = f"t_commit_backup_{failure_point}"
    template_root = Path(fake_cfg.template_folder)
    final_dir = template_root / template_id
    final_zip = template_root / f"{template_id}.zip"
    final_dir.mkdir(parents=True)
    (final_dir / "draft_content.json").write_text('{"old": true}', encoding="utf-8")
    _make_zip_with_file(final_zip, "draft_content.json", b'{"old": true}')
    old_zip_bytes = final_zip.read_bytes()

    staging_dir = template_root / f"{template_id}.tmp-stage"
    staging_zip = template_root / f"{template_id}.tmp-stage.zip"
    staging_dir.mkdir(parents=True)
    (staging_dir / "draft_content.json").write_text('{"new": true}', encoding="utf-8")
    _make_zip_with_file(staging_zip, "draft_content.json", b'{"new": true}')
    stage = storage.StagedTemplateZip(
        template_id=template_id,
        extract_dir=staging_dir,
        zip_path=staging_zip,
        final_extract_dir=final_dir,
        final_zip_path=final_zip,
    )

    if failure_point == "backup_dir":
        original_path_replace = Path.replace

        def _fail_backup_dir_replace(self, target):
            if self == final_dir and Path(target).name.startswith(f"{template_id}.bak-"):
                raise OSError("dir backup failed")
            return original_path_replace(self, target)

        monkeypatch.setattr(Path, "replace", _fail_backup_dir_replace)
        expected_message = "dir backup failed"
    else:
        original_replace = storage.os.replace

        def _fail_backup_zip_replace(src, dst):
            if Path(src) == final_zip and Path(dst).name.startswith(f"{template_id}.zip.bak-"):
                raise OSError("zip backup failed")
            return original_replace(src, dst)

        monkeypatch.setattr(storage.os, "replace", _fail_backup_zip_replace)
        expected_message = "zip backup failed"

    with pytest.raises(OSError, match=expected_message):
        storage.commit_staged_template(stage)

    assert (final_dir / "draft_content.json").read_text(encoding="utf-8") == '{"old": true}'
    assert final_zip.read_bytes() == old_zip_bytes


@pytest.mark.parametrize("cleanup_failure", ["dir_backup", "zip_backup"])
def test_commit_staged_template_ignores_backup_cleanup_failure_after_success(
    fake_cfg, tmp_path: Path, monkeypatch, cleanup_failure: str
):
    """新模板已安装后，旧 backup 清理失败不应让 commit 变成失败。"""
    template_id = f"t_commit_cleanup_{cleanup_failure}"
    template_root = Path(fake_cfg.template_folder)
    final_dir = template_root / template_id
    final_zip = template_root / f"{template_id}.zip"
    final_dir.mkdir(parents=True)
    (final_dir / "draft_content.json").write_text('{"old": true}', encoding="utf-8")
    _make_zip_with_file(final_zip, "draft_content.json", b'{"old": true}')

    staging_dir = template_root / f"{template_id}.tmp-stage"
    staging_zip = template_root / f"{template_id}.tmp-stage.zip"
    staging_dir.mkdir(parents=True)
    (staging_dir / "draft_content.json").write_text('{"new": true}', encoding="utf-8")
    _make_zip_with_file(staging_zip, "draft_content.json", b'{"new": true}')
    stage = storage.StagedTemplateZip(
        template_id=template_id,
        extract_dir=staging_dir,
        zip_path=staging_zip,
        final_extract_dir=final_dir,
        final_zip_path=final_zip,
    )

    if cleanup_failure == "dir_backup":
        original_rmtree = storage.shutil.rmtree

        def _fail_backup_rmtree(path):
            if Path(path).name.startswith(f"{template_id}.bak-"):
                raise OSError("backup dir cleanup failed")
            return original_rmtree(path)

        monkeypatch.setattr(storage.shutil, "rmtree", _fail_backup_rmtree)
    else:
        original_unlink = Path.unlink

        def _fail_backup_unlink(self, *args, **kwargs):
            if self.name.startswith(f"{template_id}.zip.bak-"):
                raise OSError("backup zip cleanup failed")
            return original_unlink(self, *args, **kwargs)

        monkeypatch.setattr(Path, "unlink", _fail_backup_unlink)

    committed_path = storage.commit_staged_template(stage)

    assert committed_path == str(final_dir)
    assert (final_dir / "draft_content.json").read_text(encoding="utf-8") == '{"new": true}'
    with zipfile.ZipFile(final_zip) as zf:
        assert zf.read("draft_content.json") == b'{"new": true}'


def test_template_lock_times_out_for_same_template_id(fake_cfg):
    """同一 template_id 的第二个跨进程文件锁获取应结构化超时。"""
    with storage.template_lock("tpl_lock", timeout_seconds=1):
        with pytest.raises(VectCutError) as exc:
            with storage.template_lock("tpl_lock", timeout_seconds=0):
                pass
    assert exc.value.code == "T_LOCK_TIMEOUT"


def test_template_lock_allows_different_template_ids(fake_cfg):
    """不同 template_id 的锁文件不同，不应互相阻塞。"""
    with storage.template_lock("tpl_lock_a", timeout_seconds=1):
        with storage.template_lock("tpl_lock_b", timeout_seconds=1):
            assert True


def test_template_lock_sanitizes_lock_file_name(fake_cfg):
    """helper 自身也要避免未校验 template_id 影响 .locks 目录外路径。"""
    with storage.template_lock("../tpl_lock", timeout_seconds=1):
        pass

    lock_dir = Path(fake_cfg.template_folder) / ".locks"
    assert lock_dir.is_dir()
    assert not (Path(fake_cfg.template_folder).parent / "tpl_lock.lock").exists()


def test_template_lock_recovers_stale_lock_file(fake_cfg):
    lock_dir = Path(fake_cfg.template_folder) / ".locks"
    lock_dir.mkdir(parents=True)
    lock_path = lock_dir / storage._safe_template_lock_name("tpl_stale")
    lock_path.write_text(
        json.dumps({
            "pid": 99999999,
            "host": "old-host",
            "created_at": 0,
            "owner": "old-owner",
        }),
        encoding="utf-8",
    )

    with storage.template_lock("tpl_stale", timeout_seconds=0, stale_seconds=1):
        assert lock_path.exists()

    assert not lock_path.exists()


def test_template_lock_release_does_not_delete_different_owner(fake_cfg):
    lock_dir = Path(fake_cfg.template_folder) / ".locks"
    lock_path = lock_dir / storage._safe_template_lock_name("tpl_owner")

    with storage.template_lock("tpl_owner", timeout_seconds=1):
        lock_path.write_text(
            json.dumps({
                "pid": 123456,
                "host": "other-host",
                "created_at": 999999,
                "owner": "other-owner",
            }),
            encoding="utf-8",
        )

    assert lock_path.exists()
    assert "other-owner" in lock_path.read_text(encoding="utf-8")
    lock_path.unlink()


# ─── get_template_draft_content_path ───────────────────────────────────────


def test_get_template_draft_content_path_success(fake_cfg):
    extract_dir = Path(fake_cfg.template_folder) / "t4"
    extract_dir.mkdir(parents=True)
    (extract_dir / "draft_content.json").write_text("{}", encoding="utf-8")

    p = storage.get_template_draft_content_path("t4")
    assert Path(p).name == "draft_content.json"


def test_get_template_draft_content_path_falls_back_to_draft_info(fake_cfg):
    extract_dir = Path(fake_cfg.template_folder) / "t5"
    extract_dir.mkdir(parents=True)
    (extract_dir / "draft_info.json").write_text("{}", encoding="utf-8")

    p = storage.get_template_draft_content_path("t5")
    assert Path(p).name == "draft_info.json"


def test_get_template_draft_content_path_not_found(fake_cfg):
    extract_dir = Path(fake_cfg.template_folder) / "t6"
    extract_dir.mkdir(parents=True)  # 目录存在但无 json

    with pytest.raises(TemplateError):
        storage.get_template_draft_content_path("t6")


# ─── save / load_slot_config ───────────────────────────────────────────────


def test_save_and_load_slot_config(fake_cfg):
    slots = [
        {"slot_id": "s1", "track_kind": "video", "segment_index": 0},
        {"slot_id": "s2", "track_kind": "text", "segment_index": 1},
    ]
    storage.save_slot_config("t7", slots)

    cfg_file = Path(fake_cfg.template_config_folder) / "t7_slots.json"
    assert cfg_file.is_file()
    # 中文不转义
    raw = cfg_file.read_text(encoding="utf-8")
    assert "\\u" not in raw
    assert '"template_id": "t7"' in raw

    loaded = storage.load_slot_config("t7")
    assert loaded == slots


def test_save_slot_config_replace_failure_preserves_existing_config(
    fake_cfg, monkeypatch
):
    storage.save_slot_config("t_atomic", [{"slot_id": "old"}])
    cfg_file = Path(fake_cfg.template_config_folder) / "t_atomic_slots.json"
    old_content = cfg_file.read_text(encoding="utf-8")

    original_replace = storage.os.replace

    def _fail_slot_config_replace(src, dst):
        if Path(dst) == cfg_file:
            raise OSError("atomic replace failed")
        return original_replace(src, dst)

    monkeypatch.setattr(storage.os, "replace", _fail_slot_config_replace)

    with pytest.raises(OSError, match="atomic replace failed"):
        storage.save_slot_config("t_atomic", [{"slot_id": "new"}])

    assert cfg_file.read_text(encoding="utf-8") == old_content
    assert storage.load_slot_config("t_atomic") == [{"slot_id": "old"}]
    assert not list(Path(fake_cfg.template_config_folder).glob("t_atomic_slots.*.tmp"))


def test_load_slot_config_not_found(fake_cfg):
    with pytest.raises(SlotError):
        storage.load_slot_config("nope")


# ─── save_generated_draft_zip ──────────────────────────────────────────────


def test_save_generated_draft_zip(fake_cfg, tmp_path: Path):
    src_dir = tmp_path / "draft_src"
    (src_dir / "sub").mkdir(parents=True)
    (src_dir / "draft_content.json").write_text('{"a":1}', encoding="utf-8")
    (src_dir / "sub" / "bin.dat").write_bytes(b"\x00\x01\x02")

    zip_path = storage.save_generated_draft_zip("d1", str(src_dir))

    assert Path(zip_path) == Path(fake_cfg.generated_draft_folder) / "d1.zip"
    assert Path(zip_path).is_file()

    # 解压回校验内容
    out = tmp_path / "unzip_out"
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(out)
    assert (out / "draft_content.json").read_text(encoding="utf-8") == '{"a":1}'
    assert (out / "sub" / "bin.dat").read_bytes() == b"\x00\x01\x02"


# ─── get_generated_draft_zip_path ──────────────────────────────────────────


def test_get_generated_draft_zip_path(fake_cfg):
    # 不存在
    assert storage.get_generated_draft_zip_path("d2") is None

    # 创建后返回路径
    folder = Path(fake_cfg.generated_draft_folder)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "d2.zip").write_bytes(b"PK\x03\x04")

    p = storage.get_generated_draft_zip_path("d2")
    assert p is not None
    assert Path(p) == folder / "d2.zip"

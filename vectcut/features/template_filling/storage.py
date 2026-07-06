"""template_filling 存储层：模板 ZIP / 槽位配置 JSON / 生成草稿 ZIP 的文件存取。

设计要点：
- 配置在每个函数内部现取（``cfg = load_config()``），不缓存，以使运行时配置变更即时生效。
- 三个目录由各函数在使用前 mkdir，无需启动时预建。
- 不依赖 ``getattr`` 兜底默认 —— Settings 已声明三个字段并保证存在。
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
import os
import shutil
import time
import uuid
import zipfile
from pathlib import Path
import re
from typing import Iterator, Optional

from vectcut.core.config import load_config
from vectcut.core.errors import VectCutError
from vectcut.core.errors import make_error

_MAX_TEMPLATE_ZIP_FILES = 10_000
_WINDOWS_ABSOLUTE_ZIP_MEMBER_RE = re.compile(r"^[A-Za-z]:[\\/]")
_TEMPLATE_LOCK_POLL_SECONDS = 0.05


@dataclass(frozen=True)
class StagedTemplateZip:
    template_id: str
    extract_dir: Path
    zip_path: Path
    final_extract_dir: Path
    final_zip_path: Path


def _ensure_parent(path: str | os.PathLike) -> Path:
    """确保目标文件的父目录存在，返回 Path。"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _safe_template_lock_name(template_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", str(template_id)).strip("_") or "template"
    digest = hashlib.sha256(str(template_id).encode("utf-8")).hexdigest()[:12]
    return f"{safe[:80]}-{digest}.lock"


@contextmanager
def template_lock(template_id: str, timeout_seconds: float = 30.0) -> Iterator[None]:
    """Acquire a cross-process per-template lock using atomic lock-file creation."""
    cfg = load_config()
    lock_dir = Path(cfg.template_folder) / ".locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_path = lock_dir / _safe_template_lock_name(template_id)
    deadline = time.monotonic() + timeout_seconds
    fd: int | None = None

    while True:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, f"pid={os.getpid()}\n".encode("utf-8"))
            break
        except FileExistsError as exc:
            remaining = deadline - time.monotonic()
            if timeout_seconds <= 0 or remaining <= 0:
                raise TimeoutError(
                    f"Timed out acquiring template lock for {template_id}"
                ) from exc
            time.sleep(min(_TEMPLATE_LOCK_POLL_SECONDS, remaining))

    try:
        yield
    finally:
        if fd is not None:
            os.close(fd)
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def save_template_zip(template_id: str, zip_path: str) -> str:
    """保存上传的模板 ZIP 到 ``template_folder/{template_id}.zip``，返回存储路径。"""
    cfg = load_config()
    dst = _ensure_parent(Path(cfg.template_folder) / f"{template_id}.zip")
    shutil.copyfile(zip_path, dst)
    return str(dst)


def _validate_zip_member_path(extract_dir: Path, member_name: str) -> None:
    if _is_absolute_zip_member_name(member_name):
        raise make_error(
            "T_INVALID_ZIP",
            "ZIP 文件包含非法路径",
            details={"entry": member_name},
        )

    target = (extract_dir / member_name).resolve()
    root = extract_dir.resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise make_error(
            "T_INVALID_ZIP",
            "ZIP 文件包含非法路径",
            details={"entry": member_name},
        ) from exc


def _is_absolute_zip_member_name(member_name: str) -> bool:
    if not member_name:
        return False
    if _WINDOWS_ABSOLUTE_ZIP_MEMBER_RE.match(member_name):
        return True
    return member_name.startswith(("/", "\\\\", "//", "\\"))


def _validate_template_zip_members(
    zf: zipfile.ZipFile,
    extract_dir: Path,
    max_uncompressed_bytes: int,
) -> None:
    infos = zf.infolist()
    if len(infos) > _MAX_TEMPLATE_ZIP_FILES:
        raise make_error(
            "T_TOO_LARGE",
            details={
                "file_count": len(infos),
                "max_file_count": _MAX_TEMPLATE_ZIP_FILES,
            },
        )

    total_size = 0
    for info in infos:
        _validate_zip_member_path(extract_dir, info.filename)
        if callable(getattr(info, "is_dir", None)) and info.is_dir():
            continue

        file_size = int(getattr(info, "file_size", 0))
        if file_size > max_uncompressed_bytes:
            raise make_error(
                "T_TOO_LARGE",
                details={
                    "entry": info.filename,
                    "file_size": file_size,
                    "max_bytes": max_uncompressed_bytes,
                },
            )

        total_size += file_size
        if total_size > max_uncompressed_bytes:
            raise make_error(
                "T_TOO_LARGE",
                details={
                    "total_uncompressed_size": total_size,
                    "max_bytes": max_uncompressed_bytes,
                },
            )


def stage_extract_template_zip(template_id: str, uploaded_zip_path: str) -> StagedTemplateZip:
    """将模板 ZIP 解压到 staging 目录，不修改已有正式模板。"""
    cfg = load_config()
    template_root = Path(cfg.template_folder)
    template_root.mkdir(parents=True, exist_ok=True)
    stored_zip = template_root / f"{template_id}.zip"
    extract_dir = Path(cfg.template_folder) / template_id
    staging_id = uuid.uuid4().hex
    staging_zip = template_root / f"{template_id}.tmp-{staging_id}.zip"
    staging_dir = template_root / f"{template_id}.tmp-{staging_id}"
    shutil.copyfile(uploaded_zip_path, staging_zip)
    staging_dir.mkdir(parents=True, exist_ok=True)
    validated = False

    try:
        with zipfile.ZipFile(staging_zip) as zf:
            max_bytes = int(cfg.max_template_zip_mb) * 1024 * 1024
            _validate_template_zip_members(zf, staging_dir, max_bytes)
            zf.extractall(staging_dir)
            validated = True
    except zipfile.BadZipFile as exc:
        raise make_error("T_INVALID_ZIP", details={"template_id": template_id}) from exc
    except VectCutError:
        raise
    finally:
        if not validated and staging_dir.exists():
            shutil.rmtree(staging_dir)
        if not validated and staging_zip.exists():
            staging_zip.unlink()

    return StagedTemplateZip(
        template_id=template_id,
        extract_dir=staging_dir,
        zip_path=staging_zip,
        final_extract_dir=extract_dir,
        final_zip_path=stored_zip,
    )


def commit_staged_template(stage: StagedTemplateZip) -> str:
    """把已完成结构和语义校验的 staging 模板切换为正式模板。"""
    backup_id = uuid.uuid4().hex
    backup_extract_dir = stage.final_extract_dir.with_name(
        f"{stage.final_extract_dir.name}.bak-{backup_id}"
    )
    backup_zip_path = stage.final_zip_path.with_name(
        f"{stage.final_zip_path.name}.bak-{backup_id}"
    )
    backed_up_dir = False
    backed_up_zip = False
    installed_dir = False
    installed_zip = False

    try:
        if stage.final_extract_dir.exists():
            stage.final_extract_dir.replace(backup_extract_dir)
            backed_up_dir = True
        if stage.final_zip_path.exists():
            os.replace(stage.final_zip_path, backup_zip_path)
            backed_up_zip = True

        stage.extract_dir.replace(stage.final_extract_dir)
        installed_dir = True
        os.replace(stage.zip_path, stage.final_zip_path)
        installed_zip = True
    except Exception:
        if (installed_dir or backed_up_dir) and stage.final_extract_dir.exists():
            shutil.rmtree(stage.final_extract_dir)
        if (installed_zip or backed_up_zip) and stage.final_zip_path.exists():
            stage.final_zip_path.unlink()
        if backed_up_dir and backup_extract_dir.exists():
            backup_extract_dir.replace(stage.final_extract_dir)
        if backed_up_zip and backup_zip_path.exists():
            os.replace(backup_zip_path, stage.final_zip_path)
        raise
    else:
        if backup_extract_dir.exists():
            shutil.rmtree(backup_extract_dir)
        if backup_zip_path.exists():
            backup_zip_path.unlink()
    return str(stage.final_extract_dir)


def cleanup_staged_template(stage: StagedTemplateZip) -> None:
    """清理未提交的 staging 模板文件。"""
    if stage.extract_dir.exists():
        shutil.rmtree(stage.extract_dir)
    if stage.zip_path.exists():
        stage.zip_path.unlink()


def extract_template_zip(template_id: str, uploaded_zip_path: str) -> str:
    """保存并解压模板 ZIP 到 ``template_folder/{template_id}/``。

    先在 staging zip / staging 解包目录中完成结构校验和解压，成功后再替换
    正式 ``{template_id}.zip`` 和 ``{template_id}/``。
    """
    stage = stage_extract_template_zip(template_id, uploaded_zip_path)
    try:
        return commit_staged_template(stage)
    except Exception:
        cleanup_staged_template(stage)
        raise


def get_template_draft_content_path_from_dir(
    template_id: str, extract_dir: str | os.PathLike
) -> str:
    """返回指定解包目录里的 draft_content.json；缺失时回退 draft_info.json。"""
    extract_dir = Path(extract_dir)
    primary = extract_dir / "draft_content.json"
    if primary.is_file():
        return str(primary)
    fallback = extract_dir / "draft_info.json"
    if fallback.is_file():
        return str(fallback)
    raise make_error(
        "T_NO_DRAFT_CONTENT",
        f"模板 {template_id} 缺少 draft_content.json / draft_info.json",
        details={"template_id": template_id},
    )


def require_template_draft_content_path_from_dir(
    template_id: str, extract_dir: str | os.PathLike
) -> str:
    """返回指定解包目录里的 draft_content.json；模板导入语义校验不允许 fallback。"""
    extract_dir = Path(extract_dir)
    primary = extract_dir / "draft_content.json"
    if primary.is_file():
        return str(primary)
    raise make_error(
        "T_NO_DRAFT_CONTENT",
        f"模板 {template_id} 缺少 draft_content.json",
        details={"template_id": template_id},
    )


def get_template_draft_content_path(template_id: str) -> str:
    """返回模板解包目录里的 draft_content.json；缺失时回退 draft_info.json。

    两者都不存在 → TemplateError。
    """
    cfg = load_config()
    return get_template_draft_content_path_from_dir(
        template_id, Path(cfg.template_folder) / template_id
    )


def save_slot_config(template_id: str, slots: list) -> None:
    """保存槽位配置到 ``template_config_folder/{template_id}_slots.json``。"""
    cfg = load_config()
    target = _ensure_parent(
        Path(cfg.template_config_folder) / f"{template_id}_slots.json"
    )
    payload = {"template_id": template_id, "slots": slots}
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def load_slot_config(template_id: str) -> list:
    """加载槽位配置列表。文件不存在抛 SlotError。"""
    cfg = load_config()
    target = Path(cfg.template_config_folder) / f"{template_id}_slots.json"
    if not target.is_file():
        raise make_error(
            "S_NOT_FOUND",
            f"模板 {template_id} 的槽位配置不存在",
            details={"template_id": template_id},
        )
    data = json.loads(target.read_text(encoding="utf-8"))
    return data.get("slots", [])


def save_generated_draft_zip(draft_id: str, draft_folder_path: str) -> str:
    """将 ``draft_folder_path`` 整个目录打包为 ``generated_draft_folder/{draft_id}.zip``。"""
    cfg = load_config()
    dst = _ensure_parent(Path(cfg.generated_draft_folder) / f"{draft_id}.zip")
    src = Path(draft_folder_path)
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(src):
            for name in files:
                abs_path = Path(root) / name
                # arcname 用相对 src 的路径，避免打包出绝对路径前缀
                arcname = abs_path.relative_to(src).as_posix()
                zf.write(abs_path, arcname)
    return str(dst)


def get_generated_draft_zip_path(draft_id: str) -> Optional[str]:
    """返回 ``generated_draft_folder/{draft_id}.zip`` 路径；不存在返回 None。"""
    cfg = load_config()
    target = Path(cfg.generated_draft_folder) / f"{draft_id}.zip"
    if target.is_file():
        return str(target)
    return None

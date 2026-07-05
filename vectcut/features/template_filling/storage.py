"""template_filling 存储层：模板 ZIP / 槽位配置 JSON / 生成草稿 ZIP 的文件存取。

设计要点：
- 配置在每个函数内部现取（``cfg = load_config()``），不缓存，以使运行时配置变更即时生效。
- 三个目录由各函数在使用前 mkdir，无需启动时预建。
- 不依赖 ``getattr`` 兜底默认 —— Settings 已声明三个字段并保证存在。
"""

from __future__ import annotations

import json
import os
import shutil
import zipfile
from pathlib import Path
from typing import Optional

from vectcut.core.config import load_config
from vectcut.core.errors import SlotError, TemplateError


def _ensure_parent(path: str | os.PathLike) -> Path:
    """确保目标文件的父目录存在，返回 Path。"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def save_template_zip(template_id: str, zip_path: str) -> str:
    """保存上传的模板 ZIP 到 ``template_folder/{template_id}.zip``，返回存储路径。"""
    cfg = load_config()
    dst = _ensure_parent(Path(cfg.template_folder) / f"{template_id}.zip")
    shutil.copyfile(zip_path, dst)
    return str(dst)


def extract_template_zip(template_id: str, uploaded_zip_path: str) -> str:
    """保存并解压模板 ZIP 到 ``template_folder/{template_id}/``。

    - 先 copy 上传 zip 到 ``{template_id}.zip`` 留档；
    - 若同名解包目录已存在，先 rmtree 再解压，保证幂等。
    """
    cfg = load_config()
    stored_zip = _ensure_parent(Path(cfg.template_folder) / f"{template_id}.zip")
    shutil.copyfile(uploaded_zip_path, stored_zip)

    extract_dir = Path(cfg.template_folder) / template_id
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(stored_zip) as zf:
        zf.extractall(extract_dir)
    return str(extract_dir)


def get_template_draft_content_path(template_id: str) -> str:
    """返回模板解包目录里的 draft_content.json；缺失时回退 draft_info.json。

    两者都不存在 → TemplateError。
    """
    cfg = load_config()
    extract_dir = Path(cfg.template_folder) / template_id
    primary = extract_dir / "draft_content.json"
    if primary.is_file():
        return str(primary)
    fallback = extract_dir / "draft_info.json"
    if fallback.is_file():
        return str(fallback)
    raise TemplateError(
        f"模板 {template_id} 缺少 draft_content.json / draft_info.json"
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
        raise SlotError(f"模板 {template_id} 的槽位配置不存在")
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

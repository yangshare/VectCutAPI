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

from vectcut.core.errors import SlotError, TemplateError
from vectcut.features.template_filling import storage


# ─── 公共 fixture：把 storage.load_config 替换成返回 tmp 目录的 fake ─────────


@pytest.fixture
def fake_cfg(tmp_path: Path, monkeypatch):
    cfg = SimpleNamespace(
        template_folder=str(tmp_path / "templates"),
        template_config_folder=str(tmp_path / "template_configs"),
        generated_draft_folder=str(tmp_path / "generated_drafts"),
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

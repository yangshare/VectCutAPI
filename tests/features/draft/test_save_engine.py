"""_save_engine 私有实现单测：mock 下载与 ffprobe，验证保存流程产出 draft_url 与任务状态。"""
import os
import logging
from types import SimpleNamespace

import pytest

from vectcut.core import draft_store


@pytest.fixture(autouse=True)
def _clean_cache():
    draft_store.DRAFT_CACHE.clear()
    yield
    draft_store.DRAFT_CACHE.clear()


def test_save_draft_background_draft_not_in_cache_marks_failed(tmp_path, monkeypatch):
    from vectcut.features.draft import _save_engine
    from vectcut.features.draft._save_engine import task_cache

    status = _save_engine.save_draft_background("missing_id", str(tmp_path), "missing_id")
    assert status == ""
    task = task_cache.get_task_status("missing_id")
    assert task["status"] == "failed"


def test_save_draft_background_writes_profile_content(tmp_path, monkeypatch):
    from vectcut.features.draft import _save_engine
    from vectcut.features.draft._save_engine import task_cache

    # 准备一个空 draft
    draft_id, script = draft_store.get_or_create_draft(None, 1080, 1920)
    # mock ffprobe（update_media_metadata 会调 get_video_duration，但空 draft 无素材，不会调）
    monkeypatch.setattr(_save_engine, "_get_video_duration", lambda url: {"success": True, "output": 1.0, "error": None})
    # mock 下载（空 draft 无素材，不会调；但 save 流程会跑）
    monkeypatch.setattr(_save_engine, "download_file", lambda url, path: path)

    out_dir = str(tmp_path / "out")
    url = _save_engine.save_draft_background(draft_id, out_dir, draft_id)
    # 空 draft + IS_UPLOAD_DRAFT 默认 False → 不上传，draft_url 为 ""
    assert url == ""
    task = task_cache.get_task_status(draft_id)
    assert task["status"] == "completed"
    assert task["progress"] == 100
    # profile content 文件应已落盘
    assert os.path.isdir(os.path.join(out_dir, draft_id))


def test_save_draft_background_sanitizes_written_file_paths_in_logs(
    tmp_path, monkeypatch, caplog
):
    from vectcut.features.draft import _save_engine

    draft_id, _script = draft_store.get_or_create_draft(None, 1080, 1920)
    monkeypatch.setattr(_save_engine, "_get_video_duration", lambda url: {"success": True, "output": 1.0, "error": None})
    monkeypatch.setattr(_save_engine, "download_file", lambda url, path: path)

    out_dir = str(tmp_path / "private" / "exports")
    with caplog.at_level(logging.INFO, logger="flask_video_generator"):
        _save_engine.save_draft_background(draft_id, out_dir, draft_id)

    logs = caplog.text
    assert out_dir not in logs
    assert "private" not in logs
    assert ".json" in logs


def test_update_media_metadata_sanitizes_exception_text_in_logs(monkeypatch, caplog):
    from vectcut.features.draft import _save_engine

    raw_url = "https://host/path/image.png?token=SECRET_TOKEN_123456"
    raw_path = r"C:\Users\Alice\secret\image.png"

    def _raise(_url):
        raise RuntimeError(f"cannot read {raw_url} from {raw_path}")

    monkeypatch.setattr(_save_engine.imageio, "imread", _raise)
    script = SimpleNamespace(
        materials=SimpleNamespace(
            audios=[],
            videos=[
                SimpleNamespace(
                    remote_url=raw_url,
                    material_name="image.png",
                    material_type="photo",
                    width=0,
                    height=0,
                )
            ],
        ),
        tracks={},
        duration=0,
    )

    with caplog.at_level(logging.ERROR, logger="flask_video_generator"):
        _save_engine.update_media_metadata(script)

    logs = caplog.text
    assert raw_url not in logs
    assert "SECRET_TOKEN_123456" not in logs
    assert "SECRET_T" not in logs
    assert raw_path not in logs
    assert "host/path/image.png" in logs
    assert "token=%2A%2A%2A" in logs or "token=***" in logs
    assert "image.png" in logs


def test_update_media_metadata_sanitizes_material_name_paths_in_logs(caplog):
    from vectcut.features.draft import _save_engine

    raw_material_name = r"C:\Users\Alice\secret\video.mp4"
    script = SimpleNamespace(
        materials=SimpleNamespace(
            audios=[
                SimpleNamespace(
                    remote_url="",
                    material_name=raw_material_name,
                )
            ],
            videos=[],
        ),
        tracks={},
        duration=0,
    )

    with caplog.at_level(logging.WARNING, logger="flask_video_generator"):
        _save_engine.update_media_metadata(script)

    logs = caplog.text
    assert raw_material_name not in logs
    assert r"C:\Users\Alice\secret" not in logs
    assert "video.mp4" in logs


def test_build_asset_path_delegates_to_util():
    from vectcut.features.draft._save_engine import build_asset_path

    p = build_asset_path("/tmp/d", "dfd_1", "video", "v.mp4")
    assert p.endswith("v.mp4")

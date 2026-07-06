"""downloader 日志/控制台输出脱敏集成测试。"""

from __future__ import annotations

import subprocess

from requests.exceptions import RequestException

from vectcut.core import downloader


def test_download_file_local_copy_output_sanitizes_paths(tmp_path, capsys):
    """本地文件复制日志不能暴露完整素材路径。"""
    source_dir = tmp_path / "private" / "素材"
    source_dir.mkdir(parents=True)
    source = source_dir / "secret-video.mp4"
    source.write_bytes(b"video")
    target = tmp_path / "output" / "secret-video.mp4"

    assert downloader.download_file(str(source), str(target)) is True

    output = capsys.readouterr().out
    assert str(source) not in output
    assert str(target) not in output
    assert "private" not in output
    assert "secret-video.mp4" in output


def test_download_file_failure_output_sanitizes_url_query(monkeypatch, capsys):
    """下载失败日志可保留 host/path，但不能暴露完整 query token。"""
    raw_url = "https://cdn.example.com/media/video.mp4?token=abcdef1234567890&user=bob"

    def _raise(*args, **kwargs):
        raise RequestException("boom")

    monkeypatch.setattr(downloader.requests, "get", _raise)

    assert downloader.download_file(raw_url, "video.mp4", max_retries=1) is False

    output = capsys.readouterr().out
    assert raw_url not in output
    assert "abcdef1234567890" not in output
    assert "abcdef12" not in output
    assert "cdn.example.com/media/video.mp4" in output
    assert "token=%2A%2A%2A" in output or "token=***" in output


def test_download_file_failure_output_sanitizes_non_url_source_path(monkeypatch, capsys):
    """下载失败尾部日志对非 URL 本地源路径也必须脱敏。"""
    raw_source = "/home/alice/private/video.mp4"

    def _raise(*args, **kwargs):
        raise RequestException("boom")

    monkeypatch.setattr(downloader.requests, "get", _raise)

    assert downloader.download_file(raw_source, "video.mp4", max_retries=1) is False

    output = capsys.readouterr().out
    assert raw_source not in output
    assert "/home/alice/private" not in output
    assert "video.mp4" in output


def test_download_video_existing_file_output_sanitizes_windows_path(monkeypatch, capsys):
    """download_video 既有文件日志不能暴露完整 Windows 用户路径。"""
    draft_name = r"C:\Users\Alice\secret"
    material_name = "video.mp4"
    raw_path = r"C:\Users\Alice\secret/assets/video/video.mp4"

    monkeypatch.setattr(downloader.os.path, "exists", lambda path: path == raw_path)

    assert downloader.download_video("https://host/path/file.mp4", draft_name, material_name) == raw_path

    output = capsys.readouterr().out
    assert raw_path not in output
    assert r"C:\Users\Alice\secret" not in output
    assert "video.mp4" in output


def test_download_video_ffmpeg_error_sanitizes_url_and_path(monkeypatch):
    """ffmpeg stderr 进入异常时不能暴露完整 URL token 或本地路径。"""
    raw_url = "https://host/path/file.mp4?token=SECRET_TOKEN_123456"
    raw_path = r"C:\Users\Alice\secret\video.mp4"

    def _raise(*args, **kwargs):
        raise subprocess.CalledProcessError(
            1,
            args[0],
            stderr=f"failed {raw_url} writing {raw_path}".encode("utf-8"),
        )

    monkeypatch.setattr(downloader.subprocess, "run", _raise)

    try:
        downloader.download_video(raw_url, r"C:\Users\Alice\secret", "video.mp4")
    except Exception as exc:
        message = str(exc)
    else:
        raise AssertionError("download_video should raise on ffmpeg failure")

    assert raw_url not in message
    assert "SECRET_TOKEN_123456" not in message
    assert "SECRET_T" not in message
    assert raw_path not in message
    assert "host/path/file.mp4" in message
    assert "token=%2A%2A%2A" in message or "token=***" in message
    assert "video.mp4" in message

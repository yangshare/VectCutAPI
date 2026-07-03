"""vectcut.core.util 纯逻辑测试（迁自根 util.py，行为不变）。"""
from vectcut.core.util import (
    hex_to_rgb,
    is_windows_path,
    build_draft_asset_path,
    url_to_hash,
    generate_draft_url,
)


def test_hex_to_rgb():
    assert hex_to_rgb("#FF8800") == (1.0, 136 / 255, 0.0)


def test_is_windows_path():
    assert is_windows_path("E:\\tmp\\x") is True
    assert is_windows_path("/tmp/x") is False


def test_build_draft_asset_path():
    p = build_draft_asset_path("/df", "d1", "audio", "a.mp3")
    assert "d1" in p and "audio" in p and "a.mp3" in p


def test_url_to_hash_stable():
    h1 = url_to_hash("https://x/y.mp4")
    h2 = url_to_hash("https://x/y.mp4")
    assert h1 == h2 and len(h1) == 16


def test_generate_draft_url_contains_id():
    assert "d1" in generate_draft_url("d1")

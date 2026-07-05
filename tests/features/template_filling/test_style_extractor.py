"""style_extractor 测试：验证默认值 + 不抛异常。"""

from __future__ import annotations

from types import SimpleNamespace

from vectcut.features.template_filling.style_extractor import (
    extract_subtitle_style_from_track,
)


class TestExtractSubtitleStyle:
    def test_none_track_returns_default(self):
        track = SimpleNamespace(segments=[])
        result = extract_subtitle_style_from_track(track)
        assert result["border"] is None
        assert result["font"] is None
        assert "text_style" in result
        assert "clip_settings" in result

    def test_track_without_segments_returns_default(self):
        track = SimpleNamespace()
        # 没有 segments 属性
        result = extract_subtitle_style_from_track(track)
        assert result["border"] is None
        assert result["font"] is None

    def test_empty_segments_returns_default(self):
        track = SimpleNamespace(segments=[])
        result = extract_subtitle_style_from_track(track)
        assert result["border"] is None

    def test_index_out_of_range_returns_default(self):
        seg = SimpleNamespace(raw_data={})
        track = SimpleNamespace(segments=[seg])
        result = extract_subtitle_style_from_track(track, segment_index=5)
        assert result["border"] is None

    def test_segment_with_raw_data_extracts_clip_settings(self):
        seg = SimpleNamespace(
            raw_data={
                "clip": {
                    "transform": {"x": 0.1, "y": -0.5},
                    "scale": {"x": 1.2, "y": 1.2},
                }
            }
        )
        track = SimpleNamespace(segments=[seg])
        result = extract_subtitle_style_from_track(track, segment_index=0)
        assert result["clip_settings"]["transform_x"] == 0.1
        assert result["clip_settings"]["transform_y"] == -0.5
        assert result["clip_settings"]["scale_x"] == 1.2

    def test_segment_without_raw_data_returns_default(self):
        seg = SimpleNamespace()
        track = SimpleNamespace(segments=[seg])
        result = extract_subtitle_style_from_track(track, segment_index=0)
        assert result["border"] is None
        # 默认 clip_settings 有 transform_y
        assert result["clip_settings"]["transform_y"] == -0.8

    def test_does_not_raise_on_malformed_raw_data(self):
        """即使 raw_data 异常也不应抛异常。"""
        seg = SimpleNamespace(raw_data={"clip": "not a dict"})
        track = SimpleNamespace(segments=[seg])
        result = extract_subtitle_style_from_track(track, segment_index=0)
        # 应该返回默认值（_default_style 走默认 clip_settings 分支）
        assert "clip_settings" in result

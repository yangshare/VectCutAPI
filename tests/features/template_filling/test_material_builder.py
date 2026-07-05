"""material_builder 测试：验证不访问文件系统 + 字段正确。"""

from __future__ import annotations

import pytest

from vectcut.features.template_filling.material_builder import (
    build_audio_material_from_metadata,
    build_image_material_from_metadata,
    build_video_material_from_metadata,
)


class TestBuildVideoMaterial:
    def test_constructs_video_material_with_correct_fields(self):
        """构造视频素材：path/duration/width/height 正确，remote_url 为 None。"""
        mat = build_video_material_from_metadata(
            {
                "path": "C:/videos/sample.mp4",
                "duration": 30.5,
                "width": 1920,
                "height": 1080,
            }
        )
        assert mat.path == "C:/videos/sample.mp4"
        assert mat.material_name == "sample.mp4"
        # duration 内部转为微秒
        assert mat.duration == int(30.5 * 1e6)
        assert mat.width == 1920
        assert mat.height == 1080
        assert mat.material_type == "video"
        assert mat.remote_url is None

    def test_construction_does_not_touch_filesystem(self):
        """核心约束：用不存在的路径应成功构造不抛异常。"""
        mat = build_video_material_from_metadata(
            {
                "path": "X:/nonexistent/video.mp4",
                "duration": 10.0,
                "width": 1280,
                "height": 720,
            }
        )
        assert mat.path == "X:/nonexistent/video.mp4"
        assert mat.remote_url is None


class TestBuildAudioMaterial:
    def test_constructs_audio_material_with_correct_fields(self):
        mat = build_audio_material_from_metadata(
            {"path": "C:/audio/bgm.mp3", "duration": 45.0}
        )
        assert mat.path == "C:/audio/bgm.mp3"
        assert mat.material_name == "bgm.mp3"
        assert mat.duration == int(45.0 * 1e6)
        assert mat.remote_url is None

    def test_construction_does_not_touch_filesystem(self):
        mat = build_audio_material_from_metadata(
            {"path": "X:/nonexistent/audio.mp3", "duration": 60.0}
        )
        assert mat.path == "X:/nonexistent/audio.mp3"
        assert mat.remote_url is None


class TestBuildImageMaterial:
    def test_constructs_image_material_as_photo(self):
        mat = build_image_material_from_metadata(
            {"path": "C:/images/cover.jpg", "width": 1080, "height": 1920}
        )
        assert mat.path == "C:/images/cover.jpg"
        assert mat.material_name == "cover.jpg"
        assert mat.material_type == "photo"
        assert mat.width == 1080
        assert mat.height == 1920
        assert mat.remote_url is None

    def test_construction_does_not_touch_filesystem(self):
        mat = build_image_material_from_metadata(
            {"path": "X:/nonexistent/image.png", "width": 800, "height": 600}
        )
        assert mat.path == "X:/nonexistent/image.png"
        assert mat.material_type == "photo"
        assert mat.remote_url is None

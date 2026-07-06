"""material_builder 测试：验证不访问文件系统 + 字段正确。"""

from __future__ import annotations

import pytest

from vectcut.core.errors import RenderError
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

    @pytest.mark.parametrize(
        ("metadata", "expected_code"),
        [
            ({"duration": 10.0, "width": 1280, "height": 720}, "R_INVALID_PATH"),
            ({"path": "", "duration": 10.0, "width": 1280, "height": 720}, "R_INVALID_PATH"),
            ({"path": "C:/videos/sample.mp4", "width": 1280, "height": 720}, "R_INVALID_DURATION"),
            ({"path": "C:/videos/sample.mp4", "duration": 0, "width": 1280, "height": 720}, "R_INVALID_DURATION"),
            ({"path": "C:/videos/sample.mp4", "duration": "bad", "width": 1280, "height": 720}, "R_INVALID_DURATION"),
            ({"path": "C:/videos/sample.mp4", "duration": 10.0, "height": 720}, "R_INVALID_PATH"),
            ({"path": "C:/videos/sample.mp4", "duration": 10.0, "width": 1280}, "R_INVALID_PATH"),
            ({"path": "C:/videos/sample.mp4", "duration": 10.0, "width": 0, "height": 720}, "R_INVALID_PATH"),
        ],
    )
    def test_invalid_video_metadata_raises_structured_render_error(
        self, metadata, expected_code
    ):
        with pytest.raises(RenderError) as exc:
            build_video_material_from_metadata(metadata)
        assert exc.value.code == expected_code

    def test_non_dict_video_metadata_raises_structured_render_error(self):
        with pytest.raises(RenderError) as exc:
            build_video_material_from_metadata("not-a-dict")
        assert exc.value.code == "R_INVALID_PATH"
        assert exc.value.details["metadata_type"] == "str"


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

    @pytest.mark.parametrize(
        ("metadata", "expected_code"),
        [
            ({"duration": 45.0}, "R_INVALID_PATH"),
            ({"path": ""}, "R_INVALID_PATH"),
            ({"path": "C:/audio/bgm.mp3"}, "R_INVALID_DURATION"),
            ({"path": "C:/audio/bgm.mp3", "duration": 0}, "R_INVALID_DURATION"),
            ({"path": "C:/audio/bgm.mp3", "duration": "bad"}, "R_INVALID_DURATION"),
        ],
    )
    def test_invalid_audio_metadata_raises_structured_render_error(
        self, metadata, expected_code
    ):
        with pytest.raises(RenderError) as exc:
            build_audio_material_from_metadata(metadata)
        assert exc.value.code == expected_code

    def test_non_dict_audio_metadata_raises_structured_render_error(self):
        with pytest.raises(RenderError) as exc:
            build_audio_material_from_metadata("not-a-dict")
        assert exc.value.code == "R_INVALID_PATH"
        assert exc.value.details["metadata_type"] == "str"


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

    def test_non_dict_image_metadata_raises_structured_render_error(self):
        with pytest.raises(RenderError) as exc:
            build_image_material_from_metadata("not-a-dict")
        assert exc.value.code == "R_INVALID_PATH"
        assert exc.value.details["metadata_type"] == "str"

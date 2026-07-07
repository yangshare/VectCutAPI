"""template_filling render_draft 合成 golden 测试。

不依赖真实剪映草稿 fixture；用 FakeScript.dump 写入固定 JSON，验证
service 渲染流程对视频替换与字幕导入的可观察输出稳定。
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any, List

import pytest

from vectcut.features.template_filling import service, storage
from vectcut.features.template_filling.schemas import RenderDraftRequest


class _TrackType:
    def __init__(self, name: str):
        self.name = name


class _GoldenScript:
    def __init__(self):
        self.tracks = [
            self._track("video_main", "video"),
            self._track("subtitle", "text"),
        ]
        self.replace_calls: List[dict[str, Any]] = []
        self.import_srt_calls: List[dict[str, Any]] = []
        self._style_reference_indexes = {
            id(segment): index
            for index, segment in enumerate(self.tracks[1].segments)
        }

    @staticmethod
    def _track(name: str, track_type: str):
        return SimpleNamespace(
            name=name,
            track_type=_TrackType(track_type),
            segments=[SimpleNamespace(target_timerange=SimpleNamespace(duration=1_000_000))],
        )

    def get_imported_track(self, _track_type, name=None, index=None):
        for track in self.tracks:
            if track.name == name:
                return track
        raise KeyError(name)

    def replace_material_by_seg(self, track, segment_index, material):
        self.replace_calls.append(
            {
                "track": track.name,
                "segment_index": segment_index,
                "material_name": material.material_name,
                "duration": material.duration,
                "path": material.path,
            }
        )

    def import_srt(self, srt_content: str, track_name: str, **kwargs):
        self.import_srt_calls.append(
            {
                "track_name": track_name,
                "srt_content": srt_content,
                "style_reference_segment_index": self._style_reference_indexes[
                    id(kwargs["style_reference"])
                ],
                "clip_settings": kwargs["clip_settings"],
            }
        )
        self.tracks[1].segments.append(
            SimpleNamespace(target_timerange=SimpleNamespace(duration=2_000_000))
        )

    def dump(self, path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "import_srt_calls": self.import_srt_calls,
            "replace_calls": self.replace_calls,
        }
        Path(path).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )


@pytest.fixture
def golden_script(monkeypatch):
    script = _GoldenScript()
    monkeypatch.setattr(
        service.draft.Script_file,
        "load_template",
        staticmethod(lambda _path: script),
    )
    return script


def test_render_draft_writes_stable_synthetic_draft_json(
    temp_storage_dirs, golden_script, sample_template_zip
):
    service.import_template("tpl_golden", str(sample_template_zip))
    storage.save_slot_config(
        "tpl_golden",
        [
            {
                "slot_id": "video_video_main_0",
                "name": "主视频",
                "type": "video",
                "track_name": "video_main",
                "segment_index": 0,
            },
            {
                "slot_id": "subtitle_subtitle_0",
                "name": "字幕",
                "type": "subtitle",
                "track_name": "subtitle",
                "segment_index": 0,
            },
        ],
    )

    srt_content = "1\n00:00:00,000 --> 00:00:02,000\nHello\n"
    req = RenderDraftRequest(
        template_id="tpl_golden",
        slot_values={
            "video_video_main_0": {
                "path": "E:/clips/main.mp4",
                "duration": 2.0,
                "width": 1920,
                "height": 1080,
            },
            "subtitle_subtitle_0": {"srt_content": srt_content},
        },
        output_draft_name="out",
    )

    resp = service.render_draft("tpl_golden", req)
    generated_zip = temp_storage_dirs["generated"] / f"{resp.draft_id}.zip"

    with zipfile.ZipFile(generated_zip) as zf:
        payload = json.loads(zf.read("draft_content.json").decode("utf-8"))

    assert payload == {
        "import_srt_calls": [
            {
                "clip_settings": None,
                "srt_content": srt_content,
                "style_reference_segment_index": 0,
                "track_name": "subtitle",
            }
        ],
        "replace_calls": [
            {
                "duration": 2000000,
                "material_name": "main.mp4",
                "path": "E:/clips/main.mp4",
                "segment_index": 0,
                "track": "video_main",
            }
        ],
    }


def test_real_template_fixture_is_explicitly_skipped_when_missing():
    fixture = Path(__file__).resolve().parents[2] / "fixtures" / "sample_template.zip"
    if not fixture.exists():
        pytest.skip("缺少 tests/fixtures/sample_template.zip fixture")
    assert fixture.is_file()

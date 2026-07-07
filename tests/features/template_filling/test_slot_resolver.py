"""slot_resolver 测试：用 mock 不依赖真实剪映草稿 fixture。"""

from __future__ import annotations

import pytest

from vectcut.core.errors import SlotError
from vectcut.features.template_filling.slot_resolver import (
    resolve_all_slots,
    resolve_slot_to_track,
    validate_slot_segment_index,
)


class _MockSegment:
    pass


class _MockTrack:
    def __init__(self, name: str, n_segs: int):
        self.name = name
        self.segments = [_MockSegment() for _ in range(n_segs)]


class _MockScript:
    def __init__(self):
        self._tracks = {
            "video_main": _MockTrack("video_main", 2),
            "audio_bgm": _MockTrack("audio_bgm", 3),
            "text_subtitle": _MockTrack("text_subtitle", 1),
        }
        self.tracks = list(self._tracks.values())

    def get_imported_track(self, track_type, name=None):
        if name in self._tracks:
            return self._tracks[name]
        raise KeyError(f"未找到轨道: {name}")


@pytest.fixture
def script():
    return _MockScript()


class TestResolveSlotToTrack:
    def test_resolve_video_slot_success(self, script):
        slot = {"type": "video", "track_name": "video_main"}
        track = resolve_slot_to_track(script, slot)
        assert track.name == "video_main"
        assert len(track.segments) == 2

    def test_resolve_audio_slot_success(self, script):
        slot = {"type": "audio", "track_name": "audio_bgm"}
        track = resolve_slot_to_track(script, slot)
        assert track.name == "audio_bgm"

    def test_resolve_bgm_slot_maps_to_audio_track(self, script):
        slot = {"type": "bgm", "track_name": "audio_bgm"}
        track = resolve_slot_to_track(script, slot)
        assert track.name == "audio_bgm"

    def test_resolve_subtitle_slot_maps_to_text_track(self, script):
        slot = {"type": "subtitle", "track_name": "text_subtitle"}
        track = resolve_slot_to_track(script, slot)
        assert track.name == "text_subtitle"

    def test_track_not_found_raises_slot_error(self, script):
        slot = {"type": "video", "track_name": "nonexistent"}
        with pytest.raises(SlotError, match="轨道不存在") as exc:
            resolve_slot_to_track(script, slot)
        assert exc.value.code == "S_TRACK_NOT_FOUND"

    def test_unknown_slot_type_raises_slot_error(self, script):
        slot = {"type": "unknown", "track_name": "video_main"}
        with pytest.raises(SlotError, match="未知槽位类型") as exc:
            resolve_slot_to_track(script, slot)
        assert exc.value.code == "S_INVALID_SLOT"

    def test_missing_type_raises_slot_error(self, script):
        slot = {"track_name": "video_main"}
        with pytest.raises(SlotError, match="缺少 type") as exc:
            resolve_slot_to_track(script, slot)
        assert exc.value.code == "S_INVALID_SLOT"

    def test_missing_track_name_raises_slot_error(self, script):
        slot = {"type": "video"}
        with pytest.raises(SlotError, match="缺少 track_name") as exc:
            resolve_slot_to_track(script, slot)
        assert exc.value.code == "S_INVALID_SLOT"

    def test_resolves_locator_track_index_without_track_name(self, script):
        slot = {
            "type": "video",
            "track_name": "",
            "locator": {
                "scope": "root",
                "track_index": 0,
                "track_type": "video",
                "segment_index": 1,
            },
        }
        track = resolve_slot_to_track(script, slot)
        assert track.name == "video_main"


class TestValidateSlotSegmentIndex:
    def test_valid_index_passes(self):
        track = _MockTrack("video_main", 3)
        validate_slot_segment_index(track, 0, "slot1")
        validate_slot_segment_index(track, 2, "slot1")

    def test_index_out_of_range_raises(self):
        track = _MockTrack("video_main", 2)
        with pytest.raises(SlotError, match="越界") as exc:
            validate_slot_segment_index(track, 2, "slot1")
        assert exc.value.code == "S_SEGMENT_NOT_FOUND"
        with pytest.raises(SlotError, match="越界") as exc:
            validate_slot_segment_index(track, 5, "slot1")
        assert exc.value.code == "S_SEGMENT_NOT_FOUND"

    def test_negative_index_raises(self):
        track = _MockTrack("video_main", 2)
        with pytest.raises(SlotError, match="越界") as exc:
            validate_slot_segment_index(track, -1, "slot1")
        assert exc.value.code == "S_SEGMENT_NOT_FOUND"


class TestResolveAllSlots:
    def test_resolve_multiple_slots(self, script):
        slots = [
            {"slot_id": "v1", "type": "video", "track_name": "video_main", "segment_index": 0},
            {"slot_id": "a1", "type": "audio", "track_name": "audio_bgm", "segment_index": 1},
            {"slot_id": "t1", "type": "subtitle", "track_name": "text_subtitle", "segment_index": 0},
        ]
        result = resolve_all_slots(script, slots)
        assert set(result.keys()) == {"v1", "a1", "t1"}
        assert result["v1"].name == "video_main"
        assert result["a1"].name == "audio_bgm"
        assert result["t1"].name == "text_subtitle"

    def test_resolve_all_validates_segment_index(self, script):
        slots = [
            {"slot_id": "v1", "type": "video", "track_name": "video_main", "segment_index": 99},
        ]
        with pytest.raises(SlotError, match="越界") as exc:
            resolve_all_slots(script, slots)
        assert exc.value.code == "S_SEGMENT_NOT_FOUND"

    @pytest.mark.parametrize(
        "slot",
        [
            {"slot_id": "v1", "type": "video", "track_name": "video_main"},
            {"slot_id": "v1", "type": "video", "track_name": "video_main", "segment_index": None},
            {"slot_id": "v1", "type": "video", "track_name": "video_main", "segment_index": ""},
            {"slot_id": "v1", "type": "video", "track_name": "video_main", "segment_index": "abc"},
            {"slot_id": "v1", "type": "video", "track_name": "video_main", "segment_index": 1.5},
        ],
    )
    def test_resolve_all_rejects_invalid_segment_index_shape(self, script, slot):
        with pytest.raises(SlotError) as exc:
            resolve_all_slots(script, [slot])
        assert exc.value.code == "S_INVALID_SLOT"

    def test_resolve_all_accepts_integer_string_segment_index(self, script):
        slots = [
            {"slot_id": "v1", "type": "video", "track_name": "video_main", "segment_index": "1"},
        ]
        result = resolve_all_slots(script, slots)
        assert result["v1"].name == "video_main"

    @pytest.mark.parametrize("segment_index", [-1, 99])
    def test_resolve_all_rejects_out_of_range_segment_index(self, script, segment_index):
        slots = [
            {
                "slot_id": "v1",
                "type": "video",
                "track_name": "video_main",
                "segment_index": segment_index,
            },
        ]
        with pytest.raises(SlotError) as exc:
            resolve_all_slots(script, slots)
        assert exc.value.code == "S_SEGMENT_NOT_FOUND"

    def test_missing_slot_id_raises(self, script):
        slots = [
            {"type": "video", "track_name": "video_main", "segment_index": 0},
        ]
        with pytest.raises(SlotError, match="缺少 slot_id") as exc:
            resolve_all_slots(script, slots)
        assert exc.value.code == "S_INVALID_SLOT"

    def test_duplicate_slot_id_raises_structured_error(self, script):
        slots = [
            {"slot_id": "dup", "type": "video", "track_name": "video_main", "segment_index": 0},
            {"slot_id": "dup", "type": "audio", "track_name": "audio_bgm", "segment_index": 0},
        ]
        with pytest.raises(SlotError) as exc:
            resolve_all_slots(script, slots)
        assert exc.value.code == "S_INVALID_SLOT"
        assert exc.value.details["slot_id"] == "dup"
        assert exc.value.details["first_index"] == 0
        assert exc.value.details["duplicate_index"] == 1

    def test_empty_slots_returns_empty_dict(self, script):
        result = resolve_all_slots(script, [])
        assert result == {}

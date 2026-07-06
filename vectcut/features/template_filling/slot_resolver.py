"""槽位解析器：把模板槽位配置映射到 pyJianYingDraft 轨道对象。

不依赖真实剪映草稿 fixture，测试用 mock。生产代码通过 script.get_imported_track 解析。
"""

from __future__ import annotations

import re
from typing import Dict, List

from pyJianYingDraft.track import Track_type

from vectcut.core.errors import make_error


def _map_slot_type_to_track_type(slot_type: str) -> Track_type:
    """槽位 type → Track_type 枚举。

    video → Track_type.video
    audio / bgm → Track_type.audio
    subtitle → Track_type.text
    """
    mapping = {
        "video": Track_type.video,
        "audio": Track_type.audio,
        "bgm": Track_type.audio,
        "subtitle": Track_type.text,
    }
    if slot_type not in mapping:
        raise make_error(
            "S_INVALID_SLOT",
            f"未知槽位类型: {slot_type}",
            details={"slot_type": slot_type},
        )
    return mapping[slot_type]


def resolve_slot_to_track(script, slot: dict):
    """把 slot（含 type/track_name）映射到 script 的轨道对象。

    Args:
        script: Script_file 实例（需有 get_imported_track 方法）。
        slot: 槽位配置 dict，必须含 type 和 track_name。

    Returns:
        Track 对象。

    Raises:
        SlotError: 槽位类型未知或轨道不存在。
    """
    slot_type = slot.get("type")
    track_name = slot.get("track_name")

    if not slot_type:
        raise make_error(
            "S_INVALID_SLOT",
            f"槽位缺少 type 字段: {slot}",
            details={"slot": slot},
        )
    if not track_name:
        raise make_error(
            "S_INVALID_SLOT",
            f"槽位缺少 track_name 字段: {slot}",
            details={"slot": slot},
        )

    track_type = _map_slot_type_to_track_type(slot_type)

    try:
        track = script.get_imported_track(track_type, name=track_name)
    except Exception as e:
        raise make_error(
            "S_TRACK_NOT_FOUND",
            f"轨道不存在: track_type={track_type.name}, track_name={track_name} ({e})",
            details={"track_type": track_type.name, "track_name": track_name},
        ) from e

    return track


def validate_slot_segment_index(track, segment_index: int, slot_id: str) -> None:
    """校验 0 <= segment_index < len(track.segments)，否则 SlotError。

    Args:
        track: 轨道对象（必须有 .segments 列表）。
        segment_index: 待校验的片段索引。
        slot_id: 槽位 ID（错误消息用）。

    Raises:
        SlotError: 索引越界（含"越界"）。
    """
    n = len(track.segments)
    if segment_index < 0 or segment_index >= n:
        raise make_error(
            "S_SEGMENT_NOT_FOUND",
            f"槽位 {slot_id} 的 segment_index {segment_index} 越界（轨道 {track.name} 有 {n} 个片段）",
            details={
                "slot_id": slot_id,
                "segment_index": segment_index,
                "track_name": track.name,
                "segment_count": n,
            },
        )


def parse_slot_segment_index(slot: dict) -> int:
    slot_id = slot.get("slot_id", "")
    if "segment_index" not in slot:
        raise make_error(
            "S_INVALID_SLOT",
            "槽位配置缺少 segment_index",
            details={"slot_id": slot_id, "slot": slot},
        )

    value = slot.get("segment_index")
    if isinstance(value, bool) or value is None:
        raise make_error(
            "S_INVALID_SLOT",
            "槽位 segment_index 必须是整数",
            details={"slot_id": slot_id, "segment_index": value},
        )
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip() and re.fullmatch(r"-?\d+", value.strip()):
        return int(value.strip())

    raise make_error(
        "S_INVALID_SLOT",
        "槽位 segment_index 必须是整数",
        details={"slot_id": slot_id, "segment_index": value},
    )


def resolve_all_slots(script, slots: List[dict]) -> Dict[str, object]:
    """批量解析槽位，返回 {slot_id: track}。

    每个 slot 都校验 segment_index。

    Args:
        script: Script_file 实例。
        slots: 槽位配置列表，每个含 slot_id/type/track_name/segment_index。

    Returns:
        {slot_id: track} 映射。

    Raises:
        SlotError: 任一槽位解析或校验失败。
    """
    result: Dict[str, object] = {}
    first_indices: Dict[str, int] = {}
    for index, slot in enumerate(slots):
        slot_id = slot.get("slot_id")
        if not slot_id:
            raise make_error(
                "S_INVALID_SLOT",
                f"槽位缺少 slot_id 字段: {slot}",
                details={"slot": slot},
            )
        if slot_id in result:
            raise make_error(
                "S_INVALID_SLOT",
                f"槽位配置包含重复 slot_id: {slot_id}",
                details={
                    "slot_id": slot_id,
                    "first_index": first_indices[slot_id],
                    "duplicate_index": index,
                },
            )
        track = resolve_slot_to_track(script, slot)
        segment_index = parse_slot_segment_index(slot)
        validate_slot_segment_index(track, segment_index, slot_id)
        first_indices[slot_id] = index
        result[slot_id] = track
    return result

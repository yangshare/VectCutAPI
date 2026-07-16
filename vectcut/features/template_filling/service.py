"""template_filling 业务逻辑层：模板导入、槽位配置、草稿渲染与下载。

4 个核心函数编排 storage / slot_resolver / material_builder / duration_calculator 等辅助模块，
完成从模板 ZIP 到可下载草稿 ZIP 的端到端流程。
"""

from __future__ import annotations

import json
import os
import re
import shutil
import time
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional

import pyJianYingDraft as draft

from vectcut.core.config import load_config
from vectcut.core.draft_store import get_draft_profile, write_profile_content
from vectcut.core.errors import SlotError, TemplateError, make_error
from vectcut.core.logger import sanitize_exception
from vectcut.features.template_filling import (
    draft_content_decryptor,
    duration_calculator,
    material_builder,
    slot_resolver,
    storage,
    style_extractor,
)
from vectcut.features.template_filling.schemas import (
    DownloadDraftResponse,
    ImportTemplateResponse,
    RenderDraftResponse,
    SaveSlotConfigResponse,
)


# ─── 辅助函数 ──────────────────────────────────────────────────────────────


def _validate_template_id(template_id: str) -> None:
    """校验 template_id 只含字母/数字/下划线/连字符，否则抛 TemplateError。"""
    if not re.fullmatch(r"[A-Za-z0-9_-]+", template_id):
        raise make_error(
            "T_INVALID_ID",
            f"非法 template_id: {template_id}",
            details={"template_id": template_id},
        )


def _validate_draft_id(draft_id: str) -> None:
    """校验 draft_id/task_id，避免路径穿越和空 ID。"""
    if not draft_id or not re.fullmatch(r"[A-Za-z0-9_-]+", draft_id):
        raise make_error(
            "R_INVALID_TASK",
            details={"draft_id": draft_id},
        )


def _map_missing_draft_content(template_id: str, exc: TemplateError) -> TemplateError:
    if exc.code != "TEMPLATE_ERROR":
        return exc
    return make_error(
        "T_NO_DRAFT_CONTENT",
        str(exc),
        details={"template_id": template_id},
    )


def _map_missing_slot_config(template_id: str, exc: SlotError) -> SlotError:
    if exc.code != "SLOT_ERROR":
        return exc
    return make_error(
        "S_NOT_FOUND",
        str(exc),
        details={"template_id": template_id},
    )


def _template_import_semantic_error(template_id: str, exc: Exception) -> TemplateError:
    return make_error(
        "T_INVALID_ZIP",
        "模板 ZIP 内容无法解析",
        details={
            "template_id": template_id,
            "reason": sanitize_exception(exc),
        },
    )


def _draft_content_import_semantic_error(template_id: str, exc: Exception) -> TemplateError:
    return make_error(
        "T_INVALID_DRAFT_CONTENT",
        "draft_content.json 内容无法解析",
        details={
            "template_id": template_id,
            "reason": sanitize_exception(exc),
        },
    )


def _parse_plain_draft_content(content: bytes) -> bytes:
    try:
        text = content.decode("utf-8-sig")
        json.loads(text)
    except Exception as exc:
        raise make_error(
            "T_INVALID_DRAFT_CONTENT",
            "draft_content.json 不是合法 JSON",
            details={"reason": sanitize_exception(exc)},
        ) from exc
    return text.encode("utf-8")


def _load_draft_content_bytes(content: bytes, *, dll_path: str) -> tuple[bytes, bool]:
    try:
        return _parse_plain_draft_content(content), False
    except TemplateError:
        plain = draft_content_decryptor.decrypt_draft_content(content, dll_path)
        return _parse_plain_draft_content(plain), True


def _scan_slots_from_template(script) -> List[Dict[str, Any]]:
    """扫描全部根轨道，由用户决定哪些轨道要配置成日常替换槽位。"""
    slots: List[Dict[str, Any]] = []
    seen_object_ids = set()
    seen_track_keys = set()
    candidate_tracks = list(_iter_tracks(getattr(script, "tracks", None)))
    candidate_tracks.extend(_iter_tracks(getattr(script, "imported_tracks", None)))
    unique_tracks = []

    for track in candidate_tracks:
        # 用 .name 字符串比较，兼容真实 Track_type 枚举与测试 mock
        tt_name = getattr(track.track_type, "name", str(track.track_type))
        track_name = getattr(track, "name", "")
        track_id = _get_track_id(track)
        track_key = ("id", track_id) if track_id else ("name", tt_name, track_name)
        if id(track) in seen_object_ids:
            continue
        if (track_id or track_name) and track_key in seen_track_keys:
            continue
        seen_object_ids.add(id(track))
        if track_id or track_name:
            seen_track_keys.add(track_key)
        unique_tracks.append(track)

    type_counts: Dict[str, int] = {}
    used_slot_ids = set()
    for track_index, track in enumerate(unique_tracks):
        tt_name = getattr(track.track_type, "name", str(track.track_type))
        track_name = getattr(track, "name", "")

        if tt_name == "video":
            slot_type = "video"
        elif tt_name == "audio":
            slot_type = "bgm" if "bgm" in track_name.lower() else "audio"
        elif tt_name == "text":
            slot_type = "subtitle"
        else:
            slot_type = tt_name or "unknown"

        segment_count = len(track.segments)
        if segment_count == 0:
            continue
        type_counts[tt_name] = type_counts.get(tt_name, 0) + 1
        ordinal = type_counts[tt_name]
        slot_id = (
            f"{slot_type}_{track_name}"
            if track_name
            else f"{slot_type}_track{track_index}"
        )
        if slot_id in used_slot_ids:
            slot_id = f"{slot_id}_track{track_index}"
        used_slot_ids.add(slot_id)
        display_type_names = {
            "video": "视频轨",
            "audio": "音频轨",
            "text": "文字轨",
            "effect": "特效轨",
            "adjust": "调节轨",
            "filter": "滤镜轨",
            "sticker": "贴纸轨",
        }
        display_name = f"{display_type_names.get(tt_name, '其他轨道')} {ordinal}"
        locator = {
            "scope": "root",
            "track_index": track_index,
            "track_type": tt_name,
            "segment_index": 0,
        }
        track_id = _get_track_id(track)
        if track_id:
            locator["track_id"] = track_id
        segment_id = getattr(track.segments[0], "segment_id", "")
        if not segment_id:
            raw_data = getattr(track.segments[0], "raw_data", None)
            if isinstance(raw_data, dict):
                segment_id = raw_data.get("id", "")
        if segment_id:
            locator["segment_id"] = segment_id

        slots.append({
            "slot_id": slot_id,
            "type": slot_type,
            "track_type": tt_name,
            "track_name": track_name,
            "segment_index": 0,
            "segment_indices": list(range(segment_count)),
            "segment_count": segment_count,
            "name": display_name,
            "replaceable": tt_name in {"video", "audio", "text"},
            "selected": False,
            "content_preview": _track_content_preview(script, track, tt_name),
            "locator": locator,
        })
    return slots


def _iter_tracks(value):
    if value is None:
        return []
    if isinstance(value, dict):
        return value.values()
    return value


def _get_track_id(track) -> str:
    value = getattr(track, "track_id", "")
    if isinstance(value, str) and value:
        return value
    raw_data = getattr(track, "raw_data", None)
    if isinstance(raw_data, dict):
        raw_id = raw_data.get("id")
        if isinstance(raw_id, str):
            return raw_id
    return ""


def _track_content_preview(script, track, track_type: str) -> str:
    imported_materials = getattr(script, "imported_materials", None)
    if not isinstance(imported_materials, dict):
        return ""
    material_group = {
        "video": "videos",
        "audio": "audios",
        "text": "texts",
    }.get(track_type)
    if not material_group:
        return ""

    materials = imported_materials.get(material_group)
    if not isinstance(materials, list):
        return ""
    by_id = {
        material.get("id"): material
        for material in materials
        if isinstance(material, dict) and material.get("id")
    }
    previews: List[str] = []
    for segment in track.segments:
        material = by_id.get(getattr(segment, "material_id", ""))
        if not material:
            continue
        preview = _material_content_preview(material, track_type)
        if preview and preview not in previews:
            previews.append(preview)
        if len(previews) == 2:
            break
    return " / ".join(previews)


def _material_content_preview(material: Dict[str, Any], track_type: str) -> str:
    if track_type == "text":
        content = material.get("content")
        if isinstance(content, str):
            try:
                parsed = json.loads(content)
                text = parsed.get("text", "") if isinstance(parsed, dict) else ""
            except (TypeError, ValueError):
                text = content
            if isinstance(text, str):
                return text.strip().replace("\n", " ")[:32]
        return ""
    keys = ("material_name", "name", "path") if track_type == "video" else ("name", "path")
    for key in keys:
        value = material.get(key)
        if isinstance(value, str) and value.strip():
            return os.path.basename(value.strip())[:48]
    return ""


def _restore_saved_slot_selections(template_id: str, slots: List[Dict[str, Any]]) -> None:
    try:
        saved_slots = storage.load_slot_config(template_id)
    except SlotError:
        return
    saved_by_id = {
        slot.get("slot_id"): slot
        for slot in saved_slots
        if isinstance(slot, dict) and slot.get("slot_id")
    }
    for slot in slots:
        saved = saved_by_id.get(slot["slot_id"])
        if not saved or not slot.get("replaceable"):
            continue
        saved_track_id = (saved.get("locator") or {}).get("track_id")
        current_track_id = (slot.get("locator") or {}).get("track_id")
        if saved_track_id and current_track_id and saved_track_id != current_track_id:
            continue
        slot["selected"] = True


def _replace_slot_material(
    script, track, slot: Dict[str, Any], material, segment_index: Optional[int] = None
) -> None:
    slot_id = slot.get("slot_id", "")
    if segment_index is None:
        segment_index = slot_resolver.parse_slot_segment_index(slot)
    slot_resolver.validate_slot_segment_index(track, segment_index, slot_id)
    script.replace_material_by_seg(track, segment_index, material)


def _track_video_material_values(slot: Dict[str, Any], value: Any) -> Optional[List[Any]]:
    if not isinstance(value, dict) or "materials" not in value:
        return None
    materials = value.get("materials")
    if not isinstance(materials, list) or not materials:
        raise make_error(
            "R_INVALID_MATERIAL_METADATA",
            "视频轨道素材必须是非空列表",
            details={"slot_id": slot.get("slot_id")},
        )
    return materials


def _fit_video_material_values(
    slot: Dict[str, Any],
    material_values: List[Any],
    target_duration: Optional[float],
) -> List[tuple[Any, float]]:
    durations: List[float] = []
    for value in material_values:
        duration = _metadata_duration_seconds(value)
        if duration is None:
            raise make_error(
                "R_INVALID_MATERIAL_METADATA",
                "视频素材时长缺失或非法",
                details={"slot_id": slot.get("slot_id"), "field": "duration"},
            )
        durations.append(duration)

    if target_duration is None:
        return list(zip(material_values, durations))

    target_us = round(target_duration * 1_000_000)
    remaining_us = target_us
    fitted: List[tuple[Any, float]] = []
    for value, duration in zip(material_values, durations):
        duration_us = round(duration * 1_000_000)
        clip_us = min(duration_us, remaining_us)
        if clip_us > 0:
            fitted.append((value, clip_us / 1_000_000))
            remaining_us -= clip_us
        if remaining_us <= 0:
            break

    if remaining_us > 0:
        available_duration = sum(durations)
        raise make_error(
            "R_VIDEO_DURATION_SHORT",
            "视频目录总时长不足，无法覆盖配音",
            details={
                "slot_id": slot.get("slot_id"),
                "target_duration": target_duration,
                "available_duration": available_duration,
                "shortage": remaining_us / 1_000_000,
            },
        )
    return fitted


def _clone_video_segment(reference, start_us: int, duration_us: int):
    segment = deepcopy(reference)
    if hasattr(segment, "segment_id"):
        segment.segment_id = uuid.uuid4().hex
    segment.target_timerange = draft.Timerange(start_us, duration_us)
    segment.source_timerange = draft.Timerange(0, duration_us)
    segment.common_keyframes = []

    speed = getattr(segment, "speed", None)
    if speed is not None:
        old_speed_id = getattr(speed, "global_id", "")
        speed.global_id = uuid.uuid4().hex
        speed.speed = 1.0
        refs = list(getattr(segment, "extra_material_refs", []))
        segment.extra_material_refs = [
            speed.global_id if ref == old_speed_id else ref
            for ref in refs
        ]
        if speed.global_id not in segment.extra_material_refs:
            segment.extra_material_refs.append(speed.global_id)
    return segment


def _register_segment_speed(script, segment) -> None:
    speed = getattr(segment, "speed", None)
    speeds = getattr(getattr(script, "materials", None), "speeds", None)
    if speed is None or not isinstance(speeds, list):
        return
    speed_id = getattr(speed, "global_id", "")
    if speed_id and all(getattr(item, "global_id", "") != speed_id for item in speeds):
        speeds.append(deepcopy(speed))


def _replace_video_track_materials(
    script,
    track,
    slot: Dict[str, Any],
    material_values: List[Any],
    target_duration: Optional[float],
) -> List[float]:
    if not track.segments:
        raise make_error(
            "R_EMPTY_VIDEO",
            details={"slot_id": slot.get("slot_id")},
        )

    fitted_values = _fit_video_material_values(slot, material_values, target_duration)
    references = [deepcopy(segment) for segment in track.segments]
    track.segments.clear()
    clip_durations: List[float] = []
    start_us = 0

    for index, (material_value, clip_duration) in enumerate(fitted_values):
        clip_duration_us = round(clip_duration * 1_000_000)
        reference = references[index % len(references)]
        track.segments.append(_clone_video_segment(reference, start_us, clip_duration_us))
        material = material_builder.build_video_material_from_metadata(material_value)
        _replace_slot_material(script, track, slot, material, index)
        track.segments[index].target_timerange = draft.Timerange(start_us, clip_duration_us)
        track.segments[index].source_timerange = draft.Timerange(0, clip_duration_us)
        _register_segment_speed(script, track.segments[index])
        clip_durations.append(clip_duration)
        start_us += clip_duration_us

    return clip_durations


def _requested_audio_target_duration(
    slot_map: Dict[str, Dict[str, Any]],
    slot_values: Dict[str, Any],
) -> Optional[float]:
    durations = [
        duration
        for slot_id, value in slot_values.items()
        if slot_map[slot_id].get("type") == "audio"
        for duration in [_metadata_duration_seconds(value)]
        if duration is not None
    ]
    return max(durations) if durations else None


def _expand_audio_segment_to_material(script, track, segment_index: int, material) -> None:
    segment = track.segments[segment_index]
    start = getattr(getattr(segment, "target_timerange", None), "start", 0)
    segment.target_timerange = draft.Timerange(start, material.duration)
    segment.source_timerange = draft.Timerange(0, material.duration)
    speed = getattr(segment, "speed", None)
    if speed is not None:
        speed.speed = 1.0
    _register_segment_speed(script, segment)


def _track_type_name(track) -> str:
    track_type = getattr(track, "track_type", "")
    return getattr(track_type, "name", str(track_type))


def _align_segment_end_to_target(segment, target_end_us: int) -> bool:
    time_range = getattr(segment, "target_timerange", None)
    if time_range is None:
        return False

    start = getattr(time_range, "start", 0) or 0
    try:
        start_us = int(start)
    except (TypeError, ValueError):
        return False

    if target_end_us <= start_us:
        return False

    new_duration = target_end_us - start_us
    if getattr(time_range, "duration", None) == new_duration:
        return False
    time_range.duration = new_duration
    return True


def _align_non_media_track_ends_to_target(
    script,
    target_duration: Optional[float],
    *,
    preserved_track_ids: Optional[set[int]] = None,
) -> None:
    if target_duration is None or target_duration <= 0:
        return

    target_end_us = round(target_duration * 1_000_000)
    preserved_track_ids = preserved_track_ids or set()
    seen_track_ids: set[int] = set()
    tracks = list(_iter_tracks(getattr(script, "tracks", None)))
    tracks.extend(_iter_tracks(getattr(script, "imported_tracks", None)))

    for track in tracks:
        object_id = id(track)
        if object_id in seen_track_ids or object_id in preserved_track_ids:
            continue
        seen_track_ids.add(object_id)

        if _track_type_name(track) in {"video", "audio"}:
            continue

        segments = getattr(track, "segments", [])
        if not segments:
            continue
        _align_segment_end_to_target(segments[-1], target_end_us)


def _update_script_duration(script) -> None:
    tracks = list(_iter_tracks(getattr(script, "tracks", None)))
    tracks.extend(_iter_tracks(getattr(script, "imported_tracks", None)))
    end_times = []
    for track in tracks:
        for segment in getattr(track, "segments", []):
            time_range = getattr(segment, "target_timerange", None)
            if time_range is None:
                continue
            end_times.append(
                getattr(
                    time_range,
                    "end",
                    getattr(time_range, "start", 0) + getattr(time_range, "duration", 0),
                )
            )
    if end_times:
        script.duration = max(end_times)


_SRT_TIMESTAMP_RE = re.compile(
    r"(?P<start>\d{2}:\d{2}:\d{2},\d{3})\s+-->\s+"
    r"(?P<end>\d{2}:\d{2}:\d{2},\d{3})"
)


def _parse_srt_timestamp(value: str) -> float:
    match = re.fullmatch(r"(\d{2}):(\d{2}):(\d{2}),(\d{3})", value)
    if not match:
        raise ValueError(f"invalid SRT timestamp: {value}")
    hours, minutes, seconds, millis = (int(part) for part in match.groups())
    return hours * 3600 + minutes * 60 + seconds + millis / 1000.0


def _subtitle_parse_error(slot_id: str, reason: str) -> Exception:
    return make_error(
        "R_SRT_PARSE_ERROR",
        "SRT 文件格式错误",
        details={"slot_id": slot_id, "reason": reason},
    )


def _require_srt_content(slot_id: str, value: Any) -> str:
    if not isinstance(value, dict):
        raise _subtitle_parse_error(slot_id, "字幕槽位值必须是对象")
    srt_content = value.get("srt_content")
    if not isinstance(srt_content, str) or not srt_content.strip():
        raise _subtitle_parse_error(slot_id, "srt_content 必须是非空字符串")
    return srt_content


def _get_srt_latest_end_seconds(slot_id: str, srt_content: str) -> float:
    return max(end for _start, end, _text in _parse_srt_entries(slot_id, srt_content))


def _parse_srt_entries(slot_id: str, srt_content: str) -> List[tuple[float, float, str]]:
    normalized = srt_content.replace("\r\n", "\n").replace("\r", "\n")
    if normalized.startswith("\ufeff"):
        normalized = normalized[1:]
    lines = normalized.split("\n")
    entries: List[tuple[float, float, str]] = []
    index = 0
    while index < len(lines):
        if not lines[index].strip():
            index += 1
            continue
        if not lines[index].strip().isdigit():
            raise _subtitle_parse_error(slot_id, f"第 {index + 1} 行应为字幕序号")
        index += 1
        if index >= len(lines):
            raise _subtitle_parse_error(slot_id, "字幕序号后缺少时间轴")
        match = _SRT_TIMESTAMP_RE.fullmatch(lines[index].strip())
        if not match:
            raise _subtitle_parse_error(slot_id, f"第 {index + 1} 行时间轴格式错误")
        start = _parse_srt_timestamp(match.group("start"))
        end = _parse_srt_timestamp(match.group("end"))
        if end <= start:
            raise _subtitle_parse_error(slot_id, "SRT 结束时间必须晚于开始时间")
        index += 1
        text_lines = []
        while index < len(lines) and lines[index].strip():
            text_lines.append(lines[index].strip())
            index += 1
        text = "\n".join(text_lines).strip()
        if not text:
            raise _subtitle_parse_error(slot_id, "字幕内容不能为空")
        entries.append((start, end, text))
    if not entries:
        raise _subtitle_parse_error(slot_id, "SRT 缺少有效时间轴")
    return entries


def _replace_text_material_content(material: Dict[str, Any], text: str) -> None:
    content = material.get("content")
    if isinstance(content, str):
        try:
            parsed = json.loads(content)
        except (TypeError, ValueError):
            parsed = None
        if isinstance(parsed, dict):
            old_text = parsed.get("text", "")
            old_length = max(len(old_text), 1) if isinstance(old_text, str) else 1
            parsed["text"] = text
            for style in parsed.get("styles", []):
                if (
                    not isinstance(style, dict)
                    or not isinstance(style.get("range"), list)
                    or len(style["range"]) < 2
                ):
                    continue
                start, end = style["range"][:2]
                style["range"] = [
                    round(int(start) / old_length * len(text)),
                    round(int(end) / old_length * len(text)),
                ]
            material["content"] = json.dumps(parsed, ensure_ascii=False, separators=(",", ":"))
        else:
            material["content"] = text
    material["base_content"] = text
    if isinstance(material.get("words"), dict):
        material["words"] = {"end_time": [], "start_time": [], "text": []}


def _has_text_content_value(value: Any) -> bool:
    return isinstance(value, dict) and "text" in value


def _require_text_content(slot_id: str, value: Any) -> str:
    if not isinstance(value, dict):
        raise make_error(
            "R_INVALID_TEXT_VALUE",
            "文字槽位值必须是对象",
            details={"slot_id": slot_id},
        )
    text = value.get("text")
    if not isinstance(text, str) or not text.strip():
        raise make_error(
            "R_INVALID_TEXT_VALUE",
            "text 必须是非空字符串",
            details={"slot_id": slot_id, "field": "text"},
        )
    return text.strip()


def _segment_material_ids(segment) -> List[str]:
    material_ids: List[str] = []
    material_id = getattr(segment, "material_id", "")
    if isinstance(material_id, str) and material_id:
        material_ids.append(material_id)

    raw_data = getattr(segment, "raw_data", None)
    if isinstance(raw_data, dict):
        raw_material_id = raw_data.get("material_id")
        if isinstance(raw_material_id, str) and raw_material_id:
            material_ids.append(raw_material_id)

        extra_refs = raw_data.get("extra_material_refs")
        if isinstance(extra_refs, list):
            material_ids.extend(ref for ref in extra_refs if isinstance(ref, str) and ref)

    return list(dict.fromkeys(material_ids))


def _replace_text_material_by_id(
    imported_materials: Dict[str, Any],
    material_id: str,
    text: str,
) -> bool:
    text_materials = imported_materials.get("texts")
    if not isinstance(text_materials, list):
        text_materials = []

    for material in text_materials:
        if isinstance(material, dict) and material.get("id") == material_id:
            _replace_text_material_content(material, text)
            return True

    text_templates = imported_materials.get("text_templates")
    if not isinstance(text_templates, list):
        return False

    for template in text_templates:
        if not isinstance(template, dict) or template.get("id") != material_id:
            continue
        resources = template.get("text_info_resources")
        if not isinstance(resources, list):
            return False
        replaced = False
        for resource in resources:
            if not isinstance(resource, dict):
                continue
            text_material_id = resource.get("text_material_id")
            if not isinstance(text_material_id, str) or not text_material_id:
                continue
            for material in text_materials:
                if isinstance(material, dict) and material.get("id") == text_material_id:
                    _replace_text_material_content(material, text)
                    replaced = True
                    break
        return replaced

    return False


def _replace_text_slot(script, track, slot: Dict[str, Any], value: Any) -> None:
    slot_id = slot.get("slot_id", "")
    text = _require_text_content(slot_id, value)
    imported_materials = getattr(script, "imported_materials", None)
    if not isinstance(imported_materials, dict):
        raise make_error(
            "R_TEXT_MATERIAL_NOT_FOUND",
            "草稿缺少文字素材表",
            details={"slot_id": slot_id},
        )

    for segment_index in slot_resolver.parse_slot_segment_indices(slot):
        slot_resolver.validate_slot_segment_index(track, segment_index, slot_id)
        segment = track.segments[segment_index]
        material_ids = _segment_material_ids(segment)
        replaced = any(
            _replace_text_material_by_id(imported_materials, material_id, text)
            for material_id in material_ids
        )
        if not replaced:
            raise make_error(
                "R_TEXT_MATERIAL_NOT_FOUND",
                "未找到文字片段对应素材",
                details={
                    "slot_id": slot_id,
                    "segment_index": segment_index,
                    "material_ids": material_ids,
                },
            )


def _import_srt_into_raw_track(script, track, style_reference, entries) -> bool:
    raw_segment = getattr(style_reference, "raw_data", None)
    imported_materials = getattr(script, "imported_materials", None)
    if not isinstance(raw_segment, dict) or not isinstance(imported_materials, dict):
        return False
    text_materials = imported_materials.get("texts")
    if not isinstance(text_materials, list):
        return False
    reference_material = next(
        (
            material for material in text_materials
            if isinstance(material, dict) and material.get("id") == style_reference.material_id
        ),
        None,
    )
    if reference_material is None:
        return False

    segment_class = type(style_reference)
    new_segments = []
    new_materials = []
    for start, end, text in entries:
        material = deepcopy(reference_material)
        material_id = uuid.uuid4().hex
        material["id"] = material_id
        _replace_text_material_content(material, text)

        segment_data = deepcopy(raw_segment)
        segment_data["id"] = uuid.uuid4().hex
        segment_data["material_id"] = material_id
        segment_data["target_timerange"] = {
            "start": round(start * 1_000_000),
            "duration": round((end - start) * 1_000_000),
        }
        segment_data["common_keyframes"] = []
        new_segments.append(segment_class(segment_data))
        new_materials.append(material)

    track.segments[:] = new_segments
    text_materials.extend(new_materials)
    return True


def _import_subtitle_srt(script, track, slot: Dict[str, Any], value: Any) -> float:
    slot_id = slot.get("slot_id", "")
    segment_index = slot_resolver.parse_slot_segment_index(slot)
    slot_resolver.validate_slot_segment_index(track, segment_index, slot_id)
    srt_content = _require_srt_content(slot_id, value)
    entries = _parse_srt_entries(slot_id, srt_content)
    latest_end = max(end for _start, end, _text in entries)
    style_reference = track.segments[segment_index]
    old_segments = list(track.segments)

    try:
        if not _import_srt_into_raw_track(script, track, style_reference, entries):
            track.segments.clear()
            script.import_srt(
                srt_content,
                track.name,
                style_reference=style_reference,
                clip_settings=None,
            )
    except ValueError as exc:
        track.segments[:] = old_segments
        raise _subtitle_parse_error(slot_id, sanitize_exception(exc)) from exc
    except Exception:
        track.segments[:] = old_segments
        raise

    return latest_end


def _metadata_duration_seconds(value: Any) -> Optional[float]:
    if not isinstance(value, dict):
        return None
    duration = value.get("duration")
    if isinstance(duration, bool):
        return None
    try:
        duration_value = float(duration)
    except (TypeError, ValueError):
        return None
    if duration_value <= 0:
        return None
    return duration_value


def _select_alignment_target(
    video_durations: List[float],
    audio_durations: List[float],
    bgm_durations: List[float],
    subtitle_latest_end_seconds: Optional[float],
) -> Optional[float]:
    if audio_durations:
        return max(audio_durations)
    if subtitle_latest_end_seconds and subtitle_latest_end_seconds > 0:
        return subtitle_latest_end_seconds
    if video_durations:
        return sum(video_durations)
    if bgm_durations:
        return max(bgm_durations)
    return None


def _merge_duration_alignment_warnings(
    warnings: List[str],
    video_durations: List[float],
    bgm_durations: List[float],
    target_duration: Optional[float],
) -> None:
    if target_duration is None:
        return
    if video_durations:
        _, video_warnings = duration_calculator.calculate_video_loop_fill(
            video_durations,
            target_duration,
        )
        warnings.extend(video_warnings)
    for bgm_duration in bgm_durations:
        _, bgm_warnings = duration_calculator.calculate_bgm_alignment(
            bgm_duration,
            target_duration,
        )
        warnings.extend(bgm_warnings)


def _build_slot_map(slots_config: List[Dict[str, Any]], template_id: str) -> Dict[str, Dict[str, Any]]:
    slot_map: Dict[str, Dict[str, Any]] = {}
    for index, slot in enumerate(slots_config):
        slot_id = slot.get("slot_id")
        if not slot_id:
            raise make_error(
                "S_INVALID_SLOT",
                "槽位配置缺少 slot_id",
                details={"template_id": template_id, "slot_index": index, "slot": slot},
            )
        if slot_id in slot_map:
            raise make_error(
                "S_INVALID_SLOT",
                f"槽位配置包含重复 slot_id: {slot_id}",
                details={
                    "template_id": template_id,
                    "slot_id": slot_id,
                    "first_index": slot_map[slot_id].get("_slot_index", 0),
                    "duplicate_index": index,
                },
            )
        slot = dict(slot)
        slot["_slot_index"] = index
        slot_map[slot_id] = slot
    return slot_map


def _validate_required_slot_values(
    slot_map: Dict[str, Dict[str, Any]],
    slot_values: Dict[str, Any],
    template_id: str,
) -> None:
    missing_slot_ids = [
        slot_id
        for slot_id, slot in slot_map.items()
        if slot.get("required", True) is not False and slot_id not in slot_values
    ]
    if missing_slot_ids:
        raise make_error(
            "R_MISSING_SLOT",
            "缺少必填槽位素材",
            details={
                "template_id": template_id,
                "missing_slot_ids": missing_slot_ids,
            },
        )


def _validate_slot_values_in_config(
    slot_map: Dict[str, Dict[str, Any]],
    slot_values: Dict[str, Any],
    template_id: str,
) -> None:
    for slot_id in slot_values:
        if slot_id not in slot_map:
            raise make_error(
                "S_INVALID_SLOT",
                f"槽位 {slot_id} 未在配置中",
                details={"slot_id": slot_id, "template_id": template_id},
            )


def _get_slot_type(slot: Dict[str, Any], template_id: str) -> str:
    slot_type = slot.get("type")
    if not slot_type:
        raise make_error(
            "S_INVALID_SLOT",
            "槽位配置缺少 type",
            details={"template_id": template_id, "slot_id": slot.get("slot_id"), "slot": slot},
        )
    if slot_type not in {"video", "audio", "bgm", "subtitle", "text", "cover_image", "cover_title"}:
        raise make_error(
            "S_INVALID_SLOT",
            f"未知槽位类型: {slot_type}",
            details={
                "template_id": template_id,
                "slot_id": slot.get("slot_id"),
                "slot_type": slot_type,
            },
        )
    return slot_type


def _validate_render_slot_config(script, slot: Dict[str, Any], template_id: str):
    slot_type = _get_slot_type(slot, template_id)

    if slot_type in ("cover_image", "cover_title"):
        segment_index = slot_resolver.parse_slot_segment_index(slot)
        validation_slot = dict(slot)
        validation_slot["type"] = "video" if slot_type == "cover_image" else "subtitle"
        track = slot_resolver.resolve_slot_to_track(script, validation_slot)
        slot_resolver.validate_slot_segment_index(
            track, segment_index, slot.get("slot_id", "")
        )
        return slot_type, track

    track = slot_resolver.resolve_slot_to_track(script, slot)
    for segment_index in slot_resolver.parse_slot_segment_indices(slot):
        slot_resolver.validate_slot_segment_index(
            track, segment_index, slot.get("slot_id", "")
        )
    return slot_type, track


def _copy_template_resources_to_output(draft_content_path: str, output_dir: str) -> None:
    """Create a complete Jianying 10.x draft folder without copying source media."""
    if not Path(draft_content_path).is_file():
        raise make_error(
            "R_GENERATE_FAILED",
            "母版 draft_content.json 不存在",
            details={"draft_content_path": str(draft_content_path)},
        )

    profile = get_draft_profile("jianying_pro_10")
    project_root = Path(__file__).resolve().parents[3]
    skeleton_dir = project_root / profile.template_dir
    if not skeleton_dir.is_dir():
        raise make_error(
            "R_GENERATE_FAILED",
            f"剪映草稿骨架目录不存在: {profile.template_dir}",
            details={"template_dir": profile.template_dir},
        )

    target_dir = Path(output_dir)
    shutil.copytree(skeleton_dir, target_dir, dirs_exist_ok=True)


def _prepare_rendered_draft_identity(script, output_draft_name: str) -> None:
    """Give the rendered draft its own identity instead of reusing the source draft ID."""
    content = getattr(script, "content", None)
    if not isinstance(content, dict):
        return

    now_us = time.time_ns() // 1_000
    content.update({
        "id": str(uuid.uuid4()).upper(),
        "name": output_draft_name,
        "create_time": now_us,
        "update_time": now_us,
    })


def _write_rendered_draft_package(script, output_dir: str, output_draft_name: str) -> None:
    """Write root content, mirrors, timeline content and draft-list metadata."""
    profile = get_draft_profile("jianying_pro_10")
    target_dir = Path(output_dir)
    draft_json_path = target_dir / profile.content_file

    dumps = getattr(script, "dumps", None)
    if callable(dumps):
        content = dumps(profile)
    else:
        script.dump(str(draft_json_path))
        content = draft_json_path.read_text(encoding="utf-8")

    write_profile_content(profile, target_dir, content)

    try:
        payload = json.loads(content)
    except (TypeError, ValueError) as exc:
        raise make_error(
            "R_GENERATE_FAILED",
            "生成的 draft_content.json 不是合法 JSON",
        ) from exc

    now_us = int(payload.get("update_time") or time.time_ns() // 1_000)
    meta_path = target_dir / "draft_meta_info.json"
    if meta_path.is_file():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta.update({
            "draft_id": str(payload.get("id") or ""),
            "draft_name": output_draft_name,
            "draft_timeline_materials_size": len(content.encode("utf-8")),
            "tm_draft_create": int(payload.get("create_time") or now_us),
            "tm_draft_modified": now_us,
            "tm_duration": int(payload.get("duration") or 0),
        })
        meta_path.write_text(
            json.dumps(meta, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )

    settings_path = target_dir / "draft_settings"
    if settings_path.is_file():
        now_seconds = now_us // 1_000_000
        settings = settings_path.read_text(encoding="utf-8")
        settings = re.sub(
            r"(?m)^draft_create_time=.*$",
            f"draft_create_time={now_seconds}",
            settings,
        )
        settings = re.sub(
            r"(?m)^draft_last_edit_time=.*$",
            f"draft_last_edit_time={now_seconds}",
            settings,
        )
        settings_path.write_text(settings, encoding="utf-8")


# ─── 4 个核心函数 ──────────────────────────────────────────────────────────


def import_draft_content(template_id: str, content: bytes) -> ImportTemplateResponse:
    """导入单个 draft_content.json bytes，不上传母版 ZIP。"""
    _validate_template_id(template_id)

    cfg = load_config()
    max_bytes = int(getattr(cfg, "max_draft_content_mb", 20)) * 1024 * 1024
    if len(content) > max_bytes:
        raise make_error(
            "T_DRAFT_CONTENT_TOO_LARGE",
            details={
                "content_length": len(content),
                "max_bytes": max_bytes,
                "max_draft_content_mb": getattr(cfg, "max_draft_content_mb", 20),
            },
        )

    plain_content, encrypted_input = _load_draft_content_bytes(
        content,
        dll_path=getattr(cfg, "jianying_decrypt_dll_path", ""),
    )
    stage = storage.stage_template_draft_content(
        template_id,
        plain_content,
        encrypted_input=encrypted_input,
    )
    committed = False
    try:
        with storage.template_lock(template_id):
            draft_content_path = storage.require_template_draft_content_path_from_dir(
                template_id, stage.extract_dir
            )
            try:
                script = draft.Script_file.load_template(draft_content_path)
                slots = _scan_slots_from_template(script)
            except Exception as exc:
                raise _draft_content_import_semantic_error(template_id, exc) from exc
            storage.commit_staged_draft_content(stage)
            committed = True
            _restore_saved_slot_selections(template_id, slots)
    finally:
        if not committed:
            storage.cleanup_staged_draft_content(stage)

    return ImportTemplateResponse(
        template_id=template_id,
        slots=slots,
        message=f"模板 {template_id} 导入成功，共识别 {len(slots)} 条轨道",
    )


def import_template(template_id: str, uploaded_zip_path: str) -> ImportTemplateResponse:
    """导入母版 ZIP。

    流程：校验 template_id → extract_template_zip → get_template_draft_content_path
    → load_template → _scan_slots_from_template → 返回响应。

    非法 template_id → TemplateError（含"非法"）。
    """
    _validate_template_id(template_id)

    stage = storage.stage_extract_template_zip(template_id, uploaded_zip_path)
    committed = False
    try:
        with storage.template_lock(template_id):
            # 获取 staging draft_content.json 路径
            try:
                draft_content_path = storage.require_template_draft_content_path_from_dir(
                    template_id, stage.extract_dir
                )
            except TemplateError as exc:
                raise _map_missing_draft_content(template_id, exc) from exc

            # 加载模板并扫描槽位，语义校验成功后才提交 staging
            try:
                script = draft.Script_file.load_template(draft_content_path)
                slots = _scan_slots_from_template(script)
            except Exception as exc:
                raise _template_import_semantic_error(template_id, exc) from exc
            storage.commit_staged_template(stage)
            committed = True
            _restore_saved_slot_selections(template_id, slots)
    finally:
        if not committed:
            storage.cleanup_staged_template(stage)

    return ImportTemplateResponse(
        template_id=template_id,
        slots=slots,
        message=f"模板 {template_id} 导入成功，共识别 {len(slots)} 条轨道",
    )


def save_slot_config(template_id: str, req) -> SaveSlotConfigResponse:
    """保存槽位配置。

    流程：校验模板已导入 → 加载母版扫描已有槽位 → 校验每个 slot_id → 保存配置 → 返回响应。
    """
    _validate_template_id(template_id)

    with storage.template_lock(template_id):
        # 校验模板已导入（get_template_draft_content_path 不抛即存在）
        try:
            draft_content_path = storage.get_template_draft_content_path(template_id)
        except TemplateError as exc:
            raise _map_missing_draft_content(template_id, exc) from exc

        # 加载母版扫描已有槽位
        script = draft.Script_file.load_template(draft_content_path)
        existing_slots = _scan_slots_from_template(script)
        existing_slot_map = {s["slot_id"]: s for s in existing_slots}

        # 校验 req.slots 每个 slot_id 都在已有槽位集合中
        for slot_cfg in req.slots:
            if slot_cfg.slot_id not in existing_slot_map:
                raise make_error(
                    "S_INVALID_SLOT",
                    f"槽位 {slot_cfg.slot_id} 不存在于母版中",
                    details={"slot_id": slot_cfg.slot_id, "template_id": template_id},
                )
            if not existing_slot_map[slot_cfg.slot_id].get("replaceable"):
                raise make_error(
                    "S_TYPE_MISMATCH",
                    f"轨道 {slot_cfg.slot_id} 不支持素材替换",
                    details={"slot_id": slot_cfg.slot_id, "template_id": template_id},
                )

        saved_slots = []
        for slot_cfg in req.slots:
            canonical_slot = dict(existing_slot_map[slot_cfg.slot_id])
            canonical_slot["name"] = slot_cfg.name or canonical_slot["name"]
            if (
                canonical_slot.get("track_type") == "text"
                and slot_cfg.type in {"text", "subtitle"}
            ):
                canonical_slot["type"] = slot_cfg.type
            canonical_slot["required"] = slot_cfg.required
            saved_slots.append(canonical_slot)
        storage.save_slot_config(template_id, saved_slots)

    return SaveSlotConfigResponse(
        template_id=template_id,
        slot_count=len(req.slots),
        message=f"模板 {template_id} 槽位配置已保存，共 {len(req.slots)} 个槽位",
    )


def render_draft(template_id: str, req) -> RenderDraftResponse:
    """渲染草稿（MVP 版本）。

    1. 加载母版 + 槽位配置
    2. 构建 slot_id → slot 映射
    3. 遍历 slot_values 按类型替换素材
    4. 按配音时长重建轨道并执行时长对齐检查
    5. 导出草稿 + 打包 zip
    """
    _validate_template_id(template_id)

    with storage.template_lock(template_id):
        # 1. 加载母版 + 槽位配置
        try:
            draft_content_path = storage.get_template_draft_content_path(template_id)
        except TemplateError as exc:
            raise _map_missing_draft_content(template_id, exc) from exc
        script = draft.Script_file.load_template(draft_content_path)
        try:
            slots_config = storage.load_slot_config(template_id)
        except SlotError as exc:
            raise _map_missing_slot_config(template_id, exc) from exc

        # 2. 构建 slot_id → slot dict 映射
        slot_map = _build_slot_map(slots_config, template_id)
        validated_slots = {
            slot_id: _validate_render_slot_config(script, slot, template_id)
            for slot_id, slot in slot_map.items()
        }
        _validate_slot_values_in_config(slot_map, req.slot_values, template_id)
        _validate_required_slot_values(slot_map, req.slot_values, template_id)
        requested_audio_target = _requested_audio_target_duration(
            slot_map,
            req.slot_values,
        )

        warnings: List[str] = []
        video_duration_entries: List[tuple[int, str, int, float]] = []
        audio_durations: List[float] = []
        bgm_durations: List[float] = []
        subtitle_latest_end_seconds: Optional[float] = None
        preserved_track_ids: set[int] = set()

        # 3. 遍历 slot_values，按槽位类型处理
        for slot_id, value in req.slot_values.items():
            slot = slot_map[slot_id]
            slot_type, track = validated_slots[slot_id]

            if slot_type in ("video", "audio", "bgm"):
                if slot_type == "video":
                    material_values = _track_video_material_values(slot, value)
                    if material_values is not None:
                        clip_durations = _replace_video_track_materials(
                            script,
                            track,
                            slot,
                            material_values,
                            requested_audio_target,
                        )
                        for segment_index, duration in enumerate(clip_durations):
                            video_duration_entries.append((
                                int(slot.get("_slot_index", 0)),
                                str(slot.get("track_name", "")),
                                segment_index,
                                duration,
                            ))
                    else:
                        segment_index = slot_resolver.parse_slot_segment_index(slot)
                        mat = material_builder.build_video_material_from_metadata(value)
                        _replace_slot_material(script, track, slot, mat, segment_index)
                        duration = _metadata_duration_seconds(value)
                        if duration is not None:
                            video_duration_entries.append((
                                int(slot.get("_slot_index", 0)),
                                str(slot.get("track_name", "")),
                                segment_index,
                                duration,
                            ))
                else:
                    mat = material_builder.build_audio_material_from_metadata(value)
                    _replace_slot_material(script, track, slot, mat)
                    if slot_type == "audio":
                        _expand_audio_segment_to_material(
                            script,
                            track,
                            slot_resolver.parse_slot_segment_index(slot),
                            mat,
                        )
                    duration = _metadata_duration_seconds(value)
                    if duration is not None and slot_type == "bgm":
                        bgm_durations.append(duration)
                    elif duration is not None:
                        audio_durations.append(duration)
            elif slot_type in ("subtitle", "text"):
                if slot_type == "text" or _has_text_content_value(value):
                    _replace_text_slot(script, track, slot, value)
                else:
                    latest_end = _import_subtitle_srt(script, track, slot, value)
                    preserved_track_ids.add(id(track))
                    subtitle_latest_end_seconds = max(
                        subtitle_latest_end_seconds or 0.0,
                        latest_end,
                    )
            elif slot_type in ("cover_image", "cover_title"):
                warnings.append(f"封面槽位 {slot_id} 替换暂未实现（MVP）")

        # 4. 合并时长对齐产生的非致命 warning，并刷新草稿总时长。
        video_durations = [
            duration
            for *_sort_key, duration in sorted(video_duration_entries)
        ]
        target_duration = _select_alignment_target(
            video_durations,
            audio_durations,
            bgm_durations,
            subtitle_latest_end_seconds,
        )
        _merge_duration_alignment_warnings(
            warnings,
            video_durations,
            bgm_durations,
            target_duration,
        )
        _align_non_media_track_ends_to_target(
            script,
            target_duration,
            preserved_track_ids=preserved_track_ids,
        )
        _update_script_duration(script)

        # 5. 导出草稿
        draft_id = f"draft_{uuid.uuid4().hex[:16]}"
        cfg = load_config()
        output_dir = os.path.join(cfg.generated_draft_folder, draft_id)
        _prepare_rendered_draft_identity(script, req.output_draft_name)
        _copy_template_resources_to_output(draft_content_path, output_dir)
        _write_rendered_draft_package(script, output_dir, req.output_draft_name)

        # 6. 打包 zip
        storage.save_generated_draft_zip(draft_id, output_dir)

    # 7. 返回
    return RenderDraftResponse(
        draft_id=draft_id,
        download_url=f"/api/template/download/{draft_id}",
        warnings=warnings,
    )


def download_draft(draft_id: str) -> DownloadDraftResponse:
    """下载草稿。

    校验 draft_id 非空 → get_generated_draft_zip_path
    → None 时 RenderError（含"不存在"）→ 返回 DownloadDraftResponse。
    """
    _validate_draft_id(draft_id)

    zip_path = storage.get_generated_draft_zip_path(draft_id)
    if zip_path is None:
        raise make_error("R_TASK_NOT_FOUND", details={"draft_id": draft_id})

    return DownloadDraftResponse(
        draft_id=draft_id,
        download_url=f"/api/template/download/{draft_id}",
        message=f"草稿 {draft_id} 下载就绪",
    )

"""样式提取器（MVP 简化版）：从文本轨道片段提取基础样式。

MVP 不强求对象返回，退化为纯 dict。样式提取失败不应阻塞生成。
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def extract_subtitle_style_from_track(track, segment_index: int = 0) -> dict:
    """MVP：从文本轨道片段的 raw_data 尝试提取基础样式；失败返回安全默认值。

    返回 {"text_style": ..., "clip_settings": ..., "border": None, "font": None}。
    若 track 无 segments 或 segment_index 越界或无 raw_data → 返回默认值。
    不抛异常（样式提取失败不应阻塞生成）。

    Args:
        track: 轨道对象（需要有 .segments 列表）。
        segment_index: 片段索引，默认 0。

    Returns:
        样式字典。
    """
    default = _default_style()

    # 安全检查
    if not hasattr(track, "segments") or not track.segments:
        return default
    if segment_index < 0 or segment_index >= len(track.segments):
        return default

    segment = track.segments[segment_index]

    # 尝试从 raw_data 提取
    raw_data = getattr(segment, "raw_data", None)
    if not raw_data or not isinstance(raw_data, dict):
        return default

    try:
        return _extract_from_raw_data(raw_data)
    except Exception:
        return default


def _default_style() -> dict:
    """返回安全默认值（MVP 退化为纯 dict）。"""
    return {
        "text_style": {"size": 5.0, "align": 1},
        "clip_settings": {"transform_y": -0.8},
        "border": None,
        "font": None,
    }


def _extract_from_raw_data(raw_data: Dict[str, Any]) -> dict:
    """从 raw_data 中提取样式信息。

    目前 MVP 只尝试读取 material_id 关联的文本素材数据。
    如果无法提取，返回默认值。
    """
    result = _default_style()

    # 尝试从 clip 提取 clip_settings
    clip = raw_data.get("clip")
    if clip and isinstance(clip, dict):
        transform = clip.get("transform", {})
        scale = clip.get("scale", {})
        result["clip_settings"] = {
            "transform_x": transform.get("x", 0.0),
            "transform_y": transform.get("y", -0.8),
            "scale_x": scale.get("x", 1.0),
            "scale_y": scale.get("y", 1.0),
        }

    return result

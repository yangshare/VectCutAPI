"""素材构造器：绕过 ffprobe，用元数据直接构造 Video/Audio/Image 素材。

核心约束：构造过程不访问文件系统（用不存在的路径也能成功）。
"""

from __future__ import annotations

import os
from typing import Any

from pyJianYingDraft.local_materials import Audio_material, Video_material

from vectcut.core.errors import make_error

_INVALID_METADATA_CODE = "R_INVALID_MATERIAL_METADATA"


def _require_metadata_dict(metadata: Any, *, material_type: str) -> dict:
    if not isinstance(metadata, dict):
        raise make_error(
            _INVALID_METADATA_CODE,
            "素材元数据必须是对象",
            details={
                "material_type": material_type,
                "field": "metadata",
                "metadata_type": type(metadata).__name__,
            },
        )
    return metadata


def _require_path(metadata: dict, *, material_type: str) -> str:
    path = metadata.get("path")
    if not isinstance(path, str) or not path.strip():
        raise make_error(
            _INVALID_METADATA_CODE,
            "素材路径缺失或非法",
            details={"material_type": material_type, "field": "path"},
        )
    return path


def _require_positive_number(
    metadata: dict,
    field: str,
    *,
    material_type: str,
) -> float:
    value: Any = metadata.get(field)
    if isinstance(value, bool):
        value = None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = 0.0
    if numeric <= 0:
        raise make_error(
            _INVALID_METADATA_CODE,
            f"素材字段 {field} 缺失或非法",
            details={"material_type": material_type, "field": field},
        )
    return numeric


def _require_positive_int(metadata: dict, field: str, *, material_type: str) -> int:
    numeric = _require_positive_number(
        metadata,
        field,
        material_type=material_type,
    )
    if not numeric.is_integer():
        raise make_error(
            _INVALID_METADATA_CODE,
            f"素材字段 {field} 缺失或非法",
            details={"material_type": material_type, "field": field},
        )
    return int(numeric)


def build_video_material_from_metadata(metadata: dict) -> Video_material:
    """用元数据构造视频素材，绕过 ffprobe。

    Args:
        metadata: {path, duration, width, height}。
            path: 素材文件路径（不需要实际存在）。
            duration: 时长（秒）。
            width: 宽度（像素）。
            height: 高度（像素）。

    Returns:
        Video_material 实例，path 已设置，remote_url 为 None。
    """
    metadata = _require_metadata_dict(metadata, material_type="video")
    path = _require_path(metadata, material_type="video")
    duration = _require_positive_number(
        metadata,
        "duration",
        material_type="video",
    )
    width = _require_positive_int(metadata, "width", material_type="video")
    height = _require_positive_int(metadata, "height", material_type="video")

    mat = Video_material(
        material_type="video",
        remote_url="placeholder://metadata",
        material_name=os.path.basename(path),
        duration=duration,
        width=width,
        height=height,
    )
    mat.path = path
    mat.remote_url = None
    return mat


def build_audio_material_from_metadata(metadata: dict) -> Audio_material:
    """用元数据构造音频素材，绕过 ffprobe。

    Args:
        metadata: {path, duration}。
            path: 素材文件路径（不需要实际存在）。
            duration: 时长（秒）。

    Returns:
        Audio_material 实例，path 已设置，remote_url 为 None。
    """
    metadata = _require_metadata_dict(metadata, material_type="audio")
    path = _require_path(metadata, material_type="audio")
    duration = _require_positive_number(
        metadata,
        "duration",
        material_type="audio",
    )

    mat = Audio_material(
        remote_url="placeholder://metadata",
        material_name=os.path.basename(path),
        duration=duration,
    )
    mat.path = path
    mat.remote_url = None
    return mat


def build_image_material_from_metadata(metadata: dict) -> Video_material:
    """用元数据构造图片素材，绕过 ffprobe。

    图片素材复用 Video_material，material_type="photo"，duration=0.0。

    Args:
        metadata: {path, width, height}。
            path: 素材文件路径（不需要实际存在）。
            width: 宽度（像素）。
            height: 高度（像素）。

    Returns:
        Video_material 实例（material_type="photo"），path 已设置，remote_url 为 None。
    """
    metadata = _require_metadata_dict(metadata, material_type="image")
    path = _require_path(metadata, material_type="image")
    width = _require_positive_int(metadata, "width", material_type="image")
    height = _require_positive_int(metadata, "height", material_type="image")

    mat = Video_material(
        material_type="photo",
        remote_url="placeholder://metadata",
        material_name=os.path.basename(path),
        duration=0.0,
        width=width,
        height=height,
    )
    # photo 分支会忽略传入的 width/height，需手动覆盖（下载时会用真实值再覆盖）
    mat.path = path
    mat.remote_url = None
    mat.width = width
    mat.height = height
    return mat

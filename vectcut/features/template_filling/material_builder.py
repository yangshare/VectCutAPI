"""素材构造器：绕过 ffprobe，用元数据直接构造 Video/Audio/Image 素材。

核心约束：构造过程不访问文件系统（用不存在的路径也能成功）。
"""

from __future__ import annotations

import os

from pyJianYingDraft.local_materials import Audio_material, Video_material


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
    path = metadata["path"]
    duration = metadata["duration"]
    width = metadata["width"]
    height = metadata["height"]

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
    path = metadata["path"]
    duration = metadata["duration"]

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
    path = metadata["path"]
    width = metadata["width"]
    height = metadata["height"]

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

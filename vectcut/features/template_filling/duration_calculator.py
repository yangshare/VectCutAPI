"""时长对齐算法：视频循环填充 + BGM 对齐。

纯算法模块，不依赖文件系统或外部服务。
"""

from __future__ import annotations

from vectcut.core.errors import RenderError


def calculate_video_loop_fill(
    video_segments_durations: list[float],
    target_duration: float,
    max_loop_count: int = 10,
    min_last_segment_duration: float = 2.0,
) -> tuple[list[float], list[str]]:
    """计算视频循环填充策略。

    - 视频总时长 >= target → 截断（保留完整段，最后一段截到 target）
    - 视频总时长 < target → 用最后一段循环填满
    - 最后一段 < min_last_segment_duration 且需循环 → 追加 warning
    - 循环次数 > max_loop_count → 抛 RenderError
    - 空列表 → RenderError

    Args:
        video_segments_durations: 各视频片段时长列表（秒）。
        target_duration: 目标总时长（秒）。
        max_loop_count: 最大循环次数，默认 10。
        min_last_segment_duration: 最后一段最短自然时长阈值，默认 2.0 秒。

    Returns:
        (调整后时长列表, warnings)

    Raises:
        RenderError: 空列表或循环次数超限。
    """
    if not video_segments_durations:
        raise RenderError("视频片段时长列表为空")

    if target_duration <= 0:
        raise RenderError("目标时长必须大于 0")

    warnings: list[str] = []
    total = sum(video_segments_durations)

    # 总时长 >= target：截断
    if total >= target_duration:
        result: list[float] = []
        accumulated = 0.0
        for dur in video_segments_durations:
            if accumulated + dur > target_duration:
                # 需要截断当前段
                result.append(target_duration - accumulated)
                break
            else:
                # accumulated + dur == target 恰好相等时保留完整段
                # accumulated + dur < target 时也保留完整段
                result.append(dur)
                accumulated += dur
        return result, warnings

    # 总时长 < target：循环最后一段填满
    last_dur = video_segments_durations[-1]
    if last_dur <= 0:
        raise RenderError("最后一段时长必须大于 0")

    # 计算需要循环多少次
    remaining = target_duration - total
    loop_count = 0
    while remaining > 0:
        remaining -= last_dur
        loop_count += 1

    if loop_count > max_loop_count:
        raise RenderError(
            f"循环次数 {loop_count} 超过限制 {max_loop_count}"
        )

    if last_dur < min_last_segment_duration:
        warnings.append(
            f"最后一段时长 {last_dur:.1f}s 不自然（低于 {min_last_segment_duration}s），循环可能不自然"
        )

    # 构建结果：原始段 + 循环段
    result = list(video_segments_durations)
    remaining = target_duration - total
    while remaining > 0:
        if remaining >= last_dur:
            result.append(last_dur)
            remaining -= last_dur
        else:
            result.append(remaining)
            remaining = 0

    return result, warnings


def calculate_bgm_alignment(
    bgm_duration: float,
    target_duration: float,
    min_bgm_for_loop: float = 10.0,
) -> tuple[float, list[str]]:
    """BGM 对齐：>= target 截断返回 target；< target 循环铺满返回 target。

    bgm_duration < min_bgm_for_loop 且需循环 → warning（含"过短"）。

    Args:
        bgm_duration: BGM 时长（秒）。
        target_duration: 目标时长（秒）。
        min_bgm_for_loop: 循环时 BGM 最短时长阈值，默认 10.0 秒。

    Returns:
        (对齐后时长, warnings)
    """
    warnings: list[str] = []

    if bgm_duration >= target_duration:
        return target_duration, warnings

    # bgm_duration < target_duration，需要循环
    if bgm_duration < min_bgm_for_loop:
        warnings.append(
            f"BGM 时长 {bgm_duration:.1f}s 过短（低于 {min_bgm_for_loop}s），循环可能不自然"
        )

    return target_duration, warnings

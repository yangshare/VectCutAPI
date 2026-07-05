"""时长对齐算法测试：覆盖 7 种边界。"""

from __future__ import annotations

import pytest

from vectcut.core.errors import RenderError
from vectcut.features.template_filling.duration_calculator import (
    calculate_bgm_alignment,
    calculate_video_loop_fill,
)


class TestCalculateVideoLoopFill:
    def test_video_longer_than_target_truncate_no_warning(self):
        """1. 视频总时长 > target → 截断，无 warning。"""
        result, warnings = calculate_video_loop_fill([5.0, 5.0, 5.0], target_duration=11.0)
        # 总 15s > 11s：保留 5+5，最后一段截 1s
        assert result == [5.0, 5.0, 1.0]
        assert warnings == []

    def test_video_shorter_than_target_loop_last_segment(self):
        """2. 视频总时长 < target → 循环最后一段。"""
        result, warnings = calculate_video_loop_fill([3.0, 4.0], target_duration=15.0)
        # 总 7s < 15s，需循环最后一段 4s 填满
        # 7 + 4 = 11, 11 + 4 = 15
        assert result == [3.0, 4.0, 4.0, 4.0]
        assert all("不自然" not in w for w in warnings)

    def test_last_segment_short_loop_triggers_warning(self):
        """3. 最后一段 < 2s 且需循环 → warning（含"不自然"）。"""
        result, warnings = calculate_video_loop_fill(
            [5.0, 1.0], target_duration=12.0
        )
        # 总 6s < 12s，最后一段 1s < 2s
        # 6 + 1 = 7, +1=8, +1=9, +1=10, +1=11, +1=12 → 6 次循环
        assert sum(result) == pytest.approx(12.0)
        assert any("不自然" in w for w in warnings)

    def test_loop_count_exceeds_max_raises_render_error(self):
        """4. 循环次数 > 10 → RenderError（含"超过限制"）。"""
        with pytest.raises(RenderError, match="超过限制"):
            # 总 1s, 最后一段 0.1s, target=10s → 需要 ~89 次循环
            calculate_video_loop_fill(
                [0.9, 0.1], target_duration=10.0, max_loop_count=10
            )

    def test_empty_list_raises_render_error(self):
        """5. 视频空 → RenderError（含"为空"）。"""
        with pytest.raises(RenderError, match="为空"):
            calculate_video_loop_fill([], target_duration=10.0)

    def test_truncate_exact_boundary_keeps_full_segment(self):
        """恰好相等时保留完整段（不截断到 0）。"""
        result, _ = calculate_video_loop_fill([5.0, 5.0], target_duration=10.0)
        # accumulated=5, 5+5=10 == target → 保留完整段
        assert result == [5.0, 5.0]

    def test_truncate_at_first_segment(self):
        """只有一段且超过 target：截断该段。"""
        result, _ = calculate_video_loop_fill([15.0], target_duration=10.0)
        assert result == [10.0]


class TestCalculateBgmAlignment:
    def test_bgm_longer_than_target_truncate_no_warning(self):
        """6. BGM > target → 截断返回 target，无 warning。"""
        aligned, warnings = calculate_bgm_alignment(
            bgm_duration=30.0, target_duration=15.0
        )
        assert aligned == 15.0
        assert warnings == []

    def test_bgm_short_needs_loop_triggers_warning(self):
        """7. BGM < 10s 且需循环 → 返回 target + warning（含"过短"）。"""
        aligned, warnings = calculate_bgm_alignment(
            bgm_duration=5.0, target_duration=20.0
        )
        assert aligned == 20.0
        assert any("过短" in w for w in warnings)

    def test_bgm_long_but_needs_loop_no_warning(self):
        """BGM >= min_bgm_for_loop 但需循环：无 warning。"""
        aligned, warnings = calculate_bgm_alignment(
            bgm_duration=15.0, target_duration=20.0, min_bgm_for_loop=10.0
        )
        assert aligned == 20.0
        assert warnings == []

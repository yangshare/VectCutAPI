"""add_video_keyframe service 正常路径回归测试。

覆盖 vectcut/features/video/service.py:add_video_keyframe 中 track 查找逻辑：
- 默认 track_name="video_main"（add_video 创建的普通轨道，存于 script.tracks）
- 批量模式 property_types/times/values 等长三参

回归背景：重构后误用 get_imported_track（只查 imported_tracks），导致
默认 video_main 轨道永远报 "Track named video_main not found"。
此测试固化 add_video → add_video_keyframe 的可用调用链路。
"""
import pytest

from vectcut.core import draft_store


@pytest.fixture(autouse=True)
def _clean_cache():
    draft_store.DRAFT_CACHE.clear()
    yield
    draft_store.DRAFT_CACHE.clear()


def _make_draft_then_video(video_url="https://example.com/v.mp4"):
    """建一个草稿并添加 video，返回 draft_id（含 video_main 轨道+1 段）。"""
    from vectcut.features.video import service
    from vectcut.features.video.schemas import AddVideoRequest

    vresp = service.add_video(AddVideoRequest(video_url=video_url))
    return vresp.draft_id


def test_add_video_keyframe_batch_on_default_track_calls_add_pending_keyframe(monkeypatch):
    """批量模式：在 add_video 创建的默认 video_main 轨道上加关键帧，
    track.add_pending_keyframe 应对每个 (property_type, time, value) 各调用一次。"""
    from vectcut.features.video import service
    from vectcut.features.video.schemas import AddVideoKeyframeRequest

    draft_id = _make_draft_then_video()
    script = draft_store.get_draft(draft_id)

    # 拦截 Track.add_pending_keyframe，记录调用
    calls = []
    video_main_track = script.get_track(
        __import__("pyJianYingDraft").Video_segment, track_name="video_main"
    )
    monkeypatch.setattr(
        video_main_track, "add_pending_keyframe",
        lambda pt, t, v: calls.append((pt, t, v)),
    )

    resp = service.add_video_keyframe(AddVideoKeyframeRequest(
        draft_id=draft_id,
        track_name="video_main",
        property_types=["scale_x", "scale_y", "alpha"],
        times=[0, 2, 4],
        values=["1.0", "1.2", "0.8"],
    ))

    assert resp.draft_id == draft_id
    assert resp.draft_url  # 生成下载链接
    assert calls == [("scale_x", 0, "1.0"),
                     ("scale_y", 2, "1.2"),
                     ("alpha", 4, "0.8")]


def test_add_video_keyframe_single_on_default_track():
    """单关键帧模式（property_type/time/value）在默认 video_main 轨道可用。"""
    from vectcut.features.video import service
    from vectcut.features.video.schemas import AddVideoKeyframeRequest

    draft_id = _make_draft_then_video()
    resp = service.add_video_keyframe(AddVideoKeyframeRequest(
        draft_id=draft_id,
        track_name="video_main",
        property_type="alpha",
        time=1.0,
        value="0.5",
    ))
    assert resp.draft_id == draft_id


def test_add_video_keyframe_missing_track_raises_invalid_param():
    """草稿无对应轨道时抛 InvalidParam（错误信息含轨道名）。"""
    from vectcut.features.video import service
    from vectcut.features.video.schemas import AddVideoKeyframeRequest
    from vectcut.core.errors import InvalidParam

    draft_id = _make_draft_then_video()
    with pytest.raises(InvalidParam) as exc:
        service.add_video_keyframe(AddVideoKeyframeRequest(
            draft_id=draft_id,
            track_name="non_existent_track",
            property_type="alpha",
            time=0.0,
            value="1.0",
        ))
    assert "non_existent_track" in str(exc.value)

from vectcut.features.video.schemas import AddVideoRequest, AddVideoResponse, AddVideoKeyframeRequest


def test_add_video_request_defaults():
    r = AddVideoRequest(video_url="https://e.com/v.mp4")
    assert r.video_url == "https://e.com/v.mp4"
    assert r.width == 1080
    assert r.height == 1920
    assert r.start == 0
    assert r.track_name == "video_main"
    assert r.volume == 1.0
    assert r.transition is None
    assert r.mask_type is None


def test_add_video_keyframe_request_defaults():
    r = AddVideoKeyframeRequest(draft_id="dfd_1")
    assert r.draft_id == "dfd_1"
    assert r.track_name == "video_main"
    assert r.property_type == "alpha"
    assert r.value == "1.0"

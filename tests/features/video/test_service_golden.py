"""add_video service 层黄金：固定输入 → script.dumps() 快照。迁移 FastAPI 后 service 不变则 dumps 不变。"""
import re

import pytest

from vectcut.core import draft_store

# 引擎为 materials/segments/speeds 等生成随机 32 位 hex UUID，跨 run 不稳定。
# 归一化为占位符，使快照反映 service 结构而非随机 ID。
_UUID_RE = re.compile(r"\b[0-9a-f]{32}\b")


def _normalize_dumps(dumps: str) -> str:
    return _UUID_RE.sub("PLACEHOLDER_UUID", dumps)


@pytest.fixture(autouse=True)
def _clean_cache():
    draft_store.DRAFT_CACHE.clear()
    yield
    draft_store.DRAFT_CACHE.clear()


def test_add_video_dumps_golden(snapshot_dir, regenerate_golden):
    from vectcut.features.video import service
    from vectcut.features.video.schemas import AddVideoRequest
    from vectcut.core.draft_store import get_active_profile

    resp = service.add_video(AddVideoRequest(
        video_url="https://example.com/golden.mp4",
        start=0, end=3.0,
        track_name="video_main",
    ))
    script = draft_store.get_draft(resp.draft_id)
    dumps = _normalize_dumps(script.dumps(get_active_profile()))
    snap_path = snapshot_dir / "video_add_video_dumps.json"
    if regenerate_golden:
        snap_path.write_text(dumps, encoding="utf-8")
        pytest.skip("golden regenerated")
    assert snap_path.exists(), "快照缺失：运行 REGENERATE_GOLDEN=1 生成"
    expected = snap_path.read_text(encoding="utf-8")
    assert dumps == expected, "add_video 的 script.dumps() 与黄金基线不一致"

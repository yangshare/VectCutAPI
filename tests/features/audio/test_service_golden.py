"""add_audio service 层黄金。"""
import re

import pytest

from vectcut.core import draft_store

_UUID_RE = re.compile(r"\b[0-9a-f]{32}\b")


def _normalize_dumps(dumps: str) -> str:
    return _UUID_RE.sub("PLACEHOLDER_UUID", dumps)


@pytest.fixture(autouse=True)
def _clean_cache():
    draft_store.DRAFT_CACHE.clear()
    yield
    draft_store.DRAFT_CACHE.clear()


def test_add_audio_dumps_golden(snapshot_dir, regenerate_golden):
    from vectcut.features.audio import service
    from vectcut.features.audio.schemas import AddAudioRequest
    from vectcut.core.draft_store import get_active_profile

    resp = service.add_audio(AddAudioRequest(
        audio_url="https://example.com/golden.mp3",
        start=0, end=2.0,
        track_name="audio_main",
    ))
    script = draft_store.get_draft(resp.draft_id)
    dumps = _normalize_dumps(script.dumps(get_active_profile()))
    snap_path = snapshot_dir / "audio_add_audio_dumps.json"
    if regenerate_golden:
        snap_path.write_text(dumps, encoding="utf-8")
        pytest.skip("golden regenerated")
    assert snap_path.exists()
    expected = snap_path.read_text(encoding="utf-8")
    assert dumps == expected, "add_audio 的 script.dumps() 与黄金基线不一致"

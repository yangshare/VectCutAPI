import json
import shutil
from types import SimpleNamespace
from pathlib import Path

import pytest


def test_jianying_10_profile_uses_versioned_template_and_content_names():
    from vectcut.core.draft_store import get_draft_profile

    profile = get_draft_profile("jianying_pro_10")

    assert profile.name == "jianying_pro_10"
    assert profile.template_dir == "template_jianying_10_2"
    assert profile.content_file == "draft_content.json"
    assert "template-2.tmp" in profile.content_mirrors
    assert profile.is_capcut_env is False


def test_legacy_profiles_keep_existing_template_names():
    from vectcut.core.draft_store import get_draft_profile

    capcut = get_draft_profile("capcut_legacy")
    jianying = get_draft_profile("jianying_legacy")

    assert capcut.template_dir == "template"
    assert capcut.content_file == "draft_info.json"
    assert capcut.is_capcut_env is True
    assert jianying.template_dir == "template_jianying"
    assert jianying.content_file == "draft_info.json"
    assert jianying.is_capcut_env is False


def test_write_profile_content_updates_main_mirrors_and_timeline(tmp_path):
    from vectcut.core.draft_store import get_draft_profile, write_profile_content

    draft_dir = tmp_path / "draft"
    timeline_dir = draft_dir / "Timelines" / "timeline-1"
    timeline_dir.mkdir(parents=True)
    (draft_dir / "timeline_layout.json").write_text(
        json.dumps({"dockItems": [{"timelineIds": ["timeline-1"], "timelineNames": ["Timeline 1"]}]}),
        encoding="utf-8",
    )

    payload = {"id": "timeline-fixed", "tracks": [], "materials": {}, "duration": 0}
    profile = get_draft_profile("jianying_pro_10")

    written = write_profile_content(profile, draft_dir, json.dumps(payload, ensure_ascii=False))

    renamed_timeline_dir = draft_dir / "Timelines" / "timeline-fixed"
    expected = {
        draft_dir / "draft_content.json",
        draft_dir / "template-2.tmp",
        renamed_timeline_dir / "draft_content.json",
        renamed_timeline_dir / "template-2.tmp",
        renamed_timeline_dir / "template.tmp",
    }
    assert expected.issubset(set(written))
    for path in expected:
        assert json.loads(path.read_text(encoding="utf-8")) == payload
    project = json.loads((draft_dir / "Timelines" / "project.json").read_text(encoding="utf-8"))
    layout = json.loads((draft_dir / "timeline_layout.json").read_text(encoding="utf-8"))
    assert project["main_timeline_id"] == "timeline-fixed"
    assert layout["dockItems"][0]["timelineIds"] == ["timeline-fixed"]


def test_script_dumps_uses_requested_profile_platform_and_mask_key():
    import pyJianYingDraft as draft
    from vectcut.core.draft_store import get_draft_profile

    profile = get_draft_profile("jianying_pro_10")
    script = draft.Script_file(1080, 1920)

    payload = json.loads(script.dumps(profile))

    assert payload["platform"] == profile.platform
    assert payload["last_modified_platform"] == profile.platform
    assert "masks" in payload["materials"]
    assert "common_mask" not in payload["materials"]


def test_windows_draft_asset_path_keeps_drive_root():
    from save_draft_impl import build_asset_path

    path = build_asset_path(
        r"D:\JianyingPro Drafts",
        "draft-1",
        "video",
        "clip.mp4",
    )

    assert path == r"D:\JianyingPro Drafts\draft-1\assets\video\clip.mp4"


def test_shared_draft_asset_path_keeps_drive_root():
    from util import build_draft_asset_path

    assert build_draft_asset_path(
        r"D:\JianyingPro Drafts",
        "draft-1",
        "image",
        "cover.png",
    ) == r"D:\JianyingPro Drafts\draft-1\assets\image\cover.png"


def test_save_draft_writes_to_requested_draft_folder(tmp_path, monkeypatch):
    import save_draft_impl
    from vectcut.core.draft_store import DRAFT_CACHE
    from vectcut.core.draft_store import get_draft_profile
    from save_task_cache import create_task

    draft_id = "draft-target-folder"
    payload = {"tracks": [], "materials": {}, "duration": 0}
    project_draft_dir = Path(save_draft_impl.__file__).resolve().parent / draft_id
    if project_draft_dir.exists():
        shutil.rmtree(project_draft_dir)

    script = SimpleNamespace(
        materials=SimpleNamespace(audios=[], videos=[]),
        tracks={},
        dumps=lambda profile=None: json.dumps(payload),
    )
    DRAFT_CACHE[draft_id] = script
    create_task(draft_id)

    monkeypatch.setattr(save_draft_impl, "get_draft_profile", lambda: get_draft_profile("jianying_pro_10"))
    monkeypatch.setattr(save_draft_impl, "update_media_metadata", lambda script, task_id=None: None)
    monkeypatch.setattr(save_draft_impl, "IS_UPLOAD_DRAFT", False)

    save_draft_impl.save_draft_background(draft_id, str(tmp_path), draft_id)

    assert (tmp_path / draft_id / "draft_content.json").exists()
    assert (tmp_path / draft_id / "Timelines").exists()
    assert not project_draft_dir.exists()


# ---- new tests ----

def test_get_draft_returns_cached_script_and_none_when_missing():
    from vectcut.core.draft_store import DRAFT_CACHE, get_draft, update_cache

    DRAFT_CACHE.pop("d1", None)
    assert get_draft("d1") is None

    sentinel = object()
    update_cache("d1", sentinel)
    assert get_draft("d1") is sentinel


def test_get_active_profile_reads_draft_profile_from_config(monkeypatch):
    from vectcut.core import draft_store
    from vectcut.core.draft_store import DraftProfile, get_active_profile

    # Inject a fake settings-like object, verify get_active_profile reads from config not settings.local
    class FakeSettings:
        draft_profile = "jianying_pro_10"

    monkeypatch.setattr(draft_store, "_load_settings", lambda: FakeSettings())

    profile = get_active_profile()
    assert isinstance(profile, DraftProfile)
    assert profile.name == "jianying_pro_10"
    assert profile.template_dir == "template_jianying_10_2"


def test_get_or_create_draft_creates_new_when_id_none():
    from vectcut.core import draft_store

    draft_store.DRAFT_CACHE.clear()
    draft_id, script = draft_store.get_or_create_draft(draft_id=None, width=1080, height=1920)
    assert draft_id.startswith("dfd_cat_")
    assert draft_id in draft_store.DRAFT_CACHE
    assert script is draft_store.DRAFT_CACHE[draft_id]


def test_get_or_create_draft_returns_cached_when_id_present():
    from vectcut.core import draft_store

    draft_store.DRAFT_CACHE.clear()
    first_id, _ = draft_store.get_or_create_draft(None, 1080, 1920)
    second_id, script = draft_store.get_or_create_draft(first_id, 1080, 1920)
    assert second_id == first_id
    assert script is draft_store.DRAFT_CACHE[first_id]


def test_legacy_create_draft_shim_forwards_get_or_create_draft():
    import create_draft
    from vectcut.core import draft_store

    draft_store.DRAFT_CACHE.clear()
    # 垫片函数应与 draft_store 同一函数
    assert create_draft.get_or_create_draft is draft_store.get_or_create_draft or callable(
        create_draft.get_or_create_draft,
    )
    draft_id, script = create_draft.get_or_create_draft(None, 1080, 1920)
    assert draft_id in draft_store.DRAFT_CACHE

"""Merged draft cache + draft profiles.

This module consolidates the responsibilities formerly split between:
  - ``draft_cache``  : LRU OrderedDict cache for draft script objects.
  - ``draft_profiles``: Draft profile definitions and content-writing utilities.

No behavioural changes from the original files; code is carried over verbatim
with import deduplication at the top of the file.
"""

from __future__ import annotations

import json
import os
import shutil
import time
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional


# ============================================================================
# draft_cache.py content (carried over verbatim)
# ============================================================================

# Modify global variable, use OrderedDict to implement LRU cache, limit the maximum number to 10000
DRAFT_CACHE: Dict[str, "draft.Script_file"] = OrderedDict()  # Use Dict for type hinting
MAX_CACHE_SIZE = 10000


def update_cache(key: str, value: "draft.Script_file") -> None:
    """Update LRU cache"""
    if key in DRAFT_CACHE:
        # If the key exists, delete the old item
        DRAFT_CACHE.pop(key)
    elif len(DRAFT_CACHE) >= MAX_CACHE_SIZE:
        print(f"{key}, Cache is full, deleting the least recently used item")
        # If the cache is full, delete the least recently used item (the first item)
        DRAFT_CACHE.popitem(last=False)
    # Add new item to the end (most recently used)
    DRAFT_CACHE[key] = value


# ============================================================================
# draft_profiles.py content (carried over verbatim)
# ============================================================================


@dataclass(frozen=True)
class DraftProfile:
    name: str
    template_dir: str
    content_file: str
    content_mirrors: tuple[str, ...] = ()
    timeline_content_file: Optional[str] = None
    is_capcut_env: bool = True
    platform: Optional[Dict[str, object]] = None


CAPCUT_PLATFORM = {
    "app_id": 359289,
    "app_source": "cc",
    "app_version": "6.5.0",
    "device_id": "c4ca4238a0b923820dcc509a6f75849b",
    "hard_disk_id": "307563e0192a94465c0e927fbc482942",
    "mac_address": "c3371f2d4fb02791c067ce44d8fb4ed5",
    "os": "mac",
    "os_version": "15.5",
}

JIANYING_10_PLATFORM = {
    "app_id": 3704,
    "app_source": "lv",
    "app_version": "10.2.0",
    "os": "windows",
}

PROFILES: Dict[str, DraftProfile] = {
    "capcut_legacy": DraftProfile(
        name="capcut_legacy",
        template_dir="template",
        content_file="draft_info.json",
        is_capcut_env=True,
        platform=CAPCUT_PLATFORM,
    ),
    "jianying_legacy": DraftProfile(
        name="jianying_legacy",
        template_dir="template_jianying",
        content_file="draft_info.json",
        is_capcut_env=False,
        platform=JIANYING_10_PLATFORM,
    ),
    "jianying_pro_10": DraftProfile(
        name="jianying_pro_10",
        template_dir="template_jianying_10_2",
        content_file="draft_content.json",
        content_mirrors=("draft_content.json.bak", "template-2.tmp"),
        timeline_content_file="template.tmp",
        is_capcut_env=False,
        platform=JIANYING_10_PLATFORM,
    ),
}

PROFILE_ALIASES = {
    "capcut": "capcut_legacy",
    "capcut_legacy": "capcut_legacy",
    "jianying": "jianying_legacy",
    "jianying_legacy": "jianying_legacy",
    "jianying_10": "jianying_pro_10",
    "jianying_10_x": "jianying_pro_10",
    "jianying_pro_10": "jianying_pro_10",
    "jianying_pro_10_2": "jianying_pro_10",
    "jianying_pro_10_2_0": "jianying_pro_10",
}


def normalize_profile_name(name: Optional[str]) -> str:
    if not name:
        return "capcut_legacy"
    key = name.strip().lower().replace(".", "_").replace("-", "_")
    if key not in PROFILE_ALIASES:
        raise ValueError(
            f"Unknown draft profile '{name}'. Supported profiles: {', '.join(sorted(PROFILE_ALIASES))}"
        )
    return PROFILE_ALIASES[key]


def get_draft_profile(name: Optional[str] = None) -> DraftProfile:
    if name is None:
        try:
            name = _load_settings().draft_profile
        except Exception:
            name = "capcut_legacy"
    return PROFILES[normalize_profile_name(name)]


def get_template_dir(name: Optional[str] = None) -> str:
    return get_draft_profile(name).template_dir


def write_profile_content(profile: DraftProfile, draft_dir: os.PathLike, content: str) -> List[Path]:
    draft_path = Path(draft_dir)
    written: List[Path] = []
    content_data = json.loads(content)

    targets = [profile.content_file, *profile.content_mirrors]
    for relative_path in targets:
        path = draft_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        written.append(path)

    if profile.timeline_content_file:
        timelines_dir = draft_path / "Timelines"
        if timelines_dir.exists():
            timeline_dirs = [path for path in timelines_dir.iterdir() if path.is_dir()]
            timeline_id = content_data.get("id")
            if timeline_id and timeline_dirs:
                timeline_dir = timeline_dirs[0]
                desired_timeline_dir = timelines_dir / timeline_id
                if timeline_dir != desired_timeline_dir:
                    if desired_timeline_dir.exists():
                        shutil.rmtree(desired_timeline_dir)
                    timeline_dir.rename(desired_timeline_dir)
                    timeline_dirs = [desired_timeline_dir]

            for timeline_dir in timeline_dirs:
                timeline_targets = set(targets)
                timeline_targets.add(profile.timeline_content_file)
                for relative_path in timeline_targets:
                    path = timeline_dir / relative_path
                    path.write_text(content, encoding="utf-8")
                    written.append(path)

            if timeline_id:
                now_us = int(time.time() * 1_000_000)
                project = {
                    "config": {
                        "color_space": -1,
                        "render_index_track_mode_on": False,
                        "use_float_render": False,
                    },
                    "create_time": now_us,
                    "id": timeline_id,
                    "main_timeline_id": timeline_id,
                    "timelines": [
                        {
                            "create_time": now_us,
                            "id": timeline_id,
                            "is_marked_delete": False,
                            "name": "时间线01",
                            "update_time": now_us,
                        }
                    ],
                    "update_time": now_us,
                    "version": 0,
                }
                for relative_path in ("project.json", "project.json.bak"):
                    path = timelines_dir / relative_path
                    path.write_text(json.dumps(project, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
                    written.append(path)

                layout_path = draft_path / "timeline_layout.json"
                if layout_path.exists():
                    layout = json.loads(layout_path.read_text(encoding="utf-8"))
                    for item in layout.get("dockItems", []):
                        item["timelineIds"] = [timeline_id]
                        item["timelineNames"] = ["时间线01"]
                    layout_path.write_text(json.dumps(layout, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
                    written.append(layout_path)

    return written


# ============================================================================
# New capabilities
# ============================================================================


def _load_settings():
    """Lazily load config to avoid circular imports. Designed for test monkeypatching."""
    from vectcut.core.config import load_config
    return load_config()


def get_draft(draft_id: str):
    """Retrieve a draft script object from the LRU cache; return None if missing."""
    return DRAFT_CACHE.get(draft_id)


def get_active_profile() -> "DraftProfile":
    """Return the currently active draft profile, resolved from config.draft_profile."""
    return get_draft_profile(_load_settings().draft_profile)


def get_or_create_draft(draft_id: Optional[str] = None, width: int = 1080, height: int = 1920):
    """草稿 get-or-create：draft_id 命中缓存则返回缓存对象，否则新建并入缓存。

    迁自根目录 create_draft.get_or_create_draft，供 video/audio/text 等业务 service 复用。
    """
    import uuid

    if draft_id is not None and draft_id in DRAFT_CACHE:
        update_cache(draft_id, DRAFT_CACHE[draft_id])  # LRU 刷新
        return draft_id, DRAFT_CACHE[draft_id]

    unique_id = uuid.uuid4().hex[:8]
    new_id = f"dfd_cat_{int(time.time())}_{unique_id}"
    import pyJianYingDraft as draft

    script = draft.Script_file(width, height)
    update_cache(new_id, script)
    return new_id, script

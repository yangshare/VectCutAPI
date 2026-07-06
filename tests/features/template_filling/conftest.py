"""template_filling 集成测试共享 fixture。

设计原则：
- mock pyJianYingDraft 的 Script_file（含 tracks/get_imported_track/dump/
  replace_material_by_seg），不依赖真实剪映 draft JSON。
- storage 三个目录 monkeypatch 到 tmp_path。
- 提供 sample_template_zip（只含假 draft_content.json），仅供 storage 解压
  /service.import_template 流程使用——load_template 由 mock 返回，不真实解析。
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest


# ─── 假对象：模拟 pyJianYingDraft 的 Track / Segment / Script_file ──────────


class _FakeTrackType:
    """模拟 Track_type 枚举（service._scan_slots 用 .name 比较）。"""

    def __init__(self, name: str):
        self.name = name

    def __repr__(self) -> str:  # 便于断言失败时观察
        return f"<FakeTrackType {self.name}>"


# 与 pyJianYingDraft.track.Track_type 同名枚举值对齐（避免真实 import 触发的副作用）
TRACK_TYPE_VIDEO = _FakeTrackType("video")
TRACK_TYPE_AUDIO = _FakeTrackType("audio")
TRACK_TYPE_TEXT = _FakeTrackType("text")


class FakeSegment:
    """模拟 segment：含 source/target timerange.duration。"""

    def __init__(self, duration_us: int = 5_000_000):
        self.source_timerange = SimpleNamespace(duration=duration_us)
        self.target_timerange = SimpleNamespace(duration=duration_us)


class FakeTrack:
    """模拟 Track：含 name / track_type / segments。"""

    def __init__(
        self,
        name: str,
        track_type: _FakeTrackType,
        n_segs: int = 2,
    ):
        self.name = name
        self.track_type = track_type
        self.segments = [FakeSegment() for _ in range(n_segs)]


class FakeScript:
    """模拟 Script_file：tracks + get_imported_track + dump + replace_material_by_seg。

    dump 写一个空 JSON 到指定路径（让 service.render_draft 能继续走流程）。
    replace_material_by_seg 记录调用以便断言。
    """

    def __init__(self, tracks: List[FakeTrack]):
        self.tracks = list(tracks)
        self.replace_calls: List[Any] = []
        self.dump_calls: List[str] = []

    def get_imported_track(self, track_type, name=None, index=None):
        for t in self.tracks:
            if t.name == name:
                return t
        raise KeyError(f"未找到轨道: {name}")

    def dump(self, path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text("{}", encoding="utf-8")
        self.dump_calls.append(path)

    def replace_material_by_seg(self, track, segment_index, material) -> None:
        self.replace_calls.append((track, segment_index, material))


# ─── fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_script() -> FakeScript:
    """返回带 video/audio(bgm)/text 三条轨道的 FakeScript。"""
    return FakeScript(
        tracks=[
            FakeTrack("video_main", TRACK_TYPE_VIDEO, n_segs=2),
            FakeTrack("bgm", TRACK_TYPE_AUDIO, n_segs=1),
            FakeTrack("subtitle", TRACK_TYPE_TEXT, n_segs=3),
        ]
    )


@pytest.fixture
def sample_template_zip(tmp_path: Path) -> Path:
    """构造含假 draft_content.json 的 zip 文件路径。

    仅用于 storage.extract_template_zip / service.import_template 流程；
    load_template 由 mock 提供，不会真实解析内容。
    """
    zip_path = tmp_path / "sample_template.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("draft_content.json", "{}")
    return zip_path


@pytest.fixture
def temp_storage_dirs(monkeypatch, tmp_path: Path) -> Dict[str, Path]:
    """把 storage 三个目录 monkeypatch 到 tmp_path 下，并返回目录映射。

    通过 patch ``vectcut.core.config.load_config`` 返回自定义 Settings
    实现，storage 每次函数内部 load_config 都拿到 tmp 目录。
    """
    from vectcut.features.template_filling import storage

    templates = tmp_path / "templates"
    configs = tmp_path / "template_configs"
    generated = tmp_path / "generated_drafts"
    for d in (templates, configs, generated):
        d.mkdir(parents=True, exist_ok=True)

    fake_cfg = SimpleNamespace(
        template_folder=str(templates),
        template_config_folder=str(configs),
        generated_draft_folder=str(generated),
        max_template_zip_mb=50,
        # 其它字段（防止意外访问）
        draft_folder=str(tmp_path / "drafts"),
    )

    # storage 与 service 都通过 vectcut.core.config.load_config 取配置
    monkeypatch.setattr(
        "vectcut.features.template_filling.storage.load_config", lambda: fake_cfg
    )
    monkeypatch.setattr(
        "vectcut.features.template_filling.service.load_config", lambda: fake_cfg
    )

    return {
        "templates": templates,
        "configs": configs,
        "generated": generated,
        "cfg": fake_cfg,
    }

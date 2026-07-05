"""service.py 单元测试：覆盖 template_filling 业务编排层。

策略：mock 掉 pyJianYingDraft 的 Script_file.load_template 及 storage 侧调用，
聚焦于流程编排与错误分支，不依赖真实剪映 draft JSON。
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List

import pytest

from vectcut.core.errors import RenderError, SlotError, TemplateError
from vectcut.features.template_filling import service
from vectcut.features.template_filling.schemas import (
    DownloadDraftResponse,
    ImportTemplateResponse,
    RenderDraftResponse,
    SaveSlotConfigResponse,
    SlotConfig,
)


# ─── 公共 fixture：fake storage + fake config ───────────────────────────────


@pytest.fixture
def fake_storage(monkeypatch, tmp_path: Path):
    """把 service 内引用的 storage 模块函数全部替换为内存版。"""
    cfg = SimpleNamespace(
        template_folder=str(tmp_path / "templates"),
        template_config_folder=str(tmp_path / "template_configs"),
        generated_draft_folder=str(tmp_path / "generated_drafts"),
    )
    monkeypatch.setattr(
        "vectcut.features.template_filling.service.load_config", lambda: cfg
    )

    # 模板解包目录字典（template_id → extract_dir 路径）
    state: Dict[str, Any] = {
        "templates": {},  # template_id → extract_dir
        "slots": {},  # template_id → list[dict]
        "drafts": {},  # draft_id → zip_path
    }

    def _extract(template_id: str, uploaded_zip_path: str) -> str:
        extract_dir = Path(cfg.template_folder) / template_id
        extract_dir.mkdir(parents=True, exist_ok=True)
        # 写一个最小 draft_content.json，让 get_template_draft_content_path 通过
        (extract_dir / "draft_content.json").write_text("{}", encoding="utf-8")
        state["templates"][template_id] = str(extract_dir)
        return str(extract_dir)

    def _get_draft_content_path(template_id: str) -> str:
        extract_dir = state["templates"].get(template_id)
        if not extract_dir:
            raise TemplateError(f"模板 {template_id} 缺少 draft_content.json")
        return str(Path(extract_dir) / "draft_content.json")

    def _save_slot_config(template_id: str, slots: list) -> None:
        state["slots"][template_id] = list(slots)

    def _load_slot_config(template_id: str) -> list:
        if template_id not in state["slots"]:
            raise SlotError(f"模板 {template_id} 的槽位配置不存在")
        return state["slots"][template_id]

    def _save_generated_draft_zip(draft_id: str, draft_folder_path: str) -> str:
        zip_path = Path(cfg.generated_draft_folder) / f"{draft_id}.zip"
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        zip_path.write_bytes(b"PK\x03\x04dummy")
        state["drafts"][draft_id] = str(zip_path)
        return str(zip_path)

    def _get_generated_draft_zip_path(draft_id: str):
        return state["drafts"].get(draft_id)

    monkeypatch.setattr(service.storage, "extract_template_zip", _extract)
    monkeypatch.setattr(
        service.storage, "get_template_draft_content_path", _get_draft_content_path
    )
    monkeypatch.setattr(service.storage, "save_slot_config", _save_slot_config)
    monkeypatch.setattr(service.storage, "load_slot_config", _load_slot_config)
    monkeypatch.setattr(
        service.storage, "save_generated_draft_zip", _save_generated_draft_zip
    )
    monkeypatch.setattr(
        service.storage, "get_generated_draft_zip_path", _get_generated_draft_zip_path
    )
    return state


# ─── fake script 工厂：构造有 tracks/segments 的 mock 母版 ──────────────────


class _FakeTrackType:
    """模拟 Track_type 枚举（仅用作 .name 属性）。"""
    def __init__(self, name: str):
        self.name = name


def _make_track(track_type, name: str, seg_count: int = 1) -> SimpleNamespace:
    segs = [SimpleNamespace(target_timerange=SimpleNamespace(duration=1_000_000))
            for _ in range(seg_count)]
    return SimpleNamespace(
        name=name,
        track_type=track_type,
        segments=segs,
    )


def _make_fake_script(
    tracks: List[SimpleNamespace],
    *,
    replace_material_by_seg: Any = None,
) -> SimpleNamespace:
    """构造一个 mock 的 Script_file，包含 dump + 可选的 replace_material_by_seg。"""

    def _dump(path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text("{}", encoding="utf-8")

    return SimpleNamespace(
        tracks=tracks,
        dump=_dump,
        replace_material_by_seg=replace_material_by_seg or (lambda *a, **k: None),
    )


# 默认 tracks：一条 video + 一条 audio(bgm) + 一条 text
_DEFAULT_TRACKS = [
    _make_track(_FakeTrackType("video"), "main_video", seg_count=1),
    _make_track(_FakeTrackType("audio"), "bgm_track", seg_count=1),
    _make_track(_FakeTrackType("text"), "subtitle_track", seg_count=1),
]


@pytest.fixture
def fake_draft_module(monkeypatch):
    """mock service 内的 draft 模块（pyJianYingDraft as draft）。

    返回 calls 字典记录 load_template / dump 调用。
    """
    calls: Dict[str, Any] = {"load_template_args": [], "dump_args": []}

    def _load_template(json_path: str):
        calls["load_template_args"].append(json_path)
        return _make_fake_script(_DEFAULT_TRACKS)

    monkeypatch.setattr(service.draft.Script_file, "load_template", _load_template)
    return calls


# ─── import_template ───────────────────────────────────────────────────────


def test_import_template_invalid_id(fake_storage, tmp_path: Path):
    """非法 template_id → TemplateError 含"非法"。"""
    zip_path = tmp_path / "src.zip"
    zip_path.write_bytes(b"PK\x03\x04")

    with pytest.raises(TemplateError, match="非法"):
        service.import_template("invalid id with space", str(zip_path))


def test_import_template_success(fake_storage, fake_draft_module, tmp_path: Path):
    """合法 template_id → 调用 extract + load_template，返回 ImportTemplateResponse。"""
    zip_path = tmp_path / "src.zip"
    zip_path.write_bytes(b"PK\x03\x04")

    resp = service.import_template("tpl_001", str(zip_path))

    assert isinstance(resp, ImportTemplateResponse)
    assert resp.template_id == "tpl_001"
    assert resp.message  # 非空
    # 应当扫描出 3 个轨道 × 1 段 = 3 个槽位
    slot_types = {s["type"] for s in resp.slots}
    assert "video" in slot_types
    assert "bgm" in slot_types  # track name 含 "bgm"
    assert "subtitle" in slot_types
    # load_template 被调用过
    assert len(fake_draft_module["load_template_args"]) == 1


# ─── save_slot_config ──────────────────────────────────────────────────────


def test_save_slot_config_template_not_imported(fake_storage):
    """模板未导入 → get_template_draft_content_path 抛 TemplateError。"""
    from vectcut.features.template_filling.schemas import SaveSlotConfigRequest

    req = SaveSlotConfigRequest(
        template_id="missing_tpl",
        slots=[SlotConfig(slot_id="video_main_0", name="v",
                          type="video", track_name="main", segment_index=0)],
    )
    with pytest.raises(TemplateError):
        service.save_slot_config("missing_tpl", req)


def test_save_slot_config_invalid_slot(fake_storage, fake_draft_module, tmp_path: Path):
    """slot_id 不存在于母版扫描结果 → SlotError 含"不存在"。"""
    # 先导入一个模板建立 state
    zip_path = tmp_path / "src.zip"
    zip_path.write_bytes(b"PK\x03\x04")
    service.import_template("tpl_x", str(zip_path))

    from vectcut.features.template_filling.schemas import SaveSlotConfigRequest

    req = SaveSlotConfigRequest(
        template_id="tpl_x",
        slots=[SlotConfig(slot_id="not_exist_slot", name="x",
                          type="video", track_name="nope", segment_index=0)],
    )
    with pytest.raises(SlotError, match="不存在"):
        service.save_slot_config("tpl_x", req)


def test_save_slot_config_success(fake_storage, fake_draft_module, tmp_path: Path):
    """正常保存 → 调用 storage.save_slot_config，返回响应。"""
    zip_path = tmp_path / "src.zip"
    zip_path.write_bytes(b"PK\x03\x04")
    service.import_template("tpl_y", str(zip_path))

    from vectcut.features.template_filling.schemas import SaveSlotConfigRequest

    req = SaveSlotConfigRequest(
        template_id="tpl_y",
        slots=[SlotConfig(
            slot_id="video_main_video_0",
            name="主视频", type="video",
            track_name="main_video", segment_index=0,
        )],
    )
    resp = service.save_slot_config("tpl_y", req)

    assert isinstance(resp, SaveSlotConfigResponse)
    assert resp.template_id == "tpl_y"
    assert resp.slot_count == 1
    # state 中应当保存
    assert "tpl_y" in fake_storage["slots"]


# ─── download_draft ────────────────────────────────────────────────────────


def test_download_draft_not_found(fake_storage):
    """storage 返回 None → RenderError 含"不存在"。"""
    with pytest.raises(RenderError, match="不存在"):
        service.download_draft("draft_unknown")


def test_download_draft_empty_id(fake_storage):
    """空 draft_id → RenderError。"""
    with pytest.raises(RenderError):
        service.download_draft("")


def test_download_draft_success(fake_storage):
    """storage 返回路径 → 返回 DownloadDraftResponse，download_url 为相对路径。"""
    fake_storage["drafts"]["d1"] = "/some/path/d1.zip"

    resp = service.download_draft("d1")

    assert isinstance(resp, DownloadDraftResponse)
    assert resp.draft_id == "d1"
    assert resp.download_url == "/api/template/download/d1"
    assert resp.message


# ─── render_draft ──────────────────────────────────────────────────────────


def test_render_draft_template_not_imported(fake_storage, fake_draft_module):
    """模板未导入 → get_template_draft_content_path 抛 TemplateError。"""
    from vectcut.features.template_filling.schemas import RenderDraftRequest

    req = RenderDraftRequest(
        template_id="missing",
        slot_values={},
        output_draft_name="out",
    )
    with pytest.raises(TemplateError):
        service.render_draft("missing", req)


def test_render_draft_no_slot_config(fake_storage, fake_draft_module, tmp_path: Path):
    """模板已导入但未保存槽位配置 → load_slot_config 抛 SlotError。"""
    zip_path = tmp_path / "src.zip"
    zip_path.write_bytes(b"PK\x03\x04")
    service.import_template("tpl_r1", str(zip_path))

    from vectcut.features.template_filling.schemas import RenderDraftRequest

    req = RenderDraftRequest(
        template_id="tpl_r1",
        slot_values={},
        output_draft_name="out",
    )
    with pytest.raises(SlotError):
        service.render_draft("tpl_r1", req)


def test_render_draft_unknown_slot(fake_storage, fake_draft_module, tmp_path: Path):
    """slot_values 含未配置的 slot_id → SlotError。"""
    zip_path = tmp_path / "src.zip"
    zip_path.write_bytes(b"PK\x03\x04")
    service.import_template("tpl_r2", str(zip_path))

    # 手动注入一个槽位配置
    fake_storage["slots"]["tpl_r2"] = [
        {"slot_id": "video_main_video_0", "type": "video",
         "track_name": "main_video", "segment_index": 0}
    ]

    from vectcut.features.template_filling.schemas import RenderDraftRequest

    req = RenderDraftRequest(
        template_id="tpl_r2",
        slot_values={"unknown_slot": {"path": "/x.mp4", "duration": 1.0,
                                      "width": 100, "height": 100}},
        output_draft_name="out",
    )
    with pytest.raises(SlotError, match="未在配置中"):
        service.render_draft("tpl_r2", req)


def test_render_draft_video_slot_success(
    fake_storage, fake_draft_module, monkeypatch, tmp_path: Path
):
    """video 槽位替换成功：mock slot_resolver + material_builder + replace_material_by_seg。"""
    zip_path = tmp_path / "src.zip"
    zip_path.write_bytes(b"PK\x03\x04")
    service.import_template("tpl_r3", str(zip_path))

    fake_storage["slots"]["tpl_r3"] = [
        {"slot_id": "video_main_video_0", "type": "video",
         "track_name": "main_video", "segment_index": 0}
    ]

    # mock slot_resolver 返回 fake track
    fake_track = SimpleNamespace(name="main_video")
    monkeypatch.setattr(
        service.slot_resolver, "resolve_slot_to_track", lambda script, slot: fake_track
    )
    # mock material_builder
    fake_mat = SimpleNamespace(material_id="m1")
    monkeypatch.setattr(
        service.material_builder,
        "build_video_material_from_metadata",
        lambda value: fake_mat,
    )
    monkeypatch.setattr(
        service.material_builder,
        "build_audio_material_from_metadata",
        lambda value: fake_mat,
    )
    # mock script.replace_material_by_seg — 通过自定义 load_template 返回带记录的 script
    replace_calls: List[Any] = []

    def _load_with_replace(path: str):
        return _make_fake_script(
            [],
            replace_material_by_seg=lambda t, i, m: replace_calls.append((t, i, m)),
        )

    monkeypatch.setattr(service.draft.Script_file, "load_template", _load_with_replace)

    from vectcut.features.template_filling.schemas import RenderDraftRequest

    req = RenderDraftRequest(
        template_id="tpl_r3",
        slot_values={"video_main_video_0": {
            "path": "/v.mp4", "duration": 5.0, "width": 1920, "height": 1080,
        }},
        output_draft_name="out",
    )
    resp = service.render_draft("tpl_r3", req)

    assert isinstance(resp, RenderDraftResponse)
    assert resp.draft_id.startswith("draft_")
    assert resp.download_url == f"/api/template/download/{resp.draft_id}"
    assert len(replace_calls) == 1
    # state 中应当有 zip
    assert resp.draft_id in fake_storage["drafts"]


def test_render_draft_subtitle_skip_with_warning(
    fake_storage, fake_draft_module, tmp_path: Path
):
    """subtitle 槽位：MVP 跳过替换，加入 warning。"""
    zip_path = tmp_path / "src.zip"
    zip_path.write_bytes(b"PK\x03\x04")
    service.import_template("tpl_r4", str(zip_path))

    fake_storage["slots"]["tpl_r4"] = [
        {"slot_id": "subtitle_sub_0", "type": "subtitle",
         "track_name": "subtitle_track", "segment_index": 0}
    ]

    from vectcut.features.template_filling.schemas import RenderDraftRequest

    req = RenderDraftRequest(
        template_id="tpl_r4",
        slot_values={"subtitle_sub_0": {"slot_id": "subtitle_sub_0",
                                         "srt_content": "1\n00:00:01,000 --> 00:00:02,000\nhi\n"}},
        output_draft_name="out",
    )
    resp = service.render_draft("tpl_r4", req)

    assert isinstance(resp, RenderDraftResponse)
    assert any("字幕" in w for w in resp.warnings)
    assert resp.draft_id in fake_storage["drafts"]


def test_render_draft_cover_slot_skip_with_warning(
    fake_storage, fake_draft_module, tmp_path: Path
):
    """cover_image / cover_title 槽位：MVP 跳过替换，加入 warning。"""
    zip_path = tmp_path / "src.zip"
    zip_path.write_bytes(b"PK\x03\x04")
    service.import_template("tpl_r5", str(zip_path))

    fake_storage["slots"]["tpl_r5"] = [
        {"slot_id": "cover_img_0", "type": "cover_image",
         "track_name": "cover", "segment_index": 0}
    ]

    from vectcut.features.template_filling.schemas import RenderDraftRequest

    req = RenderDraftRequest(
        template_id="tpl_r5",
        slot_values={"cover_img_0": {"slot_id": "cover_img_0", "text": "x"}},
        output_draft_name="out",
    )
    resp = service.render_draft("tpl_r5", req)
    assert any("封面" in w for w in resp.warnings)


# ─── _scan_slots_from_template ─────────────────────────────────────────────


def test_scan_slots_classifies_track_types():
    """直接验证 _scan_slots_from_template 的轨道分类逻辑。"""
    tracks = [
        _make_track(_FakeTrackType("video"), "main_video", seg_count=2),
        _make_track(_FakeTrackType("audio"), "bgm_track", seg_count=1),
        _make_track(_FakeTrackType("audio"), "voiceover", seg_count=1),
        _make_track(_FakeTrackType("text"), "lyrics", seg_count=1),
        _make_track(_FakeTrackType("sticker"), "skip_me", seg_count=1),
    ]
    script = _make_fake_script(tracks)

    slots = service._scan_slots_from_template(script)

    types = [s["type"] for s in slots]
    # video × 2 seg + bgm(bgm_track) × 1 + audio(voiceover) × 1 + subtitle(lyrics) × 1 = 5
    assert types.count("video") == 2
    assert types.count("bgm") == 1
    assert types.count("audio") == 1
    assert types.count("subtitle") == 1
    # sticker 类型应当被跳过
    assert "sticker" not in types

    # slot_id 格式
    video_slot = next(s for s in slots if s["type"] == "video")
    assert video_slot["slot_id"] == "video_main_video_0"
    assert video_slot["segment_index"] == 0
    assert video_slot["name"] == "video槽位0"

"""template_filling feature schemas 单元测试。"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from vectcut.features.template_filling.schemas import (
    CoverTitleMetadata,
    DownloadDraftRequest,
    DownloadDraftResponse,
    ImportTemplateRequest,
    ImportTemplateResponse,
    MaterialMetadata,
    RenderDraftRequest,
    RenderDraftResponse,
    SaveSlotConfigRequest,
    SaveSlotConfigResponse,
    SlotConfig,
    SubtitleMetadata,
    TextSlotMetadata,
)


# ---------------- ImportTemplateRequest ----------------

def test_import_template_request_valid():
    r = ImportTemplateRequest(name="my-template")
    assert r.name == "my-template"
    assert r.profile == "capcut_legacy"


def test_import_template_request_custom_profile():
    r = ImportTemplateRequest(name="t", profile="jianying_pro_10")
    assert r.profile == "jianying_pro_10"


def test_import_template_request_missing_name_raises():
    with pytest.raises(ValidationError):
        ImportTemplateRequest()


# ---------------- SlotConfig ----------------

def test_slot_config_valid_defaults():
    s = SlotConfig(
        slot_id="slot_1",
        name="主视频",
        type="video",
        track_name="video_main",
        segment_index=0,
    )
    assert s.slot_id == "slot_1"
    assert s.required is True


def test_slot_config_required_false():
    s = SlotConfig(
        slot_id="slot_bgm",
        name="背景音乐",
        type="bgm",
        track_name="audio_bgm",
        segment_index=0,
        required=False,
    )
    assert s.required is False


def test_slot_config_accepts_track_segment_group():
    s = SlotConfig(
        slot_id="video_track0",
        name="主视频",
        type="video",
        track_name="",
        segment_index=0,
        segment_indices=[0, 1, 2],
        segment_count=3,
    )

    assert s.segment_indices == [0, 1, 2]
    assert s.segment_count == 3


def test_slot_config_missing_required_field_raises():
    with pytest.raises(ValidationError):
        SlotConfig(slot_id="s", name="x", type="video", segment_index=0)
        # 缺 track_name


# ---------------- SaveSlotConfigRequest ----------------

def test_save_slot_config_request_valid_multiple_slots():
    r = SaveSlotConfigRequest(
        template_id="tpl_abc",
        slots=[
            SlotConfig(
                slot_id="s1",
                name="主视频",
                type="video",
                track_name="video_main",
                segment_index=0,
            ),
            SlotConfig(
                slot_id="s2",
                name="字幕",
                type="subtitle",
                track_name="text_subtitle",
                segment_index=0,
            ),
        ],
    )
    assert r.template_id == "tpl_abc"
    assert len(r.slots) == 2


def test_save_slot_config_request_empty_slots_allowed():
    # 空列表语义上由 service 层校验；schemas 层不强制
    r = SaveSlotConfigRequest(template_id="tpl_x", slots=[])
    assert r.slots == []


# ---------------- MaterialMetadata ----------------

def test_material_metadata_video_full():
    m = MaterialMetadata(
        slot_id="s1",
        path="/data/materials/v.mp4",
        duration=12.5,
        width=1080,
        height=1920,
    )
    assert m.slot_id == "s1"
    assert m.duration == 12.5
    assert m.width == 1080
    assert m.height == 1920


def test_material_metadata_path_only():
    m = MaterialMetadata(slot_id="s2", path="/data/materials/audio.mp3")
    assert m.duration is None
    assert m.width is None
    assert m.height is None


def test_material_metadata_missing_slot_id_raises():
    with pytest.raises(ValidationError):
        MaterialMetadata(path="/data/materials/v.mp4")


# ---------------- SubtitleMetadata ----------------

def test_subtitle_metadata_valid():
    s = SubtitleMetadata(
        slot_id="s_sub",
        srt_content="1\n00:00:00,000 --> 00:00:02,000\nHello\n",
    )
    assert s.slot_id == "s_sub"
    assert "Hello" in s.srt_content


def test_subtitle_metadata_missing_srt_raises():
    with pytest.raises(ValidationError):
        SubtitleMetadata(slot_id="s_sub")


# ---------------- TextSlotMetadata ----------------

def test_text_slot_metadata_valid():
    t = TextSlotMetadata(slot_id="s_text", text="每次生成替换")
    assert t.slot_id == "s_text"
    assert t.text == "每次生成替换"


def test_text_slot_metadata_missing_text_raises():
    with pytest.raises(ValidationError):
        TextSlotMetadata(slot_id="s_text")


# ---------------- CoverTitleMetadata ----------------

def test_cover_title_metadata_valid():
    c = CoverTitleMetadata(slot_id="s_cover", text="我的标题")
    assert c.slot_id == "s_cover"
    assert c.text == "我的标题"


def test_cover_title_metadata_missing_text_raises():
    with pytest.raises(ValidationError):
        CoverTitleMetadata(slot_id="s_cover")


# ---------------- RenderDraftRequest ----------------

def test_render_draft_request_with_multiple_slot_value_types():
    r = RenderDraftRequest(
        template_id="tpl_abc",
        slot_values={
            "slot_video": {
                "path": "/data/v.mp4",
                "duration": 10.0,
                "width": 1080,
                "height": 1920,
            },
            "slot_subtitle": {"srt_content": "1\n00:00:00,000 --> 00:00:01,000\nHi\n"},
            "slot_cover": {"text": "封面标题"},
        },
        output_draft_name="rendered_draft",
    )
    assert r.template_id == "tpl_abc"
    assert "slot_video" in r.slot_values
    assert r.output_draft_name == "rendered_draft"


def test_render_draft_request_missing_slot_values_raises():
    with pytest.raises(ValidationError):
        RenderDraftRequest(template_id="t", output_draft_name="o")


# ---------------- DownloadDraftRequest ----------------

def test_download_draft_request_valid():
    r = DownloadDraftRequest(draft_id="dfd_xyz")
    assert r.draft_id == "dfd_xyz"


def test_download_draft_request_missing_id_raises():
    with pytest.raises(ValidationError):
        DownloadDraftRequest()


# ---------------- Response models ----------------

def test_import_template_response_fields():
    r = ImportTemplateResponse(
        template_id="tpl_abc",
        slots=[{"slot_id": "s1", "type": "video"}],
        message="ok",
    )
    assert r.template_id == "tpl_abc"
    assert r.slots[0]["slot_id"] == "s1"
    assert r.message == "ok"


def test_save_slot_config_response_fields():
    r = SaveSlotConfigResponse(
        template_id="tpl_abc", slot_count=3, message="saved"
    )
    assert r.slot_count == 3


def test_render_draft_response_defaults_empty_warnings():
    r = RenderDraftResponse(draft_id="dfd_1", download_url="https://e/d.zip")
    assert r.warnings == []


def test_render_draft_response_with_warnings():
    r = RenderDraftResponse(
        draft_id="dfd_1",
        download_url="https://e/d.zip",
        warnings=["时长对齐已裁剪"],
    )
    assert r.warnings == ["时长对齐已裁剪"]


def test_download_draft_response_fields():
    r = DownloadDraftResponse(
        draft_id="dfd_1",
        download_url="https://e/d.zip",
        message="ready",
    )
    assert r.download_url == "https://e/d.zip"
    assert r.message == "ready"

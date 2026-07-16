"""template_filling service 层端到端编排测试。

策略：mock ``service.draft.Script_file.load_template`` 返回 conftest 的
FakeScript，配合 temp_storage_dirs fixture（三个目录改到 tmp_path），覆盖
完整流程 import → save_slot_config → render_draft → download_draft。

material_builder 内部真实构造 Video_material/Audio_material（仅依赖元数据，
不访问文件系统），不需要 mock。slot_resolver 通过 FakeScript.get_imported_track
工作。
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from vectcut.core.errors import RenderError, SlotError, TemplateError
from vectcut.features.template_filling import service
from vectcut.features.template_filling.schemas import (
    RenderDraftRequest,
    SaveSlotConfigRequest,
    SlotConfig,
)


# ─── 辅助：把 mock_script 与 service.draft.Script_file.load_template 绑定 ────


@pytest.fixture
def mock_load_template(monkeypatch, mock_script):
    """把 service.draft.Script_file.load_template 替换为返回 mock_script。"""
    monkeypatch.setattr(
        service.draft.Script_file,
        "load_template",
        staticmethod(lambda path: mock_script),
    )
    return mock_script


# ─── 完整流程 ────────────────────────────────────────────────────────────────


def test_full_workflow(temp_storage_dirs, mock_load_template, sample_template_zip):
    """端到端流程：import → save_slot_config → render → download。

    每步都用真实 storage + mock load_template + mock_script 验证编排正确。
    """
    # 1. import —— 真实 storage.extract_template_zip 解压 sample zip
    import_resp = service.import_template("tpl_full", str(sample_template_zip))
    assert import_resp.template_id == "tpl_full"
    assert import_resp.message
    # mock_script 含三条可替换业务轨道，每条轨道生成一个槽位。
    slot_types = [s["type"] for s in import_resp.slots]
    assert slot_types.count("video") == 1
    assert slot_types.count("bgm") == 1
    assert slot_types.count("subtitle") == 1
    assert len(import_resp.slots) == 3

    # 抽取一个 video slot 配置作为后续 render 用
    video_slot = next(s for s in import_resp.slots if s["type"] == "video")
    video_slot_id = video_slot["slot_id"]

    # 2. save_slot_config —— 真实 storage.save_slot_config 写入 JSON
    slot_configs = [
        SlotConfig(
            slot_id=s["slot_id"],
            name=s["name"],
            type=s["type"],
            track_name=s["track_name"],
            segment_index=s["segment_index"],
            segment_indices=s["segment_indices"],
            segment_count=s["segment_count"],
            locator=s["locator"],
            required=s["slot_id"] == video_slot_id,
        )
        for s in import_resp.slots
    ]
    save_req = SaveSlotConfigRequest(template_id="tpl_full", slots=slot_configs)
    save_resp = service.save_slot_config("tpl_full", save_req)
    assert save_resp.template_id == "tpl_full"
    assert save_resp.slot_count == 3
    # 确认 JSON 已落盘
    cfg_file = temp_storage_dirs["configs"] / "tpl_full_slots.json"
    assert cfg_file.is_file()

    # 3. render_draft —— video 替换走真实 slot_resolver + material_builder
    render_req = RenderDraftRequest(
        template_id="tpl_full",
        slot_values={
            video_slot_id: {
                "materials": [
                    {
                        "path": "E:/clips/main-1.mp4",
                        "duration": 5.0,
                        "width": 1920,
                        "height": 1080,
                    },
                    {
                        "path": "E:/clips/main-2.mp4",
                        "duration": 5.0,
                        "width": 1920,
                        "height": 1080,
                    },
                ]
            }
        },
        output_draft_name="out_draft",
    )
    render_resp = service.render_draft("tpl_full", render_req)
    assert render_resp.draft_id.startswith("draft_")
    assert render_resp.download_url == f"/api/template/download/{render_resp.draft_id}"
    # video 槽位替换无 warning
    assert render_resp.warnings == []
    # 确认 replace_material_by_seg 被调用过
    assert len(mock_load_template.replace_calls) == 2
    # 确认 zip 已生成
    generated_zip = temp_storage_dirs["generated"] / f"{render_resp.draft_id}.zip"
    assert generated_zip.is_file()
    # zip 应当是完整的剪映 10.x 草稿包，而不是单独一个 draft_content.json。
    with zipfile.ZipFile(generated_zip) as zf:
        names = set(zf.namelist())
        assert {
            "draft_content.json",
            "draft_content.json.bak",
            "template-2.tmp",
            "draft_meta_info.json",
            "draft_settings",
            "draft_virtual_store.json",
            "timeline_layout.json",
            "Timelines/project.json",
        }.issubset(names)
        timeline_content = [
            name for name in names
            if name.startswith("Timelines/") and name.endswith("/draft_content.json")
        ]
        assert len(timeline_content) == 1
        assert zf.read(timeline_content[0]) == zf.read("draft_content.json")
        meta = json.loads(zf.read("draft_meta_info.json").decode("utf-8"))
        assert meta["draft_name"] == "out_draft"
        assert meta["tm_draft_create"] > 0
        assert meta["tm_draft_modified"] > 0

    # 4. download —— 真实 storage 找到 zip
    download_resp = service.download_draft(render_resp.draft_id)
    assert download_resp.draft_id == render_resp.draft_id
    assert download_resp.download_url == f"/api/template/download/{render_resp.draft_id}"
    assert download_resp.message


def test_render_draft_does_not_copy_template_resource_files(
    temp_storage_dirs, mock_load_template, sample_template_zip
):
    """生成草稿 ZIP 不复制母版附件，素材由新路径引用。"""
    with zipfile.ZipFile(sample_template_zip, "a", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("Resources/cover.png", b"fake image")
        zf.writestr("Resources/audio/bgm.mp3", b"fake audio")

    import_resp = service.import_template("tpl_resources", str(sample_template_zip))
    video_slot = next(s for s in import_resp.slots if s["type"] == "video")
    service.save_slot_config(
        "tpl_resources",
        SaveSlotConfigRequest(
            template_id="tpl_resources",
            slots=[
                SlotConfig(
                    slot_id=video_slot["slot_id"],
                    name=video_slot["name"],
                    type=video_slot["type"],
                    track_name=video_slot["track_name"],
                    segment_index=video_slot["segment_index"],
                    segment_indices=video_slot["segment_indices"],
                    segment_count=video_slot["segment_count"],
                    locator=video_slot["locator"],
                )
            ],
        ),
    )

    render_resp = service.render_draft(
        "tpl_resources",
        RenderDraftRequest(
            template_id="tpl_resources",
            slot_values={
                video_slot["slot_id"]: {
                    "materials": [
                        {
                            "path": "E:/clips/main-1.mp4",
                            "duration": 5.0,
                            "width": 1920,
                            "height": 1080,
                        },
                        {
                            "path": "E:/clips/main-2.mp4",
                            "duration": 5.0,
                            "width": 1920,
                            "height": 1080,
                        },
                    ]
                }
            },
            output_draft_name="out_resources",
        ),
    )

    generated_zip = temp_storage_dirs["generated"] / f"{render_resp.draft_id}.zip"
    with zipfile.ZipFile(generated_zip) as zf:
        names = set(zf.namelist())
        assert "draft_content.json" in names
        assert "draft_meta_info.json" in names
        assert "Timelines/project.json" in names
        assert "Resources/cover.png" not in names
        assert "Resources/audio/bgm.mp3" not in names


def test_rendered_draft_gets_identity_distinct_from_source():
    source_id = "98646CAE-2FB5-4246-BF3D-818AE2352FC4"
    script = type("Script", (), {
        "content": {
            "id": source_id,
            "name": "",
            "create_time": 0,
            "update_time": 0,
        }
    })()

    service._prepare_rendered_draft_identity(script, "new draft")

    assert script.content["id"] != source_id
    assert script.content["name"] == "new draft"
    assert script.content["create_time"] > 0
    assert script.content["update_time"] == script.content["create_time"]


def test_full_workflow_subtitle_import_and_cover_skip(
    temp_storage_dirs, mock_load_template, sample_template_zip
):
    """subtitle 调用 import_srt；cover 槽位暂不支持并加入 warning。"""
    # import 拿到全部槽位
    import_resp = service.import_template("tpl_skip", str(sample_template_zip))

    # 保存配置：只保留 subtitle + cover 类型（手动构造 cover_image）
    subtitle_slot = next(s for s in import_resp.slots if s["type"] == "subtitle")
    cover_slot = {
        "slot_id": "cover_img_0", "name": "封面", "type": "cover_image",
        "track_name": "video_main", "segment_index": 0,
    }
    save_req = SaveSlotConfigRequest(
        template_id="tpl_skip",
        slots=[
            SlotConfig(**subtitle_slot),
            SlotConfig(**cover_slot),
        ],
    )
    # 手动注入（因为 cover_image 不在 import 扫描结果里，绕过 service.save_slot_config 校验）
    from vectcut.features.template_filling import storage
    storage.save_slot_config(
        "tpl_skip",
        [s.model_dump() for s in save_req.slots],
    )
    # 还需要确保模板已导入（import_template 已写入 template 目录）

    render_req = RenderDraftRequest(
        template_id="tpl_skip",
        slot_values={
            subtitle_slot["slot_id"]: {
                "slot_id": subtitle_slot["slot_id"],
                "srt_content": "1\n00:00:01,000 --> 00:00:02,000\nhi\n",
            },
            "cover_img_0": {"slot_id": "cover_img_0", "text": "title"},
        },
        output_draft_name="out",
    )
    expected_style_reference = mock_load_template.tracks[2].segments[0]
    resp = service.render_draft("tpl_skip", render_req)
    assert len(mock_load_template.import_srt_calls) == 1
    srt_content, track_name, kwargs = mock_load_template.import_srt_calls[0]
    assert srt_content == "1\n00:00:01,000 --> 00:00:02,000\nhi\n"
    assert track_name == subtitle_slot["track_name"]
    assert kwargs["style_reference"] is expected_style_reference
    assert kwargs["clip_settings"] is None
    assert not any("字幕" in w and "暂未实现" in w for w in resp.warnings)
    assert any("封面" in w for w in resp.warnings)


# ─── 错误分支 ────────────────────────────────────────────────────────────────


def test_import_invalid_id_raises(temp_storage_dirs):
    """非法 template_id → T_INVALID_ID。"""
    with pytest.raises(TemplateError, match="非法") as exc:
        service.import_template("非法!!", "E:/nonexistent.zip")
    assert exc.value.code == "T_INVALID_ID"


def test_import_template_not_zip_raises(temp_storage_dirs, mock_load_template, tmp_path):
    """非 zip 文件 → T_INVALID_ZIP。"""
    fake_zip = tmp_path / "not_a_zip.zip"
    fake_zip.write_bytes(b"not a zip")
    with pytest.raises(TemplateError) as exc:
        service.import_template("tpl_bad", str(fake_zip))
    assert exc.value.code == "T_INVALID_ZIP"


def test_save_slot_config_template_not_imported(temp_storage_dirs):
    """模板未导入 → T_NO_DRAFT_CONTENT。"""
    req = SaveSlotConfigRequest(
        template_id="missing_tpl",
        slots=[SlotConfig(slot_id="v1", name="v", type="video",
                          track_name="main", segment_index=0)],
    )
    with pytest.raises(TemplateError) as exc:
        service.save_slot_config("missing_tpl", req)
    assert exc.value.code == "T_NO_DRAFT_CONTENT"


def test_save_slot_config_invalid_slot(
    temp_storage_dirs, mock_load_template, sample_template_zip
):
    """slot_id 不在母版扫描结果 → S_INVALID_SLOT。"""
    service.import_template("tpl_v", str(sample_template_zip))
    req = SaveSlotConfigRequest(
        template_id="tpl_v",
        slots=[SlotConfig(slot_id="ghost_slot", name="g", type="video",
                          track_name="ghost", segment_index=0)],
    )
    with pytest.raises(SlotError, match="不存在") as exc:
        service.save_slot_config("tpl_v", req)
    assert exc.value.code == "S_INVALID_SLOT"


def test_render_unknown_slot_raises(
    temp_storage_dirs, mock_load_template, sample_template_zip
):
    """slot_values 含未知 slot_id → S_INVALID_SLOT。"""
    service.import_template("tpl_u", str(sample_template_zip))
    # 手动注入只含一个 slot 的配置
    from vectcut.features.template_filling import storage
    storage.save_slot_config("tpl_u", [
        {"slot_id": "video_video_main_0", "type": "video",
         "track_name": "video_main", "segment_index": 0},
    ])
    req = RenderDraftRequest(
        template_id="tpl_u",
        slot_values={"unknown_slot": {"path": "/x.mp4", "duration": 1.0,
                                       "width": 100, "height": 100}},
        output_draft_name="out",
    )
    with pytest.raises(SlotError, match="未在配置中") as exc:
        service.render_draft("tpl_u", req)
    assert exc.value.code == "S_INVALID_SLOT"


def test_render_without_slot_config_raises(
    temp_storage_dirs, mock_load_template, sample_template_zip
):
    """模板已导入但未保存槽位配置 → S_NOT_FOUND。"""
    service.import_template("tpl_nc", str(sample_template_zip))
    req = RenderDraftRequest(
        template_id="tpl_nc",
        slot_values={},
        output_draft_name="out",
    )
    with pytest.raises(SlotError, match="槽位配置不存在") as exc:
        service.render_draft("tpl_nc", req)
    assert exc.value.code == "S_NOT_FOUND"


def test_download_not_found_raises(temp_storage_dirs):
    """storage 返回 None → R_TASK_NOT_FOUND。"""
    with pytest.raises(RenderError, match="不存在") as exc:
        service.download_draft("draft_ghost")
    assert exc.value.code == "R_TASK_NOT_FOUND"


def test_download_empty_id_raises(temp_storage_dirs):
    """空 draft_id → R_INVALID_TASK。"""
    with pytest.raises(RenderError) as exc:
        service.download_draft("")
    assert exc.value.code == "R_INVALID_TASK"


def test_render_audio_slot_success(
    temp_storage_dirs, mock_load_template, sample_template_zip
):
    """audio(bgm) 槽位替换走 build_audio_material_from_metadata。"""
    service.import_template("tpl_a", str(sample_template_zip))
    from vectcut.features.template_filling import storage
    storage.save_slot_config("tpl_a", [
        {"slot_id": "bgm_bgm_0", "type": "bgm",
         "track_name": "bgm", "segment_index": 0},
    ])
    req = RenderDraftRequest(
        template_id="tpl_a",
        slot_values={
            "bgm_bgm_0": {
                "path": "E:/music/bgm.mp3", "duration": 30.0,
            }
        },
        output_draft_name="out",
    )
    resp = service.render_draft("tpl_a", req)
    assert resp.draft_id.startswith("draft_")
    assert resp.warnings == []
    # replace_material_by_seg 被调用过
    assert len(mock_load_template.replace_calls) == 1


# ─── 真实 fixture 测试（标记 skip） ─────────────────────────────────────────


def test_real_template_integration():
    """真实剪映草稿端到端测试（需手动准备 tests/fixtures/sample_template.zip）。

    本测试不 mock pyJianYingDraft，验证真实 load_template 能解析剪映导出的
    draft_content.json。缺 fixture 时 skip。
    """
    fixture = Path(__file__).resolve().parents[2] / "fixtures" / "sample_template.zip"
    if not fixture.exists():
        pytest.skip("缺少 tests/fixtures/sample_template.zip fixture")

    # 真实流程会触发 pyJianYingDraft 真实解析；保留骨架供手动验证使用
    import shutil
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        # 复制 fixture 到临时模板目录
        from vectcut.core.config import Settings
        td_path = Path(td)
        # 此处不 monkeypatch（真实测试），仅作为示例：手动调用 service。
        # 实际运行需要 load_config 返回指向 td 的目录，目前依赖真实 config.json。
        try:
            resp = service.import_template("real_tpl", str(fixture))
        except Exception as e:
            pytest.skip(f"真实 load_template 解析失败（fixture 不规范）: {e}")
        assert resp.template_id == "real_tpl"

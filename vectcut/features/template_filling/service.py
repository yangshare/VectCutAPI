"""template_filling 业务逻辑层：模板导入、槽位配置、草稿渲染与下载。

4 个核心函数编排 storage / slot_resolver / material_builder / duration_calculator 等辅助模块，
完成从模板 ZIP 到可下载草稿 ZIP 的端到端流程。
"""

from __future__ import annotations

import os
import re
import uuid
from typing import Any, Dict, List

import pyJianYingDraft as draft

from vectcut.core.config import load_config
from vectcut.core.errors import SlotError, TemplateError, make_error
from vectcut.core.logger import sanitize_exception
from vectcut.features.template_filling import (
    duration_calculator,
    material_builder,
    slot_resolver,
    storage,
    style_extractor,
)
from vectcut.features.template_filling.schemas import (
    DownloadDraftResponse,
    ImportTemplateResponse,
    RenderDraftResponse,
    SaveSlotConfigResponse,
)


# ─── 辅助函数 ──────────────────────────────────────────────────────────────


def _validate_template_id(template_id: str) -> None:
    """校验 template_id 只含字母/数字/下划线/连字符，否则抛 TemplateError。"""
    if not re.fullmatch(r"[A-Za-z0-9_-]+", template_id):
        raise make_error(
            "T_INVALID_ID",
            f"非法 template_id: {template_id}",
            details={"template_id": template_id},
        )


def _validate_draft_id(draft_id: str) -> None:
    """校验 draft_id/task_id，避免路径穿越和空 ID。"""
    if not draft_id or not re.fullmatch(r"[A-Za-z0-9_-]+", draft_id):
        raise make_error(
            "R_INVALID_TASK",
            details={"draft_id": draft_id},
        )


def _map_missing_draft_content(template_id: str, exc: TemplateError) -> TemplateError:
    if exc.code != "TEMPLATE_ERROR":
        return exc
    return make_error(
        "T_NO_DRAFT_CONTENT",
        str(exc),
        details={"template_id": template_id},
    )


def _map_missing_slot_config(template_id: str, exc: SlotError) -> SlotError:
    if exc.code != "SLOT_ERROR":
        return exc
    return make_error(
        "S_NOT_FOUND",
        str(exc),
        details={"template_id": template_id},
    )


def _template_import_semantic_error(template_id: str, exc: Exception) -> TemplateError:
    return make_error(
        "T_INVALID_ZIP",
        "模板 ZIP 内容无法解析",
        details={
            "template_id": template_id,
            "reason": sanitize_exception(exc),
        },
    )


def _scan_slots_from_template(script) -> List[Dict[str, Any]]:
    """从 script.tracks 扫描可替换槽位。

    按轨道类型分类：
    - video → type="video"
    - audio → type="bgm" if "bgm" in track.name.lower() else "audio"
    - text  → type="subtitle"
    - 其他跳过

    每段生成一个槽位 dict。
    """
    slots: List[Dict[str, Any]] = []
    for track in script.tracks:
        # 用 .name 字符串比较，兼容真实 Track_type 枚举与测试 mock
        tt_name = getattr(track.track_type, "name", str(track.track_type))
        track_name = track.name

        if tt_name == "video":
            slot_type = "video"
        elif tt_name == "audio":
            slot_type = "bgm" if "bgm" in track_name.lower() else "audio"
        elif tt_name == "text":
            slot_type = "subtitle"
        else:
            continue  # 跳过 sticker / effect 等非替换轨道

        for seg_idx in range(len(track.segments)):
            slots.append({
                "slot_id": f"{slot_type}_{track_name}_{seg_idx}",
                "type": slot_type,
                "track_name": track_name,
                "segment_index": seg_idx,
                "name": f"{slot_type}槽位{seg_idx}",
            })
    return slots


def _replace_slot_material(script, track, slot: Dict[str, Any], material) -> None:
    slot_id = slot.get("slot_id", "")
    segment_index = slot_resolver.parse_slot_segment_index(slot)
    slot_resolver.validate_slot_segment_index(track, segment_index, slot_id)
    script.replace_material_by_seg(track, segment_index, material)


def _build_slot_map(slots_config: List[Dict[str, Any]], template_id: str) -> Dict[str, Dict[str, Any]]:
    slot_map: Dict[str, Dict[str, Any]] = {}
    for index, slot in enumerate(slots_config):
        slot_id = slot.get("slot_id")
        if not slot_id:
            raise make_error(
                "S_INVALID_SLOT",
                "槽位配置缺少 slot_id",
                details={"template_id": template_id, "slot_index": index, "slot": slot},
            )
        if slot_id in slot_map:
            raise make_error(
                "S_INVALID_SLOT",
                f"槽位配置包含重复 slot_id: {slot_id}",
                details={
                    "template_id": template_id,
                    "slot_id": slot_id,
                    "first_index": slot_map[slot_id].get("_slot_index", 0),
                    "duplicate_index": index,
                },
            )
        slot = dict(slot)
        slot["_slot_index"] = index
        slot_map[slot_id] = slot
    return slot_map


def _validate_required_slot_values(
    slot_map: Dict[str, Dict[str, Any]],
    slot_values: Dict[str, Any],
    template_id: str,
) -> None:
    missing_slot_ids = [
        slot_id
        for slot_id, slot in slot_map.items()
        if slot.get("required", True) is not False and slot_id not in slot_values
    ]
    if missing_slot_ids:
        raise make_error(
            "R_MISSING_SLOT",
            "缺少必填槽位素材",
            details={
                "template_id": template_id,
                "missing_slot_ids": missing_slot_ids,
            },
        )


def _validate_slot_values_in_config(
    slot_map: Dict[str, Dict[str, Any]],
    slot_values: Dict[str, Any],
    template_id: str,
) -> None:
    for slot_id in slot_values:
        if slot_id not in slot_map:
            raise make_error(
                "S_INVALID_SLOT",
                f"槽位 {slot_id} 未在配置中",
                details={"slot_id": slot_id, "template_id": template_id},
            )


def _get_slot_type(slot: Dict[str, Any], template_id: str) -> str:
    slot_type = slot.get("type")
    if not slot_type:
        raise make_error(
            "S_INVALID_SLOT",
            "槽位配置缺少 type",
            details={"template_id": template_id, "slot_id": slot.get("slot_id"), "slot": slot},
        )
    if slot_type not in {"video", "audio", "bgm", "subtitle", "cover_image", "cover_title"}:
        raise make_error(
            "S_INVALID_SLOT",
            f"未知槽位类型: {slot_type}",
            details={
                "template_id": template_id,
                "slot_id": slot.get("slot_id"),
                "slot_type": slot_type,
            },
        )
    return slot_type


def _validate_render_slot_config(script, slot: Dict[str, Any], template_id: str):
    slot_type = _get_slot_type(slot, template_id)

    if slot_type in ("cover_image", "cover_title"):
        segment_index = slot_resolver.parse_slot_segment_index(slot)
        validation_slot = dict(slot)
        validation_slot["type"] = "video" if slot_type == "cover_image" else "subtitle"
        track = slot_resolver.resolve_slot_to_track(script, validation_slot)
        slot_resolver.validate_slot_segment_index(
            track, segment_index, slot.get("slot_id", "")
        )
        return slot_type, track

    track = slot_resolver.resolve_slot_to_track(script, slot)
    segment_index = slot_resolver.parse_slot_segment_index(slot)
    slot_resolver.validate_slot_segment_index(
        track, segment_index, slot.get("slot_id", "")
    )
    return slot_type, track


# ─── 4 个核心函数 ──────────────────────────────────────────────────────────


def import_template(template_id: str, uploaded_zip_path: str) -> ImportTemplateResponse:
    """导入母版 ZIP。

    流程：校验 template_id → extract_template_zip → get_template_draft_content_path
    → load_template → _scan_slots_from_template → 返回响应。

    非法 template_id → TemplateError（含"非法"）。
    """
    _validate_template_id(template_id)

    stage = storage.stage_extract_template_zip(template_id, uploaded_zip_path)
    committed = False
    try:
        with storage.template_lock(template_id):
            # 获取 staging draft_content.json 路径
            try:
                draft_content_path = storage.require_template_draft_content_path_from_dir(
                    template_id, stage.extract_dir
                )
            except TemplateError as exc:
                raise _map_missing_draft_content(template_id, exc) from exc

            # 加载模板并扫描槽位，语义校验成功后才提交 staging
            try:
                script = draft.Script_file.load_template(draft_content_path)
                slots = _scan_slots_from_template(script)
            except Exception as exc:
                raise _template_import_semantic_error(template_id, exc) from exc
            storage.commit_staged_template(stage)
            committed = True
    finally:
        if not committed:
            storage.cleanup_staged_template(stage)

    return ImportTemplateResponse(
        template_id=template_id,
        slots=slots,
        message=f"模板 {template_id} 导入成功，共 {len(slots)} 个槽位",
    )


def save_slot_config(template_id: str, req) -> SaveSlotConfigResponse:
    """保存槽位配置。

    流程：校验模板已导入 → 加载母版扫描已有槽位 → 校验每个 slot_id → 保存配置 → 返回响应。
    """
    _validate_template_id(template_id)

    with storage.template_lock(template_id):
        # 校验模板已导入（get_template_draft_content_path 不抛即存在）
        try:
            draft_content_path = storage.get_template_draft_content_path(template_id)
        except TemplateError as exc:
            raise _map_missing_draft_content(template_id, exc) from exc

        # 加载母版扫描已有槽位
        script = draft.Script_file.load_template(draft_content_path)
        existing_slots = _scan_slots_from_template(script)
        existing_slot_ids = {s["slot_id"] for s in existing_slots}

        # 校验 req.slots 每个 slot_id 都在已有槽位集合中
        for slot_cfg in req.slots:
            if slot_cfg.slot_id not in existing_slot_ids:
                raise make_error(
                    "S_INVALID_SLOT",
                    f"槽位 {slot_cfg.slot_id} 不存在于母版中",
                    details={"slot_id": slot_cfg.slot_id, "template_id": template_id},
                )

        # 保存配置
        storage.save_slot_config(template_id, [s.model_dump() for s in req.slots])

    return SaveSlotConfigResponse(
        template_id=template_id,
        slot_count=len(req.slots),
        message=f"模板 {template_id} 槽位配置已保存，共 {len(req.slots)} 个槽位",
    )


def render_draft(template_id: str, req) -> RenderDraftResponse:
    """渲染草稿（MVP 版本）。

    1. 加载母版 + 槽位配置
    2. 构建 slot_id → slot 映射
    3. 遍历 slot_values 按类型替换素材
    4. 时长对齐（MVP 仅收集 warnings，不实际调整片段）
    5. 导出草稿 + 打包 zip
    """
    _validate_template_id(template_id)

    with storage.template_lock(template_id):
        # 1. 加载母版 + 槽位配置
        try:
            draft_content_path = storage.get_template_draft_content_path(template_id)
        except TemplateError as exc:
            raise _map_missing_draft_content(template_id, exc) from exc
        script = draft.Script_file.load_template(draft_content_path)
        try:
            slots_config = storage.load_slot_config(template_id)
        except SlotError as exc:
            raise _map_missing_slot_config(template_id, exc) from exc

        # 2. 构建 slot_id → slot dict 映射
        slot_map = _build_slot_map(slots_config, template_id)
        validated_slots = {
            slot_id: _validate_render_slot_config(script, slot, template_id)
            for slot_id, slot in slot_map.items()
        }
        _validate_slot_values_in_config(slot_map, req.slot_values, template_id)
        _validate_required_slot_values(slot_map, req.slot_values, template_id)

        warnings: List[str] = []

        # 3. 遍历 slot_values，按槽位类型处理
        for slot_id, value in req.slot_values.items():
            slot = slot_map[slot_id]
            slot_type, track = validated_slots[slot_id]

            if slot_type in ("video", "audio", "bgm"):
                if slot_type == "video":
                    mat = material_builder.build_video_material_from_metadata(value)
                else:
                    mat = material_builder.build_audio_material_from_metadata(value)
                _replace_slot_material(script, track, slot, mat)
            elif slot_type == "subtitle":
                # MVP: 字幕替换先跳过，加 warning
                warnings.append(f"字幕槽位 {slot_id} 替换暂未实现（MVP）")
            elif slot_type in ("cover_image", "cover_title"):
                warnings.append(f"封面槽位 {slot_id} 替换暂未实现（MVP）")

        # 4. 时长对齐（MVP: 仅计算信息，不实际调整片段 — 标注 TODO）
        # TODO: 收集视频段时长，调用 calculate_video_loop_fill / calculate_bgm_alignment
        # MVP 阶段跳过实际对齐

        # 5. 导出草稿
        draft_id = f"draft_{uuid.uuid4().hex[:16]}"
        cfg = load_config()
        output_dir = os.path.join(cfg.generated_draft_folder, draft_id)
        os.makedirs(output_dir, exist_ok=True)
        draft_json_path = os.path.join(output_dir, "draft_content.json")
        script.dump(draft_json_path)

        # 6. 打包 zip
        storage.save_generated_draft_zip(draft_id, output_dir)

    # 7. 返回
    return RenderDraftResponse(
        draft_id=draft_id,
        download_url=f"/api/template/download/{draft_id}",
        warnings=warnings,
    )


def download_draft(draft_id: str) -> DownloadDraftResponse:
    """下载草稿。

    校验 draft_id 非空 → get_generated_draft_zip_path
    → None 时 RenderError（含"不存在"）→ 返回 DownloadDraftResponse。
    """
    _validate_draft_id(draft_id)

    zip_path = storage.get_generated_draft_zip_path(draft_id)
    if zip_path is None:
        raise make_error("R_TASK_NOT_FOUND", details={"draft_id": draft_id})

    return DownloadDraftResponse(
        draft_id=draft_id,
        download_url=f"/api/template/download/{draft_id}",
        message=f"草稿 {draft_id} 下载就绪",
    )

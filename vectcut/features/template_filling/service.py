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
from vectcut.core.errors import RenderError, SlotError, TemplateError
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
        raise TemplateError(f"非法 template_id: {template_id}")


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


# ─── 4 个核心函数 ──────────────────────────────────────────────────────────


def import_template(template_id: str, uploaded_zip_path: str) -> ImportTemplateResponse:
    """导入母版 ZIP。

    流程：校验 template_id → extract_template_zip → get_template_draft_content_path
    → load_template → _scan_slots_from_template → 返回响应。

    非法 template_id → TemplateError（含"非法"）。
    """
    _validate_template_id(template_id)

    # 解压模板 ZIP
    storage.extract_template_zip(template_id, uploaded_zip_path)

    # 获取 draft_content.json 路径
    draft_content_path = storage.get_template_draft_content_path(template_id)

    # 加载模板
    script = draft.Script_file.load_template(draft_content_path)

    # 扫描槽位
    slots = _scan_slots_from_template(script)

    return ImportTemplateResponse(
        template_id=template_id,
        slots=slots,
        message=f"模板 {template_id} 导入成功，共 {len(slots)} 个槽位",
    )


def save_slot_config(template_id: str, req) -> SaveSlotConfigResponse:
    """保存槽位配置。

    流程：校验模板已导入 → 加载母版扫描已有槽位 → 校验每个 slot_id → 保存配置 → 返回响应。
    """
    # 校验模板已导入（get_template_draft_content_path 不抛即存在）
    draft_content_path = storage.get_template_draft_content_path(template_id)

    # 加载母版扫描已有槽位
    script = draft.Script_file.load_template(draft_content_path)
    existing_slots = _scan_slots_from_template(script)
    existing_slot_ids = {s["slot_id"] for s in existing_slots}

    # 校验 req.slots 每个 slot_id 都在已有槽位集合中
    for slot_cfg in req.slots:
        if slot_cfg.slot_id not in existing_slot_ids:
            raise SlotError(f"槽位 {slot_cfg.slot_id} 不存在于母版中")

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
    # 1. 加载母版 + 槽位配置
    draft_content_path = storage.get_template_draft_content_path(template_id)
    script = draft.Script_file.load_template(draft_content_path)
    slots_config = storage.load_slot_config(template_id)

    # 2. 构建 slot_id → slot dict 映射
    slot_map: Dict[str, Dict[str, Any]] = {s["slot_id"]: s for s in slots_config}

    warnings: List[str] = []

    # 3. 遍历 slot_values，按槽位类型处理
    for slot_id, value in req.slot_values.items():
        if slot_id not in slot_map:
            raise SlotError(f"槽位 {slot_id} 未在配置中")
        slot = slot_map[slot_id]
        slot_type = slot["type"]

        if slot_type in ("video", "audio", "bgm"):
            track = slot_resolver.resolve_slot_to_track(script, slot)
            if slot_type == "video":
                mat = material_builder.build_video_material_from_metadata(value)
            else:
                mat = material_builder.build_audio_material_from_metadata(value)
            script.replace_material_by_seg(track, slot["segment_index"], mat)
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
    if not draft_id:
        raise RenderError("draft_id 不能为空")

    zip_path = storage.get_generated_draft_zip_path(draft_id)
    if zip_path is None:
        raise RenderError(f"草稿 {draft_id} 不存在")

    return DownloadDraftResponse(
        draft_id=draft_id,
        download_url=f"/api/template/download/{draft_id}",
        message=f"草稿 {draft_id} 下载就绪",
    )

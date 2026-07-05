"""template_filling feature 请求/响应模型。

字段定义与 service 层实际返回值逐一对齐：
- ImportTemplateResponse / SaveSlotConfigResponse / RenderDraftResponse /
  DownloadDraftResponse 字段名与后续 service.py 返回 dict 的 key 保持一致。
- MaterialMetadata 必带 slot_id（计划文档遗漏，已补齐）。
- SubtitleMetadata 采用整段 SRT 文本（srt_content），不使用 start/end 列表。
- 项目默认 profile 是 capcut_legacy（不是计划文档写的 jianying_pro_10）。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


# ---------------- 请求模型 ----------------


class ImportTemplateRequest(BaseModel):
    """导入模板 ZIP 请求。profile 默认 capcut_legacy（剪映母版）。"""

    name: str
    profile: str = "capcut_legacy"


class SlotConfig(BaseModel):
    """单个槽位配置：定义模板中某个轨道/片段对应的可替换槽位。

    type 取值：video / audio / bgm / subtitle / cover_image / cover_title。
    """

    slot_id: str
    name: str
    type: str
    track_name: str
    segment_index: int
    required: bool = True


class SaveSlotConfigRequest(BaseModel):
    """保存模板槽位配置请求。"""

    template_id: str
    slots: List[SlotConfig]


class MaterialMetadata(BaseModel):
    """视频/音频/图片等媒体素材元数据。slot_id 用于关联到具体槽位。"""

    slot_id: str
    path: str
    duration: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None


class SubtitleMetadata(BaseModel):
    """字幕素材元数据。srt_content 为整段 SRT 文本。"""

    slot_id: str
    srt_content: str


class CoverTitleMetadata(BaseModel):
    """封面标题元数据。"""

    slot_id: str
    text: str


class RenderDraftRequest(BaseModel):
    """根据模板 + 槽位素材生成草稿 ZIP 的请求。

    slot_values 是 dict，key 为 slot_id，value 的结构由具体槽位类型决定
    （MaterialMetadata / SubtitleMetadata / CoverTitleMetadata 等）。
    """

    template_id: str
    slot_values: Dict[str, Any]
    output_draft_name: str


class DownloadDraftRequest(BaseModel):
    """下载已生成的草稿 ZIP 请求。"""

    draft_id: str


# ---------------- 响应模型 ----------------


class ImportTemplateResponse(BaseModel):
    """导入模板响应。slots 为解析出的槽位描述列表（结构由 service 决定）。"""

    template_id: str
    slots: List[Dict[str, Any]]
    message: str


class SaveSlotConfigResponse(BaseModel):
    """保存槽位配置响应。"""

    template_id: str
    slot_count: int
    message: str


class RenderDraftResponse(BaseModel):
    """生成草稿响应。warnings 为非致命提示（如时长对齐裁剪）。"""

    draft_id: str
    download_url: str
    warnings: List[str] = []


class DownloadDraftResponse(BaseModel):
    """下载草稿响应。"""

    draft_id: str
    download_url: str
    message: str

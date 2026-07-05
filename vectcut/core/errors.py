"""统一业务异常基类 + 错误码。

阶段 1 只需 InvalidParam（metadata service 用）。DraftNotFound / EngineError /
MediaDownloadError 在阶段 2-4 引入对应 feature 时按需添加（YAGNI）。
错误码与 HTTP/JSON-RPC 映射见规格 §4.4 表。
"""

from __future__ import annotations


class VectCutError(Exception):
    """业务异常基类。子类声明 code（字符串错误码）与 http_status。"""

    code: str = "VECTCUT_ERROR"
    http_status: int = 500


class InvalidParam(VectCutError):
    """参数非法（未知 kind、end<=start 等）。HTTP 422 / JSON-RPC -32002。"""

    code = "INVALID_PARAM"
    http_status = 422


class DraftNotFound(VectCutError):
    """草稿不存在于缓存（draft_id 未注册）。HTTP 404 / JSON-RPC -32001。"""

    code = "DRAFT_NOT_FOUND"
    http_status = 404


class EngineError(VectCutError):
    """pyJianYingDraft 引擎抛出异常（段/轨道/材料构造失败等）。HTTP 500 / -32003。"""

    code = "ENGINE_ERROR"
    http_status = 500


class MediaDownloadError(VectCutError):
    """素材下载失败（HTTP 4xx/5xx、ffprobe 失败等）。HTTP 502 / -32004。"""

    code = "MEDIA_DOWNLOAD_ERROR"
    http_status = 502


class TemplateError(VectCutError):
    """模板相关错误（模板不存在、ZIP 格式无效等）。HTTP 400。"""

    code = "TEMPLATE_ERROR"
    http_status = 400


class SlotError(VectCutError):
    """槽位相关错误（槽位配置无效、轨道/片段不存在等）。HTTP 400。"""

    code = "SLOT_ERROR"
    http_status = 400


class RenderError(VectCutError):
    """生成相关错误（元数据无效、时长对齐失败等）。HTTP 400。"""

    code = "RENDER_ERROR"
    http_status = 400

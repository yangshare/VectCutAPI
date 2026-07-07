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

    def __init__(self, message: str = "", details: dict | None = None):
        super().__init__(message)
        self.details = details or {}


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


ERROR_CODES = {
    "T_NOT_FOUND": "模板不存在",
    "T_INVALID_ZIP": "ZIP 文件格式无效",
    "T_TOO_LARGE": "模板文件过大",
    "T_NO_DRAFT_CONTENT": "ZIP 中缺少 draft_content.json",
    "T_INVALID_ID": "模板 ID 非法",
    "T_LOCK_TIMEOUT": "模板正在被其它操作占用",
    "S_NOT_FOUND": "槽位配置不存在",
    "S_TRACK_NOT_FOUND": "母版中找不到指定轨道",
    "S_SEGMENT_NOT_FOUND": "母版中找不到指定片段",
    "S_TYPE_MISMATCH": "槽位类型与轨道类型不匹配",
    "S_INVALID_SLOT": "槽位 ID 在母版中不存在",
    "R_MISSING_SLOT": "必填槽位未提供",
    "R_INVALID_PATH": "素材路径格式无效",
    "R_INVALID_DURATION": "素材时长异常",
    "R_LOOP_TOO_MANY": "视频时长不足，需循环次数过多",
    "R_SRT_PARSE_ERROR": "SRT 文件格式错误",
    "R_GENERATE_FAILED": "草稿生成失败",
    "R_EMPTY_VIDEO": "视频槽位为空",
    "R_ZERO_DURATION": "素材总时长为 0",
    "R_TASK_NOT_FOUND": "草稿任务不存在或已过期",
    "R_INVALID_TASK": "task_id 非法",
    "INTERNAL_ERROR": "服务器内部错误",
}


def make_error(
    code: str,
    message: str | None = None,
    details: dict | None = None,
) -> "VectCutError":
    """工厂函数：按错误码构造 VectCutError 子类实例。

    根据代码前缀（T_/S_/R_）选择对应子类，方便上层 catch。
    """
    msg = message or ERROR_CODES.get(code, code)
    if code.startswith("T_"):
        err = TemplateError(msg, details=details)
    elif code.startswith("S_"):
        err = SlotError(msg, details=details)
    elif code.startswith("R_"):
        err = RenderError(msg, details=details)
    else:
        err = VectCutError(msg, details=details)
    err.code = code
    return err

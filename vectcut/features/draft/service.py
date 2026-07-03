"""draft feature 公开 service：纯 Python，不依赖 web/MCP 框架。

5 个函数：create_draft / save_draft / query_script / query_task_status / generate_draft_url。
save_draft 的重活委托 _save_engine.save_draft_background。
"""

from __future__ import annotations

from vectcut.core.config import load_config
from vectcut.core.draft_store import DRAFT_CACHE, get_active_profile, get_or_create_draft
from vectcut.core.errors import DraftNotFound
from vectcut.features.draft._save_engine import save_draft_background, get_video_duration as _get_video_duration_impl
from vectcut.features.draft.schemas import (
    CreateDraftRequest, CreateDraftResponse,
    GetVideoDurationRequest, GetVideoDurationResponse,
    QueryDraftStatusRequest, QueryDraftStatusResponse,
    QueryScriptRequest, QueryScriptResponse,
    SaveDraftRequest, SaveDraftResponse,
)
from save_task_cache import get_task_status


def generate_draft_url(draft_id: str) -> str:
    cfg = load_config()
    return f"{cfg.draft_domain}{cfg.preview_router}?draft_id={draft_id}&is_capcut={1 if cfg.is_capcut_env else 0}"


def create_draft(req: CreateDraftRequest) -> CreateDraftResponse:
    draft_id, _script = get_or_create_draft(draft_id=None, width=req.width, height=req.height)
    return CreateDraftResponse(draft_id=draft_id, draft_url=generate_draft_url(draft_id))


def save_draft(req: SaveDraftRequest) -> SaveDraftResponse:
    if req.draft_id not in DRAFT_CACHE:
        raise DraftNotFound(req.draft_id)
    cfg = load_config()
    folder = req.draft_folder if req.draft_folder is not None else cfg.draft_folder
    draft_url = save_draft_background(req.draft_id, folder, req.draft_id)
    return SaveDraftResponse(success=True, draft_url=draft_url, error="")


def query_script(req: QueryScriptRequest) -> QueryScriptResponse:
    if req.draft_id not in DRAFT_CACHE:
        raise DraftNotFound(req.draft_id)
    script = DRAFT_CACHE[req.draft_id]
    if req.force_update:
        from vectcut.features.draft._save_engine import update_media_metadata
        update_media_metadata(script)
    profile = get_active_profile()
    return QueryScriptResponse(success=True, output=script.dumps(profile), error="")


def query_task_status(req: QueryDraftStatusRequest) -> QueryDraftStatusResponse:
    status = get_task_status(req.task_id)
    return QueryDraftStatusResponse(success=True, output=status, error="")


def get_video_duration(req: GetVideoDurationRequest) -> GetVideoDurationResponse:
    """MCP/HTTP 共用的视频时长查询。委托 _save_engine.get_video_duration（ffprobe）。

    返回 {success, output, error} 结构（与根目录 get_duration_impl.py 历史输出一致）。
    """
    result = _get_video_duration_impl(req.video_url)
    return GetVideoDurationResponse(
        success=result["success"],
        output=result["output"],
        error=result["error"],
    )

"""draft feature 请求/响应 Pydantic 模型。HTTP 与 MCP 共用（规格 §4）。"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class CreateDraftRequest(BaseModel):
    width: int = 1080
    height: int = 1920


class CreateDraftResponse(BaseModel):
    draft_id: str
    draft_url: str


class SaveDraftRequest(BaseModel):
    draft_id: str
    draft_folder: Optional[str] = None


class SaveDraftResponse(BaseModel):
    success: bool = True
    draft_url: str = ""
    error: str = ""


class QueryScriptRequest(BaseModel):
    draft_id: str
    force_update: bool = True


class QueryScriptResponse(BaseModel):
    success: bool = True
    output: str = ""
    error: str = ""


class QueryDraftStatusRequest(BaseModel):
    task_id: str


class QueryDraftStatusResponse(BaseModel):
    success: bool = True
    output: Any = None
    error: str = ""


class GenerateDraftUrlRequest(BaseModel):
    draft_id: str
    draft_folder: Optional[str] = None


class GenerateDraftUrlResponse(BaseModel):
    success: bool = True
    draft_url: str = ""
    error: str = ""

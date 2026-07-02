"""强类型运行时配置。

config.json 是唯一用户可编辑源；它是 JSON5（带 // 注释），必须用 json5 加载。
为避免引入 pydantic-settings 新依赖，采用 BaseModel + load_config() 工厂，
而非 BaseSettings。规格 §5.2 的"Pydantic Settings"诉求由强类型模型满足。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

try:
    import json5  # 支持带注释的配置文件
except ModuleNotFoundError:  # settings/local.py 沿用的回退策略
    import json as json5


_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_CONFIG_PATH = _PROJECT_ROOT / "config.json"


class OssConfig(BaseModel):
    bucket_name: str = ""
    access_key_id: str = ""
    access_key_secret: str = ""
    endpoint: str = ""


class Mp4OssConfig(BaseModel):
    bucket_name: str = ""
    access_key_id: str = ""
    access_key_secret: str = ""
    region: str = ""
    endpoint: str = ""


class Settings(BaseModel):
    """运行时配置聚合。字段默认值与 config.json 现值 / settings/local.py 旧默认对齐。"""

    draft_profile: str = "capcut_legacy"
    is_capcut_env: bool = True              # 废弃字段，过渡期保留读取（规格 §5.2）
    draft_domain: str = "https://www.capcutapi.top"
    port: int = 9001
    preview_router: str = "/draft/downloader"
    is_upload_draft: bool = False
    draft_folder: str = ""
    oss_config: OssConfig = Field(default_factory=OssConfig)
    mp4_oss_config: Mp4OssConfig = Field(default_factory=Mp4OssConfig)


def load_config(path: Optional[os.PathLike] = None) -> Settings:
    """加载 config.json（JSON5）。文件缺失或解析失败时返回全默认 Settings，不抛。"""
    config_path = Path(path) if path is not None else _DEFAULT_CONFIG_PATH
    if not config_path.exists():
        return Settings()
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            raw = json5.load(f)
    except Exception:
        return Settings()
    return Settings.model_validate(raw)

"""强类型运行时配置。

config.json 是唯一用户可编辑源；它是 JSON5（带 // 注释），必须用 json5 加载。
为避免引入 pydantic-settings 新依赖，采用 BaseModel + load_config() 工厂，
而非 BaseSettings。规格 §5.2 的"Pydantic Settings"诉求由强类型模型满足。
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

try:
    import json5  # 支持带注释的配置文件
except ModuleNotFoundError:  # settings/local.py 沿用的回退策略
    import json as json5


_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_CONFIG_PATH = _PROJECT_ROOT / "config.json"
_ENV_VAR_PATTERN = re.compile(r"[$][{]([A-Za-z0-9_]+)[}]")


def _expand_env_vars(content: str) -> str:
    """将配置文件中的 ${VAR_NAME} 替换为环境变量值，未设置时保留占位符。"""

    def _replacer(match: re.Match[str]) -> str:
        var_name = match.group(1)
        return os.getenv(var_name, match.group(0))

    return _ENV_VAR_PATTERN.sub(_replacer, content)


def _expand_env_vars_in_value(value: Any) -> Any:
    if isinstance(value, str):
        return _expand_env_vars(value)
    if isinstance(value, dict):
        return {key: _expand_env_vars_in_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_expand_env_vars_in_value(item) for item in value]
    return value


class OssConfig(BaseModel):
    enabled: bool = False
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


class AuthConfig(BaseModel):
    api_token: str = ""


class Settings(BaseModel):
    """运行时配置聚合。字段默认值与 config.json 现值 / settings/local.py 旧默认对齐。"""

    draft_profile: str = "capcut_legacy"
    is_capcut_env: bool = True              # 废弃字段，过渡期保留读取（规格 §5.2）
    draft_domain: str = "https://www.capcutapi.top"
    api_base_url: str = "https://api.vectcut.com/api"
    port: int = 9001
    preview_router: str = "/draft/downloader"
    is_upload_draft: bool = False
    draft_folder: str = ""
    # template_filling feature 存储目录（相对路径，由 storage.py 在使用时 mkdir）
    template_folder: str = "./data/templates"
    template_config_folder: str = "./data/template_configs"
    generated_draft_folder: str = "./data/generated_drafts"
    temp_folder: str = "./data/temp"
    max_template_zip_mb: int = 50
    auth: AuthConfig = Field(default_factory=AuthConfig)
    oss_config: OssConfig = Field(default_factory=OssConfig)
    mp4_oss_config: Mp4OssConfig = Field(default_factory=Mp4OssConfig)


def load_config_with_env(path: str = "config.json") -> dict:
    """加载 JSON5 配置文件并展开 ${VAR} 环境变量，返回原始 dict。"""
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    raw = json5.loads(content)
    return _expand_env_vars_in_value(raw)


def load_config(path: Optional[os.PathLike] = None) -> Settings:
    """加载 config.json（JSON5）。文件缺失或解析失败时返回全默认 Settings，不抛。"""
    config_path = Path(path) if path is not None else _DEFAULT_CONFIG_PATH
    if not config_path.exists():
        return Settings()
    try:
        raw = load_config_with_env(config_path)
    except Exception:
        return Settings()
    if isinstance(raw, dict) and raw.get("max_template_zip_mb") == "${MAX_TEMPLATE_ZIP_MB}":
        raw.pop("max_template_zip_mb")
    return Settings.model_validate(raw)

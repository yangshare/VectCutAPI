"""配置垫片：转发到 vectcut.core.config。

历史：本文件曾自带 json5 加载与漂移默认值（PORT=9000 vs config.json 9001 等），
现降级为薄转发，消除配置双轨制（规格 §1.1 问题 4 / §5.2）。
仅保留供旧 import 方（capcut_server.py 等）使用的模块级常量名。
真源：config.json → vectcut.core.config.load_config()。
"""

from vectcut.core.config import load_config

_cfg = load_config(None)

IS_CAPCUT_ENV = _cfg.is_capcut_env
DRAFT_PROFILE = _cfg.draft_profile
DRAFT_DOMAIN = _cfg.draft_domain
PREVIEW_ROUTER = _cfg.preview_router
IS_UPLOAD_DRAFT = _cfg.is_upload_draft
DRAFT_FOLDER = _cfg.draft_folder
PORT = _cfg.port
OSS_CONFIG = _cfg.oss_config.model_dump()
MP4_OSS_CONFIG = _cfg.mp4_oss_config.model_dump()

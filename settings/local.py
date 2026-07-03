"""配置垫片：转发到 vectcut.core.config。

历史：本文件曾自带 json5 加载与漂移默认值（PORT=9000 vs config.json 9001 等），
现降级为薄转发，消除配置双轨制（规格 §1.1 问题 4 / §5.2）。
仅保留仍有实代码消费方的模块级常量名。
真源：config.json → vectcut.core.config.load_config()。

阶段5 任务8 瘦身：DRAFT_PROFILE / IS_UPLOAD_DRAFT 已无实代码引用
（_save_engine.py 直读 load_config().is_upload_draft，不经此垫片），
仅 tests/core/test_config.py 旧断言提及，已删。其余 7 个仍被
pyJianYingDraft 引擎 / vectcut.core.util / examples._client /
scripts.gen_local_draft / oss.py 实际 import，暂留；待任务2 迁
oss.py 后再彻底瘦身至仅 IS_CAPCUT_ENV。
"""

from vectcut.core.config import load_config

_cfg = load_config(None)

IS_CAPCUT_ENV = _cfg.is_capcut_env
DRAFT_DOMAIN = _cfg.draft_domain
PREVIEW_ROUTER = _cfg.preview_router
DRAFT_FOLDER = _cfg.draft_folder
PORT = _cfg.port
OSS_CONFIG = _cfg.oss_config.model_dump()
MP4_OSS_CONFIG = _cfg.mp4_oss_config.model_dump()

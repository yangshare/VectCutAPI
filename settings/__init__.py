"""配置包垫片：仅供 pyJianYingDraft 引擎两处 `from settings import IS_CAPCUT_ENV`
（video_segment.py:14 / script_file.py:22）以及旧业务模块 `from settings import IS_UPLOAD_DRAFT, DRAFT_FOLDER`
继续工作。

依赖方向单一：引擎/旧模块 → settings 垫片 → vectcut.core.config（真源）。
垫片仅转发在用的常量名，删除从未被 local 定义的死名（API_KEYS / MODEL_CONFIG /
PURCHASE_LINKS / LICENSE_CONFIG）和无调用方的 get_platform_info()。
"""

from .local import (  # noqa: F401
    IS_CAPCUT_ENV,
    DRAFT_PROFILE,
    DRAFT_DOMAIN,
    PREVIEW_ROUTER,
    IS_UPLOAD_DRAFT,
    DRAFT_FOLDER,
    PORT,
    OSS_CONFIG,
    MP4_OSS_CONFIG,
)

__all__ = [
    "IS_CAPCUT_ENV",
    "DRAFT_PROFILE",
    "DRAFT_DOMAIN",
    "PREVIEW_ROUTER",
    "IS_UPLOAD_DRAFT",
    "DRAFT_FOLDER",
    "PORT",
    "OSS_CONFIG",
    "MP4_OSS_CONFIG",
]

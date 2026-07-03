"""配置包垫片：转发到 vectcut.core.config。

消费方：
- pyJianYingDraft 引擎（video_segment.py:14 / script_file.py:22）`from settings import IS_CAPCUT_ENV`
- vectcut.core.util（generate_draft_url）`from settings.local import DRAFT_DOMAIN, PREVIEW_ROUTER, IS_CAPCUT_ENV`
- examples._client / scripts.gen_local_draft `from settings(.local) import PORT, DRAFT_FOLDER`
- oss.py（根，待任务2 迁 vectcut/core/）`from settings.local import OSS_CONFIG, MP4_OSS_CONFIG`

依赖方向单一：上述消费方 → settings 垫片 → vectcut.core.config（真源）。
阶段5 任务8：删 DRAFT_PROFILE / IS_UPLOAD_DRAFT（无实代码引用）。
待任务2 迁 oss.py 后，剩余常量改由消费方直读 config，本垫片再瘦身至仅 IS_CAPCUT_ENV。
"""

from .local import (  # noqa: F401
    IS_CAPCUT_ENV,
    DRAFT_DOMAIN,
    PREVIEW_ROUTER,
    DRAFT_FOLDER,
    PORT,
    OSS_CONFIG,
    MP4_OSS_CONFIG,
)

__all__ = [
    "IS_CAPCUT_ENV",
    "DRAFT_DOMAIN",
    "PREVIEW_ROUTER",
    "DRAFT_FOLDER",
    "PORT",
    "OSS_CONFIG",
    "MP4_OSS_CONFIG",
]

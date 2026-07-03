"""配置垫片：仅供引擎两处 `from settings.local import IS_CAPCUT_ENV`
（pyJianYingDraft/video_segment.py:14、script_file.py:22）。

阶段5 清理后，应用层全部经 vectcut.core.config 读配置，本垫片仅保留引擎
硬依赖的 IS_CAPCUT_ENV。其余历史常量（DRAFT_PROFILE/PORT/OSS_CONFIG 等）
随旧业务文件删除已无引用，不再转发。

依赖方向单一：引擎 → settings 垫片 → vectcut.core.config（真源）。
引擎日后若升级去掉这两处 import，本垫片即可彻底删除（见 docs 标注）。
"""
from vectcut.core.config import load_config

IS_CAPCUT_ENV = load_config(None).is_capcut_env

__all__ = ["IS_CAPCUT_ENV"]

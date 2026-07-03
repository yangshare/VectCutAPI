"""settings 包垫片：仅供 pyJianYingDraft 引擎 `from settings import IS_CAPCUT_ENV`
（video_segment.py:14 / script_file.py:22）继续工作。

依赖方向单一：引擎 → settings 垫片 → vectcut.core.config（真源）。
"""
from .local import IS_CAPCUT_ENV  # noqa: F401

__all__ = ["IS_CAPCUT_ENV"]

"""垫片：转发到 vectcut.core.draft_store.DRAFT_CACHE / update_cache。

业务代码阶段 5 才统一切换到 vectcut.core.draft_store 直连；在此之前保留此转发。
"""
from vectcut.core.draft_store import DRAFT_CACHE, MAX_CACHE_SIZE, update_cache  # noqa: F401

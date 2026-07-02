"""垫片：转发到 vectcut.core.draft_store 的 profile 相关符号。

业务代码阶段 5 才统一切换；在此之前保留此转发，旧 `from draft_profiles import ...` 不破。
"""
from vectcut.core.draft_store import (  # noqa: F401
    CAPCUT_PLATFORM,
    JIANYING_10_PLATFORM,
    PROFILES,
    PROFILE_ALIASES,
    DraftProfile,
    get_draft_profile,
    get_template_dir,
    normalize_profile_name,
    write_profile_content,
)

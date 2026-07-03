"""垫片：转发到 vectcut.core.draft_store.get_or_create_draft。

阶段 3 的 add_text_impl / add_image_impl 等仍 `from create_draft import get_or_create_draft`，
本垫片保留旧 import 不破，真源在 draft_store。阶段 5 迁完所有 add_* 后可删本文件。
"""
from vectcut.core.draft_store import get_or_create_draft  # noqa: F401


def create_draft(width=1080, height=1920):
    """兼容旧 create_draft.create_draft(width, height) → (script, draft_id) 签名。

    旧签名返回 (script, draft_id)；draft_store.get_or_create_draft 返回 (draft_id, script)。
    此处适配顺序。
    """
    draft_id, script = get_or_create_draft(None, width, height)
    return script, draft_id

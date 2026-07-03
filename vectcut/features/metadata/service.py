"""list_metadata(kind) —— 元数据查询 service（纯 Python，不依赖 web 框架）。

未知 kind -> InvalidParam（规格 §5.3 / §4.4）。
"""

from __future__ import annotations

from vectcut.core.errors import InvalidParam
from vectcut.engine import adapter
from vectcut.features.metadata.registry import META_KINDS


def list_metadata(kind: str, enum=None) -> list:
    """返回 kind 对应的 output 列表。

    enum 形参仅供测试注入；生产路径走 adapter.enum_for(kind)。
    """
    if kind not in META_KINDS:
        raise InvalidParam(
            f"Unknown metadata kind: {kind}. Supported: {sorted(META_KINDS)}"
        )
    _, getter = META_KINDS[kind]
    if enum is None:
        enum = adapter.enum_for(kind)
    return getter(enum)

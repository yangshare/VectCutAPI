"""从 Pydantic 模型生成 MCP inputSchema（单一事实源，规格 §4.3）。

替代 mcp_server.py 里 11 个手写 inputSchema。字段名/类型/required 全部
由模型定义推导，service 改字段 schema 自动同步。
"""
from __future__ import annotations

from typing import Type

from pydantic import BaseModel

# JSON Schema type 名 → MCP inputSchema 期望的简化形式
_PY_TO_JSON = {
    "str": "string",
    "int": "integer",
    "float": "number",
    "bool": "boolean",
}


def _field_type(field) -> str:
    """把 Pydantic 字段的外层类型映射到 inputSchema type 字符串。"""
    py_type = field.annotation
    # Optional[X] / List[X] 等：取 __origin__ 判断
    origin = getattr(py_type, "__origin__", None)
    if origin is list:
        return "array"
    # 取裸类型名（str/int/float/bool）；Optional 包裹的话取 arg
    if hasattr(py_type, "__args__"):
        non_none = [a for a in py_type.__args__ if a is not type(None)]
        if non_none:
            py_type = non_none[0]
        origin = getattr(py_type, "__origin__", None)
        if origin is list:
            return "array"
    name = getattr(py_type, "__name__", "")
    return _PY_TO_JSON.get(name, "string")


def pydantic_to_input_schema(model: Type[BaseModel]) -> dict:
    """生成 {type:object, properties:{...}, required:[...]}。"""
    props = {}
    required = []
    for name, field in model.model_fields.items():
        props[name] = {"type": _field_type(field)}
        if field.is_required():
            required.append(name)
    schema = {"type": "object", "properties": props}
    if required:
        schema["required"] = required
    return schema

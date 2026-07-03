"""inputSchema 生成测试：从 Pydantic 模型生成 MCP inputSchema。"""
from pydantic import BaseModel
from typing import Optional, List

from vectcut.server.mcp.schema_gen import pydantic_to_input_schema


class _DemoModel(BaseModel):
    video_url: str
    start: float = 0
    end: Optional[float] = None
    tags: Optional[List[str]] = None


def test_schema_is_object_with_properties():
    schema = pydantic_to_input_schema(_DemoModel)
    assert schema["type"] == "object"
    assert "properties" in schema
    assert "video_url" in schema["properties"]


def test_required_collected():
    schema = pydantic_to_input_schema(_DemoModel)
    assert "video_url" in schema["required"]
    assert "start" not in schema["required"]  # 有默认值


def test_property_types_mapped():
    schema = pydantic_to_input_schema(_DemoModel)
    assert schema["properties"]["video_url"]["type"] == "string"
    assert schema["properties"]["start"]["type"] == "number"


def test_optional_field_still_present():
    schema = pydantic_to_input_schema(_DemoModel)
    assert "end" in schema["properties"]

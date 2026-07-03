"""MCP tool 注册表测试：12 个 tool 全部注册、name 唯一、schema 可生成。"""
from vectcut.server.mcp.registry import TOOLS
from vectcut.server.mcp.schema_gen import pydantic_to_input_schema


EXPECTED_NAMES = {
    "create_draft", "add_video", "add_audio", "add_image", "add_text",
    "add_subtitle", "add_effect", "add_sticker", "add_video_keyframe",
    "get_video_duration", "save_draft", "generate_draft_url",
}


def test_all_12_tools_registered():
    assert set(TOOLS.keys()) == EXPECTED_NAMES


def test_each_tool_has_service_model_description():
    for name, spec in TOOLS.items():
        assert callable(spec.service), name
        assert spec.request_model is not None, name
        assert isinstance(spec.description, str) and spec.description, name


def test_each_tool_schema_generates():
    for name, spec in TOOLS.items():
        schema = pydantic_to_input_schema(spec.request_model)
        assert schema["type"] == "object", name

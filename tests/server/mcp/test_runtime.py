"""MCP runtime 测试：run_service + tools/list + tools/call + 错误码。"""
import json

from vectcut.core import draft_store
from vectcut.server.mcp.runtime import handle_request, run_service


def test_run_service_returns_model_dump():
    draft_store.DRAFT_CACHE.clear()
    from vectcut.features.draft.service import create_draft
    from vectcut.features.draft.schemas import CreateDraftRequest

    result = run_service(create_draft, CreateDraftRequest, {})
    assert "draft_id" in result
    assert result["draft_id"].startswith("dfd_cat_")


def test_run_service_validation_error_returns_error_envelope():
    from vectcut.features.video.service import add_video
    from vectcut.features.video.schemas import AddVideoRequest

    result = run_service(add_video, AddVideoRequest, {})
    # 缺 video_url → 校验失败，返回 {success:False, error:...}
    assert result["success"] is False
    assert "video_url" in result["error"]


def test_initialize_response():
    resp = json.loads(handle_request(json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "initialize"
    })))
    assert resp["result"]["protocolVersion"] == "2024-11-05"
    assert resp["result"]["serverInfo"]["name"] == "vectcut"


def test_tools_list_returns_all_tools_with_input_schema():
    resp = json.loads(handle_request(json.dumps({
        "jsonrpc": "2.0", "id": 2, "method": "tools/list"
    })))
    tools = resp["result"]["tools"]
    names = {t["name"] for t in tools}
    assert "add_video" in names
    # inputSchema 从模型生成
    add_video_tool = next(t for t in tools if t["name"] == "add_video")
    assert add_video_tool["inputSchema"]["type"] == "object"
    assert "video_url" in add_video_tool["inputSchema"]["properties"]


def test_tools_call_create_draft():
    draft_store.DRAFT_CACHE.clear()
    resp = json.loads(handle_request(json.dumps({
        "jsonrpc": "2.0", "id": 3, "method": "tools/call",
        "params": {"name": "create_draft", "arguments": {}}
    })))
    text = resp["result"]["content"][0]["text"]
    payload = json.loads(text)
    assert payload["draft_id"].startswith("dfd_cat_")


def test_unknown_method_returns_method_not_found():
    resp = json.loads(handle_request(json.dumps({
        "jsonrpc": "2.0", "id": 4, "method": "nope"
    })))
    assert resp["error"]["code"] == -32601


def test_unknown_tool_returns_error():
    resp = json.loads(handle_request(json.dumps({
        "jsonrpc": "2.0", "id": 5, "method": "tools/call",
        "params": {"name": "ghost", "arguments": {}}
    })))
    # 未知 tool 走 run_service 之前的 lookup 失败 → 内容里 success=False
    content = resp["result"]["content"][0]["text"]
    payload = json.loads(content)
    assert payload["success"] is False

"""MCP runtime：run_service + handle_request + stdio 主循环。

保真：保留 mcp_server.py 的 JSON-RPC 响应结构（protocolVersion 2024-11-05、
serverInfo、tools/list、tools/call content 包装、Method not found -32601）。
差异：tool 分派从 if/elif 改为查 TOOLS 表；inputSchema 从模型生成；
异常转 -32xxx 错误码（规格 §4.4）。
"""
from __future__ import annotations

import contextlib
import io
import json
import sys
import traceback
from typing import Any, Dict, Optional, Type

from pydantic import BaseModel, ValidationError

from vectcut.core.errors import VectCutError
from vectcut.server.mcp.registry import TOOLS
from vectcut.server.mcp.schema_gen import pydantic_to_input_schema

# 错误码：规格 §4.4。VectCutError 子类用其 code 字段映射到 -32000 段。
_BASE_ERR_CODE = -32000


def _error_code(exc: Exception) -> int:
    if isinstance(exc, VectCutError):
        mapping = {
            "DRAFT_NOT_FOUND": -32001,
            "INVALID_PARAM": -32002,
            "ENGINE_ERROR": -32003,
            "MEDIA_DOWNLOAD_ERROR": -32004,
        }
        return mapping.get(exc.code, _BASE_ERR_CODE)
    return _BASE_ERR_CODE


def run_service(service_fn, model_cls: Type[BaseModel], arguments: Dict[str, Any]) -> Dict[str, Any]:
    """共用工具：validate → service → model_dump。异常转 {success:False, error}。

    规格 §4.3：所有 tool handler 都调它，消除手写大分派。
    """
    try:
        req = model_cls.model_validate(arguments or {})
    except ValidationError as e:
        return {"success": False, "error": f"Hi, the required parameters are missing. {e}"}
    try:
        with _capture_stdout():
            resp = service_fn(req)
        if isinstance(resp, BaseModel):
            return resp.model_dump()
        return resp
    except VectCutError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        print(f"[ERROR] service error: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return {"success": False, "error": str(e)}


@contextlib.contextmanager
def _capture_stdout():
    """捕获标准输出，防止引擎调试信息干扰 JSON 响应（迁自 mcp_server.py）。"""
    old = sys.stdout
    sys.stdout = io.StringIO()
    try:
        yield
    finally:
        sys.stdout = old


def _tools_list() -> list:
    return [
        {
            "name": name,
            "description": spec.description,
            "inputSchema": pydantic_to_input_schema(spec.request_model),
        }
        for name, spec in TOOLS.items()
    ]


def handle_request(request_data: str) -> Optional[str]:
    """处理一条 JSON-RPC 请求，返回 JSON 字符串或 None（通知）。"""
    try:
        request = json.loads(request_data.strip())
    except Exception as e:
        return json.dumps({
            "jsonrpc": "2.0", "id": None,
            "error": {"code": -32700, "message": f"Parse error: {e}"},
        })

    method = request.get("method")
    req_id = request.get("id")

    if method == "initialize":
        return json.dumps({
            "jsonrpc": "2.0", "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"experimental": {}, "tools": {"listChanged": False}},
                "serverInfo": {"name": "vectcut", "version": "1.0.0"},
            },
        })

    if method == "notifications/initialized":
        return None

    if method == "tools/list":
        return json.dumps({
            "jsonrpc": "2.0", "id": req_id,
            "result": {"tools": _tools_list()},
        })

    if method == "tools/call":
        params = request.get("params", {})
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        spec = TOOLS.get(tool_name)
        if spec is None:
            result = {"success": False, "error": f"Unknown tool: {tool_name}"}
        else:
            result = run_service(spec.service, spec.request_model, arguments)
        return json.dumps({
            "jsonrpc": "2.0", "id": req_id,
            "result": {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}]},
        })

    return json.dumps({
        "jsonrpc": "2.0", "id": req_id,
        "error": {"code": -32601, "message": "Method not found"},
    })


def main():
    """stdio 主循环（迁自 mcp_server.py，仅替换分派为 handle_request）。"""
    print("🚀 Starting VectCut MCP Server...", file=sys.stderr)
    print(f"📋 Available tools: {len(TOOLS)} tools loaded", file=sys.stderr)
    try:
        while True:
            line = sys.stdin.readline()
            if not line:
                break
            response = handle_request(line)
            if response:
                print(response)
                sys.stdout.flush()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

"""text feature Flask Blueprint：/add_text + /add_subtitle。"""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from vectcut.core.errors import VectCutError
from vectcut.features.text import service
from vectcut.features.text.schemas import AddSubtitleRequest, AddTextRequest

bp = Blueprint("text", __name__)


def _ok(output):
    return jsonify({"success": True, "output": output, "error": ""})


@bp.post("/add_text")
def add_text():
    try:
        req = AddTextRequest.model_validate(request.get_json() or {})
    except ValidationError as e:
        # 保真：capcut_server.py:228 错误消息(含尾随空格)
        return jsonify(
            {
                "success": False,
                "output": "",
                "error": (
                    f"Hi, the required parameters 'text', 'start' or 'end' are "
                    f"missing. {e}"
                ),
            }
        )
    try:
        resp = service.add_text(req)
        return _ok({"draft_id": resp.draft_id, "draft_url": resp.draft_url})
    except VectCutError as e:
        # 保真：capcut_server.py:284 error_message
        return jsonify(
            {
                "success": False,
                "output": "",
                "error": (
                    f"Error occurred while processing text: {e}. You can click "
                    f"the link below for help: "
                ),
            }
        )


@bp.post("/add_subtitle")
def add_subtitle():
    try:
        req = AddSubtitleRequest.model_validate(request.get_json() or {})
    except ValidationError as e:
        # 保真：capcut_server.py:69 错误消息
        return jsonify(
            {
                "success": False,
                "output": "",
                "error": f"Hi, the required parameters 'srt' are missing. {e}",
            }
        )
    try:
        resp = service.add_subtitle(req)
        return _ok({"draft_id": resp.draft_id, "draft_url": resp.draft_url})
    except VectCutError as e:
        # 保真：capcut_server.py:110 error_message
        return jsonify(
            {
                "success": False,
                "output": "",
                "error": f"Error occurred while processing subtitle: {e}.",
            }
        )

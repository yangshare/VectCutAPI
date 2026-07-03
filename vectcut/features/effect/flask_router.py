"""effect feature Flask Blueprint：/add_effect + /add_sticker。"""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from vectcut.core.errors import VectCutError
from vectcut.features.effect import service
from vectcut.features.effect.schemas import AddEffectRequest, AddStickerRequest

bp = Blueprint("effect", __name__)


def _ok(output):
    return jsonify({"success": True, "output": output, "error": ""})


@bp.post("/add_effect")
def add_effect():
    try:
        req = AddEffectRequest.model_validate(request.get_json() or {})
    except ValidationError as e:
        return jsonify(
            {"success": False, "output": "", "error": f"Hi, the required parameters are missing. {e}"}
        )
    try:
        resp = service.add_effect(req)
        return _ok({"draft_id": resp.draft_id, "draft_url": resp.draft_url})
    except VectCutError as e:
        # 保真：capcut_server.py:481 error_message 末尾含一个空格
        return jsonify(
            {"success": False, "output": "", "error": f"Error occurred while adding effect: {e}. "}
        )


@bp.post("/add_sticker")
def add_sticker():
    try:
        req = AddStickerRequest.model_validate(request.get_json() or {})
    except ValidationError as e:
        # 阶段2 通用文案(Pydantic {e} 列出缺失字段,含 sticker_id)
        return jsonify(
            {"success": False, "output": "", "error": f"Hi, the required parameters are missing. {e}"}
        )
    try:
        resp = service.add_sticker(req)
        return _ok({"draft_id": resp.draft_id, "draft_url": resp.draft_url})
    except VectCutError as e:
        # 保真：capcut_server.py:544 error_message 末尾含一个空格
        return jsonify(
            {"success": False, "output": "", "error": f"Error occurred while adding sticker: {e}. "}
        )

"""image feature Flask Blueprint：/add_image。"""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from vectcut.core.errors import VectCutError
from vectcut.features.image import service
from vectcut.features.image.schemas import AddImageRequest

bp = Blueprint("image", __name__)


def _ok(output):
    return jsonify({"success": True, "output": output, "error": ""})


@bp.post("/add_image")
def add_image():
    try:
        req = AddImageRequest.model_validate(request.get_json() or {})
    except ValidationError as e:
        return jsonify(
            {"success": False, "output": "", "error": f"Hi, the required parameters are missing. {e}"}
        )
    try:
        resp = service.add_image(req)
        return _ok({"draft_id": resp.draft_id, "draft_url": resp.draft_url})
    except VectCutError as e:
        # 保真：capcut_server.py:385 error_message
        return jsonify(
            {"success": False, "output": "", "error": f"Error occurred while processing image: {e}."}
        )

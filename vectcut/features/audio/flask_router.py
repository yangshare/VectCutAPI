"""audio feature Flask Blueprint：/add_audio。"""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from vectcut.core.errors import VectCutError
from vectcut.features.audio import service
from vectcut.features.audio.schemas import AddAudioRequest

bp = Blueprint("audio", __name__)


@bp.post("/add_audio")
def add_audio():
    try:
        req = AddAudioRequest.model_validate(request.get_json() or {})
    except ValidationError as e:
        return jsonify(
            {"success": False, "output": "", "error": f"Hi, the required parameters are missing. {e}"}
        )
    try:
        resp = service.add_audio(req)
        return jsonify(
            {"success": True, "output": {"draft_id": resp.draft_id, "draft_url": resp.draft_url}, "error": ""}
        )
    except VectCutError as e:
        return jsonify(
            {"success": False, "output": "", "error": f"Error occurred while processing audio: {e}."}
        )

"""video feature Flask Blueprint：/add_video + /add_video_keyframe。"""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from vectcut.core.errors import VectCutError
from vectcut.features.video import service
from vectcut.features.video.schemas import AddVideoKeyframeRequest, AddVideoRequest

bp = Blueprint("video", __name__)


def _ok(output):
    return jsonify({"success": True, "output": output, "error": ""})


@bp.post("/add_video")
def add_video():
    try:
        req = AddVideoRequest.model_validate(request.get_json() or {})
    except ValidationError as e:
        return jsonify(
            {"success": False, "output": "", "error": f"Hi, the required parameters are missing. {e}"}
        )
    try:
        resp = service.add_video(req)
        return _ok({"draft_id": resp.draft_id, "draft_url": resp.draft_url})
    except VectCutError as e:
        return jsonify(
            {"success": False, "output": "", "error": f"Error occurred while processing video: {e}."}
        )


@bp.post("/add_video_keyframe")
def add_video_keyframe():
    try:
        req = AddVideoKeyframeRequest.model_validate(request.get_json() or {})
    except ValidationError as e:
        return jsonify(
            {"success": False, "output": "", "error": f"Hi, the required parameters are missing. {e}"}
        )
    try:
        resp = service.add_video_keyframe(req)
        return _ok({"draft_id": resp.draft_id, "draft_url": resp.draft_url})
    except VectCutError as e:
        return jsonify(
            {"success": False, "output": "", "error": f"Error occurred while adding keyframe: {e}."}
        )

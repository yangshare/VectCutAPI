"""Flask Blueprint：元数据查询路由。

提供 GET /metadata/{kind}（新）与 11 个旧具名别名路径（规格 §5.3 路由兼容）。
阶段 4 迁 FastAPI 时，同一 service 接到 FastAPI router，本文件随之替换。
"""

from __future__ import annotations

from flask import Blueprint, jsonify

from vectcut.core.errors import VectCutError
from vectcut.features.metadata import service

bp = Blueprint("metadata", __name__)

_KIND_TO_ALIAS = {
    "intro_animation": "/get_intro_animation_types",
    "outro_animation": "/get_outro_animation_types",
    "combo_animation": "/get_combo_animation_types",
    "transition": "/get_transition_types",
    "mask": "/get_mask_types",
    "audio_effect": "/get_audio_effect_types",
    "font": "/get_font_types",
    "text_intro": "/get_text_intro_types",
    "text_outro": "/get_text_outro_types",
    "text_loop_anim": "/get_text_loop_anim_types",
    "video_scene_effect": "/get_video_scene_effect_types",
    "video_character_effect": "/get_video_character_effect_types",
}


def _envelope(kind: str):
    try:
        return jsonify({"success": True, "output": service.list_metadata(kind), "error": ""})
    except VectCutError as e:
        return jsonify({"success": False, "output": "", "error": str(e)})


@bp.get("/metadata/<kind>")
def metadata_by_kind(kind: str):
    return _envelope(kind)


# 旧具名别名：循环注册，全部转发到同一 service（规格 §5.3）。
def _register_alias(kind: str, alias: str):
    def view():
        return _envelope(kind)

    view.__name__ = f"alias_{kind}"
    bp.add_url_rule(alias, view_func=view, methods=["GET"])


for _kind, _alias in _KIND_TO_ALIAS.items():
    _register_alias(_kind, _alias)

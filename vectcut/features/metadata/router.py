"""metadata feature FastAPI router：GET /metadata/{kind} + 12 旧别名。

保真：与 flask_router.py 路由集合、输出外壳逐字一致。
使用 try/except 处理 service 异常（kind 非法 → InvalidParam）。
"""
from __future__ import annotations

from fastapi import APIRouter

from vectcut.core.errors import VectCutError
from vectcut.features.metadata import service
from vectcut.server._helpers import envelope_ok, envelope_err

router = APIRouter()

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


@router.get("/metadata/{kind}")
def metadata_by_kind(kind: str):
    try:
        return envelope_ok(service.list_metadata(kind))
    except VectCutError as e:
        return envelope_err(str(e))
    except Exception as e:
        return envelope_err(str(e))


def _register_alias(kind: str, alias: str) -> None:
    @router.get(alias, name=f"alias_{kind}")
    def _alias():
        try:
            return envelope_ok(service.list_metadata(kind))
        except VectCutError as e:
            return envelope_err(str(e))
        except Exception as e:
            return envelope_err(str(e))


for _kind, _alias in _KIND_TO_ALIAS.items():
    _register_alias(_kind, _alias)

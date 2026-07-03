"""metadata feature FastAPI router 测试：参数化 + 12 别名等价。"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from vectcut.features.metadata.router import router
from vectcut.server.http.app import _wire_exception_handlers


def _client() -> TestClient:
    app = FastAPI()
    _wire_exception_handlers(app)
    app.include_router(router)
    return TestClient(app)


def test_metadata_by_kind_returns_envelope():
    resp = _client().get("/metadata/font")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert isinstance(body["output"], list)
    assert len(body["output"]) > 0


def test_metadata_unknown_kind_returns_error():
    resp = _client().get("/metadata/no_such_kind")
    body = resp.json()
    assert body["success"] is False
    assert "no_such_kind" in body["error"]


ALIASES = [
    "/get_intro_animation_types", "/get_outro_animation_types",
    "/get_combo_animation_types", "/get_transition_types",
    "/get_mask_types", "/get_audio_effect_types", "/get_font_types",
    "/get_text_intro_types", "/get_text_outro_types",
    "/get_text_loop_anim_types", "/get_video_scene_effect_types",
    "/get_video_character_effect_types",
]


def test_each_alias_equivalent_to_param_route():
    client = _client()
    alias_to_kind = {
        "/get_intro_animation_types": "intro_animation",
        "/get_font_types": "font",
    }
    for alias, kind in alias_to_kind.items():
        a = client.get(alias).json()
        b = client.get(f"/metadata/{kind}").json()
        assert a == b, f"{alias} != /metadata/{kind}"


@pytest.mark.parametrize(
    "kind,alias",
    [
        ("intro_animation", "/get_intro_animation_types"),
        ("outro_animation", "/get_outro_animation_types"),
        ("combo_animation", "/get_combo_animation_types"),
        ("transition", "/get_transition_types"),
        ("mask", "/get_mask_types"),
        ("audio_effect", "/get_audio_effect_types"),
        ("font", "/get_font_types"),
        ("text_intro", "/get_text_intro_types"),
        ("text_outro", "/get_text_outro_types"),
        ("text_loop_anim", "/get_text_loop_anim_types"),
        ("video_scene_effect", "/get_video_scene_effect_types"),
        ("video_character_effect", "/get_video_character_effect_types"),
    ],
)
def test_each_alias_parametrized_equivalent_to_param_route(kind, alias, monkeypatch):
    """12 别名路径调用 list_metadata 时 kind 参数与 /metadata/{kind} 一致（规格 §5.3 路由兼容）。"""
    from vectcut.features.metadata import service

    captured = []

    def spy(k, enum=None):
        captured.append(k)
        return [{"name": "X"}]

    monkeypatch.setattr(service, "list_metadata", spy)

    client = _client()
    new = client.get(f"/metadata/{kind}").json()
    old = client.get(alias).json()
    assert new == old
    assert captured[-1] == kind

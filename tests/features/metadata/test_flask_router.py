import pytest


@pytest.fixture()
def client():
    from flask import Flask
    from vectcut.features.metadata.flask_router import bp

    app = Flask(__name__)
    app.register_blueprint(bp)
    app.config["TESTING"] = True
    return app.test_client()


def test_parameterized_route_returns_success_envelope(client, monkeypatch):
    from vectcut.features.metadata import service

    monkeypatch.setattr(service, "list_metadata", lambda kind, enum=None: [{"name": "A"}])
    resp = client.get("/metadata/intro_animation")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    assert body["output"] == [{"name": "A"}]
    assert body["error"] == ""


def test_unknown_kind_returns_error_envelope(client, monkeypatch):
    from vectcut.features.metadata import service
    from vectcut.core.errors import InvalidParam

    def _raise(kind, enum=None):
        raise InvalidParam("nope")

    monkeypatch.setattr(service, "list_metadata", _raise)
    resp = client.get("/metadata/nope")
    assert resp.status_code == 200  # 旧路由也是 200 + success=false
    body = resp.get_json()
    assert body["success"] is False
    assert "nope" in body["error"]


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
def test_old_alias_route_equivalent_to_new_route(client, monkeypatch, kind, alias):
    """旧别名路径输出必须与新 /metadata/{kind} 完全一致（规格 §5.3 路由兼容）。"""
    from vectcut.features.metadata import service

    captured = []

    def spy(k, enum=None):
        captured.append(k)
        return [{"name": "X"}]

    monkeypatch.setattr(service, "list_metadata", spy)

    new = client.get(f"/metadata/{kind}").get_json()
    old = client.get(alias).get_json()
    assert new == old
    assert captured[-1] == kind  # 别名确实转发了同一 kind

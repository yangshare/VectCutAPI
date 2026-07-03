import pytest


@pytest.fixture()
def client():
    from flask import Flask
    from vectcut.features.effect.flask_router import bp

    app = Flask(__name__)
    app.register_blueprint(bp)
    app.config["TESTING"] = True
    return app.test_client()


def test_add_sticker_route_missing_sticker_id_returns_error_envelope(client):
    resp = client.post("/add_sticker", json={})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is False
    assert "sticker_id" in body["error"]


def test_add_effect_route_returns_envelope(client, monkeypatch):
    from vectcut.features.effect import service
    from vectcut.features.effect.schemas import AddEffectResponse

    # monkeypatch service,只验路由成功 envelope 外壳(不依赖真实特效枚举成员名)
    monkeypatch.setattr(
        service, "add_effect",
        lambda req: AddEffectResponse(draft_id="dfd_cat_x", draft_url="http://x"),
    )
    resp = client.post("/add_effect", json={"effect_type": "dummy", "effect_category": "scene"})
    body = resp.get_json()
    assert body["success"] is True
    assert body["output"]["draft_id"] == "dfd_cat_x"
    assert body["error"] == ""

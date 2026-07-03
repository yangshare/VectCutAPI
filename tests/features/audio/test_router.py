import pytest


@pytest.fixture()
def client():
    from flask import Flask
    from vectcut.features.audio.flask_router import bp

    app = Flask(__name__)
    app.register_blueprint(bp)
    app.config["TESTING"] = True
    return app.test_client()


def test_add_audio_route_missing_url(client):
    resp = client.post("/add_audio", json={})
    body = resp.get_json()
    assert body["success"] is False
    assert "audio_url" in body["error"]


def test_add_audio_route_success(client):
    from vectcut.core import draft_store

    draft_store.DRAFT_CACHE.clear()
    resp = client.post("/add_audio", json={"audio_url": "https://example.com/a.mp3"})
    body = resp.get_json()
    assert body["success"] is True
    assert body["output"]["draft_id"].startswith("dfd_cat_")

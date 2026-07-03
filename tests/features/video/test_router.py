import pytest


@pytest.fixture()
def client():
    from flask import Flask
    from vectcut.features.video.flask_router import bp

    app = Flask(__name__)
    app.register_blueprint(bp)
    app.config["TESTING"] = True
    return app.test_client()


def test_add_video_route_missing_video_url_returns_error(client):
    resp = client.post("/add_video", json={})
    body = resp.get_json()
    assert body["success"] is False
    assert "video_url" in body["error"]


def test_add_video_route_success(client):
    from vectcut.core import draft_store

    draft_store.DRAFT_CACHE.clear()
    resp = client.post("/add_video", json={"video_url": "https://example.com/v.mp4"})
    body = resp.get_json()
    assert body["success"] is True
    assert body["output"]["draft_id"].startswith("dfd_cat_")


def test_add_video_keyframe_route_missing_draft_id(client):
    resp = client.post("/add_video_keyframe", json={})
    body = resp.get_json()
    assert body["success"] is False

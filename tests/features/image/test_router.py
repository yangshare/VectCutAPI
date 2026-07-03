import pytest


@pytest.fixture()
def client():
    from flask import Flask
    from vectcut.features.image.flask_router import bp
    app = Flask(__name__)
    app.register_blueprint(bp)
    app.config["TESTING"] = True
    return app.test_client()


def test_add_image_route_missing_image_url_returns_error_envelope(client):
    resp = client.post("/add_image", json={})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is False
    assert "image_url" in body["error"]


def test_add_image_route_success_envelope(client):
    from vectcut.core.draft_store import DRAFT_CACHE
    DRAFT_CACHE.clear()
    resp = client.post("/add_image", json={"image_url": "https://example.com/a.png"})
    body = resp.get_json()
    assert body["success"] is True
    assert body["output"]["draft_id"].startswith("dfd_cat_")

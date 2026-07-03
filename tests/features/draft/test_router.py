import pytest


@pytest.fixture()
def client(monkeypatch):
    from flask import Flask
    from vectcut.features.draft.flask_router import bp
    from vectcut.features.draft import service

    app = Flask(__name__)
    app.register_blueprint(bp)
    app.config["TESTING"] = True
    return app.test_client()


def test_create_draft_route_returns_envelope(client):
    resp = client.post("/create_draft", json={})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    assert body["output"]["draft_id"].startswith("dfd_cat_")
    assert "draft_url" in body["output"]
    assert body["error"] == ""


def test_save_draft_route_missing_draft_id_returns_error_envelope(client):
    resp = client.post("/save_draft", json={})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is False
    assert "draft_id" in body["error"]


def test_query_script_route_missing_returns_error(client):
    resp = client.post("/query_script", json={"draft_id": "missing"})
    body = resp.get_json()
    assert body["success"] is False


def test_query_draft_status_route_not_found(client):
    resp = client.post("/query_draft_status", json={"task_id": "nope"})
    body = resp.get_json()
    assert body["success"] is True
    assert body["output"]["status"] == "not_found"


def test_generate_draft_url_route(client):
    resp = client.post("/generate_draft_url", json={"draft_id": "dfd_1"})
    body = resp.get_json()
    assert body["success"] is True
    assert "dfd_1" in body["output"]["draft_url"]
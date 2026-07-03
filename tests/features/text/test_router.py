import pytest


@pytest.fixture()
def client():
    from flask import Flask
    from vectcut.features.text.flask_router import bp

    app = Flask(__name__)
    app.register_blueprint(bp)
    app.config["TESTING"] = True
    return app.test_client()


def test_add_text_route_missing_text_returns_error_with_fidelity_message(client):
    resp = client.post("/add_text", json={})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is False
    # 保真：capcut_server.py:228 错误消息(含尾随空格)
    assert "text" in body["error"] and "start" in body["error"] and "end" in body["error"]


def test_add_text_route_color_alias_maps_to_font_color(client):
    from vectcut.core.draft_store import DRAFT_CACHE
    DRAFT_CACHE.clear()
    # color 别名应被归一化为 font_color
    resp = client.post("/add_text", json={"text": "hi", "start": 0, "end": 1, "color": "#00FF00"})
    body = resp.get_json()
    assert body["success"] is True


def test_add_subtitle_route_missing_srt_returns_error(client):
    resp = client.post("/add_subtitle", json={})
    body = resp.get_json()
    assert body["success"] is False
    assert "srt" in body["error"]

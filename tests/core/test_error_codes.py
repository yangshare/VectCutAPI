from fastapi import FastAPI
from fastapi.testclient import TestClient

from vectcut.core.errors import (
    ERROR_CODES,
    RenderError,
    SlotError,
    TemplateError,
    VectCutError,
    make_error,
)
from vectcut.server.http import app
from vectcut.server.http.app import _wire_exception_handlers


def test_make_error_maps_template_codes_to_template_error():
    assert isinstance(make_error("T_NOT_FOUND"), TemplateError)


def test_make_error_maps_slot_codes_to_slot_error():
    assert isinstance(make_error("S_TRACK_NOT_FOUND"), SlotError)


def test_make_error_maps_render_codes_to_render_error():
    assert isinstance(make_error("R_LOOP_TOO_MANY"), RenderError)


def test_make_error_preserves_code_message_override_and_details():
    err = make_error(
        "R_TASK_NOT_FOUND",
        message="草稿不存在",
        details={"draft_id": "draft_x"},
    )

    assert isinstance(err, RenderError)
    assert err.code == "R_TASK_NOT_FOUND"
    assert str(err) == "草稿不存在"
    assert err.details == {"draft_id": "draft_x"}


def test_make_error_maps_unknown_codes_to_base_error():
    err = make_error("X_UNKNOWN")
    assert isinstance(err, VectCutError)
    assert not isinstance(err, (TemplateError, SlotError, RenderError))


def test_all_error_codes_have_messages():
    assert ERROR_CODES
    assert all(message for message in ERROR_CODES.values())


def test_vectcut_exception_handler_returns_structured_error():
    sub = FastAPI()

    @sub.get("/raise")
    def _raise():
        raise make_error("T_NOT_FOUND", details={"template_id": "missing"})

    _wire_exception_handlers(sub)
    client = TestClient(sub, raise_server_exceptions=False)

    resp = client.get("/raise")

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert body["output"] is None
    assert body["error"]["code"] == "T_NOT_FOUND"
    assert body["error"]["message"] == ERROR_CODES["T_NOT_FOUND"]
    assert body["error"]["details"] == {"template_id": "missing"}


def test_template_download_not_found_returns_structured_error_envelope():
    client = TestClient(app)

    resp = client.get("/api/template/download/task_notexist_test")

    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "R_TASK_NOT_FOUND"
    assert body["error"]["message"] == ERROR_CODES["R_TASK_NOT_FOUND"]
    assert body["error"]["details"] == {"draft_id": "task_notexist_test"}

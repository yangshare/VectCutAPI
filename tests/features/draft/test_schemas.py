from vectcut.features.draft.schemas import (
    CreateDraftRequest, CreateDraftResponse,
    SaveDraftRequest, SaveDraftResponse,
    QueryScriptRequest, QueryScriptResponse,
    QueryDraftStatusRequest, QueryDraftStatusResponse,
    GenerateDraftUrlRequest, GenerateDraftUrlResponse,
)


def test_create_draft_request_defaults():
    r = CreateDraftRequest()
    assert r.width == 1080
    assert r.height == 1920


def test_save_draft_request_defaults_draft_folder_none():
    r = SaveDraftRequest(draft_id="dfd_1")
    assert r.draft_id == "dfd_1"
    assert r.draft_folder is None


def test_query_script_request_defaults_force_update_true():
    r = QueryScriptRequest(draft_id="dfd_1")
    assert r.force_update is True


def test_query_draft_status_request():
    r = QueryDraftStatusRequest(task_id="t_1")
    assert r.task_id == "t_1"


def test_generate_draft_url_request():
    r = GenerateDraftUrlRequest(draft_id="dfd_1")
    assert r.draft_id == "dfd_1"

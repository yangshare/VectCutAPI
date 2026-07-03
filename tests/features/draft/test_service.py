import pytest

from vectcut.core import draft_store


@pytest.fixture(autouse=True)
def _clean_cache():
    draft_store.DRAFT_CACHE.clear()
    yield
    draft_store.DRAFT_CACHE.clear()


def test_create_draft_service_returns_id_and_url(monkeypatch):
    from vectcut.features.draft import service
    from vectcut.features.draft.schemas import CreateDraftRequest

    monkeypatch.setattr(service, "generate_draft_url", lambda draft_id: f"http://x/{draft_id}")
    resp = service.create_draft(CreateDraftRequest(width=1080, height=1920))
    assert resp.draft_id.startswith("dfd_cat_")
    assert resp.draft_url.startswith("http://x/")


def test_generate_draft_url_service_uses_config():
    from vectcut.features.draft import service
    from vectcut.features.draft.schemas import GenerateDraftUrlRequest

    resp = service.generate_draft_url(GenerateDraftUrlRequest(draft_id="dfd_1").draft_id)
    assert "dfd_1" in resp
    assert "is_capcut=" in resp


def test_query_task_status_service_not_found():
    from vectcut.features.draft import service
    from vectcut.features.draft.schemas import QueryDraftStatusRequest

    out = service.query_task_status(QueryDraftStatusRequest(task_id="nope"))
    assert out.success is True
    assert out.output["status"] == "not_found"


def test_query_script_service_missing_draft_raises():
    from vectcut.features.draft import service
    from vectcut.features.draft.schemas import QueryScriptRequest
    from vectcut.core.errors import DraftNotFound

    with pytest.raises(DraftNotFound):
        service.query_script(QueryScriptRequest(draft_id="missing"))


def test_save_draft_service_missing_draft_raises():
    from vectcut.features.draft import service
    from vectcut.features.draft.schemas import SaveDraftRequest
    from vectcut.core.errors import DraftNotFound

    with pytest.raises(DraftNotFound):
        service.save_draft(SaveDraftRequest(draft_id="missing"))

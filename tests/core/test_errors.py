def test_invalid_param_carries_message_and_code():
    from vectcut.core.errors import InvalidParam, VectCutError

    err = InvalidParam("kind must be one of registered kinds")
    assert isinstance(err, VectCutError)
    assert err.code == "INVALID_PARAM"
    assert "kind must be" in str(err)


def test_invalid_param_default_http_status():
    from vectcut.core.errors import InvalidParam

    assert InvalidParam("x").http_status == 422


def test_draft_not_found_carries_code_and_404():
    from vectcut.core.errors import DraftNotFound, VectCutError

    err = DraftNotFound("dfd_cat_xxx")
    assert isinstance(err, VectCutError)
    assert err.code == "DRAFT_NOT_FOUND"
    assert err.http_status == 404
    assert "dfd_cat_xxx" in str(err)


def test_engine_error_carries_code_and_500():
    from vectcut.core.errors import EngineError

    err = EngineError("boom")
    assert err.code == "ENGINE_ERROR"
    assert err.http_status == 500


def test_media_download_error_carries_code_and_502():
    from vectcut.core.errors import MediaDownloadError

    err = MediaDownloadError("404 from cdn")
    assert err.code == "MEDIA_DOWNLOAD_ERROR"
    assert err.http_status == 502

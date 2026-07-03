def test_invalid_param_carries_message_and_code():
    from vectcut.core.errors import InvalidParam, VectCutError

    err = InvalidParam("kind must be one of registered kinds")
    assert isinstance(err, VectCutError)
    assert err.code == "INVALID_PARAM"
    assert "kind must be" in str(err)


def test_invalid_param_default_http_status():
    from vectcut.core.errors import InvalidParam

    assert InvalidParam("x").http_status == 422
def test_expand_env_vars_replaces_set_values(monkeypatch):
    from vectcut.core.config import _expand_env_vars

    monkeypatch.setenv("API_AUTH_TOKEN", "token-123")

    assert _expand_env_vars('{"api_token": "${API_AUTH_TOKEN}"}') == '{"api_token": "token-123"}'


def test_expand_env_vars_keeps_unset_placeholders(monkeypatch):
    from vectcut.core.config import _expand_env_vars

    monkeypatch.delenv("MISSING_TOKEN", raising=False)

    assert _expand_env_vars('{"api_token": "${MISSING_TOKEN}"}') == '{"api_token": "${MISSING_TOKEN}"}'


def test_load_config_with_env_reads_json5_and_replaces_env(tmp_path, monkeypatch):
    from vectcut.core.config import load_config_with_env

    monkeypatch.setenv("OSS_BUCKET", "vectcut-bucket")
    path = tmp_path / "config.json"
    path.write_text(
        """
        {
          // JSON5 comments are supported by project config files.
          "oss_config": {
            "bucket_name": "${OSS_BUCKET}"
          }
        }
        """,
        encoding="utf-8",
    )

    raw = load_config_with_env(path)

    assert raw["oss_config"]["bucket_name"] == "vectcut-bucket"


def test_load_config_expands_env_and_preserves_new_settings_fields(tmp_path, monkeypatch):
    from vectcut.core.config import load_config

    monkeypatch.setenv("API_AUTH_TOKEN", "api-token")
    monkeypatch.setenv("OSS_BUCKET", "oss-bucket")
    path = tmp_path / "config.json"
    path.write_text(
        """
        {
          "api_base_url": "https://api.example.com/api",
          "temp_folder": "/tmp/vectcut",
          "max_template_zip_mb": 88,
          "auth": {"api_token": "${API_AUTH_TOKEN}"},
          "oss_config": {
            "enabled": true,
            "bucket_name": "${OSS_BUCKET}"
          }
        }
        """,
        encoding="utf-8",
    )

    cfg = load_config(path)

    assert cfg.api_base_url == "https://api.example.com/api"
    assert cfg.temp_folder == "/tmp/vectcut"
    assert cfg.max_template_zip_mb == 88
    assert cfg.auth.api_token == "api-token"
    assert cfg.oss_config.enabled is True
    assert cfg.oss_config.bucket_name == "oss-bucket"


def test_load_config_expands_max_template_zip_mb_from_env(tmp_path, monkeypatch):
    from vectcut.core.config import load_config

    monkeypatch.setenv("MAX_TEMPLATE_ZIP_MB", "73")
    path = tmp_path / "config.json"
    path.write_text(
        """
        {
          "max_template_zip_mb": "${MAX_TEMPLATE_ZIP_MB}"
        }
        """,
        encoding="utf-8",
    )

    cfg = load_config(path)

    assert cfg.max_template_zip_mb == 73


def test_load_config_uses_default_when_max_template_zip_env_placeholder_is_unset(
    tmp_path, monkeypatch
):
    from vectcut.core.config import load_config

    monkeypatch.delenv("MAX_TEMPLATE_ZIP_MB", raising=False)
    path = tmp_path / "config.json"
    path.write_text(
        """
        {
          "max_template_zip_mb": "${MAX_TEMPLATE_ZIP_MB}"
        }
        """,
        encoding="utf-8",
    )

    cfg = load_config(path)

    assert cfg.max_template_zip_mb == 50


def test_load_config_with_env_preserves_special_env_chars_after_json5_parse(tmp_path, monkeypatch):
    from vectcut.core.config import load_config_with_env

    token = 'abc"def\\ghi\nnext-line'
    monkeypatch.setenv("API_AUTH_TOKEN", token)
    path = tmp_path / "config.json"
    path.write_text('{"auth": {"api_token": "${API_AUTH_TOKEN}"}}', encoding="utf-8")

    raw = load_config_with_env(path)

    assert raw["auth"]["api_token"] == token


def test_load_config_preserves_special_env_chars_after_json5_parse(tmp_path, monkeypatch):
    from vectcut.core.config import load_config

    token = 'abc"def\\ghi\nnext-line'
    monkeypatch.setenv("API_AUTH_TOKEN", token)
    path = tmp_path / "config.json"
    path.write_text('{"auth": {"api_token": "${API_AUTH_TOKEN}"}}', encoding="utf-8")

    cfg = load_config(path)

    assert cfg.auth.api_token == token


def test_load_config_with_env_expands_nested_dicts_and_lists(tmp_path, monkeypatch):
    from vectcut.core.config import load_config_with_env

    monkeypatch.setenv("ROOT", "/app/data")
    monkeypatch.setenv("BUCKET", "vectcut-bucket")
    path = tmp_path / "config.json"
    path.write_text(
        """
        {
          "paths": ["${ROOT}/templates", {"generated": "${ROOT}/generated"}],
          "oss_config": {
            "bucket_name": "${BUCKET}",
            "endpoint": "${UNSET_ENDPOINT}"
          }
        }
        """,
        encoding="utf-8",
    )

    raw = load_config_with_env(path)

    assert raw["paths"] == ["/app/data/templates", {"generated": "/app/data/generated"}]
    assert raw["oss_config"]["bucket_name"] == "vectcut-bucket"
    assert raw["oss_config"]["endpoint"] == "${UNSET_ENDPOINT}"

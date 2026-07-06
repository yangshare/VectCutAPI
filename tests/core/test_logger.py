"""日志脱敏测试。"""
import io
import logging
import os
import subprocess
import sys
from pathlib import Path

import pytest

_LOG_DIR = Path("logs")
_DEFAULT_LOG_FILE = _LOG_DIR / "vectcut.log"
_LOG_DIR_EXISTED_BEFORE_IMPORT = _LOG_DIR.exists()
_DEFAULT_LOG_FILE_EXISTED_BEFORE_IMPORT = _DEFAULT_LOG_FILE.exists()

from vectcut.core.logger import (
    default_logger,
    sanitize_dict,
    sanitize_exception,
    sanitize_path,
    sanitize_srt,
    sanitize_text,
    sanitize_token,
    sanitize_url,
    setup_logger,
)


@pytest.fixture(scope="session", autouse=True)
def cleanup_log_artifacts():
    yield
    for logger_name in (
        "vectcut",
        "test_vectcut",
        "test_idempotent",
        "test_existing_handler",
        "test_delayed_file",
        "test_no_propagate",
    ):
        logger = logging.getLogger(logger_name)
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            handler.close()
    if not _DEFAULT_LOG_FILE_EXISTED_BEFORE_IMPORT and _DEFAULT_LOG_FILE.exists():
        _DEFAULT_LOG_FILE.unlink()
    if not _LOG_DIR_EXISTED_BEFORE_IMPORT and _LOG_DIR.exists():
        try:
            _LOG_DIR.rmdir()
        except OSError:
            pass


def test_sanitize_path_keeps_only_filename():
    assert sanitize_path("E:/素材/第5期/video1.mp4") == "video1.mp4"
    assert sanitize_path("C:\\Users\\test\\audio.mp3") == "audio.mp3"
    assert sanitize_path("simple.mp4") == "simple.mp4"


def test_sanitize_srt_records_size_only():
    srt = "1\n00:00:00,000 --> 00:00:02,000\n你好世界\n"
    result = sanitize_srt(srt)
    assert "bytes" in result
    assert "3 lines" in result
    assert "你好世界" not in result


def test_sanitize_token_masks_values_completely():
    token = "abcdef1234567890xyz"
    result = sanitize_token(token)
    assert result == "***"
    assert "abcdef12" not in result
    assert token not in result


def test_sanitize_token_masks_short_values_completely():
    assert sanitize_token("abc") == "***"


def test_sanitize_url_masks_short_sensitive_query_values():
    result = sanitize_url("https://example.com/a?token=abc")
    assert "token=abc" not in result
    assert "abc" not in result
    assert "example.com/a" in result


def test_sanitize_text_masks_short_free_text_secrets():
    result = sanitize_text("token=abc")
    assert "token=abc" not in result
    assert "abc" not in result


def test_sanitize_text_preserves_http_api_paths():
    result = sanitize_text("POST /api/template/import failed")
    assert "/api/template/import" in result


def test_sanitize_text_masks_posix_media_paths():
    result = sanitize_text("failed writing /home/alice/secret/video.mp4")
    assert "/home/alice/secret/video.mp4" not in result
    assert "/home/alice/secret" not in result
    assert "video.mp4" in result


def test_sanitize_text_masks_unicode_posix_paths():
    result = sanitize_text("failed /tmp/素材/video.mp4")
    assert "/tmp/素材/video.mp4" not in result
    assert "/tmp/素材" not in result
    assert "video.mp4" in result


def test_sanitize_text_masks_top_level_posix_paths():
    result = sanitize_text("failed opening /tmp/secret.txt")
    assert "/tmp/secret.txt" not in result
    assert "secret.txt" in result


def test_sanitize_text_masks_quoted_windows_paths_with_spaces():
    raw_path = r"C:\Users\Alice\My Videos\secret.mp4"
    result = sanitize_text(f'failed writing "{raw_path}"')
    assert raw_path not in result
    assert "My Videos" not in result
    assert "secret.mp4" in result


def test_sanitize_text_masks_quoted_posix_paths_with_spaces():
    raw_path = "/home/alice/My Videos/secret.mp4"
    result = sanitize_text(f"failed writing '{raw_path}'")
    assert raw_path not in result
    assert "My Videos" not in result
    assert "secret.mp4" in result


def test_sanitize_text_masks_unquoted_windows_paths_with_spaces():
    raw_path = r"C:\Users\Alice\My Videos\secret clip.mp4"
    result = sanitize_text(f"failed writing {raw_path}")
    assert raw_path not in result
    assert r"C:\Users\Alice" not in result
    assert "My Videos" not in result
    assert "secret clip.mp4" in result


def test_sanitize_text_masks_unquoted_windows_paths_with_spaces_without_extension():
    raw_path = r"C:\Users\Alice\My Videos\draft123"
    result = sanitize_text(f"failed writing {raw_path}")
    assert raw_path not in result
    assert r"C:\Users\Alice" not in result
    assert "My Videos" not in result
    assert "draft123" in result


def test_sanitize_text_masks_unquoted_posix_paths_with_spaces():
    raw_path = "/home/alice/My Videos/secret clip.mp4"
    result = sanitize_text(f"failed writing {raw_path}")
    assert raw_path not in result
    assert "/home/alice" not in result
    assert "My Videos" not in result
    assert "secret clip.mp4" in result


def test_sanitize_text_masks_unquoted_posix_paths_with_spaces_without_extension():
    raw_path = "/home/alice/My Videos/draft123"
    result = sanitize_text(f"failed writing {raw_path}")
    assert raw_path not in result
    assert "/home/alice" not in result
    assert "My Videos" not in result
    assert "draft123" in result


def test_sanitize_text_masks_free_text_secrets():
    result = sanitize_text(
        "token=SECRET_TOKEN_123456 access_token SECRET_TOKEN_123456"
    )
    assert "SECRET_TOKEN_123456" not in result
    assert "SECRET_T" not in result
    assert "token=***" in result
    assert "access_token ***" in result


def test_sanitize_text_masks_free_text_credentials():
    result = sanitize_text(
        "credential=secret123 credential: secret456 credential secret789 token=tok123"
    )
    assert "secret123" not in result
    assert "secret456" not in result
    assert "secret789" not in result
    assert "tok123" not in result
    assert "credential=***" in result
    assert "credential: ***" in result
    assert "credential ***" in result
    assert "token=***" in result


def test_sanitize_text_masks_authorization_bearer_token():
    result = sanitize_text("Authorization: Bearer SECRET_TOKEN_123456")
    assert "SECRET_TOKEN_123456" not in result
    assert "SECRET_T" not in result
    assert "Authorization: Bearer ***" in result


def test_sanitize_text_masks_authorization_basic_credential():
    result = sanitize_text("Request failed with Authorization: Basic dXNlcjpwYXNz")
    assert "dXNlcjpwYXNz" not in result
    assert "dXNlcj" not in result
    assert "Authorization: Basic ***" in result


def test_sanitize_text_masks_authorization_basic_without_colon():
    result = sanitize_text("Request failed with Authorization Basic dXNlcjpwYXNz")
    assert "dXNlcjpwYXNz" not in result
    assert "dXNlcj" not in result
    assert "Authorization Basic ***" in result


def test_sanitize_text_masks_bare_bearer_token():
    result = sanitize_text("download failed: Bearer SECRET_TOKEN_123456")
    assert "SECRET_TOKEN_123456" not in result
    assert "SECRET_T" not in result
    assert "Bearer ***" in result


def test_sanitize_url_removes_userinfo_and_sensitive_query():
    result = sanitize_url(
        "https://user:password@example.com/path/file.mp4?token=SECRET_TOKEN_123456"
    )
    assert "user:password@" not in result
    assert "password" not in result
    assert "SECRET_TOKEN_123456" not in result
    assert "SECRET_T" not in result
    assert "example.com/path/file.mp4" in result
    assert "token=%2A%2A%2A" in result or "token=***" in result


@pytest.mark.parametrize(
    "url",
    [
        "https://cdn.example.com/token/SECRET_TOKEN_123456/video.mp4",
        "https://cdn.example.com/access_token=SECRET_TOKEN_123456/video.mp4",
    ],
)
def test_sanitize_url_masks_sensitive_path_segments(url):
    result = sanitize_text(f"download failed: {url}")

    assert "cdn.example.com" in result
    assert "video.mp4" in result
    assert "SECRET_TOKEN_123456" not in result
    assert "SECRET_T" not in result


def test_sanitize_exception_masks_posix_path_without_extension():
    result = sanitize_exception(
        PermissionError(13, "Permission denied", "/home/alice/secret/draft123")
    )
    assert "/home/alice/secret/draft123" not in result
    assert "/home/alice/secret" not in result
    assert "draft123" in result


def test_sanitize_dict_masks_sensitive_keys():
    data = {
        "username": "test",
        "password": "secret123",
        "api_key": "key456",
        "nested": {"token": "tok789", "safe": "ok"},
    }
    result = sanitize_dict(data)
    assert result["username"] == "test"
    assert result["password"] == "***"
    assert result["api_key"] == "***"
    assert result["nested"]["token"] == "***"
    assert result["nested"]["safe"] == "ok"


def test_sanitize_dict_masks_sensitive_keys_inside_sequences():
    data = {
        "items": [{"access_token": "tok123", "safe": "ok"}],
        "tuple_items": ({"client_secret": "secret123"}, {"safe": "value"}),
    }
    result = sanitize_dict(data)
    assert isinstance(result["items"], list)
    assert isinstance(result["tuple_items"], tuple)
    assert result["items"][0]["access_token"] == "***"
    assert result["items"][0]["safe"] == "ok"
    assert result["tuple_items"][0]["client_secret"] == "***"
    assert result["tuple_items"][1]["safe"] == "value"


def test_sanitize_dict_masks_normalized_sensitive_keys():
    data = {
        "client_secret": "secret123",
        "apiKey": "key456",
        "refresh-token": "tok789",
        "username": "test",
    }
    result = sanitize_dict(data)
    assert result["client_secret"] == "***"
    assert result["apiKey"] == "***"
    assert result["refresh-token"] == "***"
    assert result["username"] == "test"


def test_setup_logger_returns_logger_with_handlers(tmp_path):
    logger = setup_logger("test_vectcut", log_dir=str(tmp_path))
    assert isinstance(logger, logging.Logger)
    assert len(logger.handlers) >= 2


def test_setup_logger_idempotent(tmp_path):
    logger1 = setup_logger("test_idempotent", log_dir=str(tmp_path))
    handler_count = len(logger1.handlers)
    logger2 = setup_logger("test_idempotent", log_dir=str(tmp_path))
    assert len(logger2.handlers) == handler_count


def test_setup_logger_preserves_existing_handlers_and_adds_managed_handlers(tmp_path):
    logger = logging.getLogger("test_existing_handler")
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()
    null_handler = logging.NullHandler()
    logger.addHandler(null_handler)

    logger = setup_logger("test_existing_handler", log_dir=str(tmp_path))

    managed_handlers = [
        handler
        for handler in logger.handlers
        if getattr(handler, "_vectcut_managed", False)
    ]
    assert null_handler in logger.handlers
    assert len(managed_handlers) == 2
    assert {
        getattr(handler, "_vectcut_handler_kind", None) for handler in managed_handlers
    } == {"file", "console"}

    setup_logger("test_existing_handler", log_level="DEBUG", log_dir=str(tmp_path))
    managed_handlers_after_repeat = [
        handler
        for handler in logger.handlers
        if getattr(handler, "_vectcut_managed", False)
    ]
    assert null_handler in logger.handlers
    assert len(managed_handlers_after_repeat) == 2
    assert logger.level == logging.DEBUG


def test_import_does_not_create_default_logs_directory(tmp_path):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2])

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import pathlib; import vectcut.core.logger; print(pathlib.Path('logs').exists())",
        ],
        cwd=tmp_path,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.strip() == "False"
    assert not (tmp_path / "logs").exists()


def test_setup_logger_creates_log_file_on_first_emit(tmp_path):
    log_dir = tmp_path / "nested" / "logs"
    logger = setup_logger("test_delayed_file", log_dir=str(log_dir))
    log_file = log_dir / "vectcut.log"

    assert not log_dir.exists()
    assert not log_file.exists()

    logger.info("hello")
    for handler in logger.handlers:
        handler.flush()

    assert log_file.exists()
    assert "hello" in log_file.read_text(encoding="utf-8")


def test_setup_logger_does_not_propagate_to_root(tmp_path):
    stream = io.StringIO()
    root_handler = logging.StreamHandler(stream)
    root_logger = logging.getLogger()
    root_logger.addHandler(root_handler)
    try:
        logger = setup_logger("test_no_propagate", log_dir=str(tmp_path))

        assert logger.propagate is False

        logger.info("root should not see this")
        for handler in logger.handlers:
            handler.flush()
        root_handler.flush()

        assert "root should not see this" not in stream.getvalue()
    finally:
        root_logger.removeHandler(root_handler)
        root_handler.close()


def test_default_logger_configures_vectcut_handlers():
    assert default_logger is logging.getLogger("vectcut")
    assert len(default_logger.handlers) >= 2

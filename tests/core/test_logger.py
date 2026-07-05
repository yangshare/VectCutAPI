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
    sanitize_path,
    sanitize_srt,
    sanitize_token,
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


def test_sanitize_token_keeps_first_8_chars():
    token = "abcdef1234567890xyz"
    result = sanitize_token(token)
    assert result == "abcdef12..."
    assert "xyz" not in result


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

"""统一日志器，内置用户隐私脱敏（方案一 §6.2）。

脱敏规则：
  - 素材路径：仅保留文件名
  - SRT 内容：仅记录字节数/行数
  - 下载 token：替换为固定占位
  - 敏感字段（password/token/api_key/secret）：替换为 ***
"""
from __future__ import annotations

import logging
import logging.handlers
import os
import re
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Dict
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


_SENSITIVE_KEY_PARTS = ("password", "token", "secret", "credential")
_SENSITIVE_KEYS = {"apikey", "accesskey", "accesssecret"}
_MANAGED_HANDLER_ATTR = "_vectcut_managed"
_HANDLER_KIND_ATTR = "_vectcut_handler_kind"
_URL_PATTERN = re.compile(r"https?://[^\s'\"<>]+")
_QUOTED_PATH_PATTERN = re.compile(
    r"(?P<quote>['\"])(?P<path>(?:[A-Za-z]:[\\/]|/)[^'\"]+"
    r"\.(?:mp4|mov|m4v|mp3|wav|m4a|aac|png|jpg|jpeg|webp|gif|zip|json|srt|txt))"
    r"(?P=quote)",
    re.IGNORECASE,
)
_SPACED_ABSOLUTE_PATH_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_])(?:[A-Za-z]:[\\/]|/)[^'\"<>]*?\s+[^'\"<>]*?"
    r"\.(?:mp4|mov|m4v|avi|mkv|flv|mp3|wav|aac|m4a|flac|jpg|jpeg|png|webp|bmp|gif|zip|json|srt|txt)\b",
    re.IGNORECASE,
)
_SPACED_ABSOLUTE_PATH_NO_EXT_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_])"
    r"(?:[A-Za-z]:[\\/]|/(?:home|Users|tmp|var|private|mnt|media|opt|Volumes)/)"
    r"(?=[^'\"<>\r\n]*\s)"
    r"(?:[^\\/ \t\r\n'\"<>]+[\\/])*"
    r"[^'\"<>\r\n]*[\\/][^\\/ \t\r\n'\"<>.,;:)]+",
    re.IGNORECASE,
)
_WINDOWS_PATH_PATTERN = re.compile(r"[A-Za-z]:[\\/](?![\\/])[^\s'\"<>]+")
_POSIX_PATH_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_])/"
    r"(?:home|Users|tmp|var|private|mnt|media|opt|Volumes)/"
    r"(?:[^\s'\"<>/:]+/)*[^\s'\"<>/:]+",
    re.IGNORECASE,
)
_AUTHORIZATION_CREDENTIAL_PATTERN = re.compile(
    r"\b(?P<prefix>Authorization(?:\s*:\s*|\s+)[A-Za-z][A-Za-z0-9._~-]*\s+)"
    r"(?P<value>[^\s'\"&;,)]+)",
    re.IGNORECASE,
)
_BEARER_TOKEN_PATTERN = re.compile(
    r"\b(?P<prefix>Bearer\s+)"
    r"(?P<value>[^\s'\"&;,)]+)",
    re.IGNORECASE,
)
_FREE_TEXT_SECRET_PATTERN = re.compile(
    r"\b(?P<key>access[_-]?token|api[_-]?key|password|secret|credential|token)\b"
    r"(?P<sep>\s*[=:]\s*|\s+)"
    r"(?P<value>[^\s'\"&;,)]+)",
    re.IGNORECASE,
)


class _DelayedDirectoryTimedRotatingFileHandler(logging.handlers.TimedRotatingFileHandler):
    """Create the log directory only when the file is opened for emit."""

    def _open(self):
        os.makedirs(os.path.dirname(self.baseFilename), exist_ok=True)
        return super()._open()


def sanitize_path(path: str) -> str:
    """素材路径脱敏：仅保留文件名。"""
    if not path:
        return path
    return Path(path.replace("\\", "/")).name


def sanitize_srt(srt: str) -> str:
    """SRT 内容脱敏：仅记录字节数和行数。"""
    if not srt:
        return "SRT: empty"
    return f"SRT: {len(srt.encode('utf-8'))} bytes, {len(srt.splitlines())} lines"


def sanitize_token(token: str) -> str:
    """token 脱敏：任意非空值替换为固定占位。"""
    if not token:
        return token
    return "***"


def _sanitize_url_path(path: str) -> str:
    if not path:
        return path

    segments = path.split("/")
    sanitized: list[str] = []
    mask_next = False
    for segment in segments:
        if not segment:
            sanitized.append(segment)
            continue

        if mask_next:
            sanitized.append(sanitize_token(segment))
            mask_next = False
            continue

        if "=" in segment:
            key, value = segment.split("=", 1)
            if _is_sensitive_key(key):
                sanitized.append(f"{key}={sanitize_token(value)}")
                continue

        sanitized.append(segment)
        if _is_sensitive_key(segment):
            mask_next = True

    return "/".join(sanitized)


def sanitize_url(url: str) -> str:
    """URL 脱敏：保留 host/path，敏感 query 仅保留摘要。"""
    if not url:
        return url
    parts = urlsplit(url)
    if not parts.scheme or not parts.netloc:
        return url

    safe_netloc = parts.hostname or parts.netloc.rsplit("@", 1)[-1]
    if ":" in safe_netloc and not safe_netloc.startswith("["):
        safe_netloc = f"[{safe_netloc}]"
    try:
        port = parts.port
    except ValueError:
        port = None
    if port is not None:
        safe_netloc = f"{safe_netloc}:{port}"

    safe_params = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        if _is_sensitive_key(key):
            safe_params.append((key, sanitize_token(value)))
    safe_query = urlencode(safe_params)
    safe_path = _sanitize_url_path(parts.path)
    return urlunsplit((parts.scheme, safe_netloc, safe_path, safe_query, ""))


def sanitize_text(text: str) -> str:
    """脱敏自由文本中的 URL query/token 和本地路径。"""
    if not text:
        return text

    placeholder_id = uuid.uuid4().hex
    sanitized_urls: list[str] = []
    sanitized_paths: list[str] = []

    def _stash_url(match: re.Match[str]) -> str:
        sanitized_urls.append(sanitize_url(match.group(0)))
        return f"__VECTCUT_{placeholder_id}_URL_{len(sanitized_urls) - 1}__"

    def _restore_url(match: re.Match[str]) -> str:
        try:
            return sanitized_urls[int(match.group(1))]
        except (IndexError, ValueError):
            return match.group(0)

    def _stash_path(path: str) -> str:
        sanitized_paths.append(sanitize_path(path))
        return f"__VECTCUT_{placeholder_id}_PATH_{len(sanitized_paths) - 1}__"

    def _restore_path(match: re.Match[str]) -> str:
        try:
            return sanitized_paths[int(match.group(1))]
        except (IndexError, ValueError):
            return match.group(0)

    def _sanitize_secret(match: re.Match[str]) -> str:
        return (
            f"{match.group('key')}{match.group('sep')}"
            f"{sanitize_token(match.group('value'))}"
        )

    text = _URL_PATTERN.sub(_stash_url, text)
    text = _QUOTED_PATH_PATTERN.sub(
        lambda match: f"{match.group('quote')}{_stash_path(match.group('path'))}{match.group('quote')}",
        text,
    )
    text = _SPACED_ABSOLUTE_PATH_PATTERN.sub(
        lambda match: _stash_path(match.group(0)), text
    )
    text = _SPACED_ABSOLUTE_PATH_NO_EXT_PATTERN.sub(
        lambda match: _stash_path(match.group(0)), text
    )
    text = _WINDOWS_PATH_PATTERN.sub(
        lambda match: _stash_path(match.group(0)), text
    )
    text = _POSIX_PATH_PATTERN.sub(
        lambda match: _stash_path(match.group(0)), text
    )
    text = _AUTHORIZATION_CREDENTIAL_PATTERN.sub(
        lambda match: f"{match.group('prefix')}{sanitize_token(match.group('value'))}",
        text,
    )
    text = _BEARER_TOKEN_PATTERN.sub(
        lambda match: f"{match.group('prefix')}{sanitize_token(match.group('value'))}",
        text,
    )
    text = _FREE_TEXT_SECRET_PATTERN.sub(_sanitize_secret, text)
    prefix = re.escape(placeholder_id)
    text = re.sub(rf"__VECTCUT_{prefix}_PATH_(\d+)__", _restore_path, text)
    return re.sub(rf"__VECTCUT_{prefix}_URL_(\d+)__", _restore_url, text)


def sanitize_exception(exc: BaseException) -> str:
    """异常文本脱敏，避免下游 stderr/trace message 泄露路径或 token。"""
    return sanitize_text(str(exc))


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("_", "").replace("-", "")
    return normalized in _SENSITIVE_KEYS or any(
        part in normalized for part in _SENSITIVE_KEY_PARTS
    )


def _sanitize_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return sanitize_dict(dict(value))
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_sanitize_value(item) for item in value)
    return value


def sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """字典脱敏：敏感字段替换为 ***。"""
    result = {}
    for k, v in data.items():
        if _is_sensitive_key(str(k)):
            result[k] = "***"
        else:
            result[k] = _sanitize_value(v)
    return result


def _is_managed_handler(handler: logging.Handler, kind: str) -> bool:
    return (
        getattr(handler, _MANAGED_HANDLER_ATTR, False)
        and getattr(handler, _HANDLER_KIND_ATTR, None) == kind
    )


def _mark_managed_handler(handler: logging.Handler, kind: str) -> None:
    setattr(handler, _MANAGED_HANDLER_ATTR, True)
    setattr(handler, _HANDLER_KIND_ATTR, kind)
    handler.set_name(f"vectcut.{kind}")


def setup_logger(
    name: str,
    log_level: str = "INFO",
    log_dir: str = "logs",
    backup_days: int = 7,
) -> logging.Logger:
    """构造统一日志器（文件按天滚动 + 控制台双输出）。"""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    logger.propagate = False

    has_file_handler = any(_is_managed_handler(handler, "file") for handler in logger.handlers)
    has_console_handler = any(
        _is_managed_handler(handler, "console") for handler in logger.handlers
    )

    if not has_file_handler:
        file_handler = _DelayedDirectoryTimedRotatingFileHandler(
            filename=os.path.join(log_dir, "vectcut.log"),
            when="midnight",
            backupCount=backup_days,
            encoding="utf-8",
            delay=True,
        )
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
        )
        _mark_managed_handler(file_handler, "file")
        logger.addHandler(file_handler)

    if not has_console_handler:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(
            logging.Formatter("%(levelname)-8s | %(name)s | %(message)s")
        )
        _mark_managed_handler(console_handler, "console")
        logger.addHandler(console_handler)

    return logger


default_logger = setup_logger("vectcut")

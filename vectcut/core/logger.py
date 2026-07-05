"""统一日志器，内置用户隐私脱敏（方案一 §6.2）。

脱敏规则：
  - 素材路径：仅保留文件名
  - SRT 内容：仅记录字节数/行数
  - 下载 token：仅保留前 8 位
  - 敏感字段（password/token/api_key/secret）：替换为 ***
"""
from __future__ import annotations

import logging
import logging.handlers
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Dict


_SENSITIVE_KEY_PARTS = ("password", "token", "secret")
_SENSITIVE_KEYS = {"apikey", "accesskey", "accesssecret"}
_MANAGED_HANDLER_ATTR = "_vectcut_managed"
_HANDLER_KIND_ATTR = "_vectcut_handler_kind"


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
    """token 脱敏：仅保留前 8 位。"""
    if not token:
        return token
    return token[:8] + "..."


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

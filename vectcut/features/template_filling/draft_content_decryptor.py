"""剪映 draft_content.json 服务端解密封装。"""

from __future__ import annotations

import ctypes
import os
from ctypes import POINTER, Structure, c_bool, c_uint64, c_void_p
from ctypes import wintypes
from pathlib import Path

from vectcut.core.errors import make_error
from vectcut.core.logger import sanitize_exception

_ORD_DECRYPT = 7256


class _MsvcString(Structure):
    _pack_ = 8
    _fields_ = [
        ("d0", c_uint64),
        ("d1", c_uint64),
        ("size", c_uint64),
        ("capacity", c_uint64),
    ]


class _StrArg:
    def __init__(self, data: bytes):
        self._buf = data
        n = len(data)
        self.s = _MsvcString(0, 0, n, 15 if n < 16 else n)
        if n < 16:
            self.s.d0 = int.from_bytes(data[:8].ljust(8, b"\x00"), "little")
            self.s.d1 = int.from_bytes(data[8:16].ljust(8, b"\x00"), "little")
        else:
            self._addr = ctypes.create_string_buffer(data, len(data))
            self.s.d0 = ctypes.addressof(self._addr)
            self.s.d1 = 0
            self.s.capacity = n


_DECRYPT_T = ctypes.CFUNCTYPE(
    c_void_p,
    c_void_p,
    POINTER(_MsvcString),
    POINTER(_MsvcString),
    POINTER(_MsvcString),
    POINTER(c_bool),
)


def decrypt_draft_content(cipher: bytes, dll_path: str) -> bytes:
    """用剪映 videoeditor.dll 解密 draft_content bytes。"""
    dll = Path(dll_path) if dll_path else None
    if dll is None or not dll.is_file():
        raise make_error(
            "T_ENCRYPTED_DRAFT_UNSUPPORTED",
            "服务端未配置剪映解密 DLL，无法导入加密 draft_content.json",
        )
    if os.name != "nt":
        raise make_error(
            "T_DECRYPT_FAILED",
            "当前平台无法加载剪映 videoeditor.dll",
            details={"platform": os.name},
        )

    try:
        decrypt_fn = _load_decrypt_fn(dll)
        plain, ok = _call_decrypt(decrypt_fn, cipher)
    except Exception as exc:
        raise make_error(
            "T_DECRYPT_FAILED",
            "draft_content.json 解密失败",
            details={"reason": sanitize_exception(exc)},
        ) from exc

    if not ok:
        raise make_error("T_DECRYPT_FAILED", "draft_content.json 解密失败")
    return plain


def _load_decrypt_fn(dll_path: Path):
    dll_dir = str(dll_path.parent)
    os.add_dll_directory(dll_dir)

    kernel32 = ctypes.windll.kernel32
    kernel32.LoadLibraryExW.argtypes = [wintypes.LPCWSTR, c_void_p, wintypes.DWORD]
    kernel32.LoadLibraryExW.restype = c_void_p
    kernel32.GetProcAddress.argtypes = [c_void_p, c_void_p]
    kernel32.GetProcAddress.restype = c_void_p

    flags = 0x00000100 | 0x00001000
    handle = kernel32.LoadLibraryExW(str(dll_path), None, flags)
    if not handle:
        raise OSError(f"LoadLibraryExW failed: {kernel32.GetLastError()}")
    address = kernel32.GetProcAddress(handle, _ORD_DECRYPT)
    if not address:
        raise OSError(f"GetProcAddress ordinal {_ORD_DECRYPT} failed")
    return _DECRYPT_T(address)


def _take(value: _MsvcString) -> bytes:
    if value.capacity < 16:
        raw = (ctypes.c_ubyte * 16).from_address(ctypes.addressof(value))
        return bytes(raw)[: value.size]
    return ctypes.string_at(value.d0, value.size)


def _call_decrypt(decrypt_fn, cipher: bytes) -> tuple[bytes, bool]:
    in_arg = _StrArg(cipher)
    param = _StrArg(b"{}")
    out = _MsvcString(0, 0, 0, 15)
    ok = c_bool(False)
    decrypt_fn(
        None,
        ctypes.byref(out),
        ctypes.byref(in_arg.s),
        ctypes.byref(param.s),
        ctypes.byref(ok),
    )
    return _take(out), bool(ok.value)

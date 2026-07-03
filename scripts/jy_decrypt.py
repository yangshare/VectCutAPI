# -*- coding: utf-8 -*-
"""
剪映 draft_content.json 解密工具（适用于 jianying_draft_encrypt 方案）。

原理：剪映的加密密钥/算法内嵌在安装目录的 videoeditor.dll 中，
通过加载本机该 DLL 并调用其导出函数 EncryptUtils::decrypt 来解密。
完全复刻社区工具 jy-draftc (MIT, wenshui330) 的调用方式。

用法：
    python jy_decrypt.py <draft_content.json> [输出明文路径]
不传输出路径则默认 <输入>.plain.json，原文件不会被覆盖。
"""
import os
import sys
import ctypes
from ctypes import (
    Structure, c_void_p, c_uint64, c_ubyte, c_bool,
    POINTER, c_char_p, cast,
)
import ctypes.wintypes as wt

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# ---- 路径与符号 ----
JY_INSTALL_DIR = r"C:\Users\Administrator\AppData\Local\JianyingPro\Apps\8.9.0.13361"
DLL_NAME = "videoeditor.dll"

# ---- 导出符号（序号，来自 dumpbin /exports，按 ordinal 调用更稳） ----
# 8.9.0.13361 videoeditor.dll
ORD_DECRYPT = 7256   # ?decrypt@EncryptUtils@lvve@@...AEBV34@0AEA_N@Z  (带 bool& ok)
ORD_ENCRYPT = 8177   # ?encrypt@EncryptUtils@lvve@@...AEBV34@@Z
ORD_ENABLE = 8159    # ?enable@EncryptUtils@lvve@@QEAAX_N@Z


class MsvcString(Structure):
    """模拟 MSVC std::string 的内存布局 (SSO 阈值 16)。

    布局: data[16] | size(u64) | capacity(u64)
    - capacity < 16: 数据内联在 data 前 size 字节
    - capacity >= 16: data 前 8 字节是堆指针
    """
    _pack_ = 8
    _fields_ = [
        ("d0", c_uint64),   # data[0:8]
        ("d1", c_uint64),   # data[8:16]
        ("size", c_uint64),
        ("capacity", c_uint64),
    ]


class StrArg:
    """构造一个传入 DLL 的 std::string，并保持底层缓冲存活。"""
    def __init__(self, text: bytes):
        self._buf = text  # 保持引用
        n = len(text)
        self.s = MsvcString(0, 0, n, 15 if n < 16 else n)
        if n < 16:
            self.s.d0 = int.from_bytes(text[:8].ljust(8, b"\x00"), "little")
            self.s.d1 = int.from_bytes(text[8:16].ljust(8, b"\x00"), "little")
        else:
            # 前 8 字节存放堆指针
            self._addr = ctypes.create_string_buffer(text, len(text))
            self.s.d0 = ctypes.addressof(self._addr)
            self.s.d1 = 0
            self.s.capacity = n


def take(s: MsvcString) -> bytes:
    """从 DLL 写回的 std::string 中取出 bytes。"""
    if s.capacity < 16:
        raw = (ctypes.c_ubyte * 16).from_address(ctypes.addressof(s))
        data = bytes(raw)[: s.size]
        return data
    else:
        ptr = s.d0
        return ctypes.string_at(ptr, s.size)


# ---- 函数指针类型 ----
# 复刻 jy-draftc:
#   DecryptFn = MsvcString* (*)(void* this, MsvcString* out,
#                               const MsvcString* in, const MsvcString* param, bool* ok)
#   EncryptFn = MsvcString* (*)(void* this, MsvcString* out, const MsvcString* in)
#   EnableFn  = void          (void* this, bool)
DECRYPT_T = ctypes.CFUNCTYPE(
    c_void_p, c_void_p, POINTER(MsvcString),
    POINTER(MsvcString), POINTER(MsvcString), POINTER(c_bool),
)
ENCRYPT_T = ctypes.CFUNCTYPE(
    c_void_p, c_void_p, POINTER(MsvcString), POINTER(MsvcString),
)
ENABLE_T = ctypes.CFUNCTYPE(None, c_void_p, c_bool)


def load_dll():
    k32 = ctypes.windll.kernel32
    k32.AddDllDirectory.argtypes = [wt.LPCWSTR]
    k32.AddDllDirectory.restype = c_void_p
    k32.LoadLibraryExW.argtypes = [wt.LPCWSTR, c_void_p, wt.DWORD]
    k32.LoadLibraryExW.restype = c_void_p
    os.add_dll_directory(JY_INSTALL_DIR)
    LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR = 0x00000100
    LOAD_LIBRARY_SEARCH_DEFAULT_DIRS = 0x00001000
    flags = LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_DEFAULT_DIRS
    h = k32.LoadLibraryExW(JY_INSTALL_DIR + os.sep + DLL_NAME, None, flags)
    if not h:
        raise OSError(f"LoadLibraryExW 失败, err={k32.GetLastError()}")
    k32.GetProcAddress.argtypes = [c_void_p, c_void_p]
    k32.GetProcAddress.restype = c_void_p

    def get(ordinal, ftype, label):
        # 按 ordinal 调用：GetProcAddress(h, MAKEINTRESOURCE(ordinal))
        # 传整数作 c_void_p，低 16 位 < 64K 触发 IS_INTRESOURCE 序号路径
        addr = k32.GetProcAddress(h, ordinal)
        if not addr:
            raise OSError(f"找不到导出序号 {ordinal} ({label}), err={k32.GetLastError()}")
        return ftype(addr)

    return (
        get(ORD_DECRYPT, DECRYPT_T, "decrypt"),
        get(ORD_ENCRYPT, ENCRYPT_T, "encrypt"),
        get(ORD_ENABLE, ENABLE_T, "enable"),
    )


def decrypt_text(dec_fn, cipher_text: bytes) -> bytes:
    """对加密文本调用 DLL decrypt，返回明文 bytes。"""
    in_arg = StrArg(cipher_text)
    param = StrArg(b"{}")
    out = MsvcString(0, 0, 0, 15)
    ok = c_bool(False)
    dec_fn(None, ctypes.byref(out), ctypes.byref(in_arg.s),
           ctypes.byref(param.s), ctypes.byref(ok))
    return take(out), ok.value


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else src + ".plain.json"

    with open(src, "rb") as f:
        cipher = f.read()
    print(f"读入密文: {src} ({len(cipher)} 字节)")

    print(f"加载 videoeditor.dll: {JY_INSTALL_DIR}")
    dec_fn, enc_fn, enable_fn = load_dll()
    print("DLL 与 EncryptUtils 入口加载成功")

    plain, ok = decrypt_text(dec_fn, cipher)
    print(f"解密返回 ok={ok}, 明文长度={len(plain)}")
    head = plain[:80].decode("utf-8", "replace")
    print(f"明文开头: {head!r}")

    # 校验是否为合法 JSON
    import json
    try:
        json.loads(plain)
        print("✅ 明文是合法 JSON")
    except Exception as e:
        print(f"⚠️ 明文 JSON 校验失败: {e}")

    with open(dst, "wb") as f:
        f.write(plain)
    print(f"✅ 已写出明文: {dst}")


if __name__ == "__main__":
    main()

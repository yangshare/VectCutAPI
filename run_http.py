#!/usr/bin/env python3
"""VectCutAPI FastAPI 入口（替代 capcut_server.py）。

规格 §3.1：根目录只留入口脚本与配置，业务全进 vectcut/ 包。
"""
import uvicorn

from vectcut.core.config import load_config


def main():
    cfg = load_config()
    uvicorn.run(
        "vectcut.server.http.app:app",
        host="0.0.0.0",
        port=cfg.port,
    )


if __name__ == "__main__":
    main()

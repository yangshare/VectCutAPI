"""黄金测试公共 fixture。

REGENERATE_GOLDEN=1 时，测试把当前路由输出写回 snapshots/ 而非比对——
用于首次建基线或确认变更后主动更新基线。
"""
import os
from pathlib import Path

import pytest

SNAPSHOT_DIR = Path(__file__).parent / "snapshots"


@pytest.fixture(scope="session")
def regenerate_golden() -> bool:
    return os.environ.get("REGENERATE_GOLDEN") == "1"


@pytest.fixture(scope="session")
def snapshot_dir() -> Path:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    return SNAPSHOT_DIR

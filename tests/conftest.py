import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SNAPSHOT_DIR = Path(__file__).parent / "golden" / "snapshots"


@pytest.fixture(scope="session")
def regenerate_golden() -> bool:
    """REGENERATE_GOLDEN=1 时写回 snapshots/ 而非比对（首次建基线或主动更新）。"""
    return os.environ.get("REGENERATE_GOLDEN") == "1"


@pytest.fixture(scope="session")
def snapshot_dir() -> Path:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    return SNAPSHOT_DIR

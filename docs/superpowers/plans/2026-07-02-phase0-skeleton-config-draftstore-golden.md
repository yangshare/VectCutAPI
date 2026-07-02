# 阶段 0：骨架 + 配置统一 + draft_store 合并 + 黄金测试基线 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 在不动业务路由的前提下，搭出 `vectcut/` 包骨架，把配置统一到 `core/config.py`（Pydantic 强类型），把 `settings/` 降级为薄转发垫片以解除引擎循环依赖，合并 `draft_cache` + `draft_profiles` 为 `core/draft_store.py`，并建立黄金测试基线作为后续阶段迁移的防回归安全网。

**架构：** 新增 `vectcut/` 包，`core/` 子层承载跨切面基础设施。`config.json`（JSON5）仍为唯一用户可编辑源；`core/config.py` 用 Pydantic `BaseModel` + `load_config()` 工厂加载（不引入 `pydantic-settings` 新依赖，刻意简化）。`settings/` 不删，改为转发 `config.py` 的垫片，引擎两处 `IS_CAPCUT_ENV` import 走单一依赖方向：引擎 → settings 垫片 → config.py。`draft_store` 合并 cache（LRU）与 profiles（DraftProfile 注册表），对外提供 `get_draft(id)` / `get_active_profile()`。

**技术栈：** Python 3.10+、Pydantic v2（已在依赖中）、json5（settings/local.py 已 try-import，沿用）、pytest（已有 conftest）。

**前置约束（来自规格 §2、§5.2）：**
- 引擎层 `pyJianYingDraft/` **只读不改**。
- `config.json` 是 JSON5（带 `//` 注释），**必须用 `json5` 加载**，不能用标准 `json`。
- 引擎两处循环依赖：`pyJianYingDraft/video_segment.py:14`、`pyJianYingDraft/script_file.py:22`，均 `import` 应用层 `settings`。垫片必须保 `IS_CAPCUT_ENV` 可用。
- `settings/__init__.py` 死代码（`API_KEYS / MODEL_CONFIG / PURCHASE_LINKS / LICENSE_CONFIG`、`get_platform_info()`）在本阶段删除。

**本阶段不触碰：** `capcut_server.py`、`mcp_server.py`、各 `add_*` / `save_draft_impl` 业务实现、`pyJianYingDraft/` 内部。它们继续从旧 `settings.local` / `draft_cache` / `draft_profiles` 导入——垫片与 `draft_store` 必须向后兼容这些旧导入路径（旧模块保留为转发垫片直到阶段 5 清理）。

---

## 文件结构

| 文件 | 职责 | 动作 |
|------|------|------|
| `vectcut/__init__.py` | 主包入口，导出版本号 | 创建 |
| `vectcut/core/__init__.py` | core 子包 | 创建 |
| `vectcut/core/config.py` | Pydantic 配置模型 + `load_config()` 工厂（json5 加载） | 创建 |
| `vectcut/core/draft_store.py` | 合并 draft_cache（LRU）+ draft_profiles（DraftProfile 注册表）；提供 `get_draft` / `get_active_profile` / `update_cache` | 创建 |
| `settings/__init__.py` | 降级为垫片：只导出 `IS_CAPCUT_ENV`（从 config 读）；删死代码 | 修改 |
| `settings/local.py` | 降级为垫片：转发 `config.load_config()` 结果，导出旧常量名（`IS_CAPCUT_ENV`/`DRAFT_PROFILE`/`DRAFT_DOMAIN`/`PREVIEW_ROUTER`/`PORT`/`IS_UPLOAD_DRAFT`/`DRAFT_FOLDER`/`OSS_CONFIG`/`MP4_OSS_CONFIG`） | 修改 |
| `draft_cache.py` | 暂时保留，改为转发 `vectcut.core.draft_store` 的 `DRAFT_CACHE` / `update_cache` | 修改 |
| `draft_profiles.py` | 暂时保留，改为转发 `vectcut.core.draft_store` 的 `DraftProfile` / `PROFILES` / `get_draft_profile` / `write_profile_content` 等 | 修改 |
| `pyproject.toml` | 暂不动 name/URL（阶段 5 统一）；本阶段不动 | — |
| `tests/core/test_config.py` | config 模型 + load_config 单元测试 | 创建 |
| `tests/core/test_draft_store.py` | draft_store 合并后行为测试（含从 `test_draft_profiles.py` 移植的用例） | 创建 |
| `tests/golden/__init__.py` | 黄金测试包标记 | 创建 |
| `tests/golden/conftest.py` | 黄金基线：Flask test client fixture + 快照比对 helper | 创建 |
| `tests/golden/test_metadata_routes_golden.py` | 11 个 `get_xxx_types` 路由输出快照 | 创建 |
| `tests/golden/snapshots/*.json` | 元数据路由的实际快照（首次运行生成并 commit） | 创建 |
| `tests/core/__init__.py`、`tests/__init__.py` | 包标记 | 创建（若缺） |

**关键设计决策：**
- `config.py` 用 `BaseModel` + 工厂函数而非 `pydantic-settings.BaseSettings`：避免新增 `pydantic-settings` 依赖；json5 加载逻辑已在 `settings/local.py` 验证过，沿用。
- `draft_store` 同时保留 `DRAFT_CACHE` 模块级 `OrderedDict`（旧代码直接 `from draft_cache import DRAFT_CACHE` 引用），向后兼容。
- 黄金基线**只覆盖确定性路由**：11 个元数据 GET 路由（无网络、无 draft 状态、纯枚举遍历）。draft 变更类路由因依赖远程 URL 下载与文件系统，本阶段不建快照，留给阶段 2 迁移时按 feature 补service 单测。规格 §7 "每个路由跑一遍" 的理想目标受网络依赖约束做务实收敛，已在自检中标注。

---

### 任务 1：建 vectcut/ 包骨架与包发现

**文件：**
- 创建：`vectcut/__init__.py`、`vectcut/core/__init__.py`
- 创建：`tests/__init__.py`、`tests/core/__init__.py`

- [ ] **步骤 1：创建包标记文件**

`vectcut/__init__.py`：
```python
"""VectCutAPI 主包。阶段 0 骨架：仅 core 子包就位，业务 features 在后续阶段填入。"""

__version__ = "1.0.0"
```

`vectcut/core/__init__.py`：
```python
"""跨切面基础设施：配置、错误、日志、draft_store、oss、downloader。阶段 0 只含 config + draft_store。"""
```

`tests/__init__.py`（空文件）：
```python
```
`tests/core/__init__.py`（空文件）：
```python
```

- [ ] **步骤 2：验证包可导入**

运行：`python -c "import vectcut, vectcut.core; print(vectcut.__version__)"`
预期：输出 `1.0.0`，无 ImportError。

- [ ] **步骤 3：Commit**

```bash
git add vectcut/__init__.py vectcut/core/__init__.py tests/__init__.py tests/core/__init__.py
git commit -m "feat(core): 新增 vectcut 包骨架与 core 子包"
```

---

### 任务 2：core/config.py — Pydantic 配置模型 + json5 加载（TDD）

**文件：**
- 创建：`vectcut/core/config.py`
- 创建：`tests/core/test_config.py`

- [ ] **步骤 1：编写失败的测试**

`tests/core/test_config.py`：
```python
import json
from pathlib import Path

import pytest


def _write_config(tmp_path: Path, **overrides) -> Path:
    """生成一份最小合法 config.json（JSON5，带注释）。"""
    base = {
        "draft_profile": "jianying_legacy",
        "is_capcut_env": False,
        "draft_domain": "https://www.example.com",
        "port": 9001,
        "preview_router": "/draft/downloader",
        "is_upload_draft": False,
        "draft_folder": "",
        "oss_config": {
            "bucket_name": "b",
            "access_key_id": "k",
            "access_key_secret": "s",
            "endpoint": "https://e",
        },
        "mp4_oss_config": {
            "bucket_name": "mb",
            "access_key_id": "mk",
            "access_key_secret": "ms",
            "region": "cn-hangzhou",
            "endpoint": "http://m",
        },
    }
    base.update(overrides)
    path = tmp_path / "config.json"
    # 故意写入 JSON5 注释，验证加载器容忍注释
    text = json.dumps(base, ensure_ascii=False) + "\n// trailing comment line\n"
    path.write_text(text, encoding="utf-8")
    return path


def test_load_config_reads_all_fields_and_tolerates_json5_comments(tmp_path):
    from vectcut.core.config import load_config

    path = _write_config(tmp_path)
    cfg = load_config(path)

    assert cfg.draft_profile == "jianying_legacy"
    assert cfg.is_capcut_env is False
    assert cfg.draft_domain == "https://www.example.com"
    assert cfg.port == 9001
    assert cfg.preview_router == "/draft/downloader"
    assert cfg.is_upload_draft is False
    assert cfg.draft_folder == ""
    assert cfg.oss_config.bucket_name == "b"
    assert cfg.oss_config.endpoint == "https://e"
    assert cfg.mp4_oss_config.region == "cn-hangzhou"


def test_load_config_applies_defaults_when_fields_missing(tmp_path):
    from vectcut.core.config import load_config

    path = tmp_path / "config.json"
    # 只写 draft_profile，其余走默认
    path.write_text('{"draft_profile": "capcut_legacy"}', encoding="utf-8")
    cfg = load_config(path)

    assert cfg.draft_profile == "capcut_legacy"
    assert cfg.port == 9001           # 默认与 config.json 现值一致
    assert cfg.is_upload_draft is False
    assert cfg.draft_folder == ""


def test_load_config_falls_back_to_project_root_config_when_path_none(tmp_path, monkeypatch):
    from vectcut.core.config import load_config

    # 不传路径 → 读项目根 config.json（真实存在）
    cfg = load_config(None)
    assert cfg.draft_profile in {"capcut_legacy", "jianying_legacy", "jianying_pro_10"}
    assert isinstance(cfg.port, int)


def test_load_config_missing_file_uses_defaults_and_does_not_raise(tmp_path):
    from vectcut.core.config import load_config

    cfg = load_config(tmp_path / "nope.json")
    assert cfg.draft_profile == "capcut_legacy"  # 缺省默认
    assert cfg.is_capcut_env is True
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m pytest tests/core/test_config.py -v`
预期：FAIL，`ModuleNotFoundError: No module named 'vectcut.core.config'`（或 `AttributeError: cannot import load_config`）。

- [ ] **步骤 3：编写最少实现代码**

`vectcut/core/config.py`：
```python
"""强类型运行时配置。

config.json 是唯一用户可编辑源；它是 JSON5（带 // 注释），必须用 json5 加载。
为避免引入 pydantic-settings 新依赖，采用 BaseModel + load_config() 工厂，
而非 BaseSettings。规格 §5.2 的"Pydantic Settings"诉求由强类型模型满足。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

try:
    import json5  # 支持带注释的配置文件
except ModuleNotFoundError:  # settings/local.py 沿用的回退策略
    import json as json5


_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_CONFIG_PATH = _PROJECT_ROOT / "config.json"


class OssConfig(BaseModel):
    bucket_name: str = ""
    access_key_id: str = ""
    access_key_secret: str = ""
    endpoint: str = ""


class Mp4OssConfig(BaseModel):
    bucket_name: str = ""
    access_key_id: str = ""
    access_key_secret: str = ""
    region: str = ""
    endpoint: str = ""


class Settings(BaseModel):
    """运行时配置聚合。字段默认值与 config.json 现值 / settings/local.py 旧默认对齐。"""

    draft_profile: str = "capcut_legacy"
    is_capcut_env: bool = True              # 废弃字段，过渡期保留读取（规格 §5.2）
    draft_domain: str = "https://www.capcutapi.top"
    port: int = 9001
    preview_router: str = "/draft/downloader"
    is_upload_draft: bool = False
    draft_folder: str = ""
    oss_config: OssConfig = Field(default_factory=OssConfig)
    mp4_oss_config: Mp4OssConfig = Field(default_factory=Mp4OssConfig)


def load_config(path: Optional[os.PathLike] = None) -> Settings:
    """加载 config.json（JSON5）。文件缺失或解析失败时返回全默认 Settings，不抛。"""
    config_path = Path(path) if path is not None else _DEFAULT_CONFIG_PATH
    if not config_path.exists():
        return Settings()
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            raw = json5.load(f)
    except Exception:
        return Settings()
    return Settings.model_validate(raw)
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m pytest tests/core/test_config.py -v`
预期：4 项全 PASS。

- [ ] **步骤 5：Commit**

```bash
git add vectcut/core/config.py tests/core/test_config.py
git commit -m "feat(core): 新增 Pydantic 强类型 config 加载器（json5 兼容）"
```

---

### 任务 3：core/draft_store.py — 合并 draft_cache + draft_profiles（TDD）

**文件：**
- 创建：`vectcut/core/draft_store.py`
- 创建：`tests/core/test_draft_store.py`

**说明：** `draft_cache.py`（LRU OrderedDict + `update_cache`）与 `draft_profiles.py`（`DraftProfile` dataclass + `PROFILES`/`ALIASES` + `get_draft_profile`/`write_profile_content`）本就管同一件事（草稿存取），合并为 `draft_store`。实现内容**逐字搬运**自现有两文件（不改行为），外加 `get_draft(id)` 访问器与 `get_active_profile()`（从 `config` 读激活 profile）。`tests/test_draft_profiles.py` 现有 5 个用例全部移植到 `test_draft_store.py`，断言保持不变。

- [ ] **步骤 1：编写失败的测试（移植 + 新增）**

`tests/core/test_draft_store.py`：把 `tests/test_draft_profiles.py` 的全部 5 个测试函数**原样复制**过来，仅把 `from draft_profiles import ...` 改为 `from vectcut.core.draft_store import ...`、`from draft_cache import DRAFT_CACHE` 改为 `from vectcut.core.draft_store import DRAFT_CACHE`、`from save_draft_impl import build_asset_path` 等保持不变（save_draft_impl 本阶段不动）。

再加 2 个新测试覆盖新增能力：

```python
def test_get_draft_returns_cached_script_and_none_when_missing():
    from vectcut.core.draft_store import DRAFT_CACHE, get_draft, update_cache

    DRAFT_CACHE.pop("d1", None)
    assert get_draft("d1") is None

    sentinel = object()
    update_cache("d1", sentinel)
    assert get_draft("d1") is sentinel


def test_get_active_profile_reads_draft_profile_from_config(monkeypatch):
    from vectcut.core import draft_store
    from vectcut.core.draft_store import DraftProfile, get_active_profile

    # 注入伪 Settings，验证 get_active_profile 走 config 而非 settings.local
    class FakeSettings:
        draft_profile = "jianying_pro_10"

    monkeypatch.setattr(draft_store, "_load_settings", lambda: FakeSettings())

    profile = get_active_profile()
    assert isinstance(profile, DraftProfile)
    assert profile.name == "jianying_pro_10"
    assert profile.template_dir == "template_jianying_10_2"
```

移植的 5 个用例（`test_jianying_10_profile_uses_versioned_template_and_content_names`、`test_legacy_profiles_keep_existing_template_names`、`test_write_profile_content_updates_main_mirrors_and_timeline`、`test_script_dumps_uses_requested_profile_platform_and_mask_key`、`test_save_draft_writes_to_requested_draft_folder`、`test_shared_draft_asset_path_keeps_drive_root`）原样保留——注意 `test_save_draft_writes_to_requested_draft_folder` 内 `from draft_cache import DRAFT_CACHE` 要改成 `from vectcut.core.draft_store import DRAFT_CACHE`。

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m pytest tests/core/test_draft_store.py -v`
预期：FAIL，`ModuleNotFoundError: No module named 'vectcut.core.draft_store'`。

- [ ] **步骤 3：编写实现（搬运 + 合并）**

`vectcut/core/draft_store.py`：把 `draft_cache.py` 与 `draft_profiles.py` 的全部代码合并到此处，**逻辑不改**，外加：

```python
# 文件顶部新增
from typing import Dict, Optional
from collections import OrderedDict
import pyJianYingDraft as draft

# —— 以下为 draft_cache.py 原内容（逐字搬运）——
DRAFT_CACHE: Dict[str, 'draft.Script_file'] = OrderedDict()
MAX_CACHE_SIZE = 10000

def update_cache(key: str, value: draft.Script_file) -> None:
    if key in DRAFT_CACHE:
        DRAFT_CACHE.pop(key)
    elif len(DRAFT_CACHE) >= MAX_CACHE_SIZE:
        print(f"{key}, Cache is full, deleting the least recently used item")
        DRAFT_CACHE.popitem(last=False)
    DRAFT_CACHE[key] = value

# —— 以下为 draft_profiles.py 原内容（逐字搬运：DraftProfile / CAPCUT_PLATFORM /
#    JIANYING_10_PLATFORM / PROFILES / PROFILE_ALIASES / normalize_profile_name /
#    get_draft_profile / get_template_dir / write_profile_content）——
#    其中 get_draft_profile(name=None) 内部 `from settings.local import DRAFT_PROFILE`
#    改为走 config：name 为 None 时调 get_active_profile()。

# —— 新增 ——
def _load_settings():
    """惰性加载 config，避免循环 import。供测试 monkeypatch。"""
    from vectcut.core.config import load_config
    return load_config()

def get_draft(draft_id: str):
    """从 LRU cache 取草稿对象；不存在返回 None。"""
    return DRAFT_CACHE.get(draft_id)

def get_active_profile() -> "DraftProfile":
    """返回当前激活 profile（从 config.draft_profile 解析）。"""
    return get_draft_profile(_load_settings().draft_profile)
```

`get_draft_profile` 的 name=None 分支改为：
```python
def get_draft_profile(name: Optional[str] = None) -> DraftProfile:
    if name is None:
        try:
            name = _load_settings().draft_profile
        except Exception:
            name = "capcut_legacy"
    return PROFILES[normalize_profile_name(name)]
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m pytest tests/core/test_draft_store.py -v`
预期：移植的 5 项 + 新增 2 项，全 PASS。

- [ ] **步骤 5：Commit**

```bash
git add vectcut/core/draft_store.py tests/core/test_draft_store.py
git commit -m "feat(core): 合并 draft_cache 与 draft_profiles 为 draft_store"
```

---

### 任务 4：settings/ 降级为 config.py 薄转发垫片

**文件：**
- 修改：`settings/__init__.py`
- 修改：`settings/local.py`

**目标：** 删除 `settings/local.py` 的 json5 加载逻辑、漂移默认值、死代码；改为从 `vectcut.core.config.load_config()` 读一次，导出旧常量名供现有 import 方（`capcut_server.py:39` 等）继续工作。`settings/__init__.py` 删除 `API_KEYS / MODEL_CONFIG / PURCHASE_LINKS / LICENSE_CONFIG` 死声明与 `get_platform_info()`（与 `draft_profiles.CAPCUT_PLATFORM` 重复且无调用方）。

- [ ] **步骤 1：编写回归测试（验证垫片导出旧名）**

追加到 `tests/core/test_config.py`：
```python
def test_settings_shim_reexports_legacy_constants_from_config(tmp_path, monkeypatch):
    """capcut_server.py 仍 `from settings.local import IS_CAPCUT_ENV, DRAFT_DOMAIN,
    PREVIEW_ROUTER, PORT` — 垫片必须继续导出这些名字且值与 config 一致。"""
    import settings
    import settings.local as local
    from vectcut.core.config import load_config

    cfg = load_config(None)

    assert settings.IS_CAPCUT_ENV == cfg.is_capcut_env
    assert local.IS_CAPCUT_ENV == cfg.is_capcut_env
    assert local.DRAFT_DOMAIN == cfg.draft_domain
    assert local.PREVIEW_ROUTER == cfg.preview_router
    assert local.PORT == cfg.port
    assert local.DRAFT_PROFILE == cfg.draft_profile
    assert local.IS_UPLOAD_DRAFT == cfg.is_upload_draft
    assert local.DRAFT_FOLDER == cfg.draft_folder


def test_settings_shim_drops_dead_code():
    """死代码已删：__all__ 不再声明 4 个无人定义的名字。"""
    import settings

    for dead in ("API_KEYS", "MODEL_CONFIG", "PURCHASE_LINKS", "LICENSE_CONFIG"):
        assert dead not in getattr(settings, "__all__", [])
        assert not hasattr(settings, dead)
    assert not hasattr(settings, "get_platform_info")
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m pytest tests/core/test_config.py -v`
预期：新增 2 项 FAIL（`settings.local.DRAFT_DOMAIN` 等仍为旧漂移值 `https://www.install-ai-guider.top`，与 config 不一致；`__all__` 仍含死名）。

- [ ] **步骤 3：改写 settings/local.py 为垫片**

`settings/local.py` 全量替换为：
```python
"""配置垫片：转发到 vectcut.core.config。

历史：本文件曾自带 json5 加载与漂移默认值（PORT=9000 vs config.json 9001 等），
现降级为薄转发，消除配置双轨制（规格 §1.1 问题 4 / §5.2）。
仅保留供旧 import 方（capcut_server.py 等）使用的模块级常量名。
真源：config.json → vectcut.core.config.load_config()。
"""

from vectcut.core.config import load_config

_cfg = load_config(None)

IS_CAPCUT_ENV = _cfg.is_capcut_env
DRAFT_PROFILE = _cfg.draft_profile
DRAFT_DOMAIN = _cfg.draft_domain
PREVIEW_ROUTER = _cfg.preview_router
IS_UPLOAD_DRAFT = _cfg.is_upload_draft
DRAFT_FOLDER = _cfg.draft_folder
PORT = _cfg.port
OSS_CONFIG = _cfg.oss_config.model_dump()
MP4_OSS_CONFIG = _cfg.mp4_oss_config.model_dump()
```

- [ ] **步骤 4：改写 settings/__init__.py 为垫片**

`settings/__init__.py` 全量替换为：
```python
"""配置包垫片：仅供 pyJianYingDraft 引擎两处 `from settings import IS_CAPCUT_ENV`
（video_segment.py:14 / script_file.py:22）继续工作。

依赖方向单一：引擎 → settings 垫片 → vectcut.core.config（真源）。
引擎日后若移除那两处 import，本垫片即可彻底删除（规格 §5.2）。
"""

from .local import IS_CAPCUT_ENV  # noqa: F401  引擎 import 此名

__all__ = ["IS_CAPCUT_ENV"]
```

- [ ] **步骤 5：运行测试验证通过**

运行：`python -m pytest tests/core/test_config.py -v`
预期：全 PASS（含新增 2 项）。

- [ ] **步骤 6：验证引擎循环依赖未破**

运行：
```bash
python -c "import pyJianYingDraft; print('engine import OK')"
python -c "from settings import IS_CAPCUT_ENV; print('settings shim OK', IS_CAPCUT_ENV)"
```
预期：两行均无 ImportError。

- [ ] **步骤 7：Commit**

```bash
git add settings/__init__.py settings/local.py tests/core/test_config.py
git commit -m "refactor(settings): 降级为 config.py 薄转发垫片，删除死代码与漂移默认值"
```

---

### 任务 5：draft_cache.py / draft_profiles.py 改为转发垫片（向后兼容旧 import）

**文件：**
- 修改：`draft_cache.py`
- 修改：`draft_profiles.py`

**目标：** 业务代码（`capcut_server.py`、`save_draft_impl.py`、`test_draft_profiles.py` 等）本阶段不动，仍 `from draft_cache import DRAFT_CACHE` / `from draft_profiles import get_draft_profile`。把这两个根目录模块改为转发 `vectcut.core.draft_store`，保证旧行为不破。原 `test_draft_profiles.py` 保留**原样**作为额外回归网（它从根 `draft_profiles` 导入，验证垫片转发正确）。

- [ ] **步骤 1：改写 draft_cache.py**

`draft_cache.py` 全量替换为：
```python
"""垫片：转发到 vectcut.core.draft_store.DRAFT_CACHE / update_cache。

业务代码阶段 5 才统一切换到 vectcut.core.draft_store 直连；在此之前保留此转发。
"""
from vectcut.core.draft_store import DRAFT_CACHE, MAX_CACHE_SIZE, update_cache  # noqa: F401
```

- [ ] **步骤 2：改写 draft_profiles.py**

`draft_profiles.py` 全量替换为：
```python
"""垫片：转发到 vectcut.core.draft_store 的 profile 相关符号。

业务代码阶段 5 才统一切换；在此之前保留此转发，旧 `from draft_profiles import ...` 不破。
"""
from vectcut.core.draft_store import (  # noqa: F401
    CAPCUT_PLATFORM,
    JIANYING_10_PLATFORM,
    PROFILES,
    PROFILE_ALIASES,
    DraftProfile,
    get_draft_profile,
    get_template_dir,
    normalize_profile_name,
    write_profile_content,
)
```

- [ ] **步骤 3：运行全量测试验证不破**

运行：`python -m pytest tests/ -v`
预期：`test_draft_profiles.py`（5 项，从根 `draft_profiles` 导入）+ `test_draft_store.py`（7 项）+ `test_config.py` 全 PASS。

- [ ] **步骤 4：Commit**

```bash
git add draft_cache.py draft_profiles.py
git commit -m "refactor(core): draft_cache/draft_profiles 改为转发 draft_store 的垫片"
```

---

### 任务 6：黄金测试基线 — 元数据路由快照（11 个 GET 路由）

**文件：**
- 创建：`tests/golden/__init__.py`
- 创建：`tests/golden/conftest.py`
- 创建：`tests/golden/test_metadata_routes_golden.py`
- 创建：`tests/golden/snapshots/`（首次运行生成 .json）

**目标（规格 §7）：** 迁移前对确定性路由建快照基线。本任务覆盖 11 个 `get_xxx_types` 元数据 GET 路由——它们纯枚举遍历、无网络、无 draft 状态，是黄金基线的理想首批对象。draft 变更类路由因依赖远程 URL 下载，本阶段不建快照（自检已标注遗漏）。

11 个路由清单（从 `capcut_server.py` grep 实测，规格称"14"已修正为 11）：
`/get_intro_animation_types`、`/get_outro_animation_types`、`/get_combo_animation_types`、`/get_transition_types`、`/get_mask_types`、`/get_audio_effect_types`、`/get_font_types`、`/get_text_intro_types`、`/get_text_outro_types`、`/get_text_loop_anim_types`、`/get_video_scene_effect_types`、`/get_video_character_effect_types`。

- [ ] **步骤 1：编写黄金测试（首次运行以"生成模式"产出快照）**

`tests/golden/__init__.py`（空）：
```python
```

`tests/golden/conftest.py`：
```python
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
```

`tests/golden/test_metadata_routes_golden.py`：
```python
"""11 个 get_xxx_types 元数据路由的黄金基线。

迁移前捕获：阶段 1 元数据收敛为 /metadata/{kind} 后，每个 kind 必须复现同样输出，
旧 14 别名路径也必须等价——本基线即防回归网。
"""
import json

import pytest

# 路由路径列表（与 capcut_server.py grep 实测一致）
METADATA_ROUTES = [
    "/get_intro_animation_types",
    "/get_outro_animation_types",
    "/get_combo_animation_types",
    "/get_transition_types",
    "/get_mask_types",
    "/get_audio_effect_types",
    "/get_font_types",
    "/get_text_intro_types",
    "/get_text_outro_types",
    "/get_text_loop_anim_types",
    "/get_video_scene_effect_types",
    "/get_video_character_effect_types",
]


@pytest.fixture(scope="module")
def client():
    """启动现有 Flask app 的测试客户端。本阶段 capcut_server 未动。"""
    # 延迟 import，避免收集期副作用
    import capcut_server

    capcut_server.app.config["TESTING"] = True
    with capcut_server.app.test_client() as c:
        yield c


@pytest.mark.parametrize("route", METADATA_ROUTES)
def test_metadata_route_matches_golden(client, route, snapshot_dir, regenerate_golden):
    resp = client.get(route)
    assert resp.status_code == 200
    payload = resp.get_json()

    # 规范化：output 列表按 JSON 序列化排序，消除枚举遍历顺序漂移，
    # 但**保留每个 item 的完整结构**（audio_effect 含 {name,type,params}，必须原样留存，
    # 供阶段 1 元数据收敛验证完全保真）。
    normalized = _normalize(payload)
    snap_path = snapshot_dir / f"metadata{route.replace('/', '_')}.json"

    if regenerate_golden:
        snap_path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
        pytest.skip(f"golden regenerated: {snap_path.name}")

    assert snap_path.exists(), (
        f"快照缺失：{snap_path}。运行 `REGENERATE_GOLDEN=1 python -m pytest "
        "tests/golden/test_metadata_routes_golden.py` 生成基线。"
    )
    expected = json.loads(snap_path.read_text(encoding="utf-8"))
    assert normalized == expected, f"{route} 输出与黄金基线不一致（见 {snap_path.name}）"


def _normalize(payload):
    """保留 output 完整结构，仅对列表排序以消除遍历顺序漂移。

    audio_effect 的 item 形如 {name, type, params:[{name,default_value,...}]}，
    必须原样保留——阶段 1 收敛须复现 params 的 ×100 缩放与 type 标签。
    """
    import json as _json

    out = payload.get("output", [])
    if isinstance(out, list):
        out = sorted(out, key=lambda x: _json.dumps(x, ensure_ascii=False, sort_keys=True))
    return {"success": payload.get("success"), "output": out, "error": payload.get("error", "")}
```

- [ ] **步骤 2：首次运行生成快照**

运行（PowerShell）：
```bash
$env:REGENERATE_GOLDEN=1; python -m pytest tests/golden/test_metadata_routes_golden.py -v
```
预期：12 项（11 路由 × 1，参数化）全部 SKIPPED，并在 `tests/golden/snapshots/` 下生成 12 个 `metadata_get_xxx_types.json` 文件。

- [ ] **步骤 3：复核生成的快照**

运行：`python -c "import json,pathlib; p=sorted(pathlib.Path('tests/golden/snapshots').glob('*.json')); [print(x.name, len(json.loads(x.read_text(encoding='utf-8'))['output']), 'items') for x in p]"`
预期：12 个文件，每个 `output` 项数 > 0（font 可能较少，但非空）。人工抽查 `metadata_get_audio_effect_types.json` 确认 item 含 `name/type/params` 三键（富结构保真）；抽查 `metadata_get_intro_animation_types.json` 确认 item 形如 `{"name": "..."}`。

- [ ] **步骤 4：回归模式运行验证基线稳定**

运行：
```bash
python -m pytest tests/golden/test_metadata_routes_golden.py -v
```
预期：12 项全 PASS（不带 REGENERATE_GOLDEN 时走比对分支）。

- [ ] **步骤 5：Commit 快照与测试**

```bash
git add tests/golden/
git commit -m "test(golden): 新增 11 个元数据路由的黄金基线快照"
```

---

### 任务 7：阶段 0 收尾验证

- [ ] **步骤 1：全量测试**

运行：`python -m pytest tests/ -v`
预期：全绿。应包含 `test_config.py`（6 项）、`test_draft_store.py`（7 项）、`test_draft_profiles.py`（5 项，垫片回归）、`test_metadata_routes_golden.py`（12 项）。

- [ ] **步骤 2：验证旧入口仍可启动（未触碰业务）**

运行：
```bash
python -c "import capcut_server; print('capcut_server OK', len([r for r in capcut_server.app.url_map.iter_rules() if r.endpoint != 'static']), 'routes')"
python -c "import mcp_server; print('mcp_server OK')"
```
预期：两行均无 ImportError；`capcut_server` 报 ~25 路由。

- [ ] **步骤 3：验证配置单一源生效**

运行：
```bash
python -c "from settings.local import PORT; from vectcut.core.config import load_config; assert PORT == load_config(None).port, (PORT, load_config(None).port); print('config single-source OK', PORT)"
```
预期：`config single-source OK 9001`（证明 settings 垫片与 config 同源，漂移默认值已消除）。

- [ ] **步骤 4：Commit 阶段标记（可选 tag）**

```bash
git commit --allow-empty -m "chore: 阶段0 骨架完成——vectcut 包 + config 统一 + draft_store 合并 + 黄金基线"
```

---

## 自检

**1. 规格覆盖度（阶段 0 范围 = 规格 §8 阶段 0 行）：**

| 规格要求 | 覆盖任务 |
|----------|----------|
| 建 `vectcut/` 包空骨架 | 任务 1 |
| `core/config.py`（Pydantic Settings，读 config.json） | 任务 2 |
| `settings/` 降级为 config.py 薄转发垫片（保引擎两处 IS_CAPCUT_ENV） | 任务 4 |
| 删 `settings/` 死代码（`__all__` 4 名 / `get_platform_info`） | 任务 4 步骤 3-4 + 测试 |
| `draft_store`（合并 cache + profiles） | 任务 3 |
| 黄金测试基线 | 任务 6（元数据 11 路由） |
| 旧模块向后兼容（业务本阶段不动） | 任务 5（垫片转发） |

**阶段 0 未覆盖（明确留给后续阶段，非遗漏）：**
- `core/errors.py` / `logging.py` / `oss.py` / `downloader.py`：规格 §3.1 列出但属阶段 1-2 范围（errors 在阶段 1 双入口统一时落地最自然；oss/downloader 迁移随 features）。
- draft 变更类路由黄金快照：受远程 URL 下载约束，本阶段务实收敛；阶段 2 迁移各 feature service 时按 service 单测补防回归网（规格 §7 "feature 测试直接调 service"）。

**2. 占位符扫描：** 无 "TODO"/"待定"/"添加错误处理" 等空泛步骤；每个代码步骤均含完整可运行代码或精确命令。任务 3 的 draft_profiles 搬运指明"逐字搬运"并附关键函数签名，非泛述。

**3. 类型/命名一致性：**
- `load_config(path) -> Settings`：任务 2 定义，任务 4 `settings/local.py` 调用，任务 3 `draft_store._load_settings` 调用——签名一致。
- `Settings` 字段名（`draft_profile` / `is_capcut_env` / `draft_domain` / `port` / `preview_router` / `is_upload_draft` / `draft_folder` / `oss_config` / `mp4_oss_config`）：任务 2、任务 4 垫片导出名、任务 4 测试断言名三处一致。
- `DRAFT_CACHE` / `update_cache` / `DraftProfile` / `PROFILES` / `get_draft_profile` / `write_profile_content` / `get_active_profile` / `get_draft`：任务 3 定义，任务 5 垫片转发名一致。
- `get_active_profile()` 与 `get_draft(id)` 为新增，仅任务 3 内部及测试使用，无后续阶段冲突。

**自检发现并修正：**
- 原规格 §8 称元数据"14 接口"，实测 11 个具名路由（任务 6 已据实修正并注明）。
- 原规格 §5.2 称用 `pydantic-settings` 风格 Settings；本计划改用 `BaseModel + load_config()` 工厂以避免新增依赖，已在 config.py 顶部注释说明该刻意简化。

---

## 执行交接

计划已完成并保存到 `docs/superpowers/plans/2026-07-02-phase0-skeleton-config-draftstore-golden.md`。两种执行方式：

**1. 子代理驱动（推荐）** - 每个任务调度一个新的子代理，任务间进行审查，快速迭代

**2. 内联执行** - 在当前会话中使用 executing-plans 执行任务，批量执行并设有检查点

**选哪种方式？**

> 阶段 1 计划（engine 适配层 + 元数据收敛）见 `docs/superpowers/plans/2026-07-02-phase1-engine-adapter-metadata.md`，建议在阶段 0 全绿出 release 后再启动。

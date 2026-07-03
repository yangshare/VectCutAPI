# 阶段5 清理收尾与身份统一 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 删除阶段 0–4 迁移后遗留的根目录旧文件、flask_router、settings 死代码，迁移仍被引用的工具模块到 `vectcut/core/`，归位脚本/资源，统一项目身份（pyproject name、mcp_config command、URL），拆分 `example.py` 88KB 上帝文件，最终全量测试 + 36 黄金全绿出 release。

**架构：** 阶段 0–4 已完成分层 + Feature 包 + FastAPI/MCP 双入口（最新 commit `611cc75` 收官）。本阶段不再加功能，只做"行为不变的结构清理"。核心约束：引擎层 `pyJianYingDraft` 只读不改，其对应用层 `settings`（`video_segment.py:14` / `script_file.py:22`）与 `draft_profiles`（`draft_folder.py:9` / `script_file.py:23`）的两处反向 import 必须以垫片保留，不可删垫片。所有清理步骤以"黄金测试 + 全量测试不回归"为安全网。

**技术栈：** Python 3.10+、FastAPI、Pydantic v2、pytest、flake8、pyJianYingDraft（只读引擎）。

**前置状态确认（每个任务开始前必做）：**
- 当前分支干净：`git status` 应 clean
- 基线绿：`pytest -q` 全绿 + `flake8 vectcut tests run_http.py run_mcp.py` 无错
- 黄金绿：`pytest tests/golden -q` 36 项全绿

**验证命令约定（本计划全程复用）：**
- 全量测试：`pytest -q`
- 黄金测试：`pytest tests/golden -q`
- Lint：`flake8 vectcut tests run_http.py run_mcp.py`
- 单文件引用扫描：`grep -rln --include="*.py" "<模块名>" . | grep -v __pycache__`

---

## 文件结构（本阶段产出/改动）

**迁移（根目录 → `vectcut/core/`）：**
- `util.py` → `vectcut/core/util.py`（7 函数：hex_to_rgb / is_windows_path / build_draft_asset_path / zip_draft / url_to_hash / timing_decorator / generate_draft_url）
- `oss.py` → `vectcut/core/oss.py`
- `downloader.py` → `vectcut/core/downloader.py`
- `save_task_cache.py` → `vectcut/core/task_cache.py`（6 函数）

**删除（根目录旧业务文件，零或仅垫片引用）：**
- `add_audio_track.py` `add_video_track.py` `add_text_impl.py` `add_subtitle_impl.py` `add_image_impl.py` `add_effect_impl.py` `add_sticker_impl.py` `add_video_keyframe_impl.py` `get_duration_impl.py` `save_draft_impl.py` `create_draft.py` `draft_cache.py`
- `vectcut/features/*/flask_router.py`（7 个，已被 FastAPI `router.py` 取代）

**保留为垫片（引擎循环依赖，不可删）：**
- `settings/__init__.py` `settings/local.py`（瘦身到仅 `IS_CAPCUT_ENV`）
- `draft_profiles.py`（已垫片，转发 `vectcut.core.draft_store`）

**归位（移动）：**
- `jy_decrypt.py` `gen_local_draft.py` → `scripts/`
- `test_mcp_client.py` → `tests/`
- `rest_client_test.http` `shuangnan.plain.json` → `examples/` / `tests/golden/`
- `pattern/` 内容 → `examples/`
- `example.py`（2377 行）→ 拆成 `examples/` 下按功能切分的多个小脚本

**身份统一：**
- `pyproject.toml`（name / URL）
- `mcp_config.json`（command / server 名）

---

### 任务 1：迁移 `util.py` → `vectcut/core/util.py`

`util.py`（95 行，7 函数）被 vectcut 内 6 处 + 测试若干处引用，是迁移最大头。先迁它，建立迁移范式。

**文件：**
- 创建：`vectcut/core/util.py`
- 修改：`vectcut/engine/material_factory.py:15`、`vectcut/features/draft/_save_engine.py:28`、`vectcut/features/audio/service.py:12`、`vectcut/features/text/service.py:27`、`vectcut/features/image/service.py:18`、`vectcut/features/video/service.py:22`
- 删除：`util.py`
- 测试：`tests/core/test_util.py`（新建，覆盖 7 函数纯逻辑）

- [ ] **步骤 1：编写失败测试 `tests/core/test_util.py`**

```python
"""vectcut.core.util 纯逻辑测试（迁自根 util.py，行为不变）。"""
from vectcut.core.util import (
    hex_to_rgb,
    is_windows_path,
    build_draft_asset_path,
    url_to_hash,
    generate_draft_url,
)


def test_hex_to_rgb():
    assert hex_to_rgb("#FF8800") == (255, 136, 0)


def test_is_windows_path():
    assert is_windows_path("E:\\tmp\\x") is True
    assert is_windows_path("/tmp/x") is False


def test_build_draft_asset_path():
    p = build_draft_asset_path("/df", "d1", "audio", "a.mp3")
    assert "d1" in p and "audio" in p and "a.mp3" in p


def test_url_to_hash_stable():
    h1 = url_to_hash("https://x/y.mp4")
    h2 = url_to_hash("https://x/y.mp4")
    assert h1 == h2 and len(h1) == 16


def test_generate_draft_url_contains_id():
    assert "d1" in generate_draft_url("d1")
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest tests/core/test_util.py -q`
预期：FAIL，`ModuleNotFoundError: No module named 'vectcut.core.util'`

- [ ] **步骤 3：创建 `vectcut/core/util.py`（逐字复制根 `util.py` 全部内容）**

读取根 `util.py` 全部 95 行，原样写入 `vectcut/core/util.py`，仅在文件头追加模块 docstring 注明"迁自根 util.py（阶段5）"。函数体、签名、实现一字不改。

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest tests/core/test_util.py -q`
预期：PASS

- [ ] **步骤 5：改 vectcut 内 6 处 import 为 `vectcut.core.util`**

逐文件替换（精确行号见上"修改"清单）：

| 文件 | 旧 | 新 |
|------|----|----|
| `vectcut/engine/material_factory.py:15` | `from util import build_draft_asset_path` | `from vectcut.core.util import build_draft_asset_path` |
| `vectcut/features/draft/_save_engine.py:28` | `from util import build_draft_asset_path, zip_draft` | `from vectcut.core.util import build_draft_asset_path, zip_draft` |
| `vectcut/features/audio/service.py:12` | `from util import url_to_hash` | `from vectcut.core.util import url_to_hash` |
| `vectcut/features/text/service.py:27` | `from util import hex_to_rgb` | `from vectcut.core.util import hex_to_rgb` |
| `vectcut/features/image/service.py:18` | `from util import url_to_hash` | `from vectcut.core.util import url_to_hash` |
| `vectcut/features/video/service.py:22` | `from util import url_to_hash` | `from vectcut.core.util import url_to_hash` |

- [ ] **步骤 6：确认根 `util.py` 已无 vectcut/tests 引用**

运行：`grep -rln --include="*.py" "from util import\|import util" vectcut tests run_http.py run_mcp.py | grep -v __pycache__`
预期：空输出（注意排除 `vectcut.core.util` 的误匹配——此 grep 匹配的是裸 `util`，不会匹配 `vectcut.core.util`）

若仍有匹配，逐处改为 `vectcut.core.util`。

- [ ] **步骤 7：删根 `util.py`**

```bash
git rm util.py
```

- [ ] **步骤 8：全量验证不回归**

运行：`pytest -q && flake8 vectcut tests run_http.py run_mcp.py && pytest tests/golden -q`
预期：全量测试全绿、flake8 无错、36 黄金全绿

- [ ] **步骤 9：Commit**

```bash
git add vectcut/core/util.py tests/core/test_util.py vectcut/engine/material_factory.py vectcut/features/draft/_save_engine.py vectcut/features/audio/service.py vectcut/features/text/service.py vectcut/features/image/service.py vectcut/features/video/service.py
git commit -m "refactor(core): 阶段5 任务1 迁移 util.py → vectcut/core/util.py，6 处 import 切换"
```

---

### 任务 2：迁移 `oss.py` / `downloader.py` / `save_task_cache.py` → `vectcut/core/`

三模块均小且仅各 1–5 处引用，按任务 1 范式批量迁移。`save_task_cache.py` 改名为 `task_cache.py`（去 save_ 前缀，统一命名）。

**文件：**
- 创建：`vectcut/core/oss.py`、`vectcut/core/downloader.py`、`vectcut/core/task_cache.py`
- 修改：`vectcut/features/draft/_save_engine.py:20-22,29`、`vectcut/features/draft/service.py:20`
- 删除：`oss.py`、`downloader.py`、`save_task_cache.py`

- [ ] **步骤 1：创建三个新模块（逐字复制根文件内容）**

- `vectcut/core/oss.py` ← 复制根 `oss.py` 全部内容（头加 docstring "迁自根 oss.py（阶段5）"）
- `vectcut/core/downloader.py` ← 复制根 `downloader.py` 全部内容
- `vectcut/core/task_cache.py` ← 复制根 `save_task_cache.py` 全部内容（模块名改 `task_cache`，函数体不动）

- [ ] **步骤 2：编写迁移冒烟测试 `tests/core/test_task_cache.py`**

```python
"""vectcut.core.task_cache 行为测试（迁自 save_task_cache.py）。"""
from vectcut.core.task_cache import create_task, get_task_status, update_task_field


def test_task_lifecycle():
    create_task("t1")
    update_task_field("t1", "status", "processing")
    assert get_task_status("t1")["status"] == "processing"
```

- [ ] **步骤 3：运行测试验证通过**

运行：`pytest tests/core/test_task_cache.py -q`
预期：PASS（如 FAIL，检查 `vectcut/core/task_cache.py` 是否完整复制）

- [ ] **步骤 4：改 vectcut 内 import**

`vectcut/features/draft/_save_engine.py`：

```python
# 旧（20-22, 29 行）
from downloader import download_file  # 阶段5再迁 downloader
import save_task_cache  # noqa: F401  纯内存 LRU，测试经 _save_engine.save_task_cache 访问
from save_task_cache import (  # 单函数别名
    get_task_status,
    update_task_field,
    update_task_fields,
    update_tasks_cache,
)
from util import build_draft_asset_path, zip_draft
from oss import upload_to_oss

# 新
from vectcut.core.downloader import download_file
from vectcut.core import task_cache  # noqa: F401  测试经 _save_engine.task_cache 访问
from vectcut.core.task_cache import (
    get_task_status,
    update_task_field,
    update_task_fields,
    update_tasks_cache,
)
from vectcut.core.util import build_draft_asset_path, zip_draft  # 任务1已改，此处确认
from vectcut.core.oss import upload_to_oss
```

`vectcut/features/draft/service.py:20`：

```python
# 旧
from save_task_cache import get_task_status
# 新
from vectcut.core.task_cache import get_task_status
```

- [ ] **步骤 5：确认根三模块已无 vectcut/tests 引用**

运行：`grep -rln --include="*.py" "from oss import\|import oss\|from downloader import\|import downloader\|from save_task_cache import\|import save_task_cache" vectcut tests run_http.py run_mcp.py | grep -v __pycache__`
预期：空输出

- [ ] **步骤 6：删根三模块**

```bash
git rm oss.py downloader.py save_task_cache.py
```

- [ ] **步骤 7：全量验证**

运行：`pytest -q && flake8 vectcut tests run_http.py run_mcp.py && pytest tests/golden -q`
预期：全绿、无 lint 错、36 黄金全绿

- [ ] **步骤 8：Commit**

```bash
git add vectcut/core/oss.py vectcut/core/downloader.py vectcut/core/task_cache.py tests/core/test_task_cache.py vectcut/features/draft/_save_engine.py vectcut/features/draft/service.py
git commit -m "refactor(core): 阶段5 任务2 迁移 oss/downloader/save_task_cache → vectcut/core/，task_cache 改名"
```

---

### 任务 3：删除零引用的旧业务文件

8 个 `add_*_impl`/`add_*_track` 与 `get_duration_impl.py` 在阶段 2–3 迁移后已零 vectcut/tests 引用（阶段 0 基线已确认：仅互相引用）。

**文件（删除）：**
- `add_audio_track.py` `add_video_track.py` `add_text_impl.py` `add_subtitle_impl.py` `add_image_impl.py` `add_effect_impl.py` `add_sticker_impl.py` `add_video_keyframe_impl.py` `get_duration_impl.py`

- [ ] **步骤 1：确认 9 文件零 vectcut/tests 引用**

运行：
```bash
for f in add_audio_track add_video_track add_text_impl add_subtitle_impl add_image_impl add_effect_impl add_sticker_impl add_video_keyframe_impl get_duration_impl; do
  echo "$f: $(grep -rln --include='*.py' \"from $f import\|import $f\" vectcut tests run_http.py run_mcp.py 2>/dev/null | grep -v __pycache__ | wc -l)"
done
```
预期：每行 `: 0`

若任一非 0，先改引用到 vectcut 对应 service，再继续。

- [ ] **步骤 2：删 9 文件**

```bash
git rm add_audio_track.py add_video_track.py add_text_impl.py add_subtitle_impl.py add_image_impl.py add_effect_impl.py add_sticker_impl.py add_video_keyframe_impl.py get_duration_impl.py
```

- [ ] **步骤 3：全量验证**

运行：`pytest -q && flake8 vectcut tests run_http.py run_mcp.py && pytest tests/golden -q`
预期：全绿、无 lint 错、36 黄金全绿

- [ ] **步骤 4：Commit**

```bash
git commit -m "refactor: 阶段5 任务3 删 9 个零引用旧业务文件（add_*_impl/track + get_duration_impl）"
```

---

### 任务 4：删除 `save_draft_impl.py` 与 `create_draft.py`

二者均已被 vectcut 取代，仅脚本/测试残留引用。`create_draft.py` 已是垫片（转发 `draft_store.get_or_create_draft`），`save_draft_impl.py` 仍是旧实现但已被 `_save_engine` 取代。

**文件：**
- 修改：`gen_local_draft.py`（移 `scripts/` 前先改 import）、`tests/core/test_draft_store.py`、`tests/test_draft_profiles.py`、`tests/server/mcp/test_runtime.py`
- 删除：`save_draft_impl.py`、`create_draft.py`、`draft_cache.py`（垫片，引擎不直接 import，可删）

- [ ] **步骤 1：确认引用方**

运行：`grep -rln --include="*.py" "from save_draft_impl\|import save_draft_impl\|from create_draft\|import create_draft\|from draft_cache\|import draft_cache" . | grep -v __pycache__`
预期仅：`gen_local_draft.py` `tests/core/test_draft_store.py` `tests/test_draft_profiles.py` `tests/server/mcp/test_runtime.py` `save_draft_impl.py`（自身）

- [ ] **步骤 2：改 `tests/core/test_draft_store.py` 的 `create_draft` / `draft_cache` 引用**

把 `from create_draft import ...` 改为 `from vectcut.core.draft_store import get_or_create_draft`（注意签名顺序：旧 `create_draft.create_draft` 返回 `(script, draft_id)`，`draft_store.get_or_create_draft` 返回 `(draft_id, script)`——测试若用 `create_draft.create_draft`，调用处交换返回元组顺序）。

把 `from draft_cache import ...` 改为 `from vectcut.core.draft_store import DRAFT_CACHE, update_cache`。

- [ ] **步骤 3：改 `tests/test_draft_profiles.py` 的 `draft_cache` / `save_draft_impl` 引用**

`from draft_cache import DRAFT_CACHE` → `from vectcut.core.draft_store import DRAFT_CACHE`
`from save_draft_impl import ...` → 改为 `from vectcut.features.draft._save_engine import ...`（对应函数已在 _save_engine）

- [ ] **步骤 4：改 `tests/server/mcp/test_runtime.py` 的 `create_draft` 引用**

同步骤 2，改为 `vectcut.core.draft_store.get_or_create_draft`，注意返回元组顺序。

- [ ] **步骤 5：改 `gen_local_draft.py` 的 `save_draft_impl` 引用**

`from save_draft_impl import ...` → `from vectcut.features.draft._save_engine import ...`

（`gen_local_draft.py` 本身会在任务 6 移到 `scripts/`，此处只改 import 不挪位置。）

- [ ] **步骤 6：全量验证（此时旧文件还在，确认改 import 后仍绿）**

运行：`pytest -q && flake8 vectcut tests run_http.py run_mcp.py`
预期：全绿、无 lint 错

- [ ] **步骤 7：删 3 文件**

```bash
git rm save_draft_impl.py create_draft.py draft_cache.py
```

- [ ] **步骤 8：确认零残留 + 黄金绿**

运行：`grep -rln --include="*.py" "save_draft_impl\|create_draft\|draft_cache" vectcut tests run_http.py run_mcp.py | grep -v __pycache__ | grep -v vectcut.core.draft_store`
预期：空（`draft_store` 内部对 `draft_cache` 字样的注释可保留）

运行：`pytest -q && pytest tests/golden -q`
预期：全绿、36 黄金全绿

- [ ] **步骤 9：Commit**

```bash
git add tests/core/test_draft_store.py tests/test_draft_profiles.py tests/server/mcp/test_runtime.py gen_local_draft.py
git commit -m "refactor: 阶段5 任务4 删 save_draft_impl/create_draft/draft_cache，测试与脚本 import 切换到 vectcut"
```

---

### 任务 5：删除 7 个 `flask_router.py`

阶段 4 已用 FastAPI `router.py` 取代所有 Flask Blueprint，`vectcut/server/http/__init__.py` 只挂载 FastAPI router，flask_router 零引用。

**文件（删除）：**
- `vectcut/features/draft/flask_router.py` `vectcut/features/video/flask_router.py` `vectcut/features/audio/flask_router.py` `vectcut/features/text/flask_router.py` `vectcut/features/image/flask_router.py` `vectcut/features/effect/flask_router.py` `vectcut/features/metadata/flask_router.py`

- [ ] **步骤 1：确认 flask_router 零挂载零引用**

运行：`grep -rln --include="*.py" "flask_router" vectcut tests run_http.py run_mcp.py | grep -v __pycache__`
预期：仅各 `router.py` 文件 docstring 注释里提到"flask_router.py"（保真说明），无实际 import。

若出现 `from .flask_router import` 或 `import flask_router`，先解除引用。

- [ ] **步骤 2：删 7 文件**

```bash
git rm vectcut/features/draft/flask_router.py vectcut/features/video/flask_router.py vectcut/features/audio/flask_router.py vectcut/features/text/flask_router.py vectcut/features/image/flask_router.py vectcut/features/effect/flask_router.py vectcut/features/metadata/flask_router.py
```

- [ ] **步骤 3：清理各 `router.py` docstring 里对 flask_router 的提述（可选，保 lint 干净）**

各 `vectcut/features/*/router.py` 顶部 docstring 中"保真：响应体与 flask_router.py 逐字一致"改为"保真：响应体 {success,output,error} 外壳与历史 Flask 版逐字一致"。非硬性，跳过亦可。

- [ ] **步骤 4：全量验证**

运行：`pytest -q && flake8 vectcut tests run_http.py run_mcp.py && pytest tests/golden -q`
预期：全绿、无 lint 错、36 黄金全绿

- [ ] **步骤 5：Commit**

```bash
git commit -m "refactor(server): 阶段5 任务5 删 7 个 flask_router.py，Flask Blueprint 退场"
```

---

### 任务 6：脚本与资源归位

按规格 §6.1 移动一次性/调试脚本与资源到专属目录。

**文件（移动）：**
- `jy_decrypt.py` → `scripts/jy_decrypt.py`
- `gen_local_draft.py` → `scripts/gen_local_draft.py`
- `test_mcp_client.py` → `tests/test_mcp_client.py`
- `rest_client_test.http` → `examples/rest_client_test.http`
- `shuangnan.plain.json` → `tests/golden/shuangnan.plain.json`（黄金基线参考，归入 golden）
- `pattern/` 三文件 → `examples/`（`001-words.py` `002-relationship.py` `001-words-coze.md` `README.md`）

- [ ] **步骤 1：建目录 + git mv**

```bash
mkdir -p scripts examples
git mv jy_decrypt.py scripts/jy_decrypt.py
git mv gen_local_draft.py scripts/gen_local_draft.py
git mv test_mcp_client.py tests/test_mcp_client.py
git mv rest_client_test.http examples/rest_client_test.http
git mv shuangnan.plain.json tests/golden/shuangnan.plain.json
git mv pattern/001-words.py examples/001-words.py
git mv pattern/002-relationship.py examples/002-relationship.py
git mv pattern/001-words-coze.md examples/001-words-coze.md
git mv pattern/README.md examples/pattern-readme.md
rmdir pattern
```

- [ ] **步骤 2：修正 `scripts/gen_local_draft.py` 内部对根模块的 import**

任务 4 已把它的 `save_draft_impl` import 改到 `vectcut.features.draft._save_engine`。移到 `scripts/` 后，若它还 import 了根目录其他模块（`create_draft` 等已在任务 4 删），逐一改到 `vectcut.core.*`。运行：

```bash
grep -n "from .* import\|^import" scripts/gen_local_draft.py
```

把所有根目录裸 import 改为 `vectcut.*`。若 `scripts/` 不在 sys.path，`tests/conftest.py` 已注入 PROJECT_ROOT，`scripts/` 下的脚本作为独立脚本运行时需在自身头部加：

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```

- [ ] **步骤 3：修正 `tests/test_mcp_client.py` 与 `examples/001-words.py` 的 `example` import**

`examples/example_capcut_effect.py` 和 `examples/001-words.py` 此前 `import example`（根 example.py，任务 7 会拆）。本步骤先确认它们能 import 到——任务 7 拆分后再改。若移动后 `import example` 失败，先在 `examples/001-words.py` 头部加 PROJECT_ROOT 到 sys.path（同步骤 2 模式）。

- [ ] **步骤 4：全量验证**

运行：`pytest -q && flake8 vectcut tests run_http.py run_mcp.py && pytest tests/golden -q`
预期：全绿、无 lint 错、36 黄金全绿

- [ ] **步骤 5：Commit**

```bash
git add -A
git commit -m "chore: 阶段5 任务6 脚本/资源归位（scripts/ examples/ tests/golden/），pattern/ 并入 examples/"
```

---

### 任务 7：拆分 `example.py`（2377 行）→ `examples/` 按功能多脚本

`example.py` 是面向 HTTP API 的客户端示例集合，被 `examples/example_capcut_effect.py` 与 `examples/001-words.py` import。按剪辑功能域切分，公共 `make_request` 提到 `_client.py`。

**拆分映射表（源行号 → 目标文件）：**

| 源行号 | 内容 | 目标文件 |
|--------|------|----------|
| 1–43 | docstring + imports + `make_request` | `examples/_client.py` |
| 45–63 | `add_audio_track` | `examples/audio_demo.py` |
| 65–165 | `add_text_impl` | `examples/text_demo.py` |
| 166–203 | `add_image_impl` | `examples/image_demo.py` |
| 204–226 | `generate_image_impl` | `examples/image_demo.py` |
| 227–254 | `add_sticker_impl` | `examples/sticker_demo.py` |
| 255–285 | `add_video_keyframe_impl` | `examples/video_demo.py` |
| 286–330 | `add_video_impl` | `examples/video_demo.py` |
| 331–350 | `add_effect` | `examples/effect_demo.py` |
| 352–426 | `test_effect_01/02` | `examples/effect_demo.py` |
| 427–846 | `test_text/02/03` | `examples/text_demo.py` |
| 847–994 | `test_image01–05` | `examples/image_demo.py` |
| 995–1117 | `test_mask_01/02` | `examples/effect_demo.py` |
| 1118–1243 | `test_audio01–04` | `examples/audio_demo.py` |
| 1244–1281 | `add_subtitle_impl` | `examples/text_demo.py` |
| 1282–1289 | `save_draft_impl` | `examples/draft_demo.py` |
| 1290–1297 | `query_script_impl` | `examples/draft_demo.py` |
| 1298–1377 | `query_draft_status_impl` + `_polling` | `examples/draft_demo.py` |
| 1378–1411 | `test_subtitle` | `examples/text_demo.py` |
| 1412–1562 | `test01` | `examples/video_demo.py` |
| 1563–1713 | `test02` | `examples/video_demo.py` |
| 1714–1925 | `test_video_track01–05` + `test_keyframe` | `examples/video_demo.py` |
| 1926–1986 | `test_keyframe_02` | `examples/video_demo.py` |
| 1987–2042 | `test_subtitle_01/02` | `examples/text_demo.py` |
| 2043–2179 | `test_video_01/02` | `examples/video_demo.py` |
| 2180–2342 | `test_stiker_01–03` + `test_transition_01/02` | `examples/sticker_demo.py`（transition 可并入 `effect_demo.py`） |
| 2343–2377 | `if __name__ == "__main__"` | 拆到各 demo 末尾或新建 `examples/run_all.py` |

**文件：**
- 创建：`examples/_client.py` `examples/audio_demo.py` `examples/text_demo.py` `examples/image_demo.py` `examples/sticker_demo.py` `examples/video_demo.py` `examples/effect_demo.py` `examples/draft_demo.py`
- 删除：`example.py`

- [ ] **步骤 1：建 `examples/_client.py`（公共 make_request + imports）**

把 `example.py` 1–43 行（docstring + imports + `make_request` 函数）复制到 `examples/_client.py`。在文件头加：

```python
"""HTTP 客户端公共工具（迁自 example.py 头部，阶段5 拆分）。"""
import os
import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
```

各 demo 文件首行加 `from _client import make_request`（依赖 `examples/` 在 sys.path——通过各 demo 头部同款 PROJECT_ROOT 注入保证）。

- [ ] **步骤 2：按映射表逐文件创建 demo 脚本**

对每个目标文件：
1. 头部加 PROJECT_ROOT sys.path 注入 + `from _client import make_request`（除 `_client.py` 自身）
2. 按映射表把 `example.py` 对应行号区间的函数逐字复制进来
3. 函数体不动（它们都调 `make_request`，不依赖 example.py 内其他函数）

注：`add_*_impl` 这些函数名与已删的根模块同名但互不依赖（它们是 HTTP 客户端封装，调 `make_request`），保留原名不冲突。

- [ ] **步骤 3：修正 `examples/example_capcut_effect.py` 与 `examples/001-words.py` 的 `import example`**

`grep -rn "import example\|from example" examples/`

把 `import example` 改为按需导入对应 demo 模块，例如 `from video_demo import add_video_impl`。若无明确调用，可保留 `import video_demo, text_demo, audio_demo, image_demo, effect_demo, sticker_demo, draft_demo` 兜底。

- [ ] **步骤 4：删 `example.py`**

```bash
git rm example.py
```

- [ ] **步骤 5：冒烟验证（examples 不参与 pytest，只验可 import）**

运行：
```bash
python -c "import sys; sys.path.insert(0,'examples'); import _client, audio_demo, text_demo, image_demo, sticker_demo, video_demo, effect_demo, draft_demo; print('ok')"
```
预期：`ok`（若有 SyntaxError/ImportError，按报错修对应 demo 的复制区间边界）

- [ ] **步骤 6：全量回归验证**

运行：`pytest -q && flake8 vectcut tests run_http.py run_mcp.py && pytest tests/golden -q`
预期：全绿、无 lint 错、36 黄金全绿

- [ ] **步骤 7：Commit**

```bash
git add examples/ example.py
git commit -m "docs(examples): 阶段5 任务7 拆 example.py(2377行) → examples/ 8 个按功能切分的 demo 脚本"
```

---

### 任务 8：`settings/` 死代码瘦身

任务 1–4 完成后，旧业务模块全删，`settings/local.py` 转发的 9 个常量中仅 `IS_CAPCUT_ENV` 仍被引擎两处 import（`pyJianYingDraft/video_segment.py:14`、`script_file.py:22`）。其余 8 个（DRAFT_PROFILE/DRAFT_DOMAIN/PREVIEW_ROUTER/IS_UPLOAD_DRAFT/DRAFT_FOLDER/PORT/OSS_CONFIG/MP4_OSS_CONFIG）无引用。

**文件：**
- 修改：`settings/__init__.py`、`settings/local.py`

- [ ] **步骤 1：确认除 IS_CAPCUT_ENV 外其余 8 常量零引用**

运行：`grep -rn --include="*.py" "DRAFT_PROFILE\|DRAFT_DOMAIN\|PREVIEW_ROUTER\|IS_UPLOAD_DRAFT\|DRAFT_FOLDER\|OSS_CONFIG\|MP4_OSS_CONFIG" vectcut tests run_http.py run_mcp.py pyJianYingDraft | grep -v __pycache__ | grep -v "settings/"`
预期：空输出（`settings/` 自身除外）

- [ ] **步骤 2：瘦身 `settings/local.py`**

全文替换为：

```python
"""配置垫片：仅供引擎两处 `from settings.local import IS_CAPCUT_ENV`
（pyJianYingDraft/video_segment.py:14、script_file.py:22）。

阶段5 清理后，应用层全部经 vectcut.core.config 读配置，本垫片仅保留引擎
硬依赖的 IS_CAPCUT_ENV。其余历史常量（DRAFT_PROFILE/PORT/OSS_CONFIG 等）
随旧业务文件删除已无引用，不再转发。

依赖方向单一：引擎 → settings 垫片 → vectcut.core.config（真源）。
引擎日后若升级去掉这两处 import，本垫片即可彻底删除（见 docs 标注）。
"""
from vectcut.core.config import load_config

IS_CAPCUT_ENV = load_config(None).is_capcut_env

__all__ = ["IS_CAPCUT_ENV"]
```

- [ ] **步骤 3：瘦身 `settings/__init__.py`**

全文替换为：

```python
"""settings 包垫片：仅供 pyJianYingDraft 引擎 `from settings import IS_CAPCUT_ENV`
（video_segment.py:14 / script_file.py:22）继续工作。

依赖方向单一：引擎 → settings 垫片 → vectcut.core.config（真源）。
"""
from .local import IS_CAPCUT_ENV  # noqa: F401

__all__ = ["IS_CAPCUT_ENV"]
```

- [ ] **步骤 4：全量验证（含引擎 import 仍通）**

运行：`python -c "from pyJianYingDraft import video_segment, script_file; from settings import IS_CAPCUT_ENV; print('engine import ok', IS_CAPCUT_ENV)"`
预期：`engine import ok <bool>`

运行：`pytest -q && flake8 vectcut tests run_http.py run_mcp.py && pytest tests/golden -q`
预期：全绿、无 lint 错、36 黄金全绿

- [ ] **步骤 5：Commit**

```bash
git add settings/__init__.py settings/local.py
git commit -m "refactor(settings): 阶段5 任务8 settings 垫片瘦身至仅 IS_CAPCUT_ENV，删 8 个无引用常量"
```

---

### 任务 9：项目身份统一

规格 §6.2：pyproject name 统一为 vectcut，URL 修正为 `sun-guannan/VectCutAPI`，入口脚本 `run_http.py`/`run_mcp.py`，mcp_config command 同步。

**文件：**
- 修改：`pyproject.toml`、`mcp_config.json`

- [ ] **步骤 1：改 `pyproject.toml`**

```toml
[project]
name = "vectcut-api"
version = "1.0.0"
description = "VectCut — open source video editing API tool with MCP support"
```

```toml
[project.urls]
Homepage = "https://github.com/sun-guannan/VectCutAPI"
Repository = "https://github.com/sun-guannan/VectCutAPI.git"
Issues = "https://github.com/sun-guannan/VectCutAPI/issues"
```

- [ ] **步骤 2：改 `mcp_config.json`**

```json
{
  "mcpServers": {
    "vectcut": {
      "command": "python",
      "args": ["run_mcp.py"],
      "cwd": ".",
      "env": {
        "PYTHONPATH": "."
      }
    }
  }
}
```

（注：原 `python3.10` + 绝对 cwd 改为 `python` + 相对 `.`，便于跨机部署；用户按本机环境调整 command。）

- [ ] **步骤 3：扫描 README/docs 残留 CapCutAPI 命名**

运行：`grep -rn "CapCutAPI\|capcut-api\|ashreo" README.md README-zh.md docs/ 2>/dev/null`
对每处判断：品牌名 VectCut 已统一（README 头已是 VectCut）；历史仓库引用 `ashreo/CapCutAPI` 改为 `sun-guannan/VectCutAPI`；`CapCutAPI` 作为旧称在文档里提一句即可，代码层不保留别名。

- [ ] **步骤 4：验证 MCP runtime 仍可用**

运行：`python -c "from vectcut.server.mcp.runtime import run_server; print('mcp runtime import ok')"`
预期：`mcp runtime import ok`

运行：`pytest tests/server/mcp -q`
预期：全绿

- [ ] **步骤 5：全量验证**

运行：`pytest -q && flake8 vectcut tests run_http.py run_mcp.py && pytest tests/golden -q`
预期：全绿、36 黄金全绿

- [ ] **步骤 6：Commit**

```bash
git add pyproject.toml mcp_config.json README.md README-zh.md docs/
git commit -m "chore: 阶段5 任务9 项目身份统一——pyproject name=vectcut-api、URL 修正、mcp_config command=run_mcp.py"
```

---

### 任务 10：模板资源 `importlib.resources` 改造（可选，低风险）

规格 §6.1：template 引用改为相对 `vectcut/` 包用 `importlib.resources` 定位。当前 `_save_engine.py` 用 `os.path` 拼项目根 + `template_dir`（见 `_save_engine.py:100-116`）。

**风险提示：** 模板目录 `template/` `template_jianying/` `template_jianying_10_2/` 在项目根，不在 `vectcut/` 包内。若不改包结构，`importlib.resources` 收益有限。**本任务标记为可选**——若不动模板目录位置，保持现有 `os.path` 方式即可（已工作，黄金绿）。

**若执行（把 template 纳入包资源）：**

- [ ] **步骤 1：在 `pyproject.toml` 声明包数据**

```toml
[tool.setuptools.package-data]
vectcut = ["../template/**", "../template_jianying/**", "../template_jianying_10_2/**"]
```

- [ ] **步骤 2：`_save_engine.py` template_dir 解析改 importlib.resources**

把 `_save_engine.py:113-116` 的 `template_source_dir = os.path.join(project_root, template_dir)` 改为通过 `importlib.resources` 定位，并跑黄金测试确认 draft 输出不变。

- [ ] **步骤 3：全量验证 + Commit**

运行：`pytest -q && pytest tests/golden -q`
预期：36 黄金全绿（draft 二进制/文本逐字一致）

```bash
git commit -am "refactor(engine): 阶段5 任务10 模板资源 importlib.resources 定位（可选）"
```

**若不执行：** 在 `docs/superpowers/plans/2026-07-03-phase5-cleanup-identity-consolidation.md` 末尾标注"任务10 暂缓，template 仍走 os.path，待引擎升级时一并处理"。

> **执行决定（2026-07-03）：任务10 暂缓。** 模板目录 `template/` `template_jianying/` `template_jianying_10_2/` 仍位于项目根而非 `vectcut/` 包内，不改包结构则 `importlib.resources` 收益有限且会引入 `package-data` 跨包上跳的脆弱配置。当前 `_save_engine.py` 的 `os.path` 拼接已稳定工作，36 黄金全绿。待 pyJianYingDraft 引擎升级、模板目录一并纳入包结构时再统一改造。

---

### 任务 11：最终验收 + release 标注

- [ ] **步骤 1：全量测试 + 黄金 + lint 三连**

运行：`pytest -q && flake8 vectcut tests run_http.py run_mcp.py && pytest tests/golden -q`
预期：全绿、无 lint 错、36 黄金全绿

- [ ] **步骤 2：根目录残留 .py 审计**

运行：`ls *.py`
预期仅：`run_http.py` `run_mcp.py`（+ `vectcut-skill/` 子目录内脚本，不计）

- [ ] **步骤 3：根目录结构确认**

运行：`ls -1`
预期：`CLAUDE.md` `README.md` `README-zh.md` `config.json` `mcp_config.json` `pyproject.toml` `run_http.py` `run_mcp.py` + 目录 `vectcut/` `pyJianYingDraft/` `settings/` `scripts/` `examples/` `tests/` `template*/` `docs/` `vectcut-skill/` + `.git*` 等

- [ ] **步骤 4：确认引擎循环依赖仅剩 settings 垫片（draft_profiles 垫片保留）**

运行：`grep -rn "from settings\|from draft_profiles\|from draft_cache" pyJianYingDraft | grep -v __pycache__`
预期：`video_segment.py: from settings import IS_CAPCUT_ENV`、`script_file.py: from settings.local import IS_CAPCUT_ENV` + `from draft_profiles import get_draft_profile`、`draft_folder.py: from draft_profiles import get_draft_profile`。这些是硬约束，垫片已通，**符合预期，不算遗留**。

- [ ] **步骤 5：Commit 收尾 + 打 tag**

```bash
git commit --allow-empty -m "chore: 阶段5 清理收尾完成——根目录瘦身、身份统一、36 黄金全绿

规格 docs/superpowers/specs/2026-07-02-architecture-refactor-design.md 阶段5 全部完成。
架构重排阶段 0–5 收官。"
git tag phase5-cleanup-done
```

- [ ] **步骤 6：更新规格文档状态**

编辑 `docs/superpowers/specs/2026-07-02-architecture-refactor-design.md` 顶部"状态：草案"改为"状态：已实现（阶段 0–5 全部完成，2026-07-03）"。

```bash
git add docs/superpowers/specs/2026-07-02-architecture-refactor-design.md
git commit -m "docs: 架构重排规格状态更新为已实现"
```

---

## 自检

**1. 规格覆盖度（对照规格 §5.2 / §6 / §8 阶段5）：**

| 规格需求 | 对应任务 |
|----------|----------|
| §5.2 settings 降级垫片、删死代码 | 任务 8 |
| §5.2 is_capcut_env 标记废弃 | 任务 8（垫片仅留 IS_CAPCUT_ENV，过渡期保留读取） |
| §6.1 template 引用改 importlib.resources | 任务 10（可选） |
| §6.1 pattern 并入 examples | 任务 6 |
| §6.1 example.py 拆分 | 任务 7 |
| §6.1 jy_decrypt/gen_local_draft 移 scripts | 任务 6 |
| §6.1 rest_client_test.http 移 examples | 任务 6 |
| §6.1 test_mcp_client.py 并入 tests | 任务 6 |
| §6.2 pyproject name 统一 | 任务 9 |
| §6.2 入口脚本 run_http/run_mcp | 任务 9（mcp_config 同步） |
| §6.2 README 品牌统一 | 任务 9 |
| §8 删旧文件 | 任务 3、4、5 |
| §8 删 settings 死代码 | 任务 8 |
| §8 拆 example.py | 任务 7 |
| §8 身份统一 | 任务 9 |
| §8 文档更新 | 任务 11 步骤 6 |

**遗漏：无。** 任务 1–2（迁移 util/oss/downloader/save_task_cache）虽不在规格 §6 显式列出，但属 §8"删旧文件"的前置——这些模块被 vectcut 引用，必须先迁后删，是规格"根目录只留入口脚本与配置，业务全进 vectcut/ 包"（§3.1 关键决策）的落实。

**2. 占位符扫描：** 无"TODO/待定/类似任务N"。任务 7 example.py 拆分用行号映射表 + 逐字复制策略，非占位符。任务 10 明确标"可选"并给出两种路径（执行/暂缓），非含糊。

**3. 类型一致性：** `vectcut.core.util` / `vectcut.core.oss` / `vectcut.core.downloader` / `vectcut.core.task_cache` 命名在任务 1–2 定义，任务 4、8 引用一致。`task_cache` 改名（去 save_ 前缀）在任务 2 步骤 1、4 与任务 4 步骤 2–3 引用一致。`get_or_create_draft` 返回 `(draft_id, script)` 顺序在任务 4 步骤 2、4 均提示测试需交换元组，一致。`settings` 仅留 `IS_CAPCUT_ENV` 在任务 8 与任务 11 步骤 4 审计一致。

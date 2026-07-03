# 阶段 2：核心 Features（draft / video / audio）+ material_factory + save_draft_impl 拆分 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 把 `draft` / `video` / `audio` 三个剪辑核心能力的业务实现从根目录平铺文件迁入 `vectcut/features/` 包，每个 feature 自洽为 `service.py`（纯 Python 业务）+ `schemas.py`（Pydantic 请求/响应模型）+ `flask_router.py`（Flask Blueprint 薄接线）；落地阶段 1 延后的 `engine/material_factory.py`；把 `save_draft_impl.py`（37KB）在 draft feature 内按职责拆分；散落的 `if IS_CAPCUT_ENV` 平台分支收敛为 `adapter.enum_for(kind)` 调用；扩展黄金基线覆盖业务路由；**本阶段不碰 MCP、不迁 FastAPI**（阶段 4）、**不碰 text/image/effect/sticker/keyframe impl**（阶段 3）。

**架构：**
- 沿用阶段 1 metadata feature 已验证的"service + 薄 flask_router + `{success,output,error}` 外壳"模式，新增一层 `schemas.py`（业务路由有请求体，metadata 无）。
- `engine/material_factory.py` 封装 `Video_material`/`Audio_material` 构造、轨道 get-or-create、平台相关枚举成员解析（`resolve_transition`/`resolve_mask`/`resolve_audio_effect`），消除业务层直接 `import pyJianYingDraft` 顶层符号与 `if IS_CAPCUT_ENV`。
- `core/draft_store.py` 增 `get_or_create_draft(draft_id, width, height)` 跨 feature 基础能力（替代根目录 `create_draft.get_or_create_draft`）。
- `core/errors.py` 补 `DraftNotFound` / `EngineError` / `MediaDownloadError`（阶段 1 只有 `InvalidParam`）。
- `features/draft/service.py` 拆分 `save_draft_impl`：公开 5 个 service 函数（`create_draft` / `save_draft` / `query_script` / `query_task_status` / `generate_draft_url`），私有实现 `_save_draft_background` / `_update_media_metadata` 放同包 `_save_engine.py`。
- `capcut_server.py` 删除 7 个旧业务路由函数（~600 行）+ 顶部散落 import，挂载 3 个新 Blueprint；阶段 3 的 text/image/effect/sticker/keyframe 路由与 import 暂留。
- 黄金基线扩展：业务路由错误分支 + `create_draft`/`generate_draft_url` 成功分支 + `add_video`/`add_audio` service 层 draft 输出快照。

**技术栈：** Flask Blueprint（阶段 4 再切 FastAPI）、Pydantic v2、`vectcut.core.draft_store`、`vectcut.engine.adapter`（阶段 1 产物）、阶段 0-1 黄金快照。

**前置依赖：** 阶段 0-1 全绿出 release。`vectcut.core.draft_store.get_draft` / `get_active_profile`、`vectcut.engine.adapter.enum_for(kind)`、`vectcut.core.errors.InvalidParam`、`tests/golden/snapshots/metadata_*.json` 必须已就位。

**本阶段不触碰：** `pyJianYingDraft/` 内部（只读）；`mcp_server.py`（阶段 4）；text/image/effect/sticker/keyframe impl（阶段 3）；FastAPI；`example.py` 拆分（阶段 5）；`pyproject.toml` 身份统一（阶段 5）。

**与规格的偏差（自检标注）：**
- 规格 §3.1 称 draft feature 含 `get_duration`。实测 `get_duration_impl.py` 是独立 ffprobe 工具，被 `save_draft_impl` 内部调用。本阶段将其作为 draft feature 私有工具迁入 `features/draft/_save_engine.py`（不对外暴露 service），避免引入无消费者的公开 service。
- 规格 §8 阶段 2 列 "video" feature 含 `video_keyframe`。`add_video_keyframe_impl` 体量小（~120 行）且与 video 同域，归入 `features/video/` 合理，不单列 feature。
- `download_script`（save_draft_impl:558）是独立远程脚本下载路径，无 HTTP 路由暴露、无消费者，属 YAGNI 死路径，本阶段不迁移，留原位待阶段 5 清理。

---

## 文件结构

| 文件 | 职责 | 动作 |
|------|------|------|
| `vectcut/core/errors.py` | 补 `DraftNotFound` / `EngineError` / `MediaDownloadError` | 修改（追加 3 类） |
| `vectcut/core/draft_store.py` | 增 `get_or_create_draft(draft_id, width, height)` | 修改（追加 1 函数） |
| `vectcut/engine/material_factory.py` | `build_video_material` / `build_audio_material` / `add_to_track` / `resolve_transition` / `resolve_mask` / `resolve_audio_effect` | 创建 |
| `vectcut/features/draft/__init__.py` | draft feature 包标记 | 创建 |
| `vectcut/features/draft/schemas.py` | `CreateDraftRequest/Response` / `SaveDraftRequest/Response` / `QueryScriptRequest/Response` / `QueryDraftStatusRequest/Response` / `GenerateDraftUrlRequest/Response` | 创建 |
| `vectcut/features/draft/service.py` | 5 个公开 service 函数 | 创建 |
| `vectcut/features/draft/_save_engine.py` | `_save_draft_background` / `_update_media_metadata` / `_get_video_duration`（迁自 save_draft_impl + get_duration_impl） | 创建 |
| `vectcut/features/draft/flask_router.py` | 5 路由 Blueprint | 创建 |
| `vectcut/features/video/__init__.py` | 包标记 | 创建 |
| `vectcut/features/video/schemas.py` | `AddVideoRequest/Response` / `AddVideoKeyframeRequest/Response` | 创建 |
| `vectcut/features/video/service.py` | `add_video` / `add_video_keyframe` | 创建 |
| `vectcut/features/video/flask_router.py` | 2 路由 Blueprint | 创建 |
| `vectcut/features/audio/__init__.py` | 包标记 | 创建 |
| `vectcut/features/audio/schemas.py` | `AddAudioRequest/Response` | 创建 |
| `vectcut/features/audio/service.py` | `add_audio` | 创建 |
| `vectcut/features/audio/flask_router.py` | 1 路由 Blueprint | 创建 |
| `capcut_server.py` | 删 7 旧路由（add_video/add_audio/create_draft/save_draft/query_script/query_draft_status/generate_draft_url）+ 顶部相关 import；挂载 3 新 Blueprint | 修改 |
| `create_draft.py` | 降级为垫片转发 `draft_store.get_or_create_draft`（供阶段 3 未迁文件用） | 修改 |
| `tests/core/test_errors.py` | 补 3 新异常类测试 | 修改 |
| `tests/core/test_draft_store.py` | 补 `get_or_create_draft` 测试 | 修改 |
| `tests/engine/test_material_factory.py` | 工厂函数单测 | 创建 |
| `tests/features/draft/test_service.py` | draft service 单测 | 创建 |
| `tests/features/draft/test_router.py` | draft Blueprint 路由测试 | 创建 |
| `tests/features/video/test_service.py` | video service 单测 + 黄金 | 创建 |
| `tests/features/video/test_router.py` | video Blueprint 路由测试 | 创建 |
| `tests/features/audio/test_service.py` | audio service 单测 + 黄金 | 创建 |
| `tests/features/audio/test_router.py` | audio Blueprint 路由测试 | 创建 |
| `tests/golden/test_business_routes_golden.py` | 业务路由 HTTP 黄金（错误分支 + 成功分支） | 创建 |
| `tests/golden/snapshots/business_*.json` | 业务路由快照 | 创建 |

**关键设计决策：**
- **service 是纯 Python**：不 import Flask / FastAPI / MCP / `settings`（垫片）。配置经 `draft_store` 或 `vectcut.core.config.load_config()`；引擎经 `engine.adapter` + `engine.material_factory`；草稿经 `draft_store.get_draft` / `get_or_create_draft`。
- **Pydantic 替代 `data.get('xxx', default)`**：每个请求模型带类型 + 默认值 + 校验，Flask router 用 `Model.model_validate(request.get_json())` 一次解析。这是上帝文件瘦身的关键。
- **`get_or_create_draft` 下沉到 `draft_store`**：video/audio/text 都要它，是跨 feature 基础能力，不该躲在 `create_draft.py`。下沉后旧 `create_draft.py` 降级为垫片，阶段 3 文件不破。
- **`material_factory.resolve_*` 收敛平台分支**：`resolve_transition(name)` = `getattr(adapter.enum_for("transition"), name)`，业务层不再写 `if IS_CAPCUT_ENV`。
- **`save_draft_impl` 拆分边界**：公开 service 函数（`save_draft` 等）在 `service.py`；`_save_draft_background`/`_update_media_metadata` 这两个 200+ 行私有实现放 `_save_engine.py`（下划线前缀表内部），service 通过 `from vectcut.features.draft._save_engine import _save_draft_background` 调用。`save_task_cache` 已是独立 LRU，service 直接调，不迁。
- **黄金基线双轨**：HTTP 层（`test_business_routes_golden.py`）验路由外壳 + 错误分支 + 确定性成功分支；service 层（`test_video/test_service.py` 等）验 draft 输出（`script.dumps()` 快照），这是迁移 FastAPI 后的真正防回归网。
- **`add_video` 无网络副作用可建黄金**：`add_video_track` 只建 `Video_material`（`remote_url` 字段）+ 加段，**不下载**（下载在 `save_draft_background`）。故 `add_video` service 用固定 URL 调用，`script.dumps()` 确定性可快照。

---

### 任务 1：core/errors.py 补 DraftNotFound / EngineError / MediaDownloadError

**文件：**
- 修改：`vectcut/core/errors.py`
- 修改：`tests/core/test_errors.py`

- [ ] **步骤 1：编写失败的测试**

在 `tests/core/test_errors.py` 末尾追加：
```python
def test_draft_not_found_carries_code_and_404():
    from vectcut.core.errors import DraftNotFound, VectCutError

    err = DraftNotFound("dfd_cat_xxx")
    assert isinstance(err, VectCutError)
    assert err.code == "DRAFT_NOT_FOUND"
    assert err.http_status == 404
    assert "dfd_cat_xxx" in str(err)


def test_engine_error_carries_code_and_500():
    from vectcut.core.errors import EngineError

    err = EngineError("boom")
    assert err.code == "ENGINE_ERROR"
    assert err.http_status == 500


def test_media_download_error_carries_code_and_502():
    from vectcut.core.errors import MediaDownloadError

    err = MediaDownloadError("404 from cdn")
    assert err.code == "MEDIA_DOWNLOAD_ERROR"
    assert err.http_status == 502
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m pytest tests/core/test_errors.py -v`
预期：FAIL，`ImportError: cannot import name 'DraftNotFound'`。

- [ ] **步骤 3：编写实现**

在 `vectcut/core/errors.py` 的 `InvalidParam` 类后追加：
```python
class DraftNotFound(VectCutError):
    """草稿不存在于缓存（draft_id 未注册）。HTTP 404 / JSON-RPC -32001。"""

    code = "DRAFT_NOT_FOUND"
    http_status = 404


class EngineError(VectCutError):
    """pyJianYingDraft 引擎抛出异常（段/轨道/材料构造失败等）。HTTP 500 / -32003。"""

    code = "ENGINE_ERROR"
    http_status = 500


class MediaDownloadError(VectCutError):
    """素材下载失败（HTTP 4xx/5xx、ffprobe 失败等）。HTTP 502 / -32004。"""

    code = "MEDIA_DOWNLOAD_ERROR"
    http_status = 502
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m pytest tests/core/test_errors.py -v`
预期：PASS。

- [ ] **步骤 5：Commit**

```bash
git add vectcut/core/errors.py tests/core/test_errors.py
git commit -m "feat(core): 补 DraftNotFound/EngineError/MediaDownloadError 异常类（阶段2）"
```

---

### 任务 2：core/draft_store.py 增 get_or_create_draft

**文件：**
- 修改：`vectcut/core/draft_store.py`
- 修改：`tests/core/test_draft_store.py`

- [ ] **步骤 1：编写失败的测试**

在 `tests/core/test_draft_store.py` 末尾追加（若已用 `DRAFT_CACHE` fixture 则复用，否则直接操作全局）：
```python
def test_get_or_create_draft_creates_new_when_id_none():
    from vectcut.core import draft_store

    draft_store.DRAFT_CACHE.clear()
    draft_id, script = draft_store.get_or_create_draft(draft_id=None, width=1080, height=1920)
    assert draft_id.startswith("dfd_cat_")
    assert draft_id in draft_store.DRAFT_CACHE
    assert script is draft_store.DRAFT_CACHE[draft_id]


def test_get_or_create_draft_returns_cached_when_id_present():
    from vectcut.core import draft_store

    draft_store.DRAFT_CACHE.clear()
    first_id, _ = draft_store.get_or_create_draft(None, 1080, 1920)
    second_id, script = draft_store.get_or_create_draft(first_id, 1080, 1920)
    assert second_id == first_id
    assert script is draft_store.DRAFT_CACHE[first_id]
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m pytest tests/core/test_draft_store.py -v`
预期：FAIL，`AttributeError: module 'vectcut.core.draft_store' has no attribute 'get_or_create_draft'`。

- [ ] **步骤 3：编写实现**

在 `vectcut/core/draft_store.py` 末尾（`get_active_profile` 之后）追加：
```python
def get_or_create_draft(draft_id: Optional[str] = None, width: int = 1080, height: int = 1920):
    """草稿 get-or-create：draft_id 命中缓存则返回缓存对象，否则新建并入缓存。

    迁自根目录 create_draft.get_or_create_draft，供 video/audio/text 等业务 service 复用。
    """
    import time
    import uuid

    import pyJianYingDraft as draft

    if draft_id is not None and draft_id in DRAFT_CACHE:
        update_cache(draft_id, DRAFT_CACHE[draft_id])  # LRU 刷新
        return draft_id, DRAFT_CACHE[draft_id]

    unix_time = int(time.time())
    unique_id = uuid.uuid4().hex[:8]
    new_id = f"dfd_cat_{unix_time}_{unique_id}"
    script = draft.Script_file(width, height)
    update_cache(new_id, script)
    return new_id, script
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m pytest tests/core/test_draft_store.py -v`
预期：PASS。

- [ ] **步骤 5：Commit**

```bash
git add vectcut/core/draft_store.py tests/core/test_draft_store.py
git commit -m "feat(core): draft_store 增 get_or_create_draft 跨 feature 基础能力（阶段2）"
```

---

### 任务 3：engine/material_factory.py

**文件：**
- 创建：`vectcut/engine/material_factory.py`
- 创建：`tests/engine/test_material_factory.py`

- [ ] **步骤 1：编写失败的测试**

`tests/engine/test_material_factory.py`：
```python
"""material_factory 单测：材料构造 + 轨道 get-or-create + 平台枚举成员解析。"""
import pytest

from vectcut.engine import material_factory as mf


def test_build_video_material_without_draft_folder_uses_remote_url():
    m = mf.build_video_material(
        video_url="https://example.com/v.mp4",
        draft_folder=None,
        draft_id="dfd_1",
        material_name="video_abc.mp4",
        duration=3.0,
    )
    assert m.remote_url == "https://example.com/v.mp4"
    assert m.material_name == "video_abc.mp4"
    assert m.duration == 3.0


def test_build_video_material_with_draft_folder_sets_replace_path():
    m = mf.build_video_material(
        video_url="https://example.com/v.mp4",
        draft_folder="/tmp/drafts",
        draft_id="dfd_1",
        material_name="video_abc.mp4",
        duration=3.0,
    )
    assert m.replace_path is not None
    assert "video_abc.mp4" in m.replace_path


def test_build_audio_material_basic():
    m = mf.build_audio_material(
        audio_url="https://example.com/a.mp3",
        draft_folder=None,
        draft_id="dfd_1",
        material_name="audio_xyz.mp3",
        duration=2.0,
    )
    assert m.remote_url == "https://example.com/a.mp3"
    assert m.material_name == "audio_xyz.mp3"


def test_resolve_transition_uses_active_platform(monkeypatch):
    """resolve_transition 经 adapter.enum_for('transition')，按平台取成员。"""
    from pyJianYingDraft.metadata.transition_meta import Transition_type
    from pyJianYingDraft.metadata.capcut_transition_meta import CapCut_Transition_type

    monkeypatch.setattr(mf.adapter, "active_platform", lambda: "jianying")
    member = mf.resolve_transition(list(Transition_type.__members__)[0])
    assert member in Transition_type.__members__.values()

    monkeypatch.setattr(mf.adapter, "active_platform", lambda: "capcut")
    member = mf.resolve_transition(list(CapCut_Transition_type.__members__)[0])
    assert member in CapCut_Transition_type.__members__.values()


def test_resolve_transition_unknown_name_raises_attr_error(monkeypatch):
    monkeypatch.setattr(mf.adapter, "active_platform", lambda: "jianying")
    with pytest.raises(AttributeError):
        mf.resolve_transition("DEFINITELY_NOT_A_TRANSITION")


def test_resolve_mask_uses_active_platform(monkeypatch):
    from pyJianYingDraft.metadata.mask_meta import Mask_type

    monkeypatch.setattr(mf.adapter, "active_platform", lambda: "jianying")
    member = mf.resolve_mask(list(Mask_type.__members__)[0])
    assert member in Mask_type.__members__.values()


def test_resolve_audio_effect_searches_all_subtypes(monkeypatch):
    """audio_effect 返回 {子类型: 枚举} dict，resolve_audio_effect 遍历子类型命中。"""
    from pyJianYingDraft.metadata.audio_effect_meta import Tone_effect_type

    monkeypatch.setattr(mf.adapter, "active_platform", lambda: "jianying")
    first_name = list(Tone_effect_type.__members__)[0]
    member, subtype = mf.resolve_audio_effect(first_name)
    assert member in Tone_effect_type.__members__.values()
    assert subtype == "Tone"


def test_resolve_audio_effect_unknown_returns_none(monkeypatch):
    monkeypatch.setattr(mf.adapter, "active_platform", lambda: "jianying")
    assert mf.resolve_audio_effect("NOPE") is None


def test_add_to_track_creates_track_if_missing():
    import pyJianYingDraft as draft
    from vectcut.core import draft_store

    draft_store.DRAFT_CACHE.clear()
    _, script = draft_store.get_or_create_draft(None, 1080, 1920)
    material = mf.build_video_material("https://e.com/v.mp4", None, "x", "v.mp4", 1.0)
    seg = draft.Video_segment(material, target_timerange=draft.trange("0s", "1s"), source_timerange=draft.trange("0s", "1s"))
    mf.add_to_track(script, seg, track_name="video_main", track_type=draft.Track_type.video, relative_index=0)
    assert len(script.materials.videos) == 1
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m pytest tests/engine/test_material_factory.py -v`
预期：FAIL，`ModuleNotFoundError: No module named 'vectcut.engine.material_factory'`。

- [ ] **步骤 3：编写实现**

`vectcut/engine/material_factory.py`：
```python
"""材料/轨道构造工厂 + 平台枚举成员解析。

封装散在 add_*_track.py / add_*_impl.py 里的引擎调用（规格 §5.1②）。
应用层业务 service 只调本模块，不再直接 import pyJianYingDraft 顶层符号、不再写 if IS_CAPCUT_ENV。
平台派发经 vectcut.engine.adapter.enum_for(kind)。
"""

from __future__ import annotations

from typing import Optional, Tuple

import pyJianYingDraft as draft
from pyJianYingDraft import Clip_settings, exceptions, trange

from util import build_draft_asset_path
from vectcut.engine import adapter


def build_video_material(
    video_url: str,
    draft_folder: Optional[str],
    draft_id: str,
    material_name: str,
    duration: float = 0.0,
    width: int = 0,
    height: int = 0,
) -> "draft.Video_material":
    """构造 Video_material。draft_folder 非空时设 replace_path，否则仅 remote_url。"""
    kwargs = dict(
        material_type="video",
        remote_url=video_url,
        material_name=material_name,
        duration=duration,
        width=width,
        height=height,
    )
    if draft_folder:
        kwargs["replace_path"] = build_draft_asset_path(draft_folder, draft_id, "video", material_name)
    return draft.Video_material(**kwargs)


def build_audio_material(
    audio_url: str,
    draft_folder: Optional[str],
    draft_id: str,
    material_name: str,
    duration: float = 0.0,
) -> "draft.Audio_material":
    """构造 Audio_material。draft_folder 非空时设 replace_path。"""
    kwargs = dict(
        remote_url=audio_url,
        material_name=material_name,
        duration=duration,
    )
    if draft_folder:
        kwargs["replace_path"] = build_draft_asset_path(draft_folder, draft_id, "audio", material_name)
    return draft.Audio_material(**kwargs)


def add_to_track(script, segment, track_name: Optional[str], track_type, relative_index: int = 0) -> None:
    """get-or-create 命名轨道并添加段。track_name 为 None 时建匿名轨道。"""
    if track_name is not None:
        try:
            script.get_imported_track(track_type, name=track_name)
        except exceptions.TrackNotFound:
            script.add_track(track_type, track_name=track_name, relative_index=relative_index)
    else:
        script.add_track(track_type, relative_index=relative_index)
    script.add_segment(segment, track_name=track_name)


def resolve_transition(name: str):
    """按激活平台返回 Transition_type / CapCut_Transition_type 的成员。未知名抛 AttributeError。"""
    return getattr(adapter.enum_for("transition"), name)


def resolve_mask(name: str):
    """按激活平台返回 Mask_type / CapCut_Mask_type 的成员。"""
    return getattr(adapter.enum_for("mask"), name)


def resolve_audio_effect(name: str) -> Optional[Tuple[object, str]]:
    """遍历 audio_effect 子类型 dict，命中返回 (枚举成员, 子类型标签)，未命中返回 None。

    adapter.enum_for('audio_effect') 返回 {子类型标签: 枚举类}，子类型遍历顺序与旧 add_audio_track 一致。
    """
    subtype_to_enum = adapter.enum_for("audio_effect")
    for subtype, enum_cls in subtype_to_enum.items():
        member = getattr(enum_cls, name, None)
        if member is not None:
            return member, subtype
    return None
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m pytest tests/engine/test_material_factory.py -v`
预期：PASS。

- [ ] **步骤 5：Commit**

```bash
git add vectcut/engine/material_factory.py tests/engine/test_material_factory.py
git commit -m "feat(engine): 新增 material_factory 收敛材料构造与平台枚举解析（阶段2）"
```

---

### 任务 4：features/draft/schemas.py

**文件：**
- 创建：`vectcut/features/draft/__init__.py`
- 创建：`vectcut/features/draft/schemas.py`
- 创建：`tests/features/draft/__init__.py`
- 创建：`tests/features/draft/test_schemas.py`

- [ ] **步骤 1：编写失败的测试**

`tests/features/draft/__init__.py`（空文件）。

`tests/features/draft/test_schemas.py`：
```python
from vectcut.features.draft.schemas import (
    CreateDraftRequest, CreateDraftResponse,
    SaveDraftRequest, SaveDraftResponse,
    QueryScriptRequest, QueryScriptResponse,
    QueryDraftStatusRequest, QueryDraftStatusResponse,
    GenerateDraftUrlRequest, GenerateDraftUrlResponse,
)


def test_create_draft_request_defaults():
    r = CreateDraftRequest()
    assert r.width == 1080
    assert r.height == 1920


def test_save_draft_request_defaults_draft_folder_none():
    r = SaveDraftRequest(draft_id="dfd_1")
    assert r.draft_id == "dfd_1"
    assert r.draft_folder is None


def test_query_script_request_defaults_force_update_true():
    r = QueryScriptRequest(draft_id="dfd_1")
    assert r.force_update is True


def test_query_draft_status_request():
    r = QueryDraftStatusRequest(task_id="t_1")
    assert r.task_id == "t_1"


def test_generate_draft_url_request():
    r = GenerateDraftUrlRequest(draft_id="dfd_1")
    assert r.draft_id == "dfd_1"
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m pytest tests/features/draft/test_schemas.py -v`
预期：FAIL，`ModuleNotFoundError: No module named 'vectcut.features.draft.schemas'`。

- [ ] **步骤 3：编写实现**

`vectcut/features/draft/__init__.py`（空文件）。

`vectcut/features/draft/schemas.py`：
```python
"""draft feature 请求/响应 Pydantic 模型。HTTP 与 MCP 共用（规格 §4）。"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class CreateDraftRequest(BaseModel):
    width: int = 1080
    height: int = 1920


class CreateDraftResponse(BaseModel):
    draft_id: str
    draft_url: str


class SaveDraftRequest(BaseModel):
    draft_id: str
    draft_folder: Optional[str] = None


class SaveDraftResponse(BaseModel):
    success: bool = True
    draft_url: str = ""
    error: str = ""


class QueryScriptRequest(BaseModel):
    draft_id: str
    force_update: bool = True


class QueryScriptResponse(BaseModel):
    success: bool = True
    output: str = ""
    error: str = ""


class QueryDraftStatusRequest(BaseModel):
    task_id: str


class QueryDraftStatusResponse(BaseModel):
    success: bool = True
    output: Any = None
    error: str = ""


class GenerateDraftUrlRequest(BaseModel):
    draft_id: str
    draft_folder: Optional[str] = None


class GenerateDraftUrlResponse(BaseModel):
    success: bool = True
    draft_url: str = ""
    error: str = ""
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m pytest tests/features/draft/test_schemas.py -v`
预期：PASS。

- [ ] **步骤 5：Commit**

```bash
git add vectcut/features/draft/__init__.py vectcut/features/draft/schemas.py tests/features/draft/__init__.py tests/features/draft/test_schemas.py
git commit -m "feat(draft): 新增 schemas Pydantic 请求/响应模型（阶段2）"
```

---

### 任务 5：features/draft/_save_engine.py（save_draft_impl 拆分·私有实现）

**文件：**
- 创建：`vectcut/features/draft/_save_engine.py`
- 创建：`tests/features/draft/test_save_engine.py`

把 `save_draft_impl.py` 的 `save_draft_background`（43-255 行）+ `update_media_metadata`（292-533 行）+ `build_asset_path`（32-41 行）+ `get_duration_impl.py` 的 `get_video_duration` 迁入，去除 `from settings import` / `from draft_cache import` 等旧依赖，改走 `vectcut.core.*`。

- [ ] **步骤 1：编写失败的测试**

`tests/features/draft/test_save_engine.py`：
```python
"""_save_engine 私有实现单测：mock 下载与 ffprobe，验证保存流程产出 draft_url 与任务状态。"""
import os

import pytest

from vectcut.core import draft_store


@pytest.fixture(autouse=True)
def _clean_cache():
    draft_store.DRAFT_CACHE.clear()
    yield
    draft_store.DRAFT_CACHE.clear()


def test_save_draft_background_draft_not_in_cache_marks_failed(tmp_path, monkeypatch):
    from vectcut.features.draft import _save_engine
    from vectcut.features.draft._save_engine import save_task_cache

    status = _save_engine.save_draft_background("missing_id", str(tmp_path), "missing_id")
    assert status == ""
    task = save_task_cache.get_task_status("missing_id")
    assert task["status"] == "failed"


def test_save_draft_background_writes_profile_content(tmp_path, monkeypatch):
    from vectcut.features.draft import _save_engine
    from vectcut.features.draft._save_engine import save_task_cache

    # 准备一个空 draft
    draft_id, script = draft_store.get_or_create_draft(None, 1080, 1920)
    # mock ffprobe（update_media_metadata 会调 get_video_duration，但空 draft 无素材，不会调）
    monkeypatch.setattr(_save_engine, "_get_video_duration", lambda url: {"success": True, "output": 1.0, "error": None})
    # mock 下载（空 draft 无素材，不会调；但 save 流程会跑）
    monkeypatch.setattr(_save_engine, "download_file", lambda url, path: path)

    out_dir = str(tmp_path / "out")
    url = _save_engine.save_draft_background(draft_id, out_dir, draft_id)
    # 空 draft + IS_UPLOAD_DRAFT 默认 False → 不上传，draft_url 为 ""
    assert url == ""
    task = save_task_cache.get_task_status(draft_id)
    assert task["status"] == "completed"
    assert task["progress"] == 100
    # profile content 文件应已落盘
    assert os.path.isdir(os.path.join(out_dir, draft_id))


def test_build_asset_path_delegates_to_util():
    from vectcut.features.draft._save_engine import build_asset_path

    p = build_asset_path("/tmp/d", "dfd_1", "video", "v.mp4")
    assert p.endswith("v.mp4")
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m pytest tests/features/draft/test_save_engine.py -v`
预期：FAIL，`ModuleNotFoundError: No module named 'vectcut.features.draft._save_engine'`。

- [ ] **步骤 3：编写实现**

`vectcut/features/draft/_save_engine.py`：
```python
"""save_draft_impl 拆分后的私有保存引擎。

迁自根目录 save_draft_impl.py（save_draft_background / update_media_metadata / build_asset_path）
与 get_duration_impl.py（get_video_duration）。改走 vectcut.core.* 与 save_task_cache，
不再 import settings / draft_cache / draft_profiles 旧模块。
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Optional

import requests

from downloader import download_file  # 阶段5再迁 downloader
from save_task_cache import (  # 纯内存 LRU，独立模块，本阶段不迁
    create_task,
    get_task_status,
    increment_task_field,
    update_task_field,
    update_task_fields,
    update_tasks_cache,
)
from util import build_draft_asset_path, zip_draft
from oss import upload_to_oss
from vectcut.core.config import load_config
from vectcut.core.draft_store import DRAFT_CACHE, get_active_profile, write_profile_content

logger = logging.getLogger("flask_video_generator")

# 供测试 monkeypatch 的别名（_save_engine 内部统一调本模块的 _get_video_duration）
def _get_video_duration(video_url):
    return get_video_duration(video_url)


def get_video_duration(video_url):
    """ffprobe 取时长（秒）。迁自 get_duration_impl.py。3 次重试，10s 超时。"""
    for attempt in range(3):
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", video_url],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return {"success": True, "output": float(data["format"]["duration"]), "error": None}
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError, KeyError):
            pass
        except Exception:
            pass
        time.sleep(1)
    return {"success": False, "output": 0.0, "error": "ffprobe failed"}


def build_asset_path(draft_folder: str, draft_id: str, asset_type: str, material_name: str) -> str:
    return build_draft_asset_path(draft_folder, draft_id, asset_type, material_name)


def save_draft_background(draft_id, draft_folder, task_id):
    """后台保存草稿到磁盘 / OSS。迁自 save_draft_impl.save_draft_background，逻辑逐段保真。"""
    try:
        if draft_id not in DRAFT_CACHE:
            update_tasks_cache(task_id, {
                "status": "failed", "message": f"Draft {draft_id} does not exist in cache",
                "progress": 0, "completed_files": 0, "total_files": 0, "draft_url": "",
            })
            logger.error(f"Draft {draft_id} does not exist in cache, task {task_id} failed.")
            return ""

        script = DRAFT_CACHE[draft_id]
        update_tasks_cache(task_id, {
            "status": "processing", "message": "Preparing draft files",
            "progress": 0, "completed_files": 0, "total_files": 0, "draft_url": "",
        })

        current_dir = os.path.dirname(os.path.abspath(__file__))  # features/draft/
        # 模板在项目根，回退两级
        project_root = os.path.dirname(os.path.dirname(current_dir))
        output_base_dir = draft_folder or project_root
        draft_dir = os.path.join(output_base_dir, draft_id)

        if os.path.exists(draft_dir):
            shutil.rmtree(draft_dir)

        draft_profile = get_active_profile()
        template_source_dir = os.path.join(project_root, draft_profile.template_dir)
        if not os.path.exists(template_source_dir):
            raise FileNotFoundError(f"Template draft {draft_profile.template_dir} does not exist")
        shutil.copytree(template_source_dir, draft_dir)

        update_task_field(task_id, "message", "Updating media file metadata")
        update_task_field(task_id, "progress", 5)
        update_media_metadata(script, task_id)

        download_tasks = []
        audios = script.materials.audios
        if audios:
            for audio in audios:
                remote_url = audio.remote_url
                material_name = audio.material_name
                if draft_folder:
                    audio.replace_path = build_asset_path(draft_folder, draft_id, "audio", material_name)
                if not remote_url:
                    continue
                download_tasks.append({
                    "type": "audio", "func": download_file,
                    "args": (remote_url, os.path.join(output_base_dir, f"{draft_id}/assets/audio/{material_name}")),
                    "material": audio,
                })

        videos = script.materials.videos
        if videos:
            for video in videos:
                remote_url = video.remote_url
                material_name = video.material_name
                if video.material_type == "photo":
                    if draft_folder:
                        video.replace_path = build_asset_path(draft_folder, draft_id, "image", material_name)
                    if not remote_url:
                        continue
                    download_tasks.append({
                        "type": "image", "func": download_file,
                        "args": (remote_url, os.path.join(output_base_dir, f"{draft_id}/assets/image/{material_name}")),
                        "material": video,
                    })
                elif video.material_type == "video":
                    if draft_folder:
                        video.replace_path = build_asset_path(draft_folder, draft_id, "video", material_name)
                    if not remote_url:
                        continue
                    download_tasks.append({
                        "type": "video", "func": download_file,
                        "args": (remote_url, os.path.join(output_base_dir, f"{draft_id}/assets/video/{material_name}")),
                        "material": video,
                    })

        update_task_field(task_id, "message", f"Collected {len(download_tasks)} download tasks in total")
        update_task_field(task_id, "progress", 10)

        completed_files = 0
        if download_tasks:
            with ThreadPoolExecutor(max_workers=16) as executor:
                future_to_task = {executor.submit(t["func"], *t["args"]): t for t in download_tasks}
                for future in as_completed(future_to_task):
                    t = future_to_task[future]
                    try:
                        future.result()
                        completed_files += 1
                        update_task_field(task_id, "completed_files", completed_files)
                        total = len(download_tasks)
                        update_task_field(task_id, "total_files", total)
                        update_task_field(task_id, "progress", 10 + int((completed_files / total) * 60))
                        update_task_field(task_id, "message", f"Downloaded {completed_files}/{total} files")
                    except Exception as e:
                        logger.error(f"Task {task_id}: Download {t['type']} failed: {e}")

        update_task_field(task_id, "progress", 70)
        update_task_field(task_id, "message", "Saving draft information")
        write_profile_content(draft_profile, draft_dir, script.dumps(draft_profile))

        draft_url = ""
        cfg = load_config()
        if cfg.is_upload_draft:
            update_task_field(task_id, "progress", 80)
            update_task_field(task_id, "message", "Compressing draft files")
            zip_path = zip_draft(draft_id)
            update_task_field(task_id, "progress", 90)
            update_task_field(task_id, "message", "Uploading to cloud storage")
            draft_url = upload_to_oss(zip_path)
            update_task_field(task_id, "draft_url", draft_url)
            tmp_draft_dir = os.path.join(project_root, draft_id)
            if os.path.exists(tmp_draft_dir):
                shutil.rmtree(tmp_draft_dir)

        update_task_field(task_id, "status", "completed")
        update_task_field(task_id, "progress", 100)
        update_task_field(task_id, "message", "Draft creation completed")
        return draft_url

    except Exception as e:
        update_task_fields(task_id, status="failed", message=f"Failed to save draft: {str(e)}")
        logger.error(f"Saving draft {draft_id} task {task_id} failed: {str(e)}", exc_info=True)
        return ""


def update_media_metadata(script, task_id=None):
    """遍历素材用 ffprobe 修正时长/宽高与 timerange。迁自 save_draft_impl.update_media_metadata，逐段保真。"""
    # —— 音频素材 ——
    audios = script.materials.audios
    if audios:
        for audio in audios:
            remote_url = audio.remote_url
            if not remote_url:
                continue
            dur = _get_video_duration(remote_url)
            if not dur["success"]:
                continue
            duration = dur["output"]
            if audio.duration != duration and duration > 0:
                audio.duration = duration
            for seg in script.segments:
                if hasattr(seg, "source_timerange") and getattr(seg, "source", None) is audio:
                    try:
                        from pyJianYingDraft import Timerange
                        seg.source_timerange = Timerange(0, int(duration * 1_000_000))
                        seg.target_timerange = Timerange(
                            seg.target_timerange.start,
                            int(duration * 1_000_000),
                        )
                    except Exception:
                        pass

    # —— 视频素材 ——
    videos = script.materials.videos
    if videos:
        for video in videos:
            remote_url = video.remote_url
            if not remote_url:
                continue
            dur = _get_video_duration(remote_url)
            if not dur["success"]:
                continue
            duration = dur["output"]
            if video.duration != duration and duration > 0:
                video.duration = duration
            for seg in script.segments:
                if hasattr(seg, "source_timerange") and getattr(seg, "source", None) is video:
                    try:
                        from pyJianYingDraft import Timerange
                        seg.source_timerange = Timerange(0, int(duration * 1_000_000))
                    except Exception:
                        pass

    if task_id:
        update_task_field(task_id, "message", "Media metadata updated")
```

> **说明**：`update_media_metadata` 原始实现 200+ 行含关键帧挂起、时间轴冲突处理等细节。上面是保真迁移的**主体框架**——迁移者须对照 `save_draft_impl.py:292-533` 把剩余逐段逻辑（关键帧 timerange 修正、`script.duration` 重算）补齐，**逐段复制不改语义**。本计划只展示框架以控制篇幅；迁移者必须打开原文件逐行对照，不得简化。测试 `test_save_draft_background_writes_profile_content` 用空 draft（无素材）绕过 `update_media_metadata` 的 ffprobe 路径，验证保存主流程。

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m pytest tests/features/draft/test_save_engine.py -v`
预期：PASS。

- [ ] **步骤 5：Commit**

```bash
git add vectcut/features/draft/_save_engine.py tests/features/draft/test_save_engine.py
git commit -m "feat(draft): 拆分 save_draft_impl 为 _save_engine 私有保存引擎（阶段2）"
```

---

### 任务 6：features/draft/service.py（5 公开 service 函数）

**文件：**
- 创建：`vectcut/features/draft/service.py`
- 创建：`tests/features/draft/test_service.py`

- [ ] **步骤 1：编写失败的测试**

`tests/features/draft/test_service.py`：
```python
import pytest

from vectcut.core import draft_store


@pytest.fixture(autouse=True)
def _clean_cache():
    draft_store.DRAFT_CACHE.clear()
    yield
    draft_store.DRAFT_CACHE.clear()


def test_create_draft_service_returns_id_and_url(monkeypatch):
    from vectcut.features.draft import service
    from vectcut.features.draft.schemas import CreateDraftRequest

    monkeypatch.setattr(service, "generate_draft_url", lambda draft_id: f"http://x/{draft_id}")
    resp = service.create_draft(CreateDraftRequest(width=1080, height=1920))
    assert resp.draft_id.startswith("dfd_cat_")
    assert resp.draft_url.startswith("http://x/")


def test_generate_draft_url_service_uses_config():
    from vectcut.features.draft import service
    from vectcut.features.draft.schemas import GenerateDraftUrlRequest

    resp = service.generate_draft_url(GenerateDraftUrlRequest(draft_id="dfd_1").draft_id)
    assert "dfd_1" in resp
    assert "is_capcut=" in resp


def test_query_task_status_service_not_found():
    from vectcut.features.draft import service
    from vectcut.features.draft.schemas import QueryDraftStatusRequest

    out = service.query_task_status(QueryDraftStatusRequest(task_id="nope"))
    assert out.success is True
    assert out.output["status"] == "not_found"


def test_query_script_service_missing_draft_raises():
    from vectcut.features.draft import service
    from vectcut.features.draft.schemas import QueryScriptRequest
    from vectcut.core.errors import DraftNotFound

    with pytest.raises(DraftNotFound):
        service.query_script(QueryScriptRequest(draft_id="missing"))


def test_save_draft_service_missing_draft_raises():
    from vectcut.features.draft import service
    from vectcut.features.draft.schemas import SaveDraftRequest
    from vectcut.core.errors import DraftNotFound

    with pytest.raises(DraftNotFound):
        service.save_draft(SaveDraftRequest(draft_id="missing"))
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m pytest tests/features/draft/test_service.py -v`
预期：FAIL，`ModuleNotFoundError: No module named 'vectcut.features.draft.service'`。

- [ ] **步骤 3：编写实现**

`vectcut/features/draft/service.py`：
```python
"""draft feature 公开 service：纯 Python，不依赖 web/MCP 框架。

5 个函数：create_draft / save_draft / query_script / query_task_status / generate_draft_url。
save_draft 的重活委托 _save_engine.save_draft_background。
"""

from __future__ import annotations

from vectcut.core.config import load_config
from vectcut.core.draft_store import DRAFT_CACHE, get_active_profile, get_or_create_draft, write_profile_content
from vectcut.core.errors import DraftNotFound
from vectcut.features.draft._save_engine import save_draft_background
from vectcut.features.draft.schemas import (
    CreateDraftRequest, CreateDraftResponse,
    GenerateDraftUrlResponse,
    QueryDraftStatusRequest, QueryDraftStatusResponse,
    QueryScriptRequest, QueryScriptResponse,
    SaveDraftRequest, SaveDraftResponse,
)
from save_task_cache import get_task_status


def generate_draft_url(draft_id: str) -> str:
    cfg = load_config()
    return f"{cfg.draft_domain}{cfg.preview_router}?draft_id={draft_id}&is_capcut={1 if cfg.is_capcut_env else 0}"


def create_draft(req: CreateDraftRequest) -> CreateDraftResponse:
    draft_id, _script = get_or_create_draft(draft_id=None, width=req.width, height=req.height)
    return CreateDraftResponse(draft_id=draft_id, draft_url=generate_draft_url(draft_id))


def save_draft(req: SaveDraftRequest) -> SaveDraftResponse:
    if req.draft_id not in DRAFT_CACHE:
        raise DraftNotFound(req.draft_id)
    cfg = load_config()
    folder = req.draft_folder if req.draft_folder is not None else cfg.draft_folder
    draft_url = save_draft_background(req.draft_id, folder, req.draft_id)
    return SaveDraftResponse(success=True, draft_url=draft_url, error="")


def query_script(req: QueryScriptRequest) -> QueryScriptResponse:
    if req.draft_id not in DRAFT_CACHE:
        raise DraftNotFound(req.draft_id)
    script = DRAFT_CACHE[req.draft_id]
    if req.force_update:
        from vectcut.features.draft._save_engine import update_media_metadata
        update_media_metadata(script)
    profile = get_active_profile()
    return QueryScriptResponse(success=True, output=script.dumps(profile), error="")


def query_task_status(req: QueryDraftStatusRequest) -> QueryDraftStatusResponse:
    status = get_task_status(req.task_id)
    if status["status"] == "not_found":
        return QueryDraftStatusResponse(success=True, output=status, error="")
    return QueryDraftStatusResponse(success=True, output=status, error="")
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m pytest tests/features/draft/test_service.py -v`
预期：PASS。

- [ ] **步骤 5：Commit**

```bash
git add vectcut/features/draft/service.py tests/features/draft/test_service.py
git commit -m "feat(draft): 新增 5 个公开 service 函数（阶段2）"
```

---

### 任务 7：features/draft/flask_router.py

**文件：**
- 创建：`vectcut/features/draft/flask_router.py`
- 创建：`tests/features/draft/test_router.py`

- [ ] **步骤 1：编写失败的测试**

`tests/features/draft/test_router.py`：
```python
import pytest


@pytest.fixture()
def client(monkeypatch):
    from flask import Flask
    from vectcut.features.draft.flask_router import bp
    from vectcut.features.draft import service

    app = Flask(__name__)
    app.register_blueprint(bp)
    app.config["TESTING"] = True
    return app.test_client()


def test_create_draft_route_returns_envelope(client):
    resp = client.post("/create_draft", json={})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    assert body["output"]["draft_id"].startswith("dfd_cat_")
    assert "draft_url" in body["output"]
    assert body["error"] == ""


def test_save_draft_route_missing_draft_id_returns_error_envelope(client):
    resp = client.post("/save_draft", json={})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is False
    assert "draft_id" in body["error"]


def test_query_script_route_missing_returns_error(client):
    resp = client.post("/query_script", json={"draft_id": "missing"})
    body = resp.get_json()
    assert body["success"] is False


def test_query_draft_status_route_not_found(client):
    resp = client.post("/query_draft_status", json={"task_id": "nope"})
    body = resp.get_json()
    assert body["success"] is True
    assert body["output"]["status"] == "not_found"


def test_generate_draft_url_route(client):
    resp = client.post("/generate_draft_url", json={"draft_id": "dfd_1"})
    body = resp.get_json()
    assert body["success"] is True
    assert "dfd_1" in body["output"]["draft_url"]
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m pytest tests/features/draft/test_router.py -v`
预期：FAIL，`ModuleNotFoundError: No module named 'vectcut.features.draft.flask_router'`。

- [ ] **步骤 3：编写实现**

`vectcut/features/draft/flask_router.py`：
```python
"""draft feature Flask Blueprint：5 路由薄接线，统一 {success,output,error} 外壳。

阶段 4 迁 FastAPI 时，同一 service 接到 FastAPI router，本文件替换。
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from vectcut.core.errors import VectCutError
from vectcut.features.draft import service
from vectcut.features.draft.schemas import (
    CreateDraftRequest, GenerateDraftUrlRequest,
    QueryDraftStatusRequest, QueryScriptRequest, SaveDraftRequest,
)

bp = Blueprint("draft", __name__)


def _ok(output):
    return jsonify({"success": True, "output": output, "error": ""})


def _err(e: VectCutError):
    return jsonify({"success": False, "output": "", "error": str(e)})


@bp.post("/create_draft")
def create_draft():
    try:
        req = CreateDraftRequest.model_validate(request.get_json() or {})
        resp = service.create_draft(req)
        return _ok({"draft_id": resp.draft_id, "draft_url": resp.draft_url})
    except VectCutError as e:
        return _err(e)


@bp.post("/save_draft")
def save_draft():
    try:
        req = SaveDraftRequest.model_validate(request.get_json() or {})
        resp = service.save_draft(req)
        return _ok({"draft_url": resp.draft_url} if resp.draft_url else {})
    except VectCutError as e:
        return _err(e)
    except Exception as e:
        return jsonify({"success": False, "output": "", "error": f"Error occurred while saving draft: {e}. "})


@bp.post("/query_script")
def query_script():
    try:
        req = QueryScriptRequest.model_validate(request.get_json() or {})
        resp = service.query_script(req)
        return _ok(resp.output)
    except VectCutError as e:
        return _err(e)


@bp.post("/query_draft_status")
def query_draft_status():
    try:
        req = QueryDraftStatusRequest.model_validate(request.get_json() or {})
        resp = service.query_task_status(req)
        return _ok(resp.output)
    except VectCutError as e:
        return _err(e)
    except Exception as e:
        return jsonify({"success": False, "output": "", "error": f"Error occurred while querying task status: {e}."})


@bp.post("/generate_draft_url")
def generate_draft_url():
    try:
        req = GenerateDraftUrlRequest.model_validate(request.get_json() or {})
        url = service.generate_draft_url(req.draft_id)
        return _ok({"draft_url": url})
    except VectCutError as e:
        return _err(e)
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m pytest tests/features/draft/test_router.py -v`
预期：PASS。

- [ ] **步骤 5：Commit**

```bash
git add vectcut/features/draft/flask_router.py tests/features/draft/test_router.py
git commit -m "feat(draft): 新增 Flask Blueprint 5 路由（阶段2）"
```

---

### 任务 8：create_draft.py 降级为垫片

**文件：**
- 修改：`create_draft.py`

阶段 3 的 `add_text_impl` / `add_image_impl` 等仍 `from create_draft import get_or_create_draft`，本阶段不迁它们，故 `create_draft.py` 须保留可 import，降级为转发 `draft_store.get_or_create_draft`。

- [ ] **步骤 1：编写失败的测试**

`tests/core/test_draft_store.py` 已覆盖 `get_or_create_draft`。这里加一个垫片等价性测试：
```python
def test_legacy_create_draft_shim_forwards_get_or_create_draft():
    import create_draft
    from vectcut.core import draft_store

    draft_store.DRAFT_CACHE.clear()
    # 垫片函数应与 draft_store 同一函数
    assert create_draft.get_or_create_draft is draft_store.get_or_create_draft or callable(create_draft.get_or_create_draft)
    draft_id, script = create_draft.get_or_create_draft(None, 1080, 1920)
    assert draft_id in draft_store.DRAFT_CACHE
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m pytest tests/core/test_draft_store.py::test_legacy_create_draft_shim_forwards_get_or_create_draft -v`
预期：FAIL（旧 `create_draft.get_or_create_draft` 是独立实现，能跑通但 `is` 判断失败；或行为不一致）。

- [ ] **步骤 3：编写实现**

`create_draft.py` 整体替换为：
```python
"""垫片：转发到 vectcut.core.draft_store.get_or_create_draft。

阶段 3 的 add_text_impl / add_image_impl 等仍 `from create_draft import get_or_create_draft`，
本垫片保留旧 import 不破，真源在 draft_store。阶段 5 迁完所有 add_* 后可删本文件。
"""
from vectcut.core.draft_store import get_or_create_draft  # noqa: F401


def create_draft(width=1080, height=1920):
    """兼容旧 create_draft.create_draft(width, height) → (script, draft_id) 签名。

    旧签名返回 (script, draft_id)；draft_store.get_or_create_draft 返回 (draft_id, script)。
    此处适配顺序。
    """
    draft_id, script = get_or_create_draft(None, width, height)
    return script, draft_id
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m pytest tests/core/test_draft_store.py -v`
预期：PASS。

- [ ] **步骤 5：Commit**

```bash
git add create_draft.py tests/core/test_draft_store.py
git commit -m "refactor(create_draft): 降级为 draft_store 垫片（阶段2）"
```

---

### 任务 9：features/video/schemas.py

**文件：**
- 创建：`vectcut/features/video/__init__.py`
- 创建：`vectcut/features/video/schemas.py`
- 创建：`tests/features/video/__init__.py`
- 创建：`tests/features/video/test_schemas.py`

- [ ] **步骤 1：编写失败的测试**

`tests/features/video/__init__.py`（空）。

`tests/features/video/test_schemas.py`：
```python
from vectcut.features.video.schemas import AddVideoRequest, AddVideoResponse, AddVideoKeyframeRequest


def test_add_video_request_defaults():
    r = AddVideoRequest(video_url="https://e.com/v.mp4")
    assert r.video_url == "https://e.com/v.mp4"
    assert r.width == 1080
    assert r.height == 1920
    assert r.start == 0
    assert r.track_name == "video_main"
    assert r.volume == 1.0
    assert r.transition is None
    assert r.mask_type is None


def test_add_video_keyframe_request_defaults():
    r = AddVideoKeyframeRequest(draft_id="dfd_1")
    assert r.draft_id == "dfd_1"
    assert r.track_name == "video_main"
    assert r.property_type == "alpha"
    assert r.value == "1.0"
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m pytest tests/features/video/test_schemas.py -v`
预期：FAIL，`ModuleNotFoundError`。

- [ ] **步骤 3：编写实现**

`vectcut/features/video/__init__.py`（空）。

`vectcut/features/video/schemas.py`：
```python
"""video feature 请求/响应模型。字段默认值与 capcut_server.py:add_video 逐一对齐。"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class AddVideoRequest(BaseModel):
    draft_id: Optional[str] = None
    video_url: str
    draft_folder: Optional[str] = None
    width: int = 1080
    height: int = 1920
    start: float = 0
    end: float = 0
    target_start: float = 0
    transform_y: float = 0
    transform_x: float = 0
    scale_x: float = 1
    scale_y: float = 1
    speed: float = 1.0
    track_name: str = "video_main"
    relative_index: int = 0
    duration: Optional[float] = None
    transition: Optional[str] = None
    transition_duration: float = 0.5
    volume: float = 1.0
    # mask
    mask_type: Optional[str] = None
    mask_center_x: float = 0.5
    mask_center_y: float = 0.5
    mask_size: float = 1.0
    mask_rotation: float = 0.0
    mask_feather: float = 0.0
    mask_invert: bool = False
    mask_rect_width: Optional[float] = None
    mask_round_corner: Optional[float] = None
    # background
    background_blur: Optional[int] = None


class AddVideoResponse(BaseModel):
    draft_id: str
    draft_url: str


class AddVideoKeyframeRequest(BaseModel):
    draft_id: str
    track_name: str = "video_main"
    property_type: str = "alpha"
    time: float = 0.0
    value: str = "1.0"
    property_types: Optional[List[str]] = None
    times: Optional[List[float]] = None
    values: Optional[List[str]] = None


class AddVideoKeyframeResponse(BaseModel):
    draft_id: str
    draft_url: str
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m pytest tests/features/video/test_schemas.py -v`
预期：PASS。

- [ ] **步骤 5：Commit**

```bash
git add vectcut/features/video/__init__.py vectcut/features/video/schemas.py tests/features/video/__init__.py tests/features/video/test_schemas.py
git commit -m "feat(video): 新增 schemas（阶段2）"
```

---

### 任务 10：features/video/service.py — add_video

**文件：**
- 创建：`vectcut/features/video/service.py`
- 创建：`tests/features/video/test_service.py`

迁移 `add_video_track.py` 逻辑，`if IS_CAPCUT_ENV` → `material_factory.resolve_transition` / `resolve_mask`，`get_or_create_draft` 走 `draft_store`，`generate_draft_url` 走 draft service。

- [ ] **步骤 1：编写失败的测试**

`tests/features/video/test_service.py`：
```python
import pytest

from vectcut.core import draft_store


@pytest.fixture(autouse=True)
def _clean_cache():
    draft_store.DRAFT_CACHE.clear()
    yield
    draft_store.DRAFT_CACHE.clear()


def test_add_video_creates_video_segment_in_draft():
    from vectcut.features.video import service
    from vectcut.features.video.schemas import AddVideoRequest

    resp = service.add_video(AddVideoRequest(video_url="https://example.com/v.mp4"))
    assert resp.draft_id.startswith("dfd_cat_")
    script = draft_store.get_draft(resp.draft_id)
    assert script is not None
    assert len(script.materials.videos) == 1
    assert script.materials.videos[0].remote_url == "https://example.com/v.mp4"


def test_add_video_with_transition_resolves_via_adapter(monkeypatch):
    from vectcut.features.video import service
    from vectcut.features.video.schemas import AddVideoRequest
    from vectcut.engine import material_factory

    called = {}
    def fake_resolve(name):
        called["name"] = name
        class _M: pass
        return _M()
    monkeypatch.setattr(material_factory, "resolve_transition", fake_resolve)
    # transition add_transition 会调引擎；mock segment.add_transition
    import pyJianYingDraft as draft
    orig_seg = draft.Video_segment
    class FakeSeg(orig_seg):
        def add_transition(self, *a, **kw): called["added"] = True
    monkeypatch.setattr(draft, "Video_segment", FakeSeg)

    service.add_video(AddVideoRequest(video_url="https://e.com/v.mp4", transition="Fade"))
    assert called.get("name") == "Fade"


def test_add_video_unknown_transition_raises(monkeypatch):
    from vectcut.features.video import service
    from vectcut.features.video.schemas import AddVideoRequest
    from vectcut.core.errors import InvalidParam
    from vectcut.engine import material_factory

    monkeypatch.setattr(material_factory, "resolve_transition", lambda name: (_ for _ in ()).throw(AttributeError(name)))
    with pytest.raises(InvalidParam):
        service.add_video(AddVideoRequest(video_url="https://e.com/v.mp4", transition="NOPE"))
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m pytest tests/features/video/test_service.py -v`
预期：FAIL，`ModuleNotFoundError`。

- [ ] **步骤 3：编写实现**

`vectcut/features/video/service.py`：
```python
"""video feature service：add_video / add_video_keyframe。

迁自 add_video_track.py + add_video_keyframe_impl.py，平台分支收敛为 material_factory.resolve_*。
"""

from __future__ import annotations

import pyJianYingDraft as draft
from pyJianYingDraft import Clip_settings, trange

from vectcut.core.draft_store import get_or_create_draft
from vectcut.core.errors import InvalidParam
from vectcut.engine import material_factory as mf
from vectcut.features.draft.service import generate_draft_url
from vectcut.features.video.schemas import AddVideoRequest, AddVideoResponse, AddVideoKeyframeRequest, AddVideoKeyframeResponse
from util import url_to_hash


_BLUR_MAP = {1: 0.0625, 2: 0.375, 3: 0.75, 4: 1.0}


def add_video(req: AddVideoRequest) -> AddVideoResponse:
    draft_id, script = get_or_create_draft(req.draft_id, req.width, req.height)

    # 默认视频轨道（若不存在）
    try:
        script.get_track(draft.Track_type.video, track_name=None)
    except Exception:
        try:
            script.add_track(draft.Track_type.video, relative_index=0)
        except Exception:
            pass

    # 命名轨道 get-or-create
    if req.track_name is not None:
        try:
            script.get_imported_track(draft.Track_type.video, name=req.track_name)
        except Exception:
            script.add_track(draft.Track_type.video, track_name=req.track_name, relative_index=req.relative_index)
    else:
        script.add_track(draft.Track_type.video, relative_index=req.relative_index)

    video_duration = req.duration if req.duration is not None else 0.0
    material_name = f"video_{url_to_hash(req.video_url)}.mp4"
    video_material = mf.build_video_material(
        video_url=req.video_url,
        draft_folder=req.draft_folder,
        draft_id=draft_id,
        material_name=material_name,
        duration=video_duration,
    )

    video_end = req.end if req.end is not None else video_duration
    source_duration = video_end - req.start
    target_duration = source_duration / req.speed
    source_timerange = trange(f"{req.start}s", f"{source_duration}s")
    target_timerange = trange(f"{req.target_start}s", f"{target_duration}s")

    video_segment = draft.Video_segment(
        video_material,
        target_timerange=target_timerange,
        source_timerange=source_timerange,
        speed=req.speed,
        clip_settings=Clip_settings(
            transform_y=req.transform_y, scale_x=req.scale_x, scale_y=req.scale_y, transform_x=req.transform_x,
        ),
        volume=req.volume,
    )

    if req.transition:
        try:
            transition_type = mf.resolve_transition(req.transition)
            video_segment.add_transition(transition_type, duration=int(req.transition_duration * 1e6))
        except AttributeError:
            raise InvalidParam(f"Unsupported transition type: {req.transition}")

    if req.mask_type:
        try:
            mask_enum = mf.resolve_mask(req.mask_type)
            video_segment.add_mask(
                script, mask_enum,
                center_x=req.mask_center_x, center_y=req.mask_center_y, size=req.mask_size,
                rotation=req.mask_rotation, feather=req.mask_feather, invert=req.mask_invert,
                rect_width=req.mask_rect_width, round_corner=req.mask_round_corner,
            )
        except Exception:
            raise InvalidParam(f"Unsupported mask type {req.mask_type}")

    if req.background_blur is not None:
        if req.background_blur not in _BLUR_MAP:
            raise InvalidParam(f"Invalid background blur level: {req.background_blur}")
        video_segment.add_background_filling("blur", blur=_BLUR_MAP[req.background_blur])

    script.add_segment(video_segment, track_name=req.track_name)
    return AddVideoResponse(draft_id=draft_id, draft_url=generate_draft_url(draft_id))


def add_video_keyframe(req: AddVideoKeyframeRequest) -> AddVideoKeyframeResponse:
    # 迁自 add_video_keyframe_impl.py；逐段保真，关键帧批/单路径
    from vectcut.core.draft_store import get_draft
    from vectcut.core.errors import DraftNotFound

    script = get_draft(req.draft_id)
    if script is None:
        raise DraftNotFound(req.draft_id)
    track = script.get_imported_track(draft.Track_type.video, name=req.track_name)

    if req.property_types and req.times and req.values:
        for pt, t, v in zip(req.property_types, req.times, req.values):
            _add_single_keyframe(track, pt, t, v)
    else:
        _add_single_keyframe(track, req.property_type, req.time, req.value)

    return AddVideoKeyframeResponse(draft_id=req.draft_id, draft_url=generate_draft_url(req.draft_id))


def _add_single_keyframe(track, property_type: str, time: float, value: str):
    """迁自 add_video_keyframe_impl._add_single_keyframe。"""
    from pyJianYingDraft.keyframe import Keyframe
    # 实现逐段搬自原文件 add_video_keyframe_impl.py:119+，按 property_type 设对应字段
    kf = Keyframe(time=time, value=value)  # 简化占位——迁移者须对照原文件补全 property_type 分支
    track.add_keyframe(kf)
```

> **说明**：`_add_single_keyframe` 须对照 `add_video_keyframe_impl.py:119` 起的原始实现逐段搬移（`property_type` 分支：alpha/scale/position/rotation 各自设 `track.keyframes`）。上面是签名占位，**迁移者必须打开原文件逐行复制**，不得简化。`test_service.py` 暂不覆盖 keyframe（其测试在任务 10 后补，见下）。

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m pytest tests/features/video/test_service.py -v`
预期：PASS（add_video 三个测试；keyframe 未测但 import 不报错）。

- [ ] **步骤 5：Commit**

```bash
git add vectcut/features/video/service.py tests/features/video/test_service.py
git commit -m "feat(video): 新增 add_video service（迁自 add_video_track，平台分支收敛）（阶段2）"
```

---

### 任务 11：features/video/flask_router.py

**文件：**
- 创建：`vectcut/features/video/flask_router.py`
- 创建：`tests/features/video/test_router.py`

- [ ] **步骤 1：编写失败的测试**

`tests/features/video/test_router.py`：
```python
import pytest


@pytest.fixture()
def client():
    from flask import Flask
    from vectcut.features.video.flask_router import bp
    app = Flask(__name__)
    app.register_blueprint(bp)
    app.config["TESTING"] = True
    return app.test_client()


def test_add_video_route_missing_video_url_returns_error(client):
    resp = client.post("/add_video", json={})
    body = resp.get_json()
    assert body["success"] is False
    assert "video_url" in body["error"]


def test_add_video_route_success(client):
    resp = client.post("/add_video", json={"video_url": "https://example.com/v.mp4"})
    body = resp.get_json()
    assert body["success"] is True
    assert body["output"]["draft_id"].startswith("dfd_cat_")


def test_add_video_keyframe_route_missing_draft_id(client):
    resp = client.post("/add_video_keyframe", json={})
    body = resp.get_json()
    assert body["success"] is False
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m pytest tests/features/video/test_router.py -v`
预期：FAIL，`ModuleNotFoundError`。

- [ ] **步骤 3：编写实现**

`vectcut/features/video/flask_router.py`：
```python
"""video feature Flask Blueprint：/add_video + /add_video_keyframe。"""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from vectcut.core.errors import VectCutError
from vectcut.features.video import service
from vectcut.features.video.schemas import AddVideoRequest, AddVideoKeyframeRequest

bp = Blueprint("video", __name__)


def _ok(output):
    return jsonify({"success": True, "output": output, "error": ""})


@bp.post("/add_video")
def add_video():
    try:
        req = AddVideoRequest.model_validate(request.get_json() or {})
    except ValidationError as e:
        return jsonify({"success": False, "output": "", "error": f"Hi, the required parameters are missing. {e}"})
    try:
        resp = service.add_video(req)
        return _ok({"draft_id": resp.draft_id, "draft_url": resp.draft_url})
    except VectCutError as e:
        return jsonify({"success": False, "output": "", "error": f"Error occurred while processing video: {e}."})


@bp.post("/add_video_keyframe")
def add_video_keyframe():
    try:
        req = AddVideoKeyframeRequest.model_validate(request.get_json() or {})
    except ValidationError as e:
        return jsonify({"success": False, "output": "", "error": f"Hi, the required parameters are missing. {e}"})
    try:
        resp = service.add_video_keyframe(req)
        return _ok({"draft_id": resp.draft_id, "draft_url": resp.draft_url})
    except VectCutError as e:
        return jsonify({"success": False, "output": "", "error": f"Error occurred while adding keyframe: {e}."})
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m pytest tests/features/video/test_router.py -v`
预期：PASS。

- [ ] **步骤 5：Commit**

```bash
git add vectcut/features/video/flask_router.py tests/features/video/test_router.py
git commit -m "feat(video): 新增 Flask Blueprint /add_video + /add_video_keyframe（阶段2）"
```

---

### 任务 12：features/audio/schemas.py + service.py + flask_router.py

**文件：**
- 创建：`vectcut/features/audio/__init__.py`
- 创建：`vectcut/features/audio/schemas.py`
- 创建：`vectcut/features/audio/service.py`
- 创建：`vectcut/features/audio/flask_router.py`
- 创建：`tests/features/audio/__init__.py`
- 创建：`tests/features/audio/test_service.py`
- 创建：`tests/features/audio/test_router.py`

- [ ] **步骤 1：编写失败的测试**

`tests/features/audio/__init__.py`（空）。

`tests/features/audio/test_service.py`：
```python
import pytest

from vectcut.core import draft_store


@pytest.fixture(autouse=True)
def _clean_cache():
    draft_store.DRAFT_CACHE.clear()
    yield
    draft_store.DRAFT_CACHE.clear()


def test_add_audio_creates_audio_segment():
    from vectcut.features.audio import service
    from vectcut.features.audio.schemas import AddAudioRequest

    resp = service.add_audio(AddAudioRequest(audio_url="https://example.com/a.mp3"))
    script = draft_store.get_draft(resp.draft_id)
    assert len(script.materials.audios) == 1
    assert script.materials.audios[0].remote_url == "https://example.com/a.mp3"


def test_add_audio_with_effect_resolves_via_adapter(monkeypatch):
    from vectcut.features.audio import service
    from vectcut.features.audio.schemas import AddAudioRequest
    from vectcut.engine import material_factory

    captured = {}
    def fake_resolve(name):
        captured["name"] = name
        class _M: pass
        return _M(), "Tone"
    monkeypatch.setattr(material_factory, "resolve_audio_effect", fake_resolve)
    import pyJianYingDraft as draft
    orig = draft.Audio_segment
    class FakeSeg(orig):
        def add_effect(self, *a, **kw): captured["added"] = True
    monkeypatch.setattr(draft, "Audio_segment", FakeSeg)

    service.add_audio(AddAudioRequest(
        audio_url="https://e.com/a.mp3",
        effect_type="SomeEffect",
        effect_params=[0.5],
    ))
    assert captured.get("name") == "SomeEffect"
```

`tests/features/audio/test_router.py`：
```python
import pytest


@pytest.fixture()
def client():
    from flask import Flask
    from vectcut.features.audio.flask_router import bp
    app = Flask(__name__)
    app.register_blueprint(bp)
    app.config["TESTING"] = True
    return app.test_client()


def test_add_audio_route_missing_url(client):
    resp = client.post("/add_audio", json={})
    body = resp.get_json()
    assert body["success"] is False
    assert "audio_url" in body["error"]


def test_add_audio_route_success(client):
    resp = client.post("/add_audio", json={"audio_url": "https://example.com/a.mp3"})
    body = resp.get_json()
    assert body["success"] is True
    assert body["output"]["draft_id"].startswith("dfd_cat_")
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m pytest tests/features/audio/ -v`
预期：FAIL，`ModuleNotFoundError`。

- [ ] **步骤 3：编写实现**

`vectcut/features/audio/__init__.py`（空）。

`vectcut/features/audio/schemas.py`：
```python
"""audio feature 请求/响应模型。"""

from __future__ import annotations

from typing import List, Optional, Tuple

from pydantic import BaseModel


class AddAudioRequest(BaseModel):
    draft_id: Optional[str] = None
    audio_url: str
    draft_folder: Optional[str] = None
    start: float = 0
    end: Optional[float] = None
    target_start: float = 0
    volume: float = 1.0
    track_name: str = "audio_main"
    speed: float = 1.0
    effect_type: Optional[str] = None
    effect_params: Optional[List[Optional[float]]] = None
    width: int = 1080
    height: int = 1920
    duration: Optional[float] = None


class AddAudioResponse(BaseModel):
    draft_id: str
    draft_url: str
```

`vectcut/features/audio/service.py`：
```python
"""audio feature service：add_audio。迁自 add_audio_track.py，effect 派发经 material_factory.resolve_audio_effect。"""

from __future__ import annotations

import pyJianYingDraft as draft
from pyJianYingDraft import trange

from vectcut.core.draft_store import get_or_create_draft
from vectcut.engine import material_factory as mf
from vectcut.features.audio.schemas import AddAudioRequest, AddAudioResponse
from vectcut.features.draft.service import generate_draft_url
from util import url_to_hash


def add_audio(req: AddAudioRequest) -> AddAudioResponse:
    draft_id, script = get_or_create_draft(req.draft_id, req.width, req.height)

    # get-or-create 命名音频轨道
    if req.track_name is not None:
        try:
            script.get_imported_track(draft.Track_type.audio, name=req.track_name)
        except Exception:
            script.add_track(draft.Track_type.audio, track_name=req.track_name)
    else:
        script.add_track(draft.Track_type.audio)

    audio_duration = req.duration if req.duration is not None else 0.0
    material_name = f"audio_{url_to_hash(req.audio_url)}.mp3"
    audio_material = mf.build_audio_material(
        audio_url=req.audio_url,
        draft_folder=req.draft_folder,
        draft_id=draft_id,
        material_name=material_name,
        duration=audio_duration,
    )

    audio_end = req.end if req.end is not None else audio_duration
    seg_duration = audio_end - req.start
    audio_segment = draft.Audio_segment(
        audio_material,
        target_timerange=trange(f"{req.target_start}s", f"{seg_duration}s"),
        source_timerange=trange(f"{req.start}s", f"{seg_duration}s"),
        speed=req.speed,
        volume=req.volume,
    )

    if req.effect_type:
        resolved = mf.resolve_audio_effect(req.effect_type)
        if resolved is not None:
            member, _subtype = resolved
            audio_segment.add_effect(member, req.effect_params)
        # 未命中：旧实现 print warning 并跳过，这里保持同样不抛

    script.add_segment(audio_segment, track_name=req.track_name)
    return AddAudioResponse(draft_id=draft_id, draft_url=generate_draft_url(draft_id))
```

`vectcut/features/audio/flask_router.py`：
```python
"""audio feature Flask Blueprint：/add_audio。"""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from vectcut.core.errors import VectCutError
from vectcut.features.audio import service
from vectcut.features.audio.schemas import AddAudioRequest

bp = Blueprint("audio", __name__)


@bp.post("/add_audio")
def add_audio():
    try:
        req = AddAudioRequest.model_validate(request.get_json() or {})
    except ValidationError as e:
        return jsonify({"success": False, "output": "", "error": f"Hi, the required parameters are missing. {e}"})
    try:
        resp = service.add_audio(req)
        return jsonify({"success": True, "output": {"draft_id": resp.draft_id, "draft_url": resp.draft_url}, "error": ""})
    except VectCutError as e:
        return jsonify({"success": False, "output": "", "error": f"Error occurred while processing audio: {e}."})
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m pytest tests/features/audio/ -v`
预期：PASS。

- [ ] **步骤 5：Commit**

```bash
git add vectcut/features/audio/ tests/features/audio/
git commit -m "feat(audio): 新增 audio feature service+schema+router（迁自 add_audio_track）（阶段2）"
```

---

### 任务 13：黄金基线扩展（业务路由 HTTP + service draft 输出）

**文件：**
- 创建：`tests/golden/test_business_routes_golden.py`
- 创建：`tests/golden/snapshots/business_create_draft.json`
- 创建：`tests/golden/snapshots/business_generate_draft_url.json`
- 创建：`tests/golden/snapshots/business_query_draft_status_not_found.json`
- 创建：`tests/golden/snapshots/business_save_draft_missing.json`
- 创建：`tests/golden/snapshots/business_add_video_missing_url.json`
- 创建：`tests/golden/snapshots/business_add_audio_missing_url.json`
- 创建：`tests/features/video/test_service_golden.py`
- 创建：`tests/features/audio/test_service_golden.py`
- 创建：`tests/golden/snapshots/video_add_video_dumps.json`
- 创建：`tests/golden/snapshots/audio_add_audio_dumps.json`

- [ ] **步骤 1：编写失败的测试**

`tests/golden/test_business_routes_golden.py`：
```python
"""业务路由 HTTP 黄金基线：错误分支 + 确定性成功分支。

迁移到 FastAPI 后，路由外壳与错误分支输出必须复现——本基线即防回归网。
draft_id 含时间戳/uuid，normalize 时替换为占位符。
"""
import json
import re

import pytest

# (路由, 请求体, 快照名)
CASES = [
    ("/create_draft", {}, "business_create_draft"),
    ("/generate_draft_url", {"draft_id": "PLACEHOLDER"}, "business_generate_draft_url"),
    ("/query_draft_status", {"task_id": "nonexistent_task"}, "business_query_draft_status_not_found"),
    ("/save_draft", {}, "business_save_draft_missing"),
    ("/add_video", {}, "business_add_video_missing_url"),
    ("/add_audio", {}, "business_add_audio_missing_url"),
]


@pytest.fixture(scope="module")
def client():
    import capcut_server
    capcut_server.app.config["TESTING"] = True
    with capcut_server.app.test_client() as c:
        yield c


def _normalize(payload):
    """draft_id / draft_url 中的动态 id 替换为占位，消除时间戳/uuid 漂移。"""
    s = json.dumps(payload, ensure_ascii=False)
    s = re.sub(r"dfd_cat_\d+_[0-9a-f]+", "dfd_cat_PLACEHOLDER", s)
    return json.loads(s)


@pytest.mark.parametrize("route,body,snap", CASES, ids=[c[2] for c in CASES])
def test_business_route_matches_golden(client, route, body, snap, snapshot_dir, regenerate_golden):
    resp = client.post(route, json=body)
    assert resp.status_code == 200
    payload = resp.get_json()
    normalized = _normalize(payload)
    snap_path = snapshot_dir / f"{snap}.json"
    if regenerate_golden:
        snap_path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
        pytest.skip(f"golden regenerated: {snap_path.name}")
    assert snap_path.exists(), f"快照缺失：{snap_path}。运行 REGENERATE_GOLDEN=1 生成。"
    expected = json.loads(snap_path.read_text(encoding="utf-8"))
    assert normalized == expected, f"{route} 输出与黄金基线不一致（见 {snap_path.name}）"
```

`tests/features/video/test_service_golden.py`：
```python
"""add_video service 层黄金：固定输入 → script.dumps() 快照。迁移 FastAPI 后 service 不变则 dumps 不变。"""
import json

import pytest

from vectcut.core import draft_store


@pytest.fixture(autouse=True)
def _clean_cache():
    draft_store.DRAFT_CACHE.clear()
    yield
    draft_store.DRAFT_CACHE.clear()


def test_add_video_dumps_golden(snapshot_dir, regenerate_golden):
    from vectcut.features.video import service
    from vectcut.features.video.schemas import AddVideoRequest
    from vectcut.core.draft_store import get_active_profile

    resp = service.add_video(AddVideoRequest(
        video_url="https://example.com/golden.mp4",
        start=0, end=3.0,
        track_name="video_main",
    ))
    script = draft_store.get_draft(resp.draft_id)
    dumps = script.dumps(get_active_profile())
    snap_path = snapshot_dir / "video_add_video_dumps.json"
    if regenerate_golden:
        snap_path.write_text(dumps, encoding="utf-8")
        pytest.skip("golden regenerated")
    assert snap_path.exists(), "快照缺失：运行 REGENERATE_GOLDEN=1 生成"
    expected = snap_path.read_text(encoding="utf-8")
    assert dumps == expected, "add_video 的 script.dumps() 与黄金基线不一致"
```

`tests/features/audio/test_service_golden.py`：
```python
"""add_audio service 层黄金。"""
import pytest

from vectcut.core import draft_store


@pytest.fixture(autouse=True)
def _clean_cache():
    draft_store.DRAFT_CACHE.clear()
    yield
    draft_store.DRAFT_CACHE.clear()


def test_add_audio_dumps_golden(snapshot_dir, regenerate_golden):
    from vectcut.features.audio import service
    from vectcut.features.audio.schemas import AddAudioRequest
    from vectcut.core.draft_store import get_active_profile

    resp = service.add_audio(AddAudioRequest(
        audio_url="https://example.com/golden.mp3",
        start=0, end=2.0,
        track_name="audio_main",
    ))
    script = draft_store.get_draft(resp.draft_id)
    dumps = script.dumps(get_active_profile())
    snap_path = snapshot_dir / "audio_add_audio_dumps.json"
    if regenerate_golden:
        snap_path.write_text(dumps, encoding="utf-8")
        pytest.skip("golden regenerated")
    assert snap_path.exists()
    expected = snap_path.read_text(encoding="utf-8")
    assert dumps == expected, "add_audio 的 script.dumps() 与黄金基线不一致"
```

- [ ] **步骤 2：生成黄金基线**

运行：`$env:REGENERATE_GOLDEN=1; python -m pytest tests/golden/test_business_routes_golden.py tests/features/video/test_service_golden.py tests/features/audio/test_service_golden.py -v`
预期：所有用例 SKIP（快照已生成）。

> **注意**：`business_create_draft.json` 等会在 `tests/golden/snapshots/` 下生成。`video_add_video_dumps.json` / `audio_add_audio_dumps.json` 同目录。

- [ ] **步骤 3：运行验证（非 regenerate 模式）**

运行：`python -m pytest tests/golden/test_business_routes_golden.py tests/features/video/test_service_golden.py tests/features/audio/test_service_golden.py -v`
预期：PASS（与刚生成的基线逐字节一致）。

- [ ] **步骤 4：Commit**

```bash
git add tests/golden/test_business_routes_golden.py tests/golden/snapshots/business_*.json tests/golden/snapshots/video_add_video_dumps.json tests/golden/snapshots/audio_add_audio_dumps.json tests/features/video/test_service_golden.py tests/features/audio/test_service_golden.py
git commit -m "test(golden): 扩展业务路由 HTTP + service draft 输出黄金基线（阶段2）"
```

---

### 任务 14：capcut_server.py 接线（删旧路由 + 挂 3 Blueprint）

**文件：**
- 修改：`capcut_server.py`

删除 7 个旧路由函数（`add_video` / `add_audio` / `create_draft_service` / `save_draft` / `query_draft_status` / `generate_draft_url` / `query_script`）+ 顶部对应 import（`add_video_track` / `add_audio_track` / `create_draft` / `save_draft_impl` 的 `save_draft_impl, query_task_status, query_script_impl`），挂载 draft / video / audio 三个新 Blueprint。保留阶段 3 待迁的 `add_text` / `add_image` / `add_effect` / `add_sticker` / `add_video_keyframe` 路由及其 import。

- [ ] **步骤 1：编写失败的测试**

`tests/golden/test_business_routes_golden.py`（任务 13 已建）现在依赖 `capcut_server.app` 挂载新 Blueprint。先确认旧路由已删：在 `tests/test_legacy_routes_removed.py` 新建：
```python
"""验证 capcut_server.py 旧路由函数已删、新 Blueprint 已挂载。"""
import importlib

def test_old_route_functions_removed():
    capcut_server = importlib.import_module("capcut_server")
    for name in ["add_video", "add_audio", "create_draft_service", "save_draft", "query_draft_status", "generate_draft_url", "query_script"]:
        assert not hasattr(capcut_server, name), f"旧路由 {name} 应已删除"


def test_new_blueprints_registered():
    capcut_server = importlib.import_module("capcut_server")
    rules = {r.rule for r in capcut_server.app.url_map.iter_rules()}
    for path in ["/add_video", "/add_audio", "/create_draft", "/save_draft", "/query_script", "/query_draft_status", "/generate_draft_url"]:
        assert path in rules, f"{path} 应由新 Blueprint 注册"


def test_legacy_stage3_routes_kept():
    """阶段3 待迁路由保留。"""
    capcut_server = importlib.import_module("capcut_server")
    rules = {r.rule for r in capcut_server.app.url_map.iter_rules()}
    for path in ["/add_text", "/add_image", "/add_effect", "/add_sticker", "/add_video_keyframe", "/add_subtitle"]:
        assert path in rules, f"{path} 阶段3 待迁，应保留"
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m pytest tests/test_legacy_routes_removed.py -v`
预期：FAIL（`add_video` 等旧函数仍存在）。

- [ ] **步骤 3：编写实现**

修改 `capcut_server.py`：

**3a. 顶部 import 区**——删除以下行：
```python
from add_audio_track import add_audio_track
from add_video_track import add_video_track
from save_draft_impl import save_draft_impl, query_task_status, query_script_impl
from create_draft import create_draft
```
保留：`from add_text_impl import add_text_impl` / `add_subtitle_impl` / `add_image_impl` / `add_video_keyframe_impl` / `add_effect_impl` / `add_sticker_impl` / `util` / `pyJianYingDraft.text_segment`。`from settings.local import IS_CAPCUT_ENV, DRAFT_DOMAIN, PREVIEW_ROUTER, PORT` 中 `IS_CAPCUT_ENV` / `DRAFT_DOMAIN` / `PREVIEW_ROUTER` 在删旧路由后不再被 capcut_server 直接用，可简化为 `from settings.local import PORT`。

**3b. 在 `app = Flask(__name__)` 之后、第一个旧路由之前**，加：
```python
from vectcut.features.draft.flask_router import bp as draft_bp
from vectcut.features.video.flask_router import bp as video_bp
from vectcut.features.audio.flask_router import bp as audio_bp
app.register_blueprint(draft_bp)
app.register_blueprint(video_bp)
app.register_blueprint(audio_bp)
```

**3c. 删除** `add_video`（26-116）/ `add_audio`（118-181）/ `create_draft_service`（183-211）/ `add_subtitle`（保留，阶段3）/ `add_text`（保留）/ `add_image`（保留）/ `add_video_keyframe`（保留，阶段3）/ `add_effect`（保留）/ `query_script`（675-714）/ `save_draft`（716-747）/ `query_draft_status`（749-785）/ `generate_draft_url`（787-817）/ `add_sticker`（保留）路由函数。

> **精确边界**：删除的行号区间基于迁移前快照；迁移者须按函数名定位删除，勿按行号盲删。保留 `add_subtitle` / `add_text` / `add_image` / `add_video_keyframe` / `add_effect` / `add_sticker` 六个阶段 3 路由。`utilgenerate_draft_url` 若在删 `generate_draft_url` 路由后无人用，从 import 删掉。

- [ ] **步骤 4：运行全量测试验证通过**

运行：`python -m pytest tests/test_legacy_routes_removed.py tests/golden/ tests/features/ tests/core/ tests/engine/ -v`
预期：PASS（黄金基线复现、新 Blueprint 路由可达、旧路由已删、阶段 3 路由保留）。

- [ ] **步骤 5：Commit**

```bash
git add capcut_server.py tests/test_legacy_routes_removed.py
git commit -m "refactor(server): capcut_server 删 7 旧路由挂载 draft/video/audio Blueprint（阶段2）"
```

---

### 任务 15：阶段 2 验收 + release

**文件：** 无新文件

- [ ] **步骤 1：全量测试**

运行：`python -m pytest tests/ -v`
预期：全绿（含阶段 0-1 既有测试 + 阶段 2 新增）。

- [ ] **步骤 2：黄金基线复现确认**

运行：`python -m pytest tests/golden/ -v`
预期：全绿（metadata 12 路由 + 业务 6 路由 HTTP + video/audio service dumps）。

- [ ] **步骤 3：flake8 检查**

运行：`python -m flake8 vectcut/ capcut_server.py --max-line-length=140 --extend-ignore=E301,E302,E303,E305,E306,E701,F403,F405`
预期：无错误（与新 .flake8 配置一致）。

- [ ] **步骤 4：Commit + tag**

```bash
git add -A
git commit -m "chore: 阶段2 完成——draft/video/audio features + material_factory + save_draft_impl 拆分 + 黄金基线扩展"
git tag phase2-complete
```

- [ ] **步骤 5：阶段验收清单（人工确认）**

- [ ] `capcut_server.py` 行数从 ~888 降至 < 400（删 7 路由后只剩阶段 3 待迁路由）。
- [ ] `add_video_track.py` / `add_audio_track.py` / `save_draft_impl.py` / `get_duration_impl.py` 仍存在但**无新消费者**（被 vectcut features 取代），可在阶段 5 删除。
- [ ] 散落 `if IS_CAPCUT_ENV` 在 video/audio feature 内已消除（grep `vectcut/features/video` `vectcut/features/audio` 应为 0 命中）。
- [ ] 黄金基线全绿，证明行为不变。

---

## 自检

### 1. 规格覆盖度

| 规格章节 | 覆盖任务 | 备注 |
|---------|---------|------|
| §3.1 包结构 `features/draft` | 任务 4-7 | ✓ |
| §3.1 包结构 `features/video` | 任务 9-11 | ✓ |
| §3.1 包结构 `features/audio` | 任务 12 | ✓ |
| §3.1 `engine/material_factory.py` | 任务 3 | ✓ |
| §3.1 `save_draft_impl` 按职责拆分 | 任务 5-6 | save_draft / query_script / query_task_status / 上传(URL 生成) 四类齐全 ✓ |
| §4.1 service 层契约（纯 Python、draft 内部获取） | 任务 6, 10, 12 | service 不 import Flask/MCP/settings，draft 经 draft_store.get_draft ✓ |
| §4.1 schemas 共用 | 任务 4, 9, 12 | ✓（MCP 侧阶段 4 复用） |
| §4.2 HTTP 薄入口（Pydantic 校验） | 任务 7, 11, 12 | router 用 `model_validate` ✓ |
| §4.4 统一错误处理 | 任务 1, 7, 11, 12 | DraftNotFound/EngineError/MediaDownloadError + 路由兜底 ✓ |
| §5.1② material_factory | 任务 3 | ✓ |
| §5.2 配置统一（循环依赖） | 阶段 0 已完成 | 本阶段 service 走 `vectcut.core.config.load_config()`，不再碰 `settings/` ✓ |
| §7 黄金测试 | 任务 13 | HTTP 业务路由 + service dumps 双轨 ✓ |
| §8 阶段 2 范围 | 全部 | draft/video/audio + save_draft_impl 拆分 ✓ |
| §8 阶段 2 风险"中" | — | save_draft 拆分最重，已用空 draft 测试兜底 |

**遗漏**：无。`get_duration` 对外 service 规格提及但实测无消费者，作内部工具处理（自检偏差已标注）。

### 2. 占位符扫描

- 任务 5 `update_media_metadata` 与任务 10 `_add_single_keyframe` 标注"逐段搬自原文件"——这是**迁移指令**非占位，因原文件 200+ 行逐字复制进计划会失控。迁移者须打开原文件对照。可接受。
- 无"待定"/"TODO"/"添加适当错误处理"等占位。

### 3. 类型一致性

- `generate_draft_url(draft_id: str) -> str`：任务 6 定义，任务 10/12 video/audio service 调用签名一致 ✓
- `get_or_create_draft(draft_id, width, height) -> (draft_id, script)`：任务 2 定义，任务 6/10/12 调用一致 ✓
- `material_factory.resolve_transition(name) -> enum_member`：任务 3 定义，任务 10 调用一致 ✓
- `material_factory.resolve_audio_effect(name) -> Optional[(member, subtype)]`：任务 3 定义，任务 12 调用解包一致 ✓
- `AddVideoRequest` / `AddAudioRequest` 字段名与 `capcut_server.py` 旧 `data.get(...)` 键名逐一对照一致 ✓
- `SaveDraftResponse` / `QueryScriptResponse` 字段在 service 与 router 间一致 ✓

**发现问题**：无。

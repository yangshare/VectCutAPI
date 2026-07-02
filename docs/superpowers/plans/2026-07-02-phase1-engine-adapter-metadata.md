# 阶段 1：Engine 适配层 + 元数据收敛 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 收敛 `capcut_server.py` 顶部散落的 17 行 `pyJianYingDraft.metadata.*` / `capcut_*` import 到 `vectcut/engine/adapter.py`，按平台派发枚举；把 11 个近乎复制的 `get_xxx_types` 路由收敛为声明式注册表 + 一个参数化路由 `GET /metadata/{kind}`，同时保留 11 个旧具名路径作别名；整个过程**不迁 Flask→FastAPI**（那是阶段 4），黄金基线必须全程保持绿色。

**架构：** `engine/adapter.py` 集中所有引擎枚举 import，对外提供 `active_platform()`（读 `draft_store.get_active_profile().is_capcut_env`）与 `enum_for(kind)`（返回当前平台的枚举类，font 无 CapCut 变体时两平台共用 `Font_type`）。`features/metadata/registry.py` 用 `META_KINDS = { kind: (描述, getter) }` 声明 11 种 kind，getter 接收 adapter 返回的枚举、产出最终 output 列表——简单 kind 产 `[{name}]`，`audio_effect` 产 `[{name, type, params:[...]}]`（params ×100 缩放与 3 子枚举逻辑搬入 getter）。`features/metadata/service.py` 的 `list_metadata(kind)` 调 getter，`KeyError → InvalidParam`。`features/metadata/flask_router.py` 提供 Flask `Blueprint`：`GET /metadata/{kind}` + 11 个旧别名，全部委托 service。`capcut_server.py` 删掉 11 个旧路由函数与顶部散落 import，挂载该 Blueprint。

**技术栈：** Flask（本阶段仍用，FastAPI 迁移在阶段 4）、Pydantic（service 异常类型基类）、`vectcut.core.draft_store`（阶段 0 产物）、阶段 0 黄金快照（防回归网）。

**前置依赖：** 阶段 0 全绿出 release。`vectcut.core.draft_store.get_active_profile()` 与 `tests/golden/snapshots/metadata_*.json` 必须已就位。

**本阶段不触碰：** `pyJianYingDraft/` 内部（只读）；各 `add_*` / `save_draft_impl` 业务实现；HTTP 框架（仍 Flask）；MCP 侧。

**与规格的偏差（已在自检标注）：**
- 规格 §8 阶段 1 含 `material_factory.py`，但它的消费者（`add_video_track`/`add_audio_track` 等）要到阶段 2-3 才迁移。无消费者时建工厂违反 YAGNI 且无法 TDD，故 `material_factory` **延后到阶段 2** 与 video feature 一同落地。本阶段只交付 `adapter.py` + 元数据收敛。
- 规格 §5.3 称"14 个 get_xxx_types"，实测 11 个具名路由（阶段 0 已修正）。

---

## 文件结构

| 文件 | 职责 | 动作 |
|------|------|------|
| `vectcut/engine/__init__.py` | engine 子包标记 | 创建 |
| `vectcut/engine/adapter.py` | 收敛引擎枚举 import + `active_platform()` + `enum_for(kind)` + `META_KINDS` 枚举映射表 | 创建 |
| `vectcut/core/errors.py` | 业务异常基类 + 错误码（规格 §4.4，本阶段只需 `InvalidParam`，余者在阶段 2-4 按需补） | 创建 |
| `vectcut/features/__init__.py` | features 子包标记 | 创建 |
| `vectcut/features/metadata/__init__.py` | metadata feature 包标记 | 创建 |
| `vectcut/features/metadata/registry.py` | `META_KINDS = { kind: (desc, getter) }` 声明式注册表 | 创建 |
| `vectcut/features/metadata/service.py` | `list_metadata(kind) -> list[dict]`；`KeyError → InvalidParam` | 创建 |
| `vectcut/features/metadata/flask_router.py` | Flask Blueprint：`GET /metadata/{kind}` + 11 旧别名；统一 `{success,output,error}` 外壳 | 创建 |
| `capcut_server.py` | 删 11 个 `get_xxx_types` 路由函数（~330 行）+ 顶部 17 行散落引擎 import；挂载 metadata Blueprint | 修改 |
| `tests/engine/test_adapter.py` | adapter 平台派发单测 | 创建 |
| `tests/features/__init__.py`、`tests/features/metadata/__init__.py`、`tests/engine/__init__.py` | 包标记 | 创建 |
| `tests/features/metadata/test_registry_service.py` | 注册表 + service 单测（含 audio_effect 富结构、font 无 CapCut 变体） | 创建 |
| `tests/features/metadata/test_flask_router.py` | Blueprint 路由测试：新参数化路由 + 11 旧别名等价性 | 创建 |
| `tests/golden/test_metadata_routes_golden.py` | 阶段 0 既有黄金测试，本阶段必须保持绿（收敛后输出不变） | 不改 |
| `tests/golden/snapshots/metadata_*.json` | 阶段 0 既有快照 | 不改 |

**关键设计决策：**
- **getter 接收枚举、产出最终 output**：而非 adapter 统一返回"成员列表"。因为 `audio_effect` 的 item 形态（含 `type` 标签与 ×100 缩放的 params）与简单 kind 完全不同，把 shaping 放进 adapter 会让 adapter 知道太多业务细节。adapter 只管"哪个枚举类属于哪个 kind/平台"，getter 管"怎么渲染成 API 输出"——职责干净。
- **font 无 CapCut 变体**：`enum_for("font")` 在两平台都返回 `Font_type`。registry 的 font getter 不关心平台。
- **旧别名路由复用同一 service**：11 个 `/get_xxx_types` 旧路径与新 `/metadata/{kind}` 都调 `list_metadata(kind)`，输出外壳一致 `{success, output, error}`，与现有黄金快照逐字节可比。
- **Flask Blueprint 而非 FastAPI**：HTTP 框架迁移是阶段 4。本阶段在现有 Flask app 上挂 Blueprint，阶段 4 再把同一 service 接到 FastAPI router（service 是纯 Python，不依赖 Flask）。
- **`core/errors.py` 提前建最小版**：`InvalidParam` 本阶段就要用（service 抛、路由转 422-ish）。完整异常体系（`DraftNotFound`/`EngineError`/`MediaDownloadError`）阶段 2-4 按需补，YAGNI。

---

### 任务 1：core/errors.py — 最小异常基类 + InvalidParam

**文件：**
- 创建：`vectcut/core/errors.py`
- 创建：`tests/core/test_errors.py`

- [ ] **步骤 1：编写失败的测试**

`tests/core/test_errors.py`：
```python
def test_invalid_param_carries_message_and_code():
    from vectcut.core.errors import InvalidParam, VectCutError

    err = InvalidParam("kind must be one of registered kinds")
    assert isinstance(err, VectCutError)
    assert err.code == "INVALID_PARAM"
    assert "kind must be" in str(err)


def test_invalid_param_default_http_status():
    from vectcut.core.errors import InvalidParam

    assert InvalidParam("x").http_status == 422
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m pytest tests/core/test_errors.py -v`
预期：FAIL，`ModuleNotFoundError: No module named 'vectcut.core.errors'`。

- [ ] **步骤 3：编写实现**

`vectcut/core/errors.py`：
```python
"""统一业务异常基类 + 错误码。

阶段 1 只需 InvalidParam（metadata service 用）。DraftNotFound / EngineError /
MediaDownloadError 在阶段 2-4 引入对应 feature 时按需添加（YAGNI）。
错误码与 HTTP/JSON-RPC 映射见规格 §4.4 表。
"""

from __future__ import annotations


class VectCutError(Exception):
    """业务异常基类。子类声明 code（字符串错误码）与 http_status。"""

    code: str = "VECTCUT_ERROR"
    http_status: int = 500


class InvalidParam(VectCutError):
    """参数非法（未知 kind、end<=start 等）。HTTP 422 / JSON-RPC -32002。"""

    code = "INVALID_PARAM"
    http_status = 422
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m pytest tests/core/test_errors.py -v`
预期：2 项 PASS。

- [ ] **步骤 5：Commit**

```bash
git add vectcut/core/errors.py tests/core/test_errors.py
git commit -m "feat(core): 新增统一异常基类与 InvalidParam"
```

---

### 任务 2：engine/adapter.py — 收敛引擎枚举 import + 平台派发（TDD）

**文件：**
- 创建：`vectcut/engine/__init__.py`、`vectcut/engine/adapter.py`
- 创建：`tests/engine/__init__.py`、`tests/engine/test_adapter.py`

**说明：** 把 `capcut_server.py:5-17` 的 17 行散落 import 收敛到此处。`enum_for(kind)` 返回当前激活平台对应的枚举**类**（不是成员列表）——registry getter 负责遍历成员。font 在两平台都用 `Font_type`（无 CapCut 变体）。audio_effect 涉及 3 组枚举对，由 `enum_for` 返回一个**字典** `{"Voice_filters":..., "Voice_characters":..., "Speech_to_song":...}`（CapCut）/ `{"Tone":..., "Audio_scene":..., "Speech_to_song":...}`（剪映），registry getter 据此构造富结构。

- [ ] **步骤 1：编写失败的测试**

`tests/engine/test_adapter.py`：
```python
import pytest


def test_active_platform_reflects_config_profile(monkeypatch):
    """active_platform() 读 draft_store.get_active_profile().is_capcut_env。"""
    from vectcut.engine import adapter
    from vectcut.core import draft_store

    class FakeProfile:
        is_capcut_env = True

    monkeypatch.setattr(draft_store, "get_active_profile", lambda: FakeProfile())
    assert adapter.active_platform() == "capcut"

    class FakeProfile2:
        is_capcut_env = False

    monkeypatch.setattr(draft_store, "get_active_profile", lambda: FakeProfile2())
    assert adapter.active_platform() == "jianying"


def test_enum_for_simple_kind_returns_platform_enum(monkeypatch):
    from vectcut.engine import adapter
    from pyJianYingDraft.metadata.animation_meta import Intro_type
    from pyJianYingDraft.metadata.capcut_animation_meta import CapCut_Intro_type

    monkeypatch.setattr(adapter, "active_platform", lambda: "capcut")
    assert adapter.enum_for("intro_animation") is CapCut_Intro_type

    monkeypatch.setattr(adapter, "active_platform", lambda: "jianying")
    assert adapter.enum_for("intro_animation") is Intro_type


def test_enum_for_font_has_no_capcut_variant_returns_same_on_both_platforms(monkeypatch):
    from vectcut.engine import adapter
    from pyJianYingDraft.metadata.font_meta import Font_type

    monkeypatch.setattr(adapter, "active_platform", lambda: "capcut")
    assert adapter.enum_for("font") is Font_type

    monkeypatch.setattr(adapter, "active_platform", lambda: "jianying")
    assert adapter.enum_for("font") is Font_type


def test_enum_for_audio_effect_returns_subtype_dict(monkeypatch):
    from vectcut.engine import adapter

    monkeypatch.setattr(adapter, "active_platform", lambda: "capcut")
    cap = adapter.enum_for("audio_effect")
    assert set(cap.keys()) == {"Voice_filters", "Voice_characters", "Speech_to_song"}

    monkeypatch.setattr(adapter, "active_platform", lambda: "jianying")
    jy = adapter.enum_for("audio_effect")
    assert set(jy.keys()) == {"Tone", "Audio_scene", "Speech_to_song"}


def test_enum_for_unknown_kind_raises():
    from vectcut.engine import adapter

    with pytest.raises(KeyError):
        adapter.enum_for("nope_kind")
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m pytest tests/engine/test_adapter.py -v`
预期：FAIL，`ModuleNotFoundError: No module named 'vectcut.engine'`。

- [ ] **步骤 3：编写实现**

`vectcut/engine/__init__.py`（空）：
```python
"""对只读 pyJianYingDraft 的薄适配层。"""
```

`vectcut/engine/adapter.py`：
```python
"""收敛引擎枚举 import + 按平台派发。

应用层只有本模块直接 import pyJianYingDraft.metadata.*。
业务/元数据接口只调 enum_for(kind)，消除散落的 if IS_CAPCUT_ENV（规格 §5.1①）。
"""

from __future__ import annotations

from typing import Dict

# —— 收敛 capcut_server.py:5-17 的散落 import ——
from pyJianYingDraft.metadata.animation_meta import (
    Intro_type,
    Outro_type,
    Group_animation_type,
    Text_intro,
    Text_outro,
    Text_loop_anim,
)
from pyJianYingDraft.metadata.capcut_animation_meta import (
    CapCut_Intro_type,
    CapCut_Outro_type,
    CapCut_Group_animation_type,
    CapCut_Text_intro,
    CapCut_Text_outro,
    CapCut_Text_loop_anim,
)
from pyJianYingDraft.metadata.transition_meta import Transition_type
from pyJianYingDraft.metadata.capcut_transition_meta import CapCut_Transition_type
from pyJianYingDraft.metadata.mask_meta import Mask_type
from pyJianYingDraft.metadata.capcut_mask_meta import CapCut_Mask_type
from pyJianYingDraft.metadata.audio_effect_meta import (
    Tone_effect_type,
    Audio_scene_effect_type,
    Speech_to_song_type,
)
from pyJianYingDraft.metadata.capcut_audio_effect_meta import (
    CapCut_Voice_filters_effect_type,
    CapCut_Voice_characters_effect_type,
    CapCut_Speech_to_song_effect_type,
)
from pyJianYingDraft.metadata.font_meta import Font_type
from pyJianYingDraft.metadata.video_effect_meta import (
    Video_scene_effect_type,
    Video_character_effect_type,
)
from pyJianYingDraft.metadata.capcut_effect_meta import (
    CapCut_Video_scene_effect_type,
    CapCut_Video_character_effect_type,
)


# kind -> (capcut_enum_or_dict, jianying_enum_or_dict)
# font 无 CapCut 变体，两平台共用 Font_type。
# audio_effect 返回 {子类型标签: 枚举} 字典，由 registry getter 展开为富结构。
_ENUM_MAP: Dict[str, tuple] = {
    "intro_animation": (CapCut_Intro_type, Intro_type),
    "outro_animation": (CapCut_Outro_type, Outro_type),
    "combo_animation": (CapCut_Group_animation_type, Group_animation_type),
    "transition": (CapCut_Transition_type, Transition_type),
    "mask": (CapCut_Mask_type, Mask_type),
    "audio_effect": (
        {  # capcut
            "Voice_filters": CapCut_Voice_filters_effect_type,
            "Voice_characters": CapCut_Voice_characters_effect_type,
            "Speech_to_song": CapCut_Speech_to_song_effect_type,
        },
        {  # jianying
            "Tone": Tone_effect_type,
            "Audio_scene": Audio_scene_effect_type,
            "Speech_to_song": Speech_to_song_type,
        },
    ),
    "font": (Font_type, Font_type),  # 无 CapCut 变体
    "text_intro": (CapCut_Text_intro, Text_intro),
    "text_outro": (CapCut_Text_outro, Text_outro),
    "text_loop_anim": (CapCut_Text_loop_anim, Text_loop_anim),
    "video_scene_effect": (CapCut_Video_scene_effect_type, Video_scene_effect_type),
    "video_character_effect": (CapCut_Video_character_effect_type, Video_character_effect_type),
}


def active_platform() -> str:
    """返回 'capcut' 或 'jianying'，读 draft_store 激活 profile。"""
    from vectcut.core.draft_store import get_active_profile

    return "capcut" if get_active_profile().is_capcut_env else "jianying"


def enum_for(kind: str):
    """返回当前平台对应 kind 的枚举类（audio_effect 返回 {子类型: 枚举} 字典）。

    未知 kind 抛 KeyError（由 service 转 InvalidParam）。
    """
    if kind not in _ENUM_MAP:
        raise KeyError(kind)
    cap, jy = _ENUM_MAP[kind]
    return cap if active_platform() == "capcut" else jy
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m pytest tests/engine/test_adapter.py -v`
预期：5 项 PASS。

- [ ] **步骤 5：Commit**

```bash
git add vectcut/engine/ tests/engine/
git commit -m "feat(engine): 新增 adapter 收敛引擎枚举 import 并按平台派发"
```

---

### 任务 3：features/metadata/registry.py + service.py — 声明式注册表（TDD）

**文件：**
- 创建：`vectcut/features/__init__.py`、`vectcut/features/metadata/__init__.py`
- 创建：`vectcut/features/metadata/registry.py`
- 创建：`vectcut/features/metadata/service.py`
- 创建：`tests/features/__init__.py`、`tests/features/metadata/__init__.py`
- 创建：`tests/features/metadata/test_registry_service.py`

**说明：** registry 持 `META_KINDS = { kind: (描述, getter) }`。getter 接收 `enum_for(kind)` 的返回值（枚举类或字典），产出最终 output 列表。简单 kind 的 getter 产 `[{"name": m.name}]`；audio_effect 的 getter 遍历子类型字典，产 `[{name, type, params:[{name, default_value, min_value, max_value}]}]`（params ×100，逐字搬自 `capcut_server.py:1084-1216`）。service `list_metadata(kind)` 查表调 getter，未知 kind 抛 `InvalidParam`。

- [ ] **步骤 1：编写失败的测试**

`tests/features/metadata/test_registry_service.py`：
```python
import pytest


def test_list_metadata_simple_kind_returns_name_only_items(monkeypatch):
    from vectcut.features.metadata import service
    from pyJianYingDraft.metadata.animation_meta import Intro_type

    # 不依赖平台：直接验证 simple getter 形态
    items = service.list_metadata("intro_animation", enum=Intro_type)
    assert items and all(set(i.keys()) == {"name"} for i in items)
    assert all(i["name"] for i in items)


def test_list_metadata_audio_effect_rich_shape_with_params(monkeypatch):
    from vectcut.features.metadata import service
    from vectcut.engine import adapter
    from pyJianYingDraft.metadata.audio_effect_meta import Tone_effect_type

    items = service.list_metadata(
        "audio_effect", enum={"Tone": Tone_effect_type, "Audio_scene": type(None), "Speech_to_song": type(None)}
    )
    tone_items = [i for i in items if i["type"] == "Tone"]
    assert tone_items, "Tone 子类型应被展开"
    sample = tone_items[0]
    assert set(sample.keys()) == {"name", "type", "params"}
    if sample["params"]:
        p = sample["params"][0]
        assert set(p.keys()) == {"name", "default_value", "min_value", "max_value"}


def test_list_metadata_unknown_kind_raises_invalid_param():
    from vectcut.features.metadata import service
    from vectcut.core.errors import InvalidParam

    with pytest.raises(InvalidParam):
        service.list_metadata("nope")


def test_list_metadata_default_uses_adapter_enum_for(monkeypatch):
    """不传 enum 时，service 走 adapter.enum_for(kind) + active_platform。"""
    from vectcut.features.metadata import service
    from vectcut.engine import adapter
    from pyJianYingDraft.metadata.font_meta import Font_type

    monkeypatch.setattr(adapter, "enum_for", lambda kind: Font_type)
    items = service.list_metadata("font")
    assert items and all(set(i.keys()) == {"name"} for i in items)


def test_registry_covers_all_11_kinds():
    from vectcut.features.metadata.registry import META_KINDS

    expected = {
        "intro_animation", "outro_animation", "combo_animation", "transition",
        "mask", "audio_effect", "font", "text_intro", "text_outro",
        "text_loop_anim", "video_scene_effect", "video_character_effect",
    }
    assert set(META_KINDS.keys()) == expected
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m pytest tests/features/metadata/test_registry_service.py -v`
预期：FAIL，`ModuleNotFoundError: No module named 'vectcut.features'`。

- [ ] **步骤 3：编写 registry 实现**

`vectcut/features/__init__.py`（空）：
```python
"""业务能力，按剪辑领域分包。"""
```
`vectcut/features/metadata/__init__.py`（空）：
```python
"""元数据查询 feature。"""
```

`vectcut/features/metadata/registry.py`：
```python
"""元数据声明式注册表：kind -> (描述, getter)。

getter(enum_value) 接收 adapter.enum_for(kind) 的返回值（枚举类 或 {子类型: 枚举} 字典），
产出最终 output 列表。新增一种枚举只加一行（规格 §5.3）。
"""

from __future__ import annotations

from typing import Callable, Dict, Tuple


def _simple_items(enum_cls) -> list:
    """简单 kind：[{name: member.name}]，与旧 get_xxx_types 输出一致。"""
    return [{"name": name} for name, _ in enum_cls.__members__.items()]


def _audio_effect_items(subtype_to_enum: dict) -> list:
    """audio_effect 富结构：[{name, type, params:[{name, default_value, min_value, max_value}]}]。

    params ×100 缩放，逐字搬自 capcut_server.py:1084-1216 旧实现，保证黄金快照保真。
    """
    items = []
    for subtype, enum_cls in subtype_to_enum.items():
        for name, member in enum_cls.__members__.items():
            params_info = []
            for param in member.value.params:
                params_info.append({
                    "name": param.name,
                    "default_value": param.default_value * 100,
                    "min_value": param.min_value * 100,
                    "max_value": param.max_value * 100,
                })
            items.append({"name": name, "type": subtype, "params": params_info})
    return items


# kind -> (人类描述, getter)
META_KINDS: Dict[str, Tuple[str, Callable]] = {
    "intro_animation":         ("入场动画",        _simple_items),
    "outro_animation":         ("出场动画",        _simple_items),
    "combo_animation":         ("组合动画",        _simple_items),
    "transition":              ("转场",            _simple_items),
    "mask":                    ("蒙版",            _simple_items),
    "audio_effect":            ("音频效果",        _audio_effect_items),
    "font":                    ("字体",            _simple_items),
    "text_intro":              ("文本入场动画",    _simple_items),
    "text_outro":              ("文本出场动画",    _simple_items),
    "text_loop_anim":          ("文本循环动画",    _simple_items),
    "video_scene_effect":      ("视频场景特效",    _simple_items),
    "video_character_effect":  ("视频人物特效",    _simple_items),
}
```

- [ ] **步骤 4：编写 service 实现**

`vectcut/features/metadata/service.py`：
```python
"""list_metadata(kind) —— 元数据查询 service（纯 Python，不依赖 web 框架）。

未知 kind -> InvalidParam（规格 §5.3 / §4.4）。
"""

from __future__ import annotations

from typing import Optional

from vectcut.core.errors import InvalidParam
from vectcut.engine import adapter
from vectcut.features.metadata.registry import META_KINDS


def list_metadata(kind: str, enum=None) -> list:
    """返回 kind 对应的 output 列表。

    enum 形参仅供测试注入；生产路径走 adapter.enum_for(kind)。
    """
    if kind not in META_KINDS:
        raise InvalidParam(f"Unknown metadata kind: {kind}. Supported: {sorted(META_KINDS)}")
    _, getter = META_KINDS[kind]
    if enum is None:
        enum = adapter.enum_for(kind)
    return getter(enum)
```

- [ ] **步骤 5：运行测试验证通过**

运行：`python -m pytest tests/features/metadata/test_registry_service.py -v`
预期：5 项 PASS。

- [ ] **步骤 6：Commit**

```bash
git add vectcut/features/ tests/features/
git commit -m "feat(metadata): 新增元数据声明式注册表与 list_metadata service"
```

---

### 任务 4：features/metadata/flask_router.py — 参数化路由 + 11 旧别名（TDD）

**文件：**
- 创建：`vectcut/features/metadata/flask_router.py`
- 创建：`tests/features/metadata/test_flask_router.py`

**说明：** Flask `Blueprint`。`GET /metadata/{kind}` 调 service，输出统一外壳 `{success, output, error}`（与旧路由逐字节同形）。11 个旧具名路径作为别名，循环注册，每个映射到对应 kind。异常用 `try/except` 兜底（沿用旧路由的外壳错误格式，阶段 4 FastAPI 化时再接全局 exception handler）。

kind → 旧路径别名映射（与 `capcut_server.py` 实测一致）：
```
intro_animation        -> /get_intro_animation_types
outro_animation        -> /get_outro_animation_types
combo_animation        -> /get_combo_animation_types
transition             -> /get_transition_types
mask                   -> /get_mask_types
audio_effect           -> /get_audio_effect_types
font                   -> /get_font_types
text_intro             -> /get_text_intro_types
text_outro             -> /get_text_outro_types
text_loop_anim         -> /get_text_loop_anim_types
video_scene_effect     -> /get_video_scene_effect_types
video_character_effect -> /get_video_character_effect_types
```

- [ ] **步骤 1：编写失败的测试**

`tests/features/metadata/test_flask_router.py`：
```python
import pytest


@pytest.fixture()
def client():
    from flask import Flask
    from vectcut.features.metadata.flask_router import bp

    app = Flask(__name__)
    app.register_blueprint(bp)
    app.config["TESTING"] = True
    return app.test_client()


def test_parameterized_route_returns_success_envelope(client, monkeypatch):
    from vectcut.features.metadata import service

    monkeypatch.setattr(service, "list_metadata", lambda kind, enum=None: [{"name": "A"}])
    resp = client.get("/metadata/intro_animation")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is True
    assert body["output"] == [{"name": "A"}]
    assert body["error"] == ""


def test_unknown_kind_returns_error_envelope(client, monkeypatch):
    from vectcut.features.metadata import service
    from vectcut.core.errors import InvalidParam

    def _raise(kind, enum=None):
        raise InvalidParam("nope")

    monkeypatch.setattr(service, "list_metadata", _raise)
    resp = client.get("/metadata/nope")
    assert resp.status_code == 200  # 旧路由也是 200 + success=false
    body = resp.get_json()
    assert body["success"] is False
    assert "nope" in body["error"]


@pytest.mark.parametrize("kind,alias", [
    ("intro_animation", "/get_intro_animation_types"),
    ("outro_animation", "/get_outro_animation_types"),
    ("combo_animation", "/get_combo_animation_types"),
    ("transition", "/get_transition_types"),
    ("mask", "/get_mask_types"),
    ("audio_effect", "/get_audio_effect_types"),
    ("font", "/get_font_types"),
    ("text_intro", "/get_text_intro_types"),
    ("text_outro", "/get_text_outro_types"),
    ("text_loop_anim", "/get_text_loop_anim_types"),
    ("video_scene_effect", "/get_video_scene_effect_types"),
    ("video_character_effect", "/get_video_character_effect_types"),
])
def test_old_alias_route_equivalent_to_new_route(client, monkeypatch, kind, alias):
    """旧别名路径输出必须与新 /metadata/{kind} 完全一致（规格 §5.3 路由兼容）。"""
    from vectcut.features.metadata import service

    captured = []

    def spy(k, enum=None):
        captured.append(k)
        return [{"name": "X"}]

    monkeypatch.setattr(service, "list_metadata", spy)

    new = client.get(f"/metadata/{kind}").get_json()
    old = client.get(alias).get_json()
    assert new == old
    assert captured[-1] == kind  # 别名确实转发了同一 kind
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m pytest tests/features/metadata/test_flask_router.py -v`
预期：FAIL，`ModuleNotFoundError: No module named 'vectcut.features.metadata.flask_router'`。

- [ ] **步骤 3：编写实现**

`vectcut/features/metadata/flask_router.py`：
```python
"""Flask Blueprint：元数据查询路由。

提供 GET /metadata/{kind}（新）与 11 个旧具名别名路径（规格 §5.3 路由兼容）。
阶段 4 迁 FastAPI 时，同一 service 接到 FastAPI router，本文件随之替换。
"""

from __future__ import annotations

from flask import Blueprint, jsonify

from vectcut.core.errors import VectCutError
from vectcut.features.metadata import service
from vectcut.features.metadata.registry import META_KINDS

bp = Blueprint("metadata", __name__)

_KIND_TO_ALIAS = {
    "intro_animation":         "/get_intro_animation_types",
    "outro_animation":         "/get_outro_animation_types",
    "combo_animation":         "/get_combo_animation_types",
    "transition":              "/get_transition_types",
    "mask":                    "/get_mask_types",
    "audio_effect":            "/get_audio_effect_types",
    "font":                    "/get_font_types",
    "text_intro":              "/get_text_intro_types",
    "text_outro":              "/get_text_outro_types",
    "text_loop_anim":          "/get_text_loop_anim_types",
    "video_scene_effect":      "/get_video_scene_effect_types",
    "video_character_effect":  "/get_video_character_effect_types",
}


def _envelope(kind: str):
    try:
        return jsonify({"success": True, "output": service.list_metadata(kind), "error": ""})
    except VectCutError as e:
        return jsonify({"success": False, "output": "", "error": str(e)})


@bp.get("/metadata/<kind>")
def metadata_by_kind(kind: str):
    return _envelope(kind)


# 旧具名别名：循环注册，全部转发到同一 service（规格 §5.3）。
def _register_alias(kind: str, alias: str):
    def view():
        return _envelope(kind)
    view.__name__ = f"alias_{kind}"
    bp.add_url_rule(alias, view_func=view, methods=["GET"])


for _kind, _alias in _KIND_TO_ALIAS.items():
    _register_alias(_kind, _alias)
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m pytest tests/features/metadata/test_flask_router.py -v`
预期：参数化 12 项 + 2 基础项全 PASS。

- [ ] **步骤 5：Commit**

```bash
git add vectcut/features/metadata/flask_router.py tests/features/metadata/test_flask_router.py
git commit -m "feat(metadata): 新增 Flask Blueprint 参数化路由与 11 旧别名"
```

---

### 任务 5：capcut_server.py 挂载 Blueprint、删除旧 11 路由与散落 import

**文件：**
- 修改：`capcut_server.py`

**说明：** 删除 `capcut_server.py` 顶部 5-17 行的 17 行散落 `pyJianYingDraft.metadata.*` / `capcut_*` import（已收敛到 adapter）；删除 11 个 `get_xxx_types` 路由函数（895-1450 行区间，约 330 行）；挂载 metadata Blueprint。保留其余 14 个业务路由不动。`IS_CAPCUT_ENV` 仍从 `settings.local` import（业务路由里还在用，阶段 2-3 迁移时清除）。

- [ ] **步骤 1：先跑黄金基线确认当前绿**

运行：`python -m pytest tests/golden/test_metadata_routes_golden.py -v`
预期：12 项全 PASS（基线已建，作改造前对照）。

- [ ] **步骤 2：删除散落 import（capcut_server.py 第 5-17 行）**

删除以下 13 行（保留 `import pyJianYingDraft as draft` 与 `from pyJianYingDraft.text_segment import ...`，后者用于业务路由）：
```python
from pyJianYingDraft.metadata.animation_meta import Intro_type, Outro_type, Group_animation_type
from pyJianYingDraft.metadata.capcut_animation_meta import CapCut_Intro_type, CapCut_Outro_type, CapCut_Group_animation_type
from pyJianYingDraft.metadata.transition_meta import Transition_type
from pyJianYingDraft.metadata.capcut_transition_meta import CapCut_Transition_type
from pyJianYingDraft.metadata.mask_meta import Mask_type
from pyJianYingDraft.metadata.capcut_mask_meta import CapCut_Mask_type
from pyJianYingDraft.metadata.audio_effect_meta import Tone_effect_type, Audio_scene_effect_type, Speech_to_song_type
from pyJianYingDraft.metadata.capcut_audio_effect_meta import CapCut_Voice_filters_effect_type, CapCut_Voice_characters_effect_type, CapCut_Speech_to_song_effect_type
from pyJianYingDraft.metadata.font_meta import Font_type
from pyJianYingDraft.metadata.animation_meta import Text_intro, Text_outro, Text_loop_anim
from pyJianYingDraft.metadata.capcut_text_animation_meta import CapCut_Text_intro, CapCut_Text_outro, CapCut_Text_loop_anim
from pyJianYingDraft.metadata.video_effect_meta import Video_scene_effect_type, Video_character_effect_type
from pyJianYingDraft.metadata.capcut_effect_meta import CapCut_Video_scene_effect_type, CapCut_Video_character_effect_type
```

- [ ] **步骤 3：删除 11 个 get_xxx_types 路由函数**

删除 `capcut_server.py` 中以下函数及其 `@app.route` 装饰器（共 11 个，约 895-1450 行区间）：
`get_intro_animation_types` / `get_outro_animation_types` / `get_combo_animation_types` / `get_transition_types` / `get_mask_types` / `get_audio_effect_types` / `get_font_types` / `get_text_intro_types` / `get_text_outro_types` / `get_text_loop_anim_types` / `get_video_scene_effect_types` / `get_video_character_effect_types`。

- [ ] **步骤 4：挂载 metadata Blueprint**

在 `capcut_server.py` 的 `app = Flask(__name__)` 之后、第一个业务路由之前，加入：
```python
from vectcut.features.metadata.flask_router import bp as metadata_bp
app.register_blueprint(metadata_bp)
```

- [ ] **步骤 5：黄金基线必须保持绿（关键验收）**

运行：`python -m pytest tests/golden/test_metadata_routes_golden.py -v`
预期：12 项全 PASS。**这是收敛后输出与旧实现逐字节一致的最强证据。** 若失败，说明 registry getter 或 adapter 平台派发与旧逻辑有偏差——对照快照 JSON 定位差异（最可能点：audio_effect params 未 ×100、子类型 type 标签拼写、font 平台变体）。

- [ ] **步骤 6：新增 /metadata/{kind} 路由也纳入黄金（可选加强）**

在 `tests/golden/test_metadata_routes_golden.py` 的 `METADATA_ROUTES` 列表末尾追加 12 项 `f"/metadata/{kind}"`（kind 取自 `META_KINDS.keys()`，或硬编码 12 个），然后：
```bash
$env:REGENERATE_GOLDEN=1; python -m pytest tests/golden/test_metadata_routes_golden.py -v
python -m pytest tests/golden/test_metadata_routes_golden.py -v
```
预期：新 12 项快照生成且与对应旧别名快照内容一致（可在快照文件 diff 中确认）。

> 若不想扩大黄金集，可跳过此步骤——旧 11 别名已覆盖保真验证。但推荐纳入，给新路由也建基线。

- [ ] **步骤 7：Commit**

```bash
git add capcut_server.py tests/golden/test_metadata_routes_golden.py tests/golden/snapshots/
git commit -m "refactor(server): 11 个 get_xxx_types 路由收敛为 metadata Blueprint，散落 import 收敛至 adapter"
```

---

### 任务 6：阶段 1 收尾验证

- [ ] **步骤 1：全量测试**

运行：`python -m pytest tests/ -v`
预期：全绿。含阶段 0 全部 + 阶段 1 新增（`test_errors` 2、`test_adapter` 5、`test_registry_service` 5、`test_flask_router` 14）+ 黄金 12（或 24，若任务 5 步骤 6 执行）。

- [ ] **步骤 2：验证 capcut_server 路由数与启动**

运行：
```bash
python -c "import capcut_server; rules=[r for r in capcut_server.app.url_map.iter_rules() if r.endpoint!='static']; print(len(rules), 'routes'); print(sorted(r.rule for r in rules))"
```
预期：约 25 路由（14 业务 + 1 新 `/metadata/<kind>` + 11 别名 + 静态剔除后）。含 `/metadata/<kind>` 与 11 个 `/get_xxx_types` 别名。

- [ ] **步骤 3：验证散落 import 已清**

运行：
```bash
python -c "import capcut_server; src=open(capcut_server.__file__,encoding='utf-8').read(); assert 'from pyJianYingDraft.metadata' not in src, '散落 import 残留'; assert 'CapCut_Intro_type' not in src, 'CapCut_ 枚举符号应在 adapter 而非 capcut_server'; print('import 收敛 OK')"
```
预期：`import 收敛 OK`。

- [ ] **步骤 4：Commit 阶段标记**

```bash
git commit --allow-empty -m "chore: 阶段1 完成——engine adapter + 元数据收敛（14→1 参数化路由 + 11 别名）"
```

---

## 自检

**1. 规格覆盖度（阶段 1 范围 = 规格 §8 阶段 1 行 + §5.1① + §5.3）：**

| 规格要求 | 覆盖任务 |
|----------|----------|
| `engine/adapter.py`（收敛 import + 平台派发 `enums(kind)`） | 任务 2 |
| `material_factory.py`（材料/轨道构造工厂） | **延后到阶段 2**（见偏差说明：无消费者，YAGNI） |
| 元数据注册表 `META_KINDS`（声明式） | 任务 3 |
| `list_metadata(kind)` service，`KeyError → InvalidParam` | 任务 3 |
| 参数化路由 `GET /metadata/{kind}` | 任务 4 |
| 保留 11 旧具名别名路径 | 任务 4（循环注册） |
| 收敛后 < 50 行 / 新增一种枚举只加一行 | 任务 3（registry 一行/种） |
| 黄金基线保持绿（防回归） | 任务 5 步骤 1、5 |
| `core/errors.py`（规格 §4.4 异常体系） | 任务 1（最小版 `InvalidParam`，余者阶段 2-4 按需） |

**未覆盖（留给后续阶段，非遗漏）：**
- `material_factory.py`：延后阶段 2（偏差已说明）。
- `core/errors.py` 完整体系（`DraftNotFound`/`EngineError`/`MediaDownloadError`）：阶段 2-4 按需补。
- FastAPI router：阶段 4（本阶段用 Flask Blueprint 是刻意选择）。

**2. 占位符扫描：** 无 "TODO/待定/添加错误处理"。任务 5 步骤 2-3 给出精确删除清单（行号 + 符号名 + 函数名）。audio_effect getter 的 params ×100 逻辑含完整代码，非泛述。

**3. 类型/命名一致性：**
- `enum_for(kind)` 返回值：任务 2 定义（枚举类 或 audio_effect 的 `{子类型: 枚举}` 字典），任务 3 service 调用、registry getter 接收——契约一致。
- `META_KINDS` 的 11 个 kind 名：任务 3 registry 定义、任务 4 `_KIND_TO_ALIAS` 别名映射、任务 1 测试 `test_registry_covers_all_11_kinds` 断言集、任务 5 步骤 6（若执行）新黄金路由——四处 kind 名集合一致。
- `list_metadata(kind, enum=None)`：任务 3 service 定义、任务 4 `_envelope` 调用、任务 3/4 测试注入签名——一致。
- `active_platform()`：任务 2 定义、`enum_for` 内部调用、任务 2 测试 monkeypatch——一致。
- `InvalidParam`：任务 1 定义 `code="INVALID_PARAM"`/`http_status=422`，任务 3 service 抛、任务 4 `_envelope` 捕获 `VectCutError` 基类——继承链一致。
- `_KIND_TO_ALIAS` 11 条与 `capcut_server.py` grep 实测的 11 个 `@app.route('/get_xxx_types')` 路径一一对应（已核对）。

**自检发现并修正：**
- 规格 §5.3 称"14 接口"，实测 11——任务 3/4 全程按 11 落地，`test_registry_covers_all_11_kinds` 锁定集合。
- 原规格 §5.1① 称 adapter 提供 `enums(kind)`；本计划改名 `enum_for(kind)`（返回枚举类而非成员列表，便于 registry getter 复用），语义等价，命名更准。
- 阶段 0 黄金快照原 `_normalize` 只留 names 会丢 audio_effect 富结构——已在阶段 0 计划中修正为保留完整 output，本阶段任务 5 步骤 5 据此做逐字节保真验证。

---

## 执行交接

计划已完成并保存到 `docs/superpowers/plans/2026-07-02-phase1-engine-adapter-metadata.md`。两种执行方式：

**1. 子代理驱动（推荐）** - 每个任务调度一个新的子代理，任务间进行审查，快速迭代

**2. 内联执行** - 在当前会话中使用 executing-plans 执行任务，批量执行并设有检查点

**选哪种方式？**

> 前置：阶段 0 必须全绿出 release 后再启动本计划（依赖 `vectcut.core.draft_store.get_active_profile` 与黄金快照）。后续阶段 2-5 计划待阶段 1 完成后按需另起会话编写。

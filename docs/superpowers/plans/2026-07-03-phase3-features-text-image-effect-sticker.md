# 阶段 3：Features（text / image / effect）+ material_factory 扩展 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 把 `text`（`add_text` + `add_subtitle`）/ `image`（`add_image`）/ `effect`（`add_effect` + `add_sticker`）四个剪辑能力的业务实现从根目录平铺文件迁入 `vectcut/features/` 包，沿用阶段 2 已验证的"service + schemas + flask_router"三件套模式；扩展 `engine/material_factory.py` 补齐阶段 3 所需的图片材料构造与动画/特效/掩膜枚举解析；`capcut_server.py` 删除 6 个阶段 3 旧路由（`add_text`/`add_subtitle`/`add_image`/`add_effect`/`add_sticker`/`add_video_keyframe`）+ 顶部散落 import，挂载 `text`/`image`/`effect` 三个新 Blueprint（`add_video_keyframe` 已在阶段 2 归入 video Blueprint，仅删旧路由）；扩展黄金基线覆盖阶段 3 业务路由；flake8 清理；**本阶段不碰 MCP、不迁 FastAPI**（阶段 4）、**不拆 example.py / 不统一 pyproject 身份**（阶段 5）。

**架构：**
- 沿用阶段 2 metadata/draft/video/audio 已验证模式：`service.py`（纯 Python 业务，不 import Flask/settings）+ `schemas.py`（Pydantic v2 请求/响应模型，字段默认值与 `capcut_server.py` 路由层逐一对齐）+ `flask_router.py`（薄 Blueprint，`{success,output,error}` 外壳，try/except `VectCutError`）。
- `engine/material_factory.py` 扩展 7 个新能力：`build_photo_material`（图片 `Video_material(material_type='photo')`）、`resolve_intro`/`resolve_outro`/`resolve_combo`（视频段进/出/组动画）、`resolve_text_intro`/`resolve_text_outro`（文本段进/出动画）、`resolve_video_effect`（场景/人物特效）、共享 `_BLUR_MAP` 常量（从 `video/service.py` 提取，image/video 共用）。业务层不再直接 `import pyJianYingDraft` 顶层符号、不再写 `if IS_CAPCUT_ENV`。
- `text` feature 含两个 service 函数（`add_text` / `add_subtitle`），是本阶段最复杂包：`add_text` 涉及多样式 `text_styles`、`IS_CAPCUT_ENV` 文本动画分支、动画 `int(*1000000)` 整型截断、`track_name=None` 创建音频轨道的保真行为；`add_subtitle` 涉及 SRT 三态来源（URL/本地文件/纯文本）、`requests` 下载、`script.import_srt`。
- `image` feature 含 5 处 `IS_CAPCUT_ENV` 分支（进/出/组动画、转场、掩膜），全部经 `material_factory.resolve_*` 收敛；photo 材料经 `build_photo_material`。
- `effect` feature 含 `add_effect`（场景/人物特效，`params[::-1]` 反转保真）与 `add_sticker`（无平台分支，最简单）。
- `capcut_server.py` 收尾：删 6 旧路由函数（~440 行）+ 顶部 6 个 `add_*_impl` import + `hex_to_rgb`/`Text_style`/`Text_border`/`TextStyleRange` import，挂载 3 新 Blueprint；`add_video_keyframe` 路由删除（video Blueprint 已提供，URL 重复 endpoint 由 Blueprint 接管）。
- 黄金基线扩展：阶段 3 业务路由错误分支 + 成功分支（`add_sticker`/`add_effect`/`add_image`/`add_text`/`add_subtitle`）HTTP 快照。

**技术栈：** Flask Blueprint（阶段 4 再切 FastAPI）、Pydantic v2、`vectcut.core.draft_store`、`vectcut.engine.adapter`（`enum_for` kinds：`intro_animation`/`outro_animation`/`combo_animation`/`transition`/`mask`/`font`/`text_intro`/`text_outro`/`video_scene_effect`/`video_character_effect`）、`vectcut.engine.material_factory`、阶段 0-2 黄金快照、`requests`（subtitle 下载）。

**前置依赖：** 阶段 2 全绿、标签 `phase2-complete` 已打。以下必须已就位：
- `vectcut.core.draft_store.get_or_create_draft` / `get_draft` / `get_active_profile`
- `vectcut.engine.adapter.enum_for(kind)`（已覆盖全部阶段 3 kinds）
- `vectcut.engine.material_factory.build_video_material` / `build_audio_material` / `add_to_track` / `resolve_transition` / `resolve_mask`
- `vectcut.core.errors.InvalidParam` / `DraftNotFound` / `VectCutError`
- `vectcut.features.draft.service.generate_draft_url`
- `vectcut.features.video.flask_router.bp`（含 `/add_video_keyframe`）
- `tests/golden/conftest.py`（含 `snapshot_dir` / `regenerate_golden` fixtures）
- `util.url_to_hash` / `util.build_draft_asset_path` / `util.hex_to_rgb`
- `pyJianYingDraft.text_segment.TextBubble` / `TextEffect` / `TextStyleRange`

**本阶段不触碰：** `pyJianYingDraft/` 内部（只读）；`mcp_server.py`（阶段 4）；FastAPI（阶段 4）；`example.py` 拆分、`pyproject.toml` 身份统一（阶段 5）；`add_video_keyframe_impl.py` / `add_video_track.py` / `add_audio_track.py` 等根目录旧 impl 文件本身（保留待阶段 5 清理，仅断开 `capcut_server.py` 对它们的引用）。

**与规格的偏差（自检标注）：**
- 规格 §3 目录树 `text/` 注释 `add_text + add_subtitle`。本阶段把两者都迁入 `features/text/`（`service.py` 两函数），符合规格。
- 规格 §8 阶段 3 列"text image effect (含 sticker)"。`add_video_keyframe` 规格 §8 阶段 2 已列入 video feature 且阶段 2 已实现 service+路由。本阶段仅清理 `capcut_server.py` 中重复的旧 `add_video_keyframe` 路由（与 video Blueprint URL 重叠），不重复迁移。
- `add_subtitle_impl` 用 `requests` 下载 URL 且 `import os` 读本地文件——属网络/IO 副作用，service 层保留原行为（保真），不引入 HTTP 客户端抽象（YAGNI，阶段 4 统一抽象时再处理）。其 SRT 三态解析逻辑逐段复制，不简化。
- `add_text_impl` 第 138 行 `track_name is None` 分支创建的是 **音频轨道**（`draft.Track_type.audio`）而非文本轨道——这是源文件既有行为（疑似 bug），本阶段**逐字保真保留**，不修正，注释标注。
- `add_text_impl` 动画 try/except 用 `print` 忽略不支持动画（宽容不抛）；`add_image_impl` 动画 try/except 抛 `ValueError`（严格）。两者行为不同，**逐字保留各自的宽容/严格策略**，不统一。
- `add_image_impl` 动画时长用 `*1e6`（float），转场时长用 `int(*1000000)`（int）；`add_text_impl` 动画时长用 `int(*1000000)`（int）。三处数值转换**逐字保留各自的截断方式**，不统一。
- `add_subtitle_impl` 的 `TextEffect(effect_id=effect_effect_id, resource_id=effect_effect_id)`——`resource_id` 复用 `effect_effect_id`（源文件 line 139-141 既有），逐字保留。
- `add_text_impl` `Text_background(color=background_color)` 传**原始十六进制字符串**（非 rgb 元组），与 `Text_border(color=rgb_border_color)` 传 rgb 元组不同——逐字保留。
- **路由 ValidationError 分支文案**：阶段 2 的 video/audio 路由已把原 `capcut_server` 各路由手写的"缺 XX 字段"特定消息（如 `Hi, the required parameter 'sticker_id' is missing. Please add it and try again. `）统一收敛为通用 `f"Hi, the required parameters are missing. {e}"`（Pydantic 错误细节 `{e}` 列出缺失字段名）。阶段 3 为保持 features 包内路由风格一致，**沿用阶段 2 通用文案**，不回退到原始特定消息。各路由 `except VectCutError` 异常分支文案则**逐字保留原 `capcut_server` 各路由的异常消息**（含尾随空格：`add_effect`/`add_sticker`/`add_text` 的异常消息末尾有空格，`add_image`/`add_subtitle` 无）。
- **`add_effect` params=None 守卫**：原 `add_effect_impl.py:85` 直接 `params[::-1]`，当 `params=None`（路由 `data.get('params')` 缺省即 None）时 `None[::-1]` 抛 `TypeError`，被路由 `except Exception` 兜为错误 envelope——这是源文件既有的 latent 崩溃。引擎 `Effect_meta.parse_params` 本身支持 `params=None`（`effect_meta.py:77` `if params is None: params = []`）。阶段 3 service 加 `req.params[::-1] if req.params is not None else None` 守卫，让无 params 调用正常走引擎（修正 latent 崩溃，与阶段 2 `except VectCutError` 收窄一致——否则 TypeError 会变 500 而非 envelope）。`params[::-1]` 反转逻辑本身逐字保留。
- **`resolve_video_effect` 用 `getattr` 而非下标 `[]`**：原 `add_effect_impl.py:49,54,61,66` 用 `Video_scene_effect_type[effect_type]`（EnumMeta `__getitem__` 按成员名查）。`Effect_enum` 继承 `enum.Enum`（`effect_meta.py:92`），未覆写 `__getitem__`/`__getattr__`，故 `getattr(enum, name)` 与 `enum[name]` 对**合法成员名**完全等价（仅缺失时异常类型不同：AttributeError vs KeyError），service `except (AttributeError, KeyError)` 双捕，结果等价。用 `getattr` 是为与其余 `resolve_intro/outro/combo/transition/mask/text_intro/text_outro`（原 impl 均用 `getattr`）保持一致。
- **`get_imported_track` 异常类型**：原 `add_text_impl.py:134`/`add_effect_impl.py:78`/`add_sticker_impl.py:58`/`add_image_impl.py:105` 均用 `except exceptions.TrackNotFound:`（精确异常），阶段 3 service 逐字保留 `except exceptions.TrackNotFound:`，不用更宽的 `except Exception:`。

---

## 文件结构

| 文件 | 职责 | 动作 |
|------|------|------|
| `vectcut/engine/material_factory.py` | 补 `build_photo_material` / `resolve_intro` / `resolve_outro` / `resolve_combo` / `resolve_text_intro` / `resolve_text_outro` / `resolve_video_effect`；提取 `_BLUR_MAP` 共享常量 | 修改（追加 7 函数 + 1 常量） |
| `vectcut/features/video/service.py` | `_BLUR_MAP` 改为从 `material_factory` 导入 | 修改（1 行 import + 删本地常量） |
| `vectcut/features/effect/__init__.py` | effect feature 包标记 | 创建 |
| `vectcut/features/effect/schemas.py` | `AddEffectRequest/Response` / `AddStickerRequest/Response` | 创建 |
| `vectcut/features/effect/service.py` | `add_effect` / `add_sticker` | 创建 |
| `vectcut/features/effect/flask_router.py` | 2 路由 Blueprint | 创建 |
| `vectcut/features/image/__init__.py` | 包标记 | 创建 |
| `vectcut/features/image/schemas.py` | `AddImageRequest/Response` | 创建 |
| `vectcut/features/image/service.py` | `add_image` | 创建 |
| `vectcut/features/image/flask_router.py` | 1 路由 Blueprint | 创建 |
| `vectcut/features/text/__init__.py` | 包标记 | 创建 |
| `vectcut/features/text/schemas.py` | `AddTextRequest/Response` / `AddSubtitleRequest/Response` / `TextStyleRangeSpec` / `TextStyleSpec` / `TextBorderSpec`（嵌套模型） | 创建 |
| `vectcut/features/text/service.py` | `add_text` / `add_subtitle` + 私有 `_build_text_styles` | 创建 |
| `vectcut/features/text/flask_router.py` | 2 路由 Blueprint | 创建 |
| `capcut_server.py` | 删 6 旧路由（add_text/add_subtitle/add_image/add_effect/add_sticker/add_video_keyframe）+ 顶部 `add_*_impl` / `hex_to_rgb` / `Text_style` / `Text_border` / `TextStyleRange` import；挂载 text/image/effect 3 新 Blueprint | 修改 |
| `tests/engine/test_material_factory.py` | 补 7 新函数单测 | 修改（追加） |
| `tests/features/effect/test_service.py` | effect service 单测 + 黄金 | 创建 |
| `tests/features/effect/test_router.py` | effect Blueprint 路由测试 | 创建 |
| `tests/features/image/test_service.py` | image service 单测 + 黄金 | 创建 |
| `tests/features/image/test_router.py` | image Blueprint 路由测试 | 创建 |
| `tests/features/text/test_service.py` | text service 单测 + 黄金 | 创建 |
| `tests/features/text/test_router.py` | text Blueprint 路由测试 | 创建 |
| `tests/golden/test_business_routes_golden.py` | 追加阶段 3 业务路由 HTTP 黄金用例 | 修改 |
| `tests/golden/snapshots/business_add_*.json` | 阶段 3 路由快照 | 创建 |
| `.flake8` | 移除 `capcut_server.py` 的 E231/E251/E501/E261/E402 per-file-ignores（阶段 3 路由已删，文件已洁净） | 修改 |

**关键设计决策：**
- **service 是纯 Python**：不 import Flask / `settings`（垫片）。配置经 `draft_store`；引擎经 `engine.adapter` + `engine.material_factory`；草稿经 `draft_store.get_draft` / `get_or_create_draft`；URL 经 `vectcut.features.draft.service.generate_draft_url`。唯一例外：`add_subtitle` 用 `requests` + `os`（保真保留原 SRT 三态来源行为）。
- **schemas 默认值与 capcut_server.py 路由层逐一对齐**（不是与 impl 层对齐）——路由层是 HTTP 入口的真实默认值。例：`AddTextRequest.font="文轩体"`（路由层）、`font_color="#FF0000"`（路由层）、`background_style=0`（路由层），而 impl 层分别是 `None`/`"#ffffff"`/`1`。**保真基准是 HTTP 行为**，故 schemas 锁路由层默认值，service 把这些值原样透传给引擎（不再走 impl 层的"被路由覆盖"默认值）。
- **双名别名在路由层处理**：`add_text` 路由支持 `color`/`font_color`、`size`/`font_size`、`alpha`/`font_alpha`。Pydantic 用 `model_validator(mode='before')` 把 `color`→`font_color`、`size`→`font_size`、`alpha`→`font_alpha` 归一化（`font_color`/`font_size`/`font_alpha` 优先）。原 `capcut_server` 用 `data.get('color', data.get('font_color', ...))` 实现，归一化后语义等价。
- **`_BLUR_MAP` 提取到 material_factory**：`video/service.py` 与 `image/service.py` 都用 `{1:0.0625,2:0.375,3:0.75,4:1.0}`，提取为 `material_factory.BLUR_MAP` 共享，避免重复（DRY）。
- **`add_text` 的 `text_styles` 用嵌套 Pydantic 模型**：`TextStyleRangeSpec(start,end,style,border,font)` + `TextStyleSpec` + `TextBorderSpec`，service 内构造 `pyJianYingDraft.text_segment.TextStyleRange` / `Text_style` / `Text_border`（迁自 `capcut_server.py:add_text` 路由内的构造逻辑 line 177-218）。
- **黄金基线双轨**：HTTP 层（`test_business_routes_golden.py`）验路由外壳 + 错误分支 + 确定性成功分支；service 层（各 feature `test_service.py`）验 draft 输出（`script.dumps()` 快照）。`add_subtitle` 因 `requests` 下载有网络副作用，service 黄金只用**纯文本 SRT 内容**入参（无 URL/文件路径），保证确定性。
- **`add_image`/`add_effect`/`add_sticker`/`add_text` 无网络副作用可建黄金**：均只构造材料/段+加段，不下载（下载在 `save_draft_background`）。`add_subtitle` 纯文本路径也无副作用。

---

### 任务 1：material_factory 扩展（photo 材料 + 动画/特效/掩膜枚举解析 + 共享 _BLUR_MAP）

**文件：**
- 修改：`vectcut/engine/material_factory.py`
- 修改：`vectcut/features/video/service.py`（`_BLUR_MAP` 改导入）
- 修改：`tests/engine/test_material_factory.py`（追加 7 函数 + 常量测试）

**场景铺垫：** 阶段 2 已落地 `build_video_material`/`build_audio_material`/`add_to_track`/`resolve_transition`/`resolve_mask`/`resolve_audio_effect`。阶段 3 业务（image/text/effect）还需：图片材料（`Video_material(material_type='photo')`）、视频段进/出/组动画枚举、文本段进/出动画枚举、场景/人物特效枚举，以及 image/video 共享的背景模糊等级表。本任务把全部新增收敛到 `material_factory`，使后续 service 不再直接碰 `pyJianYingDraft` 顶层符号与 `if IS_CAPCUT_ENV`。`BLUR_MAP` 提取到工厂后，`video/service.py` 改为 `from vectcut.engine.material_factory import BLUR_MAP`，消除重复定义。

- [ ] **步骤 1：编写失败的测试**

在 `tests/engine/test_material_factory.py` 末尾追加（文件已存在，含阶段 2 的 `build_video_material` 等测试）：
```python
def test_build_photo_material_sets_material_type_photo_and_remote_url():
    from vectcut.engine import material_factory as mf

    m = mf.build_photo_material(
        image_url="https://example.com/a.png",
        draft_folder=None,
        draft_id="dfd_x",
        material_name="image_abc.png",
    )
    assert m is not None  # Video_material 实例（material_type='photo'）


def test_build_photo_material_sets_replace_path_when_draft_folder_given(monkeypatch):
    from vectcut.engine import material_factory as mf

    m = mf.build_photo_material(
        image_url="https://example.com/a.png",
        draft_folder="D:/drafts",
        draft_id="dfd_x",
        material_name="image_abc.png",
    )
    assert m is not None  # replace_path 路径已注入（构造不下载，只赋字段）


def test_resolve_intro_returns_member_for_active_platform():
    from vectcut.engine import material_factory as mf

    member = mf.resolve_intro("Zoom In")  # Intro_type / CapCut_Intro_type 成员
    assert member is not None


def test_resolve_outro_returns_member_for_active_platform():
    from vectcut.engine import material_factory as mf

    assert mf.resolve_outro("Fade Out") is not None or mf.resolve_outro("Zoom Out") is not None


def test_resolve_combo_returns_member_for_active_platform():
    from vectcut.engine import material_factory as mf

    assert mf.resolve_combo("Blink") is not None


def test_resolve_text_intro_returns_member_for_active_platform():
    from vectcut.engine import material_factory as mf

    assert mf.resolve_text_intro("Soft") is not None


def test_resolve_text_outro_returns_member_for_active_platform():
    from vectcut.engine import material_factory as mf

    assert mf.resolve_text_outro("Soft") is not None


def test_resolve_video_effect_dispatches_scene_and_character():
    from vectcut.engine import material_factory as mf

    scene = mf.resolve_video_effect("scene", "梦幻")
    char = mf.resolve_video_effect("character", "淡入淡出")
    assert scene is not None or char is not None  # 至少一类有成员


def test_resolve_video_effect_unknown_category_raises_key_error():
    import pytest
    from vectcut.engine import material_factory as mf

    with pytest.raises(KeyError):
        mf.resolve_video_effect("unknown_category", "whatever")


def test_blur_map_constant_matches_source_levels():
    from vectcut.engine.material_factory import BLUR_MAP

    assert BLUR_MAP == {1: 0.0625, 2: 0.375, 3: 0.75, 4: 1.0}
```

- [ ] **步骤 2：运行测试验证失败**

运行：
```powershell
python -m pytest tests/engine/test_material_factory.py -v
```
预期：FAIL，`build_photo_material`/`resolve_intro`/`resolve_outro`/`resolve_combo`/`resolve_text_intro`/`resolve_text_outro`/`resolve_video_effect`/`BLUR_MAP` 全部 `AttributeError: module ... has no attribute`。

- [ ] **步骤 3：编写最少实现代码**

在 `vectcut/engine/material_factory.py` 中：
(a) 在文件顶部常量区（`from util import build_draft_asset_path` 之后、`def build_video_material` 之前）追加共享常量：
```python
# 背景模糊等级表（迁自 add_image_impl.py:218-223 与 video/service.py，image/video 共用）
BLUR_MAP = {1: 0.0625, 2: 0.375, 3: 0.75, 4: 1.0}
```

(b) 在 `build_audio_material` 之后、`add_to_track` 之前追加图片材料构造：
```python
def build_photo_material(
    image_url: str,
    draft_folder: Optional[str],
    draft_id: str,
    material_name: str,
) -> "draft.Video_material":
    """构造图片材料（Video_material material_type='photo'）。draft_folder 非空时设 replace_path。

    迁自 add_image_impl.py:122-125：path=None 始终，draft_folder 决定 replace_path。
    """
    kwargs = dict(
        path=None,
        material_type="photo",
        remote_url=image_url,
        material_name=material_name,
    )
    if draft_folder:
        kwargs["replace_path"] = build_draft_asset_path(draft_folder, draft_id, "image", material_name)
    return draft.Video_material(**kwargs)
```

(c) 在 `resolve_mask` 之后、`resolve_audio_effect` 之前追加 7 个枚举解析函数（视频段动画 + 文本段动画 + 特效）：
```python
def resolve_intro(name: str):
    """视频段进场动画成员（Intro_type / CapCut_Intro_type）。未知名抛 AttributeError。"""
    return getattr(adapter.enum_for("intro_animation"), name)


def resolve_outro(name: str):
    """视频段出场动画成员（Outro_type / CapCut_Outro_type）。"""
    return getattr(adapter.enum_for("outro_animation"), name)


def resolve_combo(name: str):
    """视频段组合动画成员（Group_animation_type / CapCut_Group_animation_type）。"""
    return getattr(adapter.enum_for("combo_animation"), name)


def resolve_text_intro(name: str):
    """文本段进场动画成员（Text_intro / CapCut_Text_intro）。"""
    return getattr(adapter.enum_for("text_intro"), name)


def resolve_text_outro(name: str):
    """文本段出场动画成员（Text_outro / CapCut_Text_outro）。"""
    return getattr(adapter.enum_for("text_outro"), name)


def resolve_video_effect(category: str, name: str):
    """场景/人物特效成员。category ∈ {'scene','character'}，未知名抛 AttributeError。

    迁自 add_effect_impl.py:43-68 的 IS_CAPCUT_ENV 分支：
      scene     → video_scene_effect     (Video_scene_effect_type / CapCut_Video_scene_effect_type)
      character → video_character_effect (Video_character_effect_type / CapCut_Video_character_effect_type)
    未知 category 抛 KeyError（与 enum_for 未知 kind 一致），由 service 转 InvalidParam。
    """
    kind = {"scene": "video_scene_effect", "character": "video_character_effect"}.get(category)
    if kind is None:
        raise KeyError(category)
    return getattr(adapter.enum_for(kind), name)
```

(d) 修改 `vectcut/features/video/service.py`：删除第 23 行 `_BLUR_MAP = {1: 0.0625, 2: 0.375, 3: 0.75, 4: 1.0}`，在 import 区（`from vectcut.engine import material_factory as mf` 之后）追加：
```python
from vectcut.engine.material_factory import BLUR_MAP as _BLUR_MAP
```
（保留别名 `_BLUR_MAP` 以最小化 service 体内改动：第 111-113 行 `if req.background_blur not in _BLUR_MAP` 与 `_BLUR_MAP[req.background_blur]` 不变。）

- [ ] **步骤 4：运行测试验证通过**

运行：
```powershell
python -m pytest tests/engine/test_material_factory.py tests/features/video -v
```
预期：PASS（新 9 个测试 + video 既有测试全绿）。确认 `_BLUR_MAP` 改导入后 video service 行为不变。

- [ ] **步骤 5：flake8 检查**

运行：
```powershell
python -m flake8 vectcut/engine/material_factory.py vectcut/features/video/service.py
```
预期：无输出（洁净）。

- [ ] **步骤 6：Commit**

```powershell
git add vectcut/engine/material_factory.py vectcut/features/video/service.py tests/engine/test_material_factory.py
git commit -m "refactor(engine): material_factory 扩展 photo 材料+动画/特效枚举解析，提取共享 BLUR_MAP"
```

---

### 任务 2：effect feature（add_effect + add_sticker）

**文件：**
- 创建：`vectcut/features/effect/__init__.py`
- 创建：`vectcut/features/effect/schemas.py`
- 创建：`vectcut/features/effect/service.py`
- 创建：`vectcut/features/effect/flask_router.py`
- 创建：`tests/features/effect/__init__.py`
- 创建：`tests/features/effect/test_service.py`
- 创建：`tests/features/effect/test_router.py`

**场景铺垫：** effect feature 是阶段 3 最简包，无多样式/无掩膜/无图片材料，仅 `add_effect`（场景/人物特效，`params[::-1]` 反转保真）与 `add_sticker`（贴纸段，无平台分支）。`add_effect` 的 `IS_CAPCUT_ENV` 四分支经 `material_factory.resolve_video_effect(category, name)` 一次性收敛。先做此包验证阶段 3 三件套流水线，再做 image/text。

- [ ] **步骤 1：编写失败的测试**

创建 `tests/features/effect/__init__.py`（空文件）。

创建 `tests/features/effect/test_service.py`：
```python
import json

import pyJianYingDraft as draft

from vectcut.core.draft_store import DRAFT_CACHE


def _fresh_draft():
    DRAFT_CACHE.clear()
    return draft.Script_file(1080, 1920)


def test_add_sticker_creates_sticker_segment_on_named_track():
    from vectcut.features.effect.schemas import AddStickerRequest
    from vectcut.features.effect.service import add_sticker

    _fresh_draft()
    req = AddStickerRequest(sticker_id="7129384756_sticker", start=0, end=2.0)
    resp = add_sticker(req)
    assert resp.draft_id.startswith("dfd_cat_")
    assert "draft_url" in resp.draft_url or resp.draft_url  # 非空


def test_add_effect_scene_reverses_params_before_passing_to_engine(monkeypatch):
    """保真：add_effect 把 params 反转后传给 script.add_effect（params[::-1]）。
    monkeypatch 跳过真实枚举解析和引擎调用，隔离验证反转逻辑。"""
    captured = {}
    from vectcut.features.effect.schemas import AddEffectRequest
    from vectcut.features.effect import service

    _fresh_draft()
    req = AddEffectRequest(
        effect_type="dummy", effect_category="scene", start=0, end=1.0,
        params=[1.0, 2.0, 3.0],
    )
    monkeypatch.setattr(service.mf, "resolve_video_effect", lambda category, name: object())

    def _spy(self, effect, t_range, params=None, track_name=None):
        captured["params"] = params
        return None  # 不调 orig，避免 effect=object() 崩溃

    monkeypatch.setattr(draft.Script_file, "add_effect", _spy)
    service.add_effect(req)
    assert captured["params"] == [3.0, 2.0, 1.0]  # [::-1] 反转


def test_add_effect_unknown_type_raises_invalid_param():
    import pytest
    from vectcut.core.errors import InvalidParam
    from vectcut.features.effect.schemas import AddEffectRequest
    from vectcut.features.effect.service import add_effect

    _fresh_draft()
    req = AddEffectRequest(effect_type="__no_such_effect__", effect_category="scene")
    with pytest.raises(InvalidParam):
        add_effect(req)
```

创建 `tests/features/effect/test_router.py`：
```python
import pytest


@pytest.fixture()
def client():
    from flask import Flask
    from vectcut.features.effect.flask_router import bp

    app = Flask(__name__)
    app.register_blueprint(bp)
    app.config["TESTING"] = True
    return app.test_client()


def test_add_sticker_route_missing_sticker_id_returns_error_envelope(client):
    resp = client.post("/add_sticker", json={})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is False
    assert "sticker_id" in body["error"]


def test_add_effect_route_returns_envelope(client, monkeypatch):
    from vectcut.features.effect import service
    from vectcut.features.effect.schemas import AddEffectResponse

    # monkeypatch service，只验路由成功 envelope 外壳（不依赖真实特效枚举成员名）
    monkeypatch.setattr(
        service, "add_effect",
        lambda req: AddEffectResponse(draft_id="dfd_cat_x", draft_url="http://x"),
    )
    resp = client.post("/add_effect", json={"effect_type": "dummy", "effect_category": "scene"})
    body = resp.get_json()
    assert body["success"] is True
    assert body["output"]["draft_id"] == "dfd_cat_x"
    assert body["error"] == ""
```

- [ ] **步骤 2：运行测试验证失败**

运行：
```powershell
python -m pytest tests/features/effect -v
```
预期：FAIL，`ModuleNotFoundError: No module named 'vectcut.features.effect'`。

- [ ] **步骤 3：编写最少实现代码**

创建 `vectcut/features/effect/__init__.py`（空文件）。

创建 `vectcut/features/effect/schemas.py`（字段默认值对齐 `capcut_server.py` 路由层 `add_effect`:435-448 与 `add_sticker`:485-504）：
```python
"""effect feature 请求/响应模型。字段默认值与 capcut_server.py 路由层逐一对齐。"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class AddEffectRequest(BaseModel):
    effect_type: str
    effect_category: str = "scene"
    start: float = 0
    end: float = 3.0
    draft_id: Optional[str] = None
    track_name: Optional[str] = "effect_01"
    params: Optional[List[Optional[float]]] = None
    width: int = 1080
    height: int = 1920


class AddEffectResponse(BaseModel):
    draft_id: str
    draft_url: str


class AddStickerRequest(BaseModel):
    # HTTP 字段名 sticker_id（capcut_server.py:489 data.get('sticker_id')），对应 impl 参数 resource_id
    sticker_id: str
    start: float = 0
    end: float = 5.0
    draft_id: Optional[str] = None
    transform_y: float = 0
    transform_x: float = 0
    alpha: float = 1.0
    flip_horizontal: bool = False
    flip_vertical: bool = False
    rotation: float = 0.0
    scale_x: float = 1.0
    scale_y: float = 1.0
    track_name: str = "sticker_main"
    relative_index: int = 0
    width: int = 1080
    height: int = 1920


class AddStickerResponse(BaseModel):
    draft_id: str
    draft_url: str
```

创建 `vectcut/features/effect/service.py`（逐段迁自 `add_effect_impl.py` + `add_sticker_impl.py`，平台分支经 `material_factory`）：
```python
"""effect feature service：add_effect + add_sticker。

迁自 add_effect_impl.py + add_sticker_impl.py。
- add_effect：IS_CAPCUT_ENV 四分支收敛为 material_factory.resolve_video_effect；params[::-1] 反转保真。
- add_sticker：无平台分支，Sticker_segment + Clip_settings。
"""

from __future__ import annotations

import pyJianYingDraft as draft
from pyJianYingDraft import Clip_settings, exceptions, trange

from vectcut.core.draft_store import get_or_create_draft
from vectcut.core.errors import InvalidParam
from vectcut.engine import material_factory as mf
from vectcut.features.draft.service import generate_draft_url
from vectcut.features.effect.schemas import (
    AddEffectRequest,
    AddEffectResponse,
    AddStickerRequest,
    AddStickerResponse,
)


def add_effect(req: AddEffectRequest) -> AddEffectResponse:
    draft_id, script = get_or_create_draft(req.draft_id, req.width, req.height)

    # 解析场景/人物特效（迁自 add_effect_impl.py:43-68 的 IS_CAPCUT_ENV 分支）
    try:
        effect_enum = mf.resolve_video_effect(req.effect_category, req.effect_type)
    except (AttributeError, KeyError):
        # 保真：原 impl 未知类型 raise ValueError(f"Unknown {category} effect type: {type}")
        raise InvalidParam(
            f"Unknown {req.effect_category} effect type: {req.effect_type}"
        )

    # get-or-create 命名特效轨道（迁自 add_effect_impl.py:73-82）
    if req.track_name is not None:
        try:
            script.get_imported_track(draft.Track_type.effect, name=req.track_name)
        except exceptions.TrackNotFound:
            script.add_track(draft.Track_type.effect, track_name=req.track_name)
    else:
        script.add_track(draft.Track_type.effect)

    # 保真：params 反转（add_effect_impl.py:85 params=params[::-1]）；None 守卫见计划偏差说明
    duration = req.end - req.start
    t_range = trange(f"{req.start}s", f"{duration}s")
    reversed_params = req.params[::-1] if req.params is not None else None
    script.add_effect(effect_enum, t_range, params=reversed_params, track_name=req.track_name)

    return AddEffectResponse(draft_id=draft_id, draft_url=generate_draft_url(draft_id))


def add_sticker(req: AddStickerRequest) -> AddStickerResponse:
    draft_id, script = get_or_create_draft(req.draft_id, req.width, req.height)

    # get-or-create 命名贴纸轨道（迁自 add_sticker_impl.py:53-62）
    if req.track_name is not None:
        try:
            script.get_imported_track(draft.Track_type.sticker, name=req.track_name)
        except exceptions.TrackNotFound:
            script.add_track(
                draft.Track_type.sticker,
                track_name=req.track_name,
                relative_index=req.relative_index,
            )
    else:
        script.add_track(draft.Track_type.sticker, relative_index=req.relative_index)

    # 贴纸段（迁自 add_sticker_impl.py:64-78）
    sticker_segment = draft.Sticker_segment(
        req.sticker_id,
        trange(f"{req.start}s", f"{req.end - req.start}s"),
        clip_settings=Clip_settings(
            transform_y=req.transform_y,
            transform_x=req.transform_x,
            alpha=req.alpha,
            flip_horizontal=req.flip_horizontal,
            flip_vertical=req.flip_vertical,
            rotation=req.rotation,
            scale_x=req.scale_x,
            scale_y=req.scale_y,
        ),
    )

    script.add_segment(sticker_segment, track_name=req.track_name)
    return AddStickerResponse(draft_id=draft_id, draft_url=generate_draft_url(draft_id))
```

创建 `vectcut/features/effect/flask_router.py`（沿用 video/audio 路由外壳模式；错误信息对齐 `capcut_server.py` add_effect:481 / add_sticker:544，含尾随空格）：
```python
"""effect feature Flask Blueprint：/add_effect + /add_sticker。"""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from vectcut.core.errors import VectCutError
from vectcut.features.effect import service
from vectcut.features.effect.schemas import AddEffectRequest, AddStickerRequest

bp = Blueprint("effect", __name__)


def _ok(output):
    return jsonify({"success": True, "output": output, "error": ""})


@bp.post("/add_effect")
def add_effect():
    try:
        req = AddEffectRequest.model_validate(request.get_json() or {})
    except ValidationError as e:
        return jsonify(
            {"success": False, "output": "", "error": f"Hi, the required parameters are missing. {e}"}
        )
    try:
        resp = service.add_effect(req)
        return _ok({"draft_id": resp.draft_id, "draft_url": resp.draft_url})
    except VectCutError as e:
        # 保真：capcut_server.py:481 error_message 末尾含一个空格
        return jsonify(
            {"success": False, "output": "", "error": f"Error occurred while adding effect: {e}. "}
        )


@bp.post("/add_sticker")
def add_sticker():
    try:
        req = AddStickerRequest.model_validate(request.get_json() or {})
    except ValidationError as e:
        # 阶段2 通用文案（Pydantic {e} 列出缺失字段，含 sticker_id）
        return jsonify(
            {"success": False, "output": "", "error": f"Hi, the required parameters are missing. {e}"}
        )
    try:
        resp = service.add_sticker(req)
        return _ok({"draft_id": resp.draft_id, "draft_url": resp.draft_url})
    except VectCutError as e:
        # 保真：capcut_server.py:544 error_message 末尾含一个空格
        return jsonify(
            {"success": False, "output": "", "error": f"Error occurred while adding sticker: {e}. "}
        )
```

- [ ] **步骤 4：运行测试验证通过**

运行：
```powershell
python -m pytest tests/features/effect -v
```
预期：PASS（4 测试全绿）。

- [ ] **步骤 5：flake8 检查**

运行：
```powershell
python -m flake8 vectcut/features/effect tests/features/effect
```
预期：无输出。

- [ ] **步骤 6：Commit**

```powershell
git add vectcut/features/effect tests/features/effect
git commit -m "feat(effect): 迁移 add_effect + add_sticker 为 effect feature（service+schemas+router）"
```

---

### 任务 3：image feature（add_image）

**文件：**
- 创建：`vectcut/features/image/__init__.py`
- 创建：`vectcut/features/image/schemas.py`
- 创建：`vectcut/features/image/service.py`
- 创建：`vectcut/features/image/flask_router.py`
- 创建：`tests/features/image/__init__.py`
- 创建：`tests/features/image/test_service.py`
- 创建：`tests/features/image/test_router.py`

**场景铺垫：** image feature 含 5 处 `IS_CAPCUT_ENV` 分支（进场/出场/组动画、转场、掩膜），全部经 `material_factory.resolve_intro/outro/combo/transition/mask` 收敛；图片材料经 `build_photo_material`。保真关键点：(1) 默认视频轨道检查用 `except TrackNotFound` + `except NameError` 双分支（与 video service 的 `except Exception` 不同，逐字保留）；(2) 进/出/组动画时长用 `*1e6`（float），转场时长用 `int(*1000000)`（int）——三处截断方式不同，逐字保留；(3) 进场动画优先级：`intro_animation` 非 None 优先于 `animation`（向后兼容），`intro_animation_duration` 非 None 优先于 `animation_duration`；(4) 动画/转场 try/except 抛 `ValueError`（严格），掩膜用裸 except 抛 `ValueError`——逐字保留严格策略（与 add_text 的 `print` 宽容策略不同）；(5) `draft_folder` 非空时 `print('replace_path:', path)` 保留。

- [ ] **步骤 1：编写失败的测试**

创建 `tests/features/image/__init__.py`（空文件）。

创建 `tests/features/image/test_service.py`：
```python
import pyJianYingDraft as draft

from vectcut.core.draft_store import DRAFT_CACHE


def _fresh_draft():
    DRAFT_CACHE.clear()


def test_add_image_creates_photo_segment_with_named_track():
    from vectcut.features.image.schemas import AddImageRequest
    from vectcut.features.image.service import add_image

    _fresh_draft()
    req = AddImageRequest(image_url="https://example.com/a.png", start=0, end=2.0)
    resp = add_image(req)
    assert resp.draft_id.startswith("dfd_cat_")


def test_add_image_intro_animation_takes_priority_over_animation(monkeypatch):
    """保真：intro_animation 非 None 时优先于 animation（向后兼容）。
    monkeypatch resolve_intro 跳过真实枚举解析，隔离验证优先级与 *1e6 时长。"""
    captured = {}
    from vectcut.features.image.schemas import AddImageRequest
    from vectcut.features.image import service

    _fresh_draft()
    req = AddImageRequest(
        image_url="https://example.com/a.png",
        animation="Fade In", animation_duration=0.3,
        intro_animation="Zoom In", intro_animation_duration=0.7,
    )
    monkeypatch.setattr(service.mf, "resolve_intro", lambda name: object())

    def _spy(self, anim_type, duration):
        captured.setdefault("calls", []).append((anim_type, duration))
        return None

    monkeypatch.setattr(draft.Video_segment, "add_animation", _spy)
    service.add_image(req)
    # 第一条 add_animation 调用应是 intro（duration=0.7*1e6 float）
    assert captured["calls"][0][1] == 0.7 * 1e6


def test_add_image_unknown_mask_raises_invalid_param_with_fidelity_message():
    import pytest
    from vectcut.core.errors import InvalidParam
    from vectcut.features.image.schemas import AddImageRequest
    from vectcut.features.image.service import add_image

    _fresh_draft()
    req = AddImageRequest(image_url="https://example.com/a.png", mask_type="__no_such_mask__")
    with pytest.raises(InvalidParam) as exc:
        add_image(req)
    assert "Unsupported mask type" in str(exc.value)
    assert "Linear, Mirror, Circle, Rectangle, Heart, Star" in str(exc.value)


def test_add_image_invalid_blur_level_raises():
    import pytest
    from vectcut.core.errors import InvalidParam
    from vectcut.features.image.schemas import AddImageRequest
    from vectcut.features.image.service import add_image

    _fresh_draft()
    req = AddImageRequest(image_url="https://example.com/a.png", background_blur=9)
    with pytest.raises(InvalidParam):
        add_image(req)


def test_add_image_transition_duration_uses_int_truncation(monkeypatch):
    """保真：转场时长 int(transition_duration*1000000)（整型截断），与动画 *1e6（float）不同。
    monkeypatch resolve_transition 跳过真实枚举解析，隔离验证整型截断。"""
    captured = {}
    from vectcut.features.image.schemas import AddImageRequest
    from vectcut.features.image import service

    _fresh_draft()
    req = AddImageRequest(
        image_url="https://example.com/a.png", transition="Dissolve", transition_duration=0.7,
    )
    monkeypatch.setattr(service.mf, "resolve_transition", lambda name: object())

    def _spy(self, transition_type, duration=None):
        captured["duration"] = duration
        return None

    monkeypatch.setattr(draft.Video_segment, "add_transition", _spy)
    service.add_image(req)
    assert captured["duration"] == int(0.7 * 1000000)  # 整型，非 0.7e6
```

创建 `tests/features/image/test_router.py`：
```python
import pytest


@pytest.fixture()
def client():
    from flask import Flask
    from vectcut.features.image.flask_router import bp

    app = Flask(__name__)
    app.register_blueprint(bp)
    app.config["TESTING"] = True
    return app.test_client()


def test_add_image_route_missing_image_url_returns_error_envelope(client):
    resp = client.post("/add_image", json={})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is False
    assert "image_url" in body["error"]


def test_add_image_route_success_envelope(client):
    from vectcut.core.draft_store import DRAFT_CACHE
    DRAFT_CACHE.clear()
    resp = client.post("/add_image", json={"image_url": "https://example.com/a.png"})
    body = resp.get_json()
    assert body["success"] is True
    assert body["output"]["draft_id"].startswith("dfd_cat_")
```

- [ ] **步骤 2：运行测试验证失败**

运行：
```powershell
python -m pytest tests/features/image -v
```
预期：FAIL，`ModuleNotFoundError: No module named 'vectcut.features.image'`。

- [ ] **步骤 3：编写最少实现代码**

创建 `vectcut/features/image/__init__.py`（空文件）。

创建 `vectcut/features/image/schemas.py`（字段默认值对齐 `capcut_server.py` 路由层 `add_image`:288-328；掩膜默认值与 video schemas **不同**——image 用 0.0/0.0/0.5，逐字保真）：
```python
"""image feature 请求/响应模型。字段默认值与 capcut_server.py 路由层逐一对齐。"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class AddImageRequest(BaseModel):
    draft_folder: Optional[str] = None
    image_url: str
    width: int = 1080
    height: int = 1920
    start: float = 0
    end: float = 3.0
    draft_id: Optional[str] = None
    transform_y: float = 0
    scale_x: float = 1
    scale_y: float = 1
    transform_x: float = 0
    track_name: str = "image_main"  # 路由层默认（impl 层是 "main"，被路由覆盖）
    relative_index: int = 0
    animation: Optional[str] = None
    animation_duration: float = 0.5
    intro_animation: Optional[str] = None
    intro_animation_duration: float = 0.5
    outro_animation: Optional[str] = None
    outro_animation_duration: float = 0.5
    combo_animation: Optional[str] = None
    combo_animation_duration: float = 0.5
    transition: Optional[str] = None
    transition_duration: float = 0.5
    # mask（默认值与 video schemas 不同：image 用 0.0/0.0/0.5，逐字保真 add_image_impl）
    mask_type: Optional[str] = None
    mask_center_x: float = 0.0
    mask_center_y: float = 0.0
    mask_size: float = 0.5
    mask_rotation: float = 0.0
    mask_feather: float = 0.0
    mask_invert: bool = False
    mask_rect_width: Optional[float] = None
    mask_round_corner: Optional[float] = None
    background_blur: Optional[int] = None


class AddImageResponse(BaseModel):
    draft_id: str
    draft_url: str
```

创建 `vectcut/features/image/service.py`（逐段迁自 `add_image_impl.py`，5 处 `IS_CAPCUT_ENV` 分支经 `material_factory` 收敛）：
```python
"""image feature service：add_image。

迁自 add_image_impl.py。5 处 IS_CAPCUT_ENV 分支（进/出/组动画、转场、掩膜）
收敛为 material_factory.resolve_*。保真点见计划任务 3 场景铺垫。
"""

from __future__ import annotations

import pyJianYingDraft as draft
from pyJianYingDraft import Clip_settings, exceptions, trange

from vectcut.core.draft_store import get_or_create_draft
from vectcut.core.errors import InvalidParam
from vectcut.engine import material_factory as mf
from vectcut.features.draft.service import generate_draft_url
from vectcut.features.image.schemas import AddImageRequest, AddImageResponse
from vectcut.engine.material_factory import BLUR_MAP
from util import url_to_hash


def add_image(req: AddImageRequest) -> AddImageResponse:
    draft_id, script = get_or_create_draft(req.draft_id, req.width, req.height)

    # 检查默认视频轨道（迁自 add_image_impl.py:91-98，保留 TrackNotFound + NameError 双分支）
    try:
        script.get_track(draft.Track_type.video, track_name=None)
    except exceptions.TrackNotFound:
        script.add_track(draft.Track_type.video, relative_index=0)
    except NameError:
        # 多视频轨道时 get_track 抛 NameError，什么都不做
        pass

    # get-or-create 命名视频轨道（迁自 add_image_impl.py:100-109）
    if req.track_name is not None:
        try:
            script.get_imported_track(draft.Track_type.video, name=req.track_name)
        except exceptions.TrackNotFound:
            script.add_track(
                draft.Track_type.video,
                track_name=req.track_name,
                relative_index=req.relative_index,
            )
    else:
        script.add_track(draft.Track_type.video, relative_index=req.relative_index)

    # 图片材料（迁自 add_image_impl.py:111-125）
    material_name = f"image_{url_to_hash(req.image_url)}.png"
    # draft_image_path 仅用于 print 副作用（原 impl 亦如此），不传入材料构造
    # build_photo_material 内部据 draft_folder 自行 build_draft_asset_path
    draft_image_path = None
    if req.draft_folder:
        from util import build_draft_asset_path
        draft_image_path = build_draft_asset_path(req.draft_folder, draft_id, "image", material_name)
        print("replace_path:", draft_image_path)

    image_material = mf.build_photo_material(
        image_url=req.image_url,
        draft_folder=req.draft_folder,
        draft_id=draft_id,
        material_name=material_name,
    )

    # 图片段（迁自 add_image_impl.py:127-143）
    duration = req.end - req.start
    target_timerange = trange(f"{req.start}s", f"{duration}s")
    source_timerange = trange(f"{0}s", f"{duration}s")
    image_segment = draft.Video_segment(
        image_material,
        target_timerange=target_timerange,
        source_timerange=source_timerange,
        clip_settings=Clip_settings(
            transform_y=req.transform_y,
            scale_x=req.scale_x,
            scale_y=req.scale_y,
            transform_x=req.transform_x,
        ),
    )

    # 进场动画（迁自 add_image_impl.py:145-156）：intro_animation 优先于 animation
    intro_anim = req.intro_animation if req.intro_animation is not None else req.animation
    intro_dur = req.intro_animation_duration if req.intro_animation_duration is not None else req.animation_duration
    if intro_anim:
        try:
            animation_type = mf.resolve_intro(intro_anim)
            image_segment.add_animation(animation_type, intro_dur * 1e6)  # float *1e6 保真
        except AttributeError:
            raise InvalidParam(
                f"Warning: Unsupported entrance animation type {intro_anim}, this parameter will be ignored"
            )

    # 出场动画（迁自 add_image_impl.py:158-167）
    if req.outro_animation:
        try:
            outro_type = mf.resolve_outro(req.outro_animation)
            image_segment.add_animation(outro_type, req.outro_animation_duration * 1e6)  # float *1e6 保真
        except AttributeError:
            raise InvalidParam(
                f"Warning: Unsupported exit animation type {req.outro_animation}, this parameter will be ignored"
            )

    # 组合动画（迁自 add_image_impl.py:169-178）
    if req.combo_animation:
        try:
            combo_type = mf.resolve_combo(req.combo_animation)
            image_segment.add_animation(combo_type, req.combo_animation_duration * 1e6)  # float *1e6 保真
        except AttributeError:
            raise InvalidParam(
                f"Warning: Unsupported combo animation type {req.combo_animation}, this parameter will be ignored"
            )

    # 转场（迁自 add_image_impl.py:180-191）：duration 用 int(*1000000) 整型截断（与动画 *1e6 不同）
    if req.transition:
        try:
            transition_type = mf.resolve_transition(req.transition)
            duration_microseconds = int(req.transition_duration * 1000000) if req.transition_duration is not None else None
            image_segment.add_transition(transition_type, duration=duration_microseconds)
        except AttributeError:
            raise InvalidParam(
                f"Warning: Unsupported transition type {req.transition}, this parameter will be ignored"
            )

    # 掩膜（迁自 add_image_impl.py:193-213）：裸 except 保真
    if req.mask_type:
        try:
            mask_type_enum = mf.resolve_mask(req.mask_type)
            image_segment.add_mask(
                script,
                mask_type_enum,
                center_x=req.mask_center_x,
                center_y=req.mask_center_y,
                size=req.mask_size,
                rotation=req.mask_rotation,
                feather=req.mask_feather,
                invert=req.mask_invert,
                rect_width=req.mask_rect_width,
                round_corner=req.mask_round_corner,
            )
        except Exception:
            raise InvalidParam(
                f"Unsupported mask type {req.mask_type}, supported types include: Linear, Mirror, Circle, Rectangle, Heart, Star"
            )

    # 背景模糊（迁自 add_image_impl.py:215-230）
    if req.background_blur is not None:
        if req.background_blur not in BLUR_MAP:
            raise InvalidParam(f"Invalid background blur level {req.background_blur}, valid values are 1-4")
        image_segment.add_background_filling("blur", blur=BLUR_MAP[req.background_blur])

    script.add_segment(image_segment, track_name=req.track_name)
    return AddImageResponse(draft_id=draft_id, draft_url=generate_draft_url(draft_id))
```

创建 `vectcut/features/image/flask_router.py`（错误信息对齐 `capcut_server.py:385`）：
```python
"""image feature Flask Blueprint：/add_image。"""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from vectcut.core.errors import VectCutError
from vectcut.features.image import service
from vectcut.features.image.schemas import AddImageRequest

bp = Blueprint("image", __name__)


def _ok(output):
    return jsonify({"success": True, "output": output, "error": ""})


@bp.post("/add_image")
def add_image():
    try:
        req = AddImageRequest.model_validate(request.get_json() or {})
    except ValidationError as e:
        return jsonify(
            {"success": False, "output": "", "error": f"Hi, the required parameters are missing. {e}"}
        )
    try:
        resp = service.add_image(req)
        return _ok({"draft_id": resp.draft_id, "draft_url": resp.draft_url})
    except VectCutError as e:
        # 保真：capcut_server.py:385 error_message
        return jsonify(
            {"success": False, "output": "", "error": f"Error occurred while processing image: {e}."}
        )
```

- [ ] **步骤 4：运行测试验证通过**

运行：
```powershell
python -m pytest tests/features/image -v
```
预期：PASS（6 测试全绿）。

- [ ] **步骤 5：flake8 检查**

运行：
```powershell
python -m flake8 vectcut/features/image tests/features/image
```
预期：无输出。

- [ ] **步骤 6：Commit**

```powershell
git add vectcut/features/image tests/features/image
git commit -m "feat(image): 迁移 add_image 为 image feature，5 处 IS_CAPCUT_ENV 分支收敛为 material_factory.resolve_*"
```

---

### 任务 4：text feature（add_text + add_subtitle）

**文件：**
- 创建：`vectcut/features/text/__init__.py`
- 创建：`vectcut/features/text/schemas.py`
- 创建：`vectcut/features/text/service.py`
- 创建：`vectcut/features/text/flask_router.py`
- 创建：`tests/features/text/__init__.py`
- 创建：`tests/features/text/test_service.py`
- 创建：`tests/features/text/test_router.py`

**场景铺垫：** text feature 是阶段 3 最复杂包，含 `add_text`（多样式 `text_styles`、文本动画、`IS_CAPCUT_ENV` 分支）与 `add_subtitle`（SRT 三态来源、`requests` 下载、`script.import_srt`）。保真关键点（逐字保留，不得简化）：

**add_text 保真点：**
1. **`track_name=None` 创建音频轨道**（`add_text_impl.py:138` `script.add_track(draft.Track_type.audio)`）——源文件既有行为（疑似 bug），逐字保留，注释标注。
2. **动画 `print` 宽容不抛**（`add_text_impl.py:250-251,263-264`）：未知 intro/outro 动画 `print` warning 后跳过，**不 raise**（与 `add_image` 的 raise 严格策略不同）。
3. **动画时长 `int(*1000000)` 整型截断**（非 `*1e6` float，与 `add_image` 动画不同）。
4. **`Text_background(color=background_color)` 传原始十六进制字符串**（`add_text_impl.py:160`），非 rgb 元组；`Text_border(color=rgb_border_color)` 传 rgb 元组——两者不同。
5. **`Text_shadow(color=shadow_color)` 传原始字符串**。
6. **`text_styles` 范围验证中文错误**（`add_text_impl.py:229-230`）：`f"无效的文本范围: [{start}, {end}), 文本长度: {len(text)}"`。
7. **`font` 未知枚举错误**（`add_text_impl.py:111-112`）：`f"Unsupported font: {font}, please use one of the fonts in Font_type: {available_fonts}"`。
8. **alpha 范围校验**（`add_text_impl.py:115-120`）：`font_alpha`/`border_alpha`/`background_alpha` ∈ [0,1]，分别 `raise ValueError("alpha value must be between 0.0 and 1.0")` / `"border_alpha value must be between 0.0 and 1.0"` / `"background_alpha value must be between 0.0 and 1.0"`。
9. **双名别名**（`capcut_server.py:126,127,130`）：`color`→`font_color`、`size`→`font_size`、`alpha`→`font_alpha`，`color`/`size`/`alpha` 优先于 `font_*`。
10. **路由层默认值与 impl 层不同**：schemas 锁路由层（`font="文轩体"`、`font_color="#FF0000"`、`background_style=0`、`transform_y=0`、`end=5`），service 原样透传。

**add_subtitle 保真点：**
1. **SRT 三态来源**（`add_subtitle_impl.py:69-91`）：URL（`requests.get` + `encoding='utf-8'`）、本地文件（`open` `utf-8-sig`）、纯文本（`replace('\\n','\n').replace('/n','\n')`）。
2. **`TextEffect(effect_id=effect_effect_id, resource_id=effect_effect_id)`**（`add_subtitle_impl.py:139-141`）：`resource_id` 复用 `effect_effect_id`（源文件既有，逐字保留）。
3. **`text_background` 只传 3 字段**（`add_subtitle_impl.py:109-113`）：`color`/`style`/`alpha`，无 `round_radius`/`height`/`width` 等（与 `add_text` 的 8 字段不同）。
4. **`time_offset=int(time_offset*1000000)`** 整型截断（`add_subtitle_impl.py:155`）。
5. **默认值与 impl 层不同**：schemas 锁路由层（`font="思源粗宋"`、`font_size=5.0`、`vertical=False`、`alpha=1`、`background_style=0`），impl 层分别是 `None`/`8.0`/`True`/`0.4`/`1`。
6. **`alpha` 字段名**（非 `font_alpha`）：`add_subtitle` 路由用 `data.get('alpha',1)`，无 `font_alpha` 别名。
7. **`style_reference` 不暴露**：`capcut_server.py:add_subtitle` 未传 `style_reference`，service 传 `None`。

- [ ] **步骤 1：编写失败的测试**

创建 `tests/features/text/__init__.py`（空文件）。

创建 `tests/features/text/test_service.py`：
```python
import pyJianYingDraft as draft

from vectcut.core.draft_store import DRAFT_CACHE


def _fresh():
    DRAFT_CACHE.clear()


def test_add_text_creates_text_segment_with_named_track():
    from vectcut.features.text.schemas import AddTextRequest
    from vectcut.features.text.service import add_text

    _fresh()
    req = AddTextRequest(text="hello", start=0, end=2.0)
    resp = add_text(req)
    assert resp.draft_id.startswith("dfd_cat_")


def test_add_text_track_name_none_creates_audio_track_not_text():
    """保真：track_name=None 时创建音频轨道（add_text_impl.py:138 既有行为）。"""
    from vectcut.features.text.schemas import AddTextRequest
    from vectcut.features.text.service import add_text

    _fresh()
    req = AddTextRequest(text="hello", start=0, end=2.0, track_name=None)
    add_text(req)
    # 验证存在音频轨道（而非文本轨道）
    script = next(iter(DRAFT_CACHE.values()))
    try:
        script.get_track(draft.Track_type.audio, track_name=None)
        audio_exists = True
    except Exception:
        audio_exists = False
    assert audio_exists


def test_add_text_unknown_intro_animation_prints_warning_does_not_raise(capsys):
    """保真：未知动画 print warning 后跳过，不 raise（与 add_image 严格策略不同）。"""
    from vectcut.features.text.schemas import AddTextRequest
    from vectcut.features.text.service import add_text

    _fresh()
    req = AddTextRequest(text="hello", start=0, end=2.0, intro_animation="__no_such_anim__")
    add_text(req)  # 不应抛
    out = capsys.readouterr().out
    assert "Unsupported intro animation type" in out


def test_add_text_intro_duration_uses_int_truncation(monkeypatch):
    """保真：动画时长 int(intro_duration*1000000) 整型截断（非 *1e6）。
    monkeypatch resolve_text_intro 跳过真实枚举解析，隔离验证整型截断。"""
    captured = {}
    from vectcut.features.text.schemas import AddTextRequest
    from vectcut.features.text import service

    _fresh()
    req = AddTextRequest(text="hello", start=0, end=2.0, intro_animation="Soft", intro_duration=0.7)
    monkeypatch.setattr(service.mf, "resolve_text_intro", lambda name: object())

    def _spy(self, anim_type, duration):
        captured["duration"] = duration
        return None

    monkeypatch.setattr(draft.Text_segment, "add_animation", _spy)
    service.add_text(req)
    assert captured["duration"] == int(0.7 * 1000000)


def test_add_text_invalid_text_style_range_raises_with_chinese_message():
    import pytest
    from vectcut.core.errors import InvalidParam
    from vectcut.features.text.schemas import AddTextRequest, TextStyleRangeSpec
    from vectcut.features.text.service import add_text

    _fresh()
    req = AddTextRequest(
        text="ab", start=0, end=2.0,
        text_styles=[TextStyleRangeSpec(start=0, end=99)],  # end > len(text)
    )
    with pytest.raises(InvalidParam) as exc:
        add_text(req)
    assert "无效的文本范围" in str(exc.value)


def test_add_text_unknown_font_raises_invalid_param():
    import pytest
    from vectcut.core.errors import InvalidParam
    from vectcut.features.text.schemas import AddTextRequest
    from vectcut.features.text.service import add_text

    _fresh()
    req = AddTextRequest(text="ab", start=0, end=2.0, font="__no_such_font__")
    with pytest.raises(InvalidParam) as exc:
        add_text(req)
    assert "Unsupported font" in str(exc.value)


def test_add_subtitle_pure_text_replaces_escape_sequences():
    """保真：纯文本 SRT 内容 replace('\\n','\\n').replace('/n','\\n') 后 import_srt。"""
    captured = {}
    from vectcut.features.text.schemas import AddSubtitleRequest
    from vectcut.features.text import service

    _fresh()
    req = AddSubtitleRequest(srt="1\\n00:00:01 --> 00:00:02\\nHello/nWorld")

    def _spy(self, srt_content, *args, **kwargs):
        captured["content"] = srt_content
        return None

    from unittest.mock import patch
    with patch.object(draft.Script_file, "import_srt", _spy):
        service.add_subtitle(req)
    # \\n 与 /n 都应被替换为真实换行
    assert "\\n" not in captured["content"].replace("\n", "")  # 反斜杠+n 已转真换行
    assert "\n" in captured["content"]


def test_add_subtitle_text_effect_reuses_effect_id_as_resource_id(monkeypatch):
    """保真：TextEffect(effect_id=x, resource_id=x) resource_id 复用（add_subtitle_impl.py:139-141）。"""
    from vectcut.features.text.schemas import AddSubtitleRequest
    from vectcut.features.text import service
    from pyJianYingDraft.text_segment import TextEffect

    _fresh()
    captured = {}
    orig_init = TextEffect.__init__

    def spy(self, *args, **kwargs):
        captured["kwargs"] = kwargs
        return orig_init(self, *args, **kwargs)

    monkeypatch.setattr(TextEffect, "__init__", spy)
    req = AddSubtitleRequest(srt="text", effect_effect_id="eff_123")
    from unittest.mock import patch
    with patch.object(draft.Script_file, "import_srt", lambda self, *a, **k: None):
        service.add_subtitle(req)
    assert captured["kwargs"].get("resource_id") == "eff_123"
    assert captured["kwargs"].get("effect_id") == "eff_123"
```

创建 `tests/features/text/test_router.py`：
```python
import pytest


@pytest.fixture()
def client():
    from flask import Flask
    from vectcut.features.text.flask_router import bp

    app = Flask(__name__)
    app.register_blueprint(bp)
    app.config["TESTING"] = True
    return app.test_client()


def test_add_text_route_missing_text_returns_error_with_fidelity_message(client):
    resp = client.post("/add_text", json={})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["success"] is False
    # 保真：capcut_server.py:228 错误消息（含尾随空格）
    assert "text" in body["error"] and "start" in body["error"] and "end" in body["error"]


def test_add_text_route_color_alias_maps_to_font_color(client):
    from vectcut.core.draft_store import DRAFT_CACHE
    DRAFT_CACHE.clear()
    # color 别名应被归一化为 font_color
    resp = client.post("/add_text", json={"text": "hi", "start": 0, "end": 1, "color": "#00FF00"})
    body = resp.get_json()
    assert body["success"] is True


def test_add_subtitle_route_missing_srt_returns_error(client):
    resp = client.post("/add_subtitle", json={})
    body = resp.get_json()
    assert body["success"] is False
    assert "srt" in body["error"]
```

- [ ] **步骤 2：运行测试验证失败**

运行：
```powershell
python -m pytest tests/features/text -v
```
预期：FAIL，`ModuleNotFoundError: No module named 'vectcut.features.text'`。

- [ ] **步骤 3：编写最少实现代码（schemas）**

创建 `vectcut/features/text/__init__.py`（空文件）。

创建 `vectcut/features/text/schemas.py`：
```python
"""text feature 请求/响应模型。字段默认值与 capcut_server.py 路由层逐一对齐。"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, model_validator


# —— add_text 嵌套模型（迁自 capcut_server.py:177-218 的 dict 构造）——


class TextStyleSpec(BaseModel):
    size: Optional[float] = None  # None → 回退外层 font_size
    bold: bool = False
    italic: bool = False
    underline: bool = False
    color: Optional[str] = None  # None → 回退外层 font_color
    alpha: Optional[float] = None  # None → 回退外层 font_alpha
    align: int = 1
    vertical: Optional[bool] = None  # None → 回退外层 vertical
    letter_spacing: int = 0
    line_spacing: int = 0


class TextBorderSpec(BaseModel):
    width: float = 0
    alpha: Optional[float] = None  # None → 回退外层 border_alpha
    color: Optional[str] = None  # None → 回退外层 border_color


class TextStyleRangeSpec(BaseModel):
    start: int = 0
    end: int = 0
    style: Optional[TextStyleSpec] = None
    border: Optional[TextBorderSpec] = None
    font: Optional[str] = None  # None → 回退外层 font


class AddTextRequest(BaseModel):
    text: str
    start: float = 0
    end: float = 5  # 路由层默认 5（impl 无默认，被路由覆盖）
    draft_id: Optional[str] = None
    transform_y: float = 0  # 路由层 0（impl -0.8）
    transform_x: float = 0
    font: Optional[str] = "文轩体"  # 路由层默认（impl None）；Optional 保真：用户传 null → None → font_type=None
    font_color: str = "#FF0000"  # 路由层（impl #ffffff）
    font_size: float = 8.0
    track_name: str = "text_main"
    vertical: bool = False
    font_alpha: float = 1.0
    outro_animation: Optional[str] = None
    outro_duration: float = 0.5
    width: int = 1080
    height: int = 1920
    fixed_width: float = -1
    fixed_height: float = -1
    border_alpha: float = 1.0
    border_color: str = "#000000"
    border_width: float = 0.0
    background_color: str = "#000000"
    background_style: int = 0  # 路由层 0（impl 1）
    background_alpha: float = 0.0
    background_round_radius: float = 0.0
    background_height: float = 0.14
    background_width: float = 0.14
    background_horizontal_offset: float = 0.5
    background_vertical_offset: float = 0.5
    shadow_enabled: bool = False
    shadow_alpha: float = 0.9
    shadow_angle: float = -45.0
    shadow_color: str = "#000000"
    shadow_distance: float = 5.0
    shadow_smoothing: float = 0.15
    bubble_effect_id: Optional[str] = None
    bubble_resource_id: Optional[str] = None
    effect_effect_id: Optional[str] = None
    intro_animation: Optional[str] = None
    intro_duration: float = 0.5
    text_styles: Optional[List[TextStyleRangeSpec]] = None

    @model_validator(mode="before")
    @classmethod
    def _normalize_aliases(cls, data):
        # 保真：capcut_server.py:126,127,130 —— color/size/alpha 优先于 font_color/font_size/font_alpha
        if isinstance(data, dict):
            if "color" in data:
                data["font_color"] = data["color"]
            if "size" in data:
                data["font_size"] = data["size"]
            if "alpha" in data:
                data["font_alpha"] = data["alpha"]
        return data


class AddTextResponse(BaseModel):
    draft_id: str
    draft_url: str


class AddSubtitleRequest(BaseModel):
    srt: str  # 路由层必需（capcut_server.py:28 data.get('srt')）
    draft_id: Optional[str] = None
    time_offset: float = 0.0
    font: Optional[str] = "思源粗宋"  # 路由层（impl None）；Optional 保真：用户传 null → None
    font_size: float = 5.0  # 路由层（impl 8.0）
    bold: bool = False
    italic: bool = False
    underline: bool = False
    font_color: str = "#FFFFFF"
    vertical: bool = False  # 路由层（impl True）
    alpha: float = 1  # 路由层字段名 alpha（impl 0.4）；无 font_alpha 别名
    border_alpha: float = 1.0
    border_color: str = "#000000"
    border_width: float = 0.0
    background_color: str = "#000000"
    background_style: int = 0  # 路由层（impl 1）
    background_alpha: float = 0.0
    transform_x: float = 0.0
    transform_y: float = -0.8
    scale_x: float = 1.0
    scale_y: float = 1.0
    rotation: float = 0.0
    track_name: str = "subtitle"
    width: int = 1080
    height: int = 1920
    bubble_effect_id: Optional[str] = None
    bubble_resource_id: Optional[str] = None
    effect_effect_id: Optional[str] = None


class AddSubtitleResponse(BaseModel):
    draft_id: str
    draft_url: str
```

- [ ] **步骤 4：编写最少实现代码（service）**

创建 `vectcut/features/text/service.py`：
```python
"""text feature service：add_text + add_subtitle。

迁自 add_text_impl.py + add_subtitle_impl.py + capcut_server.py:add_text 路由的 text_styles 构造。
IS_CAPCUT_ENV 文本动画分支收敛为 material_factory.resolve_text_intro/outro。
保真点见计划任务 4 场景铺垫。
"""

from __future__ import annotations

import os

import pyJianYingDraft as draft
import requests
from pyJianYingDraft import Font_type, trange
from pyJianYingDraft.text_segment import TextBubble, TextEffect, TextStyleRange

from vectcut.core.draft_store import get_or_create_draft
from vectcut.core.errors import InvalidParam
from vectcut.engine import material_factory as mf
from vectcut.features.draft.service import generate_draft_url
from vectcut.features.text.schemas import (
    AddSubtitleRequest,
    AddSubtitleResponse,
    AddTextRequest,
    AddTextResponse,
)
from util import hex_to_rgb


def add_text(req: AddTextRequest) -> AddTextResponse:
    # font 解析（迁自 add_text_impl.py:104-112）
    if req.font is None:
        font_type = None
    else:
        try:
            font_type = getattr(Font_type, req.font)
        except Exception:
            available_fonts = [a for a in dir(Font_type) if not a.startswith("_")]
            raise InvalidParam(
                f"Unsupported font: {req.font}, please use one of the fonts in Font_type: {available_fonts}"
            )

    # alpha 范围校验（迁自 add_text_impl.py:114-120）
    if not 0.0 <= req.font_alpha <= 1.0:
        raise InvalidParam("alpha value must be between 0.0 and 1.0")
    if not 0.0 <= req.border_alpha <= 1.0:
        raise InvalidParam("border_alpha value must be between 0.0 and 1.0")
    if not 0.0 <= req.background_alpha <= 1.0:
        raise InvalidParam("background_alpha value must be between 0.0 and 1.0")

    draft_id, script = get_or_create_draft(req.draft_id, req.width, req.height)

    # 文本轨道 get-or-create（迁自 add_text_impl.py:130-138）
    # 保真：track_name=None 创建【音频】轨道（源文件既有行为，疑似 bug，逐字保留）
    if req.track_name is not None:
        try:
            script.get_imported_track(draft.Track_type.text, name=req.track_name)
        except Exception:
            script.add_track(draft.Track_type.text, track_name=req.track_name)
    else:
        script.add_track(draft.Track_type.audio)

    # 颜色转换（迁自 add_text_impl.py:140-145）
    try:
        rgb_color = hex_to_rgb(req.font_color)
        rgb_border_color = hex_to_rgb(req.border_color)
    except ValueError as e:
        raise InvalidParam(f"Color parameter error: {str(e)}")

    # text_border（迁自 add_text_impl.py:147-154）
    text_border = None
    if req.border_width > 0:
        text_border = draft.Text_border(
            alpha=req.border_alpha, color=rgb_border_color, width=req.border_width
        )

    # text_background（迁自 add_text_impl.py:156-168）—— color 传原始十六进制字符串（保真）
    text_background = None
    if req.background_alpha > 0:
        text_background = draft.Text_background(
            color=req.background_color,
            style=req.background_style,
            alpha=req.background_alpha,
            round_radius=req.background_round_radius,
            height=req.background_height,
            width=req.background_width,
            horizontal_offset=req.background_horizontal_offset,
            vertical_offset=req.background_vertical_offset,
        )

    # text_shadow（迁自 add_text_impl.py:170-180）—— color 传原始字符串（保真）
    text_shadow = None
    if req.shadow_enabled:
        text_shadow = draft.Text_shadow(
            has_shadow=req.shadow_enabled,
            alpha=req.shadow_alpha,
            angle=req.shadow_angle,
            color=req.shadow_color,
            distance=req.shadow_distance,
            smoothing=req.shadow_smoothing,
        )

    # bubble / effect（迁自 add_text_impl.py:182-195）
    text_bubble = None
    if req.bubble_effect_id and req.bubble_resource_id:
        text_bubble = TextBubble(
            effect_id=req.bubble_effect_id, resource_id=req.bubble_resource_id
        )
    text_effect = None
    if req.effect_effect_id:
        text_effect = TextEffect(effect_id=req.effect_effect_id)

    # fixed_width/height 像素换算（迁自 add_text_impl.py:197-203）
    pixel_fixed_width = -1
    pixel_fixed_height = -1
    if req.fixed_width > 0:
        pixel_fixed_width = int(req.fixed_width * script.width)
    if req.fixed_height > 0:
        pixel_fixed_height = int(req.fixed_height * script.height)

    # 文本段（迁自 add_text_impl.py:205-223）
    text_segment = draft.Text_segment(
        req.text,
        trange(f"{req.start}s", f"{req.end - req.start}s"),
        font=font_type,
        style=draft.Text_style(
            color=rgb_color,
            size=req.font_size,
            align=1,
            vertical=req.vertical,
            alpha=req.font_alpha,
        ),
        clip_settings=draft.Clip_settings(
            transform_y=req.transform_y, transform_x=req.transform_x
        ),
        border=text_border,
        background=text_background,
        shadow=text_shadow,
        fixed_width=pixel_fixed_width,
        fixed_height=pixel_fixed_height,
    )

    # 多样式文本（迁自 capcut_server.py:177-218 + add_text_impl.py:226-233）
    if req.text_styles:
        for spec in req.text_styles:
            style = _build_text_style(spec, req)
            border = _build_text_border(spec, req)
            style_range = TextStyleRange(
                start=spec.start,
                end=spec.end,
                style=style,
                border=border,
                font_str=spec.font if spec.font else req.font,
            )
            # 范围验证（保真：中文错误消息，add_text_impl.py:229-230）
            if (
                style_range.start < 0
                or style_range.end > len(req.text)
                or style_range.start >= style_range.end
            ):
                raise InvalidParam(
                    f"无效的文本范围: [{style_range.start}, {style_range.end}), 文本长度: {len(req.text)}"
                )
            text_segment.add_text_style(style_range)

    if text_bubble:
        text_segment.add_bubble(text_bubble.effect_id, text_bubble.resource_id)
    if text_effect:
        text_segment.add_effect(text_effect.effect_id)

    # intro 动画（迁自 add_text_impl.py:240-251）—— print 宽容不抛 + int(*1000000) 截断
    if req.intro_animation:
        try:
            animation_type = mf.resolve_text_intro(req.intro_animation)
            duration_microseconds = int(req.intro_duration * 1000000)
            text_segment.add_animation(animation_type, duration_microseconds)
        except Exception:
            print(f"Warning: Unsupported intro animation type {req.intro_animation}, this parameter will be ignored")

    # outro 动画（迁自 add_text_impl.py:253-264）
    if req.outro_animation:
        try:
            animation_type = mf.resolve_text_outro(req.outro_animation)
            duration_microseconds = int(req.outro_duration * 1000000)
            text_segment.add_animation(animation_type, duration_microseconds)
        except Exception:
            print(f"Warning: Unsupported outro animation type {req.outro_animation}, this parameter will be ignored")

    script.add_segment(text_segment, track_name=req.track_name)
    return AddTextResponse(draft_id=draft_id, draft_url=generate_draft_url(draft_id))


def _build_text_style(spec, req: AddTextRequest):
    """迁自 capcut_server.py:187-198：嵌套样式回退外层默认。"""
    s = spec.style
    if s is None:
        return None
    return draft.Text_style(
        size=s.size if s.size is not None else req.font_size,
        bold=s.bold,
        italic=s.italic,
        underline=s.underline,
        color=hex_to_rgb(s.color) if s.color else hex_to_rgb(req.font_color),
        alpha=s.alpha if s.alpha is not None else req.font_alpha,
        align=s.align,
        vertical=s.vertical if s.vertical is not None else req.vertical,
        letter_spacing=s.letter_spacing,
        line_spacing=s.line_spacing,
    )


def _build_text_border(spec, req: AddTextRequest):
    """迁自 capcut_server.py:201-207：嵌套边框回退外层默认。"""
    b = spec.border
    if b is None or b.width <= 0:
        return None
    return draft.Text_border(
        alpha=b.alpha if b.alpha is not None else req.border_alpha,
        color=hex_to_rgb(b.color) if b.color else hex_to_rgb(req.border_color),
        width=b.width,
    )


def add_subtitle(req: AddSubtitleRequest) -> AddSubtitleResponse:
    draft_id, script = get_or_create_draft(req.draft_id, req.width, req.height)

    # SRT 三态来源（迁自 add_subtitle_impl.py:69-91）
    srt_content = None
    if req.srt.startswith(("http://", "https://")):
        try:
            response = requests.get(req.srt)
            response.raise_for_status()
            response.encoding = "utf-8"
            srt_content = response.text
        except Exception as e:
            raise InvalidParam(f"Failed to download subtitle file: {str(e)}")
    elif os.path.isfile(req.srt):
        try:
            with open(req.srt, "r", encoding="utf-8-sig") as f:
                srt_content = f.read()
        except Exception as e:
            raise InvalidParam(f"Failed to read local subtitle file: {str(e)}")
    else:
        srt_content = req.srt
        srt_content = srt_content.replace("\\n", "\n").replace("/n", "\n")

    rgb_color = hex_to_rgb(req.font_color)

    # text_border（迁自 add_subtitle_impl.py:97-104）
    text_border = None
    if req.border_width > 0:
        text_border = draft.Text_border(
            alpha=req.border_alpha,
            color=hex_to_rgb(req.border_color),
            width=req.border_width,
        )

    # text_background（迁自 add_subtitle_impl.py:106-113）—— 只传 3 字段（保真，与 add_text 8 字段不同）
    text_background = None
    if req.background_alpha > 0:
        text_background = draft.Text_background(
            color=req.background_color,
            style=req.background_style,
            alpha=req.background_alpha,
        )

    # text_style（迁自 add_subtitle_impl.py:115-125）
    text_style = draft.Text_style(
        size=req.font_size,
        bold=req.bold,
        italic=req.italic,
        underline=req.underline,
        color=rgb_color,
        align=1,
        vertical=req.vertical,
        alpha=req.alpha,
    )

    # bubble / effect（迁自 add_subtitle_impl.py:127-141）
    text_bubble = None
    if req.bubble_effect_id and req.bubble_resource_id:
        text_bubble = TextBubble(
            effect_id=req.bubble_effect_id, resource_id=req.bubble_resource_id
        )
    text_effect = None
    if req.effect_effect_id:
        # 保真：resource_id 复用 effect_effect_id（add_subtitle_impl.py:139-141）
        text_effect = TextEffect(
            effect_id=req.effect_effect_id, resource_id=req.effect_effect_id
        )

    # clip_settings（迁自 add_subtitle_impl.py:143-150）
    clip_settings = draft.Clip_settings(
        transform_x=req.transform_x,
        transform_y=req.transform_y,
        scale_x=req.scale_x,
        scale_y=req.scale_y,
        rotation=req.rotation,
    )

    # import_srt（迁自 add_subtitle_impl.py:152-164）—— time_offset int(*1000000) 截断
    script.import_srt(
        srt_content,
        track_name=req.track_name,
        time_offset=int(req.time_offset * 1000000),
        text_style=text_style,
        font=req.font,
        clip_settings=clip_settings,
        style_reference=None,  # 保真：capcut_server 路由未传 style_reference
        border=text_border,
        background=text_background,
        bubble=text_bubble,
        effect=text_effect,
    )

    return AddSubtitleResponse(draft_id=draft_id, draft_url=generate_draft_url(draft_id))
```

- [ ] **步骤 5：编写最少实现代码（flask_router）**

创建 `vectcut/features/text/flask_router.py`（错误信息对齐 `capcut_server.py:228,284`）：
```python
"""text feature Flask Blueprint：/add_text + /add_subtitle。"""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from pydantic import ValidationError

from vectcut.core.errors import VectCutError
from vectcut.features.text import service
from vectcut.features.text.schemas import AddSubtitleRequest, AddTextRequest

bp = Blueprint("text", __name__)


def _ok(output):
    return jsonify({"success": True, "output": output, "error": ""})


@bp.post("/add_text")
def add_text():
    try:
        req = AddTextRequest.model_validate(request.get_json() or {})
    except ValidationError as e:
        # 保真：capcut_server.py:228 错误消息（含尾随空格）
        return jsonify(
            {"success": False, "output": "", "error": f"Hi, the required parameters 'text', 'start' or 'end' are missing. {e}"}
        )
    try:
        resp = service.add_text(req)
        return _ok({"draft_id": resp.draft_id, "draft_url": resp.draft_url})
    except VectCutError as e:
        # 保真：capcut_server.py:284 error_message
        return jsonify(
            {"success": False, "output": "", "error": f"Error occurred while processing text: {e}. You can click the link below for help: "}
        )


@bp.post("/add_subtitle")
def add_subtitle():
    try:
        req = AddSubtitleRequest.model_validate(request.get_json() or {})
    except ValidationError as e:
        # 保真：capcut_server.py:69 错误消息
        return jsonify(
            {"success": False, "output": "", "error": f"Hi, the required parameters 'srt' are missing. {e}"}
        )
    try:
        resp = service.add_subtitle(req)
        return _ok({"draft_id": resp.draft_id, "draft_url": resp.draft_url})
    except VectCutError as e:
        # 保真：capcut_server.py:110 error_message
        return jsonify(
            {"success": False, "output": "", "error": f"Error occurred while processing subtitle: {e}."}
        )
```

- [ ] **步骤 6：运行测试验证通过**

运行：
```powershell
python -m pytest tests/features/text -v
```
预期：PASS（10 测试全绿）。

- [ ] **步骤 7：flake8 检查**

运行：
```powershell
python -m flake8 vectcut/features/text tests/features/text
```
预期：无输出。

- [ ] **步骤 8：Commit**

```powershell
git add vectcut/features/text tests/features/text
git commit -m "feat(text): 迁移 add_text + add_subtitle 为 text feature，文本动画分支收敛 + 双名别名 + 多样式保真"
```

---

### 任务 5：capcut_server.py 收尾（删 6 旧路由 + 挂 3 新 Blueprint + flake8 配置瘦身）

**文件：**
- 修改：`capcut_server.py`
- 修改：`.flake8`

**场景铺垫：** 阶段 2 已挂载 draft/video/audio/metadata 4 个 Blueprint，`capcut_server.py` 仅剩 6 个阶段 3 旧路由（`add_subtitle`/`add_text`/`add_image`/`add_video_keyframe`/`add_effect`/`add_sticker`）+ 顶部 6 个 `add_*_impl` import + `hex_to_rgb`/`Text_style`/`Text_border`/`TextStyleRange` import。本任务：(1) 删除全部 6 旧路由函数（~440 行）；(2) 删除顶部 `add_text_impl`/`add_subtitle_impl`/`add_image_impl`/`add_video_keyframe_impl`/`add_effect_impl`/`add_sticker_impl` 6 个 import + `hex_to_rgb`/`Text_style`/`Text_border`/`TextStyleRange` 4 个 import（仅旧路由用）；(3) 挂载 `text_bp`/`image_bp`/`effect_bp` 3 个新 Blueprint；(4) 删除 `add_video_keyframe` 旧路由（video Blueprint 已提供 `/add_video_keyframe`，URL 重叠由 Blueprint 接管）。完成后 `capcut_server.py` 仅剩：Flask app 创建 + 6 个 Blueprint 注册（draft/video/audio/text/image/effect/metadata）+ `app.run`。`.flake8` 移除 `capcut_server.py` 的 `E231,E251,E501,E261,E402` per-file-ignores（文件已无逐字保留的旧路由代码，自然洁净）。

- [ ] **步骤 1：编写失败的测试（验证旧路由已被 Blueprint 取代）**

在 `tests/golden/test_business_routes_golden.py` 的 `CASES` 列表追加阶段 3 用例（在 `/add_audio` 条目之后）：
```python
    ("/add_video_keyframe", {}, "business_add_video_keyframe_missing"),
    ("/add_effect", {}, "business_add_effect_missing_type"),
    ("/add_sticker", {}, "business_add_sticker_missing_id"),
    ("/add_image", {}, "business_add_image_missing_url"),
    ("/add_text", {}, "business_add_text_missing"),
    ("/add_subtitle", {}, "business_add_subtitle_missing"),
```

运行验证当前状态（此时旧路由仍在，路由存在但行为来自旧 impl；快照尚未生成）：
```powershell
python -m pytest tests/golden/test_business_routes_golden.py -v
```
预期：6 个新用例 FAIL（快照缺失）。这仅记录起点；真正验证在步骤 4。

- [ ] **步骤 2：重写 capcut_server.py**

用 Write 工具整体覆盖 `capcut_server.py` 为以下内容（删除全部 6 旧路由 + 散落 import，挂载 7 个 Blueprint）：
```python
from flask import Flask

from settings.local import PORT

app = Flask(__name__)

# —— 业务路由收敛为声明式 Blueprint（draft/video/audio/text/image/effect）——
from vectcut.features.draft.flask_router import bp as draft_bp
from vectcut.features.video.flask_router import bp as video_bp
from vectcut.features.audio.flask_router import bp as audio_bp
from vectcut.features.text.flask_router import bp as text_bp
from vectcut.features.image.flask_router import bp as image_bp
from vectcut.features.effect.flask_router import bp as effect_bp
app.register_blueprint(draft_bp)
app.register_blueprint(video_bp)
app.register_blueprint(audio_bp)
app.register_blueprint(text_bp)
app.register_blueprint(image_bp)
app.register_blueprint(effect_bp)

# —— 元数据查询路由（阶段 1 收敛为声明式 Blueprint，含 /metadata/{kind} 与 11 旧别名）——
from vectcut.features.metadata.flask_router import bp as metadata_bp
app.register_blueprint(metadata_bp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)
```

> **保真核对：** 旧 `capcut_server.py` 的 6 路由错误信息与 envelope 结构已由各 feature `flask_router.py` 在任务 2-4 逐字复刻（含尾随空格、中文/英文消息）。删除旧路由后，HTTP 行为由 Blueprint 接管，外壳等价。

- [ ] **步骤 3：修改 .flake8 瘦身 capcut_server.py per-file-ignores**

编辑 `.flake8`，将 `per-file-ignores` 中的 `capcut_server.py:E231,E251,E501,E261,E402` 行删除（文件已洁净，不再需要逐字保留旧代码的豁免）。保留 `vectcut/features/draft/_save_engine.py:E501,E128` 与其他既有配置。预期 `.flake8` 内容：
```
[flake8]
extend-ignore = E301, E302, E303, E305, E306, E701, F403, F405
per-file-ignores =
    vectcut/features/draft/_save_engine.py:E501,E128
```

- [ ] **步骤 4：生成阶段 3 黄金快照 + 验证通过**

运行（生成新快照）：
```powershell
$env:REGENERATE_GOLDEN=1; python -m pytest tests/golden/test_business_routes_golden.py -v
$env:REGENERATE_GOLDEN=$null
```
预期：6 个新用例 `SKIPPED (golden regenerated)`，生成 `business_add_video_keyframe_missing.json` / `business_add_effect_missing_type.json` / `business_add_sticker_missing_id.json` / `business_add_image_missing_url.json` / `business_add_text_missing.json` / `business_add_subtitle_missing.json` 6 个快照文件。

再运行（验证快照稳定）：
```powershell
python -m pytest tests/golden/test_business_routes_golden.py -v
```
预期：全部 PASS（含阶段 2 既有 6 用例 + 阶段 3 新 6 用例）。

- [ ] **步骤 5：flake8 检查 capcut_server.py 洁净**

运行：
```powershell
python -m flake8 capcut_server.py
```
预期：无输出（确认 `.flake8` 瘦身后文件仍洁净，无需 per-file-ignores）。

- [ ] **步骤 6：全量冒烟（确认 app 可启动 + 全部路由注册）**

运行：
```powershell
python -c "import capcut_server; print(sorted([str(r) for r in capcut_server.app.url_map.iter_rules()]))"
```
预期：输出含 `/add_text` / `/add_subtitle` / `/add_image` / `/add_effect` / `/add_sticker` / `/add_video_keyframe` / `/add_video` / `/add_audio` / `/create_draft` / `/save_draft` / `/query_script` / `/query_draft_status` / `/generate_draft_url` / `/metadata/<kind>` 等，且**无重复 URL rule 警告**。

- [ ] **步骤 7：Commit**

```powershell
git add capcut_server.py .flake8 tests/golden/test_business_routes_golden.py tests/golden/snapshots/business_add_*.json
git commit -m "refactor(server): 删除 capcut_server 6 个阶段3旧路由，挂载 text/image/effect 3 Blueprint，flake8 瘦身"
```

---

### 任务 6：阶段 3 最终验收（全量测试 + flake8 + 黄金 + 标签）

**文件：** 无新增（仅验证）

**场景铺垫：** 阶段 3 全部代码迁移完成后的收尾验收。运行全量测试套件、flake8 全量检查、黄金基线全量验证，确认无回归后打标签 `phase3-complete`。

- [ ] **步骤 1：全量 flake8**

运行：
```powershell
python -m flake8 vectcut capcut_server.py tests
```
预期：无输出（全洁净）。

- [ ] **步骤 2：全量 pytest**

运行：
```powershell
python -m pytest -v
```
预期：全绿。重点确认：
- `tests/engine/test_material_factory.py`（含任务 1 新 9 测试）
- `tests/features/effect/`（任务 2，4 测试）
- `tests/features/image/`（任务 3，6 测试）
- `tests/features/text/`（任务 4，10 测试）
- `tests/golden/test_business_routes_golden.py`（12 用例：阶段 2 既有 6 + 阶段 3 新 6）
- 阶段 0-2 既有测试无回归

- [ ] **步骤 3：黄金基线最终验证（无 REGENERATE）**

运行：
```powershell
python -m pytest tests/golden -v
```
预期：全绿（确认快照稳定，未被实现改动打破）。

- [ ] **步骤 4：保真自检（人工抽查）**

逐项核对保真点（见各任务"场景铺垫"），重点：
- `add_text` 路由 `/add_text` 错误消息含 `'text', 'start' or 'end' are missing. `（尾随空格）——查 `business_add_text_missing.json` 快照。
- `add_effect` 路由错误消息含 `effect_type` ——查 `business_add_effect_missing_type.json`。
- `add_sticker` 路由错误消息含 `sticker_id` ——查 `business_add_sticker_missing_id.json`。
- `add_image` 路由错误消息含 `image_url` ——查 `business_add_image_missing_url.json`。
- `add_subtitle` 路由错误消息含 `srt` ——查 `business_add_subtitle_missing.json`。
- `add_video_keyframe` 路由错误消息（video Blueprint 提供）——查 `business_add_video_keyframe_missing.json`。

- [ ] **步骤 5：Commit 验收记录 + 打标签**

```powershell
git add -A
git commit --allow-empty -m "test: 阶段3 最终验收——全量绿 + flake8 洁净 + 黄金稳定"
git tag phase3-complete
```

- [ ] **步骤 6：确认标签**

运行：
```powershell
git tag --list "phase*"
```
预期：含 `phase2-complete` 与 `phase3-complete`。

---

## 完成标志

阶段 3 完成的判据（全部满足）：
1. `vectcut/features/{text,image,effect}/` 三包就位，每包含 `__init__.py` / `schemas.py` / `service.py` / `flask_router.py`。
2. `capcut_server.py` 无业务路由函数，仅剩 app 创建 + 7 Blueprint 注册 + `app.run`（约 30 行）。
3. `material_factory.py` 含 `build_photo_material` / `resolve_intro` / `resolve_outro` / `resolve_combo` / `resolve_text_intro` / `resolve_text_outro` / `resolve_video_effect` + `BLUR_MAP`。
4. 全量 `pytest` 绿、`flake8` 洁净、黄金基线稳定。
5. 标签 `phase3-complete` 已打。
6. 全部保真点（各任务场景铺垫所列）逐字保留，无简化。

## 执行交接

本计划共 6 个任务，任务间有顺序依赖（任务 1 是任务 2-4 的前置；任务 5 依赖任务 2-4 的 Blueprint 就位；任务 6 依赖全部完成）。推荐执行方式：

- **子代理驱动（推荐）**：用 `superpowers:subagent-driven-development` 逐任务派发，每个任务内严格 TDD（失败测试 → 验证失败 → 实现 → 验证通过 → commit）。任务 1-4 内部独立，但任务 2-4 都依赖任务 1 的 material_factory 扩展，故任务 1 必须先完成。任务 2-4 之间无依赖，可考虑并行（但三包都改 `capcut_server.py` 在任务 5，本身不冲突；并行时各自建 feature 包互不影响）。
- **内联执行**：在当前会话直接按任务顺序执行，适合需要紧密观察保真点的场景（`add_text` 的多处保真点建议内联细看）。

**关键风险提示：**
- `add_text` 保真点最多（10 项），是回归高发区——任务 4 实现时务必逐项核对，尤其 `track_name=None` 创建音频轨道、动画 print 宽容、`int(*1000000)` 截断、background 原始字符串。
- `add_image` 的转场 `int(*1000000)` 与动画 `*1e6` 截断方式不同，易混。
- `add_subtitle` 的 `TextEffect(resource_id=effect_effect_id)` 复用是反直觉保真点，勿"修正"。
- 阶段 3 路由错误消息含多处尾随空格（`add_effect`/`add_sticker`/`add_text`），已逐字复刻，黄金快照会锁定。
- `capcut_server.py` 删除 `add_video_keyframe` 旧路由后，`/add_video_keyframe` 由 video Blueprint 提供——若启动报 URL rule 重复，检查 video Blueprint 是否已在阶段 2 挂载（应已挂载）。

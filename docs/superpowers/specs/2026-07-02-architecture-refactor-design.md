# VectCutAPI 架构重排设计

- 日期：2026-07-02
- 状态：已实现（阶段 0–5 全部完成，2026-07-03）
- 范围：应用层整体架构重排（不含 `pyJianYingDraft` 引擎层内部）

## 1. 背景与问题诊断

VectCutAPI 是一个面向 AI Agent 的视频剪辑工具，提供 HTTP API 与 MCP 两种接入方式，底层基于 `pyJianYingDraft` 引擎生成剪映/CapCut 草稿。

当前应用层结构混乱，主要表现为 7 类问题：

| # | 问题 | 证据 |
|---|------|------|
| 1 | 根目录平铺 40+ 个 .py 文件，角色完全不分离 | HTTP 入口、MCP 入口、业务实现（`add_*_impl`/`add_*_track`）、工具（`util`/`oss`/`downloader`/`draft_cache`）、示例（`example.py` 88KB）、测试、调试脚本（`jy_decrypt.py`/`gen_local_draft.py`/`shuangnan.plain.json`）全堆在根目录 |
| 2 | 上帝文件 | `capcut_server.py` 54KB（30 路由 + 14 个 `get_xxx_types`）、`save_draft_impl.py` 37KB、`example.py` 88KB |
| 3 | 双入口各自为政 | `capcut_server.py`（Flask）与 `mcp_server.py` 各自 import 一堆 `add_*`，参数校验/错误处理/返回格式两套 |
| 4 | 配置双轨制 | 根目录 `config.json` + `settings/` 包两处定义同一组配置，且默认值已漂移（PORT 9000 vs 9001、DRAFT_DOMAIN 默认值不一致） |
| 5 | 命名不统一 | `add_text_impl` vs `add_video_track` vs `add_audio_track` vs `save_draft_impl`，后缀混用 |
| 6 | 项目身份混乱 | `pyproject.toml` name=`capcut-api`、Homepage=`ashreo/CapCutAPI`、仓库=`sun-guannan/VectCutAPI`、品牌=`VectCut` |
| 7 | 资源目录冗余 | `template/` `template_jianying/` `template_jianying_10_2/` `pattern/` `examples/` 边界不清 |

底层引擎 `pyJianYingDraft/` 反而是结构最清晰的部分（有 `metadata/`、`segment.py`、`track.py` 等合理拆分）。**"乱"集中在应用层（根目录文件），不在引擎层。**

### 1.1 重构中发现的两个硬约束

1. **循环依赖**：`pyJianYingDraft/video_segment.py:14` 和 `script_file.py:22` 反向 `import` 了应用层的 `settings`（`from settings import IS_CAPCUT_ENV` / `from settings.local import IS_CAPCUT_ENV`）。应用层依赖引擎，引擎又依赖应用层 `settings`。在"引擎只读不改"约束下，`settings/` 不能直接删。
2. **死代码**：`settings/__init__.py` 的 `__all__` 声明了 `API_KEYS / MODEL_CONFIG / PURCHASE_LINKS / LICENSE_CONFIG`，全项目无人定义、无人使用；`get_platform_info()` 与 `draft_profiles.py` 的 `CAPCUT_PLATFORM` 重复且无调用方。

## 2. 约束

| 约束 | 决策 |
|------|------|
| 对外兼容性 | **允许 breaking change**（HTTP 路由、MCP tool 名可重新设计） |
| 引擎层 | **只读上游，不改** `pyJianYingDraft` 包内部 |
| 执行方式 | 团队集中重构，可分阶段但每阶段可独立交付、出 release |
| HTTP 框架 | **从 Flask 迁移到 FastAPI**（pyproject 已声明 fastapi/uvicorn 依赖但未使用） |

## 3. 目标架构

选定方案：**🅰 分层 + Feature 包**（HTTP/MCP 退为薄入口，共用 `features.*.service` + `schemas`）。否决方案见 §8。

### 3.1 包结构

```
VectCutAPI/
├─ pyproject.toml          # name 统一为 vectcut
├─ config.json             # 唯一运行时配置源
├─ run_http.py             # FastAPI 入口（替代 capcut_server.py）
├─ run_mcp.py              # MCP 入口（替代 mcp_server.py）
│
├─ vectcut/                # ── 主包 ──
│   ├─ core/               # 跨切面基础设施
│   │   ├─ config.py       #   读 config.json → 强类型 Settings（Pydantic）
│   │   ├─ errors.py       #   统一异常基类 + 错误码
│   │   ├─ logging.py
│   │   ├─ draft_store.py  #   draft_cache + draft_profiles 合并
│   │   ├─ oss.py
│   │   └─ downloader.py
│   │
│   ├─ engine/             # 对只读 pyJianYingDraft 的薄适配层
│   │   ├─ adapter.py      #   收敛引擎 import + 平台枚举派发
│   │   └─ material_factory.py
│   │
│   ├─ schemas/            # Pydantic 请求/响应模型，HTTP 与 MCP 共用（单一事实源）
│   │
│   ├─ features/           # 业务能力，按剪辑领域分包
│   │   ├─ draft/          #   create / save / query / get_duration
│   │   ├─ video/          #   add_video + video_keyframe
│   │   ├─ audio/          #   add_audio
│   │   ├─ text/           #   add_text + add_subtitle
│   │   ├─ image/          #   add_image
│   │   ├─ effect/         #   add_effect + add_sticker
│   │   └─ metadata/       #   14 个 get_xxx_types 收敛
│   │   （每个 feature 包内：service.py + schemas.py + router.py）
│   │
│   └─ server/
│       ├─ http/           #   FastAPI app 组装 + 挂载各 feature router
│       └─ mcp/            #   MCP server 组装 + tool 注册表化
│
├─ settings/               # 降级为 config.py 的薄转发垫片（仅供引擎两处 IS_CAPCUT_ENV import）
├─ scripts/                # 一次性/调试脚本（jy_decrypt.py, gen_local_draft.py）
├─ examples/               # example.py 拆分 + pattern/ 并入
├─ tests/
├─ template/               # 保留引擎所需模板资源
├─ pyJianYingDraft/        # 只读上游，原样不动
└─ README.md / docs/
```

**关键决策**：
- 根目录只留入口脚本与配置，业务全进 `vectcut/` 包。
- 每个 feature 包是自洽单元：`service.py`（纯 Python 业务，不依赖 web/MCP 框架）+ 该 feature 私有 `schemas.py` + 薄 `router.py`。
- `core/draft_store.py` 合并 `draft_cache.py` + `draft_profiles.py`（二者本就管同一件事）。
- `engine/` 是适配层，不修改 `pyJianYingDraft` 本身；应用层只有 `engine/` 一处依赖引擎。
- `save_draft_impl.py`（37KB）在 `features/draft/` 内按职责拆分（save_draft / query_task_status / query_script / 上传/URL 生成）。

## 4. 双入口统一 + Schema 共用 + 错误处理

### 4.1 service 层契约

`service.py` 是纯 Python，不 import 任何 web/MCP 框架。签名统一：接收强类型请求模型，返回响应模型，或抛项目内异常。draft 对象在 service 内部通过 `draft_store.get_draft(req.draft_id)` 获取，不作为参数从入口传入（保持 service 签名干净）。

以 `add_video` 为例三文件分工：

```python
# vectcut/schemas/video.py —— 两入口共用的事实源
class AddVideoRequest(BaseModel):
    draft_id: str
    video_url: str
    start: float = 0
    end: float = 0
    width: int = 1080
    height: int = 1920
    track_name: str = "video_main"
    transition: str | None = None
    # ... 全部带类型 + 默认值 + 校验（替换散落的 data.get('xxx', 默认)）

class AddVideoResponse(BaseModel):
    draft_id: str
    track_name: str
    duration: float
```

```python
# vectcut/features/video/service.py —— 唯一业务实现
def add_video(req: AddVideoRequest) -> AddVideoResponse:
    draft = get_draft(req.draft_id)
    if draft is None:
        raise DraftNotFound(req.draft_id)
    if req.end <= req.start:
        raise InvalidParam("end must be > start")
    material = build_video_material(req.video_url, ...)
    add_to_track(draft, material, req.track_name, req.start, req.end, ...)
    return AddVideoResponse(...)
```

### 4.2 HTTP 入口（薄）

```python
# vectcut/features/video/router.py
@router.post("/add_video", response_model=AddVideoResponse)
def add_video_endpoint(req: AddVideoRequest):
    return add_video(req)   # 异常由全局 handler 转 HTTP
```

FastAPI 用 Pydantic 自动校验请求体，`capcut_server.py` 每个路由那一长串 `data.get('xxx', default)` 全部消失。这是上帝文件瘦身的关键。

### 4.3 MCP 入口（薄，零业务逻辑）

MCP tool 的 `inputSchema` 直接从同一个 Pydantic 模型生成，不再手写一遍：

```python
# vectcut/server/mcp/tools_video.py
TOOL = {
    "name": "add_video",
    "description": "Add a video track to the draft.",
    "inputSchema": pydantic_to_input_schema(AddVideoRequest),   # 单一事实源
}
def handle(arguments: dict):
    return run_service(add_video, AddVideoRequest, arguments)   # validate → service → 响应
```

`run_service` 是共用工具函数：`req = Model.model_validate(arguments)` → `resp = service(req)` → `return resp.model_dump()`，异常转 MCP error。所有 tool handler 都调它，消除 `mcp_server.py` 现在的手写大分派。

### 4.4 统一错误处理

`core/errors.py` 定义业务异常基类与错误码，一套异常两处映射：

| 异常 | HTTP 映射 | MCP 映射 |
|------|-----------|----------|
| `DraftNotFound` | 404 | JSON-RPC -32001 |
| `InvalidParam` | 422 | -32002 |
| `EngineError`（pyJianYingDraft 抛出） | 500 | -32003 |
| `MediaDownloadError` | 502 | -32004 |

HTTP 端用 FastAPI 全局 exception handler 兜底；MCP 端在 `run_service` 内 try/except 转 JSON-RPC error。业务代码只 raise 领域异常，不写任何 to-HTTP 逻辑。错误码采用自定义 JSON-RPC 扩展码（-32xxx），便于客户端按码处理。

### 4.5 收益

- 加一个剪辑功能 = 一个 feature 包内加 service+schema+router，HTTP/MCP 同时获得，不再两处改。
- `capcut_server.py` 54KB 消失；`mcp_server.py` execute_tool 大分派注册表化。
- 参数校验从两套手写变为一处定义、两入口共用。

## 5. Engine 适配层 + 配置统一 + 元数据收敛

### 5.1 engine 适配层

现状：`capcut_server.py` 顶部 17 行 import 散落地从 `pyJianYingDraft.metadata.*` 与 `capcut_*` 拉符号，业务里用 `if IS_CAPCUT_ENV` 选 CapCut 版还是剪映版。

适配层做两件事：

**① 收敛 import + 按平台派发**：把"同一语义、两个平台枚举"绑成查找表，提供 `enums(kind)` 按当前激活 profile 的平台返回对应枚举。业务/元数据接口只调 `adapter.enums(kind)`，消除散落的 `if IS_CAPCUT_ENV`。

**② 材料/轨道构造工厂**：`material_factory.py` 封装散在 `add_*_track.py` 里的引擎调用，提供 `build_video_material / build_audio_material / add_to_track` 等。应用层不再直接 import `pyJianYingDraft` 顶层符号。

边界声明：适配层不修改 `pyJianYingDraft` 包本身，只 import 它。引擎升级或换 fork 时只改 `engine/` 一处。

### 5.2 配置统一（含循环依赖处理）

- `config.json` 是用户编辑的唯一文件。`vectcut/core/config.py` 用 Pydantic `Settings` 加载它（强类型，含 `OssConfig` 子模型）。
- 处理循环依赖：`settings/` **不删，降级为 `config.py` 的薄转发垫片**。新的 `settings/local.py` 只剩几行——从 `vectcut.core.config` 读 `Settings`，导出模块级常量 `IS_CAPCUT_ENV`（值 = `get_active_profile().is_capcut_env`），专供引擎那两处 import。依赖方向单一：引擎 → settings 垫片 → config.py（真源）。
- 旧 `settings/local.py` 的 json5 加载逻辑、漂移的默认值、死代码 `__all__`（`API_KEYS` 等 4 个）、`get_platform_info()` 全部删除。
- 引擎日后若升级去掉那两处 import，`settings/` 垫片即可彻底删除（在文档/TODO 标注）。
- `is_capcut_env` 在 `config.json` 标记废弃（`draft_profiles.py` 已有更准的 per-profile `is_capcut_env` 字段），过渡期保留读取，逐步移除。

### 5.3 元数据收敛

现状 14+ 个 `get_xxx_types` 接口各 ~30 行近乎复制（`result{success,output,error}` → 按 `IS_CAPCUT_ENV` 分支遍历 enum → jsonify）。改为声明式注册表：

- `features/metadata/registry.py`：`META_KINDS = { kind: (描述, 取值函数) }`，每个取值函数调 `adapter.enums(kind)`。
- `features/metadata/service.py`：`list_metadata(kind)` 返回 `[{"name": e.name} for e in getter()]`，KeyError → `InvalidParam`。
- `features/metadata/router.py`：一个参数化路由 `GET /metadata/{kind}` 替换 14 个具名路由。

收敛后 ~420 行 → < 50 行，新增一种枚举只加一行。

**路由兼容**：保留 14 个旧具名路径（`/get_intro_animation_types` 等）做别名（循环注册），同时提供新的 `/metadata/{kind}`。AI Agent 客户端不受影响。

## 6. 资源归位 + 项目身份统一

### 6.1 资源/脚本归位

| 现状 | 去向 |
|------|------|
| `template/` `template_jianying/` `template_jianying_10_2/` | 原地保留；引用路径改为相对 `vectcut/` 包，用 `importlib.resources` 定位 |
| `pattern/` 内容 | 并入 `examples/` |
| `example.py`（88KB） | 拆成 `examples/` 下多个小脚本，按功能模块切 |
| `jy_decrypt.py` `gen_local_draft.py` `shuangnan.plain.json` | 移入 `scripts/`，继续纳入 git |
| `rest_client_test.http` | 移入 `examples/` |
| `test_mcp_client.py` | 并入 `tests/` |

### 6.2 项目身份统一

- Python 主包名：`vectcut`；引擎包 `pyJianYingDraft` 保持不动。
- `pyproject.toml` name 改 `vectcut`（或 `vectcut-api`），Homepage/Repository URL 修正为 `sun-guannan/VectCutAPI`。
- 入口脚本 `run_http.py` / `run_mcp.py`；`mcp_config.json` 的 `command` 同步更新。
- README/MCP 文档统一品牌名 VectCut，CapCut/剪映作为"支持的平台"描述。历史名在文档里作为旧称提一句，代码层不保留别名。

## 7. 测试策略（TDD）

重构是"行为不变、结构变"，测试需先于迁移写到位：

- **黄金测试先建**：迁移前对现有 `capcut_server.py` 每个路由跑一遍，把"请求 → 生成的 draft json"存为黄金基线（`shuangnan.plain.json` 等已有 plain json 可作参考）。迁移后每个 feature 必须复现同样的 draft 输出，作为防回归安全网。
- feature 测试：`tests/features/test_video.py` 直接调 `service.add_video()`（不经 HTTP/MCP），断言草稿状态。
- HTTP 层：FastAPI TestClient，只验"路由→service 接线 + 错误码映射"。
- MCP 层：验证 `inputSchema` 从 Pydantic 生成正确 + tool 调用转发无误。
- 元数据：参数化测试覆盖 `/metadata/{kind}` 全部 kind + 14 个旧别名路径返回相同结果。

## 8. 迁移阶段（每阶段可独立交付 + 出 release）

| 阶段 | 内容 | 风险 |
|------|------|------|
| **0 骨架** | 建 `vectcut/` 包空骨架 + `core/config.py` + `settings/` 降级垫片 + `draft_store`（合并 cache/profiles）+ 黄金测试基线 | 低 |
| **1 engine + 元数据** | `engine/adapter.py` + `material_factory.py`；元数据注册表收敛 14 接口（保留旧别名） | 低 |
| **2 核心 features** | `draft` `video` `audio` 三个 feature 的 service+schema（含 `save_draft_impl` 拆分） | 中 |
| **3 其余 features** | `text` `image` `effect`（含 sticker） | 中 |
| **4 两入口落 FastAPI** | `server/http`（FastAPI routers）+ `server/mcp`（tool 注册表化）+ `run_http.py`/`run_mcp.py` | 高 |
| **5 清理收尾** | 删旧文件、拆 `example.py`、身份统一、文档更新、删 `settings/` 死代码 | 低 |

每阶段结束跑黄金测试 + 全量测试，绿了即出 release，随时可停在任一阶段。阶段 4 是唯一需一鼓作气切换的环节（Flask↔FastAPI 不能并存太久）。

## 9. 否决的方案

- **🅱 严格三层（controller/service/repository）**：横切分层导致加一个剪辑功能要在 3 个目录跳；对"按媒体类型天然分块"的领域是反模式；开源协作门槛升高。适合 CRUD 业务系统，不适合工具型项目。
- **🅲 物理整理（只挪文件 + 统一命名 + Flask→FastAPI）**：不抽象 service 层，`save_draft_impl.py` 37KB 上帝文件原样搬入，双入口割裂依旧。只适合个人项目渐进，不符合"团队集中、全都要治"诉求。

## 10. 非目标（YAGNI）

- 不重构 `pyJianYingDraft` 引擎内部（只读约束）。
- 不引入数据库/外部存储（草稿仍走文件 + 内存 cache）。
- 不做 API 版本化（v1/v2 路由前缀）——允许 breaking，无需多版本并存。
- 不拆微服务/多进程——保持单进程双入口。
- 不引入新的编排/插件框架——feature 包即足够。

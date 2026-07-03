# 阶段 4：双入口落 FastAPI + MCP 注册表化 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 把 7 个 feature 的 Flask Blueprint 替换为 FastAPI `APIRouter`，组装到 `vectcut/server/http/` 的统一 app；把手写 stdio JSON-RPC 的 `mcp_server.py`（~480 行、11 tool 的 `if/elif` 大分派 + 手写 inputSchema）改造为 `vectcut/server/mcp/`：tool 注册表（name → (service, RequestModel)）+ inputSchema 从 Pydantic 模型自动生成 + 共用 `run_service`。新增入口脚本 `run_http.py` / `run_mcp.py`。黄金测试全程保持绿色。

**架构：**
- HTTP：`server/http/app.py` 暴露 FastAPI `app`，挂载 7 个 feature 的 `router.py`（与现有 `flask_router.py` 同样的 `{success, output, error}` 外壳，HTTP 状态码恒为 200——**保真约束**：黄金测试 `assert resp.status_code == 200` 是硬约束，规格 §4.4 的语义状态码列为本阶段非目标）。FastAPI 全局 `RequestValidationError` 与 `VectCutError` handler 统一把异常转成 200 外壳，业务代码零 `to-HTTP` 逻辑。
- MCP：`server/mcp/registry.py` 一张 `TOOLS = {name: ToolSpec(service_fn, RequestModel, description)}` 表；`schema_gen.py` 用 `Model.model_json_schema()` 生成 `inputSchema`（单一事实源）；`runtime.py` 的 `run_service` 做 `model_validate(arguments) → service(req) → resp.model_dump()`，异常转 JSON-RPC `-32xxx` 错误码；`run_mcp.py` 是手写 stdio JSON-RPC 主循环（保留现有不依赖 SDK 的 stdio 协议，仅替换分派为查表）。
- 入口脚本 `run_http.py`（`uvicorn`）、`run_mcp.py`（调 `server.mcp.runtime.main()`）。

**技术栈：** FastAPI + uvicorn（pyproject 已声明，未使用）、Pydantic v2（service 层已用）、pytest + starlette `TestClient`（HTTP 测试）、手写 stdio JSON-RPC（MCP，不引第三方 SDK）。

**保真与黄金策略（贯穿全计划）：**
1. **HTTP 200 外壳保真**：每个 FastAPI 路由的响应体必须与对应 Flask 路由逐字一致——`success`/`output`/`error` 三键，错误消息文本与现有 `flask_router.py` 逐字对齐（含尾随空格、`Hi, the required parameters are missing.` 前缀）。`tests/golden/test_business_routes_golden.py` 与 `test_metadata_routes_golden.py` 是防回归网，迁移后跑通即证明保真。
2. **MCP 行为保真**：保留现有 `initialize` / `notifications/initialized` / `tools/list` / `tools/call` / `Method not found` 的 JSON-RPC 响应结构、`protocolVersion: 2024-11-05`、`serverInfo.name/version`。`tools/list` 返回的 inputSchema 从 Pydantic 生成——结构与现有手写 schema 字段语义对齐（字段名、类型、required 一致）。
3. **切换动作一次性**：任务 9 切换黄金测试的 `client` fixture 从 `capcut_server.app` 到 `vectcut.server.http.app`，是本阶段唯一"一鼓作气"环节，前面所有任务先把 FastAPI 侧建好并独立测试，最后一步才切换全局 fixture + 删旧入口。

---

## 文件结构

### 新建

| 文件 | 职责 |
|---|---|
| `vectcut/server/__init__.py` | 空 |
| `vectcut/server/http/__init__.py` | 导出 `app` |
| `vectcut/server/http/app.py` | FastAPI app 实例 + 全局 exception handler + 挂载 7 个 router |
| `vectcut/server/mcp/__init__.py` | 空 |
| `vectcut/server/mcp/registry.py` | `ToolSpec` + `TOOLS` 注册表（11 个 tool） |
| `vectcut/server/mcp/schema_gen.py` | `pydantic_to_input_schema(Model) -> dict` |
| `vectcut/server/mcp/runtime.py` | `run_service` + `handle_request` + `main`（stdio 主循环） |
| `vectcut/features/{draft,video,audio,text,image,effect}/router.py` | 7 个 FastAPI APIRouter（逐个 feature 一个） |
| `vectcut/features/metadata/router.py` | FastAPI APIRouter：`GET /metadata/{kind}` + 11 别名 |
| `vectcut/features/draft/schemas.py` 内补 `GetVideoDurationRequest/Response` | （修改，非新建）draft feature 增加 duration tool 的请求/响应模型 |
| `run_http.py` | uvicorn 入口 |
| `run_mcp.py` | MCP stdio 入口 |
| `tests/server/__init__.py`、`tests/server/http/__init__.py`、`tests/server/mcp/__init__.py` | 测试包 |
| `tests/server/http/test_app_envelope.py` | envelope / handler 单元测试 |
| `tests/server/mcp/test_schema_gen.py` | inputSchema 生成测试 |
| `tests/server/mcp/test_registry.py` | 注册表完整性测试 |
| `tests/server/mcp/test_runtime.py` | run_service + tools/list + tools/call 测试 |
| `tests/features/{draft,video,audio,text,image,effect,metadata}/test_fastapi_router.py` | 7 个 feature 的 FastAPI router 测试 |

### 修改

| 文件 | 改动 |
|---|---|
| `vectcut/features/draft/service.py` | 新增 `get_video_duration(req)` 公开 service（委托 `_save_engine.get_video_duration`，返回强类型响应） |
| `vectcut/features/draft/schemas.py` | 新增 `GetVideoDurationRequest/Response` |
| `tests/golden/test_business_routes_golden.py` | `client` fixture 切换到 `vectcut.server.http.app`（任务 9） |
| `tests/golden/test_metadata_routes_golden.py` | 同上切换 |
| `tests/features/*/test_router.py`（7 个 Flask 版） | 任务 9 后删除或保留——本计划保留 Flask 测试直到删除 `flask_router.py`（阶段 5），本阶段不删 |

### 本阶段不动

- `capcut_server.py` / `mcp_server.py`：任务 9 切换黄金测试后，本阶段最后（任务 10）才从 git 删除。
- 7 个 `flask_router.py`：保留到阶段 5 一并删。本阶段 FastAPI `router.py` 与之并存，黄金测试切换后 Flask 版无人引用即自动失效。
- 根目录 `util.py` / `oss.py` / `downloader.py` / `save_task_cache.py` / `create_draft.py` 等：仍被 `vectcut/` 包内 service 直接 import，内化到 `core/` 是阶段 5 的事，本阶段不动。

---

## 任务总览

| 任务 | 内容 |
|---|---|
| 1 | `server/http/app.py`：FastAPI app + envelope helper + 全局 handler（不挂 router） |
| 2 | draft feature FastAPI router + service 补 `get_video_duration` |
| 3 | video feature FastAPI router |
| 4 | audio feature FastAPI router |
| 5 | image feature FastAPI router |
| 6 | effect feature FastAPI router |
| 7 | text feature FastAPI router |
| 8 | metadata feature FastAPI router（参数化 + 11 别名） |
| 9 | 挂载全部 router + `run_http.py` + 黄金测试切换到 FastAPI app |
| 10 | MCP：schema_gen + registry + runtime + `run_mcp.py` |
| 11 | 删旧入口 `capcut_server.py` / `mcp_server.py` + 全量验收 |

---

## 任务 1：FastAPI app 骨架 + envelope + 全局 handler

**文件：**
- 创建：`vectcut/server/__init__.py`
- 创建：`vectcut/server/http/__init__.py`
- 创建：`vectcut/server/http/app.py`
- 创建：`tests/server/__init__.py`
- 创建：`tests/server/http/__init__.py`
- 创建：`tests/server/http/test_app_envelope.py`

- [ ] **步骤 1：编写失败的测试**

`tests/server/http/test_app_envelope.py`：

```python
"""FastAPI app 骨架测试：envelope 工具函数 + 全局异常 handler。
不挂业务 router，只测 handler 把异常转成 200 + {success,output,error} 外壳。
"""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from vectcut.server.http.app import app, envelope_ok, envelope_err
from vectcut.core.errors import InvalidParam, DraftNotFound


def test_envelope_ok_shape():
    assert envelope_ok({"a": 1}) == {"success": True, "output": {"a": 1}, "error": ""}


def test_envelope_err_shape():
    assert envelope_err("boom") == {"success": False, "output": "", "error": "boom"}


def _bare_client() -> TestClient:
    """独立 app（不挂业务 router）测 handler：手动加一条临时路由。"""
    sub = FastAPI()

    @sub.post("/raise_invalid")
    def _raise_invalid():
        raise InvalidParam("bad param")

    @sub.post("/raise_not_found")
    def _raise_not_found():
        raise DraftNotFound("dfd_x")

    @sub.post("/raise_value_error")
    def _raise_value_error():
        raise ValueError("plain")

    app._wire_exception_handlers(sub)
    return TestClient(sub)


def test_invalid_param_handler_returns_200_envelope():
    client = _bare_client()
    resp = client.post("/raise_invalid")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert body["output"] == ""
    assert "bad param" in body["error"]


def test_draft_not_found_handler_returns_200_envelope():
    client = _bare_client()
    resp = client.post("/raise_not_found")
    assert resp.status_code == 200
    assert resp.json()["success"] is False
    assert "dfd_x" in resp.json()["error"]


def test_unexpected_exception_handler_returns_200_envelope():
    client = _bare_client()
    resp = client.post("/raise_value_error")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert "plain" in body["error"]
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m pytest tests/server/http/test_app_envelope.py -v`
预期：FAIL，`ModuleNotFoundError: No module named 'vectcut.server'`

- [ ] **步骤 3：编写实现**

`vectcut/server/__init__.py`：

```python
"""server 子包：HTTP（FastAPI）与 MCP（手写 stdio JSON-RPC）双入口组装。"""
```

`vectcut/server/http/__init__.py`：

```python
from vectcut.server.http.app import app  # noqa: F401
```

`vectcut/server/http/app.py`：

```python
"""FastAPI app + envelope helper + 全局异常 handler。

保真约束：所有路由响应体恒为 200 + {success, output, error}（与现有 Flask
flask_router.py 外壳逐字一致，黄金测试 assert status_code==200 是硬约束）。
规格 §4.4 的语义状态码（422/404）列为本阶段非目标。
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from vectcut.core.errors import VectCutError


def envelope_ok(output) -> dict:
    return {"success": True, "output": output, "error": ""}


def envelope_err(error: str) -> dict:
    return {"success": False, "output": "", "error": error}


def _wire_exception_handlers(app: FastAPI) -> None:
    """把 VectCutError / ValidationError / 兜底异常统一转成 200 外壳。

    抽成函数以便测试在独立 sub-app 上复用同一套 handler。
    """

    @app.exception_handler(VectCutError)
    async def _vectcut_error_handler(_req: Request, exc: VectCutError):
        return JSONResponse(status_code=200, content=envelope_err(str(exc)))

    @app.exception_handler(RequestValidationError)
    async def _validation_error_handler(_req: Request, exc: RequestValidationError):
        # 保真：与 flask_router.py 的 ValidationError 分支文案前缀一致
        return JSONResponse(
            status_code=200,
            content=envelope_err(f"Hi, the required parameters are missing. {exc}"),
        )

    @app.exception_handler(Exception)
    async def _unexpected_error_handler(_req: Request, exc: Exception):
        return JSONResponse(status_code=200, content=envelope_err(str(exc)))


app = FastAPI(title="VectCutAPI")
_wire_exception_handlers(app)
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m pytest tests/server/http/test_app_envelope.py -v`
预期：PASS（5 个测试全过）

- [ ] **步骤 5：Commit**

```bash
git add vectcut/server/__init__.py vectcut/server/http/__init__.py vectcut/server/http/app.py tests/server/__init__.py tests/server/http/__init__.py tests/server/http/test_app_envelope.py
git commit -m "feat(server): 阶段4 任务1 FastAPI app 骨架 + envelope + 全局异常 handler（200 外壳保真）"
```

---

## 任务 2：draft feature FastAPI router + service 补 get_video_duration

draft feature 有 6 个路由：`/create_draft` `/save_draft` `/query_script` `/query_draft_status` `/generate_draft_url`，外加 MCP 的 `get_video_duration`（当前只在 `_save_engine`，service 未暴露——补一个公开 service + schema，供 MCP 注册）。

**文件：**
- 修改：`vectcut/features/draft/schemas.py`（追加 `GetVideoDurationRequest/Response`）
- 修改：`vectcut/features/draft/service.py`（追加 `get_video_duration`）
- 创建：`vectcut/features/draft/router.py`
- 创建：`tests/features/draft/test_fastapi_router.py`

- [ ] **步骤 1：编写失败的测试**

`tests/features/draft/test_fastapi_router.py`：

```python
"""draft feature FastAPI router 测试（独立挂载，不经全局 app）。"""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from vectcut.core import draft_store
from vectcut.features.draft.router import router


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_create_draft_route_returns_envelope():
    draft_store.DRAFT_CACHE.clear()
    resp = _client().post("/create_draft", json={})
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["output"]["draft_id"].startswith("dfd_cat_")
    assert "draft_url" in body["output"]
    assert body["error"] == ""


def test_save_draft_route_missing_draft_id_returns_error_envelope():
    resp = _client().post("/save_draft", json={})
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert "draft_id" in body["error"]


def test_query_script_route_missing_returns_error():
    resp = _client().post("/query_script", json={"draft_id": "missing"})
    assert resp.status_code == 200
    assert resp.json()["success"] is False


def test_query_draft_status_route_not_found():
    resp = _client().post("/query_draft_status", json={"task_id": "nope"})
    body = resp.json()
    assert body["success"] is True
    assert body["output"]["status"] == "not_found"


def test_generate_draft_url_route():
    resp = _client().post("/generate_draft_url", json={"draft_id": "dfd_1"})
    body = resp.json()
    assert body["success"] is True
    assert "dfd_1" in body["output"]["draft_url"]


def test_get_video_duration_service_returns_envelope_dict():
    """MCP 用的 get_video_duration service：返回 {success,output,error} 结构（迁自 _save_engine）。"""
    from vectcut.features.draft import service

    result = service.get_video_duration(video_url="https://example.com/nope.mp4")
    # ffprobe 失败时 success=False；只要结构正确即可（真实 ffprobe 由黄金/集成测试覆盖）
    assert set(result.keys()) >= {"success", "output", "error"}
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m pytest tests/features/draft/test_fastapi_router.py -v`
预期：FAIL，`ModuleNotFoundError: No module named 'vectcut.features.draft.router'`

- [ ] **步骤 3：追加 schema 与 service**

在 `vectcut/features/draft/schemas.py` 末尾追加：

```python


class GetVideoDurationRequest(BaseModel):
    video_url: str


class GetVideoDurationResponse(BaseModel):
    success: bool = True
    output: Any = 0.0
    error: Optional[str] = None
```

在 `vectcut/features/draft/service.py` 末尾追加：

```python


def get_video_duration(req: GetVideoDurationRequest) -> GetVideoDurationResponse:
    """MCP/HTTP 共用的视频时长查询。委托 _save_engine.get_video_duration（ffprobe）。

    返回 {success, output, error} 结构（与根目录 get_duration_impl.py 历史输出一致）。
    """
    result = _save_engine.get_video_duration(req.video_url)
    return GetVideoDurationResponse(
        success=result["success"],
        output=result["output"],
        error=result["error"],
    )
```

并在 `service.py` 顶部 import 区追加（与现有 `from vectcut.features.draft._save_engine import save_draft_background` 同行附近）：

```python
from vectcut.features.draft._save_engine import save_draft_background, get_video_duration as _get_video_duration_impl
```

把新函数体改为：

```python
def get_video_duration(req: GetVideoDurationRequest) -> GetVideoDurationResponse:
    result = _get_video_duration_impl(req.video_url)
    return GetVideoDurationResponse(
        success=result["success"],
        output=result["output"],
        error=result["error"],
    )
```

并在 `service.py` 的 schemas import 块追加 `GetVideoDurationRequest, GetVideoDurationResponse`。

- [ ] **步骤 4：编写 FastAPI router**

`vectcut/features/draft/router.py`：

```python
"""draft feature FastAPI router：5 路由薄接线。

保真：响应体与 flask_router.py 逐字一致（200 + {success,output,error}）。
异常由全局 handler 兜底，本文件只调 service。
"""
from __future__ import annotations

from fastapi import APIRouter

from vectcut.features.draft import service
from vectcut.features.draft.schemas import (
    CreateDraftRequest,
    GenerateDraftUrlRequest,
    QueryDraftStatusRequest,
    QueryScriptRequest,
    SaveDraftRequest,
)
from vectcut.server.http.app import envelope_ok

router = APIRouter()


@router.post("/create_draft")
def create_draft(req: CreateDraftRequest):
    resp = service.create_draft(req)
    return envelope_ok({"draft_id": resp.draft_id, "draft_url": resp.draft_url})


@router.post("/save_draft")
def save_draft(req: SaveDraftRequest):
    resp = service.save_draft(req)
    return envelope_ok({"draft_url": resp.draft_url} if resp.draft_url else {})


@router.post("/query_script")
def query_script(req: QueryScriptRequest):
    resp = service.query_script(req)
    return envelope_ok(resp.output)


@router.post("/query_draft_status")
def query_draft_status(req: QueryDraftStatusRequest):
    resp = service.query_task_status(req)
    return envelope_ok(resp.output)


@router.post("/generate_draft_url")
def generate_draft_url(req: GenerateDraftUrlRequest):
    url = service.generate_draft_url(req.draft_id)
    return envelope_ok({"draft_url": url})
```

- [ ] **步骤 5：运行测试验证通过**

运行：`python -m pytest tests/features/draft/test_fastapi_router.py -v`
预期：PASS（6 个测试全过）

- [ ] **步骤 6：Commit**

```bash
git add vectcut/features/draft/schemas.py vectcut/features/draft/service.py vectcut/features/draft/router.py tests/features/draft/test_fastapi_router.py
git commit -m "feat(draft): 阶段4 任务2 FastAPI router + service 补 get_video_duration（供 MCP 注册）"
```

---

## 任务 3：video feature FastAPI router

video 有 2 路由：`/add_video` `/add_video_keyframe`。错误文案保真见现有 `flask_router.py`。

**文件：**
- 创建：`vectcut/features/video/router.py`
- 创建：`tests/features/video/test_fastapi_router.py`

- [ ] **步骤 1：编写失败的测试**

`tests/features/video/test_fastapi_router.py`：

```python
"""video feature FastAPI router 测试。"""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from vectcut.core import draft_store
from vectcut.features.video.router import router


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_add_video_route_missing_video_url_returns_error():
    resp = _client().post("/add_video", json={})
    body = resp.json()
    assert body["success"] is False
    assert "video_url" in body["error"]


def test_add_video_route_success():
    draft_store.DRAFT_CACHE.clear()
    resp = _client().post("/add_video", json={"video_url": "https://example.com/v.mp4"})
    body = resp.json()
    assert body["success"] is True
    assert body["output"]["draft_id"].startswith("dfd_cat_")


def test_add_video_keyframe_route_missing_draft_id():
    resp = _client().post("/add_video_keyframe", json={})
    body = resp.json()
    assert body["success"] is False
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m pytest tests/features/video/test_fastapi_router.py -v`
预期：FAIL，`ModuleNotFoundError: No module named 'vectcut.features.video.router'`

- [ ] **步骤 3：编写实现**

`vectcut/features/video/router.py`：

```python
"""video feature FastAPI router：/add_video + /add_video_keyframe。

保真：响应体与 flask_router.py 逐字一致。
Pydantic 自动校验替代手写 data.get()；缺字段由全局 RequestValidationError
handler 转 200 外壳（文案前缀与 Flask 版一致）。
"""
from __future__ import annotations

from fastapi import APIRouter

from vectcut.features.video import service
from vectcut.features.video.schemas import AddVideoKeyframeRequest, AddVideoRequest
from vectcut.server.http.app import envelope_ok

router = APIRouter()


@router.post("/add_video")
def add_video(req: AddVideoRequest):
    resp = service.add_video(req)
    return envelope_ok({"draft_id": resp.draft_id, "draft_url": resp.draft_url})


@router.post("/add_video_keyframe")
def add_video_keyframe(req: AddVideoKeyframeRequest):
    resp = service.add_video_keyframe(req)
    return envelope_ok({"draft_id": resp.draft_id, "draft_url": resp.draft_url})
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m pytest tests/features/video/test_fastapi_router.py -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add vectcut/features/video/router.py tests/features/video/test_fastapi_router.py
git commit -m "feat(video): 阶段4 任务3 FastAPI router（/add_video + /add_video_keyframe）"
```

---

## 任务 4：audio feature FastAPI router

**文件：**
- 创建：`vectcut/features/audio/router.py`
- 创建：`tests/features/audio/test_fastapi_router.py`

- [ ] **步骤 1：编写失败的测试**

`tests/features/audio/test_fastapi_router.py`：

```python
"""audio feature FastAPI router 测试。"""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from vectcut.core import draft_store
from vectcut.features.audio.router import router


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_add_audio_route_missing_url_returns_error():
    resp = _client().post("/add_audio", json={})
    body = resp.json()
    assert body["success"] is False
    assert "audio_url" in body["error"]


def test_add_audio_route_success():
    draft_store.DRAFT_CACHE.clear()
    resp = _client().post("/add_audio", json={"audio_url": "https://example.com/a.mp3"})
    body = resp.json()
    assert body["success"] is True
    assert body["output"]["draft_id"].startswith("dfd_cat_")
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m pytest tests/features/audio/test_fastapi_router.py -v`
预期：FAIL，`ModuleNotFoundError`

- [ ] **步骤 3：编写实现**

`vectcut/features/audio/router.py`：

```python
"""audio feature FastAPI router：/add_audio。"""
from __future__ import annotations

from fastapi import APIRouter

from vectcut.features.audio import service
from vectcut.features.audio.schemas import AddAudioRequest
from vectcut.server.http.app import envelope_ok

router = APIRouter()


@router.post("/add_audio")
def add_audio(req: AddAudioRequest):
    resp = service.add_audio(req)
    return envelope_ok({"draft_id": resp.draft_id, "draft_url": resp.draft_url})
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m pytest tests/features/audio/test_fastapi_router.py -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add vectcut/features/audio/router.py tests/features/audio/test_fastapi_router.py
git commit -m "feat(audio): 阶段4 任务4 FastAPI router（/add_audio）"
```

---

## 任务 5：image feature FastAPI router

**文件：**
- 创建：`vectcut/features/image/router.py`
- 创建：`tests/features/image/test_fastapi_router.py`

- [ ] **步骤 1：编写失败的测试**

`tests/features/image/test_fastapi_router.py`：

```python
"""image feature FastAPI router 测试。"""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from vectcut.core import draft_store
from vectcut.features.image.router import router


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_add_image_route_missing_url_returns_error():
    resp = _client().post("/add_image", json={})
    body = resp.json()
    assert body["success"] is False
    assert "image_url" in body["error"]


def test_add_image_route_success():
    draft_store.DRAFT_CACHE.clear()
    resp = _client().post(
        "/add_image",
        json={"image_url": "https://example.com/i.png", "start": 0, "end": 1},
    )
    body = resp.json()
    assert body["success"] is True
    assert body["output"]["draft_id"].startswith("dfd_cat_")
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m pytest tests/features/image/test_fastapi_router.py -v`
预期：FAIL

- [ ] **步骤 3：编写实现**

`vectcut/features/image/router.py`：

```python
"""image feature FastAPI router：/add_image。"""
from __future__ import annotations

from fastapi import APIRouter

from vectcut.features.image import service
from vectcut.features.image.schemas import AddImageRequest
from vectcut.server.http.app import envelope_ok

router = APIRouter()


@router.post("/add_image")
def add_image(req: AddImageRequest):
    resp = service.add_image(req)
    return envelope_ok({"draft_id": resp.draft_id, "draft_url": resp.draft_url})
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m pytest tests/features/image/test_fastapi_router.py -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add vectcut/features/image/router.py tests/features/image/test_fastapi_router.py
git commit -m "feat(image): 阶段4 任务5 FastAPI router（/add_image）"
```

---

## 任务 6：effect feature FastAPI router

effect 有 2 路由：`/add_effect` `/add_sticker`。

**文件：**
- 创建：`vectcut/features/effect/router.py`
- 创建：`tests/features/effect/test_fastapi_router.py`

- [ ] **步骤 1：编写失败的测试**

`tests/features/effect/test_fastapi_router.py`：

```python
"""effect feature FastAPI router 测试。"""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from vectcut.core import draft_store
from vectcut.features.effect.router import router


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_add_effect_route_missing_type_returns_error():
    resp = _client().post("/add_effect", json={})
    body = resp.json()
    assert body["success"] is False
    assert "effect_type" in body["error"]


def test_add_sticker_route_missing_id_returns_error():
    resp = _client().post("/add_sticker", json={})
    body = resp.json()
    assert body["success"] is False
    assert "sticker_id" in body["error"]
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m pytest tests/features/effect/test_fastapi_router.py -v`
预期：FAIL

- [ ] **步骤 3：编写实现**

`vectcut/features/effect/router.py`：

```python
"""effect feature FastAPI router：/add_effect + /add_sticker。"""
from __future__ import annotations

from fastapi import APIRouter

from vectcut.features.effect import service
from vectcut.features.effect.schemas import AddEffectRequest, AddStickerRequest
from vectcut.server.http.app import envelope_ok

router = APIRouter()


@router.post("/add_effect")
def add_effect(req: AddEffectRequest):
    resp = service.add_effect(req)
    return envelope_ok({"draft_id": resp.draft_id, "draft_url": resp.draft_url})


@router.post("/add_sticker")
def add_sticker(req: AddStickerRequest):
    resp = service.add_sticker(req)
    return envelope_ok({"draft_id": resp.draft_id, "draft_url": resp.draft_url})
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m pytest tests/features/effect/test_fastapi_router.py -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add vectcut/features/effect/router.py tests/features/effect/test_fastapi_router.py
git commit -m "feat(effect): 阶段4 任务6 FastAPI router（/add_effect + /add_sticker）"
```

---

## 任务 7：text feature FastAPI router

text 有 2 路由：`/add_text` `/add_subtitle`。

**文件：**
- 创建：`vectcut/features/text/router.py`
- 创建：`tests/features/text/test_fastapi_router.py`

- [ ] **步骤 1：编写失败的测试**

`tests/features/text/test_fastapi_router.py`：

```python
"""text feature FastAPI router 测试。"""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from vectcut.core import draft_store
from vectcut.features.text.router import router


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_add_text_route_missing_text_returns_error():
    resp = _client().post("/add_text", json={"start": 0, "end": 1})
    body = resp.json()
    assert body["success"] is False


def test_add_text_route_success():
    draft_store.DRAFT_CACHE.clear()
    resp = _client().post(
        "/add_text", json={"text": "hello", "start": 0, "end": 1}
    )
    body = resp.json()
    assert body["success"] is True
    assert body["output"]["draft_id"].startswith("dfd_cat_")


def test_add_subtitle_route_missing_srt_returns_error():
    resp = _client().post("/add_subtitle", json={})
    body = resp.json()
    assert body["success"] is False
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m pytest tests/features/text/test_fastapi_router.py -v`
预期：FAIL

- [ ] **步骤 3：编写实现**

`vectcut/features/text/router.py`：

```python
"""text feature FastAPI router：/add_text + /add_subtitle。"""
from __future__ import annotations

from fastapi import APIRouter

from vectcut.features.text import service
from vectcut.features.text.schemas import AddSubtitleRequest, AddTextRequest
from vectcut.server.http.app import envelope_ok

router = APIRouter()


@router.post("/add_text")
def add_text(req: AddTextRequest):
    resp = service.add_text(req)
    return envelope_ok({"draft_id": resp.draft_id, "draft_url": resp.draft_url})


@router.post("/add_subtitle")
def add_subtitle(req: AddSubtitleRequest):
    resp = service.add_subtitle(req)
    return envelope_ok({"draft_id": resp.draft_id, "draft_url": resp.draft_url})
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m pytest tests/features/text/test_fastapi_router.py -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add vectcut/features/text/router.py tests/features/text/test_fastapi_router.py
git commit -m "feat(text): 阶段4 任务7 FastAPI router（/add_text + /add_subtitle）"
```

---

## 任务 8：metadata feature FastAPI router（参数化 + 11 别名）

保真要点：与 `flask_router.py` 相同——`GET /metadata/{kind}` + 11 个旧具名别名全部转发同一 service。

**文件：**
- 创建：`vectcut/features/metadata/router.py`
- 创建：`tests/features/metadata/test_fastapi_router.py`

- [ ] **步骤 1：编写失败的测试**

`tests/features/metadata/test_fastapi_router.py`：

```python
"""metadata feature FastAPI router 测试：参数化 + 11 别名等价。"""
from fastapi import FastAPI
from fastapi.testclient import TestClient

from vectcut.features.metadata.router import router


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_metadata_by_kind_returns_envelope():
    resp = _client().get("/metadata/font")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert isinstance(body["output"], list)
    assert len(body["output"]) > 0


def test_metadata_unknown_kind_returns_error():
    resp = _client().get("/metadata/no_such_kind")
    body = resp.json()
    assert body["success"] is False
    assert "no_such_kind" in body["error"]


ALIASES = [
    "/get_intro_animation_types", "/get_outro_animation_types",
    "/get_combo_animation_types", "/get_transition_types",
    "/get_mask_types", "/get_audio_effect_types", "/get_font_types",
    "/get_text_intro_types", "/get_text_outro_types",
    "/get_text_loop_anim_types", "/get_video_scene_effect_types",
    "/get_video_character_effect_types",
]


def test_each_alias_equivalent_to_param_route():
    client = _client()
    alias_to_kind = {
        "/get_intro_animation_types": "intro_animation",
        "/get_font_types": "font",
    }
    for alias, kind in alias_to_kind.items():
        a = client.get(alias).json()
        b = client.get(f"/metadata/{kind}").json()
        assert a == b, f"{alias} != /metadata/{kind}"
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m pytest tests/features/metadata/test_fastapi_router.py -v`
预期：FAIL

- [ ] **步骤 3：编写实现**

`vectcut/features/metadata/router.py`：

```python
"""metadata feature FastAPI router：GET /metadata/{kind} + 11 旧别名。

保真：与 flask_router.py 路由集合、输出外壳逐字一致。
"""
from __future__ import annotations

from fastapi import APIRouter

from vectcut.features.metadata import service
from vectcut.server.http.app import envelope_ok, envelope_err

router = APIRouter()

_KIND_TO_ALIAS = {
    "intro_animation": "/get_intro_animation_types",
    "outro_animation": "/get_outro_animation_types",
    "combo_animation": "/get_combo_animation_types",
    "transition": "/get_transition_types",
    "mask": "/get_mask_types",
    "audio_effect": "/get_audio_effect_types",
    "font": "/get_font_types",
    "text_intro": "/get_text_intro_types",
    "text_outro": "/get_text_outro_types",
    "text_loop_anim": "/get_text_loop_anim_types",
    "video_scene_effect": "/get_video_scene_effect_types",
    "video_character_effect": "/get_video_character_effect_types",
}


@router.get("/metadata/{kind}")
def metadata_by_kind(kind: str):
    try:
        return envelope_ok(service.list_metadata(kind))
    except Exception as e:
        return envelope_err(str(e))


def _register_alias(kind: str, alias: str) -> None:
    @router.get(alias, name=f"alias_{kind}")
    def _alias():
        try:
            return envelope_ok(service.list_metadata(kind))
        except Exception as e:
            return envelope_err(str(e))


for _kind, _alias in _KIND_TO_ALIAS.items():
    _register_alias(_kind, _alias)
```

> **注**：metadata service `list_metadata` 抛 `InvalidParam`（`VectCutError` 子类），按理会被全局 handler 接住。但 GET 路由的异常经 `app.include_router` 后由全局 handler 兜底——测试用独立 sub-app（含全局 handler? 否，`_client()` 只 include_router 未 wire handler）。
> **修正**：metadata router 测试的 `_client()` 需 wire 全局 handler，否则 `InvalidParam` 会冒泡成 500。改 `tests/features/metadata/test_fastapi_router.py` 的 `_client()`：

```python
def _client() -> TestClient:
    from vectcut.server.http.app import app as _shared  # noqa: F401
    app = FastAPI()
    # 复用全局 handler（wire 同一套）
    from vectcut.server.http.app import _wire_exception_handlers
    _wire_exception_handlers(app)
    app.include_router(router)
    return TestClient(app)
```

> 同样地，所有 feature router 测试中若 service 抛 `VectCutError`（如 `query_script` 草稿不存在 → `DraftNotFound`），独立 sub-app 需 wire handler 才能转 200 外壳。统一规则：**所有 feature router 测试的 `_client()` 都调用 `_wire_exception_handlers(app)`**。回填任务 2-7 的 `_client()`：在 `app.include_router(router)` 前加 `from vectcut.server.http.app import _wire_exception_handlers; _wire_exception_handlers(app)`。

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m pytest tests/features/metadata/test_fastapi_router.py -v`
预期：PASS

> **回填后**：重跑任务 2-7 的 fastapi router 测试确认仍绿（因它们 service 也会抛 `VectCutError`，未 wire 时会变 500）。
> 运行：`python -m pytest tests/features/draft tests/features/video tests/features/audio tests/features/image tests/features/effect tests/features/text tests/features/metadata -k fastapi_router -v`
> 预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add vectcut/features/metadata/router.py tests/features/metadata/test_fastapi_router.py tests/features/draft/test_fastapi_router.py tests/features/video/test_fastapi_router.py tests/features/audio/test_fastapi_router.py tests/features/image/test_fastapi_router.py tests/features/effect/test_fastapi_router.py tests/features/text/test_fastapi_router.py
git commit -m "feat(metadata): 阶段4 任务8 FastAPI router（参数化 + 11 别名）+ 回填各 feature router 测试 wire handler"
```

---

## 任务 9：挂载全部 router + run_http.py + 黄金测试切换

这是本阶段"一鼓作气"环节：把 7 个 router 挂到全局 `app`，新增 `run_http.py`，把两份黄金测试的 `client` fixture 从 `capcut_server.app`（Flask）切到 `vectcut.server.http.app`（FastAPI）。切换后若黄金快照比对失败，说明 FastAPI 输出与 Flask 不一致——必须修到一致（不许 `REGENERATE_GOLDEN` 抹平，那是回归遮羞布）。

**文件：**
- 修改：`vectcut/server/http/app.py`（挂载 7 router）
- 创建：`run_http.py`
- 修改：`tests/golden/test_business_routes_golden.py`（fixture 切换）
- 修改：`tests/golden/test_metadata_routes_golden.py`（fixture 切换）

- [ ] **步骤 1：先编写切换后黄金测试的预期（红灯先行）**

修改 `tests/golden/test_business_routes_golden.py` 的 `client` fixture：

```python
@pytest.fixture(scope="module")
def client():
    from vectcut.server.http.app import app
    return TestClient(app)
```

并在文件顶部 import 加 `from fastapi.testclient import TestClient`，删去 `import capcut_server`。

同样修改 `tests/golden/test_metadata_routes_golden.py`：

```python
@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from vectcut.server.http.app import app
    return TestClient(app)
```

> metadata 测试用 `client.get(route)`，Flask 与 TestClient 接口一致，无需改用例本体。但 `resp.get_json()` → `resp.json()`（starlette 无 `get_json`），且断言 `resp.status_code == 200` 不变。逐一把 `resp.get_json()` 改为 `resp.json()`。

- [ ] **步骤 2：运行黄金测试验证失败**

运行：`python -m pytest tests/golden/ -v`
预期：FAIL（app 未挂 router，路由 404；且 metadata 测试 `get_json` 报错）

- [ ] **步骤 3：挂载 router 到 app**

在 `vectcut/server/http/app.py` 末尾（`app = FastAPI(...)` 与 `_wire_exception_handlers(app)` 之后）追加：

```python
from vectcut.features.draft.router import router as draft_router
from vectcut.features.video.router import router as video_router
from vectcut.features.audio.router import router as audio_router
from vectcut.features.text.router import router as text_router
from vectcut.features.image.router import router as image_router
from vectcut.features.effect.router import router as effect_router
from vectcut.features.metadata.router import router as metadata_router

app.include_router(draft_router)
app.include_router(video_router)
app.include_router(audio_router)
app.include_router(text_router)
app.include_router(image_router)
app.include_router(effect_router)
app.include_router(metadata_router)
```

- [ ] **步骤 4：编写 run_http.py**

`run_http.py`：

```python
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
```

- [ ] **步骤 5：运行黄金测试验证通过（关键验收点）**

运行：`python -m pytest tests/golden/ -v`
预期：PASS（24 个 metadata 用例 + 12 个 business 用例全过，快照与 Flask 时代逐字一致）

> **若失败**：比对失败用例的 `normalized` 与快照 JSON，差异通常是：(a) error 文案尾随空格/前缀；(b) Pydantic 校验错误消息体与 Flask 手写 `data.get` 不同。修 FastAPI router 或 handler 文案至一致，**不要 REGENERATE_GOLDEN**。

- [ ] **步骤 6：运行全量测试确认无回归**

运行：`python -m pytest -q`
预期：PASS（含阶段 0-3 所有 service/golden 测试 + 阶段 4 新增 fastapi router 测试）
> 旧的 `tests/features/*/test_router.py`（Flask 版）仍应绿，因为 `flask_router.py` 与 `capcut_server.py` 仍在。

- [ ] **步骤 7：Commit**

```bash
git add vectcut/server/http/app.py run_http.py tests/golden/test_business_routes_golden.py tests/golden/test_metadata_routes_golden.py
git commit -m "feat(server): 阶段4 任务9 挂载7 FastAPI router + run_http.py + 黄金测试切换 FastAPI app（24+12 黄金全绿）"
```

---

## 任务 10：MCP schema_gen + registry + runtime + run_mcp.py

把 `mcp_server.py`（~480 行手写 inputSchema + if/elif 大分派）改造为 `vectcut/server/mcp/`：注册表 + 自动 schema + 共用 `run_service`。保留手写 stdio JSON-RPC 主循环（不引 SDK）。

**文件：**
- 创建：`vectcut/server/mcp/__init__.py`
- 创建：`vectcut/server/mcp/schema_gen.py`
- 创建：`vectcut/server/mcp/registry.py`
- 创建：`vectcut/server/mcp/runtime.py`
- 创建：`run_mcp.py`
- 创建：`tests/server/mcp/__init__.py`
- 创建：`tests/server/mcp/test_schema_gen.py`
- 创建：`tests/server/mcp/test_registry.py`
- 创建：`tests/server/mcp/test_runtime.py`

### 任务 10a：schema_gen

- [ ] **步骤 1：编写失败的测试**

`tests/server/mcp/test_schema_gen.py`：

```python
"""inputSchema 生成测试：从 Pydantic 模型生成 MCP inputSchema。"""
from pydantic import BaseModel
from typing import Optional, List

from vectcut.server.mcp.schema_gen import pydantic_to_input_schema


class _DemoModel(BaseModel):
    video_url: str
    start: float = 0
    end: Optional[float] = None
    tags: Optional[List[str]] = None


def test_schema_is_object_with_properties():
    schema = pydantic_to_input_schema(_DemoModel)
    assert schema["type"] == "object"
    assert "properties" in schema
    assert "video_url" in schema["properties"]


def test_required_collected():
    schema = pydantic_to_input_schema(_DemoModel)
    assert "video_url" in schema["required"]
    assert "start" not in schema["required"]  # 有默认值


def test_property_types_mapped():
    schema = pydantic_to_input_schema(_DemoModel)
    assert schema["properties"]["video_url"]["type"] == "string"
    assert schema["properties"]["start"]["type"] == "number"


def test_optional_field_still_present():
    schema = pydantic_to_input_schema(_DemoModel)
    assert "end" in schema["properties"]
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m pytest tests/server/mcp/test_schema_gen.py -v`
预期：FAIL，`ModuleNotFoundError`

- [ ] **步骤 3：编写实现**

`vectcut/server/mcp/__init__.py`：

```python
"""MCP server：手写 stdio JSON-RPC（不依赖第三方 SDK）+ tool 注册表化。"""
```

`vectcut/server/mcp/schema_gen.py`：

```python
"""从 Pydantic 模型生成 MCP inputSchema（单一事实源，规格 §4.3）。

替代 mcp_server.py 里 11 个手写 inputSchema。字段名/类型/required 全部
由模型定义推导，service 改字段 schema 自动同步。
"""
from __future__ import annotations

from typing import Type

from pydantic import BaseModel

# JSON Schema type 名 → MCP inputSchema 期望的简化形式
_PY_TO_JSON = {
    "str": "string",
    "int": "integer",
    "float": "number",
    "bool": "boolean",
}


def _field_type(field) -> str:
    """把 Pydantic 字段的外层类型映射到 inputSchema type 字符串。"""
    py_type = field.annotation
    # Optional[X] / List[X] 等：取 __origin__ 判断
    origin = getattr(py_type, "__origin__", None)
    if origin is list:
        return "array"
    # 取裸类型名（str/int/float/bool）；Optional 包裹的话取 arg
    if hasattr(py_type, "__args__"):
        non_none = [a for a in py_type.__args__ if a is not type(None)]
        if non_none:
            py_type = non_none[0]
            origin = getattr(py_type, "__origin__", None)
            if origin is list:
                return "array"
    name = getattr(py_type, "__name__", "")
    return _PY_TO_JSON.get(name, "string")


def pydantic_to_input_schema(model: Type[BaseModel]) -> dict:
    """生成 {type:object, properties:{...}, required:[...]}。"""
    props = {}
    required = []
    for name, field in model.model_fields.items():
        props[name] = {"type": _field_type(field)}
        if field.is_required():
            required.append(name)
    schema = {"type": "object", "properties": props}
    if required:
        schema["required"] = required
    return schema
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m pytest tests/server/mcp/test_schema_gen.py -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add vectcut/server/mcp/__init__.py vectcut/server/mcp/schema_gen.py tests/server/mcp/__init__.py tests/server/mcp/test_schema_gen.py
git commit -m "feat(mcp): 阶段4 任务10a schema_gen 从 Pydantic 模型生成 inputSchema"
```

### 任务 10b：registry

- [ ] **步骤 1：编写失败的测试**

`tests/server/mcp/test_registry.py`：

```python
"""MCP tool 注册表测试：11 个 tool 全部注册、name 唯一、schema 可生成。"""
from vectcut.server.mcp.registry import TOOLS, ToolSpec
from vectcut.server.mcp.schema_gen import pydantic_to_input_schema


EXPECTED_NAMES = {
    "create_draft", "add_video", "add_audio", "add_image", "add_text",
    "add_subtitle", "add_effect", "add_sticker", "add_video_keyframe",
    "get_video_duration", "save_draft",
}


def test_all_11_tools_registered():
    assert set(TOOLS.keys()) == EXPECTED_NAMES


def test_each_tool_has_service_model_description():
    for name, spec in TOOLS.items():
        assert callable(spec.service), name
        assert spec.request_model is not None, name
        assert isinstance(spec.description, str) and spec.description, name


def test_each_tool_schema_generates():
    for name, spec in TOOLS.items():
        schema = pydantic_to_input_schema(spec.request_model)
        assert schema["type"] == "object", name
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m pytest tests/server/mcp/test_registry.py -v`
预期：FAIL，`ModuleNotFoundError`

- [ ] **步骤 3：编写实现**

`vectcut/server/mcp/registry.py`：

```python
"""MCP tool 注册表：name -> ToolSpec(service, request_model, description)。

单一事实源：inputSchema 从 request_model 生成，handler 调 service。
新增 tool 只加一行。替代 mcp_server.py 的 if/elif 大分派（规格 §4.3）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Type

from pydantic import BaseModel

from vectcut.features.audio.schemas import AddAudioRequest
from vectcut.features.audio.service import add_audio
from vectcut.features.draft.schemas import (
    CreateDraftRequest,
    GenerateDraftUrlRequest,
    GetVideoDurationRequest,
    SaveDraftRequest,
)
from vectcut.features.draft.service import (
    create_draft,
    generate_draft_url,
    get_video_duration,
    save_draft,
)
from vectcut.features.effect.schemas import AddEffectRequest, AddStickerRequest
from vectcut.features.effect.service import add_effect, add_sticker
from vectcut.features.image.schemas import AddImageRequest
from vectcut.features.image.service import add_image
from vectcut.features.text.schemas import AddSubtitleRequest, AddTextRequest
from vectcut.features.text.service import add_subtitle, add_text
from vectcut.features.video.schemas import AddVideoKeyframeRequest, AddVideoRequest
from vectcut.features.video.service import add_video, add_video_keyframe


@dataclass
class ToolSpec:
    service: Callable
    request_model: Type[BaseModel]
    description: str


# 注：generate_draft_url service 接受 str 而非 model，单独包一层
def _generate_draft_url_service(req: GenerateDraftUrlRequest):
    url = generate_draft_url(req.draft_id)
    # 复用 GenerateDraftUrlResponse 外壳
    from vectcut.features.draft.schemas import GenerateDraftUrlResponse
    return GenerateDraftUrlResponse(success=True, draft_url=url, error="")


TOOLS: Dict[str, ToolSpec] = {
    "create_draft": ToolSpec(create_draft, CreateDraftRequest, "创建新的 VectCut 草稿"),
    "add_video": ToolSpec(add_video, AddVideoRequest, "添加视频到草稿，支持转场、蒙版、背景模糊等效果"),
    "add_audio": ToolSpec(add_audio, AddAudioRequest, "添加音频到草稿，支持音效处理"),
    "add_image": ToolSpec(add_image, AddImageRequest, "添加图片到草稿，支持动画、转场、蒙版等效果"),
    "add_text": ToolSpec(add_text, AddTextRequest, "添加文本到草稿，支持文本多样式、文字阴影和文字背景"),
    "add_subtitle": ToolSpec(add_subtitle, AddSubtitleRequest, "添加字幕到草稿，支持SRT文件和样式设置"),
    "add_effect": ToolSpec(add_effect, AddEffectRequest, "添加特效到草稿"),
    "add_sticker": ToolSpec(add_sticker, AddStickerRequest, "添加贴纸到草稿"),
    "add_video_keyframe": ToolSpec(add_video_keyframe, AddVideoKeyframeRequest, "添加视频关键帧，支持位置、缩放、旋转、透明度等属性动画"),
    "get_video_duration": ToolSpec(get_video_duration, GetVideoDurationRequest, "获取视频时长"),
    "save_draft": ToolSpec(save_draft, SaveDraftRequest, "保存草稿"),
    "generate_draft_url": ToolSpec(
        _generate_draft_url_service, GenerateDraftUrlRequest, "生成草稿下载链接"
    ),
}
```

> **注**：现有 `mcp_server.py` 的 11 个 tool 不含 `generate_draft_url`（它只暴露 11 个：create_draft/add_video/add_audio/add_image/add_text/add_subtitle/add_effect/add_sticker/add_video_keyframe/get_video_duration/save_draft）。但 HTTP 侧有 `/generate_draft_url` 路由。为对称、且规格 §4.5"加一个功能 HTTP/MCP 同时获得"，注册表**新增** `generate_draft_url` tool（第 12 个）。测试 `EXPECTED_NAMES` 需相应包含它——更新测试：

```python
EXPECTED_NAMES = {
    "create_draft", "add_video", "add_audio", "add_image", "add_text",
    "add_subtitle", "add_effect", "add_sticker", "add_video_keyframe",
    "get_video_duration", "save_draft", "generate_draft_url",
}
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m pytest tests/server/mcp/test_registry.py -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add vectcut/server/mcp/registry.py tests/server/mcp/test_registry.py
git commit -m "feat(mcp): 阶段4 任务10b tool 注册表（12 tool，inputSchema 从模型生成）"
```

### 任务 10c：runtime + run_mcp.py

- [ ] **步骤 1：编写失败的测试**

`tests/server/mcp/test_runtime.py`：

```python
"""MCP runtime 测试：run_service + tools/list + tools/call + 错误码。"""
import json

from vectcut.core import draft_store
from vectcut.server.mcp.runtime import handle_request, run_service


def test_run_service_returns_model_dump():
    draft_store.DRAFT_CACHE.clear()
    from vectcut.features.draft.service import create_draft
    from vectcut.features.draft.schemas import CreateDraftRequest

    result = run_service(create_draft, CreateDraftRequest, {})
    assert "draft_id" in result
    assert result["draft_id"].startswith("dfd_cat_")


def test_run_service_validation_error_returns_error_envelope():
    from vectcut.features.video.service import add_video
    from vectcut.features.video.schemas import AddVideoRequest

    result = run_service(add_video, AddVideoRequest, {})
    # 缺 video_url → 校验失败，返回 {success:False, error:...}
    assert result["success"] is False
    assert "video_url" in result["error"]


def test_initialize_response():
    resp = json.loads(handle_request(json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "initialize"
    })))
    assert resp["result"]["protocolVersion"] == "2024-11-05"
    assert resp["result"]["serverInfo"]["name"] == "vectcut"


def test_tools_list_returns_all_tools_with_input_schema():
    resp = json.loads(handle_request(json.dumps({
        "jsonrpc": "2.0", "id": 2, "method": "tools/list"
    })))
    tools = resp["result"]["tools"]
    names = {t["name"] for t in tools}
    assert "add_video" in names
    # inputSchema 从模型生成
    add_video_tool = next(t for t in tools if t["name"] == "add_video")
    assert add_video_tool["inputSchema"]["type"] == "object"
    assert "video_url" in add_video_tool["inputSchema"]["properties"]


def test_tools_call_create_draft():
    draft_store.DRAFT_CACHE.clear()
    resp = json.loads(handle_request(json.dumps({
        "jsonrpc": "2.0", "id": 3, "method": "tools/call",
        "params": {"name": "create_draft", "arguments": {}}
    })))
    text = resp["result"]["content"][0]["text"]
    payload = json.loads(text)
    assert payload["draft_id"].startswith("dfd_cat_")


def test_unknown_method_returns_method_not_found():
    resp = json.loads(handle_request(json.dumps({
        "jsonrpc": "2.0", "id": 4, "method": "nope"
    })))
    assert resp["error"]["code"] == -32601


def test_unknown_tool_returns_error():
    resp = json.loads(handle_request(json.dumps({
        "jsonrpc": "2.0", "id": 5, "method": "tools/call",
        "params": {"name": "ghost", "arguments": {}}
    })))
    # 未知 tool 走 run_service 之前的 lookup 失败 → -32601 或内容里 success=False
    content = resp["result"]["content"][0]["text"]
    payload = json.loads(content)
    assert payload["success"] is False
```

- [ ] **步骤 2：运行测试验证失败**

运行：`python -m pytest tests/server/mcp/test_runtime.py -v`
预期：FAIL，`ModuleNotFoundError`

- [ ] **步骤 3：编写实现**

`vectcut/server/mcp/runtime.py`：

```python
"""MCP runtime：run_service + handle_request + stdio 主循环。

保真：保留 mcp_server.py 的 JSON-RPC 响应结构（protocolVersion 2024-11-05、
serverInfo、tools/list、tools/call content 包装、Method not found -32601）。
差异：tool 分派从 if/elif 改为查 TOOLS 表；inputSchema 从模型生成；
异常转 -32xxx 错误码（规格 §4.4）。
"""
from __future__ import annotations

import contextlib
import io
import json
import sys
import traceback
from typing import Any, Dict, Optional, Type

from pydantic import BaseModel, ValidationError

from vectcut.core.errors import VectCutError
from vectcut.server.mcp.registry import TOOLS
from vectcut.server.mcp.schema_gen import pydantic_to_input_schema

# 错误码：规格 §4.4。VectCutError 子类用其 code 字段映射到 -32000 段。
_BASE_ERR_CODE = -32000


def _error_code(exc: Exception) -> int:
    if isinstance(exc, VectCutError):
        mapping = {
            "DRAFT_NOT_FOUND": -32001,
            "INVALID_PARAM": -32002,
            "ENGINE_ERROR": -32003,
            "MEDIA_DOWNLOAD_ERROR": -32004,
        }
        return mapping.get(exc.code, _BASE_ERR_CODE)
    return _BASE_ERR_CODE


def run_service(service_fn, model_cls: Type[BaseModel], arguments: Dict[str, Any]) -> Dict[str, Any]:
    """共用工具：validate → service → model_dump。异常转 {success:False, error}。

    规格 §4.3：所有 tool handler 都调它，消除手写大分派。
    """
    try:
        req = model_cls.model_validate(arguments or {})
    except ValidationError as e:
        return {"success": False, "error": f"Hi, the required parameters are missing. {e}"}
    try:
        with _capture_stdout():
            resp = service_fn(req)
        if isinstance(resp, BaseModel):
            return resp.model_dump()
        return resp
    except VectCutError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        print(f"[ERROR] service error: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return {"success": False, "error": str(e)}


@contextlib.contextmanager
def _capture_stdout():
    """捕获标准输出，防止引擎调试信息干扰 JSON 响应（迁自 mcp_server.py）。"""
    old = sys.stdout
    sys.stdout = io.StringIO()
    try:
        yield
    finally:
        sys.stdout = old


def _tools_list() -> list:
    return [
        {
            "name": name,
            "description": spec.description,
            "inputSchema": pydantic_to_input_schema(spec.request_model),
        }
        for name, spec in TOOLS.items()
    ]


def handle_request(request_data: str) -> Optional[str]:
    """处理一条 JSON-RPC 请求，返回 JSON 字符串或 None（通知）。"""
    try:
        request = json.loads(request_data.strip())
    except Exception as e:
        return json.dumps({
            "jsonrpc": "2.0", "id": None,
            "error": {"code": -32700, "message": f"Parse error: {e}"},
        })

    method = request.get("method")
    req_id = request.get("id")

    if method == "initialize":
        return json.dumps({
            "jsonrpc": "2.0", "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"experimental": {}, "tools": {"listChanged": False}},
                "serverInfo": {"name": "vectcut", "version": "1.0.0"},
            },
        })

    if method == "notifications/initialized":
        return None

    if method == "tools/list":
        return json.dumps({
            "jsonrpc": "2.0", "id": req_id,
            "result": {"tools": _tools_list()},
        })

    if method == "tools/call":
        params = request.get("params", {})
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        spec = TOOLS.get(tool_name)
        if spec is None:
            result = {"success": False, "error": f"Unknown tool: {tool_name}"}
        else:
            result = run_service(spec.service, spec.request_model, arguments)
        return json.dumps({
            "jsonrpc": "2.0", "id": req_id,
            "result": {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}]},
        })

    return json.dumps({
        "jsonrpc": "2.0", "id": req_id,
        "error": {"code": -32601, "message": "Method not found"},
    })


def main():
    """stdio 主循环（迁自 mcp_server.py，仅替换分派为 handle_request）。"""
    print("🚀 Starting VectCut MCP Server...", file=sys.stderr)
    print(f"📋 Available tools: {len(TOOLS)} tools loaded", file=sys.stderr)
    try:
        while True:
            line = sys.stdin.readline()
            if not line:
                break
            response = handle_request(line)
            if response:
                print(response)
                sys.stdout.flush()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
```

`run_mcp.py`：

```python
#!/usr/bin/env python3
"""VectCutAPI MCP 入口（替代 mcp_server.py）。"""
from vectcut.server.mcp.runtime import main

if __name__ == "__main__":
    main()
```

- [ ] **步骤 4：运行测试验证通过**

运行：`python -m pytest tests/server/mcp/test_runtime.py -v`
预期：PASS

- [ ] **步骤 5：Commit**

```bash
git add vectcut/server/mcp/runtime.py run_mcp.py tests/server/mcp/test_runtime.py
git commit -m "feat(mcp): 阶段4 任务10c runtime（run_service+注册表分派+stdio 主循环）+ run_mcp.py"
```

---

## 任务 11：删旧入口 + 全量验收

切换完成且新入口全部就位后，删 `capcut_server.py` / `mcp_server.py`，跑全量 + flake8。

**文件：**
- 删除：`capcut_server.py`
- 删除：`mcp_server.py`
- 修改：`tests/test_legacy_routes_removed.py`（若引用旧入口）
- 修改：`tests/features/*/test_router.py`（Flask 版）——见步骤说明

- [ ] **步骤 1：先确认旧入口无人引用**

运行：`grep -rn "capcut_server\|mcp_server" --include="*.py" tests/ vectcut/ run_*.py`
预期：仅 `tests/golden/*`（已切走，应无）、`tests/test_legacy_routes_removed.py`、`tests/features/*/test_router.py`（Flask 版 fixture import `flask_router`，不直接 import capcut_server，应无）。
> 若 `tests/test_legacy_routes_removed.py` 仍 import capcut_server，需先把它的 fixture 切到 `vectcut.server.http.app`（同任务 9 模式）。

- [ ] **步骤 2：删除旧入口**

```bash
git rm capcut_server.py mcp_server.py
```

- [ ] **步骤 3：处理 Flask 版 feature router 测试**

`tests/features/{draft,video,audio,text,image,effect,metadata}/test_router.py`（7 个 Flask 版）此时仍 import `flask_router`。`flask_router.py` 本阶段**保留**（阶段 5 才删），故这些测试仍可跑。但它们与 FastAPI 版重复测同一路由——保留双测至阶段 5 一并清理。
> **决策**：本阶段不删 Flask 测试与 `flask_router.py`，避免阶段 4 范围膨胀。阶段 5 删 `flask_router.py` 时连同 Flask 测试一起删。

- [ ] **步骤 4：运行全量测试**

运行：`python -m pytest -q`
预期：PASS（所有 service / golden / fastapi router / mcp runtime 测试绿；Flask router 测试也仍绿）

- [ ] **步骤 5：flake8 洁净检查**

运行：`python -m flake8 vectcut/ run_http.py run_mcp.py tests/server/ tests/features/*/test_fastapi_router.py --max-line-length=120`
预期：无输出（洁净）

- [ ] **步骤 6：手动冒烟（可选但推荐）**

```bash
python run_http.py  # 应监听 9001，curl http://localhost:9001/metadata/font 返回 200 外壳
```

- [ ] **步骤 7：Commit**

```bash
git add -A
git commit -m "refactor(server): 阶段4 任务11 删旧入口 capcut_server/mcp_server，FastAPI+MCP 注册表化收官"
```

---

## 自检

**1. 规格覆盖度（§4 双入口统一 + §3.1 包结构 + §8 阶段4）：**
- §4.1 service 层契约（纯 Python、强类型入参出参、draft 在 service 内取）：阶段 0-3 已建，本阶段不动 service 主体，仅 draft 补 `get_video_duration` —— 任务 2 覆盖。
- §4.2 HTTP 薄入口（FastAPI 自动校验，`data.get` 消失）：任务 2-8 的 `router.py` 用声明式 `req: Model` 参数，Pydantic 自动校验 —— 覆盖。
- §4.3 MCP 薄入口（inputSchema 从模型生成 + `run_service` 共用 + 注册表化）：任务 10a/10b/10c —— 覆盖。
- §4.4 统一错误处理（一套异常两处映射）：任务 1 全局 handler + 任务 10c `_error_code` 映射 —— 覆盖（注：本阶段 HTTP 侧保真 200 外壳，语义状态码列为非目标，已在计划头部声明）。
- §3.1 `server/http` + `server/mcp` + `run_http.py`/`run_mcp.py`：任务 1/9/10 —— 覆盖。
- §8 阶段4"两入口落 FastAPI"：全部任务 —— 覆盖。

**2. 占位符扫描：** 无 TODO/待定；每个代码步骤都给了完整代码块；命令与预期输出齐全。任务 8 内有一处"修正/回填"说明（wire handler），已写成可执行步骤而非占位。

**3. 类型一致性：**
- `envelope_ok`/`envelope_err` 在任务 1 定义，任务 2-9 全部复用，签名一致。
- `ToolSpec(service, request_model, description)` 在任务 10b 定义，任务 10c `TOOLS.get(name)` 返回同结构 —— 一致。
- `run_service(service_fn, model_cls, arguments)` 签名在任务 10c 测试与实现一致。
- `get_video_duration` service（任务 2）返回 `GetVideoDurationResponse`，registry（任务 10b）注册同一函数 + `GetVideoDurationRequest` —— 一致。
- 各 feature 的 `router` 变量名统一（任务 9 import 用 `router as xxx_router`）。
- `GenerateDraftUrlRequest` 在 draft schemas（阶段 2 已存在）与 registry（任务 10b）引用一致；`_generate_draft_url_service` 包裹层返回 `GenerateDraftUrlResponse`（阶段 2 已存在）—— 一致。

**发现并已修复的问题：**
- 任务 8 自检发现：独立 sub-app 测试未 wire 全局 handler 时，service 抛 `VectCutError` 会变 500。已在任务 8 步骤 3 末尾以"修正/回填"形式写成可执行步骤（回填任务 2-7 的 `_client()`）。
- 任务 10b 自检发现：`generate_draft_url` service 签名是 `(draft_id: str)` 而非接 model，与注册表的 `run_service(service, Model, args)` 契约不符。已加 `_generate_draft_url_service` 适配层，并在注册表新增第 12 个 tool，相应更新测试 `EXPECTED_NAMES`。

计划无遗留缺陷。

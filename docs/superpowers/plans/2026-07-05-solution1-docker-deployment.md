# 实施计划：方案一 Docker 部署

- 日期：2026-07-05
- 规格：`docs/superpowers/specs/2026-07-04-solution1-docker-deployment.md`
- 目标：将 VectCutAPI 容器化，提供云端 API 基座支撑方案二桌面客户端
- 原则：DRY / YAGNI / TDD；每步带可运行代码与验证命令；零上下文工程师可执行

## 元信息

**架构概览：**

外部访问 → Nginx (SSL + 限流) → FastAPI (VectCutAPI 容器, :9001) → Docker Volume（持久化）

**技术栈：**
- Docker + Docker Compose（编排）
- Nginx Alpine（反向代理 + SSL）
- Python 3.10-slim（FastAPI 容器）
- 健康检查 + 日志脱敏 + 错误码标准化

**前置依赖：**
- 方案二后端 template_filling feature 已实现（任务 #2）
- 服务器已安装 Docker + Docker Compose
- 域名 + SSL 证书（生产环境）

**文件结构（本计划新增/修改）：**
- docker/Dockerfile.api（新增）
- docker/nginx.conf（新增）
- docker-compose.yml（新增）
- docker-compose.override.yml（新增，开发环境覆盖）
- .env.example（新增）
- config.json.example（新增）
- vectcut/core/errors.py（修改：错误码标准化）
- vectcut/core/logger.py（新增：脱敏日志）
- vectcut/core/config.py（修改：环境变量注入）
- vectcut/server/http/app.py（修改：健康检查端点）
- scripts/backup.sh（新增：数据备份）
- scripts/deploy.sh（新增：部署脚本）
- tests/core/test_logger.py（新增）
- tests/core/test_config_env.py（新增）
- tests/core/test_error_codes.py（新增）
- tests/server/http/test_health.py（新增）

---

## 任务 1：健康检查端点

**文件：**
- 修改：vectcut/server/http/app.py

- [ ] **步骤 1.1：添加 GET /api/health 端点**

在 vectcut/server/http/app.py 中追加（路由挂载之后、异常处理之前）：

```python
from datetime import datetime

@app.get("/api/health")
async def health_check():
    """健康检查端点（供 Docker HEALTHCHECK 与 Nginx 探活）。

    返回 200 + {status, timestamp, version}。
    不走统一信封，方便 Docker/Nginx 直接判断状态码。
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
    }
```

- [ ] **步骤 1.2：验证端点可用**

```bash
python run_http.py
# 另开终端
curl http://localhost:9001/api/health
# 预期：{"status":"healthy","timestamp":"...","version":"1.0.0"}
```

- [ ] **步骤 1.3：添加健康检查路由测试**

```python
# tests/server/http/test_health.py
"""健康检查端点测试。"""
from fastapi.testclient import TestClient
from vectcut.server.http.app import create_app


def test_health_endpoint():
    """GET /api/health 返回 200 + healthy 状态"""
    client = TestClient(create_app())
    resp = client.get("/api/health")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "version" in data
```

- [ ] **步骤 1.4：运行测试 + Commit**

```bash
pytest tests/server/http/test_health.py -v
git add vectcut/server/http/app.py tests/server/http/test_health.py
git commit -m "feat(server): add /api/health endpoint for Docker healthcheck"
```

---

## 任务 2：错误码标准化

**文件：**
- 修改：vectcut/core/errors.py
- 修改：vectcut/server/http/app.py（统一错误响应格式）

- [ ] **步骤 2.1：在 errors.py 增加错误码常量表与工厂函数**

在 vectcut/core/errors.py 末尾追加（不破坏现有 VectCutError/InvalidParam 等类的接口）：

```python
# vectcut/core/errors.py 追加

# 预定义错误码（方案一 §10.4.1）
ERROR_CODES = {
    # 模板错误 (T_xxx)
    "T_NOT_FOUND": "模板不存在",
    "T_INVALID_ZIP": "ZIP 文件格式无效",
    "T_TOO_LARGE": "模板文件过大",
    "T_NO_DRAFT_CONTENT": "ZIP 中缺少 draft_content.json",
    "T_INVALID_ID": "模板 ID 非法",
    # 槽位错误 (S_xxx)
    "S_NOT_FOUND": "槽位配置不存在",
    "S_TRACK_NOT_FOUND": "母版中找不到指定轨道",
    "S_SEGMENT_NOT_FOUND": "母版中找不到指定片段",
    "S_TYPE_MISMATCH": "槽位类型与轨道类型不匹配",
    "S_INVALID_SLOT": "槽位 ID 在母版中不存在",
    # 生成错误 (R_xxx)
    "R_MISSING_SLOT": "必填槽位未提供",
    "R_INVALID_PATH": "素材路径格式无效",
    "R_INVALID_DURATION": "素材时长异常",
    "R_LOOP_TOO_MANY": "视频时长不足，需循环次数过多",
    "R_SRT_PARSE_ERROR": "SRT 文件格式错误",
    "R_GENERATE_FAILED": "草稿生成失败",
    "R_EMPTY_VIDEO": "视频槽位为空",
    "R_ZERO_DURATION": "素材总时长为 0",
    "R_TASK_NOT_FOUND": "草稿任务不存在或已过期",
    "R_INVALID_TASK": "task_id 非法",
    # 通用
    "INTERNAL_ERROR": "服务器内部错误",
}


def make_error(code: str, message: str = None, details: dict = None) -> "VectCutError":
    """工厂函数：按错误码构造 VectCutError 子类实例。

    根据代码前缀（T_/S_/R_）选择对应子类，方便上层 catch。
    """
    msg = message or ERROR_CODES.get(code, code)
    if code.startswith("T_"):
        return TemplateError(msg)
    if code.startswith("S_"):
        return SlotError(msg)
    if code.startswith("R_"):
        return RenderError(msg)
    return VectCutError(msg)
```

注意：TemplateError/SlotError/RenderError 子类若未定义，需补上（参考方案二后端计划任务 1.1）：

```python
class TemplateError(VectCutError):
    code = "TEMPLATE_ERROR"
    http_status = 400


class SlotError(VectCutError):
    code = "SLOT_ERROR"
    http_status = 400


class RenderError(VectCutError):
    code = "RENDER_ERROR"
    http_status = 400
```

- [ ] **步骤 2.2：增强统一异常处理器，输出 code + details**

在 vectcut/server/http/app.py 的 _wire_exception_handlers() 中追加：

```python
@app.exception_handler(VectCutError)
async def vectcut_error_handler(request, exc: VectCutError):
    """VectCutError → 200 + {success:false, error:{code, message, details}}

    保持 HTTP 200（与现有信封一致），用 success 字段区分。
    """
    return JSONResponse(
        status_code=200,
        content={
            "success": False,
            "output": None,
            "error": {
                "code": exc.code,
                "message": str(exc),
                "details": getattr(exc, "details", {}) or {},
            },
        },
    )
```

- [ ] **步骤 2.3：单测错误码工厂**

```python
# tests/core/test_error_codes.py
"""错误码标准化测试。"""
from fastapi.testclient import TestClient

from vectcut.core.errors import (
    ERROR_CODES, make_error,
    TemplateError, SlotError, RenderError, VectCutError,
)


def test_make_error_template():
    err = make_error("T_NOT_FOUND")
    assert isinstance(err, TemplateError)


def test_make_error_slot():
    err = make_error("S_TRACK_NOT_FOUND")
    assert isinstance(err, SlotError)


def test_make_error_render():
    err = make_error("R_LOOP_TOO_MANY")
    assert isinstance(err, RenderError)


def test_make_error_unknown_falls_back():
    err = make_error("X_UNKNOWN")
    assert isinstance(err, VectCutError)


def test_all_error_codes_have_messages():
    for code, msg in ERROR_CODES.items():
        assert msg, f"错误码 {code} 缺少消息"


def test_error_response_envelope_shape():
    """异常处理器返回统一信封格式"""
    from vectcut.server.http.app import create_app
    client = TestClient(create_app())

    resp = client.get("/api/template/download/task_notexist_test")
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert isinstance(data["error"], dict)
    assert "code" in data["error"]
    assert "message" in data["error"]
```

- [ ] **步骤 2.4：运行测试 + Commit**

```bash
pytest tests/core/test_error_codes.py -v
git add vectcut/core/errors.py vectcut/server/http/app.py tests/core/test_error_codes.py
git commit -m "feat(core): standardize error codes with structured response envelope"
```

---
## 任务 3：日志系统（脱敏）

**文件：**
- 创建：vectcut/core/logger.py
- 创建：tests/core/test_logger.py

- [ ] **步骤 3.1：创建 logger.py（含路径/SRT/token 脱敏）**

```python
# vectcut/core/logger.py
"""统一日志器，内置用户隐私脱敏（方案一 §6.2）。

脱敏规则：
  - 素材路径：仅保留文件名
  - SRT 内容：仅记录字节数/行数
  - 下载 token：仅保留前 8 位
  - 敏感字段（password/token/api_key/secret）：替换为 ***
"""
from __future__ import annotations

import logging
import logging.handlers
import os
from pathlib import Path
from typing import Any, Dict


_SENSITIVE_KEYS = {"password", "token", "api_key", "secret", "access_key", "access_secret"}


def sanitize_path(path: str) -> str:
    """素材路径脱敏：仅保留文件名。"""
    if not path:
        return path
    return Path(path).name


def sanitize_srt(srt: str) -> str:
    """SRT 内容脱敏：仅记录字节数和行数。"""
    if not srt:
        return "SRT: empty"
    return f"SRT: {len(srt.encode('utf-8'))} bytes, {srt.count(chr(10)) + 1} lines"


def sanitize_token(token: str) -> str:
    """token 脱敏：仅保留前 8 位。"""
    if not token:
        return token
    return token[:8] + "..."


def sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """字典脱敏：敏感字段替换为 ***。"""
    result = {}
    for k, v in data.items():
        if k.lower() in _SENSITIVE_KEYS:
            result[k] = "***"
        elif isinstance(v, dict):
            result[k] = sanitize_dict(v)
        else:
            result[k] = v
    return result


def setup_logger(
    name: str,
    log_level: str = "INFO",
    log_dir: str = "logs",
    backup_days: int = 7,
) -> logging.Logger:
    """构造统一日志器（文件按天滚动 + 控制台双输出）。"""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    if logger.handlers:
        return logger

    os.makedirs(log_dir, exist_ok=True)

    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=os.path.join(log_dir, "vectcut.log"),
        when="midnight",
        backupCount=backup_days,
        encoding="utf-8",
    )
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    ))

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        "%(levelname)-8s | %(name)s | %(message)s"
    ))

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


default_logger = setup_logger("vectcut")
```

- [ ] **步骤 3.2：创建 test_logger.py（验证脱敏）**

```python
# tests/core/test_logger.py
"""日志脱敏测试。"""
from vectcut.core.logger import (
    sanitize_path, sanitize_srt, sanitize_token, sanitize_dict, setup_logger,
)


def test_sanitize_path_keeps_only_filename():
    assert sanitize_path("E:/素材/第5期/video1.mp4") == "video1.mp4"
    assert sanitize_path("C:\\Users\\test\\audio.mp3") == "audio.mp3"
    assert sanitize_path("simple.mp4") == "simple.mp4"


def test_sanitize_srt_records_size_only():
    srt = "1\n00:00:00,000 --> 00:00:02,000\n你好世界\n"
    result = sanitize_srt(srt)
    assert "bytes" in result
    assert "lines" in result
    assert "你好世界" not in result


def test_sanitize_token_keeps_first_8_chars():
    token = "abcdef1234567890xyz"
    result = sanitize_token(token)
    assert result == "abcdef12..."
    assert "xyz" not in result


def test_sanitize_dict_masks_sensitive_keys():
    data = {
        "username": "test",
        "password": "secret123",
        "api_key": "key456",
        "nested": {"token": "tok789", "safe": "ok"},
    }
    result = sanitize_dict(data)
    assert result["username"] == "test"
    assert result["password"] == "***"
    assert result["api_key"] == "***"
    assert result["nested"]["token"] == "***"
    assert result["nested"]["safe"] == "ok"


def test_setup_logger_returns_logger_with_handlers():
    import logging
    logger = setup_logger("test_vectcut", log_dir="logs")
    assert isinstance(logger, logging.Logger)
    assert len(logger.handlers) >= 2


def test_setup_logger_idempotent():
    logger1 = setup_logger("test_idempotent", log_dir="logs")
    handler_count = len(logger1.handlers)
    logger2 = setup_logger("test_idempotent", log_dir="logs")
    assert len(logger2.handlers) == handler_count
```

- [ ] **步骤 3.3：运行测试 + Commit**

```bash
pytest tests/core/test_logger.py -v
git add vectcut/core/logger.py tests/core/test_logger.py
git commit -m "feat(core): add sanitized logger with privacy protection"
```

---

## 任务 4：环境变量配置注入

**文件：**
- 修改：vectcut/core/config.py
- 创建：tests/core/test_config_env.py
- 创建：config.json.example
- 创建：.env.example

- [ ] **步骤 4.1：在 config.py 支持 ${VAR} 环境变量替换**

在 vectcut/core/config.py 追加（不破坏现有逻辑）：

```python
# vectcut/core/config.py 追加
import os
import re

# 匹配 ${VAR_NAME} 占位符（VAR_NAME 由字母数字下划线组成）
# 用字符类 [$][{] 代替转义，可读性更佳
_ENV_VAR_PATTERN = re.compile(r'[$][{]([A-Za-z0-9_]+)[}]')


def _expand_env_vars(content: str) -> str:
    """将配置文件中的 ${VAR_NAME} 替换为环境变量值。

    若环境变量未设置，保留原占位符（便于发现配置缺失）。
    """
    def _replacer(m):
        var_name = m.group(1)
        return os.getenv(var_name, m.group(0))

    return _ENV_VAR_PATTERN.sub(_replacer, content)


def load_config_with_env(path: str = "config.json") -> dict:
    """加载 config.json 并展开 ${VAR} 环境变量。"""
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    expanded = _expand_env_vars(content)
    import json
    return json.loads(expanded)
```

- [ ] **步骤 4.2：创建 test_config_env.py**

```python
# tests/core/test_config_env.py
"""环境变量配置注入测试。"""
import os
import tempfile

from vectcut.core.config import _expand_env_vars, load_config_with_env


def test_expand_env_vars_replaces_known():
    os.environ["TEST_DB_HOST"] = "myhost"
    try:
        content = '{"host": "${TEST_DB_HOST}"}'
        result = _expand_env_vars(content)
        assert result == '{"host": "myhost"}'
    finally:
        del os.environ["TEST_DB_HOST"]


def test_expand_env_vars_keeps_unknown():
    os.environ.pop("TEST_UNKNOWN_VAR", None)
    content = '{"host": "${TEST_UNKNOWN_VAR}"}'
    result = _expand_env_vars(content)
    assert "${TEST_UNKNOWN_VAR}" in result


def test_load_config_with_env():
    os.environ["TEST_PORT"] = "9999"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as handle:
        handle.write('{"port": "${TEST_PORT}", "name": "test"}')
        tmp_path = handle.name
    try:
        cfg = load_config_with_env(tmp_path)
        assert cfg["port"] == "9999"
        assert cfg["name"] == "test"
    finally:
        os.remove(tmp_path)
        del os.environ["TEST_PORT"]
```

- [ ] **步骤 4.3：创建 config.json.example**

```json
{
  "draft_profile": "jianying_pro_10",
  "is_capcut_env": false,
  "api_base_url": "https://api.vectcut.com/api",
  "port": 9001,
  "template_folder": "/app/data/templates",
  "template_config_folder": "/app/data/template_configs",
  "generated_draft_folder": "/app/data/generated",
  "temp_folder": "/app/data/temp",
  "max_template_zip_mb": 50,
  "auth": {
    "api_token": "${API_AUTH_TOKEN}"
  },
  "oss_config": {
    "enabled": false,
    "bucket_name": "${OSS_BUCKET}",
    "access_key_id": "${OSS_ACCESS_KEY}",
    "access_key_secret": "${OSS_ACCESS_SECRET}",
    "endpoint": "${OSS_ENDPOINT}"
  }
}
```

- [ ] **步骤 4.4：创建 .env.example**

```bash
# OSS 配置（可选，仅保存母版 ZIP 和生成草稿 ZIP）
OSS_BUCKET=your-bucket
OSS_ACCESS_KEY=your-key
OSS_ACCESS_SECRET=your-secret
OSS_ENDPOINT=https://oss-cn-hangzhou.aliyuncs.com

# API 访问控制
API_AUTH_TOKEN=replace-with-random-token
MAX_TEMPLATE_ZIP_MB=50

# 时区
TZ=Asia/Shanghai
```

- [ ] **步骤 4.5：运行测试 + Commit**

```bash
pytest tests/core/test_config_env.py -v
git add vectcut/core/config.py tests/core/test_config_env.py config.json.example .env.example
git commit -m "feat(core): support env var injection in config"
```

---
## 任务 5：Dockerfile

**文件：**
- 创建：docker/Dockerfile.api

- [ ] **步骤 5.1：创建 Dockerfile.api**

```dockerfile
# docker/Dockerfile.api
FROM python:3.10-slim

# 安装系统依赖（curl 用于 HEALTHCHECK）
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 复制依赖文件并安装（利用 Docker 层缓存）
COPY requirements.txt requirements-mcp.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -r requirements-mcp.txt || true

# 复制项目代码
COPY vectcut/ ./vectcut/
COPY run_http.py run_mcp.py ./
COPY config.json.example ./config.json.example

# 创建数据目录（运行时由 Volume 覆盖）
RUN mkdir -p \
    /app/data/templates \
    /app/data/template_configs \
    /app/data/generated \
    /app/data/temp \
    /app/logs

EXPOSE 9001

# 健康检查：每 30s 探活 /api/health
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -fsS http://localhost:9001/api/health || exit 1

# 时区
ENV TZ=Asia/Shanghai
ENV PYTHONUNBUFFERED=1

CMD ["python", "run_http.py"]
```

- [ ] **步骤 5.2：创建 docker/.gitignore（忽略证书和敏感文件）**

```gitignore
# docker/.gitignore
ssl/
*.pem
*.key
.htpasswd
```

- [ ] **步骤 5.3：本地构建验证**

```bash
# 在仓库根目录执行
docker build -f docker/Dockerfile.api -t vectcut-api:dev .

# 预期：构建成功，最后一行输出 Successfully tagged vectcut-api:dev
```

- [ ] **步骤 5.4：本地运行验证镜像**

```bash
# 运行容器（映射端口，挂载临时数据卷）
docker run --rm -d \
  --name vectcut-api-test \
  -p 9001:9001 \
  vectcut-api:dev

# 等待 5 秒后测试健康检查
timeout 5 docker logs -f vectcut-api-test || true
curl http://localhost:9001/api/health
# 预期：{"status":"healthy",...}

# 清理
docker stop vectcut-api-test
```

- [ ] **步骤 5.5：Commit**

```bash
git add docker/Dockerfile.api docker/.gitignore
git commit -m "feat(docker): add Dockerfile.api with healthcheck"
```

---

## 任务 6：Docker Compose 编排

**文件：**
- 创建：docker-compose.yml（生产）
- 创建：docker-compose.override.yml（开发覆盖）

- [ ] **步骤 6.1：创建 docker-compose.yml（生产单实例）**

```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build:
      context: .
      dockerfile: docker/Dockerfile.api
    image: vectcut-api:latest
    container_name: vectcut-api
    restart: unless-stopped
    env_file:
      - .env
    environment:
      - TZ=Asia/Shanghai
      - PYTHONUNBUFFERED=1
    volumes:
      - ./config.json:/app/config.json:ro
      - template_data:/app/data/templates
      - template_config_data:/app/data/template_configs
      - generated_data:/app/data/generated
      - temp_data:/app/data/temp
      - logs_data:/app/logs
    networks:
      - vectcut_net
    healthcheck:
      test: ["CMD", "curl", "-fsS", "http://localhost:9001/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  nginx:
    image: nginx:alpine
    container_name: vectcut-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./docker/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./docker/ssl:/etc/nginx/ssl:ro
    depends_on:
      api:
        condition: service_healthy
    networks:
      - vectcut_net

networks:
  vectcut_net:
    driver: bridge

volumes:
  template_data:
  template_config_data:
  generated_data:
  temp_data:
  logs_data:
```

- [ ] **步骤 6.2：创建 docker-compose.override.yml（开发环境，不启动 nginx）**

```yaml
# docker-compose.override.yml
# 开发环境覆盖：仅启动 api，直接暴露端口，无需 SSL
version: '3.8'

services:
  api:
    ports:
      - "9001:9001"
    environment:
      - PYTHONUNBUFFERED=1

  nginx:
    profiles: ["production"]  # 开发时不启动 nginx
```

- [ ] **步骤 6.3：config.yml 配置校验测试**

```bash
# 校验 compose 文件语法
docker-compose config
# 预期：输出完整的合并配置，无报错

# 校验开发环境（不含 nginx）
docker-compose --profile production config > /dev/null && echo "production config OK"
```

- [ ] **步骤 6.4：启动开发环境验证**

```bash
# 准备最小 config.json
cp config.json.example config.json
# 编辑 config.json，把 ${...} 占位符替换为实际值或留空

# 启动（开发模式，仅 api）
docker-compose up -d

# 验证
docker-compose ps
curl http://localhost:9001/api/health

# 查看日志
docker-compose logs -f api

# 清理
docker-compose down
```

- [ ] **步骤 6.5：数据持久化验证（关键）**

```bash
# 启动并写入测试数据
docker-compose up -d
curl -X POST "http://localhost:9001/api/template/import?template_id=persist_test" \
  -F "file=@./test_template.zip"

# 重启容器
docker-compose restart api
sleep 5

# 验证数据还在（导入过的模板应能查询）
curl http://localhost:9001/api/template/import?template_id=persist_test
# 预期：提示模板已存在或返回槽位信息，说明 Volume 持久化生效
```

- [ ] **步骤 6.6：Commit**

```bash
git add docker-compose.yml docker-compose.override.yml
git commit -m "feat(docker): add compose orchestration with volumes and dev override"
```

---
## 任务 7：Nginx 反向代理 + SSL

**文件：**
- 创建：docker/nginx.conf

- [ ] **步骤 7.1：创建 nginx.conf（保留 /api 前缀转发）**

```nginx
# docker/nginx.conf
events {
    worker_connections 1024;
}

http {
    upstream vectcut_api {
        server api:9001;
    }

    # 限流：每 IP 每秒 10 个请求，突发 20
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

    # HTTP → HTTPS 重定向
    server {
        listen 80;
        server_name _;
        return 301 https://$host$request_uri;
    }

    # HTTPS 主服务
    server {
        listen 443 ssl http2;
        server_name _;

        # SSL 证书（占位，生产替换为真实证书路径）
        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;

        # 母版 ZIP 上传上限 50M（用户素材不上传云端）
        client_max_body_size 50M;

        # API 代理：proxy_pass 不带尾部斜杠，保留 /api 前缀
        location /api/ {
            limit_req zone=api_limit burst=20 nodelay;

            proxy_pass http://vectcut_api;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            proxy_connect_timeout 300s;
            proxy_send_timeout 300s;
            proxy_read_timeout 300s;
        }

        # 健康检查（运维探活用）
        location /health {
            proxy_pass http://vectcut_api/api/health;
        }
    }
}
```

- [ ] **步骤 7.2：准备自签名证书（开发/测试用）**

```bash
# 生成自签名证书，仅用于开发测试
mkdir -p docker/ssl

# 用 openssl 生成（需本地装 openssl，或用 wsl）
openssl req -x509 -newkey rsa:4096 -nodes \
  -keyout docker/ssl/privkey.pem \
  -out docker/ssl/fullchain.pem \
  -days 365 \
  -subj "/CN=localhost"

# 校验证书已生成
ls -la docker/ssl/
# 预期：fullchain.pem 和 privkey.pem
```

- [ ] **步骤 7.3：Nginx 配置语法校验**

```bash
# 启动 nginx 容器校验配置语法
docker run --rm \
  -v $(pwd)/docker/nginx.conf:/etc/nginx/nginx.conf:ro \
  nginx:alpine nginx -t

# 预期：syntax is ok / test is successful
```

- [ ] **步骤 7.4：生产环境联调（带 nginx profile）**

```bash
# 启动完整栈（api + nginx）
docker-compose --profile production up -d

# 等待健康检查通过
sleep 30
docker-compose ps
# 预期：api 和 nginx 都 healthy

# 测试 HTTPS（自签名证书用 -k 跳过校验）
curl -k https://localhost/api/health
# 预期：{"status":"healthy",...}

# 测试 HTTP → HTTPS 重定向
curl -I http://localhost/api/health
# 预期：301 Moved Permanently

# 清理
docker-compose --profile production down
```

- [ ] **步骤 7.5：Commit**

```bash
git add docker/nginx.conf
git commit -m "feat(docker): add nginx reverse proxy with SSL and rate limiting"
```

---

## 任务 8：访问控制与限流细化

**文件：**
- 修改：docker/nginx.conf（添加基础认证）
- 创建：docker/ssl/.htpasswd.example（占位说明）

- [ ] **步骤 8.1：在 nginx.conf 添加可选基础认证**

修改 docker/nginx.conf 的 `location /api/` 块，在 limit_req 之后追加：

```nginx
        location /api/ {
            limit_req zone=api_limit burst=20 nodelay;

            # 基础认证（生产环境启用，开发环境注释掉）
            # auth_basic "VectCut API";
            # auth_basic_user_file /etc/nginx/.htpasswd;

            proxy_pass http://vectcut_api;
            # ... 其余 proxy_set_header 保持不变
        }
```

- [ ] **步骤 8.2：生成 .htpasswd（生产环境）**

```bash
# 安装 apache2-utils（含 htpasswd）
# Ubuntu/Debian: apt-get install -y apache2-utils

# 生成密码文件（交互式输入密码）
htpasswd -c docker/ssl/.htpasswd admin
# 或非交互式：
# htpasswd -bc docker/ssl/.htpasswd admin YOUR_PASSWORD

# 校验
cat docker/ssl/.htpasswd
# 预期：admin:$apr1$xxxxx...
```

- [ ] **步骤 8.3：在 docker-compose.yml 挂载 .htpasswd**

修改 docker-compose.yml 的 nginx.volumes 追加：

```yaml
    volumes:
      - ./docker/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./docker/ssl:/etc/nginx/ssl:ro
      - ./docker/ssl/.htpasswd:/etc/nginx/.htpasswd:ro
```

- [ ] **步骤 8.4：启用并验证基础认证**

```bash
# 取消 nginx.conf 中 auth_basic 两行的注释
# 重启 nginx
docker-compose --profile production restart nginx

# 不带认证 → 401
curl -k https://localhost/api/health
# 预期：401 Authorization Required

# 带认证 → 200
curl -k -u admin:YOUR_PASSWORD https://localhost/api/health
# 预期：{"status":"healthy",...}
```

- [ ] **步骤 8.5：Commit**

```bash
git add docker/nginx.conf docker-compose.yml
git commit -m "feat(docker): add optional basic auth for production"
```

---
## 任务 9：数据备份脚本

**文件：**
- 创建：scripts/backup.sh
- 创建：scripts/deploy.sh

- [ ] **步骤 9.1：创建 backup.sh（备份三个数据卷）**

```bash
#!/usr/bin/env bash
# scripts/backup.sh
# 备份 template_data / template_config_data / generated_data 三个数据卷
# 用法：./scripts/backup.sh [backup_dir]
# 默认备份到 ./backup/

set -euo pipefail

BACKUP_DIR="${1:-./backup}"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
mkdir -p "$BACKUP_DIR"

# 项目名（docker-compose 默认用目录名作前缀，需根据实际调整）
PROJECT_NAME="vectcutapi"

echo "开始备份到 $BACKUP_DIR ..."

for VOL in template_data template_config_data generated_data; do
    FULL_VOL="${PROJECT_NAME}_${VOL}"
    OUT="$BACKUP_DIR/${VOL}-${TIMESTAMP}.tar.gz"

    echo "备份 $FULL_VOL → $OUT"
    docker run --rm \
        -v "${FULL_VOL}:/data:ro" \
        -v "$(pwd)/${BACKUP_DIR#/}:/backup" \
        alpine tar czf "/backup/${VOL}-${TIMESTAMP}.tar.gz" -C /data .

    echo "  ✓ $OUT ($(du -h "$OUT" | cut -f1))"
done

echo ""
echo "备份完成：$BACKUP_DIR"
ls -lh "$BACKUP_DIR"/*-"$TIMESTAMP".tar.gz
```

- [ ] **步骤 9.2：创建 deploy.sh（一键部署/更新）**

```bash
#!/usr/bin/env bash
# scripts/deploy.sh
# 用法：
#   ./scripts/deploy.sh         # 拉取并重启（生产）
#   ./scripts/deploy.sh --build # 重新构建并启动
#   ./scripts/deploy.sh --prod  # 含 nginx 完整栈
#   ./scripts/deploy.sh --down  # 停止并清理

set -euo pipefail

PROFILE="--profile production"
ACTION="up"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --build) BUILD="--build"; shift;;
        --prod)  PROFILE="--profile production"; shift;;
        --dev)   PROFILE=""; shift;;
        --down)  ACTION="down"; shift;;
        *) echo "未知参数：$1"; exit 1;;
    esac
done

if [[ "$ACTION" == "down" ]]; then
    echo "停止服务 ..."
    docker-compose $PROFILE down
    exit 0
fi

echo "拉取最新代码 ..."
git pull --ff-only

echo "构建并启动 ..."
docker-compose $PROFILE up -d $BUILD

echo "等待健康检查 ..."
for i in {1..12}; do
    if curl -fsS http://localhost:9001/api/health > /dev/null 2>&1; then
        echo "✓ 服务健康"
        docker-compose $PROFILE ps
        exit 0
    fi
    sleep 5
done

echo "✗ 健康检查超时，查看日志："
docker-compose $PROFILE logs --tail=50 api
exit 1
```

- [ ] **步骤 9.3：赋予脚本可执行权限并验证语法**

```bash
chmod +x scripts/backup.sh scripts/deploy.sh

# bash 语法校验
bash -n scripts/backup.sh && echo "backup.sh 语法 OK"
bash -n scripts/deploy.sh && echo "deploy.sh 语法 OK"
```

- [ ] **步骤 9.4：执行备份验证（在已有数据的环境）**

```bash
# 前提：容器已运行且有数据
./scripts/backup.sh ./backup

# 预期：backup/ 目录下生成 3 个 tar.gz 文件
ls -lh backup/
```

- [ ] **步骤 9.5：Commit**

```bash
git add scripts/backup.sh scripts/deploy.sh
git commit -m "feat(scripts): add backup and deploy scripts"
```

---

## 任务 10：部署文档与端到端验收

**文件：**
- 创建：docs/deployment/README.md
- 修改：README.md（追加部署章节链接）

- [ ] **步骤 10.1：创建部署文档 docs/deployment/README.md**

````markdown
# VectCutAPI 部署指南

## 一、本地开发部署（MVP 1.0 内测）

无需 Docker，直接运行：

```bash
git clone <repo-url> && cd VectCutAPI
pip install -r requirements.txt
cp config.json.example config.json
# 编辑 config.json
mkdir -p data/{templates,template_configs,generated,temp}
python run_http.py
```

验证：访问 http://localhost:9001/api/health

## 二、Docker 开发部署

```bash
cp config.json.example config.json
cp .env.example .env
# 编辑配置
docker-compose up -d
```

## 三、生产部署（Docker + Nginx + SSL）

### 1. 准备服务器

- 云服务器：2 核 4G / 60G SSD（推荐阿里云/腾讯云）
- 已安装 Docker + Docker Compose
- 域名解析到服务器 IP

### 2. 部署步骤

```bash
git clone <repo-url> && cd VectCutAPI
cp config.json.example config.json
cp .env.example .env

# 编辑 config.json：api_base_url 改为实际域名
# 编辑 .env：填入 API_AUTH_TOKEN、OSS 配置（可选）

# 申请 SSL 证书（Let's Encrypt）
mkdir -p docker/ssl
# 把 fullchain.pem 和 privkey.pem 放到 docker/ssl/

# 生成 htpasswd（基础认证）
htpasswd -bc docker/ssl/.htpasswd admin YOUR_PASSWORD

# 取消 nginx.conf 中 auth_basic 的注释

# 启动完整栈
docker-compose --profile production up -d

# 验证
curl -k -u admin:YOUR_PASSWORD https://your-domain.com/api/health
```

### 3. 更新部署

```bash
./scripts/deploy.sh --build --prod
```

### 4. 数据备份

```bash
./scripts/backup.sh ./backup
# 建议加入 crontab 每日备份
```

## 四、运维命令速查

| 操作 | 命令 |
|------|------|
| 查看日志 | `docker-compose logs -f api` |
| 查看最近 100 行 | `docker-compose logs --tail=100 api` |
| 按时间导出 | `docker-compose logs --since="2026-07-05T10:00:00" api` |
| 重启服务 | `docker-compose restart api` |
| 进入容器 | `docker-compose exec api bash` |
| 查看卷 | `docker volume inspect vectcutapi_template_data` |
| 清理旧镜像 | `docker image prune -f` |

## 五、故障排查

### 容器无法启动

```bash
docker-compose logs api
docker-compose exec api python -c "from vectcut.core.config import load_config_with_env; print(load_config_with_env())"
```

### 数据丢失

确认 Volume 挂载正确：

```bash
docker volume ls | grep vectcutapi
docker volume inspect vectcutapi_template_data
```

### Nginx 502

- 检查 api 容器健康状态：`docker-compose ps`
- 检查 api 是否在 9001 端口监听：`docker-compose exec api curl http://localhost:9001/api/health`
````

- [ ] **步骤 10.2：在 README.md 追加部署章节入口**

在 README.md 末尾追加：

```markdown
## 部署

详见 [部署指南](docs/deployment/README.md)。

- **本地开发**：`pip install -r requirements.txt && python run_http.py`
- **Docker 部署**：`docker-compose up -d`
- **生产部署**：Docker + Nginx + SSL（含基础认证、限流、数据备份）

云端 API 基座规格见 `docs/superpowers/specs/2026-07-04-solution1-docker-deployment.md`。
```

- [ ] **步骤 10.3：端到端验收清单（对照方案一规格）**

逐项确认：

- [ ] `GET /api/health` 返回 healthy（任务 1）
- [ ] 错误码标准化 + 统一信封格式（任务 2）
- [ ] 日志脱敏（路径/SRT/token/敏感字段）（任务 3）
- [ ] `${VAR}` 环境变量注入生效（任务 4）
- [ ] Dockerfile.api 可构建可运行（任务 5）
- [ ] docker-compose 编排 + Volume 持久化（任务 6）
- [ ] Nginx 反向代理 + SSL + 限流（任务 7）
- [ ] 基础认证（生产）（任务 8）
- [ ] 备份脚本可用（任务 9）
- [ ] 部署文档完整（任务 10.1）

- [ ] **步骤 10.4：最终 Commit**

```bash
git add docs/deployment/README.md README.md
git commit -m "docs(deployment): add deployment guide and wire README"
```

---

## 附录 A：规格映射

| 方案一规格章节 | 实现任务 |
|---------------|---------|
| §0.2 MVP 本地快速启动 | 任务 1（健康检查）+ 部署文档（任务 10） |
| §3.2 Dockerfile + Compose + Nginx | 任务 5、6、7 |
| §4 配置管理（环境变量） | 任务 4 |
| §5 部署流程（初次/更新/备份） | 任务 9（脚本）+ 任务 10（文档） |
| §6.1 健康检查 | 任务 1 |
| §6.2 日志管理（脱敏） | 任务 3 |
| §9 安全加固（认证/限流） | 任务 7（限流）+ 任务 8（认证） |
| §10.4 错误信息用户化 | 任务 2（错误码标准化） |

## 附录 B：验收命令汇总

```bash
# 单测
pytest tests/server/http/test_health.py tests/core/test_error_codes.py tests/core/test_logger.py tests/core/test_config_env.py -v

# Docker 构建
docker build -f docker/Dockerfile.api -t vectcut-api:dev .

# Compose 配置校验
docker-compose config > /dev/null && echo "compose OK"
docker-compose --profile production config > /dev/null && echo "production compose OK"

# Nginx 配置校验
docker run --rm -v $(pwd)/docker/nginx.conf:/etc/nginx/nginx.conf:ro nginx:alpine nginx -t

# 脚本语法校验
bash -n scripts/backup.sh && bash -n scripts/deploy.sh

# 端到端
docker-compose --profile production up -d
sleep 30
curl -k -u admin:PASSWORD https://localhost/api/health
```

---

**计划结束。** 任意零上下文工程师按任务 1→10 顺序执行，每步带可运行代码与验证命令，即可交付可工作的 Docker 化 VectCutAPI 云端部署。

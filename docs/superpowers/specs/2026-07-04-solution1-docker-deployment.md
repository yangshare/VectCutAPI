# 方案一：VectCutAPI Docker 云端部署方案

- 日期：2026-07-04
- 最后更新：2026-07-05（补充 MVP 部署策略、错误信息用户化、日志策略）
- 状态：待评审
- 范围：支撑方案二 Electron 桌面客户端的 VectCutAPI 云端 API 容器化部署

## 0. MVP 部署策略 ⚠️

**重要决策**：MVP 1.0 阶段（10-20 人内测）不需要立即上云，本地开发环境即可。

### 0.1 阶段化部署路径

| 阶段 | 用户规模 | 部署方式 | 成本 | 何时迁移 |
|------|---------|---------|------|---------|
| **MVP 1.0 内测** | 10-20 人 | 开发者本机 `python run_http.py` | ¥0 | 核心假设验证通过后 |
| **MVP 1.5 公测** | 30-100 人 | 单台云服务器 Docker | ~¥120/月 | 内测反馈良好，准备扩大测试 |
| **正式发布** | 100+ 人 | Docker + Nginx + OSS | ~¥300/月 | 用户增长到 50+ 活跃 |
| **规模化** | 500+ 人 | K8s + 数据库 + 负载均衡 | ~¥1000/月 | 并发请求 > 10 QPS |

### 0.2 MVP 1.0 本地部署快速启动

```bash
# 1. 克隆项目
git clone https://github.com/your-org/VectCutAPI.git
cd VectCutAPI

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置文件（最小配置）
cat > config.json << EOF
{
  "draft_profile": "jianying_pro_10",
  "port": 9001,
  "template_folder": "./data/templates",
  "template_config_folder": "./data/template_configs",
  "generated_draft_folder": "./data/generated",
  "temp_folder": "./data/temp"
}
EOF

# 4. 创建数据目录
mkdir -p data/{templates,template_configs,generated,temp}

# 5. 启动服务
python run_http.py

# 6. 验证
curl http://localhost:9001/api/health
```

**内测用户访问方式**：
- 开发者本机作为服务器
- 使用内网穿透工具（ngrok / frp）暴露给内测用户
- 或通过 Tailscale 组网（更安全）

**何时迁移到云端**：
- ✅ 核心假设验证通过（方案二 §0）
- ✅ 内测用户反馈良好（满意度 ≥ 4/5）
- ✅ 准备扩大测试范围（> 20 人）

## 1. 方案目标

将 VectCutAPI（FastAPI 接口服务）容器化，实现云端部署，为方案二的 Electron 桌面客户端提供稳定 API 基座。

本方案的生产主线是：**桌面客户端上传母版 ZIP，提交本地素材路径/时长/尺寸等元数据，云端生成草稿 JSON/ZIP；用户音视频/图片素材不上传云端，云端也不读取这些本地路径。**

**核心原则**：
- 核心剪辑能力在服务端
- 接口服务可独立部署；MVP 先按单实例部署，后续引入共享存储/数据库后再水平扩展
- HTTP API 为生产主入口；MCP 协议可作为独立进程按需部署
- 后端 FastAPI 真实挂载 `/api` 前缀，反向代理必须保留 `/api`
- 云端只持有母版、槽位配置、SRT 文本和生成草稿包，不持有用户素材文件

## 2. 当前状态分析

### 2.1 现有架构

```
VectCutAPI（本地运行）
├── run_http.py        # FastAPI 入口，端口 9001
├── run_mcp.py         # MCP 协议入口
├── vectcut/
│   ├── core/          # 配置、错误处理
│   ├── features/      # 业务功能（draft/...；新增 template_filling）
│   ├── engine/        # pyJianYingDraft 引擎适配层
│   └── server/
│       ├── http/      # FastAPI app
│       └── mcp/       # MCP runtime
├── config.json        # 配置文件
└── requirements.txt   # Python 依赖
```

### 2.2 方案二需要的服务端能力

方案二不需要云端读取或上传用户素材，只需要云端具备母版解析、槽位配置、元数据写草稿和草稿 ZIP 下载能力。

| 能力 | 说明 | 状态 |
|------|------|------|
| **FastAPI HTTP 服务** | 统一暴露 `/api/template/*` 接口 | 已有底座 |
| **pyJianYingDraft 引擎适配** | 复制母版、修改 `draft_content.json`、保存草稿 | 已有底座 |
| **字幕/SRT 能力** | 解析 SRT，继承母版字幕样式并重建字幕轨 | 已有底座，需封装到套版流程 |
| **模板套版 feature** | import_template、save_slot_config、render_draft、download_draft | 待新增 |
| **JSON 文件存储** | 保存模板、槽位配置、生成草稿索引 | 待新增 |

### 2.3 部署需求

- Python 3.10+ 运行环境
- pyJianYingDraft 依赖
- 文件存储（母版 ZIP、模板配置、生成草稿 ZIP）
- 可选：OSS 配置（用于母版 ZIP 和生成草稿 ZIP）

## 3. Docker 部署架构

### 3.1 架构图

```
┌────────────────────────────────────────────────────────┐
│ 外部访问（Electron 桌面客户端 / 运维访问）               │
└───────────────────────┬────────────────────────────────┘
                        │ HTTPS
┌───────────────────────▼────────────────────────────────┐
│ Nginx 容器（反向代理 + SSL）                            │
│   · HTTP  → :80   → FastAPI :9001                      │
│   · HTTPS → :443  → FastAPI :9001                      │
│   · 保留 /api 前缀转发，不直接暴露草稿目录               │
└───────────────────────┬────────────────────────────────┘
                        │
┌───────────────────────▼────────────────────────────────┐
│ VectCutAPI 容器（FastAPI + template_filling + 引擎）    │
│ ┌────────────────────────────────────────────────────┐ │
│ │ FastAPI (run_http.py)                              │ │
│ │   · 端口：9001                                      │ │
│ │   · 路由：/api/template/import、/api/template/render│ │
│ │   · 响应格式：{success, output, error}              │ │
│ └────────────────────────────────────────────────────┘ │
│ ┌────────────────────────────────────────────────────┐ │
│ │ template_filling feature                            │ │
│ │   · 解析母版 ZIP → 保存模板/槽位配置                │ │
│ │   · 接收路径/时长/尺寸/SRT 文本等元数据             │ │
│ │   · 调用引擎生成 draft_content.json 并打包 ZIP      │ │
│ └────────────────────────────────────────────────────┘ │
│ ┌────────────────────────────────────────────────────┐ │
│ │ pyJianYingDraft 引擎                                │ │
│ │   · duplicate_as_template                           │ │
│ │   · Script_file（写入本地素材路径引用，不读文件）    │ │
│ │   · 字幕/封面样式继承与时间轴重算                  │ │
│ └────────────────────────────────────────────────────┘ │
└───────────────────────┬────────────────────────────────┘
                        │
┌───────────────────────▼────────────────────────────────┐
│ Docker Volume（持久化存储）                             │
│   · /app/data/templates/        母版 ZIP / 母版解包缓存  │
│   · /app/data/template_configs/ 模板与槽位配置 JSON     │
│   · /app/data/generated/        生成草稿 ZIP             │
│   · /app/data/temp/             临时文件                 │
│   · /app/config.json            配置文件挂载             │
└────────────────────────────────────────────────────────┘
```

### 3.2 容器设计

#### 3.2.1 VectCutAPI 容器（Dockerfile.api）

```dockerfile
FROM python:3.10-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY requirements.txt requirements-mcp.txt ./

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -r requirements-mcp.txt

# 复制项目代码
COPY vectcut/ ./vectcut/
COPY run_http.py run_mcp.py ./

# 创建数据目录
RUN mkdir -p \
    /app/data/templates \
    /app/data/template_configs \
    /app/data/generated \
    /app/data/temp

# 暴露端口
EXPOSE 9001

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:9001/api/health || exit 1

# 启动命令
CMD ["python", "run_http.py"]
```

#### 3.2.2 Nginx 容器配置（nginx.conf）

```nginx
upstream vectcut_api {
    server api:9001;
}

server {
    listen 80;
    server_name your-domain.com;

    # HTTP 重定向到 HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL 证书配置
    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # 仅允许上传母版草稿 ZIP；用户素材不上传云端
    client_max_body_size 50M;

    # API 代理：后端真实挂载 /api，proxy_pass 不带尾部 /，避免剥离 /api 前缀
    location /api/ {
        proxy_pass http://vectcut_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 超时配置（处理长时间操作）
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # 健康检查端点
    location /health {
        proxy_pass http://vectcut_api/api/health;
    }
}
```

#### 3.2.3 Docker Compose 编排（docker-compose.yml）

```yaml
version: '3.8'

services:
  api:
    build:
      context: .
      dockerfile: docker/Dockerfile.api
    container_name: vectcut-api
    restart: unless-stopped
    volumes:
      - ./config.json:/app/config.json:ro          # 配置文件（只读）
      - template_data:/app/data/templates          # 母版 ZIP / 母版解包缓存
      - template_config_data:/app/data/template_configs # 模板与槽位配置 JSON
      - generated_data:/app/data/generated         # 生成草稿 ZIP
      - temp_data:/app/data/temp                   # 临时文件
    environment:
      - TZ=Asia/Shanghai                           # 时区
      - PYTHONUNBUFFERED=1                         # Python 输出不缓冲
    networks:
      - vectcut_net
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9001/api/health"]
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
      - ./docker/ssl:/etc/nginx/ssl:ro             # SSL 证书
    depends_on:
      api:
        condition: service_healthy
    networks:
      - vectcut_net

networks:
  vectcut_net:
    driver: bridge

volumes:
  template_data:          # 母版 ZIP / 母版解包缓存
  template_config_data:   # 模板与槽位配置 JSON
  generated_data:         # 生成草稿 ZIP
  temp_data:              # 临时文件（可定期清理）
```

## 4. 配置管理

### 4.1 配置文件（config.json）

方案二主链路的最小配置如下。

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

### 4.2 环境变量（.env）

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

### 4.3 配置注入（支持环境变量）

修改 `vectcut/core/config.py` 支持环境变量替换：

```python
import os
import re

def load_config(path: str = "config.json") -> Config:
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
        # 替换环境变量 ${VAR_NAME}
        content = re.sub(
            r'\$\{(\w+)\}',
            lambda m: os.getenv(m.group(1), m.group(0)),
            content
        )
        data = json.loads(content)
    return Config(**data)
```

## 5. 部署流程

### 5.1 初次部署

```bash
# 1. 克隆项目
git clone https://github.com/your-org/VectCutAPI.git
cd VectCutAPI

# 2. 准备配置文件
cp config.json.example config.json
# 编辑 config.json，或配置 .env 文件

# 3. 准备 SSL 证书（Let's Encrypt）
mkdir -p docker/ssl
# 将证书文件放到 docker/ssl/ 目录
# 或使用 certbot 自动申请：
# certbot certonly --standalone -d your-domain.com

# 4. 构建并启动
docker-compose build
docker-compose up -d

# 5. 查看日志
docker-compose logs -f api

# 6. 测试接口
curl https://your-domain.com/api/health
```

### 5.2 更新部署

```bash
# 1. 拉取最新代码
git pull origin main

# 2. 重新构建
docker-compose build

# 3. 滚动更新（零停机）
docker-compose up -d --no-deps --build api

# 4. 清理旧镜像
docker image prune -f
```

### 5.3 数据备份

```bash
# 备份全部业务数据（母版、模板配置、生成草稿）
mkdir -p backup

docker run --rm \
  -v vectcutapi_template_data:/data \
  -v $(pwd)/backup:/backup \
  alpine tar czf /backup/templates-$(date +%Y%m%d-%H%M%S).tar.gz -C /data .

docker run --rm \
  -v vectcutapi_template_config_data:/data \
  -v $(pwd)/backup:/backup \
  alpine tar czf /backup/template-configs-$(date +%Y%m%d-%H%M%S).tar.gz -C /data .

docker run --rm \
  -v vectcutapi_generated_data:/data \
  -v $(pwd)/backup:/backup \
  alpine tar czf /backup/generated-$(date +%Y%m%d-%H%M%S).tar.gz -C /data .
```

## 6. 监控与运维

### 6.1 健康检查

在 `vectcut/server/http/app.py` 中添加健康检查端点。后端真实挂载 `/api` 时，对外路径为 `/api/health`：

```python
@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }
```

### 6.2 日志管理

**生产日志脱敏规则**（保护用户隐私）：

| 数据类型 | 记录策略 | 示例 |
|---------|---------|------|
| **素材路径** | 仅记录文件名和扩展名，不记录完整路径 | ✅ `video1.mp4` ❌ `E:/素材/第5期/video1.mp4` |
| **SRT 内容** | 仅记录字节数/行数，不记录文本内容 | ✅ `SRT: 1024 bytes, 15 lines` ❌ 完整 SRT 文本 |
| **draft_content.json** | 不记录完整 JSON，仅记录关键指标 | ✅ `tracks: 5, segments: 12, duration: 120s` |
| **下载 token** | 不记录完整 token，仅记录前 8 位 | ✅ `token: abc12345...` ❌ 完整 token |
| **用户 IP** | 记录但定期清理（7 天） | ✅ 记录供限流，但 7 天后删除 |

**日志级别策略**：

```python
# vectcut/core/logger.py
import logging
from pathlib import Path

def setup_logger(name: str, log_level: str = "INFO"):
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level))
    
    # 文件日志（保留 7 天）
    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename="logs/vectcut.log",
        when="midnight",
        backupCount=7,
        encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
    ))
    
    # 控制台日志（开发用）
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '%(levelname)-8s | %(message)s'
    ))
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# 使用示例
logger = setup_logger("vectcut.template_filling")

# ✅ 正确：脱敏日志
logger.info(f"处理槽位 video1，文件: {Path(file_path).name}")

# ❌ 错误：泄露隐私
logger.info(f"处理槽位 video1，路径: {file_path}")
```

**用户问题排查日志策略**：

为了帮助用户排查问题，同时保护隐私，提供"诊断模式"（用户主动开启）：

```python
# 诊断模式（仅在用户主动开启时记录详细信息）
class DiagnosticLogger:
    def __init__(self, enabled: bool = False):
        self.enabled = enabled
        self.session_id = generate_session_id()
        self.log_file = f"logs/diagnostic_{self.session_id}.log"
    
    def log(self, level: str, message: str, **context):
        if not self.enabled:
            return
        
        # 诊断模式下记录完整上下文（但仍脱敏敏感信息）
        with open(self.log_file, 'a', encoding='utf-8') as f:
            sanitized_context = self._sanitize(context)
            f.write(f"{datetime.now()} | {level} | {message} | {sanitized_context}\n")
    
    def _sanitize(self, context: dict) -> dict:
        """即使在诊断模式，也要脱敏敏感字段"""
        sensitive_keys = ['password', 'token', 'api_key', 'secret']
        return {
            k: '***' if k in sensitive_keys else v
            for k, v in context.items()
        }

# 桌面客户端中启用诊断模式
# 设置 → 高级 → 开启诊断模式 → 生成诊断报告 ID
```

**Docker 日志查看**：

```bash
# 实时查看日志
docker-compose logs -f api

# 查看最近 100 行
docker-compose logs --tail=100 api

# 按时间范围导出
docker-compose logs --since="2026-07-05T10:00:00" api > logs/api-20260705.log

# 按关键词过滤
docker-compose logs api | grep "ERROR"
```

### 6.3 性能监控（可选）

集成 Prometheus + Grafana：

```yaml
# docker-compose.yml 添加
  prometheus:
    image: prom/prometheus
    volumes:
      - ./docker/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana
    volumes:
      - grafana_data:/var/lib/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

## 7. 扩展路径

### 7.1 水平扩展（多实例）

MVP 阶段按单实例部署。方案二的 `template_filling` 暂定使用 JSON 文件保存模板和槽位配置，多实例直接写同一份 Volume 会引入并发写、文件锁和一致性问题。

满足以下条件后再开启多实例：

1. 模板/槽位配置迁移到数据库，或引入可靠的文件锁与单写队列。
2. 母版 ZIP 与生成草稿 ZIP 迁移到对象存储，或使用支持多写一致性的共享存储。
3. 下载接口使用签名 URL 或集中式 token 校验，避免实例本地状态。
4. 后台临时目录只保存可丢弃缓存，不依赖实例亲和性。

完成上述改造后，再在 Nginx upstream 或 K8s Service 层做负载均衡。

### 7.2 迁移到 Kubernetes

将 `docker-compose.yml` 转换为 K8s YAML：

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vectcut-api
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vectcut-api
  template:
    metadata:
      labels:
        app: vectcut-api
    spec:
      containers:
      - name: api
        image: your-registry/vectcut-api:latest
        ports:
        - containerPort: 9001
        volumeMounts:
        - name: config
          mountPath: /app/config.json
          subPath: config.json
        - name: template-data
          mountPath: /app/data/templates
        - name: template-config-data
          mountPath: /app/data/template_configs
        - name: generated-data
          mountPath: /app/data/generated
      volumes:
      - name: config
        configMap:
          name: vectcut-config
      - name: template-data
        persistentVolumeClaim:
          claimName: template-data-pvc
      - name: template-config-data
        persistentVolumeClaim:
          claimName: template-config-data-pvc
      - name: generated-data
        persistentVolumeClaim:
          claimName: generated-data-pvc
```

### 7.3 对象存储集成

当母版 ZIP 或生成草稿 ZIP 数量增大时，迁移到 OSS。方案二不上传用户音视频/图片素材，对象存储只保存母版、模板配置和生成草稿包：

1. 配置 `config.json` 的 `oss_config`
2. 将 `template_folder`、`generated_draft_folder` 迁移为 OSS 路径标识
3. `vectcut/features/template_filling/storage.py` 中增加 OSS 存取逻辑

## 8. 成本估算

### 8.1 云服务器配置

| 场景 | 配置 | 月成本（¥） |
|------|------|-------------|
| **开发/测试** | 1 核 2G / 40G SSD | ~60 |
| **小规模生产** | 2 核 4G / 60G SSD | ~120 |
| **中规模生产** | 4 核 8G / 100G SSD | ~300 |

### 8.2 OSS 存储（可选）

| 项目 | 用量 | 月成本（¥） |
|------|------|-------------|
| **存储空间** | 5GB | ~0.6 |
| **下行流量** | 10GB | ~9 |
| **请求次数** | 10万次 | ~0.4 |

### 8.3 域名 + SSL

| 项目 | 成本 |
|------|------|
| **.com 域名** | ~60/年 |
| **Let's Encrypt SSL** | 免费 |

## 9. 安全加固

### 9.1 网络安全

```yaml
# docker-compose.yml
services:
  api:
    networks:
      vectcut_net:
        ipv4_address: 172.20.0.10
    # 不暴露端口到宿主机，仅通过 Nginx 访问

networks:
  vectcut_net:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

### 9.2 访问控制（生产必需）

生产环境必须启用访问控制。MVP 可在 Nginx 增加基础认证；正式对外建议在 FastAPI 层使用 API token/JWT，并对 `/api/template/download/:draft_id` 做下载鉴权或签名 URL。

```nginx
location /api/ {
    auth_basic "VectCut API";
    auth_basic_user_file /etc/nginx/.htpasswd;
    proxy_pass http://vectcut_api;
}
```

生成密码文件：

```bash
htpasswd -c docker/ssl/.htpasswd admin
```

### 9.3 限流保护

```nginx
# nginx.conf 添加
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

location /api/ {
    limit_req zone=api_limit burst=20 nodelay;
    # ... 其他配置
}
```

`/api/template/import` 可单独设置更低频率和 `client_max_body_size 50M`；`/api/template/render` 与下载接口按账号/IP 做分钟级限流。

## 10. 常见问题

### 10.1 容器无法启动

```bash
# 查看详细日志
docker-compose logs api

# 进入容器调试
docker-compose exec api bash
python -c "from vectcut.core.config import load_config; print(load_config())"
```

### 10.2 模板或生成草稿丢失

确保 Volume 正确挂载：

```bash
docker volume inspect vectcutapi_template_data
docker volume inspect vectcutapi_template_config_data
docker volume inspect vectcutapi_generated_data
```

### 10.3 性能优化

- 增加 Uvicorn worker 数量：
  ```python
  # run_http.py
  uvicorn.run(
      "vectcut.server.http.app:app",
      host="0.0.0.0",
      port=cfg.port,
      workers=4    # 根据 CPU 核心数调整
  )
  ```

### 10.4 错误信息用户化

**问题**：API 返回的错误信息是开发者视角（例如 `"slot video_main segment 0 not found"`），桌面客户端需要翻译成用户能理解的提示。

**解决方案**：标准化错误码 + 客户端映射表

#### 10.4.1 后端错误码标准化

```python
# vectcut/core/errors.py
class VectCutError(Exception):
    """基础错误类"""
    def __init__(self, code: str, message: str, details: dict = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)

class TemplateError(VectCutError):
    """模板相关错误"""
    pass

class SlotError(VectCutError):
    """槽位相关错误"""
    pass

class RenderError(VectCutError):
    """生成相关错误"""
    pass

# 预定义错误码
ERROR_CODES = {
    # 模板错误 (T_xxx)
    "T_NOT_FOUND": "模板不存在",
    "T_INVALID_ZIP": "ZIP 文件格式无效",
    "T_TOO_LARGE": "模板文件过大",
    "T_NO_DRAFT_CONTENT": "ZIP 中缺少 draft_content.json",
    
    # 槽位错误 (S_xxx)
    "S_NOT_FOUND": "槽位配置不存在",
    "S_TRACK_NOT_FOUND": "母版中找不到指定轨道",
    "S_SEGMENT_NOT_FOUND": "母版中找不到指定片段",
    "S_TYPE_MISMATCH": "槽位类型与轨道类型不匹配",
    
    # 生成错误 (R_xxx)
    "R_MISSING_SLOT": "必填槽位未提供",
    "R_INVALID_PATH": "素材路径格式无效",
    "R_INVALID_DURATION": "素材时长异常",
    "R_LOOP_TOO_MANY": "视频时长不足，需循环次数过多",
    "R_SRT_PARSE_ERROR": "SRT 文件格式错误",
    "R_GENERATE_FAILED": "草稿生成失败",
}

# 使用示例
def validate_slot_config(template_id, slots):
    template = load_template(template_id)
    if not template:
        raise TemplateError("T_NOT_FOUND", f"模板 {template_id} 不存在")
    
    for slot in slots:
        track = template.get_track(slot.track)
        if not track:
            raise SlotError(
                "S_TRACK_NOT_FOUND",
                f"母版中找不到轨道 {slot.track}",
                details={"slot_id": slot.slot_id, "track": slot.track}
            )
```

#### 10.4.2 统一错误响应格式

```python
# vectcut/server/http/app.py
from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(VectCutError)
async def vectcut_error_handler(request: Request, exc: VectCutError):
    return JSONResponse(
        status_code=400,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            }
        }
    )

@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    logger.exception("未处理的异常", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "服务器内部错误，请联系管理员",
                "details": {}
            }
        }
    )
```

#### 10.4.3 桌面客户端错误映射表

```typescript
// desktop/src/utils/errorMessages.ts
export const ERROR_MESSAGES: Record<string, string> = {
  // 模板错误
  'T_NOT_FOUND': '模板不存在，请重新导入母版',
  'T_INVALID_ZIP': '母版 ZIP 文件格式无效，请检查是否为完整的剪映草稿文件夹',
  'T_TOO_LARGE': '母版文件过大（超过 50MB），请精简母版内容',
  'T_NO_DRAFT_CONTENT': 'ZIP 中缺少 draft_content.json 文件，请确认是否为剪映草稿',
  
  // 槽位错误
  'S_NOT_FOUND': '槽位配置不存在，请重新配置',
  'S_TRACK_NOT_FOUND': '母版中找不到指定轨道，母版可能已被修改，请重新导入',
  'S_SEGMENT_NOT_FOUND': '母版中找不到指定片段，母版可能已被修改，请重新导入',
  'S_TYPE_MISMATCH': '槽位类型与轨道类型不匹配，请检查配置',
  
  // 生成错误
  'R_MISSING_SLOT': '有必填槽位未填写，请检查素材是否完整',
  'R_INVALID_PATH': '素材路径格式无效，请选择有效的本地文件',
  'R_INVALID_DURATION': '素材时长异常（可能为 0 或过大），请检查文件是否损坏',
  'R_LOOP_TOO_MANY': '视频时长远小于配音时长，请增加更多视频片段',
  'R_SRT_PARSE_ERROR': 'SRT 字幕文件格式错误，请检查时间轴格式',
  'R_GENERATE_FAILED': '草稿生成失败，请查看详细错误信息',
  
  // 通用错误
  'INTERNAL_ERROR': '服务器内部错误，请稍后重试或联系技术支持',
  'NETWORK_ERROR': '网络连接失败，请检查网络或服务器地址',
};

export function getUserFriendlyError(error: ApiError): string {
  const baseMessage = ERROR_MESSAGES[error.code] || error.message;
  
  // 如果有详细信息，追加提示
  if (error.details && Object.keys(error.details).length > 0) {
    const detailsText = formatErrorDetails(error.details);
    return `${baseMessage}\n\n详细信息：${detailsText}`;
  }
  
  return baseMessage;
}

function formatErrorDetails(details: Record<string, any>): string {
  return Object.entries(details)
    .map(([key, value]) => `${key}: ${value}`)
    .join('\n');
}

// 使用示例
try {
  await api.renderDraft(request);
} catch (error) {
  const friendlyMessage = getUserFriendlyError(error);
  showErrorDialog(friendlyMessage);
}
```

#### 10.4.4 错误提示 UI 示例

```tsx
// desktop/src/components/ErrorDialog.tsx
function ErrorDialog({ error, onClose }: Props) {
  const friendlyMessage = getUserFriendlyError(error);
  
  return (
    <Dialog open onClose={onClose}>
      <DialogTitle>
        ⚠️ {error.code === 'R_LOOP_TOO_MANY' ? '视频不足' : '操作失败'}
      </DialogTitle>
      <DialogContent>
        <Typography>{friendlyMessage}</Typography>
        
        {/* 针对特定错误提供操作建议 */}
        {error.code === 'R_LOOP_TOO_MANY' && (
          <Alert severity="info" sx={{ mt: 2 }}>
            <strong>建议：</strong>
            <ul>
              <li>增加更多视频片段</li>
              <li>缩短配音时长</li>
              <li>使用更长的视频素材</li>
            </ul>
          </Alert>
        )}
        
        {/* 诊断模式提示 */}
        <Accordion sx={{ mt: 2 }}>
          <AccordionSummary>技术详情（用于反馈 Bug）</AccordionSummary>
          <AccordionDetails>
            <pre style={{ fontSize: '12px', overflow: 'auto' }}>
              {JSON.stringify(error, null, 2)}
            </pre>
          </AccordionDetails>
        </Accordion>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>关闭</Button>
        <Button onClick={() => copyToClipboard(error)}>复制错误信息</Button>
      </DialogActions>
    </Dialog>
  );
}
```

## 11. 总结

### 方案特点

✅ **容器化**：Docker + Docker Compose 一键部署
✅ **可演进**：MVP 单实例稳定部署，后续接数据库/OSS 后水平扩展
✅ **安全**：Nginx 反向代理 + SSL + 鉴权 + 限流保护
✅ **持久化**：Docker Volume 数据不丢失
✅ **监控**：健康检查 + 日志管理

### 适用场景

- 云端部署 VectCutAPI 的 `template_filling` API
- 为 Electron 桌面客户端提供稳定 API
- 方案二 Electron 桌面客户端的云端 API 基座

### 下一步

完成 Docker 部署后，继续开发方案二的 `template_filling` 后端 feature 和 Electron 桌面客户端。

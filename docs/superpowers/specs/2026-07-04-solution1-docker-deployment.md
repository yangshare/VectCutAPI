# 方案一：VectCutAPI Docker 云端部署方案

- 日期：2026-07-04
- 状态：待评审
- 范围：现有 VectCutAPI 接口服务的 Docker 容器化部署

## 1. 方案目标

将现有的 VectCutAPI（FastAPI 接口服务）容器化，实现云端部署，为后续客户端接入提供稳定的 API 服务基础。

**核心原则**：
- 核心剪辑能力在服务端
- 接口服务可独立部署、扩展
- 支持 HTTP API + MCP 协议双入口

## 2. 当前状态分析

### 2.1 现有架构

```
VectCutAPI（本地运行）
├── run_http.py        # FastAPI 入口，端口 9001
├── run_mcp.py         # MCP 协议入口
├── vectcut/
│   ├── core/          # 配置、错误处理
│   ├── features/      # 业务功能（draft/video/audio/text/image/effect/metadata）
│   ├── engine/        # pyJianYingDraft 引擎适配层
│   └── server/
│       ├── http/      # FastAPI app
│       └── mcp/       # MCP runtime
├── config.json        # 配置文件
└── requirements.txt   # Python 依赖
```

### 2.2 已有能力

| 模块 | 功能 | 状态 |
|------|------|------|
| **草稿管理** | 创建、保存、查询草稿 | ✅ |
| **视频处理** | add_video、关键帧、转场 | ✅ |
| **音频编辑** | add_audio、音量控制 | ✅ |
| **图像处理** | add_image、动画、滤镜 | ✅ |
| **文本编辑** | add_text、样式、动画 | ✅ |
| **字幕系统** | add_subtitle（SRT 导入） | ✅ |
| **特效贴纸** | add_effect、add_sticker | ✅ |
| **元数据查询** | get_video_duration | ✅ |

### 2.3 部署需求

- Python 3.10+ 运行环境
- pyJianYingDraft 依赖
- FFmpeg（视频元数据提取）
- 文件存储（生成的草稿文件）
- 可选：OSS 配置（oss_config、mp4_oss_config）

## 3. Docker 部署架构

### 3.1 架构图

```
┌────────────────────────────────────────────────────────┐
│ 外部访问（客户端 / AI Agent / MCP 客户端）               │
└───────────────────────┬────────────────────────────────┘
                        │ HTTPS
┌───────────────────────▼────────────────────────────────┐
│ Nginx 容器（反向代理 + SSL）                            │
│   · HTTP  → :80   → FastAPI :9001                      │
│   · HTTPS → :443  → FastAPI :9001                      │
│   · 静态资源服务（可选，如 API 文档）                    │
└───────────────────────┬────────────────────────────────┘
                        │
┌───────────────────────▼────────────────────────────────┐
│ VectCutAPI 容器（FastAPI + pyJianYingDraft）           │
│ ┌────────────────────────────────────────────────────┐ │
│ │ FastAPI (run_http.py)                              │ │
│ │   · 端口：9001                                      │ │
│ │   · 路由：/create_draft、/add_video、/save_draft 等 │ │
│ │   · 响应格式：{success, output, error}              │ │
│ └────────────────────────────────────────────────────┘ │
│ ┌────────────────────────────────────────────────────┐ │
│ │ pyJianYingDraft 引擎                                │ │
│ │   · Draft_folder（草稿操作）                        │ │
│ │   · ImportedMediaTrack（素材处理）                  │ │
│ │   · Script_file（draft_content.json 生成）          │ │
│ └────────────────────────────────────────────────────┘ │
│ ┌────────────────────────────────────────────────────┐ │
│ │ FFmpeg（视频元数据提取）                            │ │
│ └────────────────────────────────────────────────────┘ │
└───────────────────────┬────────────────────────────────┘
                        │
┌───────────────────────▼────────────────────────────────┐
│ Docker Volume（持久化存储）                             │
│   · /app/data/drafts/     生成的草稿文件（dfd_*）       │
│   · /app/data/temp/       临时素材（如需缓存）           │
│   · /app/config.json      配置文件挂载                  │
└────────────────────────────────────────────────────────┘
```

### 3.2 容器设计

#### 3.2.1 VectCutAPI 容器（Dockerfile.api）

```dockerfile
FROM python:3.10-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    ffmpeg \
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
RUN mkdir -p /app/data/drafts /app/data/temp

# 暴露端口
EXPOSE 9001

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:9001/health || exit 1

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

    # 客户端最大上传大小（如需上传素材）
    client_max_body_size 500M;

    # API 代理
    location /api/ {
        proxy_pass http://vectcut_api/;
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
        proxy_pass http://vectcut_api/health;
    }

    # 草稿下载（如需通过 Nginx 提供静态文件服务）
    location /drafts/ {
        alias /app/data/drafts/;
        autoindex off;
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
      - draft_data:/app/data/drafts                # 草稿持久化
      - temp_data:/app/data/temp                   # 临时文件
    environment:
      - TZ=Asia/Shanghai                           # 时区
      - PYTHONUNBUFFERED=1                         # Python 输出不缓冲
    networks:
      - vectcut_net
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9001/health"]
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
      - draft_data:/app/data/drafts:ro             # 草稿文件（只读）
    depends_on:
      api:
        condition: service_healthy
    networks:
      - vectcut_net

networks:
  vectcut_net:
    driver: bridge

volumes:
  draft_data:      # 草稿文件持久化
  temp_data:       # 临时文件（可定期清理）
```

## 4. 配置管理

### 4.1 配置文件（config.json）

```json
{
  "draft_profile": "jianying_pro_10",
  "is_capcut_env": false,
  "draft_domain": "https://api.vectcut.com",
  "port": 9001,
  "preview_router": "/draft/downloader",
  "is_upload_draft": true,
  "draft_folder": "/app/data/drafts",
  "oss_config": {
    "bucket_name": "${OSS_BUCKET}",
    "access_key_id": "${OSS_ACCESS_KEY}",
    "access_key_secret": "${OSS_ACCESS_SECRET}",
    "endpoint": "${OSS_ENDPOINT}"
  },
  "mp4_oss_config": {
    "bucket_name": "${MP4_BUCKET}",
    "access_key_id": "${MP4_ACCESS_KEY}",
    "access_key_secret": "${MP4_ACCESS_SECRET}",
    "region": "${MP4_REGION}",
    "endpoint": "${MP4_ENDPOINT}"
  }
}
```

### 4.2 环境变量（.env）

```bash
# OSS 配置（可选）
OSS_BUCKET=your-bucket
OSS_ACCESS_KEY=your-key
OSS_ACCESS_SECRET=your-secret
OSS_ENDPOINT=https://oss-cn-hangzhou.aliyuncs.com

# MP4 OSS 配置（可选）
MP4_BUCKET=your-mp4-bucket
MP4_ACCESS_KEY=your-key
MP4_ACCESS_SECRET=your-secret
MP4_REGION=cn-hangzhou
MP4_ENDPOINT=http://your-custom-domain

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
# 备份草稿数据
docker run --rm \
  -v vectcutapi_draft_data:/data \
  -v $(pwd)/backup:/backup \
  alpine tar czf /backup/drafts-$(date +%Y%m%d-%H%M%S).tar.gz -C /data .

# 恢复数据
docker run --rm \
  -v vectcutapi_draft_data:/data \
  -v $(pwd)/backup:/backup \
  alpine tar xzf /backup/drafts-20260704-120000.tar.gz -C /data
```

## 6. 监控与运维

### 6.1 健康检查

在 `vectcut/server/http/app.py` 中添加健康检查端点：

```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }
```

### 6.2 日志管理

```bash
# 实时查看日志
docker-compose logs -f api

# 查看最近 100 行
docker-compose logs --tail=100 api

# 导出日志
docker-compose logs api > logs/api-$(date +%Y%m%d).log
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

```yaml
# docker-compose.yml
services:
  api:
    # ... 现有配置
    deploy:
      replicas: 3    # 启动 3 个实例

  nginx:
    # 添加负载均衡配置
    volumes:
      - ./docker/nginx-lb.conf:/etc/nginx/nginx.conf:ro
```

`nginx-lb.conf` 负载均衡配置：

```nginx
upstream vectcut_api {
    least_conn;    # 最少连接负载均衡
    server api_1:9001;
    server api_2:9001;
    server api_3:9001;
}
```

### 7.2 迁移到 Kubernetes

将 `docker-compose.yml` 转换为 K8s YAML：

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vectcut-api
spec:
  replicas: 3
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
        - name: draft-data
          mountPath: /app/data/drafts
      volumes:
      - name: config
        configMap:
          name: vectcut-config
      - name: draft-data
        persistentVolumeClaim:
          claimName: draft-data-pvc
```

### 7.3 对象存储集成

当草稿文件量大时，迁移到 OSS：

1. 配置 `config.json` 的 `oss_config`
2. 修改 `draft_folder` 为 OSS 路径标识
3. `vectcut/features/draft/service.py` 中增加 OSS 上传逻辑

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
| **存储空间** | 100GB | ~12 |
| **下行流量** | 50GB | ~45 |
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

### 9.2 访问控制（可选）

在 Nginx 中添加基础认证：

```nginx
location /api/ {
    auth_basic "VectCut API";
    auth_basic_user_file /etc/nginx/.htpasswd;
    proxy_pass http://vectcut_api/;
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

## 10. 常见问题

### 10.1 容器无法启动

```bash
# 查看详细日志
docker-compose logs api

# 进入容器调试
docker-compose exec api bash
python -c "from vectcut.core.config import load_config; print(load_config())"
```

### 10.2 草稿文件丢失

确保 Volume 正确挂载：

```bash
docker volume inspect vectcutapi_draft_data
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

## 11. 总结

### 方案特点

✅ **容器化**：Docker + Docker Compose 一键部署  
✅ **可扩展**：支持水平扩展、K8s 迁移  
✅ **安全**：Nginx 反向代理 + SSL + 限流保护  
✅ **持久化**：Docker Volume 数据不丢失  
✅ **监控**：健康检查 + 日志管理  

### 适用场景

- 云端部署 VectCutAPI 接口服务
- 为客户端/AI Agent 提供稳定 API
- 单机到集群的平滑扩展路径

### 下一步

完成 Docker 部署后，可基于此服务开发：
- Web 客户端（方案二）
- 桌面客户端（Electron）
- 移动客户端（React Native）
- AI Agent 集成（MCP 协议）

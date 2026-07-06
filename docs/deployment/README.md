# VectCutAPI 部署指南

本文覆盖本地开发、Docker 开发、生产部署、更新、备份和常见故障排查。

## 一、本地开发部署

适合本机调试 API 和模板套版功能。

```bash
git clone <repo-url>
cd VectCutAPI

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp config.json.example config.json
# 按需编辑 config.json

python run_http.py
```

验证：

```bash
curl http://localhost:9001/health
```

预期返回 `{"status":"healthy", ...}`。

## 二、Docker 开发部署

开发模式使用 `docker-compose.override.yml`，默认只启动 `api`，并把 API 绑定到本机 `127.0.0.1:9001`。

```bash
cp config.json.example config.json
cp .env.example .env
# 按需编辑 config.json 和 .env

docker compose up -d --build
curl http://localhost:9001/health
```

停止开发环境：

```bash
docker compose down
```

## 三、生产部署

生产环境应显式指定 base compose 文件，避免自动加载开发覆盖文件：

```bash
docker compose -f docker-compose.yml --profile production up -d --build
```

不要把 `docker compose --profile production up -d` 作为生产命令使用，因为默认 Compose 会自动合并 `docker-compose.override.yml`。

### 1. 准备服务器

- 已安装 Docker 和 Docker Compose v2。
- 域名解析到服务器。
- 已准备 SSL 证书。
- 已复制并编辑 `config.json` 和 `.env`。

```bash
git clone <repo-url>
cd VectCutAPI

cp config.json.example config.json
cp .env.example .env

mkdir -p docker/ssl
# 放入生产证书：
# docker/ssl/fullchain.pem
# docker/ssl/privkey.pem
```

### 2. 准备 Basic Auth

生产 Nginx 的 `/api/` 默认启用 Basic Auth。启动生产栈前必须生成
`docker/ssl/.htpasswd`：

```bash
# Ubuntu/Debian: apt-get install -y apache2-utils
htpasswd -c docker/ssl/.htpasswd admin
```

`.htpasswd`、证书和私钥已被 `docker/.gitignore` 忽略，不要提交到仓库。

### 3. 启动完整栈

```bash
docker compose -f docker-compose.yml --profile production up -d --build
docker compose -f docker-compose.yml --profile production ps

curl -k https://localhost/health
curl -I http://localhost/health
```

`/health` 保持未认证，供 Docker 和反代健康检查使用。访问其它 `/api/`
接口需要带 Basic Auth：

```bash
curl -k -u admin:<password> https://localhost/api/template/...
```

预期：

- HTTPS 健康检查返回 `healthy`。
- HTTP 返回 301 跳转到 HTTPS。

### 4. 使用部署脚本

`scripts/deploy.sh` 默认执行生产部署，并显式排除开发 override：

```bash
./scripts/deploy.sh
./scripts/deploy.sh --build
./scripts/deploy.sh --down
```

开发模式：

```bash
./scripts/deploy.sh --dev
./scripts/deploy.sh --dev --down
```

脚本会在生产启动前检查 `docker/ssl/.htpasswd` 是否存在，然后执行
`git pull --ff-only`。生产健康检查优先访问 `https://localhost/health`。

## 四、数据持久化与备份

Compose 使用固定 volume 名称：

- `vectcutapi_template_data`
- `vectcutapi_template_config_data`
- `vectcutapi_generated_data`
- `vectcutapi_temp_data`
- `vectcutapi_logs_data`

备份关键业务数据：

```bash
./scripts/backup.sh ./backup
```

脚本会备份：

- `vectcutapi_template_data`
- `vectcutapi_template_config_data`
- `vectcutapi_generated_data`

备份脚本会先检查 volume 是否存在，避免误创建空卷并生成空备份。

## 五、运维命令速查

```bash
# 查看生产服务
docker compose -f docker-compose.yml --profile production ps

# 查看 API 日志
docker compose -f docker-compose.yml --profile production logs -f api

# 查看 Nginx 日志
docker compose -f docker-compose.yml --profile production logs -f nginx

# 重启 API
docker compose -f docker-compose.yml --profile production restart api

# 重启 Nginx
docker compose -f docker-compose.yml --profile production restart nginx

# 检查 volume
docker volume inspect vectcutapi_template_data
```

## 六、故障排查

### 容器无法启动

```bash
docker compose -f docker-compose.yml --profile production logs --tail=100 api
docker compose -f docker-compose.yml --profile production logs --tail=100 nginx
```

确认以下文件存在：

- `config.json`
- `docker/nginx.conf`
- `docker/ssl/fullchain.pem`
- `docker/ssl/privkey.pem`
- `docker/ssl/.htpasswd`

### Nginx 502

```bash
docker compose -f docker-compose.yml --profile production ps
docker compose -f docker-compose.yml --profile production logs --tail=100 api
```

确认 `api` 容器健康检查为 healthy。

### HTTPS 不可用

检查证书文件名和挂载路径：

```bash
ls -lh docker/ssl/
docker compose -f docker-compose.yml --profile production exec nginx nginx -t
```

### 数据看起来丢失

确认当前服务使用固定 volume：

```bash
docker volume ls | grep vectcutapi
docker volume inspect vectcutapi_template_data
docker volume inspect vectcutapi_template_config_data
docker volume inspect vectcutapi_generated_data
```

如果曾用不同目录名或 `COMPOSE_PROJECT_NAME` 启动过旧版本，请检查是否存在旧前缀 volume。

## 七、验收清单

- `GET /health` 返回 healthy。
- 错误响应包含标准错误码和统一信封。
- 日志不会输出原始素材路径、SRT 内容、token 或敏感字段。
- `config.json` 支持 `${VAR}` 环境变量注入。
- Dockerfile 可构建 API 镜像。
- Compose 可解析，并持久化关键数据卷。
- Nginx 支持 HTTPS、HTTP 跳转、限流和 `/api` 前缀保留转发。
- `/api/` 默认受 Basic Auth 保护，`/health` 保持未认证。
- 备份脚本可生成三个业务数据卷归档。

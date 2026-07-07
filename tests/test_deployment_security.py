"""部署安全配置静态回归测试。"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest

from vectcut.core.config import Settings


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_production_nginx_enables_basic_auth_for_api_only():
    config = _read("docker/nginx.conf")

    api_block_start = config.index("location /api/")
    health_block_start = config.index("location = /health")
    api_block = config[api_block_start:health_block_start]
    health_block = config[health_block_start:]

    assert 'auth_basic "VectCut API";' in api_block
    assert "auth_basic_user_file /etc/nginx/ssl/.htpasswd;" in api_block
    assert "# auth_basic" not in api_block
    assert "auth_basic" not in health_block
    assert "location = /health" in config
    assert "location /health" not in config
    assert "proxy_pass http://vectcut_api/health;" in health_block
    assert "proxy_pass http://vectcut_api/api/health;" not in health_block


def test_deploy_script_preflights_htpasswd_before_production_start():
    script = _read("scripts/deploy.sh")

    assert "docker/ssl/.htpasswd" in script
    assert "htpasswd -c docker/ssl/.htpasswd admin" in script
    assert "Basic Auth" in script
    assert "action" in script
    assert '[[ -s "$htpasswd_path" ]]' in script
    assert "exists and is not empty" in script


def test_production_health_checks_use_unauthenticated_health_path():
    script = _read("scripts/deploy.sh")
    docs = _read("docs/deployment/README.md")

    assert "https://localhost/health" in script
    assert "https://localhost/api/health" not in script
    assert "http://localhost:9001/health" in script
    assert "http://localhost:9001/api/health" not in script
    assert "https://localhost/health" in docs
    assert "https://localhost/api/health" not in docs
    assert "curl http://localhost:9001/health" in docs
    assert "curl http://localhost:9001/api/health" not in docs


def test_container_healthchecks_use_unauthenticated_health_path():
    compose = _read("docker-compose.yml")
    dockerfile = _read("docker/Dockerfile.api")

    assert "http://localhost:9001/health" in compose
    assert "http://localhost:9001/api/health" not in compose
    assert "http://localhost:9001/health" in dockerfile
    assert "http://localhost:9001/api/health" not in dockerfile


def test_nginx_upload_limit_covers_app_default_plus_multipart_overhead():
    config = _read("docker/nginx.conf")
    docs = _read("docs/deployment/README.md")
    match = re.search(r"client_max_body_size\s+(\d+)M;", config)
    assert match is not None

    nginx_limit_mb = int(match.group(1))
    required_mb = Settings().max_template_zip_mb + 1

    assert nginx_limit_mb >= required_mb
    assert "client_max_body_size 52M" in config
    assert "52M" in docs
    assert "50MiB + 1MiB multipart overhead" in docs


def test_development_compose_keeps_api_loopback_only():
    override = _read("docker-compose.override.yml")

    assert "host_ip: 127.0.0.1" in override
    assert "published: \"9001\"" in override
    assert "auth_basic" not in override


def test_deployment_docs_describe_basic_auth_as_required():
    docs = _read("docs/deployment/README.md")

    assert "默认启用 Basic Auth" in docs
    assert "docker/ssl/.htpasswd" in docs
    assert "htpasswd -c docker/ssl/.htpasswd admin" in docs
    assert "`/health` 保持未认证" in docs
    assert "可选 Basic Auth" not in docs
    assert "默认 Basic Auth 未启用" not in docs
    assert "取消 `docker/nginx.conf`" not in docs


def test_deploy_script_has_valid_bash_syntax():
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("bash is not available")

    subprocess.run(
        [bash, "-n", str(ROOT / "scripts/deploy.sh")],
        check=True,
        capture_output=True,
        text=True,
    )

"""HTTP 客户端公共工具（迁自 example.py 头部，阶段5 拆分）。"""
import json
import os
import requests
import sys
import time
import threading
from vectcut.core.config import load_config

# 确保能从项目根目录 import（examples/ 在项目根下，需向上一级）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 配置直读（不再经 settings 垫片，为任务8 settings 彻底瘦身清障）。
_cfg = load_config(None)
PORT = _cfg.port
DRAFT_FOLDER = _cfg.draft_folder

# Base URL of the service, please modify according to actual situation
BASE_URL = f"http://localhost:{PORT}"
LICENSE_KEY = "trial"  # Trial license key

# 草稿目录统一从 config.json 的 draft_folder 读取；为空则由服务端回退到运行目录
CAPCUT_DRAFT_FOLDER = DRAFT_FOLDER
JIANYINGPRO_DRAFT_FOLDER = DRAFT_FOLDER


def make_request(endpoint, data, method='POST'):
    """Send HTTP request to the server and handle the response"""
    url = f"{BASE_URL}/{endpoint}"
    headers = {'Content-Type': 'application/json'}

    try:
        if method == 'POST':
            response = requests.post(url, data=json.dumps(data), headers=headers)
        elif method == 'GET':
            response = requests.get(url, params=data, headers=headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        response.raise_for_status()  # Raise an exception if the request fails
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        sys.exit(1)
    except json.JSONDecodeError:
        print("Unable to parse server response")
        sys.exit(1)

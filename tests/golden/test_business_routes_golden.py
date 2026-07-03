"""业务路由 HTTP 黄金基线：错误分支 + 确定性成功分支。

迁移到 FastAPI 后，路由外壳与错误分支输出必须复现——本基线即防回归网。
draft_id 含时间戳/ uuid，normalize 时替换为占位符。
"""
import json
import re

import pytest
from fastapi.testclient import TestClient


# (路由, 请求体, 快照名)
CASES = [
    ("/create_draft", {}, "business_create_draft"),
    ("/generate_draft_url", {"draft_id": "PLACEHOLDER"}, "business_generate_draft_url"),
    ("/query_draft_status", {"task_id": "nonexistent_task"}, "business_query_draft_status_not_found"),
    ("/save_draft", {}, "business_save_draft_missing"),
    ("/add_video", {}, "business_add_video_missing_url"),
    ("/add_audio", {}, "business_add_audio_missing_url"),
    ("/add_video_keyframe", {}, "business_add_video_keyframe_missing"),
    ("/add_effect", {}, "business_add_effect_missing_type"),
    ("/add_sticker", {}, "business_add_sticker_missing_id"),
    ("/add_image", {}, "business_add_image_missing_url"),
    ("/add_text", {}, "business_add_text_missing"),
    ("/add_subtitle", {}, "business_add_subtitle_missing"),
]


@pytest.fixture(scope="module")
def client():
    from vectcut.server.http.app import app
    with TestClient(app) as c:
        yield c


def _normalize(payload):
    """draft_id / draft_url 中的动态 id 替换为占位，消除时间戳/uuid 漂移。"""
    s = json.dumps(payload, ensure_ascii=False)
    # draft_id 占位（含 draft_url 内部出现的 id）
    s = re.sub(r'dfd_cat_\d+_[0-9a-f]+', 'dfd_cat_PLACEHOLDER', s)
    # 引擎内部 uuid（materials / segments IDs 等）
    s = re.sub(r'\b[0-9a-f]{32}\b', 'PLACEHOLDER_UUID', s)
    return json.loads(s)


@pytest.mark.parametrize("route,body,snap", CASES, ids=[c[2] for c in CASES])
def test_business_route_matches_golden(client, route, body, snap, snapshot_dir, regenerate_golden):
    resp = client.post(route, json=body)
    assert resp.status_code == 200
    payload = resp.json()
    normalized = _normalize(payload)
    snap_path = snapshot_dir / f"{snap}.json"
    if regenerate_golden:
        snap_path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
        pytest.skip(f"golden regenerated: {snap_path.name}")
    assert snap_path.exists(), f"快照缺失：{snap_path}。运行 REGENERATE_GOLDEN=1 生成。"
    expected = json.loads(snap_path.read_text(encoding="utf-8"))
    assert normalized == expected, f"{route} 输出与黄金基线不一致（见 {snap_path.name}）"

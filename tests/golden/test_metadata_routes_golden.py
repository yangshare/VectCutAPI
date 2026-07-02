"""12 个 get_xxx_types 元数据路由的黄金基线。

迁移前捕获：阶段 1 元数据收敛为 /metadata/{kind} 后，每个 kind 必须复现同样输出，
旧别名路径也必须等价——本基线即防回归网。
"""
import json

import pytest

# 路由路径列表（与 capcut_server.py grep 实测一致）
METADATA_ROUTES = [
    "/get_intro_animation_types",
    "/get_outro_animation_types",
    "/get_combo_animation_types",
    "/get_transition_types",
    "/get_mask_types",
    "/get_audio_effect_types",
    "/get_font_types",
    "/get_text_intro_types",
    "/get_text_outro_types",
    "/get_text_loop_anim_types",
    "/get_video_scene_effect_types",
    "/get_video_character_effect_types",
]


@pytest.fixture(scope="module")
def client():
    """启动现有 Flask app 的测试客户端。本阶段 capcut_server 未动。"""
    # 延迟 import，避免收集期副作用
    import capcut_server

    capcut_server.app.config["TESTING"] = True
    with capcut_server.app.test_client() as c:
        yield c


@pytest.mark.parametrize("route", METADATA_ROUTES)
def test_metadata_route_matches_golden(client, route, snapshot_dir, regenerate_golden):
    resp = client.get(route)
    assert resp.status_code == 200
    payload = resp.get_json()

    # 规范化：output 列表按 JSON 序列化排序，消除枚举遍历顺序漂移，
    # 但**保留每个 item 的完整结构**（audio_effect 含 {name,type,params}，必须原样留存，
    # 供阶段 1 元数据收敛验证完全保真）。
    normalized = _normalize(payload)
    snap_path = snapshot_dir / f"metadata{route.replace('/', '_')}.json"

    if regenerate_golden:
        snap_path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
        pytest.skip(f"golden regenerated: {snap_path.name}")

    assert snap_path.exists(), (
        f"快照缺失：{snap_path}。运行 `REGENERATE_GOLDEN=1 python -m pytest "
        "tests/golden/test_metadata_routes_golden.py` 生成基线。"
    )
    expected = json.loads(snap_path.read_text(encoding="utf-8"))
    assert normalized == expected, f"{route} 输出与黄金基线不一致（见 {snap_path.name}）"


def _normalize(payload):
    """保留 output 完整结构，仅对列表排序以消除遍历顺序漂移。

    audio_effect 的 item 形如 {name, type, params:[{name,default_value,...}]}，
    必须原样保留——阶段 1 收敛须复现 params 的 ×100 缩放与 type 标签。
    """
    out = payload.get("output", [])
    if isinstance(out, list):
        out = sorted(out, key=lambda x: json.dumps(x, ensure_ascii=False, sort_keys=True))
    return {"success": payload.get("success"), "output": out, "error": payload.get("error", "")}

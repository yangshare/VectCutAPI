"""验证 capcut_server.py 旧路由函数已删、新 Blueprint 已挂载。"""
import importlib


def test_old_route_functions_removed():
    capcut_server = importlib.import_module("capcut_server")
    for name in [
        "add_video",
        "add_audio",
        "create_draft_service",
        "save_draft",
        "query_draft_status",
        "generate_draft_url",
        "query_script",
    ]:
        assert not hasattr(capcut_server, name), f"旧路由 {name} 应已删除"


def test_new_blueprints_registered():
    capcut_server = importlib.import_module("capcut_server")
    rules = {r.rule for r in capcut_server.app.url_map.iter_rules()}
    for path in [
        "/add_video",
        "/add_audio",
        "/create_draft",
        "/save_draft",
        "/query_script",
        "/query_draft_status",
        "/generate_draft_url",
    ]:
        assert path in rules, f"{path} 应由新 Blueprint 注册"


def test_legacy_stage3_routes_kept():
    """阶段3 待迁路由保留。"""
    capcut_server = importlib.import_module("capcut_server")
    rules = {r.rule for r in capcut_server.app.url_map.iter_rules()}
    for path in ["/add_text", "/add_image", "/add_effect", "/add_sticker", "/add_video_keyframe", "/add_subtitle"]:
        assert path in rules, f"{path} 阶段3 待迁，应保留"

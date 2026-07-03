import json
from pathlib import Path


def _write_config(tmp_path: Path, **overrides) -> Path:
    """生成一份最小合法 config.json（JSON5，带注释）。"""
    base = {
        "draft_profile": "jianying_legacy",
        "is_capcut_env": False,
        "draft_domain": "https://www.example.com",
        "port": 9001,
        "preview_router": "/draft/downloader",
        "is_upload_draft": False,
        "draft_folder": "",
        "oss_config": {
            "bucket_name": "b",
            "access_key_id": "k",
            "access_key_secret": "s",
            "endpoint": "https://e",
        },
        "mp4_oss_config": {
            "bucket_name": "mb",
            "access_key_id": "mk",
            "access_key_secret": "ms",
            "region": "cn-hangzhou",
            "endpoint": "http://m",
        },
    }
    base.update(overrides)
    path = tmp_path / "config.json"
    # 故意写入 JSON5 注释，验证加载器容忍注释
    text = json.dumps(base, ensure_ascii=False) + "\n// trailing comment line\n"
    path.write_text(text, encoding="utf-8")
    return path


def test_load_config_reads_all_fields_and_tolerates_json5_comments(tmp_path):
    from vectcut.core.config import load_config

    path = _write_config(tmp_path)
    cfg = load_config(path)

    assert cfg.draft_profile == "jianying_legacy"
    assert cfg.is_capcut_env is False
    assert cfg.draft_domain == "https://www.example.com"
    assert cfg.port == 9001
    assert cfg.preview_router == "/draft/downloader"
    assert cfg.is_upload_draft is False
    assert cfg.draft_folder == ""
    assert cfg.oss_config.bucket_name == "b"
    assert cfg.oss_config.endpoint == "https://e"
    assert cfg.mp4_oss_config.region == "cn-hangzhou"


def test_load_config_applies_defaults_when_fields_missing(tmp_path):
    from vectcut.core.config import load_config

    path = tmp_path / "config.json"
    # 只写 draft_profile，其余走默认
    path.write_text('{"draft_profile": "capcut_legacy"}', encoding="utf-8")
    cfg = load_config(path)

    assert cfg.draft_profile == "capcut_legacy"
    assert cfg.port == 9001           # 默认与 config.json 现值一致
    assert cfg.is_upload_draft is False
    assert cfg.draft_folder == ""


def test_load_config_falls_back_to_project_root_config_when_path_none(tmp_path, monkeypatch):
    from vectcut.core.config import load_config

    # 不传路径 → 读项目根 config.json（真实存在）
    cfg = load_config(None)
    assert cfg.draft_profile in {"capcut_legacy", "jianying_legacy", "jianying_pro_10"}
    assert isinstance(cfg.port, int)


def test_load_config_missing_file_uses_defaults_and_does_not_raise(tmp_path):
    from vectcut.core.config import load_config

    cfg = load_config(tmp_path / "nope.json")
    assert cfg.draft_profile == "capcut_legacy"  # 缺省默认
    assert cfg.is_capcut_env is True


# ─── 步骤 1：settings 垫片回归测试 ───────────────────────────────────────────


def test_settings_shim_reexports_legacy_constants_from_config():
    """settings 垫片彻底瘦身：仅保留引擎硬依赖的 IS_CAPCUT_ENV
    （pyJianYingDraft/video_segment.py:14、script_file.py:22）。

    阶段5 任务2/8 收官：原经 settings 垫片转发的 DRAFT_DOMAIN/PREVIEW_ROUTER
    （vectcut.core.util）、PORT/DRAFT_FOLDER（examples._client /
    scripts.gen_local_draft）、OSS_CONFIG/MP4_OSS_CONFIG（vectcut.core.oss）
    已全部改为各自直读 vectcut.core.config，本垫片不再转发这些常量。
    """
    import settings
    import settings.local as local
    from vectcut.core.config import load_config

    cfg = load_config(None)

    # 唯一保留的常量
    assert settings.IS_CAPCUT_ENV == cfg.is_capcut_env
    assert local.IS_CAPCUT_ENV == cfg.is_capcut_env

    # 彻底瘦身：以下历史常量均不再由垫片导出（消费方直读 config）
    for dropped in (
        "DRAFT_PROFILE",
        "DRAFT_DOMAIN",
        "PREVIEW_ROUTER",
        "DRAFT_FOLDER",
        "PORT",
        "IS_UPLOAD_DRAFT",
        "OSS_CONFIG",
        "MP4_OSS_CONFIG",
    ):
        assert dropped not in getattr(settings, "__all__", [])
        assert not hasattr(settings, dropped)
        assert not hasattr(local, dropped)


def test_settings_shim_drops_dead_code():
    """死代码已删：__all__ 不再声明 4 个无人定义的名字，get_platform_info 已移除。"""
    import settings

    for dead in ("API_KEYS", "MODEL_CONFIG", "PURCHASE_LINKS", "LICENSE_CONFIG"):
        assert dead not in getattr(settings, "__all__", [])
        assert not hasattr(settings, dead)
    assert not hasattr(settings, "get_platform_info")

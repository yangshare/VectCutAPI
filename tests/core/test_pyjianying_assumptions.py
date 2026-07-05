"""pyJianYingDraft API 核心假设验证测试。

这些测试验证方案二的技术基础是否成立：
1. Video_material 能否用 remote_url + 元数据绕过 ffprobe
2. Script_file.load_template() 返回对象结构
3. template_mode API 的基本使用方式
"""
import pytest
from pathlib import Path
import tempfile
import zipfile


def test_video_material_bypass_ffprobe():
    """验证用 remote_url + 元数据可绕过 ffprobe。

    关键假设：构造 Video_material 时传入 remote_url="placeholder"
    + duration/width/height，可跳过 ffprobe 检测，然后手动覆盖
    path 和 remote_url 字段。
    """
    from pyJianYingDraft.local_materials import Video_material

    # 构造时用占位 URL + 元数据
    mat = Video_material(
        material_type="video",
        remote_url="placeholder://metadata",
        material_name="test.mp4",
        duration=30.5,
        width=1080,
        height=1920,
    )

    # 验证：可手动覆盖 path 和 remote_url
    mat.path = "E:/素材/test.mp4"
    mat.remote_url = None

    assert mat.path == "E:/素材/test.mp4"
    assert mat.remote_url is None
    assert mat.duration == int(30.5 * 1_000_000)  # 转为微秒
    assert mat.width == 1080
    assert mat.height == 1920
    print("[PASS] Video_material can be constructed with metadata, bypassing ffprobe")


def test_audio_material_bypass_ffprobe():
    """验证 Audio_material 同样可绕过 ffprobe"""
    from pyJianYingDraft.local_materials import Audio_material

    mat = Audio_material(
        remote_url="placeholder://metadata",
        material_name="test.mp3",
        duration=60.0,
    )

    mat.path = "E:/素材/test.mp3"
    mat.remote_url = None

    assert mat.path == "E:/素材/test.mp3"
    assert mat.duration == int(60.0 * 1_000_000)
    print("[PASS] Audio_material can be constructed with metadata, bypassing ffprobe")


def test_script_file_load_template_structure():
    """验证 load_template 返回对象有 .tracks 属性和必要方法。

    需要准备一个真实的剪映草稿 ZIP 作为 fixture。
    """
    import pyJianYingDraft as draft

    fixture_zip = Path(__file__).parent.parent / "fixtures" / "sample_template.zip"

    if not fixture_zip.exists():
        pytest.skip("缺少 sample_template.zip fixture，需手动准备真实剪映草稿")

    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(fixture_zip, 'r') as z:
            z.extractall(tmpdir)

        draft_content = Path(tmpdir) / "draft_content.json"
        if not draft_content.exists():
            pytest.fail("sample_template.zip 中缺少 draft_content.json")

        # 加载母版
        script = draft.Script_file.load_template(str(draft_content))

        # 验证必要属性和方法
        assert hasattr(script, 'tracks'), "Script_file 缺少 .tracks 属性"
        assert hasattr(script, 'get_imported_track'), "Script_file 缺少 .get_imported_track() 方法"
        assert hasattr(script, 'dump'), "Script_file 缺少 .dump() 方法"

        # 验证 tracks 结构
        assert isinstance(script.tracks, list), ".tracks 应为列表"
        if len(script.tracks) > 0:
            track = script.tracks[0]
            assert hasattr(track, 'name'), "Track 缺少 .name 属性"
            assert hasattr(track, 'track_type'), "Track 缺少 .track_type 属性"
            assert hasattr(track, 'segments'), "Track 缺少 .segments 属性"

        print(f"[PASS] Script_file structure verified, template has {len(script.tracks)} tracks")


def test_template_mode_replace_material_basic():
    """验证 replace_material_by_seg 基本用法。

    这是方案二的核心 API，需确认其签名和行为。
    """
    import pyJianYingDraft as draft
    from pyJianYingDraft.local_materials import Video_material

    fixture_zip = Path(__file__).parent.parent / "fixtures" / "sample_template.zip"

    if not fixture_zip.exists():
        pytest.skip("缺少 sample_template.zip fixture")

    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(fixture_zip, 'r') as z:
            z.extractall(tmpdir)

        draft_content = Path(tmpdir) / "draft_content.json"
        script = draft.Script_file.load_template(str(draft_content))

        # 尝试获取视频轨道
        try:
            video_track = script.get_imported_track(draft.Track_type.video, name="video_main")
            print(f"[PASS] Got video track: {video_track.name}, has {len(video_track.segments)} segments")
        except Exception as e:
            pytest.skip(f"母版中无 video_main 轨道，跳过：{e}")

        # 验证 replace_material_by_seg 方法存在
        assert hasattr(script, 'replace_material_by_seg'), "Script_file 缺少 replace_material_by_seg 方法"

        # 构造测试素材（用元数据构造）
        test_material = Video_material(
            material_type="video",
            remote_url="placeholder://test",
            material_name="test.mp4",
            duration=10.0,
            width=1080,
            height=1920,
        )
        test_material.path = "E:/test.mp4"
        test_material.remote_url = None

        # 替换第 0 个片段（不实际写入，仅验证 API 可调用）
        try:
            # 注意：这里可能会报错，因为我们没有真实文件
            # 但我们只是验证 API 签名是否正确
            script.replace_material_by_seg(video_track, 0, test_material)
            print("[PASS] replace_material_by_seg API signature is correct")
        except FileNotFoundError:
            # 预期错误：素材文件不存在
            print("[PASS] replace_material_by_seg API signature is correct (FileNotFoundError is expected)")
        except TypeError as e:
            pytest.fail(f"replace_material_by_seg API 签名错误：{e}")

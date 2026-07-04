# -*- coding: utf-8 -*-
"""
本地素材处理验证脚本：
直接调用 VectCutAPI 的模块函数（add_video_track / add_audio_track / save_draft_impl），
用本地素材生成一个约 10 分钟的剪映草稿，含视频、背景音乐、封面。
完整触发 save_draft 的本地文件复制分支与 ffprobe 元数据探测分支，验证项目对本地素材的处理。
"""
import os
import sys
import json
import glob
import shutil
import subprocess

# Windows 控制台 UTF-8 输出，避免中文乱码
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# 确保能 import 项目根目录模块（scripts/ 在项目根下，需向上两级）
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from vectcut.features.video.service import add_video as add_video_track  # 任务6 迁 scripts/ 时重写
from vectcut.features.audio.service import add_audio as add_audio_track  # 任务6 迁 scripts/ 时重写
from vectcut.features.text.service import add_text as add_text_impl  # 片头封面文字
from vectcut.features.draft.service import save_draft as save_draft_impl
from vectcut.features.video.schemas import AddVideoRequest
from vectcut.features.audio.schemas import AddAudioRequest
from vectcut.features.text.schemas import AddTextRequest
from vectcut.features.draft.schemas import SaveDraftRequest
from vectcut.core.config import load_config

_cfg = load_config(None)
DRAFT_FOLDER = _cfg.draft_folder

MATERIAL_ROOT = r"G:\剪映剪辑\小说素材\素材"
DRAFT_FOLDER = DRAFT_FOLDER or r"D:\Program Files (x86)\JianyingPro Drafts"
TARGET_DURATION = 600.0  # 10 分钟
CANVAS_W, CANVAS_H = 1080, 1920  # 竖屏

VIDEO_DIRS = [
    os.path.join(MATERIAL_ROOT, "开头"),
    os.path.join(MATERIAL_ROOT, "中间"),
    os.path.join(MATERIAL_ROOT, "夜景、车流、街景"),
    os.path.join(MATERIAL_ROOT, "城市伤感34个"),
]
MUSIC_DIR = os.path.join(MATERIAL_ROOT, "音乐")
COVER_DIR = os.path.join(MATERIAL_ROOT, "封面素材")


def probe_duration(path):
    """用 ffprobe 取媒体时长（秒），失败返回 None。"""
    try:
        out = subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", path],
            stderr=subprocess.STDOUT, timeout=60,
        ).decode("utf-8", "ignore").strip()
        return float(out) if out else None
    except Exception as e:
        print(f"[probe] {path} 失败: {e}")
        return None


def collect_videos():
    """收集各目录下的 .mp4 文件并探测时长。"""
    pool = []
    for d in VIDEO_DIRS:
        files = []
        for ext in ("*.mp4",):
            files += glob.glob(os.path.join(d, "**", ext), recursive=True)
        # 每个目录最多取 30 个，避免过多
        files = files[:30]
        for f in files:
            dur = probe_duration(f)
            if dur and dur >= 2.0:
                pool.append((f, dur))
    return pool


def main():
    print(f"草稿输出目录: {DRAFT_FOLDER}")
    print("== 收集本地视频并探测时长 ==")
    pool = collect_videos()
    print(f"可用视频片段数: {len(pool)}")

    # 贪心拼接视频到 ~600 秒
    print("\n== 添加视频轨 ==")
    draft_id = None
    cursor = 0.0
    seg_count = 0
    for path, dur in pool:
        if cursor >= TARGET_DURATION:
            break
        # 每段截取前 clip 秒；最后一段若会超出则收尾到 TARGET
        clip = min(12.0, dur)
        remain = TARGET_DURATION - cursor
        if clip > remain:
            clip = max(2.0, remain)  # 收尾
        # 保证不超出真实时长
        clip = min(clip, dur)
        end = clip
        res = add_video_track(AddVideoRequest(
            video_url=path,
            draft_folder=DRAFT_FOLDER,
            width=CANVAS_W,
            height=CANVAS_H,
            start=0,
            end=end,
            target_start=cursor,
            duration=clip,   # 传入真实时长，跳过探测，避免被裁剪
            track_name="main",
            volume=0.0,      # 视频静音，由背景音乐接管
            draft_id=draft_id,
        ))
        if not getattr(res, "draft_id", None):
            print(f"添加失败: {res}")
            continue
        draft_id = res.draft_id
        cursor += clip
        seg_count += 1
        print(f"  [{seg_count:02d}] +{clip:.2f}s -> {cursor:.2f}s  {os.path.basename(path)}")
    print(f"视频总时长: {cursor:.2f}s, 共 {seg_count} 段, draft_id={draft_id}")

    # 背景音乐：挑一首长 mp3，取 0~TARGET_DURATION
    print("\n== 添加背景音乐 ==")
    music_files = glob.glob(os.path.join(MUSIC_DIR, "**", "*.mp3"), recursive=True)
    music_files += glob.glob(os.path.join(MUSIC_DIR, "**", "*.MP3"), recursive=True)
    chosen = None
    for f in music_files:
        d = probe_duration(f)
        if d and d >= TARGET_DURATION:
            chosen = (f, d)
            break
    if chosen is None and music_files:
        # 没有单曲够长，取最长的
        best = None
        for f in music_files:
            d = probe_duration(f)
            if d and (best is None or d > best[1]):
                best = (f, d)
        chosen = best
    if chosen is None:
        print("未找到可用背景音乐！")
    else:
        f, d = chosen
        print(f"选用音乐: {os.path.basename(f)} (时长 {d:.1f}s)")
        res = add_audio_track(AddAudioRequest(
            audio_url=f,
            draft_folder=DRAFT_FOLDER,
            start=0,
            end=min(TARGET_DURATION, d),
            target_start=0,
            volume=0.6,
            track_name="bgm",
            duration=d,
            draft_id=draft_id,
        ))
        draft_id = res.draft_id
        print(f"背景音乐添加完成, draft_id={draft_id}")

    # 片头封面文字：用 add_text 在 0~5s 叠加「【测试草稿】」
    print("\n== 添加片头封面文字 ==")
    COVER_TEXT = "【测试草稿】"
    try:
        res = add_text_impl(AddTextRequest(
            text=COVER_TEXT,
            draft_id=draft_id,
            start=0,
            end=5,
            track_name="cover_text",
            font="LXGWWenKai_Bold",       # 霞鹜文楷，Font_type 内确定存在
            font_size=12.0,               # 大标题
            font_color="#FFFFFF",
            transform_y=0.0,              # 居中
            border_width=6.0,             # 描边，避免压在浅色画面上看不清
            border_color="#000000",
            shadow_enabled=True,
            shadow_color="#000000",
            shadow_distance=8.0,
        ))
        if getattr(res, "draft_id", None):
            draft_id = res.draft_id
            print(f"片头文字已添加: 「{COVER_TEXT}」 draft_id={draft_id}")
        else:
            print(f"片头文字添加失败: {res}")
    except Exception as e:
        print(f"片头文字添加异常: {e}")

    # 保存草稿（触发本地素材复制 + 元数据探测）
    print("\n== 保存草稿 ==")
    save_res = save_draft_impl(SaveDraftRequest(draft_id=draft_id, draft_folder=DRAFT_FOLDER))
    print(f"保存结果: success={save_res.success} draft_url={save_res.draft_url} error={save_res.error}")

    # 放置封面（路径 A：完整 composition 引用链）。
    # 关键经验（剪映 6.x 国内版，对照手设封面后的真实 draft_content 取证）：
    #   - 顶层 cover.cover_draft_id = "<GUID>_material"
    #   - materials.drafts[0] = composition 子草稿，id 末尾带 "_material"
    #     其 draft.id 不带后缀，draft.materials.videos[0].path 指向
    #       ##_draftpath_placeholder_<GUID>_##/Resources/cover/<图片GUID>.jpg
    #     draft.tracks[0].segments[0].material_id 指向该 videos[0].id
    #   - 封面图真实文件落在 Resources\cover\<图片GUID>.jpg
    #   - 根目录 draft_cover.jpg 是剪映自己生成的列表缩略预览，我们也放一份
    #   - 路径 B（仅放文件名 + cover=null）经实测无效：剪映 6.x 不认文件名回退对外部放置的图
    # 注入必须在 save_draft 之后：直接改磁盘 draft_info.json（pyJianYingDraft 的 Script.dumps
    # 不会写 cover / materials.drafts，会在 save 时被覆盖，所以注入点在 save_draft完之后）。
    print("\n== 放置封面 ==")
    draft_dir = os.path.join(DRAFT_FOLDER, draft_id)
    draft_info_path = os.path.join(draft_dir, "draft_info.json")
    cover_dst = os.path.join(draft_dir, "draft_cover.jpg")
    # 优先用指定的高分辨率竖屏封面；找不到则回退到 COVER_DIR 下第一张图
    PREFERRED_COVER = os.path.join(COVER_DIR, "生成二次元图片.png")  # 1536x2730 二次元竖屏
    if os.path.isfile(PREFERRED_COVER):
        cover_src = PREFERRED_COVER
    else:
        covers = []
        for ext in ("*.jpg", "*.jpeg", "*.png"):
            covers += glob.glob(os.path.join(COVER_DIR, "**", ext), recursive=True)
        cover_src = covers[0] if covers else None

    # 生成 composition 注入模板（从 scripts/cover_composition_template.json 读取）
    tpl_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cover_composition_template.json")
    cover_ready = False
    if cover_src and os.path.isfile(tpl_path):
        import uuid
        try:
            tpl = json.load(open(tpl_path, encoding="utf-8"))
            drafts_mat = tpl["drafts_material"]
            top_cover = tpl["top_cover"]

            # 为模板内所有 {{GUID_<i>}} 与 {{COVER_DRAFT_ID}} 统一重映射为新 GUID
            # 注意 f-string 里 {{ }} 会折叠成单 { }，所以这里用显式拼接，避免 key 与模板不匹配
            new_guids = {"{{GUID_%d}}" % i: str(uuid.uuid4()) for i in range(10)}
            cover_id = new_guids["{{GUID_0}}"]   # composition 子草稿 id

            def fill(o):
                if isinstance(o, str):
                    for k, v in new_guids.items():
                        o = o.replace(k, v)
                    o = o.replace("{{COVER_DRAFT_ID}}", cover_id)
                    return o
                if isinstance(o, dict):
                    return {k: fill(v) for k, v in o.items()}
                if isinstance(o, list):
                    return [fill(v) for v in o]
                return o

            drafts_mat = fill(drafts_mat)
            top_cover = fill(top_cover)

            # 探测源图实际尺寸，写进 videos[0].width/height；并把源图（白底合成后）
            # 复制到 Resources\cover\<图片GUID>.jpg（图片GUID = GUID_6 = new_guids[{{GUID_6}}]）
            from PIL import Image
            img = Image.open(cover_src).convert("RGBA")
            bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
            bg.alpha_composite(img)
            rgb = bg.convert("RGB")
            w, h = rgb.size
            cover_img_guid = new_guids["{{GUID_6}}"]
            cover_subdir = os.path.join(draft_dir, "Resources", "cover")
            os.makedirs(cover_subdir, exist_ok=True)
            cover_in_res = os.path.join(cover_subdir, cover_img_guid + ".jpg")
            rgb.save(cover_in_res, "JPEG", quality=92)
            # 根目录也放一份（剪映列表缩略预览）
            rgb.thumbnail((405, 720))
            rgb.save(cover_dst, "JPEG", quality=90)
            cover_ready = True
            print(f"封面图已落盘: {cover_in_res}（{w}x{h}）+ 根 draft_cover.jpg 预览")

            # 改写 videos[0].width/height 为源图实际尺寸
            v0 = drafts_mat["draft"]["materials"]["videos"][0]
            v0["width"] = w
            v0["height"] = h
            # path 已被 fill 自动替换为最终值

            # 注入 draft_info.json：顶层 cover + 追加 materials.drafts
            with open(draft_info_path, "r", encoding="utf-8") as f:
                info = json.load(f)
            info["cover"] = top_cover
            md = info.setdefault("materials", {}).setdefault("drafts", [])
            # 去重：若已有同 id 的 composition 条目则替换
            md = [m for m in md if m.get("id") != drafts_mat["id"]]
            md.append(drafts_mat)
            info["materials"]["drafts"] = md
            with open(draft_info_path, "w", encoding="utf-8") as f:
                json.dump(info, f, ensure_ascii=False, indent=4)
            print(f"已注入 cover + materials.drafts[composition] 到 draft_info.json（cover_draft_id={cover_id}_material）")
        except Exception as e:
            print(f"封面 composition 注入失败: {e}")
            import traceback; traceback.print_exc()
    elif not cover_src:
        print("未找到封面素材。")
    else:
        print(f"封面模板缺失: {tpl_path}")

    # 校验草稿目录结构
    print("\n== 草稿目录结构 ==")
    for root, dirs, files in os.walk(draft_dir):
        depth = root.replace(draft_dir, "").count(os.sep)
        if depth > 2:
            continue
        indent = "  " * depth
        print(f"{indent}{os.path.basename(root)}/  ({len(files)} files)")
        if depth == 2:
            for fn in files[:5]:
                print(f"{indent}  {fn}")

    print(f"\n✅ 草稿生成完成！draft_id = {draft_id}")
    print(f"   打开剪映，在草稿列表找到对应草稿即可预览。")


if __name__ == "__main__":
    main()

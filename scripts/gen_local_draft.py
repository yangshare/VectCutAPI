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
from vectcut.features.draft._save_engine import save_draft_background as save_draft_impl
from vectcut.features.video.schemas import AddVideoRequest
from vectcut.features.audio.schemas import AddAudioRequest
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
        if not res.get("draft_id"):
            print(f"添加失败: {res}")
            continue
        draft_id = res["draft_id"]
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
        draft_id = res["draft_id"]
        print(f"背景音乐添加完成, draft_id={draft_id}")

    # 保存草稿（触发本地素材复制 + 元数据探测）
    print("\n== 保存草稿 ==")
    save_res = save_draft_impl(draft_id, DRAFT_FOLDER)
    print(f"保存结果: {save_res}")

    # 放置封面：复制一张封面图到草稿目录下的 draft_cover.jpg
    print("\n== 放置封面 ==")
    draft_dir = os.path.join(DRAFT_FOLDER, draft_id)
    cover_dst = os.path.join(draft_dir, "draft_cover.jpg")
    covers = []
    for ext in ("*.jpg", "*.jpeg", "*.png"):
        covers += glob.glob(os.path.join(COVER_DIR, "**", ext), recursive=True)
    if covers:
        shutil.copyfile(covers[0], cover_dst)
        print(f"封面已复制: {covers[0]} -> {cover_dst}")
    else:
        print("未找到封面素材。")

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

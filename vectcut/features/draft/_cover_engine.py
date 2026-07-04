"""封面注入引擎：为草稿添加封面图与封面文字。

基于 gen_local_draft.py 中验证通过的 Path A（composition 引用链）方案。
核心逻辑：
1. 从 cover_composition_template.json 加载模板
2. 生成新 GUID 替换模板占位符（GUID_5 已是固定 placeholder）
3. 下载封面图，保存到 Resources/cover/<GUID>.jpg
4. 如果有封面文字，替换模板中的 text content
5. 注入 cover 和 materials.drafts 到 draft_info.json
"""

from __future__ import annotations

import json
import os
import uuid
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

from vectcut.core.config import load_config
from vectcut.core.downloader import download_file
from vectcut.core.util import url_to_hash


_COVER_MARKER = "vectcut_cover"


def _download_cover_source(cover_url: str, cover_subdir: str) -> str:
    if os.path.exists(cover_url) and os.path.isfile(cover_url):
        return cover_url

    local_path = os.path.join(cover_subdir, f"cover_source_{url_to_hash(cover_url)}.img")
    if not download_file(cover_url, local_path):
        raise IOError(f"Failed to download cover image: {cover_url}")
    return local_path


def _load_cover_font(size: int) -> ImageFont.ImageFont:
    font_paths = [
        os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "msyh.ttc"),
        os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "simhei.ttf"),
        os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "arial.ttf"),
    ]
    for font_path in font_paths:
        if os.path.isfile(font_path):
            return ImageFont.truetype(font_path, size=size)
    return ImageFont.load_default()


def _draw_cover_text(img: Image.Image, cover_text: str) -> Image.Image:
    if not cover_text:
        return img

    result = img.copy()
    draw = ImageDraw.Draw(result)
    font_size = max(24, min(result.size) // 10)
    font = _load_cover_font(font_size)

    max_width = int(result.width * 0.82)
    words = list(cover_text)
    lines = []
    current = ""
    for word in words:
        candidate = current + word
        bbox = draw.textbbox((0, 0), candidate, font=font, stroke_width=max(2, font_size // 16))
        if current and bbox[2] - bbox[0] > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)

    stroke_width = max(2, font_size // 14)
    line_boxes = [
        draw.textbbox((0, 0), line, font=font, stroke_width=stroke_width)
        for line in lines
    ]
    line_gap = max(6, font_size // 5)
    total_height = sum(box[3] - box[1] for box in line_boxes) + line_gap * max(0, len(lines) - 1)
    y = (result.height - total_height) / 2

    for line, bbox in zip(lines, line_boxes):
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        x = (result.width - width) / 2
        draw.text(
            (x, y),
            line,
            font=font,
            fill=(255, 255, 255),
            stroke_width=stroke_width,
            stroke_fill=(0, 0, 0),
        )
        y += height + line_gap

    return result


def add_cover_to_draft(
    draft_id: str,
    cover_url: str,
    cover_text: Optional[str] = None,
    draft_folder: Optional[str] = None,
) -> None:
    """为已存在的草稿添加封面。

    Args:
        draft_id: 草稿 ID
        cover_url: 封面图片 URL
        cover_text: 封面文字（可选）
        draft_folder: 草稿保存目录（None 则使用配置默认值）

    Raises:
        FileNotFoundError: 草稿不存在或模板文件不存在
        IOError: 图片下载/处理失败
    """
    cfg = load_config()
    folder = draft_folder if draft_folder is not None else cfg.draft_folder

    draft_dir = os.path.join(folder, draft_id)
    draft_info_path = os.path.join(draft_dir, "draft_info.json")

    if not os.path.isfile(draft_info_path):
        raise FileNotFoundError(f"Draft not found: {draft_info_path}")

    # 1. 加载封面模板
    template_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        "scripts",
        "cover_composition_template.json"
    )
    if not os.path.isfile(template_path):
        raise FileNotFoundError(f"Cover template not found: {template_path}")

    with open(template_path, encoding="utf-8") as f:
        tpl = json.load(f)

    drafts_mat = tpl["drafts_material"]
    top_cover = tpl["top_cover"]

    # 2. 生成新 GUID（跳过 GUID_5，它已是固定 placeholder）
    new_guids = {"{{GUID_%d}}" % i: str(uuid.uuid4()) for i in range(10) if i != 5}
    cover_id = new_guids["{{GUID_0}}"]

    # 3. 递归替换所有 {{GUID_N}} 和 {{COVER_DRAFT_ID}}
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

    # 4. 下载并处理封面图
    cover_img_guid = new_guids["{{GUID_6}}"]
    cover_subdir = os.path.join(draft_dir, "Resources", "cover")
    os.makedirs(cover_subdir, exist_ok=True)
    local_path = _download_cover_source(cover_url, cover_subdir)

    img = Image.open(local_path).convert("RGBA")
    bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
    bg.alpha_composite(img)
    rgb = _draw_cover_text(bg.convert("RGB"), cover_text or "")
    w, h = rgb.size

    # 5. 保存封面图到 Resources/cover/<GUID>.jpg
    cover_in_res = os.path.join(cover_subdir, cover_img_guid + ".jpg")
    rgb.save(cover_in_res, "JPEG", quality=92)

    # 根目录也放一份缩略图（剪映列表预览）
    cover_dst = os.path.join(draft_dir, "draft_cover.jpg")
    rgb_thumb = rgb.copy()
    rgb_thumb.thumbnail((405, 720))
    rgb_thumb.save(cover_dst, "JPEG", quality=90)

    print(f"封面图已保存: {cover_in_res} ({w}x{h}) + draft_cover.jpg")

    # 6. 更新 videos[0] 的宽高
    v0 = drafts_mat["draft"]["materials"]["videos"][0]
    v0["width"] = w
    v0["height"] = h

    # 7. 封面文字已烘焙到图片里；保留日志便于本地脚本观察
    if cover_text:
        print(f"封面文字已设置: {cover_text}")

    # 8. 读取并修改 draft_info.json
    with open(draft_info_path, encoding="utf-8") as f:
        draft_info = json.load(f)

    # 注入 cover 和 drafts
    old_cover_id = None
    if isinstance(draft_info.get("cover"), dict):
        old_cover_id = draft_info["cover"].get("cover_draft_id")

    drafts_mat["name"] = _COVER_MARKER
    draft_info["cover"] = top_cover

    materials = draft_info.setdefault("materials", {})
    existing_drafts = materials.setdefault("drafts", [])
    materials["drafts"] = [
        item for item in existing_drafts
        if item.get("id") not in {old_cover_id, drafts_mat["id"]}
        and item.get("name") != _COVER_MARKER
    ]
    materials["drafts"].append(drafts_mat)

    # 9. 写回 draft_info.json
    with open(draft_info_path, "w", encoding="utf-8") as f:
        json.dump(draft_info, f, ensure_ascii=False, indent=2)

    print(f"封面已注入到草稿: {draft_id}")

"""Text demo — 迁自 example.py（阶段5 拆分）。"""
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from _client import make_request, CAPCUT_DRAFT_FOLDER
from image_demo import add_image_impl


def add_text_impl(text, start, end, font, font_color, font_size, track_name, draft_folder="123", draft_id=None,
                  vertical=False, transform_x=0, transform_y=0, font_alpha=1.0,
                  border_color=None, border_width=0.0, border_alpha=1.0,
                  background_color=None, background_alpha=1.0, background_style=None,
                  background_round_radius=0.0, background_height=0.14, background_width=0.14,
                  background_horizontal_offset=0.5, background_vertical_offset=0.5,
                  shadow_enabled=False, shadow_alpha=0.9, shadow_angle=-45.0,
                  shadow_color="#000000", shadow_distance=5.0, shadow_smoothing=0.15,
                  bubble_effect_id=None, bubble_resource_id=None,
                  effect_effect_id=None,
                  intro_animation=None, intro_duration=0.5,
                  outro_animation=None, outro_duration=0.5,
                  width=1080, height=1920,
                  fixed_width=-1, fixed_height=-1,
                  text_styles=None):
    """Add text with support for multiple styles, shadows, and backgrounds"""
    data = {
        "draft_folder": draft_folder,
        "text": text,
        "start": start,
        "end": end,
        "font": font,
        "font_color": font_color,
        "font_size": font_size,
        "alpha": font_alpha,
        "track_name": track_name,
        "vertical": vertical,
        "transform_x": transform_x,
        "transform_y": transform_y
    }

    # Add border parameters
    if border_color:
        data["border_color"] = border_color
        data["border_width"] = border_width
        data["border_alpha"] = border_alpha

    # Add background parameters
    if background_color:
        data["background_color"] = background_color
        data["background_alpha"] = background_alpha
        if background_style:
            data["background_style"] = background_style
        data["background_round_radius"] = background_round_radius
        data["background_height"] = background_height
        data["background_width"] = background_width
        data["background_horizontal_offset"] = background_horizontal_offset
        data["background_vertical_offset"] = background_vertical_offset

    # Add shadow parameters
    if shadow_enabled:
        data["shadow_enabled"] = shadow_enabled
        data["shadow_alpha"] = shadow_alpha
        data["shadow_angle"] = shadow_angle
        data["shadow_color"] = shadow_color
        data["shadow_distance"] = shadow_distance
        data["shadow_smoothing"] = shadow_smoothing


    # Add bubble effect parameters
    if bubble_effect_id:
        data["bubble_effect_id"] = bubble_effect_id
        if bubble_resource_id:
            data["bubble_resource_id"] = bubble_resource_id

    # Add text effect parameters
    if effect_effect_id:
        data["effect_effect_id"] = effect_effect_id

    # Add intro animation parameters
    if intro_animation:
        data["intro_animation"] = intro_animation
        data["intro_duration"] = intro_duration

    # Add outro animation parameters
    if outro_animation:
        data["outro_animation"] = outro_animation
        data["outro_duration"] = outro_duration

    # Add size parameters
    data["width"] = width
    data["height"] = height

    # Add fixed size parameters
    if fixed_width > 0:
        data["fixed_width"] = fixed_width
    if fixed_height > 0:
        data["fixed_height"] = fixed_height

    if draft_id:
        data["draft_id"] = draft_id

    # Add text styles parameters
    if text_styles:
        data["text_styles"] = text_styles

    if draft_id:
        data["draft_id"] = draft_id

    return make_request("add_text", data)


def group_sentences(corrected_srt, threshold=1.0):
    """按时间间隔分句"""
    if not corrected_srt:
        return []
    sentences = []
    current_sentence = [corrected_srt[0]]
    for i in range(1, len(corrected_srt)):
        prev_end = corrected_srt[i-1]["end"]
        curr_start = corrected_srt[i]["start"]
        if curr_start - prev_end > threshold:
            sentences.append(current_sentence)
            current_sentence = [corrected_srt[i]]
        else:
            current_sentence.append(corrected_srt[i])
    sentences.append(current_sentence)
    return sentences


def adjust_sentence_timing(sentences, gap_adjust=1, time_precision=3):
    """调整句子间的时间间隔，并保留原始时间"""
    def round_time(t):
        return round(t, time_precision) if time_precision is not None else t

    adjusted_sentences = []
    total_offset = 0.0
    prev_end = sentences[0][-1]["end"]

    # 第一句保持原时间
    first_sentence = [
        {
            "word": w["word"],
            "start": w["start"],
            "end": w["end"],
            "original_start": w["start"],
            "original_end": w["end"]
        }
        for w in sentences[0]
    ]
    adjusted_sentences.append(first_sentence)

    for i in range(1, len(sentences)):
        sentence = sentences[i]
        curr_start = sentence[0]["start"]
        natural_gap = curr_start - prev_end
        adjusted_gap = natural_gap if gap_adjust == 0 else (1.0 if natural_gap > 1.0 else natural_gap)
        move_amount = natural_gap - adjusted_gap
        total_offset += move_amount

        adjusted_sentence = []
        for w in sentence:
            adjusted_sentence.append({
                "word": w["word"],
                "start": round_time(w["start"] - total_offset),
                "end": round_time(w["end"] - total_offset),
                "original_start": w["start"],
                "original_end": w["end"]
            })
        adjusted_sentences.append(adjusted_sentence)
        prev_end = sentence[-1]["end"]
    return adjusted_sentences


def split_into_paragraphs(sentence, max_words=5, max_chunk_duration=1.5):
    """把句子按词数和时长分段"""
    paragraphs = []
    i = 0
    n = len(sentence)
    while i < n:
        paragraph = [sentence[i]]
        current_start = sentence[i]["start"]
        current_end = sentence[i]["end"]
        i += 1
        while i < n:
            current_word = sentence[i]
            is_continuous = abs(current_word["start"] - current_end) < 0.001
            if (len(paragraph) >= max_words or
                (current_word["end"] - current_start) >= max_chunk_duration or
                not is_continuous):
                break
            paragraph.append(current_word)
            current_end = current_word["end"]
            i += 1
        paragraphs.append(paragraph)

    return paragraphs


def build_segments_by_mode(
    mode,
    paragraph,
    track_name,
    font,
    font_size,
    highlight_color,
    normal_color,
    transform_x,
    transform_y,
    fixed_width,
    shadow_enabled,
    shadow_color,
    border_color,
    border_width,
    border_alpha,
    background_color,
    ):

    """根据模式生成字幕片段"""
    segments = []
    #print("二级代码返回调试fx", fixed_width)

    if mode == "word_pop":
        # 单词跳出
        for w in paragraph:
            text_styles = []
            word_count = len(w["word"].replace(" ", "")) #统计有多少个字
            text_styles.append({
                        "start": 0,
                        "end": word_count,
                        "border": {
                            "alpha": border_alpha,
                            "color": border_color,
                            "width": border_width
                        }
                    })
            segments.append({
                "text": w["word"],
                "start": w["start"],
                "end": w["end"],
                "font": font,
                "track_name": track_name,
                "font_color": normal_color,
                "font_size": font_size,
                "transform_x": transform_x,
                "transform_y": transform_y,
                "shadow_enabled": shadow_enabled,
                "fixed_width": fixed_width,
                "text_styles": text_styles,

                "shadow_color": shadow_color,
                "border_color": border_color,
                "border_width": border_width,
                "border_alpha": border_alpha,

                "background_color": background_color,
            })

    elif mode == "word_highlight":
        # 单词高亮：当前词亮，其他灰
        paragraph_text = " ".join(w["word"] for w in paragraph)
        offsets = []
        ci = 0
        for w in paragraph:
            offsets.append((ci, ci + len(w["word"])))
            ci += len(w["word"]) + 1
        for idx, w in enumerate(paragraph):
            text_styles = []
            for k, (s, e) in enumerate(offsets):
                color = highlight_color if k == idx else normal_color
                text_styles.append({
                    "start": s,
                    "end": e,
                    "style": {
                        "color": color,
                        "size": font_size,
                        },
                    "border": {
                        "alpha": border_alpha,
                        "color": border_color,
                        "width": border_width
                    }
                })
            print("text_styles", text_styles)

            segments.append({
                "text": paragraph_text,
                "start": w["start"],
                "end": w["end"],
                "font": font,
                "track_name": track_name,
                "font_color": normal_color,
                "font_size": font_size,
                "text_styles": text_styles,
                "transform_x": transform_x,
                "transform_y": transform_y,
                "shadow_enabled": shadow_enabled,
                "fixed_width": fixed_width,


                "shadow_color": shadow_color,
                "border_color": border_color,
                "border_width": border_width,
                "border_alpha": border_alpha,

                "background_color": background_color,
            })

    elif mode == "sentence_fade":
        # 句子渐显：已亮过的词继续保持亮
        paragraph_text = " ".join(w["word"] for w in paragraph)
        offsets = []
        ci = 0
        for w in paragraph:
            offsets.append((ci, ci + len(w["word"])))
            ci += len(w["word"]) + 1
        for idx, w in enumerate(paragraph):
            text_styles = []
            for k, (s, e) in enumerate(offsets):
                color = highlight_color if k <= idx else normal_color
                text_styles.append({
                    "start": s,
                    "end": e,
                    "style": {"color": color, "size": font_size},
                    "border": {
                        "alpha": border_alpha,
                        "color": border_color,
                        "width": border_width
                    }
                })
            segments.append({
                "text": paragraph_text,
                "start": w["start"],
                "end": w["end"],
                "font": font,
                "track_name": track_name,
                "font_color": normal_color,
                "font_size": font_size,
                "text_styles": text_styles,
                "transform_x": transform_x,
                "transform_y": transform_y,
                "shadow_enabled": shadow_enabled,
                "fixed_width": fixed_width,


                "shadow_color": shadow_color,
                "border_color": border_color,
                "border_width": border_width,
                "border_alpha": border_alpha,

                "background_color": background_color,
            })

    elif mode == "sentence_pop":
        # 句子跳出
        text = " ".join(w["word"] for w in paragraph)
        start_time = paragraph[0]["start"]
        end_time = paragraph[-1]["end"]
        text_styles = []
        word_count = len(text.replace(" ", "")) #统计有多少个字
        text_styles.append({
                    "start": 0,
                    "end": word_count,
                    "border": {
                        "alpha": border_alpha,
                        "color": border_color,
                        "width": border_width
                    }
                })
        segments.append({
            "text": text,
            "start": start_time,
            "end": end_time,
            "font": font,
            "track_name": track_name,
            "font_color": normal_color,
            "font_size": font_size,
            "transform_x": transform_x,
            "transform_y": transform_y,
            "shadow_enabled": shadow_enabled,
            "fixed_width": fixed_width,
            "text_styles": text_styles,


            "shadow_color": shadow_color,
            "border_color": border_color,
            "border_width": border_width,
            "border_alpha": border_alpha,

            "background_color": background_color,
        })

    else:
        raise ValueError(f"未知模式: {mode}")
    """segments.append({
        "file_name": file_name,
    })"""

    return segments

corrected_srt = [{
                                "word": "Hello",
                                "start": 0.0,
                                "end": 0.64,
                                "confidence": 0.93917525
                            },
                            {
                                "word": "I'm",
                                "start": 0.64,
                                "end": 0.79999995,
                                "confidence": 0.9976464
                            },
                            {
                                "word": "PAWA",
                                "start": 0.79999995,
                                "end": 1.36,
                                "confidence": 0.6848311
                            },
                            {
                                "word": "Nice",
                                "start": 1.36,
                                "end": 1.52,
                                "confidence": 0.9850389
                            },
                            {
                                "word": "To",
                                "start": 1.52,
                                "end": 1.68,
                                "confidence": 0.9926886
                            },
                            {
                                "word": "Meet",
                                "start": 1.68,
                                "end": 2.08,
                                "confidence": 0.9972697
                            },
                            {
                                "word": "You",
                                "start": 2.08,
                                "end": 2.72,
                                "confidence": 0.9845563
                            },
                            {
                                "word": "Enjoy",
                                "start": 2.72,
                                "end": 3.04,
                                "confidence": 0.99794894
                            },
                            {
                                "word": "My",
                                "start": 3.04,
                                "end": 3.1999998,
                                "confidence": 0.9970203
                            },
                            {
                                "word": "Parttern",
                                "start": 3.1999998,
                                "end": 3.36,
                                "confidence": 0.9970235
                            },
                            {
                                "word": "Thank",
                                "start": 3.36,
                                "end": 3.6799998,
                                "confidence": 0.98627764
                            },
                            {
                                "word": "You",
                                "start": 3.6799998,
                                "end": 4.0,
                                "confidence": 0.9939551
                            },
                            ]


def add_koubo_from_srt(
    corrected_srt,
    track_name,
    mode="word_pop",
    font="ZY_Modern",
    font_size=32,
    highlight_color="#FFD700",
    normal_color="#AAAAAA", max_chunk_duration=1.5, max_words=5,
    gap_adjust=1,
    time_precision=3,
    transform_x=0.5,
    transform_y=0.3,
    fixed_width=-1,
    shadow_enabled=True,
    shadow_color="#000000",
    border_color="#000000",
    border_width=0.5,
    border_alpha=1.0,
    background_color="#000000",

    ):
    """统一入口：根据 mode 选择字幕效果"""
    sentences = group_sentences(corrected_srt)
    adjusted_sentences = adjust_sentence_timing(sentences, gap_adjust, time_precision)
    all_paragraphs = [split_into_paragraphs(s, max_words, max_chunk_duration) for s in adjusted_sentences]

    draft_id_ret = None
    for sentence_paragraphs in all_paragraphs:
        for paragraph in sentence_paragraphs:
            segments = build_segments_by_mode(
                mode,
                paragraph,
                track_name,
                font,
                font_size,
                highlight_color,
                normal_color,
                transform_x,
                transform_y,
                fixed_width,
                shadow_enabled,
                shadow_color,
                border_color,
                border_width,
                border_alpha,
                background_color,

                )
            #print("segments", segments)

            for seg in segments:
                #print("二级代码返回调试fx", seg)
                if draft_id_ret:
                    seg["draft_id"] = draft_id_ret
                    print("seg", seg)

                res = add_text_impl(**seg)
                if draft_id_ret is None and isinstance(res, dict):
                    try:
                        draft_id_ret = res["output"]["draft_id"]
                    except:
                        pass
    return draft_id_ret

colors = {
        "shadow_color": "#000000",
        "border_color": "#FFD700",
        "background_color": "#000000",
        "normal_color": "#FFFFFF",
        "highlight_color": "#DA70D6"  # 紫色
    }


def _run_koubo_demo():
    """Module-level demo code (originally ran on import, now guarded)."""
    from draft_demo import save_draft_impl
    draft_id = add_koubo_from_srt(
        corrected_srt,
        track_name="main_text",
        font_size=15,
        gap_adjust=0,
        transform_x=0,
        transform_y=-0.45,# 0=保持原间隔，1=调整>1s的间隔
        fixed_width = 0.6,
        mode="word_highlight",
        shadow_enabled=True,
        border_width=10,
        border_alpha=1.0,

        **colors,

        font="ZY_Modern", #设置自己的字体，需要在字体库中添加


    )

    add_image_impl(image_url="https://pic1.imgdb.cn/item/689aff2758cb8da5c81e64a2.png", start = 0, end = 4, draft_id=draft_id)

    save_result = save_draft_impl(draft_id, CAPCUT_DRAFT_FOLDER)

    print(save_result)


if __name__ == "__main__":
    _run_koubo_demo()

"""
# 单词高亮
mode="word_highlight"
# 单词跳出
mode="word_pop"
# 句子渐显
mode="sentence_fade"
# 句子跳出
mode="sentence_pop"
"""
def test_text():
    """Test adding text with various features"""
    draft_folder = CAPCUT_DRAFT_FOLDER

    # Test case 1: Basic text addition
    print("\nTest: Adding basic text")
    text_result = add_text_impl(
        text="Hello, I am CapCut Assistant",
        start=0,
        end=3,
        font="思源中宋",
        font_color="#FF0000",  # Red
        track_name="main_text",
        transform_y=0.8,
        transform_x=0.5,
        font_size=30.0
    )
    print("Test case 1 (Basic text) successful:", text_result)

    # Test case 2: Vertical text
    result2 = add_text_impl(
        draft_id=text_result['output']['draft_id'],
        text="Vertical text demo",
        start=3,
        end=6,
        font="云书法三行魏碑体",
        font_color="#00FF00",  # Green
        font_size=8.0,
        track_name="main_text",
        vertical=True,  # Enable vertical text
        transform_y=-0.5,
        outro_animation='Blur'
    )
    print("Test case 2 (Vertical text) successful:", result2)

    # Test case 3: Text with border and background
    result3 = add_text_impl(
        draft_id=result2['output']['draft_id'],
        text="Border and background test",
        start=6,
        end=9,
        font="思源中宋",
        font_color="#FFFFFF",  # White text
        font_size=24.0,
        track_name="main_text",
        transform_y=0.0,
        transform_x=0.5,
        border_color="#FF0000",  # Red border
        border_width=20.0,
        border_alpha=1.0,
        background_color="#0000FF",  # Blue background
        background_alpha=0.5,  # Semi-transparent background
        background_style=0  # Bubble style background
    )
    print("Test case 3 (Border and background) successful:", result3)

    # Test case 4: Text with shadow effect
    result4 = add_text_impl(
        draft_id=result3['output']['draft_id'],
        text="Shadow effect test",
        start=9,
        end=12,
        font="思源中宋",
        font_color="#FFFFFF",  # White text
        font_size=28.0,
        track_name="main_text",
        transform_y=-0.3,
        transform_x=0.5,
        shadow_enabled=True,  # Enable shadow
        shadow_alpha=0.8,
        shadow_angle=-30.0,
        shadow_color="#000000",  # Black shadow
        shadow_distance=8.0,
        shadow_smoothing=0.2
    )
    print("Test case 4 (Shadow effect) successful:", result4)

    # Test case 5: Multi-style text using TextStyleRange
    # Create different text styles
    style1 = {
        "start": 0,
        "end": 5,
        "style": {
            "color": "#FF0000",  # Red
            "size": 30,
            "bold": True
        },
        "border": {
            "color": "#FFFFFF",  # White border
            "width": 40,
            "alpha": 1.0
        },
        "font": "思源中宋"
    }

    style2 = {
        "start": 5,
        "end": 10,
        "style": {
            "color": "#00FF00",  # Green
            "size": 25,
            "italic": True
        },
        "font": "挥墨体"
    }

    style3 = {
        "start": 10,
        "end": 15,
        "style": {
            "color": "#0000FF",  # Blue
            "size": 20,
            "underline": True
        },
        "font": "金陵体"
    }

    # Add multi-style text
    result5 = add_text_impl(
        draft_id=result4['output']['draft_id'],
        text="Multi-style text test",
        start=12,
        end=15,
        font="思源粗宋",
        track_name="main_text",
        transform_y=0.3,
        transform_x=0.5,
        font_color="#000000",  # Default black
        font_size=20.0,
        # Use dictionary list instead of TextStyleRange object list
        text_styles=[style1, style2, style3]
    )
    print("Test case 5 (Multi-style text) successful:", result5)

    # Test case 6: Combined effects - shadow + background + multi-style
    combined_style1 = {
        "start": 0,
        "end": 8,
        "style": {
            "color": "#FFD700",  # Gold
            "size": 32,
            "bold": True
        },
        "border": {
            "color": "#8B4513",  # Brown border
            "width": 30,
            "alpha": 0.8
        },
        "font": "思源中宋"
    }

    combined_style2 = {
        "start": 8,
        "end": 16,
        "style": {
            "color": "#FF69B4",  # Hot pink
            "size": 28,
            "italic": True
        },
        "font": "挥墨体"
    }

    result6 = add_text_impl(
        draft_id=result5['output']['draft_id'],
        text="Combined effects demo",
        start=15,
        end=18,
        font="思源粗宋",
        track_name="main_text",
        transform_y=-0.6,
        transform_x=0.5,
        font_color="#FFFFFF",  # Default white
        font_size=24.0,
        # Background settings
        background_color="#4169E1",  # Royal blue background
        background_alpha=0.6,
        background_style=1,
        background_round_radius=0.3,
        background_height=0.18,
        background_width=0.8,
        # Shadow settings
        shadow_enabled=True,
        shadow_alpha=0.7,
        shadow_angle=-60.0,
        shadow_color="#2F4F4F",  # Dark slate gray shadow
        shadow_distance=6.0,
        shadow_smoothing=0.25,
        # Multi-style text
        text_styles=[combined_style1, combined_style2]
    )
    print("Test case 6 (Combined effects) successful:", result6)

    # Finally save and upload the draft
    if result6.get('success') and result6.get('output'):
        from draft_demo import save_draft_impl
        save_result = save_draft_impl(result6['output']['draft_id'], draft_folder)
        print(f"Draft save result: {save_result}")

    # Return the last test result for subsequent operations (if any)
    return result6


def test_text_02():
    """测试添加文本"""
    draft_folder = CAPCUT_DRAFT_FOLDER

    # 测试用例1：基本文本添加
    print("\n测试：添加基本文本")
    text_result = add_text_impl(
        text="你好，我是剪映助手",
        start=0,
        end=3,
        font="思源中宋",
        font_color="#FF0000",  # 红色
        track_name="main_text",
        transform_y=0.8,
        transform_x=0.5,
        font_size=30.0
    )
    print("测试用例1（基本文本）成功:", text_result)

    # 测试用例2：竖排文本
    result2 = add_text_impl(
        draft_id=text_result['output']['draft_id'],
        text="竖排文本演示",
        start=3,
        end=6,
        font="云书法三行魏碑体",
        font_color="#00FF00",  # 绿色
        font_size=8.0,
        track_name="main_text",
        vertical=True,  # 启用竖排
        transform_y=-0.5,
        outro_animation='晕开'
    )
    print("测试用例2（竖排文本）成功:", result2)

    # 测试用例3：带描边和背景的文本
    result3 = add_text_impl(
        draft_id=result2['output']['draft_id'],
        text="描边和背景测试",
        start=6,
        end=9,
        font="思源中宋",
        font_color="#FFFFFF",  # 白色文字
        font_size=24.0,
        track_name="main_text",
        transform_y=0.0,
        transform_x=0.5,
        border_color="#FF0000",  # 红色描边
        border_width=20.0,
        border_alpha=1.0,
        background_color="#0000FF",  # 蓝色背景
        background_alpha=0.5,  # 半透明背景
        background_style=0  # 气泡样式背景
    )
    print("测试用例3（描边和背景）成功:", result3)

    # 测试用例4：使用 TextStyleRange 的多样式文本
    # 创建不同的文本样式
    style1 = {
        "start": 0,
        "end": 2,
        "style": {
            "color": "#FF0000",  # 红色
            "size": 30,
            "bold": True
        },
        "border": {
            "color": "#FFFFFF",  # 白色描边
            "width": 40,
            "alpha": 1.0
        },
        "font": "思源中宋"
    }

    style2 = {
        "start": 2,
        "end": 4,
        "style": {
            "color": "#00FF00",  # 绿色
            "size": 25,
            "italic": True
        },
        "font": "挥墨体"
    }

    style3 = {
        "start": 4,
        "end": 6,
        "style": {
            "color": "#0000FF",  # 蓝色
            "size": 20,
            "underline": True
        },
        "font": "金陵体"
    }

    # 添加多样式文本
    result4 = add_text_impl(
        draft_id=result3['output']['draft_id'],
        text="多样式\n文本测试",
        start=9,
        end=12,
        font="思源粗宋",
        track_name="main_text",
        transform_y=0.5,
        transform_x=0.5,
        font_color="#000000",  # 默认黑色
        font_size=20.0,
        # 使用字典列表而不是 TextStyleRange 对象列表
        text_styles=[style1, style2, style3]
    )
    print("测试用例4（多样式文本）成功:", result4)

    # 最后保存并上传草稿
    if result4.get('success') and result4.get('output'):
        from draft_demo import save_draft_impl
        save_result = save_draft_impl(result4['output']['draft_id'],draft_folder)
        print(f"草稿保存结果: {save_result}")

    # 返回最后一个测试结果用于后续操作（如果有的话）
    return result4


def test_text_03():
    """测试添加文本"""
    draft_folder = CAPCUT_DRAFT_FOLDER

    # 测试用例1：基本文本添加
    print("\n测试：添加基本文本")
    text_result = add_text_impl(
        text="现在支持",
        start=0,
        end=6,
        font="挥墨体",
        font_color="#FFFFFF",  # 红色
        track_name="text_01",
        transform_y=0.58,
        transform_x=0,
        font_size=24.0,
        intro_animation="弹入",
        intro_duration=0.5
    )
    print("测试用例1（基本文本）成功:", text_result)

    # 测试用例2：带背景参数的文本
    result2 = add_text_impl(
        draft_id=text_result['output']['draft_id'],
        text="文字背景",
        start=1.5,
        end=6,
        font="思源中宋",
        font_color="#FFFFFF",
        font_size=20.0,
        track_name="text_2",
        transform_y=0.15,
        transform_x=0,
        background_color="#0000FF",  # 蓝色背景
        background_alpha=0.7,  # 70%透明度
        background_style=1,
        background_round_radius=0.5,  # 圆角半径
        background_height=0.2,  # 背景高度
        background_width=0.8,  # 背景宽度
        background_horizontal_offset=0.5,  # 水平居中
        background_vertical_offset=0.5,  # 垂直居中
        intro_animation="弹入",
        intro_duration=0.5
    )
    print("测试用例2（背景参数）成功:", result2)

    # 测试用例3：带阴影参数的文本
    result3 = add_text_impl(
        draft_id=result2['output']['draft_id'],
        text="文字阴影",
        start=3,
        end=6,
        font="金陵体",
        font_color="#FFFF00",  # 黄色文字
        font_size=25.0,
        track_name="text3",
        transform_y=-0.16,
        transform_x=0,
        shadow_enabled=True,  # 启用阴影
        shadow_alpha=0.8,  # 阴影透明度
        shadow_angle=-45.0,  # 阴影角度
        shadow_color="#0000FF",  # 蓝色阴影
        shadow_distance=10.0,  # 阴影距离
        shadow_smoothing=0.3,  # 阴影平滑度
        intro_animation="弹入",
        intro_duration=0.5
    )
    print("测试用例3（阴影参数）成功:", result3)

    # 测试用例4：带描边和背景的文本
    result4 = add_text_impl(
        draft_id=result3['output']['draft_id'],
        text="文字描边",
        start=4.5,
        end=6,
        font="思源中宋",
        font_color="#FFFFFF",  # 白色文字
        font_size=24.0,
        track_name="text_4",
        transform_y=-0.58,
        border_color="#FF0000",  # 红色描边
        border_width=20.0,
        border_alpha=1.0,
        intro_animation="弹入",
        intro_duration=0.5
    )
    print("测试用例4（综合参数）成功:", result4)

    # 最后保存并上传草稿
    if text_result.get('success') and text_result.get('output'):
        from draft_demo import save_draft_impl
        save_result = save_draft_impl(text_result['output']['draft_id'],draft_folder)
        print(f"草稿保存结果: {save_result}")

    # 返回最后一个测试结果用于后续操作（如果有的话）
    return text_result


def add_subtitle_impl(srt, draft_id=None, time_offset=0.0, font_size=5.0, font = "思源粗宋",
                    bold=False, italic=False, underline=False, font_color="#ffffff",
                    transform_x=0.0, transform_y=0.0, scale_x=1.0, scale_y=1.0,
                    vertical=False, track_name="subtitle", alpha=1,
                    border_alpha=1.0, border_color="#000000", border_width=0.0,
                    background_color="#000000", background_style=1, background_alpha=0.0,
                    rotation=0.0, width=1080, height=1920):
    """API wrapper for add_subtitle service"""
    data = {
        "license_key": LICENSE_KEY,  # Using trial version license key
        "srt": srt,  # Modified parameter name to match server side
        "draft_id": draft_id,
        "time_offset": time_offset,
        "font": font,
        "font_size": font_size,
        "bold": bold,
        "italic": italic,
        "underline": underline,
        "font_color": font_color,
        "transform_x": transform_x,
        "transform_y": transform_y,
        "scale_x": scale_x,
        "scale_y": scale_y,
        "vertical": vertical,
        "track_name": track_name,
        "alpha": alpha,
        "border_alpha": border_alpha,
        "border_color": border_color,
        "border_width": border_width,
        "background_color": background_color,
        "background_style": background_style,
        "background_alpha": background_alpha,
        "rotation": rotation,
        "width": width,
        "height": height
    }
    return make_request("add_subtitle", data)


def test_subtitle():
    draft_folder = CAPCUT_DRAFT_FOLDER

    # Test case: Add text subtitles
    print("\nTest: Adding text subtitles")
    text_result = add_subtitle_impl(
        srt="1\n00:00:00,000 --> 00:00:04,433\nHello, I am the CapCut draft assistant developed by Sun Guannan.\n\n2\n00:00:04,433 --> 00:00:11,360\nI specialize in combining audio, video, and image materials to create CapCut drafts.\n",
        font_size=8.0,
        bold=True,
        italic=True,
        underline=True,
        font_color="#FF0000",
        transform_y=0,
        transform_x=0.4,
        time_offset=42,
        scale_x=1.0,
        scale_y=2.0,
        vertical=True,
        # Add background color parameters
        background_color="#FFFF00",  # Yellow background
        background_style=1,  # Style 1 means rectangular background
        background_alpha=0.7,  # 70% opacity
        # Add border parameters
        border_color="#0000FF",  # Blue border
        border_width=20.0,  # Border width 2
        border_alpha=1.0  # Fully opaque
    )
    print(f"Text addition result: {text_result}")

    # Save draft
    if text_result.get('success') and text_result.get('output'):
        from draft_demo import save_draft_impl
        save_result = save_draft_impl(text_result['output']['draft_id'], draft_folder)
        print(f"Draft save result: {save_result}")


def test_subtitle_01():
    """Test adding text subtitles"""
    draft_folder = CAPCUT_DRAFT_FOLDER

    print("\nTest 3: Adding text subtitles")
    text_result = add_subtitle_impl(
        srt="1\n00:00:00,000 --> 00:00:04,433\n你333好，我是孙关南开发的剪映草稿助手。\n\n2\n00:00:04,433 --> 00:00:11,360\n我擅长将音频、视频、图片素材拼接在一起剪辑输出剪映草稿。\n",
        font_size=8.0,
        bold=True,
        italic=True,
        underline=True,
        font_color="#FF0000",
        transform_y=0,
        transform_x=0.4,
        time_offset=42,
        scale_x=1.0,
        scale_y=2.0,
        vertical=True
    )
    print(f"Text adding result: {text_result}")

    if text_result.get('success') and text_result.get('output'):
        from draft_demo import save_draft_impl
        save_result = save_draft_impl(text_result['output']['draft_id'], draft_folder)
        print(f"Draft saving result: {save_result}")

    return text_result


def test_subtitle_02():
    """Test adding text subtitles via SRT URL"""
    draft_folder = CAPCUT_DRAFT_FOLDER

    print("\nTest 3: Adding text subtitles (from URL)")
    text_result = add_subtitle_impl(
        srt="https://oss-oversea-bucket.oss-cn-hongkong.aliyuncs.com/dfd_srt_1748575460_kmtu56iu.srt?Expires=1748707452&OSSAccessKeyId=TMP.3Km5TL5giRLgDkc3CamKPcWZTmSrLVeRxPWxEisNB2CTymvUxrpX8VXzy5r99F6bJkwjwFM5d1RsiV3cF18iaMriAPtA1y&Signature=4JzB4YGiChsxcTFuvUyZ0v3MjMI%3D",
        font_size=8.0,
        bold=True,
        italic=True,
        underline=True,
        font_color="#FF0000",
        transform_y=0,
        transform_x=0.4,
        time_offset=42,
        scale_x=1.0,
        scale_y=2.0,
        vertical=True
    )
    print(f"Text adding result: {text_result}")

    if text_result.get('success') and text_result.get('output'):
        from draft_demo import save_draft_impl
        save_result = save_draft_impl(text_result['output']['draft_id'], draft_folder)
        print(f"Draft saving result: {save_result}")

    return text_result

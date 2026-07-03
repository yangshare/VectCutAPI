"""元数据声明式注册表：kind -> (描述, getter)。

getter(enum_value) 接收 adapter.enum_for(kind) 的返回值（枚举类 或 {子类型: 枚举} 字典），
产出最终 output 列表。新增一种枚举只加一行（规格 §5.3）。
"""

from __future__ import annotations

from typing import Callable, Dict, Tuple


def _simple_items(enum_cls) -> list:
    """简单 kind：[{name: member.name}]，与旧 get_xxx_types 输出一致。"""
    return [{"name": name} for name, _ in enum_cls.__members__.items()]


def _audio_effect_items(subtype_to_enum: dict) -> list:
    """audio_effect 富结构：[{name, type, params:[{name, default_value, min_value, max_value}]}]。

    params ×100 缩放，逐字搬自 capcut_server.py:1084-1216 旧实现，保证黄金快照保真。
    子类型遍历顺序由 adapter 返回的 dict 插入顺序决定（与旧实现逐段顺序一致）。
    """
    items = []
    for subtype, enum_cls in subtype_to_enum.items():
        for name, member in enum_cls.__members__.items():
            params_info = []
            for param in member.value.params:
                params_info.append(
                    {
                        "name": param.name,
                        "default_value": param.default_value * 100,
                        "min_value": param.min_value * 100,
                        "max_value": param.max_value * 100,
                    }
                )
            items.append({"name": name, "type": subtype, "params": params_info})
    return items


# kind -> (人类描述, getter)
META_KINDS: Dict[str, Tuple[str, Callable]] = {
    "intro_animation": ("入场动画", _simple_items),
    "outro_animation": ("出场动画", _simple_items),
    "combo_animation": ("组合动画", _simple_items),
    "transition": ("转场", _simple_items),
    "mask": ("蒙版", _simple_items),
    "audio_effect": ("音频效果", _audio_effect_items),
    "font": ("字体", _simple_items),
    "text_intro": ("文本入场动画", _simple_items),
    "text_outro": ("文本出场动画", _simple_items),
    "text_loop_anim": ("文本循环动画", _simple_items),
    "video_scene_effect": ("视频场景特效", _simple_items),
    "video_character_effect": ("视频人物特效", _simple_items),
}

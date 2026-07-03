"""收敛引擎枚举 import + 按平台派发。

应用层只有本模块直接 import pyJianYingDraft.metadata.*。
业务/元数据接口只调 enum_for(kind)，消除散落的 if IS_CAPCUT_ENV（规格 §5.1①）。
"""

from __future__ import annotations

from typing import Dict

# —— 收敛 capcut_server.py:5-17 的散落 import ——
from pyJianYingDraft.metadata.animation_meta import (
    Intro_type,
    Outro_type,
    Group_animation_type,
    Text_intro,
    Text_outro,
    Text_loop_anim,
)
from pyJianYingDraft.metadata.capcut_animation_meta import (
    CapCut_Intro_type,
    CapCut_Outro_type,
    CapCut_Group_animation_type,
)
from pyJianYingDraft.metadata.capcut_text_animation_meta import (
    CapCut_Text_intro,
    CapCut_Text_outro,
    CapCut_Text_loop_anim,
)
from pyJianYingDraft.metadata.transition_meta import Transition_type
from pyJianYingDraft.metadata.capcut_transition_meta import CapCut_Transition_type
from pyJianYingDraft.metadata.mask_meta import Mask_type
from pyJianYingDraft.metadata.capcut_mask_meta import CapCut_Mask_type
from pyJianYingDraft.metadata.audio_effect_meta import (
    Tone_effect_type,
    Audio_scene_effect_type,
    Speech_to_song_type,
)
from pyJianYingDraft.metadata.capcut_audio_effect_meta import (
    CapCut_Voice_filters_effect_type,
    CapCut_Voice_characters_effect_type,
    CapCut_Speech_to_song_effect_type,
)
from pyJianYingDraft.metadata.font_meta import Font_type
from pyJianYingDraft.metadata.video_effect_meta import (
    Video_scene_effect_type,
    Video_character_effect_type,
)
from pyJianYingDraft.metadata.capcut_effect_meta import (
    CapCut_Video_scene_effect_type,
    CapCut_Video_character_effect_type,
)


# kind -> (capcut_enum_or_dict, jianying_enum_or_dict)
# font 无 CapCut 变体，两平台共用 Font_type。
# audio_effect 返回 {子类型标签: 枚举} 字典，由 registry getter 展开为富结构。
# 字典插入顺序与旧 get_audio_effect_types 逐段顺序一致，保证黄金保真。
_ENUM_MAP: Dict[str, tuple] = {
    "intro_animation": (CapCut_Intro_type, Intro_type),
    "outro_animation": (CapCut_Outro_type, Outro_type),
    "combo_animation": (CapCut_Group_animation_type, Group_animation_type),
    "transition": (CapCut_Transition_type, Transition_type),
    "mask": (CapCut_Mask_type, Mask_type),
    "audio_effect": (
        {  # capcut：顺序 Voice_filters -> Voice_characters -> Speech_to_song
            "Voice_filters": CapCut_Voice_filters_effect_type,
            "Voice_characters": CapCut_Voice_characters_effect_type,
            "Speech_to_song": CapCut_Speech_to_song_effect_type,
        },
        {  # jianying：顺序 Tone -> Audio_scene -> Speech_to_song
            "Tone": Tone_effect_type,
            "Audio_scene": Audio_scene_effect_type,
            "Speech_to_song": Speech_to_song_type,
        },
    ),
    "font": (Font_type, Font_type),  # 无 CapCut 变体
    "text_intro": (CapCut_Text_intro, Text_intro),
    "text_outro": (CapCut_Text_outro, Text_outro),
    "text_loop_anim": (CapCut_Text_loop_anim, Text_loop_anim),
    "video_scene_effect": (CapCut_Video_scene_effect_type, Video_scene_effect_type),
    "video_character_effect": (CapCut_Video_character_effect_type, Video_character_effect_type),
}


def active_platform() -> str:
    """返回 'capcut' 或 'jianying'，读 draft_store 激活 profile。"""
    from vectcut.core.draft_store import get_active_profile

    return "capcut" if get_active_profile().is_capcut_env else "jianying"


def enum_for(kind: str):
    """返回当前平台对应 kind 的枚举类（audio_effect 返回 {子类型: 枚举} 字典）。

    未知 kind 抛 KeyError（由 service 转 InvalidParam）。
    """
    if kind not in _ENUM_MAP:
        raise KeyError(kind)
    cap, jy = _ENUM_MAP[kind]
    return cap if active_platform() == "capcut" else jy

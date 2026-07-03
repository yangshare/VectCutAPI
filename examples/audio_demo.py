"""Audio demo — 迁自 example.py（阶段5 拆分）。"""
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from _client import make_request, CAPCUT_DRAFT_FOLDER
from draft_demo import save_draft_impl


def add_audio_track(audio_url, start, end, target_start, volume=1.0,
                    speed=1.0, track_name="main_audio", effect_type=None, effect_params=None, draft_id=None):
    """API call to add audio track"""
    data = {
        "audio_url": audio_url,
        "start": start,
        "end": end,
        "target_start": target_start,
        "volume": volume,
        "speed": speed,
        "track_name": track_name,
        "effect_type": effect_type,
        "effect_params": effect_params
    }

    if draft_id:
        data["draft_id"] = draft_id

    return make_request("add_audio", data)


def test_audio01():
    """Test adding audio"""
    draft_folder = CAPCUT_DRAFT_FOLDER

    print("\nTest: Adding audio")
    audio_result = add_audio_track(
        audio_url="https://lf3-lv-music-tos.faceu.com/obj/tos-cn-ve-2774/oYACBQRCMlWBIrZipvQZhI5LAlUFYii0RwEPh",
        start=4,
        end=5,
        target_start=15,
        volume=0.8,
        speed=1.0,
        track_name="main_audio101",
        # effect_type="麦霸",
        effect_type="Tremble",
        effect_params=[90.0, 50.0]
    )
    print(f"Audio addition result: {audio_result}")
    print(save_draft_impl(audio_result['output']['draft_id'], draft_folder))


def test_audio02():
    """Test adding multiple audio segments"""
    draft_folder = CAPCUT_DRAFT_FOLDER

    print("\nTest: Adding audio 1")
    audio_result = add_audio_track(
        audio_url="https://lf3-lv-music-tos.faceu.com/obj/tos-cn-ve-2774/oYACBQRCMlWBIrZipvQZhI5LAlUFYii0RwEPh",
        start=4,
        end=5,
        target_start=0,
        volume=0.8,
        speed=1.0,
        track_name="main_audio101",
        # effect_type="麦霸",
        effect_type="Tremble",
        effect_params=[90.0, 50.0]
    )
    print(f"Audio addition result 1: {audio_result}")

    print("\nTest: Adding audio 2")
    audio_result = add_audio_track(
        draft_id=audio_result['output']['draft_id'],
        audio_url="https://lf3-lv-music-tos.faceu.com/obj/tos-cn-ve-2774/oYACBQRCMlWBIrZipvQZhI5LAlUFYii0RwEPh",
        start=4,
        end=5,
        target_start=1.5,
        volume=0.8,
        speed=1.0,
        track_name="main_audio101",
        # effect_type="麦霸",
        effect_type="Tremble",
        effect_params=[90.0, 50.0]
    )
    print(f"Audio addition result 2: {audio_result}")
    print(save_draft_impl(audio_result['output']['draft_id'], draft_folder))


def test_audio03():
    """Test adding audio in a loop"""
    draft_folder = CAPCUT_DRAFT_FOLDER

    draft_id = None  # Initialize draft_id

    for i in range(10):
        target_start = i * 1.5  # Increment by 1.5 seconds each time

        audio_result = add_audio_track(
            audio_url="https://lf3-lv-music-tos.faceu.com/obj/tos-cn-ve-2774/oYACBQRCMlWBIrZipvQZhI5LAlUFYii0RwEPh",
            start=4,
            end=5,
            target_start=target_start,
            volume=0.8,
            speed=1.0,
            track_name="main_audio101",
            # effect_type="麦霸",
            effect_type="Tremble",
            effect_params=[90.0, 50.0],
            draft_id=draft_id  # Pass the previous draft_id (None for the first time)
        )

        draft_id = audio_result['output']['draft_id']  # Update draft_id
        print(f"Audio addition result {i+1}: {audio_result}")

    # Finally save and upload draft
    save_result = save_draft_impl(draft_id, draft_folder)
    print(f"Draft save result: {save_result}")


def test_audio04():
    """Test adding audio to different tracks"""
    draft_folder = CAPCUT_DRAFT_FOLDER

    print("\nTest: Adding audio 1")
    audio_result = add_audio_track(
        audio_url="https://lf3-lv-music-tos.faceu.com/obj/tos-cn-ve-2774/oYACBQRCMlWBIrZipvQZhI5LAlUFYii0RwEPh",
        start=4,
        end=5,
        target_start=0,
        volume=0.8,
        speed=1.0,
        track_name="main_audio101",
        # effect_type="麦霸",
        effect_type="Tremble",
        effect_params=[90.0, 50.0]
    )
    print(f"Audio addition result 1: {audio_result}")

    print("\nTest: Adding audio 2")
    audio_result = add_audio_track(
        draft_id=audio_result['output']['draft_id'],
        audio_url="https://lf3-lv-music-tos.faceu.com/obj/tos-cn-ve-2774/oYACBQRCMlWBIrZipvQZhI5LAlUFYii0RwEPh",
        start=4,
        end=5,
        target_start=1.5,
        volume=0.8,
        speed=1.0,
        track_name="main_audio102",  # Use different track name
        # effect_type="麦霸",
        effect_type="Tremble",
        effect_params=[90.0, 50.0]
    )
    print(f"Audio addition result 2: {audio_result}")
    from draft_demo import query_draft_status_impl_polling
    query_draft_status_impl_polling(audio_result['output']['draft_id'])
    save_draft_impl(audio_result['output']['draft_id'], draft_folder)

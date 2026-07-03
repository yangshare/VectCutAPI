"""Sticker demo — 迁自 example.py（阶段5 拆分）。"""
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from _client import make_request, CAPCUT_DRAFT_FOLDER, JIANYINGPRO_DRAFT_FOLDER
from video_demo import add_video_impl


def add_sticker_impl(resource_id, start, end, draft_id=None, transform_x=0, transform_y=0,
                    alpha=1.0, flip_horizontal=False, flip_vertical=False, rotation=0.0,
                    scale_x=1.0, scale_y=1.0, track_name="sticker_main", relative_index=0,
                    width=1080, height=1920):
    """API call to add sticker"""
    data = {
        "sticker_id": resource_id,
        "start": start,
        "end": end,
        "transform_x": transform_x,
        "transform_y": transform_y,
        "alpha": alpha,
        "flip_horizontal": flip_horizontal,
        "flip_vertical": flip_vertical,
        "rotation": rotation,
        "scale_x": scale_x,
        "scale_y": scale_y,
        "track_name": track_name,
        "relative_index": relative_index,
        "width": width,
        "height": height
    }

    if draft_id:
        data["draft_id"] = draft_id

    return make_request("add_sticker", data)

def test_stiker_01():
    """Test adding stickers"""
    # Add stickers, test various parameters, only for jianyingpro
    draft_folder = JIANYINGPRO_DRAFT_FOLDER
    result = add_sticker_impl(
        resource_id="7107529669750066445",
        start=1.0,
        end=4.0,
        transform_y=0.3,      # Move up
        transform_x=-0.2,     # Move left
        alpha=0.8,            # Set transparency
        rotation=45.0,        # Rotate 45 degrees
        scale_x=1.5,          # Horizontal scale 1.5x
        scale_y=1.5,          # Vertical scale 1.5x
        flip_horizontal=True  # Horizontal flip
    )
    print(f"Sticker adding result: {save_draft_impl(result['output']['draft_id'], draft_folder)}")

def test_stiker_02():
    """Test adding stickers"""
    # Add stickers, test various parameters, only for jianyingpro
    draft_folder = JIANYINGPRO_DRAFT_FOLDER
    result = add_sticker_impl(
        resource_id="7107529669750066445",
        start=1.0,
        end=4.0,
        transform_y=0.3,      # Move up
        transform_x=-0.2,     # Move left
        alpha=0.8,            # Set transparency
        rotation=45.0,        # Rotate 45 degrees
        scale_x=1.5,          # Horizontal scale 1.5x
        scale_y=1.5,          # Vertical scale 1.5x
        flip_horizontal=True  # Horizontal flip
    )
    result = add_sticker_impl(
        resource_id="7107529669750066445",
        draft_id=result['output']['draft_id'],
        start=5.0,
        end=10.0,
        transform_y=-0.3,     # Move up
        transform_x=0.5,      # Move left
        alpha=0.1,            # Set transparency
        rotation=30.0,        # Rotate 30 degrees
        scale_x=1.5,          # Horizontal scale 1.5x
        scale_y=1.2,          # Vertical scale 1.2x
    )
    print(f"Sticker adding result: {save_draft_impl(result['output']['draft_id'], draft_folder)}")

def test_stiker_03():
    """Test adding stickers"""
    # Add stickers, test various parameters, only for jianyingpro
    draft_folder = JIANYINGPRO_DRAFT_FOLDER
    result = add_sticker_impl(
        resource_id="7107529669750066445",
        start=1.0,
        end=4.0,
        transform_y=0.3,      # Move up
        transform_x=-0.2,     # Move left
        alpha=0.8,            # Set transparency
        rotation=45.0,        # Rotate 45 degrees
        scale_x=1.5,          # Horizontal scale 1.5x
        scale_y=1.5,          # Vertical scale 1.5x
        flip_horizontal=True, # Horizontal flip
        track_name="stiker_main",
        relative_index=999
    )
    result = add_sticker_impl(
        resource_id="7107529669750066445",
        draft_id=result['output']['draft_id'],
        start=5.0,
        end=10.0,
        transform_y=-0.3,     # Move up
        transform_x=0.5,      # Move left
        alpha=0.1,            # Set transparency
        rotation=30.0,        # Rotate 30 degrees
        scale_x=1.5,          # Horizontal scale 1.5x
        scale_y=1.2,          # Vertical scale 1.2x
        track_name="stiker_main_2",
        relative_index=0
    )
    print(f"Sticker adding result: {save_draft_impl(result['output']['draft_id'], draft_folder)}")


def test_transition_01():
    """Test adding multiple images with dissolve transition effects"""
    # Set draft folder path for saving
    draft_folder = CAPCUT_DRAFT_FOLDER

    print("\nTest: Adding image 1")
    image_result = add_image_impl(
        image_url="https://cdn.wanx.aliyuncs.com/wanx/1719234057367822001/text_to_image_v2/d6e33c84d7554146a25b1093b012838b_0.png?x-oss-process=image/resize,w_500/watermark,image_aW1nL3dhdGVyMjAyNDExMjkwLnBuZz94LW9zcy1wcm9jZXNzPWltYWdlL3Jlc2l6ZSxtX2ZpeGVkLHdfMTQ1LGhfMjU=,t_80,g_se,x_10,y_10/format,webp",
        width=480,
        height=480,
        start=0,
        end=5.0,
        transform_y=0.7,
        scale_x=2.0,
        scale_y=1.0,
        transform_x=0,
        track_name="main",
        transition="Dissolve",
        transition_duration=1.0
    )
    print(f"Image 1 added successfully! {image_result['output']['draft_id']}")

    print("\nTest: Adding image 2")
    image_result = add_image_impl(
        draft_id=image_result['output']['draft_id'],
        image_url="https://cdn.wanx.aliyuncs.com/wanx/1719234057367822001/text_to_image_v2/d6e33c84d7554146a25b1093b012838b_0.png?x-oss-process=image/resize,w_500/watermark,image_aW1nL3dhdGVyMjAyNDExMjkwLnBuZz94LW9zcy1wcm9jZXNzPWltYWdlL3Jlc2l6ZSxtX2ZpeGVkLHdfMTQ1LGhfMjU=,t_80,g_se,x_10,y_10/format,webp",
        width=480,
        height=480,
        start=5,
        end=10.0,
        transform_y=0.7,
        scale_x=2.0,
        scale_y=1.0,
        transform_x=0,
        track_name="main"
    )
    print(f"Image 2 added successfully! {image_result['output']['draft_id']}")
    print(save_draft_impl(image_result['output']['draft_id'], draft_folder))


def test_transition_02():
    """Test adding video tracks with transition effects"""
    # Set draft folder path for saving
    draft_folder = CAPCUT_DRAFT_FOLDER
    # Define video URL for testing
    video_url = "https://cdn.wanx.aliyuncs.com/wanx/1719234057367822001/text_to_video/092faf3c94244973ab752ee1280ba76f.mp4?spm=5176.29623064.0.0.41ed26d6cBOhV3&file=092faf3c94244973ab752ee1280ba76f.mp4"

    print("\nTest: Adding video track")
    video_result = add_video_impl(
        video_url=video_url,
        width=1920,
        height=1080,
        start=0,
        end=5.0, # Trim first 5 seconds of video
        target_start=0,
        track_name="main_video_track",
        transition="Dissolve",
        transition_duration=1.0
    )
    print(f"Video track adding result: {video_result}")

    print("\nTest: Adding video track")
    video_result = add_video_impl(
        video_url=video_url,
        draft_id=video_result['output']['draft_id'],
        width=1920,
        height=1080,
        start=0,
        end=5.0, # Trim first 5 seconds of video
        target_start=5.0,
        track_name="main_video_track"
    )
    print(f"Video track adding result: {video_result}")

    if video_result and 'output' in video_result and 'draft_id' in video_result['output']:
        draft_id = video_result['output']['draft_id']
        print(f"Saving draft: {save_draft_impl(draft_id, draft_folder)}")
    else:
        print("Unable to get draft ID, skipping save operation.")

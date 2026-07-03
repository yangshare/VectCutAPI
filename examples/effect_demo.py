"""Effect demo — 迁自 example.py（阶段5 拆分）。"""
import os
import shutil
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from _client import make_request, CAPCUT_DRAFT_FOLDER
from video_demo import add_video_impl
from draft_demo import save_draft_impl


def add_effect(effect_type, start, end, draft_id=None, track_name="effect_01",
              params=None, width=1080, height=1920, effect_category=None):
    """API call to add effect"""
    data = {
        "effect_type": effect_type,
        "start": start,
        "end": end,
        "track_name": track_name,
        "params": params or [],
        "width": width,
        "height": height
    }

    if effect_category:
        data["effect_category"] = effect_category

    if draft_id:
        data["draft_id"] = draft_id

    return make_request("add_effect", data)

def test_effect_01():
    """Test adding effect service"""
    draft_folder = CAPCUT_DRAFT_FOLDER

    print("\nTest: Adding effect")
    effect_result = add_effect(
        start=0,
        end=5,
        track_name="effect_01",
        # effect_type="金粉闪闪",  # Example using glow effect
        effect_type="Gold_Sparkles",
        params=[100, 50, 34]  # Example parameters, depending on the specific effect type
    )
    print(f"Effect adding result: {effect_result}")
    print(save_draft_impl(effect_result['output']['draft_id'], draft_folder))

    # If needed, you can add other test cases here

    # Return the first test result for subsequent operations (if any)
    return effect_result


def test_effect_02():
    """Test service for adding effects"""
    # draft_folder = "/Users/sunguannan/Movies/JianyingPro/User Data/Projects/com.lveditor.draft"
    draft_folder = CAPCUT_DRAFT_FOLDER

    print("\nTest: Adding effects")
    # First add video track
    image_result = add_video_impl(
        video_url="https://pan.superbed.cn/share/1nbrg1fl/jimeng_daweidai.mp4",
        start=0,
        end=3.0,
        target_start=0,
        width=1080,
        height=1920
    )
    print(f"Video added successfully! {image_result['output']['draft_id']}")
    image_result = add_video_impl(
        video_url="https://pan.superbed.cn/share/1nbrg1fl/jimeng_daweidai.mp4",
        draft_id=image_result['output']['draft_id'],
        start=0,
        end=3.0,
        target_start=3,
    )
    print(f"Video added successfully! {image_result['output']['draft_id']}")

    # Then add effect
    effect_result = add_effect(
        effect_type="Like",
        effect_category="character",  # Explicitly specify as character effect
        start=3,
        end=6,
        draft_id=image_result['output']['draft_id'],
        track_name="effect_01"
    )
    print(f"Effect adding result: {effect_result}")
    print(save_draft_impl(effect_result['output']['draft_id'], draft_folder))

    source_folder = os.path.join(os.getcwd(), effect_result['output']['draft_id'])
    destination_folder = os.path.join(draft_folder, effect_result['output']['draft_id'])

    if os.path.exists(source_folder):
        print(f"Moving {effect_result['output']['draft_id']} to {draft_folder}")
        shutil.move(source_folder, destination_folder)
        print("Folder moved successfully!")
    else:
        print(f"Source folder {effect_result['output']['draft_id']} does not exist")

    # Add log to prompt user to find the draft in CapCut
    print(f"\n===== IMPORTANT =====\nPlease open CapCut and find the draft named '{effect_result['output']['draft_id']}'\n======================")

    # Return the first test result for subsequent operations (if any)
    return effect_result

def test_mask_01():
    """Test adding images to different tracks"""
    draft_folder = CAPCUT_DRAFT_FOLDER

    print("\nTest: Adding image 1")
    from image_demo import add_image_impl
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
        track_name="main"
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

    print("\nTest: Adding image 3")
    image_result = add_image_impl(
        draft_id=image_result['output']['draft_id'],
        image_url="https://cdn.wanx.aliyuncs.com/wanx/1719234057367822001/text_to_image_v2/d6e33c84d7554146a25b1093b012838b_0.png?x-oss-process=image/resize,w_500/watermark,image_aW1nL3dhdGVyMjAyNDExMjkwLnBuZz94LW9zcy1wcm9jZXNzPWltYWdlL3Jlc2l6ZSxtX2ZpeGVkLHdfMTQ1LGhfMjU=,t_80,g_se,x_10,y_10/format,webp",
        width=480,
        height=480,
        start=10,
        end=15.0,
        transform_y=0.7,
        scale_x=2.0,
        scale_y=1.0,
        transform_x=0,
        track_name="main_2",  # Use different track name
        mask_type="Circle",  # Add circular mask
        mask_center_x=0.5,  # Mask center X coordinate (0.5 means centered)
        mask_center_y=0.5,  # Mask center Y coordinate (0.5 means centered)
        mask_size=0.8,  # Mask size (0.8 means 80%)
        mask_feather=0.1  # Mask feathering (0.1 means 10%)
    )
    print(f"Image 3 added successfully! {image_result['output']['draft_id']}")
    print(save_draft_impl(image_result['output']['draft_id'], draft_folder))

def test_mask_02():
    """Test adding videos to different tracks"""
    # Set draft folder path for saving
    draft_folder = CAPCUT_DRAFT_FOLDER
    # Define video URL for testing
    video_url = "https://cdn.wanx.aliyuncs.com/wanx/1719234057367822001/text_to_video/092faf3c94244973ab752ee1280ba76f.mp4?spm=5176.29623064.0.0.41ed26d6cBOhV3&file=092faf3c94244973ab752ee1280ba76f.mp4"
    draft_id = None  # Initialize draft_id

    # Add video to first track
    video_result = add_video_impl(
        draft_id=draft_id,  # Pass in draft_id
        video_url=video_url,
        width=1920,
        height=1080,
        start=0,
        end=5.0, # Use first 5 seconds of video
        target_start=0,
        track_name="main_video_track"
    )
    draft_id = video_result['output']['draft_id']  # Update draft_id
    print(f"First video addition result: {video_result}")

    # Add video to second track
    video_result = add_video_impl(
        draft_id=draft_id,  # Use previous draft_id
        video_url=video_url,
        width=1920,
        height=1080,
        start=0,
        end=5.0, # Use first 5 seconds of video
        target_start=0,
        track_name="main_video_track_2",  # Use different track name
        speed=1.0,  # Change playback speed
        scale_x=0.5,  # Reduce video width
        transform_y=0.5  # Place video at bottom of screen
    )
    draft_id = video_result['output']['draft_id']  # Update draft_id
    print(f"Second video addition result: {video_result}")

    # Third time add video to another track with circular mask
    video_result = add_video_impl(
        draft_id=draft_id,  # Use previous draft_id
        video_url=video_url,
        width=1920,
        height=1080,
        start=0,
        end=5.0, # Use first 5 seconds of video
        target_start=0,
        track_name="main_video_track_3",  # Use third track
        speed=1.5,  # Faster playback speed
        scale_x=0.3,  # Smaller video width
        transform_y=-0.5,  # Place video at top of screen
        mask_type="Circle",  # Add circular mask
        mask_center_x=0.5,  # Mask center X coordinate
        mask_center_y=0.5,  # Mask center Y coordinate
        mask_size=0.8,  # Mask size
        mask_feather=0.1  # Mask feathering
    )
    draft_id = video_result['output']['draft_id']  # Update draft_id
    print(f"Third video addition result: {video_result}")

    # Finally save and upload draft
    save_result = save_draft_impl(draft_id, draft_folder)
    print(f"Draft save result: {save_result}")

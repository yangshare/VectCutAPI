"""Video demo — 迁自 example.py（阶段5 拆分）。"""
import json
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from _client import make_request, CAPCUT_DRAFT_FOLDER
from audio_demo import add_audio_track
from text_demo import add_text_impl
from image_demo import add_image_impl
from draft_demo import save_draft_impl, query_draft_status_impl_polling, query_script_impl


def add_video_keyframe_impl(draft_id, track_name, property_type=None, time=None, value=None,
                           property_types=None, times=None, values=None):
    """API call to add video keyframe

    Supports two modes:
    1. Single keyframe: using property_type, time, value parameters
    2. Batch keyframes: using property_types, times, values parameters (in list form)
    """
    data = {
        "draft_id": draft_id,
        "track_name": track_name
    }

    # Add single keyframe parameters (if provided)
    if property_type is not None:
        data["property_type"] = property_type
    if time is not None:
        data["time"] = time
    if value is not None:
        data["value"] = value

    # Add batch keyframe parameters (if provided)
    if property_types is not None:
        data["property_types"] = property_types
    if times is not None:
        data["times"] = times
    if values is not None:
        data["values"] = values

    return make_request("add_video_keyframe", data)

def add_video_impl(video_url, start=None, end=None, width=None, height=None, track_name="main",
                   draft_id=None, transform_y=0, scale_x=1, scale_y=1, transform_x=0,
                   speed=1.0, target_start=0, relative_index=0, transition=None, transition_duration=None,
                   # Mask-related parameters
                   mask_type=None, mask_center_x=0.5, mask_center_y=0.5, mask_size=1.0,
                   mask_rotation=0.0, mask_feather=0.0, mask_invert=False,
                   mask_rect_width=None, mask_round_corner=None, background_blur=None):
    """API call to add video track"""
    data = {
        "video_url": video_url,
        "height": height,
        "draft_id": draft_id,
        "track_name": track_name,
        "transform_y": transform_y,
        "scale_x": scale_x,
        "scale_y": scale_y,
        "transform_x": transform_x,
        "speed": speed,
        "target_start": target_start,
        "relative_index": relative_index,
        "transition": transition,
        "transition_duration": transition_duration or 0.5,  # Default transition duration is 0.5 seconds
        # Mask-related parameters
        "mask_type": mask_type,
        "mask_center_x": mask_center_x,
        "mask_center_y": mask_center_y,
        "mask_size": mask_size,
        "mask_rotation": mask_rotation,
        "mask_feather": mask_feather,
        "mask_invert": mask_invert,
        "mask_rect_width": mask_rect_width,
        "mask_round_corner": mask_round_corner
    }
    if start:
        data["start"] = start
    if end:
        data["end"] = end
    if width:
        data["width"] = width
    if height:
        data["height"] = height
    if background_blur:
        data["background_blur"] = background_blur
    return make_request("add_video", data)

def test01():
    draft_folder = CAPCUT_DRAFT_FOLDER

    # Combined test
    print("\nTest 2: Add audio")
    audio_result = add_audio_track(
        audio_url = "https://lf3-lv-music-tos.faceu.com/obj/tos-cn-ve-2774/oYACBQRCMlWBIrZipvQZhI5LAlUFYii0RwEPh",
        start=4,
        end=5,
        target_start=2,
        volume=0.8,
        speed=1.0,
        track_name="main_audio100",
        effect_type="Tremble",
        effect_params=[90.0, 50.0]
    )
    print(f"Audio addition result 1: {audio_result}")

    audio_result = add_audio_track(
        draft_id=audio_result['output']['draft_id'],
        audio_url = "https://lf3-lv-music-tos.faceu.com/obj/tos-cn-ve-2774/oYACBQRCMlWBIrZipvQZhI5LAlUFYii0RwEPh",
        start=4,
        end=5,
        target_start=4,
        volume=0.8,
        speed=1.0,
        track_name="main_audio100",
        effect_type="Tremble",
        effect_params=[90.0, 50.0]
    )
    print(f"Audio addition result 2: {audio_result}")

    audio_result = add_audio_track(
        draft_id=audio_result['output']['draft_id'],
        audio_url = "https://lf3-lv-music-tos.faceu.com/obj/tos-cn-ve-2774/oYACBQRCMlWBIrZipvQZhI5LAlUFYii0RwEPh",
        start=4,
        end=5,
        target_start=6,
        volume=0.8,
        speed=1.0,
        track_name="main_audio101",
        effect_type="Tremble",
        effect_params=[90.0, 50.0]
    )
    print(f"Audio addition result 3: {audio_result}")

    # Test case 1: Basic text addition
    text_result = add_text_impl(
        draft_folder=draft_folder,
        text="Test Text 1",
        draft_id=audio_result['output']['draft_id'],
        start=0,
        end=3,
        font="思源中宋",  # Use Source Han Serif font
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
        text="Vertical Text Test",
        start=3,
        end=6,
        font="云书法三行魏碑体",
        font_color="#00FF00",  # Green
        font_size=8.0,
        track_name="main_text",
        vertical=True,  # Enable vertical text
        transform_y=-0.5,
        outro_animation='Fade_Out'
    )
    print("Test case 2 (Vertical text) successful:", result2)

    print("Test completed")
    # Test adding image
    image_result = add_image_impl(
        draft_id=result2['output']['draft_id'],  # Replace with actual draft ID
        image_url="https://cdn.wanx.aliyuncs.com/wanx/1719234057367822001/text_to_image_v2/d6e33c84d7554146a25b1093b012838b_0.png?x-oss-process=image/resize,w_500/watermark,image_aW1nL3dhdGVyMjAyNDExMjkwLnBuZz94LW9zcy1wcm9jZXNzPWltYWdlL3Jlc2l6ZSxtX2ZpeGVkLHdfMTQ1LGhfMjU=,t_80,g_se,x_10,y_10/format,webp",  # Replace with actual image URL
        width=480,
        height=480,
        start = 0,
        end=5.0,  # Display for 5 seconds
        transform_y=0.7,
        scale_x=2.0,
        scale_y=1.0,
        transform_x=0,
        track_name="main"
    )
    print("Image added successfully!")


    # Test adding image
    image_result = add_image_impl(
        draft_id=result2['output']['draft_id'],  # Replace with actual draft ID
        image_url="http://gips0.baidu.com/it/u=3602773692,1512483864&fm=3028&app=3028&f=JPEG&fmt=auto?w=960&h=1280",  # Replace with actual image URL
        width=480,
        height=480,
        start = 0,
        end=5.0,  # Display for 5 seconds
        transform_y=0.7,
        scale_x=2.0,
        scale_y=1.0,
        transform_x=0,
        track_name="main_2"
    )
    print("Image added successfully!")

    image_result = add_image_impl(
        draft_id=image_result['output']['draft_id'],  # Replace with actual draft ID
        image_url="https://cdn.wanx.aliyuncs.com/wanx/1719234057367822001/text_to_image_v2/d6e33c84d7554146a25b1093b012838b_0.png?x-oss-process=image/resize,w_500/watermark,image_aW1nL3dhdGVyMjAyNDExMjkwLnBuZz94LW9zcy1wcm9jZXNzPWltYWdlL3Jlc2l6ZSxtX2ZpeGVkLHdfMTQ1LGhfMjU=,t_80,g_se,x_10,y_10/format,webp",  # Replace with actual image URL
        width=480,
        height=480,
        start = 5,
        end=10.0,  # Display for 5 seconds
        transform_y=0.7,
        scale_x=2.0,
        scale_y=1.0,
        transform_x=0,
        track_name="main"
    )
    print("Image 2 added successfully!")

    # Test adding video keyframe
    print("\nTest: Add video keyframe")
    keyframe_result = add_video_keyframe_impl(
        draft_id=image_result['output']['draft_id'],  # Use existing draft ID
        track_name="main",
        property_type="position_y",  # Test opacity
        time=1.5,  # Add keyframe at 3.5 seconds
        value="0.2"  # Move 300px
    )
    print(f"Keyframe addition result: {keyframe_result}")

    print("\nTest: Add video keyframe")
    keyframe_result = add_video_keyframe_impl(
        draft_id=image_result['output']['draft_id'],  # Use existing draft ID
        track_name="main",
        property_type="position_y",  # Test opacity
        time=3.5,  # Add keyframe at 3.5 seconds
        value="0.4"  # Move 300px
    )
    print(f"Keyframe addition result: {keyframe_result}")

    query_draft_status_impl_polling(keyframe_result['output']['draft_id'])
    save_draft_impl(keyframe_result['output']['draft_id'], draft_folder)

def test02():
    draft_folder = CAPCUT_DRAFT_FOLDER

    # Combined test
    print("\nTest 2: Add audio")
    audio_result = add_audio_track(
        audio_url = "https://lf3-lv-music-tos.faceu.com/obj/tos-cn-ve-2774/oYACBQRCMlWBIrZipvQZhI5LAlUFYii0RwEPh",
        start=4,
        end=5,
        target_start=2,
        volume=0.8,
        speed=1.0,
        track_name="main_audio100",
        effect_type = "Big_House",
        effect_params = [50.0]
    )
    print(f"Audio addition result 1: {audio_result}")

    audio_result = add_audio_track(
        draft_id=audio_result['output']['draft_id'],
        audio_url = "https://lf3-lv-music-tos.faceu.com/obj/tos-cn-ve-2774/oYACBQRCMlWBIrZipvQZhI5LAlUFYii0RwEPh",
        start=4,
        end=5,
        target_start=4,
        volume=0.8,
        speed=1.0,
        track_name="main_audio100",
        effect_type = "Big_House",
        effect_params = [50.0]
    )
    print(f"Audio addition result 2: {audio_result}")

    audio_result = add_audio_track(
        draft_id=audio_result['output']['draft_id'],
        audio_url = "https://lf3-lv-music-tos.faceu.com/obj/tos-cn-ve-2774/oYACBQRCMlWBIrZipvQZhI5LAlUFYii0RwEPh",
        start=4,
        end=5,
        target_start=6,
        volume=0.8,
        speed=1.0,
        track_name="main_audio101",
        effect_type = "Big_House",
        effect_params = [50.0]
    )
    print(f"Audio addition result 3: {audio_result}")

    # Test case 1: Basic text addition
    text_result = add_text_impl(
        draft_folder=draft_folder,
        text="Test Text 1",
        draft_id=audio_result['output']['draft_id'],
        start=0,
        end=3,
        font="思源中宋",  # Use Source Han Serif font
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
        text="Vertical Text Test",
        start=3,
        end=6,
        font="云书法三行魏碑体",
        font_color="#00FF00",  # Green
        font_size=8.0,
        track_name="main_text",
        vertical=True,  # Enable vertical text
        transform_y=-0.5,
        outro_animation='Throw_Back'
    )
    print("Test case 2 (Vertical text) successful:", result2)

    print("Test completed")
    # Test adding image
    image_result = add_image_impl(
        draft_id=result2['output']['draft_id'],  # Replace with actual draft ID
        image_url="https://cdn.wanx.aliyuncs.com/wanx/1719234057367822001/text_to_image_v2/d6e33c84d7554146a25b1093b012838b_0.png?x-oss-process=image/resize,w_500/watermark,image_aW1nL3dhdGVyMjAyNDExMjkwLnBuZz94LW9zcy1wcm9jZXNzPWltYWdlL3Jlc2l6ZSxtX2ZpeGVkLHdfMTQ1LGhfMjU=,t_80,g_se,x_10,y_10/format,webp",  # Replace with actual image URL
        width=480,
        height=480,
        start = 0,
        end=5.0,  # Display for 5 seconds
        transform_y=0.7,
        scale_x=2.0,
        scale_y=1.0,
        transform_x=0,
        track_name="main"
    )
    print("Image added successfully!")


    # Test adding image
    image_result = add_image_impl(
        draft_id=result2['output']['draft_id'],  # Replace with actual draft ID
        image_url="http://gips0.baidu.com/it/u=3602773692,1512483864&fm=3028&app=3028&f=JPEG&fmt=auto?w=960&h=1280",  # Replace with actual image URL
        width=480,
        height=480,
        start = 0,
        end=5.0,  # Display for 5 seconds
        transform_y=0.7,
        scale_x=2.0,
        scale_y=1.0,
        transform_x=0,
        track_name="main_2"
    )
    print("Image added successfully!")

    image_result = add_image_impl(
        draft_id=image_result['output']['draft_id'],  # Replace with actual draft ID
        image_url="https://cdn.wanx.aliyuncs.com/wanx/1719234057367822001/text_to_image_v2/d6e33c84d7554146a25b1093b012838b_0.png?x-oss-process=image/resize,w_500/watermark,image_aW1nL3dhdGVyMjAyNDExMjkwLnBuZz94LW9zcy1wcm9jZXNzPWltYWdlL3Jlc2l6ZSxtX2ZpeGVkLHdfMTQ1LGhfMjU=,t_80,g_se,x_10,y_10/format,webp",  # Replace with actual image URL
        width=480,
        height=480,
        start = 5,
        end=10.0,  # Display for 5 seconds
        transform_y=0.7,
        scale_x=2.0,
        scale_y=1.0,
        transform_x=0,
        track_name="main"
    )
    print("Image 2 added successfully!")

    # Test adding video keyframe
    print("\nTest: Add video keyframe")
    keyframe_result = add_video_keyframe_impl(
        draft_id=image_result['output']['draft_id'],  # Use existing draft ID
        track_name="main",
        property_type="position_y",  # Test opacity
        time=1.5,  # Add keyframe at 3.5 seconds
        value="0.2"  # Move 300px
    )
    print(f"Keyframe addition result: {keyframe_result}")

    print("\nTest: Add video keyframe")
    keyframe_result = add_video_keyframe_impl(
        draft_id=image_result['output']['draft_id'],  # Use existing draft ID
        track_name="main",
        property_type="position_y",  # Test opacity
        time=3.5,  # Add keyframe at 3.5 seconds
        value="0.4"  # Move 300px
    )
    print(f"Keyframe addition result: {keyframe_result}")

    query_draft_status_impl_polling(keyframe_result['output']['draft_id'])
    save_draft_impl(keyframe_result['output']['draft_id'], draft_folder)

def test_video_track01():
    """Test adding video track"""
    draft_folder = CAPCUT_DRAFT_FOLDER
    video_url = "https://cdn.wanx.aliyuncs.com/wanx/1719234057367822001/text_to_video/092faf3c94244973ab752ee1280ba76f.mp4?spm=5176.29623064.0.0.41ed26d6cBOhV3&file=092faf3c94244973ab752ee1280ba76f.mp4" # Replace with actual video URL

    print("\nTest: Add video track")
    video_result = add_video_impl(
        video_url=video_url,
        width=1920,
        height=1080,
        start=0,
        end=5.0, # Cut the first 5 seconds of the video
        target_start=0,
        track_name="main_video_track"
    )
    print(f"Video track addition result: {video_result}")

    if video_result and 'output' in video_result and 'draft_id' in video_result['output']:
        draft_id = video_result['output']['draft_id']
        print(f"Save draft: {save_draft_impl(draft_id, draft_folder)}")
    else:
        print("Unable to get draft ID, skipping save operation.")


def test_video_track02():
    """Test adding video tracks in a loop"""
    draft_folder = CAPCUT_DRAFT_FOLDER
    video_url = "https://cdn.wanx.aliyuncs.com/wanx/1719234057367822001/text_to_video/092faf3c94244973ab752ee1280ba76f.mp4?spm=5176.29623064.0.0.41ed26d6cBOhV3&file=092faf3c94244973ab752ee1280ba76f.mp4" # Replace with actual video URL
    draft_id = None  # Initialize draft_id

    for i in range(5):
        target_start = i * 5  # Increment by 5 seconds each time

        video_result = add_video_impl(
            draft_id=draft_id,  # Pass in draft_id
            video_url=video_url,
            width=1920,
            height=1080,
            start=0,
            end=5.0, # Cut the first 5 seconds of the video
            target_start=target_start,
            track_name="main_video_track"
        )
        draft_id = video_result['output']['draft_id']  # Update draft_id
        print(f"Video addition result {i+1}: {video_result}")

    # Finally save and upload the draft
    save_result = save_draft_impl(draft_id, draft_folder)
    print(f"Draft save result: {save_result}")


def test_video_track03():
    """Test adding videos to different tracks"""
    draft_folder = CAPCUT_DRAFT_FOLDER
    video_url = "https://cdn.wanx.aliyuncs.com/wanx/1719234057367822001/text_to_video/092faf3c94244973ab752ee1280ba76f.mp4?spm=5176.29623064.0.0.41ed26d6cBOhV3&file=092faf3c94244973ab752ee1280ba76f.mp4" # Replace with actual video URL
    draft_id = None  # Initialize draft_id

    # Add video to the first track
    video_result = add_video_impl(
        draft_id=draft_id,  # Pass in draft_id
        video_url=video_url,
        width=1920,
        height=1080,
        start=0,
        end=5.0, # Cut the first 5 seconds of the video
        target_start=0,
        track_name="main_video_track"
    )
    draft_id = video_result['output']['draft_id']  # Update draft_id
    print(f"First video addition result: {video_result}")

    # Add video to the second track
    video_result = add_video_impl(
        draft_id=draft_id,  # Use previous draft_id
        video_url=video_url,
        width=1920,
        height=1080,
        start=0,
        end=5.0, # Cut the first 5 seconds of the video
        target_start=0,
        track_name="main_video_track_2",  # Use different track name
        speed=1.0,  # Change playback speed
        scale_x=0.5,  # Reduce video width
        transform_y=0.5  # Position video at bottom of screen
    )
    draft_id = video_result['output']['draft_id']  # Update draft_id
    print(f"Second video addition result: {video_result}")

    # Third time add video to another track
    video_result = add_video_impl(
        draft_id=draft_id,  # Use previous draft_id
        video_url=video_url,
        width=1920,
        height=1080,
        start=0,
        end=5.0, # Cut the first 5 seconds of the video
        target_start=0,
        track_name="main_video_track_3",  # Use third track
        speed=1.5,  # Faster playback speed
        scale_x=0.3,  # Smaller video width
        transform_y=-0.5  # Position video at top of screen
    )
    draft_id = video_result['output']['draft_id']  # Update draft_id
    print(f"Third video addition result: {video_result}")

    # Finally save and upload the draft
    save_result = save_draft_impl(draft_id, draft_folder)
    print(f"Draft save result: {save_result}")

def test_video_track04():
    """Test adding video track"""
    draft_folder = CAPCUT_DRAFT_FOLDER
    video_url = "https://cdn.wanx.aliyuncs.com/wanx/1719234057367822001/text_to_video/092faf3c94244973ab752ee1280ba76f.mp4?spm=5176.29623064.0.0.41ed26d6cBOhV3&file=092faf3c94244973ab752ee1280ba76f.mp4" # Replace with actual video URL

    print("\nTest: Add video track")
    video_result = add_video_impl(
        video_url='https://p26-bot-workflow-sign.byteimg.com/tos-cn-i-mdko3gqilj/07bf6797a1834d75beb05c63293af204.mp4~tplv-mdko3gqilj-image.image?rk3s=81d4c505&x-expires=1782141919&x-signature=2ETX83Swh%2FwKzHeWB%2F9oGq9vqt4%3D&x-wf-file_name=output-997160b5.mp4'
    )
    print(f"Video track addition result: {video_result}")

    print("\nTest: Add video track")
    video_result = add_video_impl(
        video_url='https://cdn.wanx.aliyuncs.com/wanx/1719234057367822001/text_to_video/092faf3c94244973ab752ee1280ba76f.mp4?spm=5176.29623064.0.0.41ed26d6cBOhV3&file=092faf3c94244973ab752ee1280ba76f.mp4',
        draft_id=video_result['output']['draft_id'],  # Use existing draft ID
        target_start=19.84
    )
    print(f"Video track addition result: {video_result}")
    if video_result and 'output' in video_result and 'draft_id' in video_result['output']:
        draft_id = video_result['output']['draft_id']
        print(f"Save draft: {save_draft_impl(draft_id, draft_folder)}")
    else:
        print("Unable to get draft ID, skipping save operation.")

def test_video_track05():
    """测试添加视频轨道"""
    draft_folder = CAPCUT_DRAFT_FOLDER

    video_url = "https://cdn.wanx.aliyuncs.com/wanx/1719234057367822001/text_to_video/092faf3c94244973ab752ee1280ba76f.mp4?spm=5176.29623064.0.0.41ed26d6cBOhV3&file=092faf3c94244973ab752ee1280ba76f.mp4" # 替换为实际视频URL

    print("\n测试：添加视频轨道")
    video_result = add_video_impl(
        video_url='https://p26-bot-workflow-sign.byteimg.com/tos-cn-i-mdko3gqilj/07bf6797a1834d75beb05c63293af204.mp4~tplv-mdko3gqilj-image.image?rk3s=81d4c505&x-expires=1782141919&x-signature=2ETX83Swh%2FwKzHeWB%2F9oGq9vqt4%3D&x-wf-file_name=output-997160b5.mp4',
        background_blur=2,
        width=1920,
        height=1080
    )

    print(f"视频轨道添加结果: {video_result}")
    if video_result and 'output' in video_result and 'draft_id' in video_result['output']:
        draft_id = video_result['output']['draft_id']
        print(f"保存草稿: {save_draft_impl(draft_id, draft_folder)}")
    else:
        print("无法获取草稿ID，跳过保存操作。")

def test_keyframe():
    """Test adding keyframes"""
    draft_folder = CAPCUT_DRAFT_FOLDER
    draft_id = None  # Initialize draft_id

    print("\nTest: Add basic video track")
    video_result = add_video_impl(
        video_url="https://cdn.wanx.aliyuncs.com/wanx/1719234057367822001/text_to_video/092faf3c94244973ab752ee1280ba76f.mp4?spm=5176.29623064.0.0.41ed26d6cBOhV3&file=092faf3c94244973ab752ee1280ba76f.mp4",
        width=1920,
        height=1080,
        start=0,
        end=10.0,
        target_start=0,
        track_name="main_video_track"
    )
    print("Video addition result:", video_result)

    if video_result.get('success') and video_result.get('output'):
        draft_id = video_result['output']['draft_id']
        print("Using existing draft_id:", draft_id)
    else:
        print("Unable to get draft ID, terminating test.")
        return

    print("\nTest: Add opacity keyframe")
    keyframe_result = add_video_keyframe_impl(
        draft_id=draft_id,
        track_name="main_video_track",
        property_type="alpha",
        time=2.0,
        value="1.0"
    )
    print("Opacity keyframe addition result:", keyframe_result)

    print("\nTest: Add position Y keyframe")
    keyframe_result = add_video_keyframe_impl(
        draft_id=draft_id,
        track_name="main_video_track",
        property_type="position_y",
        time=2.0,
        value="0.5"
    )
    print("Position Y keyframe addition result:", keyframe_result)

    print("\nTest: Add scale X keyframe")
    keyframe_result = add_video_keyframe_impl(
        draft_id=draft_id,
        track_name="main_video_track",
        property_type="position_y",
        time=4.0,
        value="-0.5"
    )
    print("Scale X keyframe addition result:", keyframe_result)

    print("\nFinal draft save")
    save_result = save_draft_impl(draft_id, draft_folder)
    print(f"Draft save result: {save_result}")

def test_keyframe_02():
    """Test adding keyframes - Batch adding to implement fade-in and zoom bounce effects"""
    draft_folder = CAPCUT_DRAFT_FOLDER
    draft_id = None  # Initialize draft_id

    print("\nTest: Adding basic video track")
    video_result = add_video_impl(
        video_url="https://cdn.wanx.aliyuncs.com/wanx/1719234057367822001/text_to_video/092faf3c94244973ab752ee1280ba76f.mp4?spm=5176.29623064.0.0.41ed26d6cBOhV3&file=092faf3c94244973ab752ee1280ba76f.mp4",
        width=1920,
        height=1080,
        start=0,
        end=10.0,
        target_start=0,
        track_name="main_video_track"
    )
    print("Video adding result:", video_result)

    if video_result.get('success') and video_result.get('output'):
        draft_id = video_result['output']['draft_id']
        print("Using existing draft_id:", draft_id)
    else:
        print("Unable to get draft ID, terminating test.")
        return

    print("\nTest: Batch adding opacity keyframes - Implementing fade-in effect")
    # Add opacity keyframes to implement fade-in effect from invisible to visible
    alpha_keyframe_result = add_video_keyframe_impl(
        draft_id=draft_id,
        track_name="main_video_track",
        property_types=["alpha", "alpha", "alpha", "alpha"],
        times=[0.0, 1.0, 2.0, 3.0],
        values=["0.0", "0.3", "0.7", "1.0"]
    )
    print("Opacity keyframe batch adding result:", alpha_keyframe_result)

    print("\nTest: Batch adding scale keyframes - Implementing zoom bounce effect")
    # Add uniform scale keyframes to implement zoom bounce effect
    scale_keyframe_result = add_video_keyframe_impl(
        draft_id=draft_id,
        track_name="main_video_track",
        property_types=["uniform_scale", "uniform_scale", "uniform_scale", "uniform_scale", "uniform_scale"],
        times=[0.0, 1.5, 3.0, 4.5, 6.0],
        values=["0.8", "1.3", "1.0", "1.2", "1.0"]
    )
    print("Scale keyframe batch adding result:", scale_keyframe_result)

    print("\nTest: Batch adding position Y keyframes - Implementing up and down floating effect")
    # Add position Y keyframes to implement up and down floating effect
    position_y_keyframe_result = add_video_keyframe_impl(
        draft_id=draft_id,
        track_name="main_video_track",
        property_types=["position_y", "position_y", "position_y", "position_y"],
        times=[2.0, 3.5, 5.0, 6.5],
        values=["0.0", "0.2", "-0.2", "0.0"]
    )
    print("Position Y keyframe batch adding result:", position_y_keyframe_result)

    print("\nFinal draft saving")
    save_result = save_draft_impl(draft_id, draft_folder)
    print(f"Draft saving result: {save_result}")

def test_video_01():
    """Test adding single video with transform and speed parameters"""
    # Set draft folder path for saving
    draft_folder = CAPCUT_DRAFT_FOLDER

    print("\nTest: Adding video")
    video_result = add_video_impl(
        video_url="https://cdn.wanx.aliyuncs.com/wanx/1719234057367822001/text_to_video/092faf3c94244973ab752ee1280ba76f.mp4?spm=5176.29623064.0.0.41ed26d6cBOhV3&file=092faf3c94244973ab752ee1280ba76f.mp4", # Replace with actual video URL
        start=0,
        end=5,
        width=1920,
        height=1080,
        track_name="main_video",
        transform_y=0.1,
        scale_x=0.8,
        scale_y=0.8,
        transform_x=0.1,
        speed=1.2,
        target_start=0,
        relative_index=0
    )
    print(f"Video adding result: {video_result}")

    # Save draft
    if video_result.get('success') and video_result.get('output'):
        query_draft_status_impl_polling(video_result['output']['draft_id'])
        save_draft_impl(video_result['output']['draft_id'], draft_folder)

def test_video_02():
    """Test adding multiple videos with different resolutions to the same draft"""
    # Set draft folder path for saving
    draft_folder = CAPCUT_DRAFT_FOLDER

    print("\nTest: Adding video")
    video_result = add_video_impl(
        video_url="https://cdn.wanx.aliyuncs.com/wanx/1719234057367822001/text_to_video/092faf3c94244973ab752ee1280ba76f.mp4?spm=5176.29623064.0.0.41ed26d6cBOhV3&file=092faf3c94244973ab752ee1280ba76f.mp4", # Replace with actual video URL
        start=0,
        end=5,
        width=1920,
        height=1080,
        track_name="main_video",
        transform_y=0.1,
        scale_x=0.8,
        scale_y=0.8,
        transform_x=0.1,
        speed=1.2,
        target_start=0,
        relative_index=0
    )
    print(f"Video adding result: {video_result}")

    video_result = add_video_impl(
        video_url="https://videos.pexels.com/video-files/3129769/3129769-hd_1280_720_30fps.mp4", # Replace with actual video URL
        draft_id=video_result['output']['draft_id'],
        start=0,
        end=5,
        width=1920,
        height=1080,
        track_name="main_video_2",
        transform_y=0.1,
        scale_x=0.8,
        scale_y=0.8,
        transform_x=0.1,
        speed=1.2,
        target_start=0,
        relative_index=0
    )
    video_result = add_video_impl(
        video_url="https://videos.pexels.com/video-files/3129769/3129769-uhd_3840_2160_30fps.mp4", # Replace with actual video URL
        draft_id=video_result['output']['draft_id'],
        start=0,
        end=5,
        width=1920,
        height=1080,
        track_name="main_video_3",
        transform_y=0.1,
        scale_x=0.8,
        scale_y=0.8,
        transform_x=0.1,
        speed=1.2,
        target_start=0,
        relative_index=0
    )
    video_result = add_video_impl(
        video_url="https://videos.pexels.com/video-files/3129769/3129769-sd_426_240_30fps.mp4", # Replace with actual video URL
        draft_id=video_result['output']['draft_id'],
        start=0,
        end=5,
        width=1920,
        height=1080,
        track_name="main_video_4",
        transform_y=0.1,
        scale_x=0.8,
        scale_y=0.8,
        transform_x=0.1,
        speed=1.2,
        target_start=0,
        relative_index=0
    )
    video_result = add_video_impl(
        video_url="https://videos.pexels.com/video-files/3129769/3129769-sd_640_360_30fps.mp4", # Replace with actual video URL
        draft_id=video_result['output']['draft_id'],
        start=0,
        end=5,
        width=1920,
        height=1080,
        track_name="main_video_5",
        transform_y=0.1,
        scale_x=0.8,
        scale_y=0.8,
        transform_x=0.1,
        speed=1.2,
        target_start=0,
        relative_index=0
    )
    video_result = add_video_impl(
        video_url="https://videos.pexels.com/video-files/3129769/3129769-uhd_2560_1440_30fps.mp4", # Replace with actual video URL
        draft_id=video_result['output']['draft_id'],
        start=0,
        end=5,
        width=1920,
        height=1080,
        track_name="main_video_6",
        transform_y=0.1,
        scale_x=0.8,
        scale_y=0.8,
        transform_x=0.1,
        speed=1.2,
        target_start=0,
        relative_index=0
    )

    if video_result.get('success') and video_result.get('output'):
        print(json.loads(query_script_impl(video_result['output']['draft_id'])['output']))
        # query_draft_status_impl_polling(video_result['output']['draft_id'])
        # save_draft_impl(video_result['output']['draft_id'], draft_folder)

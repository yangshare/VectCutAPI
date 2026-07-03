"""Image demo — 迁自 example.py（阶段5 拆分）。"""
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from _client import make_request, CAPCUT_DRAFT_FOLDER


def add_image_impl(image_url, start, end, width=None, height=None, track_name="image_main", draft_id=None,
                  transform_x=0, transform_y=0, scale_x=1.0, scale_y=1.0, transition=None, transition_duration=None,
                  mask_type=None, mask_center_x=0.0, mask_center_y=0.0, mask_size=0.5,
                  mask_rotation=0.0, mask_feather=0.0, mask_invert=False,
                  mask_rect_width=None, mask_round_corner=None, background_blur=None):
    """API call to add image"""
    data = {
        "image_url": image_url,
        "width": width,
        "height": height,
        "start": start,
        "end": end,
        "track_name": track_name,
        "transform_x": transform_x,
        "transform_y": transform_y,
        "scale_x": scale_x,
        "scale_y": scale_y,
        "transition": transition,
        "transition_duration": transition_duration or 0.5,  # Default transition duration is 0.5 seconds
        # Add mask-related parameters
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

    if draft_id:
        data["draft_id"] = draft_id
    if background_blur:
        data["background_blur"] = background_blur

    return make_request("add_image", data)

def generate_image_impl(prompt, width, height, start, end, track_name, draft_id=None,
                  transform_x=0, transform_y=0, scale_x=1.0, scale_y=1.0, transition=None, transition_duration=None):
    """API call to add image"""
    data = {
        "prompt": prompt,
        "width": width,
        "height": height,
        "start": start,
        "end": end,
        "track_name": track_name,
        "transform_x": transform_x,
        "transform_y": transform_y,
        "scale_x": scale_x,
        "scale_y": scale_y,
        "transition": transition,
        "transition_duration": transition_duration or 0.5  # Default transition duration is 0.5 seconds
    }

    if draft_id:
        data["draft_id"] = draft_id

    return make_request("generate_image", data)

def test_image01():
    """Test adding image"""
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
        track_name="main"
    )
    print(f"Image added successfully! {image_result['output']['draft_id']}")
    from draft_demo import save_draft_impl
    print(save_draft_impl(image_result['output']['draft_id'], draft_folder))


def test_image02():
    """Test adding multiple images"""
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
    from draft_demo import save_draft_impl
    print(save_draft_impl(image_result['output']['draft_id'], draft_folder))


def test_image03():
    """Test adding images to different tracks"""
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
        track_name="main_2"  # Use different track name
    )
    print(f"Image 3 added successfully! {image_result['output']['draft_id']}")
    from draft_demo import query_draft_status_impl_polling, save_draft_impl
    query_draft_status_impl_polling(image_result['output']['draft_id'])
    save_draft_impl(image_result['output']['draft_id'], draft_folder)

def test_image04():
    """Test adding image"""
    draft_folder = CAPCUT_DRAFT_FOLDER

    print("\nTest: Adding image 1")
    image_result = add_image_impl(
        image_url="https://cdn.wanx.aliyuncs.com/wanx/1719234057367822001/text_to_image_v2/d6e33c84d7554146a25b1093b012838b_0.png?x-oss-process=image/resize,w_500/watermark,image_aW1nL3dhdGVyMjAyNDExMjkwLnBuZz94LW9zcy1wcm9jZXNzPWltYWdlL3Jlc2l6ZSxtX2ZpeGVkLHdfMTQ1LGhfMjU=,t_80,g_se,x_10,y_10/format,webp",
        width=480,
        height=480,
        start=5.0,
        end=10.0,
        transform_y=0.7,
        scale_x=2.0,
        scale_y=1.0,
        transform_x=0,
        track_name="image_main"
    )
    print(f"Image added successfully! {image_result['output']['draft_id']}")
    from draft_demo import save_draft_impl
    print(save_draft_impl(image_result['output']['draft_id'], draft_folder))

def test_image05():
    """测试添加图片"""
    draft_folder = CAPCUT_DRAFT_FOLDER

    print("\n测试：添加图片1")
    image_result = add_image_impl(
        image_url="https://cdn.wanx.aliyuncs.com/wanx/1719234057367822001/text_to_image_v2/d6e33c84d7554146a25b1093b012838b_0.png?x-oss-process=image/resize,w_500/watermark,image_aW1nL3dhdGVyMjAyNDExMjkwLnBuZz94LW9zcy1wcm9jZXNzPWltYWdlL3Jlc2l6ZSxtX2ZpeGVkLHdfMTQ1LGhfMjU=,t_80,g_se,x_10,y_10/format,webp",
        width=1920,
        height=1080,
        start=5.0,
        end=10.0,
        track_name="image_main",
        background_blur=3
    )
    print(f"添加图片成功！{image_result['output']['draft_id']}")
    from draft_demo import save_draft_impl
    print(save_draft_impl(image_result['output']['draft_id'], draft_folder))

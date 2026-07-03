from flask import Flask, request, jsonify
from add_text_impl import add_text_impl
from add_subtitle_impl import add_subtitle_impl
from add_image_impl import add_image_impl
from add_video_keyframe_impl import add_video_keyframe_impl
from add_effect_impl import add_effect_impl
from add_sticker_impl import add_sticker_impl
from util import hex_to_rgb
from pyJianYingDraft.text_segment import TextStyleRange, Text_style, Text_border

from settings.local import PORT

app = Flask(__name__)

# —— 阶段2：draft / video / audio 三大业务路由收敛为声明式 Blueprint ——
from vectcut.features.draft.flask_router import bp as draft_bp
from vectcut.features.video.flask_router import bp as video_bp
from vectcut.features.audio.flask_router import bp as audio_bp
app.register_blueprint(draft_bp)
app.register_blueprint(video_bp)
app.register_blueprint(audio_bp)

@app.route('/add_subtitle', methods=['POST'])
def add_subtitle():
    data = request.get_json()

    # Get required parameters
    srt = data.get('srt')  # Subtitle content or URL
    draft_id = data.get('draft_id')
    time_offset = data.get('time_offset', 0.0)  # Default 0 seconds

    # Font style parameters
    font = data.get('font', "思源粗宋")
    font_size = data.get('font_size', 5.0)  # Default size 5.0
    bold = data.get('bold', False)  # Default not bold
    italic = data.get('italic', False)  # Default not italic
    underline = data.get('underline', False)  # Default no underline
    font_color = data.get('font_color', '#FFFFFF')  # Default white
    vertical = data.get('vertical', False)  # New: whether to display vertically, default False
    alpha = data.get('alpha', 1)  # New: transparency, default 1
    # Border parameters
    border_alpha = data.get('border_alpha', 1.0)
    border_color = data.get('border_color', '#000000')
    border_width = data.get('border_width', 0.0)

    # Background parameters
    background_color = data.get('background_color', '#000000')
    background_style = data.get('background_style', 0)
    background_alpha = data.get('background_alpha', 0.0)

    # Image adjustment parameters
    transform_x = data.get('transform_x', 0.0)  # Default 0
    transform_y = data.get('transform_y', -0.8)  # Default -0.8
    scale_x = data.get('scale_x', 1.0)  # Default 1.0
    scale_y = data.get('scale_y', 1.0)  # Default 1.0
    rotation = data.get('rotation', 0.0)  # Default 0.0
    track_name = data.get('track_name', 'subtitle')  # Default track name is 'subtitle'
    width = data.get('width', 1080)
    height = data.get('height', 1920)

    result = {
        "success": False,
        "output": "",
        "error": ""
    }

    # Validate required parameters
    if not srt:
        error_message = "Hi, the required parameters 'srt' are missing."
        result["error"] = error_message
        return jsonify(result)

    try:
        # Call add_subtitle_impl method
        draft_result = add_subtitle_impl(
            srt_path=srt,
            draft_id=draft_id,
            track_name=track_name,
            time_offset=time_offset,
            # Font style parameters
            font = font,
            font_size=font_size,
            bold=bold,
            italic=italic,
            underline=underline,
            font_color=font_color,
            vertical=vertical,  # New: pass vertical parameter
            alpha=alpha,  # New: pass alpha parameter
            border_alpha=border_alpha,
            border_color=border_color,
            border_width=border_width,
            background_color=background_color,
            background_style=background_style,
            background_alpha=background_alpha,
            # Image adjustment parameters
            transform_x=transform_x,
            transform_y=transform_y,
            scale_x=scale_x,
            scale_y=scale_y,
            rotation=rotation,
            width=width,
            height=height
        )

        result["success"] = True
        result["output"] = draft_result
        return jsonify(result)

    except Exception as e:
        error_message = f"Error occurred while processing subtitle: {str(e)}."
        result["error"] = error_message
        return jsonify(result)

@app.route('/add_text', methods=['POST'])
def add_text():
    data = request.get_json()

    # Get required parameters
    text = data.get('text')
    start = data.get('start', 0)
    end = data.get('end', 5)
    draft_id = data.get('draft_id')
    transform_y = data.get('transform_y', 0)
    transform_x = data.get('transform_x', 0)
    font = data.get('font', "文轩体")
    font_color = data.get('color', data.get('font_color', "#FF0000"))  # Support both 'color' and 'font_color'
    font_size = data.get('size', data.get('font_size', 8.0))  # Support both 'size' and 'font_size'
    track_name = data.get('track_name', "text_main")
    vertical = data.get('vertical', False)
    font_alpha = data.get('alpha', data.get('font_alpha', 1.0))  # Support both 'alpha' and 'font_alpha'
    outro_animation = data.get('outro_animation', None)
    outro_duration = data.get('outro_duration', 0.5)
    width = data.get('width', 1080)
    height = data.get('height', 1920)

    # New fixed width and height parameters
    fixed_width = data.get('fixed_width', -1)
    fixed_height = data.get('fixed_height', -1)

    # Border parameters
    border_alpha = data.get('border_alpha', 1.0)
    border_color = data.get('border_color', "#000000")
    border_width = data.get('border_width', 0.0)

    # Background parameters
    background_color = data.get('background_color', "#000000")
    background_style = data.get('background_style', 0)
    background_alpha = data.get('background_alpha', 0.0)
    background_round_radius = data.get('background_round_radius', 0.0)
    background_height = data.get('background_height', 0.14)  # Background height, range 0.0-1.0
    background_width = data.get('background_width', 0.14)  # Background width, range 0.0-1.0
    background_horizontal_offset = data.get('background_horizontal_offset', 0.5)  # Background horizontal offset, range 0.0-1.0
    background_vertical_offset = data.get('background_vertical_offset', 0.5)  # Background vertical offset, range 0.0-1.0

    # Shadow parameters
    shadow_enabled = data.get('shadow_enabled', False)  # Whether to enable shadow
    shadow_alpha = data.get('shadow_alpha', 0.9)  # Shadow transparency, range 0.0-1.0
    shadow_angle = data.get('shadow_angle', -45.0)  # Shadow angle, range -180.0-180.0
    shadow_color = data.get('shadow_color', "#000000")  # Shadow color
    shadow_distance = data.get('shadow_distance', 5.0)  # Shadow distance
    shadow_smoothing = data.get('shadow_smoothing', 0.15)  # Shadow smoothing, range 0.0-1.0

    # Bubble and decorative text effects
    bubble_effect_id = data.get('bubble_effect_id')
    bubble_resource_id = data.get('bubble_resource_id')
    effect_effect_id = data.get('effect_effect_id')

    # Entrance animation
    intro_animation = data.get('intro_animation')
    intro_duration = data.get('intro_duration', 0.5)

    # Exit animation
    outro_animation = data.get('outro_animation')
    outro_duration = data.get('outro_duration', 0.5)

    # Multi-style text parameters
    text_styles_data = data.get('text_styles', [])
    text_styles = None
    if text_styles_data:
        text_styles = []
        for style_data in text_styles_data:
            # Get style range
            start_pos = style_data.get('start', 0)
            end_pos = style_data.get('end', 0)

            # Create text style
            style = Text_style(
                size=style_data.get('style',{}).get('size', font_size),
                bold=style_data.get('style',{}).get('bold', False),
                italic=style_data.get('style',{}).get('italic', False),
                underline=style_data.get('style',{}).get('underline', False),
                color=hex_to_rgb(style_data.get('style',{}).get('color', font_color)),
                alpha=style_data.get('style',{}).get('alpha', font_alpha),
                align=style_data.get('style',{}).get('align', 1),
                vertical=style_data.get('style',{}).get('vertical', vertical),
                letter_spacing=style_data.get('style',{}).get('letter_spacing', 0),
                line_spacing=style_data.get('style',{}).get('line_spacing', 0)
            )

            # Create border (if any)
            border = None
            if style_data.get('border',{}).get('width', 0) > 0:
                border = Text_border(
                    alpha=style_data.get('border',{}).get('alpha', border_alpha),
                    color=hex_to_rgb(style_data.get('border',{}).get('color', border_color)),
                    width=style_data.get('border',{}).get('width', border_width)
                )

            # Create style range object
            style_range = TextStyleRange(
                start=start_pos,
                end=end_pos,
                style=style,
                border=border,
                font_str=style_data.get('font', font)
            )

            text_styles.append(style_range)

    result = {
        "success": False,
        "output": "",
        "error": ""
    }

    # Validate required parameters
    if not text or start is None or end is None:
        error_message = "Hi, the required parameters 'text', 'start' or 'end' are missing. "
        result["error"] = error_message
        return jsonify(result)

    try:

        # Call add_text_impl method
        draft_result = add_text_impl(
            text=text,
            start=start,
            end=end,
            draft_id=draft_id,
            transform_y=transform_y,
            transform_x=transform_x,
            font=font,
            font_color=font_color,
            font_size=font_size,
            track_name=track_name,
            vertical=vertical,
            font_alpha=font_alpha,
            border_alpha=border_alpha,
            border_color=border_color,
            border_width=border_width,
            background_color=background_color,
            background_style=background_style,
            background_alpha=background_alpha,
            background_round_radius=background_round_radius,
            background_height=background_height,
            background_width=background_width,
            background_horizontal_offset=background_horizontal_offset,
            background_vertical_offset=background_vertical_offset,
            shadow_enabled=shadow_enabled,
            shadow_alpha=shadow_alpha,
            shadow_angle=shadow_angle,
            shadow_color=shadow_color,
            shadow_distance=shadow_distance,
            shadow_smoothing=shadow_smoothing,
            bubble_effect_id=bubble_effect_id,
            bubble_resource_id=bubble_resource_id,
            effect_effect_id=effect_effect_id,
            intro_animation=intro_animation,
            intro_duration=intro_duration,
            outro_animation=outro_animation,
            outro_duration=outro_duration,
            width=width,
            height=height,
            fixed_width=fixed_width,
            fixed_height=fixed_height,
            text_styles=text_styles
        )

        result["success"] = True
        result["output"] = draft_result
        return jsonify(result)

    except Exception as e:
        error_message = f"Error occurred while processing text: {str(e)}. You can click the link below for help: "
        result["error"] = error_message
        return jsonify(result)

@app.route('/add_image', methods=['POST'])
def add_image():
    data = request.get_json()

    # Get required parameters
    draft_folder = data.get('draft_folder')
    image_url = data.get('image_url')
    width = data.get('width', 1080)
    height = data.get('height', 1920)
    start = data.get('start', 0)
    end = data.get('end', 3.0)  # Default display 3 seconds
    draft_id = data.get('draft_id')
    transform_y = data.get('transform_y', 0)
    scale_x = data.get('scale_x', 1)
    scale_y = data.get('scale_y', 1)
    transform_x = data.get('transform_x', 0)
    track_name = data.get('track_name', "image_main")  # Default track name
    relative_index = data.get('relative_index', 0)  # New track rendering order index parameter
    animation = data.get('animation')  # Entrance animation parameter (backward compatibility)
    animation_duration = data.get('animation_duration', 0.5)  # Entrance animation duration
    intro_animation = data.get('intro_animation')  # New entrance animation parameter, higher priority than animation
    intro_animation_duration = data.get('intro_animation_duration', 0.5)
    outro_animation = data.get('outro_animation')  # New exit animation parameter
    outro_animation_duration = data.get('outro_animation_duration', 0.5)  # New exit animation duration
    combo_animation = data.get('combo_animation')  # New combo animation parameter
    combo_animation_duration = data.get('combo_animation_duration', 0.5)  # New combo animation duration
    transition = data.get('transition')  # Transition type parameter
    transition_duration = data.get('transition_duration', 0.5)  # Transition duration parameter, default 0.5 seconds

    # New mask related parameters
    mask_type = data.get('mask_type')  # Mask type
    mask_center_x = data.get('mask_center_x', 0.0)  # Mask center X coordinate
    mask_center_y = data.get('mask_center_y', 0.0)  # Mask center Y coordinate
    mask_size = data.get('mask_size', 0.5)  # Mask main size, relative to canvas height
    mask_rotation = data.get('mask_rotation', 0.0)  # Mask rotation angle
    mask_feather = data.get('mask_feather', 0.0)  # Mask feather parameter
    mask_invert = data.get('mask_invert', False)  # Whether to invert mask
    mask_rect_width = data.get('mask_rect_width')  # Rectangle mask width
    mask_round_corner = data.get('mask_round_corner')  # Rectangle mask rounded corner

    background_blur = data.get('background_blur')  # Background blur level, optional values: 1 (light), 2 (medium), 3 (strong), 4 (maximum), default None (no background blur)

    result = {
        "success": False,
        "output": "",
        "error": ""
    }

    # Validate required parameters
    if not image_url:
        error_message = "Hi, the required parameters 'image_url' are missing."
        result["error"] = error_message
        return jsonify(result)

    try:
        draft_result = add_image_impl(
            draft_folder=draft_folder,
            image_url=image_url,
            width=width,
            height=height,
            start=start,
            end=end,
            draft_id=draft_id,
            transform_y=transform_y,
            scale_x=scale_x,
            scale_y=scale_y,
            transform_x=transform_x,
            track_name=track_name,
            relative_index=relative_index,  # Pass track rendering order index parameter
            animation=animation,  # Pass entrance animation parameter (backward compatibility)
            animation_duration=animation_duration,  # Pass entrance animation duration
            intro_animation=intro_animation,  # Pass new entrance animation parameter
            intro_animation_duration=intro_animation_duration,
            outro_animation=outro_animation,  # Pass exit animation parameter
            outro_animation_duration=outro_animation_duration,  # Pass exit animation duration
            combo_animation=combo_animation,  # Pass combo animation parameter
            combo_animation_duration=combo_animation_duration,  # Pass combo animation duration
            transition=transition,  # Pass transition type parameter
            transition_duration=transition_duration,  # Pass transition duration parameter (seconds)
            # Pass mask related parameters
            mask_type=mask_type,
            mask_center_x=mask_center_x,
            mask_center_y=mask_center_y,
            mask_size=mask_size,
            mask_rotation=mask_rotation,
            mask_feather=mask_feather,
            mask_invert=mask_invert,
            mask_rect_width=mask_rect_width,
            mask_round_corner=mask_round_corner,
            background_blur=background_blur
        )

        result["success"] = True
        result["output"] = draft_result
        return jsonify(result)

    except Exception as e:
        error_message = f"Error occurred while processing image: {str(e)}."
        result["error"] = error_message
        return jsonify(result)

@app.route('/add_video_keyframe', methods=['POST'])
def add_video_keyframe():
    data = request.get_json()

    # Get required parameters
    draft_id = data.get('draft_id')
    track_name = data.get('track_name', 'video_main')  # Default main track

    # Single keyframe parameters (backward compatibility)
    property_type = data.get('property_type', 'alpha')  # Default opacity
    time = data.get('time', 0.0)  # Default 0 seconds
    value = data.get('value', '1.0')  # Default value 1.0

    # Batch keyframe parameters (new)
    property_types = data.get('property_types')  # Property type list
    times = data.get('times')  # Time list
    values = data.get('values')  # Value list

    result = {
        "success": False,
        "output": "",
        "error": ""
    }

    try:
        # Call add_video_keyframe_impl method
        draft_result = add_video_keyframe_impl(
            draft_id=draft_id,
            track_name=track_name,
            property_type=property_type,
            time=time,
            value=value,
            property_types=property_types,
            times=times,
            values=values
        )

        result["success"] = True
        result["output"] = draft_result
        return jsonify(result)

    except Exception as e:
        error_message = f"Error occurred while adding keyframe: {str(e)}."
        result["error"] = error_message
        return jsonify(result)

@app.route('/add_effect', methods=['POST'])
def add_effect():
    data = request.get_json()

    # Get required parameters
    effect_type = data.get('effect_type')  # Effect type name, will match from Video_scene_effect_type or Video_character_effect_type
    start = data.get('start', 0)  # Start time (seconds), default 0
    effect_category = data.get('effect_category', "scene") # Effect category, "scene" or "character", default "scene"
    end = data.get('end', 3.0)  # End time (seconds), default 3 seconds
    draft_id = data.get('draft_id')  # Draft ID, if None or corresponding zip file not found, create new draft
    track_name = data.get('track_name', "effect_01")  # Track name, can be omitted when there is only one effect track
    params = data.get('params')  # Effect parameter list, items not provided or None in parameter list use default values
    width = data.get('width', 1080)
    height = data.get('height', 1920)

    result = {
        "success": False,
        "output": "",
        "error": ""
    }

    # Validate required parameters
    if not effect_type:
        error_message = "Hi, the required parameters 'effect_type' are missing. Please add them and try again."
        result["error"] = error_message
        return jsonify(result)

    try:
        # Call add_effect_impl method
        draft_result = add_effect_impl(
            effect_type=effect_type,
            effect_category=effect_category,
            start=start,
            end=end,
            draft_id=draft_id,
            track_name=track_name,
            params=params,
            width=width,
            height=height
        )

        result["success"] = True
        result["output"] = draft_result
        return jsonify(result)

    except Exception as e:
        error_message = f"Error occurred while adding effect: {str(e)}. "
        result["error"] = error_message
        return jsonify(result)

@app.route('/add_sticker', methods=['POST'])
def add_sticker():
    data = request.get_json()
    # Get required parameters
    resource_id = data.get('sticker_id')
    start = data.get('start', 0)
    end = data.get('end', 5.0)  # Default display 5 seconds
    draft_id = data.get('draft_id')
    transform_y = data.get('transform_y', 0)
    transform_x = data.get('transform_x', 0)
    alpha = data.get('alpha', 1.0)
    flip_horizontal = data.get('flip_horizontal', False)
    flip_vertical = data.get('flip_vertical', False)
    rotation = data.get('rotation', 0.0)
    scale_x = data.get('scale_x', 1.0)
    scale_y = data.get('scale_y', 1.0)
    track_name = data.get('track_name', 'sticker_main')
    relative_index = data.get('relative_index', 0)
    width = data.get('width', 1080)
    height = data.get('height', 1920)

    result = {
        "success": False,
        "output": "",
        "error": ""
    }

    # Validate required parameters
    if not resource_id:
        error_message = "Hi, the required parameter 'sticker_id' is missing. Please add it and try again. "
        result["error"] = error_message
        return jsonify(result)

    try:
        # Call add_sticker_impl method
        draft_result = add_sticker_impl(
            resource_id=resource_id,
            start=start,
            end=end,
            draft_id=draft_id,
            transform_y=transform_y,
            transform_x=transform_x,
            alpha=alpha,
            flip_horizontal=flip_horizontal,
            flip_vertical=flip_vertical,
            rotation=rotation,
            scale_x=scale_x,
            scale_y=scale_y,
            track_name=track_name,
            relative_index=relative_index,
            width=width,
            height=height
        )

        result["success"] = True
        result["output"] = draft_result
        return jsonify(result)

    except Exception as e:
        error_message = f"Error occurred while adding sticker: {str(e)}. "
        result["error"] = error_message
        return jsonify(result)

# —— 元数据查询路由（阶段1 收敛为声明式 Blueprint，含 /metadata/{kind} 与 11 旧别名）——
from vectcut.features.metadata.flask_router import bp as metadata_bp
app.register_blueprint(metadata_bp)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)

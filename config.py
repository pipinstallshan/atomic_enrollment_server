
"""

List of formats:

{"type": "pip video over image", "video_path": "<video path>", "image_path": "<image_path>", "scale": range:0f-1f, "starting_position": "top left", "transition_positions": [(second_to_transition, "top right"), (60, "top left")], "pip_fade_in": <seconds>, "pip_fade_out": <seconds>}
{"type": "audio only over image", "video_path": "<video path>", "image_path": "<image_path>"}
{"type": "video", "video_path": "<video path>"}

Default setting:

The default setting is "skills program yes ads".
"""

all_configs = {
    "skills program yes ads": {
        "instructions": [
            {
                "type": "pip video over image",
                "video_path": "content/skills_program/general/blue_collar_pip_1.mp4",
                "image_path": "temp/website_screenshot_{}.png",
                "scale": 0.2,
                "starting_position": "top right",
                "pip_fade_in": 0,
                "pip_fade_out": 1.5,
                "transitions_enabled": True
            },
            {
                "type": "video",
                "video_path": "content/skills_program/general/blue_collar_fixed_1.mp4",
                "transitions_enabled": True
            },
            {
                "type": "audio only over image",
                "video_path": "content/skills_program/yes_ads/blue_collar_yes_ads_audio_only_1.mp4",
                "image_path": "temp/ads_screenshot_{}.png",
                "transitions_enabled": True
            },
            {
                "type": "video",
                "video_path": "content/skills_program/general/blue_collar_fixed_2.mp4",
                "transitions_enabled": True
            },
            {
                "type": "pip video over image",
                "video_path": "content/skills_program/general/blue_collar_pip_2.mp4",
                "image_path": "temp/website_screenshot_{}.png",
                "scale": 0.2,
                "starting_position": "top right",
                "pip_fade_in": 2,
                "pip_fade_out": 0,
                "transitions_enabled": True  # No fade-out to the next clip here
            }
        ],
        "resolution": (1920, 1080)
    },
    "money coaching yes ads": {
        "instructions": [
            {
                "type": "pip video over image",
                "video_path": "content/money_coaching/general/money_coaching_pip_1_1.mp4",
                "image_path": "temp/website_screenshot_{}.png",
                "scale": 0.15,
                "starting_position": "top right",
                "transitions_enabled": True
            },
            {
                "type": "pip video over image",
                "video_path": "content/money_coaching/yes_ads/money_coaching_pip_1_2.mp4",
                "image_path": "temp/ads_screenshot_{}.png",
                "scale": 0.15,
                "starting_position": "top right",
                "transitions_enabled": True
            },
            {
                "type": "pip video over image",
                "video_path": "content/money_coaching/general/money_coaching_pip_1_3.mp4",
                "image_path": "temp/website_screenshot_{}.png",
                "scale": 0.15,
                "starting_position": "top right",
                "transitions_enabled": False
            },
            {
                "type": "video",
                "video_path": "content/money_coaching/general/money_coaching_fixed_1.mp4",
                "transitions_enabled": False
            },
            {
                "type": "pip video over image",
                "video_path": "content/money_coaching/general/money_coaching_pip_2.mp4",
                "image_path": "temp/website_screenshot_{}.png",
                "scale": 0.15,
                "starting_position": "top right",
            },
            {
                "type": "video",
                "video_path": "content/money_coaching/general/money_coaching_fixed_2.mp4",
            },
            {
                "type": "pip video over image",
                "video_path": "content/money_coaching/general/money_coaching_pip_3.mp4",
                "image_path": "temp/website_screenshot_{}.png",
                "scale": 0.15,
                "starting_position": "top right",
            }
        ],
        "resolution": (1920, 1080)
    }
}

default_setting = "skills program yes ads"

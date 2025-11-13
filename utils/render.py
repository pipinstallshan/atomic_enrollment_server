from moviepy.editor import *
from moviepy.video.fx.all import resize
import config  # Import your config file
import os

def easein_easeout(t):
    """
    Provides an ease-in-ease-out transition for a given time t.

    Args:
      t: The normalized time value (between 0 and 1).

    Returns:
      The adjusted time value with ease-in-ease-out effect.
    """
    return 3 * t**2 - 2 * t**3

def calculate_position(position_str, video_width, video_height, pip_width, pip_height):
    """Calculates numerical position from string (e.g., 'top right')."""
    margin_x = 0.025 * video_height
    margin_y = 0.025 * video_height

    if position_str == "top left":
        return (margin_x, margin_y)
    elif position_str == "top right":
        return (video_width - pip_width - margin_x, margin_y)
    elif position_str == "bottom left":
        return (margin_x, video_height - pip_height - margin_y)
    elif position_str == "bottom right":
        return (video_width - pip_width - margin_x, video_height - pip_height - margin_y)
    else:
        raise ValueError(f"Invalid position string: {position_str}")


def process_pip_video_over_image(instruction, target_resolution):
    """Creates a PIP video over image segment with fade-in/out to transparency."""
    video_path = instruction["video_path"]
    image_path = instruction["image_path"]
    scale = instruction["scale"]
    starting_position_str = instruction["starting_position"]
    transition_positions = instruction.get("transition_positions")
    pip_fade_in = instruction.get("pip_fade_in", 0)
    pip_fade_out = instruction.get("pip_fade_out", 0)
    audio_fadeout = instruction.get("audio_fadeout", 0)

    try:
        background_clip = ImageClip(image_path).resize(target_resolution)
        pip_clip = VideoFileClip(video_path, has_mask=True)  # Ensure mask is handled
        pip_duration = pip_clip.duration

        # Calculate aspect-ratio preserving size
        pip_target_width = int(target_resolution[0] * scale)
        pip_target_height = int(pip_target_width * (pip_clip.h / pip_clip.w))
        pip_clip = pip_clip.resize((pip_target_width, pip_target_height))

        start_pos = calculate_position(
            starting_position_str,
            target_resolution[0],
            target_resolution[1],
            pip_clip.w,
            pip_clip.h,
        )
        pip_clip = pip_clip.set_position(start_pos)

        if transition_positions:
            # Handle transition positions (if needed)
            pass  # Your existing code for transitions

        # Apply fade-in and fade-out with transparency
        if pip_fade_in > 0:
            pip_clip = pip_clip.crossfadein(pip_fade_in)
        if pip_fade_out > 0:
            pip_clip = pip_clip.crossfadeout(pip_fade_out)
        if audio_fadeout > 0:
            pip_clip = pip_clip.audio_fadeout(audio_fadeout)

        final_clip = CompositeVideoClip(
            [background_clip.set_duration(pip_duration), pip_clip.set_duration(pip_duration)]
        )

        return final_clip

    except Exception as e:
        print(f"Error processing PIP video: {e}")
        return None

def process_video(instruction, target_resolution):
    """Creates a video segment."""
    video_path = instruction["video_path"]
    audio_fadeout = instruction.get("audio_fadeout", 0)

    try:
        clip = VideoFileClip(video_path).resize(target_resolution)

        if audio_fadeout > 0:
            clip = clip.audio_fadeout(audio_fadeout)

        return clip
    except Exception as e:
        print(f"Error processing video: {e}")
        return None

def process_audio_only_over_image(instruction, target_resolution):
    """Creates an audio-only-over-image segment."""
    video_path = instruction["video_path"]
    image_path = instruction["image_path"]
    audio_fadeout = instruction.get("audio_fadeout", 0)

    try:
        audio_clip = AudioFileClip(video_path)
        image_clip = ImageClip(image_path).resize(target_resolution).set_duration(audio_clip.duration)
        video_clip = image_clip.set_audio(audio_clip)
        
        if audio_fadeout > 0:
            video_clip = video_clip.audio_fadeout(audio_fadeout)

        return video_clip
    except Exception as e:
        print(f"Error processing audio over image: {e}")
        return None

def render_video(config_dict: dict, output_path: str):
    """Renders the video based on the given configuration."""

    instructions = config_dict["instructions"]
    target_resolution = config_dict["resolution"]
    clips = []

    for instruction in instructions:
        instruction_type = instruction["type"]

        if instruction_type == "pip video over image":
            clip = process_pip_video_over_image(instruction, target_resolution)
        elif instruction_type == "video":
            clip = process_video(instruction, target_resolution)
        elif instruction_type == "audio only over image":
            clip = process_audio_only_over_image(instruction, target_resolution)
        else:
            print(f"Warning: Unknown instruction type: {instruction_type}")
            clip = None

        if clip:
            if isinstance(clip, list):
                clips.extend(clip)
            else:
                clips.append(clip)

    final_video = concatenate_videoclips(clips)

    final_video.write_videofile(
        output_path, fps=24, codec="libx264", threads=1
    )


if __name__ == "__main__":
    render_video(config.all_configs[config.default_setting], "output/test.mp4")

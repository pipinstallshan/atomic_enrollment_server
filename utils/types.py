from typing import TypedDict, Literal, List, Tuple
from enum import Enum

class NicheCategory(str, Enum):
    """Enum representing the different niche categories."""
    MONEY_COACHING = 'money coaching'
    SKILLS_PROGRAM = 'skills program'

class LinkPair(TypedDict):
    """TypedDict representing a pair of website and ads URLs with metadata."""
    website_url: str | None
    ads_url: str | None
    niche_category: NicheCategory | None
    is_running_ads: bool | None

class ProgressEntry(TypedDict):
    """
    TypedDict representing an entry in the progress.json file.
    
    Fields:
        video_id: Unique identifier for the video (e.g., "rendered_video_0")
        status: Current status of the video processing
        instance_id: ID of the instance processing this video (None if not being processed)
        timestamp: Unix timestamp of the last status update (None if never processed)
        website_url: URL of the company's website
        ads_url: URL of the company's ads page
        niche_category: Category of the company (money coaching or skills program)
        is_running_ads: Whether the company is currently running ads
    """
    video_id: str
    status: Literal["pending", "in progress", "completed", "failed", "uploaded"]
    instance_id: str | None
    timestamp: float | None
    website_url: str | None
    ads_url: str | None
    niche_category: NicheCategory | None
    is_running_ads: bool | None

class VideoInstruction(TypedDict):
    """
    TypedDict representing a video instruction.

    Fields:
        type: The type of video instruction (e.g., "pip video over image", "video", "audio only over image").
        video_path: The path to the video file.
        image_path: The path to the image file (if applicable).
        scale: The scale of the video (if applicable).
        starting_position: The starting position of the video (if applicable).
        transition_positions: A list of tuples representing the transition positions (if applicable).
        pip_fade_in: The duration of the fade-in effect for the PIP video (if applicable).
        pip_fade_out: The duration of the fade-out effect for the PIP video (if applicable).
        audio_fadeout: The duration of the audio fade-out effect (if applicable).
        transitions_enabled: Whether transitions are enabled (if applicable).
    """
    type: Literal["pip video over image", "video", "audio only over image"]
    video_path: str
    image_path: str | None
    scale: float | None
    starting_position: Literal["top left", "top right", "bottom left", "bottom right"] | None
    transition_positions: List[Tuple[int, Literal["top left", "top right", "bottom left", "bottom right"]]] | None
    pip_fade_in: float | None
    pip_fade_out: float | None
    audio_fadeout: float | None
    transitions_enabled: bool | None

class VideoConfig(TypedDict):
    """
    TypedDict representing a video configuration.

    Fields:
        instructions: A list of video instructions.
        resolution: The resolution of the video.
    """
    instructions: List[VideoInstruction]
    resolution: Tuple[int, int]

"""
Configuration management for the video production pipeline.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv


@dataclass
class TTSConfig:
    """Text-to-Speech configuration."""
    engine: str = "espeak"
    model: Optional[str] = None
    voice: Optional[str] = None
    fallback_engine: str = "espeak"


@dataclass
class ImageConfig:
    """Image generation configuration."""
    engine: str = "dalle"
    model: str = "dall-e-3"
    size: str = "1024x1024"
    quality: str = "standard"
    fallback_engine: str = "unsplash"


@dataclass
class VideoConfig:
    """Video assembly configuration."""
    resolution: tuple = (1280, 720)
    fps: int = 24
    video_codec: str = "libx264"
    audio_codec: str = "aac"
    pixel_format: str = "yuv420p"


@dataclass
class PipelineConfig:
    """Main pipeline configuration."""
    # API Keys
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    
    # Engine configurations
    tts: TTSConfig = field(default_factory=TTSConfig)
    image: ImageConfig = field(default_factory=ImageConfig)
    video: VideoConfig = field(default_factory=VideoConfig)
    
    # Pipeline settings
    default_model: str = "models/gemini-1.5-pro-latest"
    temp_dir_name: str = "temp_segments"
    final_video_name: str = "final_video.mp4"
    
    # File patterns
    audio_pattern: str = "{idx:02d}_{heading}.wav"
    image_pattern: str = "{idx:02d}_{heading}.png"
    segment_pattern: str = "segment_{idx:02d}.mp4"
    
    # Logging
    log_level: str = "INFO"
    
    def __post_init__(self):
        """Load environment variables after initialization."""
        load_dotenv()
        self.gemini_api_key = self.gemini_api_key or os.getenv("GEMINI_API_KEY")
        self.openai_api_key = self.openai_api_key or os.getenv("OPENAI_API_KEY")


def load_config() -> PipelineConfig:
    """Load configuration from environment and defaults."""
    return PipelineConfig()


def get_safe_filename(text: str) -> str:
    """Convert text to a safe filename."""
    import re
    # Remove or replace unsafe characters
    safe = re.sub(r'[<>:"/\\|?*]', '', text)
    # Replace spaces and other characters with underscores
    safe = re.sub(r'[^\w\-_.]', '_', safe)
    # Remove multiple consecutive underscores
    safe = re.sub(r'_+', '_', safe)
    # Remove leading/trailing underscores
    safe = safe.strip('_')
    return safe or "untitled" 
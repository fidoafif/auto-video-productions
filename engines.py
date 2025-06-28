"""
Engine management for TTS and image generation.
"""

import logging
from typing import Dict, Any, Optional, Callable
from pathlib import Path

from config import PipelineConfig, TTSConfig, ImageConfig
from utils import discover_plugins
import os

logger = logging.getLogger(__name__)


class EngineManager:
    """Manages TTS and image generation engines with fallbacks."""
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.tts_engines = self._load_tts_engines()
        self.image_engines = self._load_image_engines()
    
    def _load_tts_engines(self) -> Dict[str, Callable]:
        """Dynamically load available TTS engines as plugins."""
        tts_dir = Path(os.path.dirname(__file__)) / 'tts_engines'
        plugins = discover_plugins(tts_dir, 'tts_')
        if not plugins:
            raise RuntimeError("No TTS engines available")
        logger.info(f"Available TTS engines: {list(plugins.keys())}")
        return plugins
    
    def _load_image_engines(self) -> Dict[str, Callable]:
        """Dynamically load available image generation engines as plugins."""
        image_dir = Path(os.path.dirname(__file__)) / 'image_engines'
        plugins = discover_plugins(image_dir, 'generate_')
        if not plugins:
            raise RuntimeError("No image engines available")
        logger.info(f"Available image engines: {list(plugins.keys())}")
        return plugins
    
    def generate_tts(self, text: str, output_path: Path, config: TTSConfig) -> bool:
        """Generate TTS audio with fallback support."""
        engine_name = config.engine.lower()
        
        # Try primary engine
        if engine_name in self.tts_engines:
            try:
                self.tts_engines[engine_name](text, str(output_path), config.model, config.voice)
                return True
            except Exception as e:
                logger.warning(f"Primary TTS engine {engine_name} failed: {e}")
        
        # Try fallback engine
        fallback_name = config.fallback_engine.lower()
        if fallback_name in self.tts_engines and fallback_name != engine_name:
            try:
                logger.info(f"Using fallback TTS engine: {fallback_name}")
                self.tts_engines[fallback_name](text, str(output_path), config.model, config.voice)
                return True
            except Exception as e:
                logger.error(f"Fallback TTS engine {fallback_name} also failed: {e}")
        
        # If no engines work, raise error
        available_engines = list(self.tts_engines.keys())
        raise RuntimeError(f"No working TTS engine. Available: {available_engines}")
    
    def generate_image(self, prompt: str, output_path: Path, config: ImageConfig) -> bool:
        """Generate image with fallback support."""
        engine_name = config.engine.lower()
        
        # Try primary engine
        if engine_name in self.image_engines:
            try:
                # Try to call with all possible params, fallback to less if needed
                try:
                    self.image_engines[engine_name](prompt, str(output_path), config.model, config.size, config.quality)
                except TypeError:
                    try:
                        self.image_engines[engine_name](prompt, str(output_path), config.model)
                    except TypeError:
                        self.image_engines[engine_name](prompt, str(output_path))
                return True
            except Exception as e:
                logger.warning(f"Primary image engine {engine_name} failed: {e}")
        
        # Try fallback engine
        fallback_name = config.fallback_engine.lower()
        if fallback_name in self.image_engines and fallback_name != engine_name:
            try:
                logger.info(f"Using fallback image engine: {fallback_name}")
                try:
                    self.image_engines[fallback_name](prompt, str(output_path), config.model, config.size, config.quality)
                except TypeError:
                    try:
                        self.image_engines[fallback_name](prompt, str(output_path), config.model)
                    except TypeError:
                        self.image_engines[fallback_name](prompt, str(output_path))
                return True
            except Exception as e:
                logger.error(f"Fallback image engine {fallback_name} also failed: {e}")
        
        # If no engines work, raise error
        available_engines = list(self.image_engines.keys())
        raise RuntimeError(f"No working image engine. Available: {available_engines}")
    
    def get_available_engines(self) -> Dict[str, list]:
        """Get list of available engines."""
        return {
            'tts': list(self.tts_engines.keys()),
            'image': list(self.image_engines.keys())
        } 
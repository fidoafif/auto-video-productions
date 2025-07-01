# ... update imports to use relative imports if needed ... 

import json
import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from tqdm import tqdm
import ffmpeg
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import app.helpers as helpers
from app.config import PipelineConfig, TTSConfig, ImageConfig, VideoConfig
from app.engines import EngineManager
from app.utils import save_json, load_json, ensure_directory, clean_temp_files, validate_file_exists, sanitize_filename

logger = logging.getLogger(__name__)

def validate_script_sections(sections):
    """Validate that sections is a list of dicts with non-empty heading and narration."""
    if not isinstance(sections, list) or not sections:
        return False
    for section in sections:
        if not isinstance(section, dict):
            return False
        if not section.get("heading") or not section.get("narration"):
            return False
    return True

class VideoPipeline:
    """Main video production pipeline with progress tracking, resumption, and parallel processing."""
    
    def __init__(self, config: PipelineConfig, engine_manager: EngineManager, output_dir: str, max_workers: int = 4):
        self.config = config
        self.engine_manager = engine_manager
        self.output_dir = Path(output_dir)
        self.max_workers = max_workers
        self.scripts_dir = ensure_directory(self.output_dir / "scripts")
        self.audio_dir = ensure_directory(self.output_dir / "audio")
        self.images_dir = ensure_directory(self.output_dir / "images")
        self.video_dir = ensure_directory(self.output_dir / "video")
        self.progress_path = self.output_dir / "progress.json"
        self.progress = self._load_progress()
        self._progress_lock = threading.Lock()

    def _load_progress(self):
        if self.progress_path.exists():
            try:
                with open(self.progress_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load progress.json: {e}")
        return {
            "script": False,
            "voice": [],
            "images": [],
            "video": False
        }

    def _save_progress(self):
        try:
            with open(self.progress_path, 'w') as f:
                json.dump(self.progress, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save progress.json: {e}")

    def generate_script(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        if self.progress.get("script"):
            logger.info("Script generation already completed. Skipping.")
            return self.load_step_data('script')
        if not self.config.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY not found in environment")
        from google.generativeai.client import configure
        from google.generativeai.generative_models import GenerativeModel
        configure(api_key=self.config.gemini_api_key)
        model_name = input_data.get("model", self.config.default_model)
        prompt = helpers.build_prompt(input_data)
        model = GenerativeModel(model_name)
        response = model.generate_content(prompt)
        text = response.text
        sections = self._parse_script_response(text)
        if not validate_script_sections(sections):
            raise ValueError("Generated script sections are not valid. Please check the prompt or model output.")
        for section in sections:
            section["duration"] = helpers.estimate_duration(section["narration"])
        title = input_data.get("topic", "Generated Video Script")
        if sections and sections[0].get("heading"):
            title = sections[0]["heading"]
        output = {
            "title": title,
            "sections": sections,
            "meta": {
                **input_data.get("meta", {}),
                "model": model_name,
                "topic": input_data.get("topic", ""),
                "keywords": input_data.get("keywords", []),
                "prompt": input_data.get("prompt", ""),
                "generated_at": datetime.now().isoformat()
            }
        }
        script_path = self.scripts_dir / "script.json"
        save_json(output, script_path)
        logger.info(f"Script generated and saved to {script_path}")
        self.progress["script"] = True
        self._save_progress()
        return output

    def _parse_script_response(self, text: str) -> List[Dict[str, Any]]:
        json_match = re.search(r'```json\s*(\[.*?\])\s*```', text, re.DOTALL)
        if json_match:
            try:
                sections = json.loads(json_match.group(1))
                logger.info("Successfully parsed JSON code block from response")
                return sections
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON code block: {e}")
        logger.info("Using fallback text parsing logic")
        sections = []
        lines = text.strip().split("\n")
        current = {}
        for line in lines:
            if not line.strip():
                continue
            if line.endswith(":"):
                if current:
                    sections.append(current)
                current = {"heading": line[:-1], "narration": ""}
            else:
                if not current:
                    current = {"heading": "", "narration": ""}
                current["narration"] += (line + " ")
        if current:
            sections.append(current)
        return sections

    def generate_voice(self, script_data: Dict[str, Any]) -> Dict[str, Any]:
        meta = script_data.get("meta", {})
        tts_config = TTSConfig(**meta.get("tts", {}))
        sections = script_data["sections"]
        completed = set(self.progress.get("voice", []))
        tasks = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            for idx, section in enumerate(sections, 1):
                if idx in completed:
                    logger.info(f"Voice for section {idx} already completed. Skipping.")
                    continue
                tasks.append(executor.submit(self._generate_voice_section, idx, section, tts_config))
            for future in as_completed(tasks):
                result = future.result()
                if result:
                    idx = result
                    with self._progress_lock:
                        self.progress.setdefault("voice", []).append(idx)
                        self._save_progress()
        voice_path = self.audio_dir / "voice.json"
        save_json(script_data, voice_path)
        logger.info(f"Voice generated and saved to {voice_path}")
        return script_data

    def _generate_voice_section(self, idx, section, tts_config):
        heading = section["heading"]
        narration = section["narration"]
        safe_heading = sanitize_filename(heading)
        filename = f"{idx:02d}_{safe_heading}.wav"
        output_path = self.audio_dir / filename
        try:
            self.engine_manager.generate_tts(narration, output_path, tts_config)
            section["sound_file"] = filename
            logger.info(f"[Voice] Section {idx} complete.")
            return idx
        except Exception as e:
            logger.error(f"Voice generation failed for section {idx}: {e}")
            return None

    def generate_images(self, voice_data: Dict[str, Any]) -> Dict[str, Any]:
        meta = voice_data.get('meta', {})
        image_config = ImageConfig(**meta.get('image', {}))
        topic = meta.get('topic', '')
        keywords = meta.get('keywords', [])
        sections = voice_data["sections"]
        completed = set(self.progress.get("images", []))
        tasks = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            for idx, section in enumerate(sections, 1):
                if idx in completed:
                    logger.info(f"Image for section {idx} already completed. Skipping.")
                    continue
                tasks.append(executor.submit(self._generate_image_section, idx, section, image_config, topic, keywords))
            for future in as_completed(tasks):
                result = future.result()
                if result:
                    idx = result
                    with self._progress_lock:
                        self.progress.setdefault("images", []).append(idx)
                        self._save_progress()
        images_path = self.images_dir / "images.json"
        save_json(voice_data, images_path)
        logger.info(f"Images generated and saved to {images_path}")
        return voice_data

    def _generate_image_section(self, idx, section, image_config, topic, keywords):
        heading = section.get('heading', f'Section {idx}')
        prompt = helpers.create_prompt_from_section(section, topic, keywords)
        safe_heading = sanitize_filename(heading)
        image_filename = f"{idx:02d}_{safe_heading}.png"
        image_path = self.images_dir / image_filename
        try:
            self.engine_manager.generate_image(prompt, image_path, image_config)
            section['image_file'] = image_filename
            logger.info(f"[Image] Section {idx} complete.")
            return idx
        except Exception as e:
            logger.error(f"Image generation failed for section {idx}: {e}")
            return None

    def assemble_video(self, image_data: Dict[str, Any]) -> str:
        if self.progress.get("video"):
            logger.info("Video assembly already completed. Skipping.")
            return str(self.video_dir / self.config.final_video_name)
        sections = image_data.get('sections', [])
        temp_dir = self.video_dir / self.config.temp_dir_name
        ensure_directory(temp_dir)
        try:
            segment_paths = self._create_video_segments(sections, temp_dir)
            if not segment_paths:
                raise RuntimeError("No valid video segments to assemble")
            final_video_path = self._concatenate_segments(segment_paths)
            logger.info(f"✅ Video assembled and saved to: {final_video_path}")
            self.progress["video"] = True
            self._save_progress()
            return str(final_video_path)
        finally:
            clean_temp_files(temp_dir)

    def _create_video_segments(self, sections: List[Dict[str, Any]], temp_dir: Path) -> List[Path]:
        segment_paths = []
        for i, section in enumerate(sections):
            img_file = section.get('image_file')
            audio_file = section.get('sound_file')
            duration = section.get('duration')
            if not all([img_file, audio_file, duration]):
                logger.warning(f"Skipping section {i+1}: missing image/audio/duration")
                continue
            img_path = self.images_dir / str(img_file)
            audio_path = self.audio_dir / str(audio_file)
            validate_file_exists(img_path, f"Image for section {i+1}")
            validate_file_exists(audio_path, f"Audio for section {i+1}")
            segment_path = temp_dir / f"segment_{i+1:02d}.mp4"
            logger.info(f"Creating segment {i+1}: {segment_path}")
            try:
                duration_float = float(duration) if duration is not None else 0.0
                if duration_float <= 0:
                    logger.warning(f"Skipping section {i+1}: invalid duration {duration}")
                    continue
            except (ValueError, TypeError):
                logger.warning(f"Skipping section {i+1}: invalid duration {duration}")
                continue
            if self._make_section_video(img_path, audio_path, duration_float, segment_path):
                segment_paths.append(segment_path)
        return segment_paths

    def _make_section_video(self, img_path: Path, audio_path: Path, duration: float, out_path: Path) -> bool:
        try:
            video_stream = (
                ffmpeg
                .input(str(img_path), loop=1, t=duration)
                .filter('scale', self.config.video.resolution[0], self.config.video.resolution[1], 
                       force_original_aspect_ratio='decrease')
            )
            audio_stream = ffmpeg.input(str(audio_path))
            (
                ffmpeg
                .output(video_stream, audio_stream, str(out_path), 
                       vcodec=self.config.video.video_codec, 
                       acodec=self.config.video.audio_codec, 
                       pix_fmt=self.config.video.pixel_format, 
                       t=duration, r=self.config.video.fps, shortest=None, y=None)
                .overwrite_output()
                .run(quiet=True)
            )
            return True
        except ffmpeg.Error as e:
            logger.error(f"FFmpeg error for {img_path} + {audio_path}: {e.stderr.decode() if hasattr(e, 'stderr') else e}")
            return False

    def _concatenate_segments(self, segment_paths: List[Path]) -> Path:
        concat_file = segment_paths[0].parent / 'concat_list.txt'
        with open(concat_file, 'w') as f:
            for seg in segment_paths:
                f.write(f"file '{seg.absolute()}'\n")
        final_video_path = self.video_dir / self.config.final_video_name
        concat_cmd = (
            ffmpeg
            .input(str(concat_file), format='concat', safe=0)
            .output(str(final_video_path), c='copy', y=None)
        )
        try:
            logger.info(f"Concatenating {len(segment_paths)} segments into {final_video_path}")
            concat_cmd.run(quiet=True)
            return final_video_path
        except ffmpeg.Error as e:
            raise RuntimeError(f"Failed to concatenate video: {e.stderr.decode() if hasattr(e, 'stderr') else e}")

    def load_step_data(self, step: str) -> Dict[str, Any]:
        step_files = {
            'script': self.scripts_dir / "script.json",
            'voice': self.audio_dir / "voice.json",
            'images': self.images_dir / "images.json"
        }
        if step not in step_files:
            raise ValueError(f"Unknown step: {step}. Available: {list(step_files.keys())}")
        file_path = step_files[step]
        validate_file_exists(file_path, f"{step.capitalize()} data")
        return load_json(file_path) 
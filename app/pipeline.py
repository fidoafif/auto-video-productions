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
import jsonschema
from app.image_model_defaults import IMAGE_MODEL_DEFAULTS

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
        # --- Section Consistency ---
        sections = helpers.ensure_section_consistency(sections)
        # ---
        # --- Assign style to each section (round-robin for demo) ---
        style_cycle = ['cartoon', 'anime', 'photorealistic']
        for i, section in enumerate(sections):
            section['style'] = style_cycle[i % len(style_cycle)]
        # ---
        for section in sections:
            section["duration"] = helpers.estimate_duration(section["narration"])
        title = input_data.get("topic", "Generated Video Script")
        if sections and sections[0].get("heading"):
            title = sections[0]["heading"]
        # --- Metadata Enrichment ---
        meta = helpers.enrich_metadata({**input_data.get("meta", {}),
                                        "model": model_name,
                                        "topic": input_data.get("topic", ""),
                                        "keywords": input_data.get("keywords", []),
                                        "prompt": input_data.get("prompt", "")},
                                       input_data)
        # ---
        output = {
            "title": title,
            "sections": sections,
            "meta": meta
        }
        # --- JSON Schema Validation ---
        schema_path = Path(__file__).parent.parent / "schemas" / "script.schema.json"
        with open(schema_path, "r") as f:
            schema = json.load(f)
        try:
            jsonschema.validate(instance=output, schema=schema)
        except jsonschema.ValidationError as e:
            logger.error(f"script.json validation failed: {e.message}")
            raise ValueError(f"script.json validation failed: {e.message}")
        # ---
        script_path = self.scripts_dir / "script.json"
        save_json(output, script_path)
        # --- SRT Export ---
        srt_path = self.scripts_dir / "script.srt"
        helpers.export_srt(sections, srt_path)
        logger.info(f"Script generated and saved to {script_path} and {srt_path}")
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

    def generate_voice(self, script_data: Dict[str, Any], test_mode: bool = False) -> Any:
        """Generate voice audio for each section. Returns manifest (list) in test mode, else original script_data (dict)."""
        meta = script_data.get("meta", {})
        tts_config = TTSConfig(**meta.get("tts", {}))
        sections = script_data["sections"]
        completed = set(self.progress.get("voice", []))
        tasks = []
        manifest = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            for idx, section in enumerate(sections, 1):
                if idx in completed:
                    logger.info(f"Voice for section {idx} already completed. Skipping.")
                    continue
                tasks.append(executor.submit(self._generate_voice_section, idx, section, tts_config))
            for future in tqdm(as_completed(tasks), total=len(tasks), desc="Generating voice", unit="section"):
                result = future.result()
                if result:
                    idx = result
                    with self._progress_lock:
                        self.progress.setdefault("voice", []).append(idx)
                        self._save_progress()
        # Build manifest and generate transcripts
        for idx, section in enumerate(sections, 1):
            heading = section["heading"]
            narration = section["narration"]
            safe_heading = sanitize_filename(heading)
            filename = f"{idx:02d}_{safe_heading}.wav"
            transcript_path = self.audio_dir / f"{idx:02d}_{safe_heading}.txt"
            vtt_path = self.audio_dir / f"{idx:02d}_{safe_heading}.vtt"
            # Write plain text transcript
            with open(transcript_path, 'w', encoding='utf-8') as f:
                f.write(narration.strip())
            # Write WebVTT transcript (single cue for whole narration)
            duration = section.get("duration", 0)
            start = "00:00:00.000"
            mins = int(duration // 60)
            secs = int(duration % 60)
            ms = int((duration - int(duration)) * 1000)
            end = f"00:{mins:02}:{secs:02}.{ms:03}"
            with open(vtt_path, 'w', encoding='utf-8') as f:
                f.write("WEBVTT\n\n")
                f.write(f"{start} --> {end}\n{narration.strip()}\n")
            manifest.append({
                "section_index": idx,
                "script_heading": heading,
                "filename": filename,
                "duration": duration,
                "speaker": tts_config.voice or "default",
                "text": narration,
                "format": "wav"
            })
        voice_path = self.audio_dir / "voice.json"
        save_json(manifest, voice_path)
        logger.info(f"Voice generated and saved to {voice_path} (manifest)")
        if test_mode:
            return manifest
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

    def generate_images(self, voice_data: Dict[str, Any], test_mode: bool = False) -> Any:
        """Generate images for each section. First, generate and save images.json manifest, then generate images from it."""
        meta = voice_data.get('meta', {})
        image_meta = meta.get('image', {})
        # Defaults for dynamic config
        engine = image_meta.get('engine', 'dynamic')
        default_model = image_meta.get('default_model', 'runwayml/stable-diffusion-v1-5')
        size = image_meta.get('size', '512x512')
        quality = image_meta.get('quality', 'standard')
        # Built-in default models for common styles
        models_map = image_meta.get('models') or IMAGE_MODEL_DEFAULTS
        topic = meta.get('topic', '')
        keywords = meta.get('keywords', [])
        sections = voice_data["sections"]
        completed = set(self.progress.get("images", []))
        manifest = []
        # --- Phase 1: Build and save manifest ---
        for idx, section in enumerate(sections, 1):
            heading = section.get('heading', f'Section {idx}')
            safe_heading = sanitize_filename(heading)
            filename = f"{idx:02d}_{safe_heading}.png"
            prompt = helpers.create_prompt_from_section(section, topic, keywords)
            narration = section.get('narration', '')
            alt_text = f"{heading}: {narration[:80]}" if narration else heading
            style = section.get('style') or section.get('model')
            model = None
            if engine == 'dynamic':
                if style and style in models_map:
                    model = models_map[style]
                else:
                    model = default_model
            else:
                model = image_meta.get('model', default_model)
            manifest.append({
                "section_index": idx,
                "script_heading": heading,
                "filename": filename,
                "prompt": prompt,
                "alt_text": alt_text,
                "resolution": size,
                "model": model,
                "style": style or "default"
            })
        images_path = self.images_dir / "images.json"
        save_json(manifest, images_path)
        logger.info(f"Image manifest generated and saved to {images_path}")
        if test_mode:
            return manifest
        # --- Phase 2: Generate images from manifest ---
        tasks = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            for entry in manifest:
                idx = entry["section_index"]
                if idx in completed:
                    logger.info(f"Image for section {idx} already completed. Skipping.")
                    continue
                section = sections[idx - 1]
                image_config = ImageConfig(
                    engine='stable_diffusion',
                    model=entry["model"],
                    size=size,
                    quality=quality,
                    fallback_engine='unsplash'
                )
                tasks.append(executor.submit(
                    self._generate_image_section,
                    idx,
                    section,
                    image_config,
                    topic,
                    keywords
                ))
            for future in tqdm(as_completed(tasks), total=len(tasks), desc="Generating images", unit="section"):
                result = future.result()
                if result:
                    idx = result
                    with self._progress_lock:
                        self.progress.setdefault("images", []).append(idx)
                        self._save_progress()
        logger.info(f"Images generated and saved to {images_path} (manifest)")
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
            # AI-powered image URL fallback
            try:
                # Always use the model from pipeline config or root meta
                model_name = getattr(self.config, 'default_model', None)
                url = helpers.get_image_url_from_ai(prompt, model_name)
                helpers.download_image_from_url(url, image_path)
                section['image_file'] = image_filename
                logger.info(f"[Image] Section {idx} fallback: AI image URL downloaded.")
                return idx
            except Exception as e2:
                logger.error(f"AI image URL fallback also failed for section {idx}: {e2}")
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
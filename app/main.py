import sys
import json
from pathlib import Path
from app.config import load_config
from app.engines import EngineManager
from app.pipeline import VideoPipeline
from app.utils import setup_logging, sanitize_filename, create_numbered_directory

def parse_arguments():
    import argparse
    parser = argparse.ArgumentParser(description="Automated Video Production Pipeline")
    parser.add_argument('--input', default='input.json', help='Path to input.json (default: input.json)')
    parser.add_argument('--output_dir', default='outputs', help='Directory to save all outputs (default: outputs)')
    parser.add_argument('--step', type=int, choices=[1, 2, 3, 4], help='Start pipeline from specific step (1=script, 2=voice, 3=images, 4=video)')
    parser.add_argument('--use_existing', help='Use existing data from specified output folder')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    parser.add_argument('--max_workers', type=int, default=4, help='Number of parallel workers for voice/image generation')
    parser.add_argument('--only_script', action='store_true', help='Run only the script step and validate output')
    parser.add_argument('--only_audio', action='store_true', help='Run only the audio step and validate output')
    parser.add_argument('--only_image', action='store_true', help='Run only the image step and validate output')
    args = parser.parse_args()
    return args

def validate_arguments(args):
    if args.use_existing and not args.step:
        raise ValueError("--use_existing requires --step to be specified")
    if args.use_existing and args.step != 4:
        raise ValueError("--use_existing currently only supports --step 4 (video assembly)")
    if not args.step or args.step < 4:
        if not Path(args.input).exists():
            raise FileNotFoundError(f"Input file not found: {args.input}")

def load_input_data(input_file):
    try:
        with open(input_file, 'r') as f:
            data = json.load(f)
        required_fields = ['topic']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        return data
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in input file: {e}")
    except Exception as e:
        raise RuntimeError(f"Failed to load input file: {e}")

def handle_existing_data(args, logger):
    if not args.use_existing:
        return None
    existing_path = Path(args.output_dir) / args.use_existing
    if not existing_path.exists():
        raise FileNotFoundError(f"Existing folder not found: {existing_path}")
    logger.info(f"Loading existing data from: {existing_path}")
    data_files = {
        'script': existing_path / "scripts" / "script.json",
        'voice': existing_path / "audio" / "voice.json", 
        'images': existing_path / "images" / "images.json"
    }
    pipeline_data = {}
    for data_type, file_path in data_files.items():
        if not file_path.exists():
            raise FileNotFoundError(f"{data_type} data not found: {file_path}")
        with open(file_path, 'r') as f:
            pipeline_data[data_type] = json.load(f)
    pipeline_data['images']['output_dir'] = str(existing_path)
    logger.info(f"Successfully loaded existing data with {len(pipeline_data['images'].get('sections', []))} sections")
    return pipeline_data['images']

def run_pipeline(args, logger):
    config = load_config()
    engine_manager = EngineManager(config)
    if args.use_existing:
        existing_data = handle_existing_data(args, logger)
        if existing_data is None:
            raise RuntimeError("Failed to load existing data")
        pipeline = VideoPipeline(config, engine_manager, existing_data['output_dir'], max_workers=args.max_workers)
        return pipeline.assemble_video(existing_data)
    input_data = load_input_data(args.input)
    logger.info(f"Input configuration loaded: {input_data.get('topic', 'Untitled')}")
    output_dir = create_numbered_directory(args.output_dir, input_data['topic'])
    logger.info(f"Output directory: {output_dir}")
    pipeline = VideoPipeline(config, engine_manager, str(output_dir), max_workers=args.max_workers)
    start_step = args.step or 1
    try:
        if start_step <= 1:
            logger.info("--- Step 1: Script Generation ---")
            script_data = pipeline.generate_script(input_data)
        else:
            logger.info(f"Skipping Step 1 - starting from step {start_step}")
            script_data = pipeline.load_step_data('script')
        if start_step <= 2:
            logger.info("--- Step 2: Voice Generation ---")
            voice_data = pipeline.generate_voice(script_data)
        else:
            logger.info(f"Skipping Step 2 - starting from step {start_step}")
            voice_data = pipeline.load_step_data('voice')
        if start_step <= 3:
            logger.info("--- Step 3: Image Generation ---")
            image_data = pipeline.generate_images(voice_data)
        else:
            logger.info(f"Skipping Step 3 - starting from step {start_step}")
            image_data = pipeline.load_step_data('images')
        logger.info("--- Step 4: Video Assembly ---")
        final_video_path = pipeline.assemble_video(image_data)
        logger.info(f"✅ Pipeline complete! Final video: {final_video_path}")
        return final_video_path
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        raise

def main():
    logger = setup_logging()
    try:
        args = parse_arguments()
        validate_arguments(args)
        if getattr(args, 'only_script', False):
            config = load_config()
            engine_manager = EngineManager(config)
            input_data = load_input_data(args.input)
            output_dir = create_numbered_directory(args.output_dir, input_data['topic'])
            pipeline = VideoPipeline(config, engine_manager, str(output_dir), max_workers=args.max_workers)
            logger.info("--- Step 1: Script Generation (Test Mode) ---")
            script_data = pipeline.generate_script(input_data)
            print(json.dumps(script_data, indent=2, ensure_ascii=False))
            print("\n✅ Script step complete and validated.")
            return 0
        if getattr(args, 'only_audio', False):
            config = load_config()
            engine_manager = EngineManager(config)
            # Find the latest script.json in the output_dir
            from glob import glob
            import os
            scripts_dir = Path(args.output_dir) / 'scripts'
            script_path = scripts_dir / 'script.json'
            if not script_path.exists():
                raise FileNotFoundError(f"script.json not found in {scripts_dir}")
            with open(script_path, 'r') as f:
                script_data = json.load(f)
            pipeline = VideoPipeline(config, engine_manager, str(Path(args.output_dir)), max_workers=args.max_workers)
            logger.info("--- Step 2: Voice Generation (Test Mode) ---")
            manifest = pipeline.generate_voice(script_data, test_mode=True)
            print(json.dumps(manifest, indent=2, ensure_ascii=False))
            print("\n✅ Audio step complete and validated.")
            return 0
        if getattr(args, 'only_image', False):
            config = load_config()
            engine_manager = EngineManager(config)
            # Find the latest voice.json and script.json in the output_dir
            import os
            scripts_dir = Path(args.output_dir) / 'scripts'
            audio_dir = Path(args.output_dir) / 'audio'
            script_path = scripts_dir / 'script.json'
            voice_path = audio_dir / 'voice.json'
            if not script_path.exists():
                raise FileNotFoundError(f"script.json not found in {scripts_dir}")
            if not voice_path.exists():
                raise FileNotFoundError(f"voice.json not found in {audio_dir}")
            with open(script_path, 'r') as f:
                script_data = json.load(f)
            with open(voice_path, 'r') as f:
                voice_data = json.load(f)
            # For compatibility, reconstruct voice_data as a dict with meta and sections from script
            if isinstance(voice_data, list):
                # Use script_data for meta/sections, as in the main pipeline
                voice_data = script_data
            pipeline = VideoPipeline(config, engine_manager, str(Path(args.output_dir)), max_workers=args.max_workers)
            logger.info("--- Step 3: Image Generation (Test Mode) ---")
            manifest = pipeline.generate_images(voice_data, test_mode=True)
            print(json.dumps(manifest, indent=2, ensure_ascii=False))
            print("\n✅ Image step complete and validated.")
            return 0
        final_video_path = run_pipeline(args, logger)
        print(f"\n🎉 Video production complete!")
        print(f"📁 Output: {final_video_path}")
        return 0
    except KeyboardInterrupt:
        logger.info("Pipeline interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        return 1 
"""
Automated Video Production Pipeline

This script orchestrates the full workflow:
1. Script Generation (Gemini)
2. Voice Generation (Multiple TTS engines)
3. Image Generation (Multiple image engines)
4. Video Assembly (ffmpeg)

Usage:
    python main.py --input input.json --output_dir outputs/
    python main.py --step 4 --use_existing "01_My_Video"
"""

import sys
import json
from pathlib import Path

from config import load_config
from engines import EngineManager
from pipeline import VideoPipeline
from utils import setup_logging, sanitize_filename, create_numbered_directory

# Setup logging
logger = setup_logging()


def parse_arguments():
    """Parse command line arguments."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Automated Video Production Pipeline")
    parser.add_argument('--input', default='input.json', help='Path to input.json (default: input.json)')
    parser.add_argument('--output_dir', default='outputs', help='Directory to save all outputs (default: outputs)')
    parser.add_argument('--step', type=int, choices=[1, 2, 3, 4], help='Start pipeline from specific step (1=script, 2=voice, 3=images, 4=video)')
    parser.add_argument('--use_existing', help='Use existing data from specified output folder')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    return args


def validate_arguments(args):
    """Validate command line arguments."""
    if args.use_existing and not args.step:
        raise ValueError("--use_existing requires --step to be specified")
    
    if args.use_existing and args.step != 4:
        raise ValueError("--use_existing currently only supports --step 4 (video assembly)")
    
    if not args.step or args.step < 4:
        if not Path(args.input).exists():
            raise FileNotFoundError(f"Input file not found: {args.input}")


def load_input_data(input_file):
    """Load and validate input configuration."""
    try:
        with open(input_file, 'r') as f:
            data = json.load(f)
        
        # Validate required fields
        required_fields = ['topic']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
        
        return data
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in input file: {e}")
    except Exception as e:
        raise RuntimeError(f"Failed to load input file: {e}")


def handle_existing_data(args):
    """Handle --use_existing argument by loading existing pipeline data."""
    if not args.use_existing:
        return None
    
    existing_path = Path(args.output_dir) / args.use_existing
    if not existing_path.exists():
        raise FileNotFoundError(f"Existing folder not found: {existing_path}")
    
    logger.info(f"Loading existing data from: {existing_path}")
    
    # Load all pipeline data
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
    
    # Use the most complete dataset (images data) and add output directory
    pipeline_data['images']['output_dir'] = str(existing_path)
    
    logger.info(f"Successfully loaded existing data with {len(pipeline_data['images'].get('sections', []))} sections")
    return pipeline_data['images']


def run_pipeline(args):
    """Run the video production pipeline."""
    # Load configuration
    config = load_config()
    
    # Initialize engine manager
    engine_manager = EngineManager(config)
    
    # Handle existing data case
    if args.use_existing:
        existing_data = handle_existing_data(args)
        if existing_data is None:
            raise RuntimeError("Failed to load existing data")
        pipeline = VideoPipeline(config, engine_manager, existing_data['output_dir'])
        return pipeline.assemble_video(existing_data)
    
    # Load input data
    input_data = load_input_data(args.input)
    logger.info(f"Input configuration loaded: {input_data.get('topic', 'Untitled')}")
    
    # Create output directory
    output_dir = create_numbered_directory(args.output_dir, input_data['topic'])
    logger.info(f"Output directory: {output_dir}")
    
    # Initialize pipeline
    pipeline = VideoPipeline(config, engine_manager, str(output_dir))
    
    # Determine starting step
    start_step = args.step or 1
    
    # Run pipeline steps
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
    """Main entry point."""
    try:
        # Parse and validate arguments
        args = parse_arguments()
        validate_arguments(args)
        
        # Run pipeline
        final_video_path = run_pipeline(args)
        
        # Success message
        print(f"\n🎉 Video production complete!")
        print(f"📁 Output: {final_video_path}")
        
    except KeyboardInterrupt:
        logger.info("Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 
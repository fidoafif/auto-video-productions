"""
Monolithic Automated Video Production Pipeline

This script orchestrates the full workflow:
1. Script Generation (Gemini)
2. Voice Generation (Gemini, Coqui, or eSpeak)
3. Image Generation (DALL-E or Stable Diffusion)
4. Video Assembly (ffmpeg)

Usage:
    python monolithic_pipeline.py --input input.json --output_dir outputs/

- Accepts a single input.json (same as step 1)
- Runs all steps in sequence, passing data in-memory
- Saves all outputs (final video, intermediate JSONs, audio, images) in a structured output directory

Dependencies (must be installed):
    - python-dotenv
    - google-generativeai
    - tqdm
    - ffmpeg-python
    - (Optional) TTS: coqui-ai TTS, eSpeak NG, Gemini TTS
    - (Optional) DALL-E/Stable Diffusion API clients

Python Version Notes:
    - Coqui TTS requires Python <= 3.11
    - Some engines may require additional setup (see their docs)
"""

import os
import sys
import argparse
import json
import shutil
from datetime import datetime
from dotenv import load_dotenv
import ffmpeg
from tqdm import tqdm
import helpers
import re

# Import TTS engine functions directly
from tts_engines.tts_gemini import tts_gemini
try:
    from tts_engines.tts_coqui import tts_coqui
    COQUI_AVAILABLE = True
except ImportError:
    COQUI_AVAILABLE = False
    print("[WARNING] Coqui TTS not available (requires Python <=3.11). Using alternative TTS engines.")
from tts_engines.tts_espeak import tts_espeak
try:
    from tts_engines.tts_azure import tts_azure
    AZURE_AVAILABLE = True
except ImportError:
    AZURE_AVAILABLE = False
    print("[WARNING] Azure TTS not available (requires azure-cognitiveservices-speech). Using alternative TTS engines.")
try:
    from tts_engines.tts_googlecloud import tts_googlecloud
    GOOGLECLOUD_AVAILABLE = True
except ImportError:
    GOOGLECLOUD_AVAILABLE = False
    print("[WARNING] Google Cloud TTS not available (requires google-cloud-texttospeech). Using alternative TTS engines.")
try:
    from tts_engines.tts_elevenlabs import tts_elevenlabs
    ELEVENLABS_AVAILABLE = True
except ImportError:
    ELEVENLABS_AVAILABLE = False
    print("[WARNING] ElevenLabs TTS not available (requires elevenlabs). Using alternative TTS engines.")

# Import image engine functions directly
try:
    from image_engines.dalle import generate_dalle_image
    DALLE_AVAILABLE = True
except (ImportError, EnvironmentError):
    DALLE_AVAILABLE = False
    print("[WARNING] DALL-E not available (requires openai package and OPENAI_API_KEY). Using alternative image engines.")
try:
    from image_engines.stable_diffusion import generate_sd_image
    STABLE_DIFFUSION_AVAILABLE = True
except ImportError:
    STABLE_DIFFUSION_AVAILABLE = False
    print("[WARNING] Stable Diffusion not available (requires diffusers package). Using alternative image engines.")
try:
    from image_engines.unsplash import generate_unsplash_image
    UNSPLASH_AVAILABLE = True
except ImportError:
    UNSPLASH_AVAILABLE = False
    print("[WARNING] Unsplash not available (requires requests package). Using alternative image engines.")

# --- Step 1: Script Generation (Gemini) ---
def generate_script(input_data, output_dir):
    """Generate the video script (Step 1)."""
    load_dotenv()
    API_KEY = os.getenv("GEMINI_API_KEY")
    if not API_KEY:
        print("[ERROR] GEMINI_API_KEY not found in .env file.")
        sys.exit(1)
    
    # Use the correct Gemini API import for text generation
    from google.generativeai.client import configure
    from google.generativeai.generative_models import GenerativeModel
    configure(api_key=API_KEY)
    model_name = input_data.get("model", "models/gemini-1.5-pro-latest")
    prompt = helpers.build_prompt(input_data)
    model = GenerativeModel(model_name)
    response = model.generate_content(prompt)
    text = response.text
    
    # Try to parse JSON code blocks first
    sections = []
    # Look for JSON code blocks (```json ... ```)
    json_match = re.search(r'```json\s*(\[.*?\])\s*```', text, re.DOTALL)
    if json_match:
        try:
            json_content = json_match.group(1)
            sections = json.loads(json_content)
            print("[INFO] Successfully parsed JSON code block from response")
        except json.JSONDecodeError as e:
            print(f"[WARNING] Failed to parse JSON code block: {e}")
            sections = []
    
    # If no JSON found or parsing failed, use the original parsing logic
    if not sections:
        print("[INFO] Using fallback text parsing logic")
        # Simple parser: expects headings and narration separated by newlines
        lines = text.strip().split("\n")
        current = {}
        for line in lines:
            if line.strip() == "":
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
    
    # Estimate duration for each section
    for section in sections:
        section["duration"] = helpers.estimate_duration(section["narration"])
    title = input_data.get("topic", "Generated Video Script")
    if sections and sections[0].get("heading"):
        title = sections[0]["heading"]
    output = {
        "title": title,
        "sections": sections,
        "meta": {
            **input_data.get("meta", {}),  # Preserve original meta (tts, image configs)
            "model": model_name,
            "topic": input_data.get("topic", ""),
            "keywords": input_data.get("keywords", []),
            "prompt": input_data.get("prompt", ""),
            "generated_at": datetime.now().isoformat()
        }
    }
    # Save intermediate JSON
    scripts_dir = os.path.join(output_dir, "scripts")
    os.makedirs(scripts_dir, exist_ok=True)
    script_json_path = os.path.join(scripts_dir, "script.json")
    with open(script_json_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"[Step 1] Script generated and saved to {script_json_path}")
    return output

# --- Step 2: Voice Generation (Gemini, Coqui, eSpeak) ---
def generate_voice(script_data, output_dir):
    """Generate voice audio for each section (Step 2)."""
    meta = script_data.get("meta", {})
    tts_config = meta.get("tts", {})
    tts_engine = tts_config.get("tts_engine", "espeak").lower()  # Default to eSpeak for demo
    model = tts_config.get("model", None)
    voice = tts_config.get("voice", None)
    meta_topic = meta.get("topic", "output")
    audio_dir = os.path.join(output_dir, "audio")
    os.makedirs(audio_dir, exist_ok=True)
    sections = script_data["sections"]
    for idx, section in enumerate(tqdm(sections, desc="[Step 2] Generating voice", unit="section"), 1):
        heading = section["heading"]
        narration = section["narration"]
        safe_heading = heading.replace(" ", "_").replace(":", "").replace("?", "").replace("!", "")
        filename = f"{idx:02d}_{safe_heading}.wav"
        output_path = os.path.join(audio_dir, filename)
        try:
            if tts_engine == "gemini":
                tts_gemini(narration, output_path, model, voice)
            elif tts_engine == "coqui":
                if COQUI_AVAILABLE:
                    tts_coqui(narration, output_path, model, voice)
                else:
                    print(f"[WARNING] Coqui TTS not available, falling back to eSpeak for section {idx}")
                    tts_espeak(narration, output_path, model, voice)
            elif tts_engine == "espeak":
                tts_espeak(narration, output_path, model, voice)
            elif tts_engine == "azure":
                if AZURE_AVAILABLE:
                    tts_azure(narration, output_path, model, voice)
                else:
                    print(f"[WARNING] Azure TTS not available, falling back to eSpeak for section {idx}")
                    tts_espeak(narration, output_path, model, voice)
            elif tts_engine == "googlecloud":
                if GOOGLECLOUD_AVAILABLE:
                    tts_googlecloud(narration, output_path, model, voice)
                else:
                    print(f"[WARNING] Google Cloud TTS not available, falling back to eSpeak for section {idx}")
                    tts_espeak(narration, output_path, model, voice)
            elif tts_engine == "elevenlabs":
                if ELEVENLABS_AVAILABLE:
                    tts_elevenlabs(narration, output_path, model, voice)
                else:
                    print(f"[WARNING] ElevenLabs TTS not available, falling back to eSpeak for section {idx}")
                    tts_espeak(narration, output_path, model, voice)
            else:
                raise ValueError(f"Unknown tts_engine: {tts_engine}. Supported: gemini, coqui, espeak, azure, googlecloud, elevenlabs")
            section["sound_file"] = os.path.relpath(output_path, audio_dir)
        except Exception as e:
            print(f"[ERROR] Voice generation failed for section {idx}: {e}")
            sys.exit(1)
    # Save intermediate JSON
    voice_json_path = os.path.join(audio_dir, "voice.json")
    with open(voice_json_path, "w") as f:
        json.dump(script_data, f, indent=2)
    print(f"[Step 2] Voice generated and saved to {voice_json_path}")
    return script_data

# --- Step 3: Image Generation (DALL-E, Stable Diffusion) ---
def generate_images(voice_data, output_dir):
    """Generate images for each section (Step 3)."""
    meta = voice_data.get('meta', {})
    image_config = meta.get('image', {})
    image_engine = image_config.get('image_engine', 'dalle').lower()
    model = image_config.get('model', 'dall-e-3')
    size = image_config.get('size', '1024x1024')
    quality = image_config.get('quality', 'standard')
    topic = meta.get('topic', '')
    keywords = meta.get('keywords', [])
    
    print(f"[DEBUG] generate_images - meta: {meta}")
    print(f"[DEBUG] generate_images - image_config: {image_config}")
    print(f"[DEBUG] generate_images - image_engine: {image_engine}")
    
    images_dir = os.path.join(output_dir, "images")
    os.makedirs(images_dir, exist_ok=True)
    sections = voice_data["sections"]
    for idx, section in enumerate(tqdm(sections, desc="[Step 3] Generating images", unit="section"), 1):
        heading = section.get('heading', f'Section {idx}')
        prompt = helpers.create_prompt_from_section(section, topic, keywords)
        safe_heading = "".join(c for c in heading if c.isalnum() or c in (' ', '-', '_')).rstrip()
        image_filename = f"{idx:02d}_{safe_heading}.png"
        image_path = os.path.join(images_dir, image_filename)
        try:
            print(f"[DEBUG] Section {idx} - Using image_engine: {image_engine}")
            if image_engine == 'dalle':
                print(f"[DEBUG] Section {idx} - Executing DALL-E path")
                try:
                    from image_engines.dalle import generate_dalle_image
                except ImportError:
                    raise RuntimeError("DALL-E not available (requires openai package)")
                generate_dalle_image(prompt, image_path, model, size, quality)
            elif image_engine == 'stable_diffusion':
                print(f"[DEBUG] Section {idx} - Executing Stable Diffusion path")
                if STABLE_DIFFUSION_AVAILABLE:
                    generate_sd_image(prompt, image_path, model)
                else:
                    raise RuntimeError("Stable Diffusion not available (requires diffusers package)")
            elif image_engine == 'unsplash':
                print(f"[DEBUG] Section {idx} - Executing Unsplash path")
                if UNSPLASH_AVAILABLE:
                    generate_unsplash_image(prompt, image_path)
                else:
                    raise RuntimeError("Unsplash not available (requires requests package)")
            else:
                raise ValueError(f"Unknown image_engine: {image_engine}. Supported: dalle, stable_diffusion, unsplash")
            section['image_file'] = os.path.relpath(image_path, images_dir)
        except Exception as e:
            print(f"[ERROR] Image generation failed for section {idx}: {e}")
            sys.exit(1)
    # Save intermediate JSON
    images_json_path = os.path.join(images_dir, "images.json")
    with open(images_json_path, "w") as f:
        json.dump(voice_data, f, indent=2)
    print(f"[Step 3] Images generated and saved to {images_json_path}")
    return voice_data

# --- Step 4: Video Assembly (ffmpeg) ---
def make_section_video(img_path, audio_path, duration, out_path, resolution=(1280, 720)):
    try:
        # Create video from image with audio overlay
        video_stream = (
            ffmpeg
            .input(img_path, loop=1, t=duration)
            .filter('scale', resolution[0], resolution[1], force_original_aspect_ratio='decrease')
        )
        
        audio_stream = ffmpeg.input(audio_path)
        
        (
            ffmpeg
            .output(video_stream, audio_stream, out_path, vcodec='libx264', acodec='aac', pix_fmt='yuv420p', t=duration, r=24, shortest=None, y=None)
            .overwrite_output()
            .run(quiet=True)
        )
        return True
    except ffmpeg.Error as e:
        print(f"[ERROR] FFmpeg error for {img_path} + {audio_path}: {e.stderr.decode() if hasattr(e, 'stderr') else e}")
        return False

def assemble_video(image_data, output_dir):
    """Assemble the final video (Step 4)."""
    meta = image_data.get('meta', {})
    topic = meta.get('topic', 'Untitled')
    sections = image_data.get('sections', [])
    images_dir = os.path.join(output_dir, 'images')
    audio_dir = os.path.join(output_dir, 'audio')
    video_dir = os.path.join(output_dir, 'video')
    os.makedirs(video_dir, exist_ok=True)
    temp_dir = os.path.join(video_dir, 'temp_segments')
    os.makedirs(temp_dir, exist_ok=True)
    segment_paths = []
    for i, section in enumerate(sections):
        img_file = section.get('image_file')
        audio_file = section.get('sound_file')
        duration = section.get('duration')
        if not img_file or not audio_file or not duration:
            print(f"[WARN] Skipping section {i+1}: missing image/audio/duration.")
            continue
        img_path = os.path.join(images_dir, os.path.basename(img_file))
        audio_path = os.path.join(audio_dir, os.path.basename(audio_file))
        if not os.path.exists(img_path):
            print(f"[WARN] Image not found: {img_path}")
            continue
        if not os.path.exists(audio_path):
            print(f"[WARN] Audio not found: {audio_path}")
            continue
        segment_path = os.path.join(temp_dir, f"segment_{i+1:02d}.mp4")
        print(f"[Step 4] Creating segment {i+1}: {segment_path}")
        ok = make_section_video(img_path, audio_path, duration, segment_path)
        if ok:
            segment_paths.append(segment_path)
    if not segment_paths:
        print("[ERROR] No valid video segments to assemble.")
        sys.exit(1)
    # Create a file list for ffmpeg concat
    concat_file = os.path.join(temp_dir, 'concat_list.txt')
    with open(concat_file, 'w') as f:
        for seg in segment_paths:
            f.write(f"file '{os.path.abspath(seg)}'\n")
    # Concatenate segments
    final_video_path = os.path.join(video_dir, 'final_video.mp4')
    concat_cmd = (
        ffmpeg
        .input(concat_file, format='concat', safe=0)
        .output(final_video_path, c='copy', y=None)
    )
    try:
        print(f"[Step 4] Concatenating {len(segment_paths)} segments into {final_video_path}")
        concat_cmd.run(quiet=True)
        print(f"[Step 4] ✅ Video assembled and saved to: {final_video_path}")
    except ffmpeg.Error as e:
        print(f"[ERROR] Failed to concatenate video: {e.stderr.decode() if hasattr(e, 'stderr') else e}")
        sys.exit(1)
    # Clean up temp files
    shutil.rmtree(temp_dir)
    return final_video_path


def main():
    parser = argparse.ArgumentParser(description="Monolithic Automated Video Production Pipeline")
    parser.add_argument('--input', default='input.json', help='Path to input.json (default: input.json)')
    parser.add_argument('--output_dir', default='outputs', help='Directory to save all outputs (default: outputs)')
    parser.add_argument('--step', type=int, choices=[1, 2, 3, 4], help='Start pipeline from specific step (1=script, 2=voice, 3=images, 4=video)')
    parser.add_argument('--use_existing', help='Use existing data from specified output folder (e.g., "04_The_Loving_Vegetables_for_Kids")')
    args = parser.parse_args()

    print(f"[DEBUG] Input file: {args.input}")
    print(f"[DEBUG] Output directory: {args.output_dir}")
    print(f"[DEBUG] Starting from step: {args.step if args.step else '1 (full pipeline)'}")
    print(f"[DEBUG] Using existing data: {args.use_existing if args.use_existing else 'No'}")

    # If using existing data, load it and start from the specified step
    if args.use_existing:
        existing_data = load_existing_data(args.use_existing, args.output_dir)
        if args.step == 4:
            # Start directly at video assembly
            print("[INFO] Starting directly at Step 4: Video Assembly using existing data")
            final_video_path = assemble_video(existing_data, existing_data['output_dir'])
            print(f"\n✅ Video assembly complete! Final video: {final_video_path}")
            return
        elif args.step:
            print(f"[ERROR] Starting from step {args.step} with existing data is not yet implemented. Use --step 4 for video assembly only.")
            sys.exit(1)
        else:
            print("[ERROR] --use_existing requires --step to be specified. Use --step 4 for video assembly.")
            sys.exit(1)

    # Check if input file exists (only needed for full pipeline or steps 1-3)
    if not args.step or args.step < 4:
        if not os.path.exists(args.input):
            print(f"[ERROR] Input file not found: {args.input}")
            print("Please create an input.json file or specify a different file with --input")
            sys.exit(1)

        # Load input
        with open(args.input, 'r') as f:
            input_data = json.load(f)

        # Print input config debug
        print(f"[DEBUG] Input config: {json.dumps(input_data, indent=2)}")

        # Create numbered directory structure
        topic = input_data.get("topic", "Untitled")
        safe_topic = topic.replace(" ", "_").replace(":", "").replace("?", "").replace("!", "").replace(",", "")
        
        # Find next available number
        base_output_dir = args.output_dir
        os.makedirs(base_output_dir, exist_ok=True)
        
        counter = 1
        while True:
            numbered_dir = f"{counter:02d}_{safe_topic}"
            full_output_dir = os.path.join(base_output_dir, numbered_dir)
            if not os.path.exists(full_output_dir):
                break
            counter += 1
        
        os.makedirs(full_output_dir, exist_ok=True)
        print(f"[INFO] Output directory: {full_output_dir}")

        # Determine starting step
        start_step = args.step if args.step else 1

        # Step 1: Script Generation
        if start_step <= 1:
            print("[DEBUG] --- Step 1: Script Generation ---")
            script_data = generate_script(input_data, full_output_dir)
        else:
            print(f"[INFO] Skipping Step 1 (script generation) - starting from step {start_step}")
            # Load existing script data
            script_path = os.path.join(full_output_dir, "scripts", "script.json")
            if os.path.exists(script_path):
                with open(script_path, 'r') as f:
                    script_data = json.load(f)
            else:
                print(f"[ERROR] No existing script data found at {script_path}")
                sys.exit(1)

        # Step 2: Voice Generation
        if start_step <= 2:
            print("[DEBUG] --- Step 2: Voice Generation ---")
            tts_engine = input_data.get('meta', {}).get('tts', {}).get('tts_engine', 'espeak')
            print(f"[DEBUG] TTS engine: {tts_engine}")
            voice_data = generate_voice(script_data, full_output_dir)
        else:
            print(f"[INFO] Skipping Step 2 (voice generation) - starting from step {start_step}")
            # Load existing voice data
            voice_path = os.path.join(full_output_dir, "audio", "voice.json")
            if os.path.exists(voice_path):
                with open(voice_path, 'r') as f:
                    voice_data = json.load(f)
            else:
                print(f"[ERROR] No existing voice data found at {voice_path}")
                sys.exit(1)

        # Step 3: Image Generation
        if start_step <= 3:
            print("[DEBUG] --- Step 3: Image Generation ---")
            image_engine = input_data.get('meta', {}).get('image', {}).get('image_engine', 'dalle')
            print(f"[DEBUG] Image engine: {image_engine}")
            image_data = generate_images(voice_data, full_output_dir)
        else:
            print(f"[INFO] Skipping Step 3 (image generation) - starting from step {start_step}")
            # Load existing image data
            image_path = os.path.join(full_output_dir, "images", "images.json")
            if os.path.exists(image_path):
                with open(image_path, 'r') as f:
                    image_data = json.load(f)
            else:
                print(f"[ERROR] No existing image data found at {image_path}")
                sys.exit(1)

        # Step 4: Video Assembly
        print("[DEBUG] --- Step 4: Video Assembly ---")
        final_video_path = assemble_video(image_data, full_output_dir)

        print(f"\n✅ Pipeline complete! Final video: {final_video_path}")


def load_existing_data(existing_folder, base_output_dir):
    """Load existing data from a previous pipeline run."""
    existing_path = os.path.join(base_output_dir, existing_folder)
    if not os.path.exists(existing_path):
        print(f"[ERROR] Existing folder not found: {existing_path}")
        sys.exit(1)
    
    print(f"[INFO] Loading existing data from: {existing_path}")
    
    # Load script data
    script_path = os.path.join(existing_path, "scripts", "script.json")
    if not os.path.exists(script_path):
        print(f"[ERROR] Script data not found: {script_path}")
        sys.exit(1)
    
    with open(script_path, 'r') as f:
        script_data = json.load(f)
    
    # Load voice data
    voice_path = os.path.join(existing_path, "audio", "voice.json")
    if not os.path.exists(voice_path):
        print(f"[ERROR] Voice data not found: {voice_path}")
        sys.exit(1)
    
    with open(voice_path, 'r') as f:
        voice_data = json.load(f)
    
    # Load image data
    image_path = os.path.join(existing_path, "images", "images.json")
    if not os.path.exists(image_path):
        print(f"[ERROR] Image data not found: {image_path}")
        sys.exit(1)
    
    with open(image_path, 'r') as f:
        image_data = json.load(f)
    
    # Add the output directory to the data for video assembly
    image_data['output_dir'] = existing_path
    
    print(f"[INFO] Successfully loaded existing data with {len(image_data.get('sections', []))} sections")
    return image_data

if __name__ == "__main__":
    main() 
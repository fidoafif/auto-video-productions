# Automated Video Production Pipeline

## Overview
This project provides a modular, end-to-end pipeline for automated video production. It covers script generation, voice synthesis, image creation, and video assembly, all orchestrated with a single command.

## Features
- **One-command workflow:** From idea to final video in a single run
- **Modular architecture:** All core logic is in the `app/` package, with clear separation of concerns
- **Plugin system:** Easily add new TTS or image engines by dropping a file into the appropriate folder
- **Progress tracking & resumption:** Pipeline can resume from any step and tracks progress in output folders
- **Parallel processing:** Voice and image generation steps run concurrently for speed
- **Organized outputs:** All results are saved in a structured output directory
- **Extensible:** Add new TTS or image engines without modifying core code

## Directory Structure
```
app/
  __init__.py
  main.py
  config.py
  engines.py
  pipeline.py
  utils.py
  helpers.py
  tts_engines/
    tts_gemini.py
    tts_coqui.py
    tts_espeak.py
    tts_azure.py
    tts_googlecloud.py
    tts_elevenlabs.py
  image_engines/
    dalle.py
    stable_diffusion.py
    unsplash.py
docs/
  README.md
  IMPROVEMENTS.md
  PLUGIN_SYSTEM.md
tests/
  test_dummy.py
run.py
requirements.txt
input.json
outputs/
```

## Supported Engines & Requirements
| Engine         | Type   | Python Package(s)         | System/Cloud Requirements           |
|---------------|--------|--------------------------|-------------------------------------|
| Gemini        | TTS    | google-generativeai      | Gemini API key                      |
| Coqui         | TTS    | TTS                      | Python <=3.11 (not compatible with 3.12+) |
| eSpeak NG     | TTS    | (none)                   | espeak-ng system package            |
| Azure         | TTS    | azure-cognitiveservices-speech | Azure Speech API key/region   |
| GoogleCloud   | TTS    | google-cloud-texttospeech | Google Cloud credentials           |
| ElevenLabs    | TTS    | elevenlabs               | ElevenLabs API key                  |
| DALL-E        | Image  | openai, requests, Pillow | OpenAI API key                      |
| Stable Diff.  | Image  | diffusers, torch, Pillow | GPU recommended, model weights      |
| Unsplash      | Image  | requests, Pillow         | Unsplash API key                    |
| Video         | Video  | ffmpeg-python            | ffmpeg system package               |

## Quickstart
1. **Clone the repo and enter the project directory:**
   ```sh
   cd <project-root>
   ```
2. **(Recommended) Use a Python virtual environment:**
   ```sh
   python3 -m venv venv
   source venv/bin/activate
   ```
3. **Install requirements:**
   ```sh
   pip install -r requirements.txt
   ```
4. **Install system dependencies:**
   - ffmpeg (e.g., `brew install ffmpeg` or `sudo apt install ffmpeg`)
   - eSpeak NG (e.g., `brew install espeak` or `sudo apt install espeak-ng`)
5. **Set up your .env file:**
   - Add your API keys for the engines you want to use
6. **Prepare your input.json:** (see below for example)
7. **Run the pipeline:**
   ```sh
   python run.py
   ```
   Or with custom input/output:
   ```sh
   python run.py --input my_input.json --output_dir my_outputs/
   ```

## Example input.json
```json
{
  "topic": "The Loving Vegetables for Kids",
  "keywords": ["vegetables", "kids", "healthy eating"],
  "prompt": "Write a fun, educational script for children about the superpowers of vegetables.",
  "duration": 3,
  "model": "models/gemini-1.5-pro-latest",
  "meta": {
    "tts": {"engine": "espeak", "model": null, "voice": null},
    "image": {"engine": "dalle", "model": "dall-e-3", "size": "1024x1024", "quality": "standard"}
  }
}
```

## Output Structure
```
outputs/
  01_The_Loving_Vegetables_for_Kids/
    scripts/
      script.json
    audio/
      01_Intro.wav
      ...
      voice.json
    images/
      01_Intro.png
      ...
      images.json
    video/
      final_video.mp4
```

## Troubleshooting
- **Missing dependencies:** Install with `pip install -r requirements.txt`
- **TTS engine errors:** Ensure you have the correct Python version and system dependencies (see table above)
- **API errors:** Check your API keys and quotas

### Python Version Compatibility
- **Coqui TTS compatibility:** The TTS package requires Python <=3.11. If you're using Python 3.12+, you have these options:
  1. **Use a different TTS engine:** Switch to Gemini, eSpeak NG, Azure, GoogleCloud, or ElevenLabs
  2. **Create a Python 3.11 virtual environment:**
     ```sh
     # Install Python 3.11 (if not already installed)
     # On macOS: brew install python@3.11
     # On Ubuntu: sudo apt install python3.11
     
     # Create venv with Python 3.11
     python3.11 -m venv venv311
     source venv311/bin/activate
     pip install -r requirements.txt
     ```
  3. **Remove TTS from requirements:** Comment out the `TTS` line in `requirements.txt` if you don't need Coqui TTS

## Extending
- Add new TTS/image engines by dropping a new file into `app/tts_engines/` or `app/image_engines/` (see `docs/PLUGIN_SYSTEM.md`)
- No changes to core code required

## Documentation
- See `docs/IMPROVEMENTS.md` for architecture and refactor details
- See `docs/PLUGIN_SYSTEM.md` for plugin system usage

## License
[Your License Here]
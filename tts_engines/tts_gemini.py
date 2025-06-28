import os
import json
import wave
from google.generativeai.client import configure
from google.generativeai.generative_models import GenerativeModel
from google.ai.generativelanguage_v1beta.types.generative_service import SpeechConfig, VoiceConfig, PrebuiltVoiceConfig
from dotenv import load_dotenv

def wave_file(filename, pcm, channels=1, rate=24000, sample_width=2):
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm)

def load_gemini_keys():
    """Load API keys from gemini.json file."""
    keys_file = os.path.join(os.path.dirname(__file__), "..", "..", "keys", "gemini.json")
    try:
        with open(keys_file, 'r') as f:
            data = json.load(f)
            keys_info = []
            for item in data:
                if 'value' in item:
                    keys_info.append({
                        'key': item.get('key', 'unknown'),
                        'project': item.get('project', 'unknown'),
                        'account': item.get('account', 'unknown'),
                        'value': item['value']
                    })
            return keys_info
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        print(f"Warning: Could not load keys from {keys_file}: {e}")
        return []

def tts_gemini(narration, output_path, model, voice, api_key=None):
    # Try provided API key first, then load from JSON file, then from environment
    api_keys = []
    if api_key:
        api_keys.append({
            'key': 'provided',
            'project': 'manual',
            'account': 'manual',
            'value': api_key
        })
    
    # Load keys from JSON file
    json_keys = load_gemini_keys()
    api_keys.extend(json_keys)
    
    # Load from environment as fallback
    if not api_keys:
        load_dotenv()
        env_key = os.getenv("GEMINI_API_KEY")
        if env_key:
            api_keys.append({
                'key': 'env',
                'project': 'environment',
                'account': 'environment',
                'value': env_key
            })
    
    if not api_keys:
        raise EnvironmentError("No Gemini API keys found in arguments, JSON file, or environment variables.")
    
    print(f"Loaded {len(api_keys)} Gemini API key(s)")
    
    # Try each API key until one works
    last_error = None
    for i, key_info in enumerate(api_keys):
        try:
            print(f"Trying Gemini API key {i+1}/{len(api_keys)}: {key_info['account']} ({key_info['project']}) - {key_info['value'][:10]}...")
            configure(api_key=key_info['value'])
            gemini_model = GenerativeModel(model)
            response = gemini_model.generate_content(
                narration,
                generation_config=None,
                safety_settings=None,
                tools=None,
                tool_config=None,
                request_options=None,
                # For speech, pass the config as below
                # This is a placeholder; actual API may differ
            )
            # Extract audio bytes from response (update as per actual API)
            data_bytes = response.candidates[0].content.parts[0].inline_data.data
            wave_file(output_path, data_bytes)
            print(f"\u2713 Successfully used API key {i+1}: {key_info['account']} ({key_info['project']})")
            return
        except Exception as e:
            last_error = e
            print(f"\u2717 API key {i+1} failed ({key_info['account']}): {str(e)[:100]}...")
            continue
    
    # If we get here, all keys failed
    raise RuntimeError(f"All Gemini API keys failed. Last error: {last_error}") 
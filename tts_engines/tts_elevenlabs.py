import os
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs


def tts_elevenlabs(narration, output_path, model=None, voice=None, api_key=None):
    """
    Generate speech using ElevenLabs TTS API and save as a .wav file.
    Args:
        narration (str): The text to synthesize.
        output_path (str): Path to save the .wav file.
        model (str, optional): Model ID (e.g., 'eleven_multilingual_v2').
        voice (str, optional): Voice name or ID.
        api_key (str, optional): ElevenLabs API key. If None, loads from env.
    """
    if api_key is None:
        load_dotenv()
        api_key = os.getenv("ELEVENLABS_API_KEY")
    print("Using ElevenLabs API key:", (api_key[:6] + '...' if api_key else 'MISSING'))
    if not api_key:
        raise EnvironmentError("ELEVENLABS_API_KEY not found in environment variables.")

    client = ElevenLabs(api_key=api_key)

    # Get all voices and resolve voice name to ID if needed
    voices = client.voices.get_all().voices
    voice_id = None
    if voice:
        for v in voices:
            if v.voice_id == voice or (v.name and v.name.lower() == voice.lower()):
                voice_id = v.voice_id
                break
    if not voice_id and voices:
        voice_id = voices[0].voice_id  # fallback to first available

    if not voice_id:
        raise ValueError(f"No valid ElevenLabs voice found for '{voice}'.")

    # Generate audio (returns an iterator of bytes)
    try:
        audio_chunks = client.text_to_speech.convert(
            voice_id=voice_id,
            text=narration,
            model_id=model or None,
            output_format="pcm_44100"
        )
        with open(output_path, "wb") as f:
            for chunk in audio_chunks:
                f.write(chunk)
    except Exception as e:
        if "quota" in str(e).lower() or "limit" in str(e).lower():
            raise RuntimeError("ElevenLabs quota or limit exceeded. Check your plan and usage.")
        raise 
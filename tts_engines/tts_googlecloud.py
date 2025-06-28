import os
from google.cloud import texttospeech
from dotenv import load_dotenv

def tts_googlecloud(narration, output_path, model=None, voice=None, api_key_path=None):
    """
    Generate speech using Google Cloud Text-to-Speech API and save as a .wav file.
    Args:
        narration (str): The text to synthesize.
        output_path (str): Path to save the .wav file.
        model (str, optional): Voice model (e.g., 'en-US-Wavenet-D').
        voice (str, optional): Voice name (e.g., 'en-US-Wavenet-D').
        api_key_path (str, optional): Path to service account JSON. If None, uses env var.
    """
    if api_key_path:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = api_key_path
    else:
        load_dotenv()
    client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=narration)
    voice_params = texttospeech.VoiceSelectionParams(
        language_code=voice[:5] if voice else "en-US",
        name=voice or model or "en-US-Wavenet-D"
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.LINEAR16
    )
    try:
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice_params,
            audio_config=audio_config
        )
        with open(output_path, "wb") as out:
            out.write(response.audio_content)
    except Exception as e:
        if "quota" in str(e).lower() or "limit" in str(e).lower():
            raise RuntimeError("Google Cloud TTS quota or limit exceeded. Check your plan and usage.")
        raise 
import os
from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk

def tts_azure(narration, output_path, model=None, voice=None, api_key=None, region=None):
    """
    Generate speech using Azure Cognitive Services TTS and save as a .wav file.
    Args:
        narration (str): The text to synthesize.
        output_path (str): Path to save the .wav file.
        model (str, optional): Not used (for API compatibility).
        voice (str, optional): Voice name (e.g., 'en-US-AriaNeural').
        api_key (str, optional): Azure Speech API key. If None, loads from env.
        region (str, optional): Azure region. If None, loads from env.
    """
    load_dotenv()
    api_key = api_key or os.getenv("AZURE_SPEECH_KEY")
    region = region or os.getenv("AZURE_SPEECH_REGION")
    if not api_key or not region:
        raise EnvironmentError("AZURE_SPEECH_KEY and AZURE_SPEECH_REGION must be set.")
    speech_config = speechsdk.SpeechConfig(subscription=api_key, region=region)
    if voice:
        speech_config.speech_synthesis_voice_name = voice
    audio_config = speechsdk.audio.AudioOutputConfig(filename=output_path)
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
    try:
        result = synthesizer.speak_text_async(narration).get()
        if result.reason != speechsdk.ResultReason.SynthesizingAudioCompleted:
            raise RuntimeError(f"Azure TTS failed: {result.reason}")
    except Exception as e:
        if "quota" in str(e).lower() or "limit" in str(e).lower():
            raise RuntimeError("Azure TTS quota or limit exceeded. Check your plan and usage.")
        raise 
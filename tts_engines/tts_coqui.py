import TTS

def tts_coqui(narration, output_path, model, voice):
    # Use Coqui TTS to generate speech
    tts = TTS.TTS(model_name=model)
    tts.tts_to_file(text=narration, file_path=output_path, speaker=voice) 
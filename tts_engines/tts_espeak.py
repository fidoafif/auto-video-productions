import subprocess
import shutil

def tts_espeak(narration, output_path, model=None, voice=None):
    # Auto-detect espeak or espeak-ng
    espeak_cmd = shutil.which("espeak") or shutil.which("espeak-ng")
    if not espeak_cmd:
        raise RuntimeError("Neither 'espeak' nor 'espeak-ng' was found in your PATH. Please install one of them.")
    # eSpeak voice selection: e.g., 'en', 'en-us', 'en+f3' (female), etc.
    voice_arg = ["-v", voice] if voice else []
    cmd = [espeak_cmd] + voice_arg + ["-w", output_path, narration]
    subprocess.run(cmd, check=True) 
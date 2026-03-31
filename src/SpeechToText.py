from faster_whisper import WhisperModel
import torch
import shutil

class Whisper :

    def __init__(self):
        print("[Whisper] Initializing model.")
        global whisper

        self._check_dependencies()

        if torch.cuda.is_available() :
            whisper = WhisperModel("turbo", device="cuda", compute_type="float16")
        else :
            whisper = WhisperModel("turbo", device="cpu", compute_type="int8")
        print("[Whisper] Model initialized.")

    
    def _check_dependencies():
        if shutil.which("ffmpeg") is None:
            raise EnvironmentError("ffmpeg est introuvable. Installe-le et assure-toi qu'il est dans le PATH.")

    def transcribe_wav(wav_path: str) -> str:
        if whisper is None:
            raise RuntimeError("Whisper n'est pas initialisé. Appelez init_whisper() d'abord.")
        
        segments, _ = whisper.transcribe(wav_path, language="fr")
        return " ".join(segment.text.strip() for segment in segments)
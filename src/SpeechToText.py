from faster_whisper import WhisperModel
import torch
import shutil
from time import time

class Whisper :

    # Text colors
    DEFAULT = '\033[0m'
    RED     = '\033[91m'
    GREEN   = '\033[92m'
    YELLOW  = '\033[93m'
    BLUE    = '\033[94m'
    PURPLE  = '\033[95m'

    def __init__(self):
        print("[Whisper] Initializing model.")
        global whisper

        self._check_dependencies()

        if torch.cuda.is_available() :
            whisper = WhisperModel("turbo", device="cuda", compute_type="float16")
        else :
            whisper = WhisperModel("turbo", device="cpu", compute_type="int8")
        print("[Whisper] Model initialized.")

    
    def _check_dependencies(self):
        if shutil.which("ffmpeg") is None:
            raise EnvironmentError("ffmpeg est introuvable. Installe-le et assure-toi qu'il est dans le PATH.")

    def transcribe_wav(self, wav_path: str) -> str:
        print(f"{time():.2f}" + self.PURPLE + f" [Whisper] Beginning transcription of file {wav_path}" + self.DEFAULT)
        if whisper is None:
            raise RuntimeError("Whisper n'est pas initialisé. Appelez init_whisper() d'abord.")
        
        segments, _ = whisper.transcribe(wav_path, language="fr")
        text_buffer = "".join(segment.text.strip() for segment in segments)
        print(f"{time():.2f}" + self.RED + f" [Whisper] {wav_path} converted to new text buffer : {text_buffer}" + self.DEFAULT)
        return text_buffer


if __name__ == "__main__" :
    stt = Whisper()
    start_time = time()
    stt.transcribe("../recordings/callRecord_0_0.wav")
    end_time = start_time -time()
    print(f"Finished transcribing audio buffer, took {end_time} seconds")
"""
RealTimeAudioRecorder — Cross-platform (Windows / Linux)
=========================================================
Dépendances :
    pip install soundcard sounddevice numpy

Sur Linux, soundcard utilise PulseAudio ou PipeWire pour le loopback.
Sur Windows, soundcard utilise WASAPI.

Utilisation :
    recorder = RealTimeAudioRecorder()
    recorder.record()
    ...
    recorder.stop_recording()
"""

import os
import sys
from time import time
import wave
import threading
import numpy as np

import soundcard as sc
import sounddevice as sd

GREEN   = "\033[92m"
YELLOW  = "\033[93m"
CYAN    = "\033[96m"
RED     = "\033[91m"
DEFAULT = "\033[0m"


# ───────────────────────── main class ───────────────────────────

class RealTimeAudioRecorder:
    """
    Enregistre simultanément le microphone et la sortie audio système (loopback),
    mélange les deux flux et sauvegarde le résultat en fichiers .wav de BUFFER secondes.

    Méthodes publiques
    ------------------
    record()            Lance l'enregistrement en arrière-plan (non bloquant).
    stop_recording()    Arrête l'enregistrement proprement.
    register_callback() Enregistre un callback appelé à chaque nouveau fichier sauvegardé.

    Propriété
    ---------
    LastOutputFilepath  Chemin du dernier fichier .wav sauvegardé.
    """

    # ── Paramètres audio ──────────────────────────────────────────
    RATE     = 44100   # Hz — taux d'échantillonnage cible des fichiers de sortie
    CHANNELS = 2       # Stéréo
    BUFFER   = 5       # Durée de chaque fichier .wav (secondes)

    # ── Paramètres de fichiers ────────────────────────────────────
    OUTPUT_DIR = "recordings"
    BASE_NAME  = "callRecord"

    def __init__(self):
        self._recording      : bool            = False
        self._callback                         = None
        self._LastOutputFilepath               = None

        self._speaker_thread : threading.Thread | None = None
        self._mic_thread     : threading.Thread | None = None
        self._mixer_thread   : threading.Thread | None = None

        # Buffers partagés  {buf_id: np.ndarray (int32, stereo aplati)}
        self._speaker_buf : dict[int, np.ndarray] = {}
        self._mic_buf     : dict[int, np.ndarray] = {}
        self._spk_lock    = threading.Lock()
        self._mic_lock    = threading.Lock()

        # File des IDs prêts à mixer
        self._ready_ids   : list[int]          = []
        self._ready_lock  = threading.Lock()
        self._ready_event = threading.Event()
        self._done_event  = threading.Event()   # recorders terminés

        self._output_prefix = self._next_output_prefix()

    # ══════════════════════════════════════════════════════════════
    #  Méthodes publiques
    # ══════════════════════════════════════════════════════════════

    def record(self) -> None:
        """Lance l'enregistrement en arrière-plan (non bloquant)."""
        if self._recording:
            raise RuntimeError("Un enregistrement est déjà en cours.")

        self._reset_state()
        self._output_prefix = self._next_output_prefix()
        self._recording = True

        print(f"{time():.2f} {YELLOW}[REC]     Démarrage — sortie : {self._output_prefix}*.wav {DEFAULT}", flush=True)
        print(f"{time():.2f} {YELLOW}[REC]     Durée par buffer : {self.BUFFER}s  |  Taux : {self.RATE} Hz  |  Canaux : {self.CHANNELS} {DEFAULT}", flush=True)

        self._speaker_thread = threading.Thread(target=self._record_speaker, daemon=True, name="Speaker")
        self._mic_thread     = threading.Thread(target=self._record_mic,     daemon=True, name="Mic")
        self._mixer_thread   = threading.Thread(target=self._mix_and_save,   daemon=True, name="Mixer")

        self._speaker_thread.start()
        self._mic_thread.start()
        self._mixer_thread.start()

    def stop_recording(self) -> None:
        """Arrête l'enregistrement et attend la fin propre de tous les threads."""
        if not self._recording:
            raise RuntimeError("Aucun enregistrement en cours.")

        print(f"{time():.2f} {YELLOW}[REC]     Arrêt demandé… {DEFAULT}", flush=True)
        self._recording = False

        self._speaker_thread.join()
        self._mic_thread.join()

        # Signaler au mixer qu'il n'y aura plus de buffers
        self._done_event.set()
        self._ready_event.set()
        self._mixer_thread.join()

        print(f"{time():.2f} {YELLOW}[REC]     Tous les threads terminés. {DEFAULT}", flush=True)

    def register_callback(self, callback) -> None:
        """Enregistre un callable appelé avec le chemin de chaque nouveau fichier .wav."""
        self._callback = callback
        print(f"{time():.2f} {YELLOW}[REC]     Callback enregistré. {DEFAULT}", flush=True)

    # ── Propriété LastOutputFilepath ──────────────────────────────

    @property
    def LastOutputFilepath(self) -> str | None:
        return self._LastOutputFilepath

    @LastOutputFilepath.setter
    def LastOutputFilepath(self, value: str) -> None:
        self._LastOutputFilepath = value
        if self._callback:
            self._callback(value)

    # ══════════════════════════════════════════════════════════════
    #  Méthodes privées — utilitaires
    # ══════════════════════════════════════════════════════════════

    def _reset_state(self) -> None:
        self._speaker_buf.clear()
        self._mic_buf.clear()
        self._ready_ids.clear()
        self._ready_event.clear()
        self._done_event.clear()

    def _next_output_prefix(self) -> str:
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)
        i = 0
        while os.path.isfile(os.path.join(self.OUTPUT_DIR, f"{self.BASE_NAME}_{i}_0.wav")):
            i += 1
        return os.path.join(self.OUTPUT_DIR, f"{self.BASE_NAME}_{i}_")

    def _notify_ready(self, buf_id: int) -> None:
        """Ajoute buf_id à la file du mixer si les deux sources sont disponibles."""
        with self._spk_lock:
            has_spk = buf_id in self._speaker_buf
        with self._mic_lock:
            has_mic = buf_id in self._mic_buf
        if has_spk and has_mic:
            with self._ready_lock:
                if buf_id not in self._ready_ids:
                    self._ready_ids.append(buf_id)
            self._ready_event.set()

    @staticmethod
    def _to_stereo_int32(arr: np.ndarray, channels: int) -> np.ndarray:
        """Convertit un tableau float32 (frames × ch) en int32 aplati stéréo."""
        # soundcard retourne (frames, channels) en float32 dans [-1, 1]
        if channels == 1:
            arr = np.repeat(arr, 2, axis=1)   # mono → stéréo
        elif channels > 2:
            arr = arr[:, :2]                   # ne garder que L + R
        int32 = (arr * 32767).astype(np.int32)
        return int32.flatten()                 # [L0, R0, L1, R1, …]

    @staticmethod
    def _resample_if_needed(arr: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
        """Rééchantillonnage linéaire simple si les taux diffèrent."""
        if src_rate == dst_rate:
            return arr
        factor      = dst_rate / src_rate
        old_len     = arr.shape[0]
        new_len     = int(old_len * factor)
        old_indices = np.arange(old_len)
        new_indices = np.linspace(0, old_len - 1, new_len)
        if arr.ndim == 1:
            return np.interp(new_indices, old_indices, arr).astype(arr.dtype)
        # Plusieurs canaux
        return np.column_stack([
            np.interp(new_indices, old_indices, arr[:, c]).astype(arr.dtype)
            for c in range(arr.shape[1])
        ])

    # ══════════════════════════════════════════════════════════════
    #  Threads d'enregistrement
    # ══════════════════════════════════════════════════════════════

    def _record_speaker(self) -> None:
        """Capture la sortie audio système (loopback) via soundcard."""
        try:
            loopback = sc.get_microphone(
                id=str(sc.default_speaker().name),
                include_loopback=True
            )
        except Exception as e:
            print(f"{time():.2f} {RED}[Speaker] Impossible d'ouvrir le loopback : {e} {DEFAULT}", flush=True)
            return

        frames_needed = self.BUFFER * self.RATE
        print(f"{time():.2f} [Speaker] Device : {loopback.name} ", flush=True)

        buf_id = 0
        with loopback.recorder(samplerate=self.RATE, channels=self.CHANNELS) as rec:
            print(f"{time():.2f} [Speaker] Enregistrement démarré. ", flush=True)
            while self._recording:
                data = rec.record(numframes=frames_needed)  # bloquant ~BUFFER s
                arr  = self._to_stereo_int32(data, data.shape[1])
                with self._spk_lock:
                    self._speaker_buf[buf_id] = arr
                print(f"{time():.2f} [Speaker] Buffer {buf_id} capturé ", flush=True)
                self._notify_ready(buf_id)
                buf_id += 1

        print(f"{time():.2f} [Speaker] Arrêté.", flush=True)

    def _record_mic(self) -> None:
        """Capture le microphone via soundcard."""
        try:
            mic = sc.default_microphone()
        except Exception as e:
            print(f"{time():.2f} [Mic]     Impossible d'ouvrir le microphone : {e}", flush=True)
            return

        frames_needed = self.BUFFER * self.RATE
        print(f"{time():.2f} [Mic]     Device : {mic.name}", flush=True)

        buf_id = 0
        with mic.recorder(samplerate=self.RATE, channels=self.CHANNELS) as rec:
            print(f"{time():.2f} [Mic]     Enregistrement démarré.", flush=True)
            while self._recording:
                data = rec.record(numframes=frames_needed)
                arr  = self._to_stereo_int32(data, data.shape[1])
                with self._mic_lock:
                    self._mic_buf[buf_id] = arr
                print(f"{time():.2f} [Mic]     Buffer {buf_id} capturé ", flush=True)
                self._notify_ready(buf_id)
                buf_id += 1

        print(f"{time():.2f} [Mic]     Arrêté. ", flush=True)

    # ══════════════════════════════════════════════════════════════
    #  Thread de mixage et sauvegarde
    # ══════════════════════════════════════════════════════════════

    def _mix_and_save(self) -> None:
        """Mélange les buffers speaker + mic et les sauvegarde en .wav."""
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)

        while True:
            self._ready_event.wait(timeout=0.2)
            self._ready_event.clear()

            # Vider la file
            while True:
                with self._ready_lock:
                    if not self._ready_ids:
                        break
                    buf_id = self._ready_ids.pop(0)

                with self._spk_lock:
                    spk = self._speaker_buf.pop(buf_id)
                with self._mic_lock:
                    mic = self._mic_buf.pop(buf_id)

                # Aligner les longueurs
                length = max(len(spk), len(mic))
                if len(spk) < length:
                    spk = np.pad(spk, (0, length - len(spk)))
                if len(mic) < length:
                    mic = np.pad(mic, (0, length - len(mic)))

                mixed = np.clip(spk + mic, -32768, 32767).astype(np.int16)

                filepath = self._output_prefix + str(buf_id) + ".wav"
                with wave.open(filepath, "wb") as wf:
                    wf.setnchannels(self.CHANNELS)
                    wf.setsampwidth(2)           # 16 bits = 2 octets
                    wf.setframerate(self.RATE)
                    wf.writeframes(mixed.tobytes())

                print(f"{time():.2f} {GREEN}[Mixer]   Buffer {buf_id} sauvegardé → {filepath} {DEFAULT}", flush=True)
                self.LastOutputFilepath = filepath

            # Sortir uniquement quand les recorders sont finis ET la file est vide
            if self._done_event.is_set():
                with self._ready_lock:
                    if not self._ready_ids:
                        break

        print(f"{time():.2f} {GREEN}[Mixer]   Terminé. {DEFAULT}", flush=True)


# ══════════════════════════════════════════════════════════════════
#  Point d'entrée
# ══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    recorder = RealTimeAudioRecorder()
    recorder.record()
    try:
        input("\nAppuyez sur Entrée pour arrêter…\n")
    except KeyboardInterrupt:
        pass
    recorder.stop_recording()
    # os._exit évite le nettoyage Python/PortAudio qui peut causer un segfault
    # sur certaines configurations Windows.  Tous les .wav sont fermés et
    # flushés à ce stade.
    os._exit(0)

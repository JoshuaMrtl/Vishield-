import os
import threading
from time import time, sleep
import FreeSimpleGUI as sg

from RealTimeAudioRecorder import RealTimeAudioRecorder
from SpeechToText import Whisper
from TextToNote import Bert
from interface import Interface

# --- VARIABLES GLOBALES ET CALLBACKS ---
score_history = []
is_active_call = False
is_closing_audio = False # Verrou pour empecher le redemarrage trop rapide

def on_new_file_saved(newFilepath):
    stt.transcribe_wav(newFilepath)

def on_new_text_buffer(text_buffer):
    ttn.predict_vishing(text_buffer)

def on_text_analyzed(value):
    global score_history, is_active_call
    
    if not is_active_call:
        return
        
    is_vishing = value[0]
    raw_confidence = value[1] 
    
    # Si c'est du vishing, le risque est la confiance (ex: 99%)
    # Si ce n'est PAS du vishing, le risque est l'inverse de la confiance (ex: 100 - 99% = 1%)
    vishing_prob = raw_confidence if is_vishing else (100 - raw_confidence)
    
    score_history.append(vishing_prob)
    
    if len(score_history) > 20:
        score_history.pop(0)
    
    ui.write_event_value('-UPDATE_UI_SCORE-', vishing_prob)

def _stop_recorder_safely(recorder_instance):
    """Ferme l'audio proprement et libere le verrou."""
    global is_closing_audio
    is_closing_audio = True
    try:
        recorder_instance.stop_recording()
        # Delai technique pour permettre aux pilotes OS de liberer les peripheriques
        sleep(0.5) 
    finally:
        is_closing_audio = False

# --- LOGIQUE PRINCIPALE ---

def main():
    global stt, ttn, ui, score_history, is_active_call, is_closing_audio
    recorder = None

    ui = Interface()

    try:
        stt = Whisper()
        stt.register_callback(on_new_text_buffer)
        ttn = Bert()
        ttn.register_callback(on_text_analyzed)
    except Exception as e:
        ui.show_error_popup(f"Erreur d'initialisation : {e}")

    while True:
        event, values = ui.read(timeout=100)

        if event == sg.WIN_CLOSED:
            break

        if ui.current_state == "HOME":
            if event == '-START_RECORDING-':
                # Empecher le demarrage si une fermeture est en cours
                if is_closing_audio:
                    print("[App] Attente de la liberation du microphone...")
                    continue

                # Reinitialiser l'etat de l'application
                ui.auto_cutoff_threshold = values['-THRESHOLD-']
                score_history = [0]
                is_active_call = True
                
                # Vider la memoire tampon de l'IA pour ne pas melanger les appels
                stt.bufferMemory.head = None
                stt.bufferNumber = 0
                
                ui.go_to_recording()
                recorder = RealTimeAudioRecorder()
                recorder.register_callback(on_new_file_saved)
                recorder.record()
                
            elif event == '-VIEW_HISTORY-':
                ui.go_to_history()

        elif ui.current_state == "RECORDING":
            if event == '-UPDATE_UI_SCORE-':
                if not is_active_call:
                    continue
                    
                current_score = values[event]
                ui.update_confidence_display(current_score)
                ui.update_score_graph(score_history)
                
                if current_score >= ui.auto_cutoff_threshold:
                    print(f"[AUTO-CUT] Seuil de {ui.auto_cutoff_threshold}% depasse. Coupure de l'appel.")
                    is_active_call = False
                    ui.go_to_alert()
                    if recorder:
                        threading.Thread(target=_stop_recorder_safely, args=(recorder,), daemon=True).start()

            elif event == '-STOP_RECORDING-':
                is_active_call = False
                ui.go_to_home()
                if recorder:
                    threading.Thread(target=_stop_recorder_safely, args=(recorder,), daemon=True).start()

        elif ui.current_state == "ALERT":
            if event == '-ALERT_OK-':
                ui.go_to_home()

        elif ui.current_state == "HISTORY":
            if event == '-BACK-':
                ui.go_to_home()
            elif event == '-PLAY-':
                sel = values.get('-FILE_LIST-')
                if sel: os.startfile(os.path.join("recordings", sel[0]))
            elif event == '-DELETE-':
                sel = values.get('-FILE_LIST-')
                if sel:
                    path = os.path.join("recordings", sel[0])
                    if os.path.exists(path):
                        os.remove(path)
                        ui.update_element('-FILE_LIST-', ui._get_audio_files())

    # Fermeture finale securisee
    if recorder and is_active_call:
        recorder.stop_recording()
    ui.close()

if __name__ == "__main__":
    main()
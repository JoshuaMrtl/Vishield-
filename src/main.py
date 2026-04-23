import FreeSimpleGUI as sg
from time import time

from RealTimeAudioRecorder import RealTimeAudioRecorder
from SpeechToText import Whisper
from TextToNote import Bert
from interface import Interface

__version__ = "1.0.3" # Buildozer info


# Text colors (console)
DEFAULT = '\033[0m'
RED     = '\033[91m'
GREEN   = '\033[92m'
YELLOW  = '\033[93m'
BLUE    = '\033[94m'
PURPLE  = '\033[95m'


# --- FONCTIONS CALLBACK ---

def on_new_file_saved(newFilepath):
    """Appelé par RealTimeAudioRecorder — transmet le fichier à Whisper."""
    stt.transcribe_wav(newFilepath)


def on_new_text_buffer(text_buffer):
    """Appelé par Whisper — transmet la transcription à Bert."""
    ttn.predict_vishing(text_buffer)


def on_text_analyzed(value):
    """
    Appelé par Bert — interprète le résultat et notifie l'interface.
    value : tuple (is_vishing: bool, confidence: float)
    """
    global number_of_analyzed_buffer

    is_vishing = value[0]   # Boolean
    confidence = value[1]   # Float

    if is_vishing:
        if confidence > 50:
            print(
                f"{time():.2f}" + BLUE +
                f" [App]     Buffer {number_of_analyzed_buffer}: "
                f"Vishing attack detected with {confidence:.2f}% confidence, stopping the call"
                + DEFAULT
            )
            ui.write_event_value('-VISHING_CONFIRMED-', confidence)
        else:
            print(
                f"{time():.2f}" + BLUE +
                f" [App]     Buffer {number_of_analyzed_buffer}: "
                f"Potential vishing attack, {confidence:.2f}% confidence"
                + DEFAULT
            )
            ui.write_event_value('-VISHING_PROBABLE-', confidence)
    else:
        print(
            f"{time():.2f}" + BLUE +
            f" [App]     Buffer {number_of_analyzed_buffer}: "
            f"no vishing attack detected, {confidence:.2f}% confidence"
            + DEFAULT
        )
        ui.write_event_value('-NO_VISHING-', confidence)

    number_of_analyzed_buffer += 1


# --- LOGIQUE PRINCIPALE ---

def main():
    global stt, ttn, ui, number_of_analyzed_buffer

    number_of_analyzed_buffer = 0
    recorder = None

    # Création de l'interface (état 1 — Off)
    ui = Interface()

    # Chargement de Whisper
    try:
        stt = Whisper()
        stt.register_callback(on_new_text_buffer)
    except Exception as e:
        ui.show_error_popup(
            f"Erreur lors du chargement de Whisper.\nErreur: {e}"
        )
        ui.go_to_state_1_off()

    # Chargement de Bert
    try:
        ttn = Bert()
        ttn.register_callback(on_text_analyzed)
    except Exception as e:
        ui.show_error_popup(
            f"Erreur lors du chargement de Bert.\nErreur: {e}"
        )
        ui.go_to_state_1_off()

    # Boucle d'événements
    while True:
        event, values = ui.read(timeout=100)

        if event == sg.WIN_CLOSED:
            break

        # --- État 1 : Off → démarrage ---
        if ui.current_state == 1 and event == '-START-':
            ui.go_to_state_2_transition()
            ui.refresh()   # force l'affichage avant le chargement éventuel

            ui.go_to_state_3_listening()

            recorder = RealTimeAudioRecorder()
            recorder.register_callback(on_new_file_saved)
            recorder.record()

        # --- État 3 : Écoute active ---
        elif ui.current_state == 3:

            # Simulation manuelle d'une transcription
            if event == '-ANALYZE-':
                texte_entendu = values['-SIMULATED_TEXT-']
                if texte_entendu.strip():
                    is_vishing, confidence = ttn.predict_vishing(texte_entendu)
                    print(
                        f"Analyse: '{texte_entendu}' | "
                        f"Vishing: {is_vishing} | Certitude: {confidence:.2f}%"
                    )
                    if is_vishing:
                        if confidence >= 85:
                            ui.go_to_state_5_alert_confirmed()
                        else:
                            ui.go_to_state_4_alert_probable()
                    else:
                        ui.update_element('-SIMULATED_TEXT-', '')

            # Déclenchement manuel ou détection probable par le modèle
            elif event in ('-MANUAL_ALERT-', '-VISHING_PROBABLE-'):
                ui.go_to_state_4_alert_probable()

            # Détection confirmée par le modèle (ou clic debug sur l'icône verte)
            elif event in ('-LISTENING_ICON-', '-VISHING_CONFIRMED-'):
                ui.go_to_state_5_alert_confirmed()

        # --- État 4 : Alerte probable → faux positif ---
        elif ui.current_state == 4 and event == '-FALSE_POS_4-':
            ui.go_to_state_1_off('Vishield - En Attente')
            if recorder:
                recorder.stop_recording()

        # --- État 5 : Alerte confirmée → retour accueil ---
        elif ui.current_state == 5 and event in ('-FALSE_POS_5-', '-CALLBACK-'):
            ui.go_to_state_1_off()
            if recorder:
                recorder.stop_recording()

    ui.close()


if __name__ == "__main__":
    main()

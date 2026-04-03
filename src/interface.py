import FreeSimpleGUI as sg

from RealTimeAudioRecorder import RealTimeAudioRecorder
from SpeechToText import Whisper
from TextToNote import Bert


# --- VARIABLES GLOBALES DU MODÈLE ---

stt = None # Instance of Speech To Text model (Whipser)
ttn = None # Instance of Text To Note model (Bert)

# --- CONFIGURATION DES COULEURS ET FONTS ---
THEME_COLOR = 'white'
TEXT_COLOR = '#2c3e50'
GRAY_BUTTON = '#95a5a6'
ORANGE_BUTTON = '#f1c40f'
GREEN_BUTTON = '#00c851'
RED_ALERT = '#e74c3c'
BLUE_ACTION = '#1e88e5'
DARK_GRAY = '#4a5568'
FONT_MAIN = ('Helvetica', 12)
FONT_TITLE = ('Helvetica', 16, 'bold')
FONT_ICON = ('Helvetica', 40)

sg.theme_background_color(THEME_COLOR)
sg.theme_text_element_background_color(THEME_COLOR)
sg.theme_element_background_color(THEME_COLOR)

# --- FONCTIONS CALLBACK ---

def on_new_file_saved(newFilepath) :
    # Calls Whisper when Mixer finishes its job
    global stt

    # print(f"[Callback]Nouveau fichier enregistré : {newFilepath}")
    stt.transcribe_wav(newFilepath)

def on_new_text_buffer(text_buffer) : 
    # Calls Bert when Whisper finishes its job
    global ttn

    ttn.predict_vishing(text_buffer)

# --- FONCTIONS DE LAYOUTS ---

def create_layout_1_off():
    return [
        [sg.VPush()],
        [sg.Button('⏻', key='-START-', font=FONT_ICON, button_color=('white', '#8e9eab'), border_width=0, size=(4, 2),  pad=(0,0))],
        [sg.VPush()]
    ]

def create_layout_2_transition():
    return [
        [sg.VPush()],
        [sg.Button('⏻', key='-TRANSITION-', font=FONT_ICON, button_color=('white', '#ffc107'), border_width=0, size=(4, 2), pad=(0,0))],
        [sg.Text('Chargement de l\'IA...', font=('Helvetica', 10), text_color=DARK_GRAY, pad=(0, 10))],
        [sg.VPush()]
    ]

def create_layout_3_listening():
    return [
        [sg.VPush()],
        [sg.Button('⏻', key='-LISTENING_ICON-', font=FONT_ICON, button_color=('white', '#00c851'), border_width=0, size=(4, 2), pad=(0,0))],
        [sg.Text('En écoute', font=('Helvetica', 14, 'bold'), text_color=TEXT_COLOR, pad=(0, 10))],
        
        # --- NOUVEAU : Zone pour simuler la transcription audio ---
        [sg.Input(key='-SIMULATED_TEXT-', size=(35, 1), justification='center', tooltip="Tapez une phrase à analyser")],
        [sg.Button('Simuler l\'audio', key='-ANALYZE-', button_color=('white', BLUE_ACTION), font=('Helvetica', 10, 'bold'), border_width=0, pad=(0,10))],
        
        [sg.VPush()],
        [sg.Button('Je reçois un appel frauduleux', key='-MANUAL_ALERT-', button_color=('white', '#d32f2f'), font=('Helvetica', 12, 'bold'), size=(30, 2), border_width=0, pad=(20, 40))]
    ]

def create_layout_4_alert_probable():
    anomalies = [
        "• Modèles de discours suspects",
        "• Création d'une situation urgente",
        "• Demande d'informations sensibles"
    ]
    layout = [
        [sg.VPush()],
        [sg.Text('⚠', font=('Helvetica', 80), text_color='#ff6f00', background_color=THEME_COLOR, pad=(0,0))],
        [sg.Text('Probable tentative de vishing', font=FONT_TITLE, text_color='#1a237e', pad=(0, 20))],
        [sg.Text('Anomalies détectées par l\'IA :', font=('Helvetica', 12, 'bold'), text_color=TEXT_COLOR, justification='left', pad=((20,0), 10))],
    ]
    for item in anomalies:
        layout.append([sg.Text(item, font=FONT_MAIN, text_color=DARK_GRAY, pad=((40,0), 5))])

    layout.append([sg.VPush()])
    layout.append([sg.Button('Faux positif', key='-FALSE_POS_4-', button_color=('white', DARK_GRAY), font=('Helvetica', 12, 'bold'), size=(30, 2), border_width=0, pad=(20, 40))])
    return layout

def create_layout_5_alert_confirmed():
    anomalies = [
        "• Extorsion financière détectée",
        "• Usurpation d'identité forte",
        "• Pression psychologique"
    ]
    layout = [
        [sg.VPush()],
        [sg.Text('⚠', font=('Helvetica', 80), text_color='#d50000', background_color=THEME_COLOR, pad=(0,0))],
        [sg.Text("Tentative de vishing détectée avec\ncertitude, l'appel a été interrompu", font=FONT_TITLE, text_color='#1a237e', justification='center', pad=(0, 20))],
        [sg.Text('Anomalies détectées par l\'IA :', font=('Helvetica', 12, 'bold'), text_color=TEXT_COLOR, justification='left', pad=((20,0), 10))],
    ]
    for item in anomalies:
        layout.append([sg.Text(item, font=FONT_MAIN, text_color=DARK_GRAY, pad=((40,0), 5))])

    layout.append([sg.VPush()])
    layout.append([
        sg.Button('Faux positif', key='-FALSE_POS_5-', button_color=('white', DARK_GRAY), font=('Helvetica', 11, 'bold'), size=(15, 2), border_width=0, pad=((20, 10), 40)),
        sg.Button('Rappeler', key='-CALLBACK-', button_color=('white', '#2962ff'), font=('Helvetica', 11, 'bold'), size=(15, 2), border_width=0, pad=((10, 20), 40))
    ])
    return layout


# --- LOGIQUE PRINCIPALE ---

def main():
    global stt, ttn
    
    window_size = (400, 600)
    layout = create_layout_1_off()
    window = sg.Window('Vishing Detector', layout, size=window_size, element_justification='c', finalize=True)
    current_state = 1
    
    try:
        stt = Whisper()
        stt.register_callback(on_new_text_buffer)

        ttn = Bert()
        
    except Exception as e:
        sg.popup_scrolled(
            f"Erreur lors du chargement du modèle.\n"
            f"Vérifie que le dossier 'TrainedBert' est bien placé.\n\n"
            f"Erreur: {e}",
            title="Erreur"
        )
        
        window.close()
        layout = create_layout_3_listening()
        window = sg.Window('Vishing Detector', layout, size=window_size, element_justification='c', finalize=True)
        current_state = 1

    while True:
        event, values = window.read(timeout=100)

        if event == sg.WIN_CLOSED:
            break

        # 1 -> 2 -> 3 (Allumage et Chargement du modèle)
        if current_state == 1 and event == '-START-':
            window.close()
            layout = create_layout_2_transition()
            window = sg.Window('Vishing Detector', layout, size=window_size, element_justification='c', finalize=True)
            current_state = 2
            
            # On force la fenêtre à s'afficher avant de geler l'interface avec le chargement
            window.refresh()

            window.close()
            layout = create_layout_3_listening()
            window = sg.Window('Vishing Detector', layout, size=window_size, element_justification='c', finalize=True)
            current_state = 3

            recorder = RealTimeAudioRecorder()
            recorder.register_callback(on_new_file_saved)
            recorder.record() # lance l'enregistrement avec RealTimeAudioRecorder.py

        # 3 -> Analyse par l'IA
        elif current_state == 3:
            
            # Si on clique sur le bouton "Simuler l'audio"
            if event == '-ANALYZE-':
                texte_entendu = values['-SIMULATED_TEXT-']
                
                if texte_entendu.strip():
                    # Appel au modèle BERT
                    is_vishing, confidence = ttn.predict_vishing(texte_entendu)
                    print(f"Analyse: '{texte_entendu}' | Vishing: {is_vishing} | Certitude: {confidence:.2f}%")
                    
                    if is_vishing:
                        # Si le modèle est très sûr (> 85%), on passe au rouge
                        if confidence >= 85:
                            window.close()
                            layout = create_layout_5_alert_confirmed()
                            window = sg.Window('Vishing Detector', layout, size=window_size, element_justification='c', finalize=True)
                            current_state = 5
                        # Si le modèle détecte du vishing mais avec un petit doute, on passe au orange
                        else:
                            window.close()
                            layout = create_layout_4_alert_probable()
                            window = sg.Window('Vishing Detector', layout, size=window_size, element_justification='c', finalize=True)
                            current_state = 4
                    else:
                        # Si tout est normal, on efface le champ texte pour la phrase suivante
                        window['-SIMULATED_TEXT-'].update('')
            
            # Déclenchement manuel
            elif event == '-MANUAL_ALERT-':
                window.close()
                layout = create_layout_4_alert_probable()
                window = sg.Window('Vishing Detector', layout, size=window_size, element_justification='c', finalize=True)
                current_state = 4
            
            # Triche (bouton vert) pour tester l'écran 5
            elif event == '-LISTENING_ICON-': 
                window.close()
                layout = create_layout_5_alert_confirmed()
                window = sg.Window('Vishing Detector', layout, size=window_size, element_justification='c', finalize=True)
                current_state = 5

        # Retour à l'état initial (Faux positifs)
        elif current_state == 4 and event == '-FALSE_POS_4-':
            window.close()
            layout = create_layout_1_off()
            window = sg.Window('Vishing Detector', layout, size=window_size, element_justification='c', finalize=True)

            recorder.stop_recording()
            
            current_state = 1

        elif current_state == 5:
            if event == '-FALSE_POS_5-' or event == '-CALLBACK-':
                window.close()
                layout = create_layout_1_off()
                window = sg.Window('Vishing Detector', layout, size=window_size, element_justification='c', finalize=True)

                recorder.stop_recording()

                current_state = 1

    window.close()

if __name__ == "__main__":
    main()
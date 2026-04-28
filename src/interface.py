import FreeSimpleGUI as sg
import os
import glob
from PIL import Image, ImageTk
import io

# Palette de couleurs "Dark Modern"
BG_COLOR      = '#121212'  # Fond très sombre
SURFACE_COLOR = '#1E1E1E'  # Surfaces (boutons, listes)
ACCENT_COLOR  = "#F85656"  # red néon
TEXT_COLOR    = '#E0E0E0'
DANGER_COLOR  = '#CF6679'  # Rouge doux (Material Design)
SUCCESS_COLOR = '#03DAC6'  # Cyan

FONT_MAIN    = ('Segoe UI', 11)
FONT_TITLE   = ('Segoe UI', 24, 'bold')
FONT_SUBTITLE = ('Segoe UI', 12)
FONT_PERCENT = ('Segoe UI', 54, 'bold')

class Interface:
    WINDOW_SIZE = (420, 680) 
    LOGO_FILENAME = 'logoNew.png' 

    def __init__(self):
        self.current_state = "HOME"
        self.auto_cutoff_threshold = 80
        # Configuration globale du theme pour les elements non explicites
        sg.theme_background_color(BG_COLOR)
        
        self.window = sg.Window(
            'Vishield', self._create_layout_home(),
            size=self.WINDOW_SIZE,
            background_color=BG_COLOR,
            element_justification='c',
            finalize=True,
            no_titlebar=False
        )

    def read(self, timeout=100):
        return self.window.read(timeout=timeout)

    def write_event_value(self, event, value):
        try:
            if self.window and not self.window.is_closed():
                self.window.write_event_value(event, value)
        except Exception:
            pass

    def update_element(self, key, value):
        if key in self.window.key_dict:
            self.window[key].update(value)

    def close(self):
        self.window.close()

    def _rebuild_window(self, title, layout, state):
        self.window.close()
        self.current_state = state
        self.window = sg.Window(
            title, layout,
            size=self.WINDOW_SIZE,
            background_color=BG_COLOR,
            element_justification='c',
            finalize=True
        )

    def go_to_home(self):
        self._rebuild_window('Vishield', self._create_layout_home(), "HOME")

    def go_to_recording(self):
        self._rebuild_window('Analyse Active', self._create_layout_recording(), "RECORDING")

    def go_to_history(self):
        self._rebuild_window('Historique', self._create_layout_history(), "HISTORY")

    def go_to_alert(self):
        self._rebuild_window('ALERTE', self._create_layout_alert(), "ALERT")

    # --- FONCTIONS D'AIDE VISUELLE (IMAGE ET GRAPH) ---

    def _get_image_data(self, filename, max_size=(180, 180)):
        """
        Charge un JPG, le redimensionne en gardant le ratio, 
        et le convertit en PNG en memoire compatible avec sg.Image.
        """
        try:
            if not os.path.exists(filename):
                print(f"[UI] Logo non trouve : {filename}")
                return None
                
            img = Image.open(filename)
            # Redimensionnement haute qualite (LANCZOS)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Sauvegarde en PNG dans un buffer memoire
            with io.BytesIO() as bio:
                img.save(bio, format="PNG")
                del img # Libere la memoire PIL
                return bio.getvalue()
        except Exception as e:
            print(f"[UI] Erreur lors du traitement du logo : {e}")
            return None

    def update_score_graph(self, history):
        graph = self.window['-SCORE_GRAPH-']
        graph.erase()
        if len(history) < 2:
            return
        x_step = 100 / (len(history) - 1)
        for i in range(len(history) - 1):
            p1 = (i * x_step, history[i])
            p2 = ((i + 1) * x_step, history[i+1])
            graph.draw_line(p1, p2, color=ACCENT_COLOR, width=2)

    def update_confidence_display(self, confidence):
        color = SUCCESS_COLOR
        if confidence > self.auto_cutoff_threshold:
            color = DANGER_COLOR
        elif confidence > 50:
            color = '#FFB74D' # Orange
        self.window['-CONFIDENCE-'].update(f"{confidence:.0f}%", text_color=color)

    def _get_audio_files(self):
        if not os.path.exists("recordings"): return []
        files = glob.glob(os.path.join("recordings", "*.wav"))
        return [os.path.basename(f) for f in files]

    # --- LAYOUTS (SCENES) ---

    def _create_layout_home(self):
        # Tentative de chargement du logo
        logo_data = self._get_image_data(self.LOGO_FILENAME)
        
        logo_row = []
        if logo_data:
            # Creation de l'element Image avec les donnees binaires
            logo_row = [sg.Image(data=logo_data, key='-LOGO-', background_color=BG_COLOR, pad=(0,(20,10)))]

        return [
            [sg.VPush(background_color=BG_COLOR)],
            
            logo_row, # Insertion du logo ici
            
            # Ajustement des espacements pour le style minimalist
            [sg.Text('VISHIELD', font=FONT_TITLE, text_color=ACCENT_COLOR, background_color=BG_COLOR, pad=(0,(0,5)))],
            [sg.Text('Protection IA contre le vishing', font=FONT_SUBTITLE, text_color=TEXT_COLOR, background_color=BG_COLOR, pad=(0,(0,30)))],
            
            [sg.VPush(background_color=BG_COLOR)],
            
            [sg.Frame('Sensibilite de coupure (%)', [
                [sg.Slider(range=(1, 100), default_value=self.auto_cutoff_threshold, 
                           orientation='h', key='-THRESHOLD-', background_color=BG_COLOR, 
                           text_color=TEXT_COLOR, trough_color=SURFACE_COLOR, size=(30, 20))]
            ], border_width=1, title_color=ACCENT_COLOR, background_color=BG_COLOR, pad=(0, 20))],
            
            [sg.Button('DEMARRER L\'ANALYSE', key='-START_RECORDING-', size=(30, 2), 
                       button_color=('black', ACCENT_COLOR), border_width=0, font=('Segoe UI', 11, 'bold'))],
            [sg.Button('HISTORIQUE', key='-VIEW_HISTORY-', size=(30, 2), 
                       button_color=(TEXT_COLOR, SURFACE_COLOR), border_width=0, font=FONT_MAIN, pad=(0,10))],
            
            [sg.VPush(background_color=BG_COLOR)]
        ]

    def _create_layout_recording(self):
        return [
            [sg.Text('ANALYSE EN COURS', font=('Segoe UI', 18, 'bold'), text_color=ACCENT_COLOR, background_color=BG_COLOR, pad=(0, 20))],
            [sg.Text('Risque detecte', font=FONT_MAIN, text_color=TEXT_COLOR, background_color=BG_COLOR)],
            [sg.Text('0%', key='-CONFIDENCE-', font=FONT_PERCENT, text_color=SUCCESS_COLOR, background_color=BG_COLOR)],
            [sg.Graph(canvas_size=(350, 120), graph_bottom_left=(0, 0), graph_top_right=(100, 100),
                      key='-SCORE_GRAPH-', background_color=SURFACE_COLOR, pad=(0, 20))],
            [sg.VPush(background_color=BG_COLOR)],
            [sg.Button('STOPPER L\'APPEL', key='-STOP_RECORDING-', 
                       button_color=('white', DANGER_COLOR), size=(25, 2), border_width=0, font=('Segoe UI', 12, 'bold'))],
            [sg.VPush(background_color=BG_COLOR)]
        ]

    def _create_layout_history(self):
        files = self._get_audio_files()
        return [
            [sg.Text('HISTORIQUE', font=('Segoe UI', 18, 'bold'), text_color=ACCENT_COLOR, background_color=BG_COLOR, pad=(0, 10))],
            [sg.Listbox(values=files, key='-FILE_LIST-', size=(45, 18), font=FONT_MAIN, 
                        background_color=SURFACE_COLOR, text_color=TEXT_COLOR)],
            [sg.P(background_color=BG_COLOR),
             sg.Button('ECOUTER', key='-PLAY-', size=(15, 1), button_color=('black', SUCCESS_COLOR), border_width=0),
             sg.Button('SUPPRIMER', key='-DELETE-', size=(15, 1), button_color=('white', DANGER_COLOR), border_width=0),
             sg.P(background_color=BG_COLOR)],
            [sg.Button('RETOUR', key='-BACK-', size=(10, 1), button_color=(TEXT_COLOR, SURFACE_COLOR), pad=(0, 20), border_width=0)]
        ]

    def _create_layout_alert(self):
        return [
            [sg.VPush(background_color=BG_COLOR)],
            [sg.Text('ALERTE DE SECURITE', font=('Segoe UI', 20, 'bold'), text_color=DANGER_COLOR, background_color=BG_COLOR, pad=(0,10))],
            [sg.Text('Le seuil critique a ete depasse.', font=FONT_MAIN, text_color=TEXT_COLOR, background_color=BG_COLOR)],
            [sg.Text('L\'appel a ete interrompu automatiquement.', font=FONT_MAIN, text_color=TEXT_COLOR, background_color=BG_COLOR)],
            [sg.VPush(background_color=BG_COLOR)],
            [sg.Button('RETOUR A L\'ACCUEIL', key='-ALERT_OK-', size=(25, 2), button_color=('white', SURFACE_COLOR), border_width=0, font=('Segoe UI', 11, 'bold'))],
            [sg.VPush(background_color=BG_COLOR)]
        ]
import FreeSimpleGUI as sg


# --- CONFIGURATION DES COULEURS ET FONTS ---
THEME_COLOR  = 'white'
TEXT_COLOR   = '#2c3e50'
GRAY_BUTTON  = '#95a5a6'
ORANGE_BUTTON = '#f1c40f'
GREEN_BUTTON = '#00c851'
RED_ALERT    = '#e74c3c'
BLUE_ACTION  = '#1e88e5'
DARK_GRAY    = '#4a5568'
FONT_MAIN    = ('Helvetica', 12)
FONT_TITLE   = ('Helvetica', 16, 'bold')
FONT_ICON    = ('Helvetica', 40)

sg.theme_background_color(THEME_COLOR)
sg.theme_text_element_background_color(THEME_COLOR)
sg.theme_element_background_color(THEME_COLOR)


class Interface:
    """Gère la fenêtre FreeSimpleGUI et toutes les transitions d'état visuelles."""

    WINDOW_SIZE = (400, 600)

    def __init__(self):
        layout = self._create_layout_1_off()
        self.window = sg.Window(
            'Vishield', layout,
            size=self.WINDOW_SIZE,
            element_justification='c',
            finalize=True
        )
        self.current_state = 1

    # ------------------------------------------------------------------
    # Méthodes publiques : transitions d'état
    # ------------------------------------------------------------------

    def go_to_state_2_transition(self):
        """Affiche l'écran de chargement de l'IA (état 2)."""
        self._rebuild_window('Vishield - En attente', self._create_layout_2_transition())
        self.current_state = 2

    def go_to_state_3_listening(self):
        """Affiche l'écran d'écoute active (état 3)."""
        self._rebuild_window('Vishield', self._create_layout_3_listening())
        self.current_state = 3

    def go_to_state_4_alert_probable(self):
        """Affiche l'alerte orange — vishing probable (état 4)."""
        self._rebuild_window('Vishield - Alerte', self._create_layout_4_alert_probable())
        self.current_state = 4

    def go_to_state_5_alert_confirmed(self):
        """Affiche l'alerte rouge — vishing confirmé (état 5)."""
        self._rebuild_window('Vishield - Alerte', self._create_layout_5_alert_confirmed())
        self.current_state = 5

    def go_to_state_1_off(self, title='Vishield'):
        """Revient à l'écran d'accueil (état 1)."""
        self._rebuild_window(title, self._create_layout_1_off())
        self.current_state = 1

    # ------------------------------------------------------------------
    # Méthodes publiques : interaction avec la fenêtre
    # ------------------------------------------------------------------

    def read(self, timeout=100):
        """Délègue window.read() pour la boucle d'événements dans main.py."""
        return self.window.read(timeout=timeout)

    def refresh(self):
        self.window.refresh()

    def write_event_value(self, event, value):
        """Permet aux callbacks (threads) d'envoyer des événements à la fenêtre."""
        self.window.write_event_value(event, value)

    def update_element(self, key, value):
        """Met à jour la valeur d'un élément de la fenêtre courante."""
        self.window[key].update(value)

    def show_error_popup(self, message, title='Erreur'):
        sg.popup_scrolled(message, title=title)

    def close(self):
        self.window.close()

    # ------------------------------------------------------------------
    # Méthodes privées : construction des layouts
    # ------------------------------------------------------------------

    def _rebuild_window(self, title, layout):
        self.window.close()
        self.window = sg.Window(
            title, layout,
            size=self.WINDOW_SIZE,
            element_justification='c',
            finalize=True
        )

    def _create_layout_1_off(self):
        return [
            [sg.VPush()],
            [sg.Button('⏻', key='-START-', font=FONT_ICON,
                       button_color=('white', '#8e9eab'), border_width=0,
                       size=(4, 2), pad=(0, 0))],
            [sg.VPush()]
        ]

    def _create_layout_2_transition(self):
        return [
            [sg.VPush()],
            [sg.Button('⏻', key='-TRANSITION-', font=FONT_ICON,
                       button_color=('white', '#ffc107'), border_width=0,
                       size=(4, 2), pad=(0, 0))],
            [sg.Text("Chargement de l'IA...", font=('Helvetica', 10),
                     text_color=DARK_GRAY, pad=(0, 10))],
            [sg.VPush()]
        ]

    def _create_layout_3_listening(self):
        return [
            [sg.VPush()],
            [sg.Button('⏻', key='-LISTENING_ICON-', font=FONT_ICON,
                       button_color=('white', '#00c851'), border_width=0,
                       size=(4, 2), pad=(0, 0))],
            [sg.Text('En écoute', font=('Helvetica', 14, 'bold'),
                     text_color=TEXT_COLOR, pad=(0, 10))],

            # Zone pour simuler la transcription audio
            [sg.Input(key='-SIMULATED_TEXT-', size=(35, 1),
                      justification='center', tooltip="Tapez une phrase à analyser")],
            [sg.Button("Simuler l'audio", key='-ANALYZE-',
                       button_color=('white', BLUE_ACTION),
                       font=('Helvetica', 10, 'bold'), border_width=0, pad=(0, 10))],

            [sg.VPush()],
            [sg.Button('Je reçois un appel frauduleux', key='-MANUAL_ALERT-',
                       button_color=('white', '#d32f2f'),
                       font=('Helvetica', 12, 'bold'), size=(30, 2),
                       border_width=0, pad=(20, 40))]
        ]

    def _create_layout_4_alert_probable(self):
        anomalies = [
            "• Modèles de discours suspects",
            "• Création d'une situation urgente",
            "• Demande d'informations sensibles"
        ]
        layout = [
            [sg.VPush()],
            [sg.Text('⚠', font=('Helvetica', 80), text_color='#ff6f00',
                     background_color=THEME_COLOR, pad=(0, 0))],
            [sg.Text('Probable tentative de vishing', font=FONT_TITLE,
                     text_color='#1a237e', pad=(0, 20))],
            [sg.Text("Anomalies détectées par l'IA :", font=('Helvetica', 12, 'bold'),
                     text_color=TEXT_COLOR, justification='left', pad=((20, 0), 10))],
        ]
        for item in anomalies:
            layout.append([sg.Text(item, font=FONT_MAIN, text_color=DARK_GRAY,
                                   pad=((40, 0), 5))])
        layout.append([sg.VPush()])
        layout.append([
            sg.Button('Faux positif', key='-FALSE_POS_4-',
                      button_color=('white', DARK_GRAY),
                      font=('Helvetica', 12, 'bold'), size=(30, 2),
                      border_width=0, pad=(20, 40))
        ])
        return layout

    def _create_layout_5_alert_confirmed(self):
        anomalies = [
            "• Extorsion financière détectée",
            "• Usurpation d'identité forte",
            "• Pression psychologique"
        ]
        layout = [
            [sg.VPush()],
            [sg.Text('⚠', font=('Helvetica', 80), text_color='#d50000',
                     background_color=THEME_COLOR, pad=(0, 0))],
            [sg.Text("Tentative de vishing détectée avec\ncertitude, l'appel a été interrompu",
                     font=FONT_TITLE, text_color='#1a237e',
                     justification='center', pad=(0, 20))],
            [sg.Text("Anomalies détectées par l'IA :", font=('Helvetica', 12, 'bold'),
                     text_color=TEXT_COLOR, justification='left', pad=((20, 0), 10))],
        ]
        for item in anomalies:
            layout.append([sg.Text(item, font=FONT_MAIN, text_color=DARK_GRAY,
                                   pad=((40, 0), 5))])
        layout.append([sg.VPush()])
        layout.append([
            sg.Button('Faux positif', key='-FALSE_POS_5-',
                      button_color=('white', DARK_GRAY),
                      font=('Helvetica', 11, 'bold'), size=(15, 2),
                      border_width=0, pad=((20, 10), 40)),
            sg.Button('Rappeler', key='-CALLBACK-',
                      button_color=('white', '#2962ff'),
                      font=('Helvetica', 11, 'bold'), size=(15, 2),
                      border_width=0, pad=((10, 20), 40))
        ])
        return layout

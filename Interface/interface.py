import FreeSimpleGUI as sg

# --- CONFIGURATION DES COULEURS ET FONTS ---
THEME_COLOR = 'white'
TEXT_COLOR = '#2c3e50'
GRAY_BUTTON = '#95a5a6'
ORANGE_BUTTON = '#f1c40f' # Jaune/Orange pour la transition
GREEN_BUTTON = '#00c851'
RED_ALERT = '#e74c3c'
BLUE_ACTION = '#1e88e5'
DARK_GRAY = '#4a5568'
FONT_MAIN = ('Helvetica', 12)
FONT_TITLE = ('Helvetica', 16, 'bold')
FONT_ICON = ('Helvetica', 40) # Pour simuler les icones

sg.theme_background_color(THEME_COLOR)
sg.theme_text_element_background_color(THEME_COLOR)
sg.theme_element_background_color(THEME_COLOR)

# --- FONCTIONS DE LAYOUTS (LES 5 ECRANS) ---

def create_layout_1_off():
    """Ecran 1 : Eteint, bouton gris"""
    return [
        [sg.VPush()],
        [sg.Button('⏻', key='-START-', font=FONT_ICON, button_color=('white', '#8e9eab'), border_width=0, size=(4, 2),  pad=(0,0))],
        [sg.VPush()]
    ]

def create_layout_2_transition():
    """Ecran 2 : Transition, bouton orange"""
    return [
        [sg.VPush()],
        [sg.Button('⏻', key='-TRANSITION-', font=FONT_ICON, button_color=('white', '#ffc107'), border_width=0, size=(4, 2), pad=(0,0))],
        [sg.VPush()]
    ]

def create_layout_3_listening():
    """Ecran 3 : En écoute, bouton vert + bouton rouge en bas"""
    return [
        [sg.VPush()],
        [sg.Button('⏻', key='-LISTENING_ICON-', font=FONT_ICON, button_color=('white', '#00c851'), border_width=0, size=(4, 2), pad=(0,0))],
        [sg.Text('En écoute', font=('Helvetica', 14, 'bold'), text_color=TEXT_COLOR, pad=(0, 20))],
        [sg.VPush()],
        [sg.Button('Je reçois un appel frauduleux', key='-MANUAL_ALERT-', button_color=('white', '#d32f2f'), font=('Helvetica', 12, 'bold'), size=(30, 2), border_width=0, pad=(20, 40))]
    ]

def create_layout_4_alert_probable():
    """Ecran 4 : Alerte Orange"""
    anomalies = [
        "• Voix artificielle",
        "• Usurpation d'identité d'un banquier",
        "• Extorsion de codes de carte bancaire",
        "• Création d'une situation urgente"
    ]
    
    layout = [
        [sg.VPush()],
        [sg.Text('⚠', font=('Helvetica', 80), text_color='#ff6f00', background_color=THEME_COLOR, pad=(0,0))], # Icone triangle
        [sg.Text('Probable tentative de vishing', font=FONT_TITLE, text_color='#1a237e', pad=(0, 20))],
        
        [sg.Text('Anomalies détectées :', font=('Helvetica', 12, 'bold'), text_color=TEXT_COLOR, justification='left', pad=((20,0), 10))],
    ]
    
    # Ajout de la liste à puces
    for item in anomalies:
        layout.append([sg.Text(item, font=FONT_MAIN, text_color=DARK_GRAY, pad=((40,0), 5))])

    layout.append([sg.VPush()])
    layout.append([sg.Button('Faux positif', key='-FALSE_POS_4-', button_color=('white', DARK_GRAY), font=('Helvetica', 12, 'bold'), size=(30, 2), border_width=0, pad=(20, 40))])
    
    return layout

def create_layout_5_alert_confirmed():
    """Ecran 5 : Alerte Rouge"""
    anomalies = [
        "• Voix artificielle",
        "• Usurpation d'identité d'un banquier",
        "• Extorsion de codes de carte bancaire",
        "• Création d'une situation urgente"
    ]
    
    layout = [
        [sg.VPush()],
        [sg.Text('⚠', font=('Helvetica', 80), text_color='#d50000', background_color=THEME_COLOR, pad=(0,0))], # Icone triangle rouge
        [sg.Text("Tentative de vishing détectée avec\ncertitude, l'appel a été interrompu", font=FONT_TITLE, text_color='#1a237e', justification='center', pad=(0, 20))],
        
        [sg.Text('Anomalies détectées :', font=('Helvetica', 12, 'bold'), text_color=TEXT_COLOR, justification='left', pad=((20,0), 10))],
    ]
    
    for item in anomalies:
        layout.append([sg.Text(item, font=FONT_MAIN, text_color=DARK_GRAY, pad=((40,0), 5))])

    layout.append([sg.VPush()])
    # Boutons côte à côte en bas
    layout.append([
        sg.Button('Faux positif', key='-FALSE_POS_5-', button_color=('white', DARK_GRAY), font=('Helvetica', 11, 'bold'), size=(15, 2), border_width=0, pad=((20, 10), 40)),
        sg.Button('Rappeler', key='-CALLBACK-', button_color=('white', '#2962ff'), font=('Helvetica', 11, 'bold'), size=(15, 2), border_width=0, pad=((10, 20), 40))
    ])
    
    return layout


# --- LOGIQUE PRINCIPALE ---

def main():
    # Taille simulée d'un écran mobile
    window_size = (400, 600)
    
    # Initialisation avec l'écran 1
    layout = create_layout_1_off()
    
    # On utilise element_justification='c' pour centrer horizontalement
    window = sg.Window('Vishing Detector', layout, size=window_size, element_justification='c', finalize=True)

    current_state = 1

    while True:
        event, values = window.read(timeout=100) # Timeout pour permettre les transitions automatiques si besoin

        if event == sg.WIN_CLOSED:
            break

        # --- LOGIQUE DE NAVIGATION ---

        # 1 -> 2 (Clic sur bouton gris)
        if current_state == 1 and event == '-START-':
            window.close()
            layout = create_layout_2_transition()
            window = sg.Window('Vishing Detector', layout, size=window_size, element_justification='c', finalize=True)
            current_state = 2
            
            # Transition automatique rapide de 2 -> 3 pour simuler le chargement
            window.read(timeout=600) # Attend 600ms sur l'écran orange
            window.close()
            layout = create_layout_3_listening()
            window = sg.Window('Vishing Detector', layout, size=window_size, element_justification='c', finalize=True)
            current_state = 3

        # 3 -> 4 (Clic sur "Je reçois un appel frauduleux" OU simulation backend)
        # Note: Pour simuler le backend qui détecte une alerte confirmée (5), 
        # j'ai ajouté un clic caché sur l'icône verte pour aller vers l'écran 5 à des fins de test.
        elif current_state == 3:
            if event == '-MANUAL_ALERT-':
                # Va vers "Probable" (Ecran 4)
                window.close()
                layout = create_layout_4_alert_probable()
                # Justification left pour le texte, mais container centré
                window = sg.Window('Vishing Detector', layout, size=window_size, element_justification='c', finalize=True)
                current_state = 4
            
            elif event == '-LISTENING_ICON-': 
                # (Cheatcode : cliquer sur le bouton vert simule une détection Backend CERTAINE -> Ecran 5)
                window.close()
                layout = create_layout_5_alert_confirmed()
                window = sg.Window('Vishing Detector', layout, size=window_size, element_justification='c', finalize=True)
                current_state = 5

        # 4 -> 1 (Faux positif)
        elif current_state == 4 and event == '-FALSE_POS_4-':
            window.close()
            layout = create_layout_1_off()
            window = sg.Window('Vishing Detector', layout, size=window_size, element_justification='c', finalize=True)
            current_state = 1

        # 5 -> 1 (Faux positif ou Rappeler)
        elif current_state == 5:
            if event == '-FALSE_POS_5-' or event == '-CALLBACK-':
                window.close()
                layout = create_layout_1_off()
                window = sg.Window('Vishing Detector', layout, size=window_size, element_justification='c', finalize=True)
                current_state = 1

    window.close()

if __name__ == "__main__":
    main()

#!/bin/bash

VENV_DIR=".venv"

# ── 1. Trouver Python ──────────────────────────────────────────────────
PYTHON=""
for cmd in python3 python py; do
    if command -v "$cmd" &> /dev/null; then
        VERSION=$("$cmd" --version 2>&1 | grep -oP '3\.\d+')
        echo "python version '$VERSION'"
        PYTHON="$cmd"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    echo "ERREUR : Aucun interpréteur Python 3 trouvé."
    exit 1
fi

# ── 2. Recréer le venv si --reset demandé ─────────────────────────────
if [ "$1" = "--reset" ] && [ -d "$VENV_DIR" ]; then
    echo "Suppression de l'ancien environnement virtuel..."
    rm -rf "$VENV_DIR"
fi

# ── 3. Créer le venv si inexistant ────────────────────────────────────
if [ ! -d "$VENV_DIR" ]; then
    echo "Création de l'environnement virtuel Python dans '$VENV_DIR'..."
    $PYTHON -m venv "$VENV_DIR"
    if [ $? -ne 0 ]; then
        echo "ERREUR : Impossible de créer le venv."
        exit 1
    fi
    echo "Environnement virtuel créé."
fi

# ── 4. Chemins du venv ────────────────────────────────────────────────
if [ -d "$VENV_DIR/Scripts" ]; then
    VENV_PYTHON="$VENV_DIR/Scripts/python"
    VENV_PIP="$VENV_DIR/Scripts/pip"
else
    VENV_PYTHON="$VENV_DIR/bin/python"
    VENV_PIP="$VENV_DIR/bin/pip"
fi

# ── Fonction utilitaire : installer et vérifier un paquet ─────────────
install_and_check() {
    local import_name="$1"   # nom du module Python  (ex: soundcard)
    local pip_name="$2"      # nom du paquet pip      (ex: soundcard)
    local label="$3"         # nom affiché à l'écran  (ex: soundcard)

    "$VENV_PYTHON" -c "import ${import_name}" 2>/dev/null
    if [ $? -ne 0 ]; then
        echo ""
        echo "Installation de ${label} dans le venv..."
        echo ""
        "$VENV_PIP" install --no-cache-dir "${pip_name}"
        if [ $? -ne 0 ]; then
            echo ""
            echo "ERREUR : Echec de l'installation de ${label}."
            echo ""
            exit 1
        fi
        # Vérification post-installation
        "$VENV_PYTHON" -c "import ${import_name}" 2>/dev/null
        if [ $? -ne 0 ]; then
            echo ""
            echo "ERREUR : ${label} est installé mais ne peut pas être importé."
            echo "Détail de l'erreur :"
            "$VENV_PYTHON" -c "import ${import_name}"
            echo ""
            echo "Des dépendances système sont peut-être manquantes (voir ci-dessus)."
            echo ""
            exit 1
        fi
    fi
}

# ── 5. Dépendances système pour les librairies audio ──────────────────
# soundcard et sounddevice nécessitent libpulse et libasound sur Linux
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    MISSING_PKGS=()
    for pkg in libpulse-dev libasound2-dev portaudio19-dev; do
        if ! dpkg -s "$pkg" &>/dev/null; then
            MISSING_PKGS+=("$pkg")
        fi
    done

    if [ ${#MISSING_PKGS[@]} -ne 0 ]; then
        echo ""
        echo "Installation des dépendances système audio manquantes : ${MISSING_PKGS[*]}"
        echo ""
        sudo apt-get install -y "${MISSING_PKGS[@]}"
        if [ $? -ne 0 ]; then
            echo ""
            echo "ERREUR : Impossible d'installer les dépendances système."
            echo "Essayez manuellement : sudo apt-get install -y ${MISSING_PKGS[*]}"
            echo ""
            exit 1
        fi
    fi
fi

# ── 6. Installer / vérifier les dépendances Python ────────────────────

install_and_check "faster_whisper"  "faster-whisper"  "faster-whisper"
install_and_check "safetensors"     "safetensors"     "safetensors"
install_and_check "PIL"             "Pillow"          "Pillow"

# soundcard a un bug avec sys.argv quand importé via -c : on lui passe un argv fictif
"$VENV_PYTHON" -c "import sys; sys.argv = ['vishield', 'dummy']; import soundcard" 2>/dev/null
if [ $? -ne 0 ]; then
    echo ""
    echo "Installation de soundcard dans le venv..."
    echo ""
    "$VENV_PIP" install --no-cache-dir soundcard
    if [ $? -ne 0 ]; then
        echo ""
        echo "ERREUR : Echec de l'installation de soundcard."
        echo ""
        exit 1
    fi
    "$VENV_PYTHON" -c "import sys; sys.argv = ['vishield', 'dummy']; import soundcard" 2>/dev/null
    if [ $? -ne 0 ]; then
        echo ""
        echo "ERREUR : soundcard est installé mais ne peut pas être importé."
        "$VENV_PYTHON" -c "import sys; sys.argv = ['vishield', 'dummy']; import soundcard"
        exit 1
    fi
fi
install_and_check "sounddevice"     "sounddevice"     "sounddevice"
install_and_check "numpy"           "numpy"           "numpy"
install_and_check "FreeSimpleGUI"   "FreeSimpleGUI"   "FreeSimpleGUI"
install_and_check "transformers"    "transformers"    "transformers"

# torch : traitement spécial (détection GPU)
"$VENV_PYTHON" -c "import torch" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Détection du GPU Nvidia..."
    nvidia-smi &>/dev/null
    if [ $? -eq 0 ]; then
        echo ""
        echo "GPU Nvidia détecté. Installation de torch avec support CUDA 12.1..."
        echo ""
        "$VENV_PIP" install --no-cache-dir torch # --index-url https://download.pytorch.org/whl/cu121
    else
        echo ""
        echo "Aucun GPU Nvidia détecté. Installation de torch (version CPU)..."
        echo ""
        "$VENV_PIP" install --no-cache-dir torch
    fi
    if [ $? -ne 0 ]; then
        echo ""
        echo "ERREUR : Echec de l'installation de torch."
        echo ""
        exit 1
    fi
fi

# ── 7. Diagnostic : afficher les versions installées ──────────────────
if [ "$1" = "-v" ]; then
    echo ""
    echo "Versions installées :"
    "$VENV_PYTHON" --version
    "$VENV_PIP" show soundcard      | grep -E "^(Name|Version)"
    "$VENV_PIP" show sounddevice    | grep -E "^(Name|Version)"
    "$VENV_PIP" show numpy          | grep -E "^(Name|Version)"
    "$VENV_PIP" show FreeSimpleGUI  | grep -E "^(Name|Version)"
    "$VENV_PIP" show torch          | grep -E "^(Name|Version)"
    "$VENV_PIP" show transformers   | grep -E "^(Name|Version)"
    "$VENV_PIP" show safetensors    | grep -E "^(Name|Version)"
    "$VENV_PIP" show faster-whisper | grep -E "^(Name|Version)"
    echo ""
fi

# ── 8. Lancer le programme ────────────────────────────────────────────
echo "Lancement de Vishield..."
"$VENV_PYTHON" src/main.py
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "Le programme s'est terminé avec une erreur (code $EXIT_CODE)."
    echo "Si le problème persiste, relance avec : ./Vishield.sh --reset"
    echo "Cela recréera l'environnement virtuel from scratch."
fi
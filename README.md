<img src="https://github.com/JoshuaMrtl/Vishield-/blob/main/images/logo.png" alt="logo">
# Vishield
Vishield est une application permettant de protéger les utilisateur contre les attaques de vishing, c'est-à-dire les appels frauduleux.

## How to use
Start by downloading the model.safetensor file from our drive (it is too big to put on git) and put it in Vishield-/TrainedBert

Execute ./Vishield.sh
This script will create a virtual python environment in which it will install every required library. It will then launch Vishield

## Fonctionnement
Vishield enregistre l'audio entrant et sortant de l'appareil en temps réel, le convertit en texte à l'aide de Whisper et analyse le contenu de la conversation avec un modèle de Bert entrainé à la détection du vishing.

L'application avertit l'utilisateur si elle détecte un appel frauduleux et peut même interompre l'appel d'elle même si elle est suffisemment sûre d'avoir détecté une attaque.

Vishield fonctionne entièremment localement, elle n'envoie aucune donnée sensible vers un serveur sur internet.

## Plateformes
L'application est disponible sur Windows, Linux et Android.

La version Windows et Linux est capable d'enregistrer l'appel en temps réel et d'afficher un pop up d'avertissement lors d'une attaque. Il faut tout de fois lancer l'enregistrement manuellement.

La version Android est capable de détecter un appel entrant pour commencer à enregistrer et de raccrocher d'elle même. Cependant, elle n'est pas encore fonctionnelle.

## Architecture
La version Windows - Linux est codée en python, aidée d'un script shell permettant d'installer toutes les dépendances automatiquement.
La version Android est codée en Kotlin.

Elles utilisent toutes les 2 le paradigme objet et la même architecture : 

<img src="https://github.com/JoshuaMrtl/Vishield-/blob/main/images/archi_prog.png?raw=true" alt="schema de l'architecture du logiciel">



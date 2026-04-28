<p align="center">
    <img src="https://github.com/JoshuaMrtl/Vishield-/blob/main/images/logo.png" alt="logo" style="width:20%; height:auto;">
</p>

# Vishield
Vishield est une application permettant de protéger les utilisateur contre les attaques de vishing, c'est-à-dire les appels frauduleux.

## Consignes d'utilisation
Pour utiliser Vishield sur PC, il faut faut d'abord télécharger le fichier model.safetensor contenant le modèle de Bert (il est trop volumineux pour github) et le mettre dans le dossier Vishield-/TrainedBert.
Lancer Vishield avec la commande :
```
./Vishield.sh
```
Cette commande va créer un environnement virtuel Python et y installer toutes les librairies nécessaire, avant de lancer Vishield.

Il est possible que ffmpeg pose problème lors de l'exécution, il faut alors vérifier qu'il est bien installé, puis exécuter la commande Powershell suivante :
```
./misc/add_ffmpeg_to_path.ps1
```

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



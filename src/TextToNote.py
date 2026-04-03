import torch
from transformers import DistilBertTokenizer, DistilBertForSequenceClassification
from os import path
from time import time

class Bert :

    # Text colors
    DEFAULT = '\033[0m'
    RED     = '\033[91m'
    GREEN   = '\033[92m'
    YELLOW  = '\033[93m'
    BLUE    = '\033[94m'
    PURPLE  = '\033[95m'

# -------------------- Public Methods --------------------

    def __init__(self):

        self.tokenizer = None
        self.bert      = None
        self.device    = None

        self._newNote = None
        self._callback = None

        print("[Bert]    Initializing model.")
        #Charge le modèle depuis le dossier local TrainedBert.
        bert_path = path.abspath(path.join(path.dirname(__file__), "../TrainedBert"))

        
        self.tokenizer = DistilBertTokenizer.from_pretrained(bert_path)
        self.bert = DistilBertForSequenceClassification.from_pretrained(bert_path)
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.bert.to(self.device)
        self.bert.eval() # Mode évaluation
        print("[Bert]    Model initialized.")

    def predict_vishing(self, text):
        print(f"{time():.2f}" + self.YELLOW + f"[Bert]    Analizing \"{text}\"" + self.DEFAULT)
        if self.tokenizer is None or self.bert is None:
            print("RuntimeError : Le modèle n'est pas chargé. Appelez init_bert() d'abord.")
            raise RuntimeError("Le modèle n'est pas chargé. Appelez init_bert() d'abord.")
            
        #Analyse le texte et retourne un booléen et le pourcentage de certitude.
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=128)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = self.bert(**inputs)
            
        probabilities = torch.nn.functional.softmax(outputs.logits, dim=-1)
        predicted_class_id = probabilities.argmax().item()
        confidence = probabilities[0][predicted_class_id].item() * 100
        
        is_vishing = (predicted_class_id == 1)

        print(f"{time():.2f}" + self.YELLOW + f"[Bert]    Analized \"{text}\" : Is it vishing ? {is_vishing}, confidence : {confidence}" + self.DEFAULT)
        self.newNote = (is_vishing, confidence)

#-------------------- Callback Methods --------------------

    def register_callback(self, callback):
        self._callback = callback
        print("callback registered")

    @property # Décorateur indiquant que la fonction est un getteur
    def newNote(self):
        return self._newNote

    @newNote.setter # Décorateur indiquant que la fonction est un setteur
    def newNote(self, value):
        self._newNote = value
        if self._callback:
            self._callback(value)  # déclenché automatiquement à chaque changement
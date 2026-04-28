from faster_whisper import WhisperModel
import torch
import shutil
from time import time

class Whisper :

    # Text colors
    DEFAULT = '\033[0m'
    RED     = '\033[91m'
    GREEN   = '\033[92m'
    YELLOW  = '\033[93m'
    BLUE    = '\033[94m'
    PURPLE  = '\033[95m'

# -------------------- Public Methods --------------------

    def __init__(self):
        print("[Whisper] Initializing model.")
        self.whisper = None

        self._newTextBuffer = None
        self._callback = None

        self.bufferNumber = 0
        self.bufferMemory = LinkedList()

        self._check_dependencies()

        if torch.cuda.is_available() :
            # self.whisper = WhisperModel("turbo", device="cuda", compute_type="float16")
            self. whisper = WhisperModel("turbo", device="cpu", compute_type="int8")
        else :
           self. whisper = WhisperModel("turbo", device="cpu", compute_type="int8")
        print("[Whisper] Model initialized.")
 
    def _check_dependencies(self):
        if shutil.which("ffmpeg") is None:
            raise EnvironmentError("ffmpeg est introuvable. Installe-le et assure-toi qu'il est dans le PATH.")

    def transcribe_wav(self, wav_path: str) -> str:
        print(f"{time():.2f}" + self.PURPLE + f" [Whisper] Beginning transcription of file {wav_path}" + self.DEFAULT)

        if self.whisper is None:
            raise RuntimeError("Whisper n'est pas initialisé. Appelez init_whisper() d'abord.")
        
        segments, _ = self.whisper.transcribe(wav_path, task="translate")
        # text_buffer = "".join(segment.text.strip() for segment in segments)

        # Retourne le texte des 4 derniers buffers audio
        self.bufferMemory.insertAtEnd(" ".join(segment.text.strip() for segment in segments))
        if self.bufferNumber >= 4 :
            self.bufferMemory.deleteFromBeginning()
        
        else : 
            self.bufferNumber += 1

        text_buffer = self.bufferMemory.getList()#.join(segment.text.strip() for segment in segments)

        print(f"{time():.2f}" + self.RED + f" [Whisper] {wav_path} converted to new text buffer : {text_buffer}" + self.DEFAULT)
        self.newTextBuffer = text_buffer

#-------------------- Callback Methods --------------------
    # These methods are used to call Bert in TextToNote.py to analyze a new text buffer when Whisper is done making it

    def register_callback(self, callback):
        self._callback = callback

    @property # Décorateur indiquant que la fonction est un getteur
    def newTextBuffer(self):
        return self._newTextBuffer

    @newTextBuffer.setter # Décorateur indiquant que la fonction est un setteur
    def newTextBuffer(self, value):
        self._newTextBuffer = value
        if self._callback:
            self._callback(value)  # déclenché automatiquement à chaque changement

#-------------------- Classes to implement chained list --------------------
class Node:
    def __init__(self, data):
        self.data = data  # Assigns the given data to the node
        self.next = None  # Initialize the next attribute to null

class LinkedList:
    def __init__(self):
        self.head = None  # Initialize head as None

    def insertAtBeginning(self, new_data):
        new_node = Node(new_data)  # Create a new node 
        new_node.next = self.head  # Next for new node becomes the   current head
        self.head = new_node  # Head now points to the new node

    def insertAtEnd(self, new_data):
        new_node = Node(new_data)  # Create a new node
        if self.head is None:
            self.head = new_node  # If the list is empty, make the new node the head
            return
        last = self.head 
        while last.next:  # Otherwise, traverse the list to find the last node
            last = last.next
        last.next = new_node  # Make the new node the next node of the last node

    def deleteFromBeginning(self):
        if self.head is None:
            return "The list is empty" # If the list is empty, return this string
        self.head = self.head.next  # Otherwise, remove the head by making the next node the new head

    def deleteFromEnd(self):
        if self.head is None:
            return "The list is empty" 
        if self.head.next is None:
            self.head = None  # If there's only one node, remove the head by making it None
            return
        temp = self.head
        while temp.next.next:  # Otherwise, go to the second-last node
            temp = temp.next
        temp.next = None  # Remove the last node by setting the next pointer of the second-last node to None

    def getList(self):
        temp = self.head # Start from the head of the list
        output = ""
        while temp:
            output += temp.data
            temp = temp.next # Move to the next node

        print(f"------------- [Buffer]  Buffer in memory : {output}")
        return output




if __name__ == "__main__" :
    stt = Whisper()
    start_time = time()
    stt.transcribe("../recordings/callRecord_0_0.wav")
    end_time = start_time -time()
    print(f"Finished transcribing audio buffer, took {end_time} seconds")
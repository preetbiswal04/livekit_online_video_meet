import os 
from faster_whisper import WhisperModel

def download():
    print("downloading model..")
    WhisperModel("large",device ="cpu", compute_type="int8")

if __name__ == "__main__":
    download()

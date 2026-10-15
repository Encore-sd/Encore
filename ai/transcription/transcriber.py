import os
import importlib.util
from pathlib import Path
CACHE_DIR = (Path(__file__).resolve()).parent.parent / 'models'
os.environ['HF_HOME'] = str(CACHE_DIR)
utilities_path = (Path(__file__).resolve()).parent.parent / 'shared' / 'os_utilities.py'
module_spec = importlib.util.spec_from_file_location('os_utilities', utilities_path)
os_utilities = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(os_utilities)

import torch
from transformers import pipeline

DEFAULT_ASR_MODEL = "openai/whisper-base.en"

def _set_device():
    return "cuda:0" if torch.cuda.is_available() else "cpu"
    
def _pass_in_audio_file(audio_file_path:str):
    with open(audio_file_path, 'rb') as audio_file:
        read_bytes = audio_file.read()
    return read_bytes
    
def create_asr_pipeline(asr_model:str = DEFAULT_ASR_MODEL):
    acting_device = _set_device()
    pipe = pipeline(
        "automatic-speech-recognition",
        model=asr_model,
        chunk_length_s=30,
        device=acting_device
    )
    return pipe
    
def _transcribe_file(file, asr_pipeline):
    audio_bytes = _pass_in_audio_file(file)
    prediction = asr_pipeline(audio_bytes, batch_size=8)["text"]
    return prediction

def transcribe_files(files:list[str] | str, asr_pipeline:pipeline):
    ac_files = files
    if isinstance(ac_files, str):
        ac_files = [ac_files]
    
    predictions = []
    for file in ac_files:
        predictions.append(_transcribe_file(file, asr_pipeline))
    return predictions
    
def _filter_out_non_audio_files(files):
    return [file for file in files if file.split('.')[-1] in ['mp4', 'mp3', 'wav']]
    
def get_audio_files_from_directory(root):
    temp_files = os_utilities.gather_files_from_directory(root)
    return _filter_out_non_audio_files(temp_files)
    
def format_predictions(predictions: str | list):
    if isinstance(predictions, str):
        return f'Predicted: {predictions}'
    else:
        return f'Predicted: {"\nPredicted: ".join(predictions)}'

if __name__ == '__main__':
    pass
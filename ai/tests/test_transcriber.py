import importlib.util
from pathlib import Path
import os
import numpy as np
import random

transcriber_path = (Path(__file__).resolve()).parent.parent / 'transcription' / 'transcriber.py'
test_path = Path(__file__).resolve().parent
module_spec = importlib.util.spec_from_file_location('transcriber', transcriber_path)
transcriber = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(transcriber)

utilities_path = (Path(__file__).resolve()).parent.parent / 'shared' / 'os_utilities.py'
module_spec = importlib.util.spec_from_file_location('os_utilities', utilities_path)
os_utilities = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(os_utilities)

def main():
    temp_files = os_utilities.gather_files_from_directory(test_path / 'fixtures')
    audio_files = [file for file in temp_files if file.split('.')[-1] in ['mp4', 'mp3', 'wav']]
    audio_files = [os.path.join(test_path, 'fixtures', file) for file in audio_files]
    
    # load the processor/model once because we're calling transcribe multiple times (on purpose)
    preloaded_processor, preloaded_model = transcriber.load_model_and_processor()
    
    # Single Transcription
    print('Just one set of Bytes')
    print(transcriber.transcribe(transcriber.convert_to_bytes(audio_files[0]), already_loaded_processor=preloaded_processor, already_loaded_model=preloaded_model))
    print('------------------------------------------------------------------------')
    
    # Single-File Transcription
    print('Transcribe a single file')
    print(transcriber.transcribe_audio_files(audio_files[0], already_loaded_processor=preloaded_processor, already_loaded_model=preloaded_model))
    print('------------------------------------------------------------------------')
    
    # Batched Transcription
    print('Batched Transcription with capture_time + user_id per chunk')
    # the random.randint(1, 100) is setting a random capture time; random.randint(10000, 99999) is setting a random user id
    byte_arr = [[transcriber.convert_to_bytes(file), float(random.randint(1, 100))/10.0, random.randint(10000, 99999)] for file in audio_files]
    print(transcriber.transcribe(byte_arr, already_loaded_processor=preloaded_processor, already_loaded_model=preloaded_model))
    
    # Transcribe many files
    print('Transcribe many files')
    print(transcriber.transcribe_audio_files([[file, float(random.randint(1, 100))/10.0, random.randint(10000, 99999)] for file in audio_files], already_loaded_processor=preloaded_processor, already_loaded_model=preloaded_model))
    print('------------------------------------------------------------------------')
    
    
if __name__ == '__main__':
    main()
import importlib.util
from pathlib import Path
import os
import subprocess
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


# convert_to_bytes was made by Gemma4 31B --> script to convert audio files directly into a list of bytes to mimic being sent a stream of bytes from the device; We may need an intermediary to preprocess said stream of bytes into an np.ndarry of np.float32 and make sure that if the device doesn't sample at 16K bytes/second, that they are resampled, as that is what transcription expects.
def convert_to_bytes(file):
    command = ['ffmpeg', '-i', file, '-ac', '1', '-ar', '16000', '-f', 'f32le', '-acodec', 'pcm_f32le', '-']
    
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    stdout_data, stderr_data = process.communicate()
    
    if process.returncode != 0:
        raise RuntimeError(f"FFmpeg error: {stderr_data.decode()}")

    return np.frombuffer(stdout_data, dtype=np.float32)

def main():
    temp_files = os_utilities.gather_files_from_directory(test_path / 'fixtures')
    audio_files = [file for file in temp_files if file.split('.')[-1] in ['mp4', 'mp3', 'wav']]
    audio_files = [os.path.join(test_path, 'fixtures', file) for file in audio_files]
    
    # load the processor/model once because we're calling transcribe multiple times (on purpose)
    preloaded_processor, preloaded_model = transcriber.load_model_and_processor()
    
    # Single Transcription
    print('Just one set of Bytes')
    print(transcriber.transcribe(convert_to_bytes(audio_files[0]), already_loaded_processor=preloaded_processor, already_loaded_model=preloaded_model))
    print('------------------------------------------------------------------------')
    
    # Batched Transcription
    print('Batched Transcription with capture_time + user_id per chunk')
    # the random.randint(1, 100) is setting a random capture time; random.randint(10000, 99999) is setting a random user id
    byte_arr = [[convert_to_bytes(file), random.randint(1, 100), random.randint(10000, 99999)] for file in audio_files]
    print(transcriber.transcribe(byte_arr, already_loaded_processor=preloaded_processor, already_loaded_model=preloaded_model))
    
if __name__ == '__main__':
    main()
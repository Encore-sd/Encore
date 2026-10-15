import importlib.util
from pathlib import Path
import os
transcriber_path = (Path(__file__).resolve()).parent.parent / 'transcription' / 'transcriber.py'
test_path = Path(__file__).resolve().parent
module_spec = importlib.util.spec_from_file_location('transcriber', transcriber_path)
transcriber = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(transcriber)


def main():
    asr_pipeline = transcriber.create_asr_pipeline()
    audio_files = transcriber.get_audio_files_from_directory(test_path / 'fixtures')
    audio_files = [os.path.join(test_path, 'fixtures', file) for file in audio_files]
    
    predictions = transcriber.transcribe_files(audio_files, asr_pipeline)
    print(transcriber.format_predictions(predictions))

if __name__ == '__main__':
    main()
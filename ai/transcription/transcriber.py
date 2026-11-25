# file for transcribing audio into text for the data pipeline
# USES openai/whisper-base.en

import os
from transformers import pipeline

# constant taken from .env
TRANSCRIBE_MODEL = os.environ.get("TRANSCRIBE_MODEL", "openai/whisper-base.en")

# loads whisper once, when this file is imported
ASR = pipeline("automatic-speech-recognition", model=TRANSCRIBE_MODEL)

# without these whisper makes up a sentence when the audio has no speech
NO_SPEECH_SETTINGS = {
    "no_speech_threshold": 0.6,
    "logprob_threshold": -1.0,
    "compression_ratio_threshold": 1.35,
    "temperature": (0.0, 0.2, 0.4, 0.6, 0.8, 1.0),
}


# takes a path to an audio file, returns the text with its start and end time in seconds
def transcribe(audio_file):
    # timestamps are required for audio over 30s
    result = ASR(audio_file, return_timestamps=True, generate_kwargs=NO_SPEECH_SETTINGS)
    chunks = result["chunks"]

    # no speech found, so the pipeline can skip it
    if not chunks:
        return {"transcript_string": "", "start_time": None, "end_time": None}

    return {
        "transcript_string": result["text"].strip(),
        "start_time": chunks[0]["timestamp"][0],
        "end_time": chunks[-1]["timestamp"][1],
    }


if __name__ == "__main__":
    import sys
    print(transcribe(sys.argv[1]))

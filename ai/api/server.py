from fastapi import FastAPI, UploadFile, HTTPException
from threading import Lock
from pipeline.data_pipeline import data_transport


app = FastAPI()
locker = Lock()

## from docs for init testing 
@app.get("/")
def root():
    return {"message": "Hello World"}


@app.post("/audio")
def process_audio(file: UploadFile):
    try:
        with locker: # a second request waits here until the first one is done
            response = data_transport(file.file.read())

            # error handling
            if response is None:
                return {
                    "transcript_string" : "",
                    "start_time" : None,
                    "end_time" : None,
                    "keep" : None,
                    "confidence" : None,
                    "reason" : None,
                    "embedding" : None
                }
            # end if

            #unpack response into 3 different vars
            transcript_data, cheap_classification_data, vector_data = response

            #return response
            return {
                    "transcript_string" : transcript_data["transcript_string"], # the transcription as a string 
                    "start_time" : transcript_data["start_time"], #transscription start time 
                    "end_time" : transcript_data["end_time"], # transcriptipn end time
                    "keep" : cheap_classification_data["keep"], # boolean variable for expensive classifier
                    "confidence" : cheap_classification_data["confidence"], # a score from 0-1 based on how confident Jev is 
                    "reason" : cheap_classification_data["reason"], # reason from Jev Classifier, 6 labels
                    "embedding" : vector_data # large dimensional vector 
            }
    except ValueError:
        raise HTTPException(415, "A complete audio file is required (wav, mp3, m4a, ogg, flac, webm, aiff)")

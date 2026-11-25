from fastapi import FastAPI, UploadFile, HTTPException
from threading import Lock
from pipeline.data_pipeline import data_transport # imported module
from pipeline.query_pipeline import query_transport  #imported module 
from pipeline.missing_info_pipeline import missing_info_transport  # imported module
from pydantic import BaseModel
import requests

app = FastAPI()
locker = Lock()

# shape of the /audio response, shown on the /docs page and checked on every reply
# everything except transcript_string is None when the audio has no speech
class AudioResult(BaseModel):
    transcript_string: str
    start_time: float | None
    end_time: float | None
    keep: bool | None
    confidence: float | None
    reason: str | None
    embedding: list[float] | None

# class to store a users ID and question to be processed through the pipeline
class QueryRequest(BaseModel):
    question : str
    userID : int 

# class to return the string from the query pipeline
class QueryResult(BaseModel):
    answer : str

## from docs for init testing 
@app.get("/")
def root():
    return {"message": "Hello World"}


@app.post("/audio")
def process_audio(file: UploadFile) -> AudioResult:
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
    # before ValueError: a bad JSON reply from the embedder is both, and it is not the caller's fault
    except requests.RequestException:
        # no embedding means no row, so the backend keeps the audio and sends it again later
        raise HTTPException(503, "The embedding model is unavailable, send the file again later")
    except ValueError:
        raise HTTPException(415, "A complete audio file is required (wav, mp3, m4a, ogg, flac, webm, aiff)")

@app.post("/retry_for_missing_info")
def retry_missing_info(information_dict:dict) -> AudioResult:
    # Expects a dictionary of the shape returned in process_audio
    expected_keys:list = ['transcript_string', 'start_time', 'end_time', 'keep', 'confidence', 'reason', 'embedding']
    for key in expected_keys:
        if key not in information_dict:
            raise HTTPException(400, f'(ai/api/server.py): Backend passed an input missing the required key "{key}" to retry_missing_info(); Set the key-values to None instead of ommitting them.')
    
    transcript_str:str = information_dict.get('transcript_string')
    if len(transcript_str) < 1:
        # make sure transcript isn't empty cause if it is there'd be nothing to redo regardless of what backend says
        return information_dict
    
    with locker: # a second request waits here until the first one is done
        response = missing_info_transport(information_dict)
        
        return {
            "transcript_string" : response.get("transcript_string"), # the transcription as a string 
            "start_time" : response.get("start_time"), #transscription start time 
            "end_time" : response.get("end_time"), # transcriptipn end time
            "keep" : response.get("keep"), # boolean variable for expensive classifier
            "confidence" : response.get("confidence"), # a score from 0-1 based on how confident Jev is 
            "reason" : response.get("reason"), # reason from Jev Classifier, 6 labels
            "embedding" : response.get('embedding') # large dimensional vector 
        }

@app.post("/query")
def process_query(userRequest: QueryRequest) -> QueryResult:
    model_response = query_transport(userRequest.question, userRequest.userID)

    return {
        "answer" : model_response
    }


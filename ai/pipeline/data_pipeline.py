# module imports
from transcription import transcriber
from trigger_model import jev_api
from representation import text_embedder
from requests.exceptions import ConnectionError

# import time for sleep
import time

# set environment variables
SLEEP_BASE:int = 1
RETRIES:int = 5

def handle_classification(transcript_str, number_of_attempts_used:int=0, try_again_limit:int=RETRIES):
    # Ask the trigger model if the transcript is memorable
    classification_response = jev_api.is_memorable_transcription(transcript_str)
    status = classification_response.get('status')
    if status == 5:
        # If TypeSafe messed up its response, try again
        return handle_classification(transcript_str, number_of_attempts_used=number_of_attempts_used+1, try_again_limit=try_again_limit)
    elif status != 1:
        # If we had some form of exception that wasn't resolved by the RetryPolicy, make a note of it; Don't need to retry cause RetryPolicy handles that and the ones that don't retry we'd end immediantly regardless
        classification_response['reason'] = f'An Exception was encountered during Classification: {classification_response.get("error")}'
        
    return classification_response

# where the pipeline begins
def data_transport(audio):

    #transcripe the audio
    transcription_data = transcriber.transcribe(audio)

    transcript_str = transcription_data["transcript_string"]
    if transcript_str == "":
        return

    # embed string first
    text_vector = text_embedder.embed_transcription(transcript_str)

    # check if its memorable
    try:
        cheap_classification = handle_classification(transcript_str)
    except Exception as e:
        cheap_classification = {'transcription_chunk': transcript_str, 'keep': None, 'confidence': None, 'reason': f'An Exception was raised during classification', 'status': -1, 'error': e}

    keep_val = cheap_classification.get('keep')
    if keep_val is not None and keep_val: # if true continue pipeline to KG
        print("PLACEHOLDER: Update when rest of pipeline is developed.")

    # store embedding in vector database
    print("PLACEHOLDER: Store in database when possible")

    return transcription_data, cheap_classification, text_vector


if __name__ == "__main__":
    print("Hello World")

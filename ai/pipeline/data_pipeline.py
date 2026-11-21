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

def handle_classification(transcript_str, number_of_attempts_used:int=0, try_again_limit:int=RETRIES, last_status:int=-1, error_reason_overwrite:str=''):
    # stop retrying if we've reached the maximum retries
    if number_of_attempts_used > try_again_limit:
        return {'transcription_chunk': transcript_str, 'keep': None, 'confidence': None, 'reason': f'An Exception was encountered during Classification: {error_reason_overwrite}', 'status': last_status, 'error': error_reason_overwrite}

    # Ask the trigger model if the transcript is memorable
    classification_response = jev_api.is_memorable_transcription(transcript_str)
    status = classification_response.get('status')
    error_msg = classification_response.get('error')
   
    if status == 1: 
        # No Error, no need to retry
        return classification_response  
    elif status == 3: 
        # Rate Limit Exceeded, wait a bit, we'll be retrying this
        time.sleep(SLEEP_BASE * pow(number_of_attempts_used + 1, 2))
    elif status == 2 or status == 4 or status == 6: 
        # Server Down, API Key Error, or our Input is Wrong, end immediantly without retrying
        return handle_classification(transcript_str, number_of_attempts_used=1, try_again_limit=0, last_status=status, error_reason_overwrite=error_msg)
        
    # Retry if TypeSafe made a mistake, TypeSafe timed out or Rate Limit was exceeded
    return handle_classification(transcript_str, number_of_attempts_used=number_of_attempts_used + 1, try_again_limit=try_again_limit, last_status=status, error_reason_overwrite=error_msg)
            

# where the pipeline begins
def data_transport(audio):

    #transcripe the audio
    transcription_data = transcriber.transcribe(audio)

    transcript_str = transcription_data["transcript_string"]
    if transcript_str == "":
        return

    # embed string first
    try:
        text_vector = text_embedder.embed_transcription(transcript_str)
    except ConnectionError:
        text_vector = None
    
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

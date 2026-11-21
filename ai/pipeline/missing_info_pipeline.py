from representation.text_embedder import embed_transcription
from pipeline.data_pipeline import handle_classification
from requests.exceptions import ConnectionError

# A standalone function for calling handle_classification
def redo_classification(transcript_str:str):
    try:
        cheap_classification = handle_classification(transcript_str)
    except Exception as e:
        print(e)
        cheap_classification = {'transcription_chunk': transcript_str, 'keep': None, 'confidence': None, 'reason': f'An Exception was raised during classification', 'status': -1, 'error': e}
    return cheap_classification

# A standalone function for calling embed_transcription
def redo_embedding(transcript_str:str):
    try:
        return embed_transcription(transcript_str)
    except ConnectionError:
        return None

# where the pipeline begins; we don't need to check if the dictionary keys exist because a check in api/server.py does that for us
def missing_info_transport(information_dict) -> dict:
    # define the keys with information_dict's values 
    classification_data:dict = {}
    grab_keys:list = ['keep', 'confidence', 'reason']
    for key in grab_keys:
        classification_data[key] = information_dict.get(key)
    
    transcript_string:str = information_dict.get('transcript_string')

    # if backend ommitted classification keys or keep is None (which it is when there is a Classification Error), send it off to the Classifier
    if information_dict.get('keep') is None:
        classification_data = redo_classification(transcript_string)
    
    # if backend ommitted the embedding vector or the embedding vector is None (which it is when the Embedding Model isn't available), send it off to the Embedding Model to be embedded
    embedding_vector = None
    if information_dict.get('embedding') is None:
        embedding_vector = redo_embedding(transcript_string)
    
    return {
        "transcript_string" : information_dict.get("transcript_string"), # the transcription as a string 
        "start_time" : information_dict.get("start_time"), #transscription start time 
        "end_time" : information_dict.get("end_time"), # transcriptipn end time
        "keep" : classification_data.get("keep"), # boolean variable for expensive classifier
        "confidence" : classification_data.get("confidence"), # a score from 0-1 based on how confident Jev is 
        "reason" : classification_data.get("reason"), # reason from Jev Classifier, 6 labels
        "embedding" : embedding_vector # large dimensional vector 
    }
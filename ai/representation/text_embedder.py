# file for text embeddings for the both pipeline processes
# USES embeddinggemma:300m

import os
import requests

# constants taking from .env
EMBED_URL = os.environ.get("EMBED_URL", "http://localhost:11434/api/embed")
TEXT_EMBEDDER = os.environ.get("EMBED_MODEL", "embeddinggemma:300m")



def make_request(text):
    body = { # request
        "model" : TEXT_EMBEDDER,
        "input" : text,
    }

    response = requests.post(EMBED_URL, json=body, timeout=120) 
    response.raise_for_status()
    
    return response.json()["embeddings"][0] # response is a list
                                            # so return the single vector stored hence the index

# produces query embedding for text.
def embed_query(question):
    return make_request(f"task: search result | query: {question}")

# produces the semnatic vector with the reqest
def embed_transcription(transcription):
    return make_request(f"title: none | text: {transcription}")


if __name__ == "__main__":
    print("Hello World")


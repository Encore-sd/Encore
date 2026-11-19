import os 
import requests
from representation import text_embedder # imported module

# search URL for back end to make the request
SEARCH_URL = os.environ.get("SEARCH_URL" , "PLACEHOLDER") # TODO: update placeholder to backend link

def make_request(question, embedded, topK, userID):
    body = {
        "userID" : userID, #userID taken.
        "topK" : topK, # top K rows to return
        "embedding" : embedded, #query to embedding
        "question" : question # question the user asked for future key word search
    }

    # make the call
    response = requests.post(SEARCH_URL, json=body, timeout=120)
    response.raise_for_status()

    return response.json()

def retrieve_info(query, topK, userID):
    embedding = text_embedder.embed_query(query) # embed query using embedder
    
    # call backend for transcript rows
    response = make_request(query, embedding, topK, userID)
    return response

if __name__ == "__main__":
    print("Hello World")

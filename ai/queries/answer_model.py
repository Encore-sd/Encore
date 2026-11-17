import requests 
from pathlib import Path
import os

#system prompt as a constant
SYSTEM_PROMPT = (Path(__file__).resolve().parent / "QUERY_SYSTEM_PROMPT.md").read_text(encoding="utf-8").strip()
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/chat")
ANSWER_MODEL = os.environ.get("ANSWER_MODEL", "qwen3:4b-instruct")


#function to format strings as context for the model.
# transcriptions_received is a list of dicts, each with a "transcript_string" key (same key the pipeline saves)
def format_transcriptions(transcriptions_received):
    formatted = []

    #format ex: [1] This is a memory that is retrived
    for i, segment in enumerate(transcriptions_received, start=1):
        app_str = f"[{i}] {segment['transcript_string']}"
        formatted.append(app_str)

    #join each line in the list as one with new lines for model context
    return "\n".join(formatted)

# since this is using an OLLAMA model, this will need a request to the "server"
def make_request(transcriptions, user_question):

    body = {
        "model" : ANSWER_MODEL, 
        "stream" : False, # set True for words being streamlined instead of waiting.
        "options" : {"temperature": 0, "num_ctx" : 16384},
        "messages": [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Memory segments:\n{transcriptions}\n\nQuestion: {user_question}"},
        ],    
    }

    response = requests.post(OLLAMA_URL, json=body, timeout=120)  # json= turns the dict into the request body
    response.raise_for_status()                            # raises an error if the status is not 200

    return response.json()                                 # the response body as a Python dict

# transcritions are from the retriever
# function that gets called from the query pipeline
def get_answer(transcriptions_received, user_question):
    transcriptions = format_transcriptions(transcriptions_received)

    data = make_request(transcriptions, user_question)

    return data["message"]["content"]


# main for testing, just says hello world after testing.
if __name__ == "__main__":
    print("Hello World")

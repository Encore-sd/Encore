# module imports
from transcription import transcriber
from trigger_model import jev_api
from representation import text_embedder

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
    cheap_classification = jev_api.is_memorable_transcription(transcript_str)
    if cheap_classification["keep"]: # if true continue pipeline to KG
        print("PLACEHOLDER: Update when rest of pipeline is developed.")

    # store embedding in vector database
    print("PLACEHOLDER: Store in database when possible")

    return transcription_data, cheap_classification, text_vector


if __name__ == "__main__":
    print("Hello World")

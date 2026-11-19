from representation.retriever import retriever # imported module
from queries import answer_model

#constant K
K = 10

def query_transport(userQuery, userID):
    # search K rows, and retrieve
    retrieved_rows = retriever.retrieve_info(userQuery, K, userID)

    if not retrieved_rows:
        model_response = "I don't have a memory of that."
    else:
        model_response = answer_model.get_answer(retrieved_rows, userQuery)

    return model_response


if __name__ == "__main__":
    print("Hello World")

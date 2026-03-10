import ollama

MODEL = "all-minilm"


def embed_texts(texts):
    if not texts:
        return []

    # Keeping the model alive for 1 hour prevents the constant disk-read
    # cycles that cause the 2-minute hangs on DRAM-less SSDs.
    response = ollama.embed(model=MODEL, input=texts, keep_alive="1h")

    return response["embeddings"]
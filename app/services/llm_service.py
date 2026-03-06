import ollama

MODEL = "phi3:mini"

def generate_answer(question, context_chunks):

    context = "\n\n".join(chunk["content"] for chunk in context_chunks)

    prompt = f"""
You are a helpful assistant that explains GitHub repositories.

Use the context below to answer the question.

Context:
{context}

Question:
{question}

Answer clearly and concisely.
"""

    response = ollama.chat(
        model=MODEL,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return response["message"]["content"]
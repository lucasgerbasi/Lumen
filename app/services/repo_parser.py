import os

SUPPORTED_EXTENSIONS = [".py", ".md", ".txt", ".json", ".yaml", ".yml"]

def extract_files(repo_path: str):
    documents = []

    for root, _, files in os.walk(repo_path):
        for file in files:
            if any(file.endswith(ext) for ext in SUPPORTED_EXTENSIONS):

                file_path = os.path.join(root, file)

                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    chunks = chunk_text(content)

                    for chunk in chunks:
                        documents.append({
                            "path": file_path,
                            "content": chunk
                        })

                except:
                    continue

    return documents

def chunk_text(text, chunk_size=500):
    chunks = []
    for i in range(0, len(text), chunk_size):
        chunks.append(text[i:i+chunk_size])
    return chunks
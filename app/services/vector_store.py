import faiss
import numpy as np

class VectorStore:

    def __init__(self, dim):
        self.index = faiss.IndexFlatL2(dim)
        self.documents = []

    def add(self, embeddings, docs):
        embeddings = np.array(embeddings).astype("float32")
        self.index.add(embeddings)
        self.documents.extend(docs)

    def search(self, query_embedding, k=3):
        query_embedding = np.array([query_embedding]).astype("float32")
        distances, indices = self.index.search(query_embedding, k)

        results = []
        for idx in indices[0]:
            if idx < len(self.documents):
                results.append(self.documents[idx])

        return results
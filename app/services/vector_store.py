from __future__ import annotations
import faiss
import numpy as np
from threading import Lock


class VectorStore:

    def __init__(self, dim: int = 384):
        self.dim = dim
        self._lock = Lock()
        self.index = faiss.IndexFlatL2(dim)
        self.documents: list[dict] = []
        self._embeddings: list[list[float]] = []

    # ── Helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _doc_key(doc: dict) -> str:
        return doc.get("source", doc.get("path", ""))

    @staticmethod
    def _top_level_key(raw_key: str) -> str:
        """
        For repo chunks whose key is "repo_name/some/file.py", return "repo_name".
        For PDF chunks whose key is "report.pdf", return "report.pdf".
        """
        parts = raw_key.replace("\\", "/").split("/")
        return parts[0] if parts else raw_key

    # ── Write ──────────────────────────────────────────────────────────────

    def add(self, embeddings: list, docs: list[dict]) -> None:
        if not embeddings:
            return
        vectors = np.array(embeddings, dtype="float32")
        with self._lock:
            self.index.add(vectors)
            self.documents.extend(docs)
            self._embeddings.extend(embeddings)

    def delete_source(self, source_key: str) -> int:
        """
        Remove all chunks that belong to source_key.
        Matches both exact keys (PDFs: "report.pdf") and prefix keys
        (repos: "my-repo" matches "my-repo/src/main.py").
        Returns the number of chunks removed.
        """
        with self._lock:
            before = len(self.documents)

            def _keep(doc: dict) -> bool:
                raw = self._doc_key(doc)
                top = self._top_level_key(raw)
                return top != source_key and raw != source_key

            surviving = [
                (doc, emb)
                for doc, emb in zip(self.documents, self._embeddings)
                if _keep(doc)
            ]

            removed = before - len(surviving)
            if removed == 0:
                return 0

            self.index = faiss.IndexFlatL2(self.dim)
            if surviving:
                docs, embs = zip(*surviving)
                self.documents = list(docs)
                self._embeddings = list(embs)
                self.index.add(np.array(self._embeddings, dtype="float32"))
            else:
                self.documents = []
                self._embeddings = []

            return removed

    def clear(self) -> None:
        with self._lock:
            self.index = faiss.IndexFlatL2(self.dim)
            self.documents = []
            self._embeddings = []

    # ── Read ───────────────────────────────────────────────────────────────

    def search(self, query_embedding: list, k: int = 3) -> list[dict]:
        if self.index.ntotal == 0:
            return []
        vec = np.array([query_embedding], dtype="float32")
        distances, indices = self.index.search(vec, min(k, self.index.ntotal))
        return [
            self.documents[idx]
            for idx in indices[0]
            if 0 <= idx < len(self.documents)
        ]

    def list_sources(self) -> list[dict]:
        """
        Return deduplicated sources with type and chunk count.
        { "key": str, "type": "pdf" | "github", "chunks": int }
        """
        top_counts: dict[str, int] = {}
        top_type: dict[str, str] = {}

        for doc in self.documents:
            raw = self._doc_key(doc)
            top = self._top_level_key(raw)
            top_counts[top] = top_counts.get(top, 0) + 1
            normalised = raw.replace("\\", "/")
            top_type[top] = "github" if "/" in normalised else "pdf"

        return [
            {"key": k, "type": top_type[k], "chunks": v}
            for k, v in sorted(top_counts.items())
        ]
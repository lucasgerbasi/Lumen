from fastapi import APIRouter
from app.services.github_loader import clone_repo
from app.services.repo_parser import extract_files
from app.services.embedding_service import embed_texts
from app.store import vector_store
from app.services.llm_service import generate_answer
from app.api import pdf_ingest

app.include_router(pdf_ingest.router)
router = APIRouter()

@router.post("/ingest/github")
def ingest_github(repo_url: str):

    repo_path = clone_repo(repo_url)
    documents = extract_files(repo_path)

    texts = [doc["content"] for doc in documents]

    embeddings = embed_texts(texts)

    vector_store.add(embeddings, documents)

    return {
        "repo_path": repo_path,
        "chunks": len(texts),
        "stored_vectors": len(embeddings)
    }

@router.post("/ask")
def ask(question: str):

    query_embedding = embed_texts([question])[0]

    results = vector_store.search(query_embedding)

    answer = generate_answer(question, results)

    return {
        "question": question,
        "answer": answer,
        "sources": results
    }
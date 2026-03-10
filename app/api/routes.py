from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool
from app.services.github_loader import clone_repo, delete_repo_clone
from app.services.repo_parser import extract_files
from app.services.embedding_service import embed_texts
from app.store import vector_store
from app.services.llm_service import generate_answer_stream
from app.api import pdf_ingest
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

router = APIRouter()
router.include_router(pdf_ingest.router)

MAX_QUESTION_LEN = 1000


# ── Ingest ─────────────────────────────────────────────────────────────────

@router.post("/ingest/github")
def ingest_github(repo_url: str):
    logger.info("Starting GitHub ingestion")

    repo_path, repo_name = clone_repo(repo_url)
    documents = extract_files(repo_path, repo_name)

    texts = [doc["content"] for doc in documents]
    logger.info(f"Extracted {len(texts)} chunks. Generating embeddings...")

    embeddings = embed_texts(texts)
    vector_store.add(embeddings, documents)
    logger.info("GitHub ingestion complete.")

    return {
        "repo": repo_name,
        "chunks": len(texts),
        "stored_vectors": len(embeddings),
    }


# ── Sources (Read) ─────────────────────────────────────────────────────────

@router.get("/sources")
def list_sources():
    """Return all ingested sources with type and chunk count."""
    return {"sources": vector_store.list_sources()}


# ── Delete ─────────────────────────────────────────────────────────────────

@router.delete("/sources/{source_key:path}")
def delete_source(source_key: str):
    """
    Remove a source from the vector store.
    For GitHub repos, also removes the cloned directory from disk.
    source_key must exactly match the 'key' field returned by GET /sources.
    """
    if not source_key or not source_key.strip():
        raise HTTPException(status_code=400, detail="source_key cannot be empty.")

    removed = vector_store.delete_source(source_key)
    if removed == 0:
        raise HTTPException(status_code=404, detail=f"Source '{source_key}' not found.")

    # If it looks like a repo name (no extension), also clean up the clone
    if "." not in source_key or source_key.endswith(".git"):
        try:
            delete_repo_clone(source_key)
        except Exception:
            pass

    logger.info(f"Deleted source '{source_key}': {removed} chunks removed.")
    return {"deleted": source_key, "chunks_removed": removed}


@router.delete("/sources")
def clear_all_sources():
    """Wipe the entire vector store."""
    vector_store.clear()
    logger.info("Vector store cleared.")
    return {"message": "All sources cleared."}


# ── Ask ────────────────────────────────────────────────────────────────────

@router.post("/ask/stream")
async def ask_stream(question: str):
    if not question or not question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    if len(question) > MAX_QUESTION_LEN:
        raise HTTPException(
            status_code=400,
            detail=f"Question exceeds {MAX_QUESTION_LEN} character limit."
        )

    logger.info(f"Received question ({len(question)} chars)")

    query_embedding = await run_in_threadpool(lambda: embed_texts([question])[0])
    results = vector_store.search(query_embedding)
    logger.info(f"Found {len(results)} relevant source chunks.")

    async def event_generator():
        logger.info("Starting LLM stream generation...")
        async for chunk in generate_answer_stream(question, results):
            if chunk:
                yield chunk
        logger.info("LLM stream completed.")

    return StreamingResponse(event_generator(), media_type="text/plain")
from fastapi import APIRouter, UploadFile, File, HTTPException
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.services.embedding_service import embed_texts
from app.store import vector_store
import os
import uuid

router = APIRouter()

PDF_DIR = "data/pdfs"
os.makedirs(PDF_DIR, exist_ok=True)

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
ALLOWED_CONTENT_TYPES = {"application/pdf"}


@router.post("/ingest/pdf")
def ingest_pdf(file: UploadFile = File(...)):

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    data = file.file.read(MAX_FILE_SIZE + 1)
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File exceeds 20 MB limit.")

    if not data.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="File does not appear to be a valid PDF.")

    safe_name = f"{uuid.uuid4().hex}.pdf"
    path = os.path.join(PDF_DIR, safe_name)

    with open(path, "wb") as f:
        f.write(data)

    try:
        reader = PdfReader(path)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    except Exception:
        os.remove(path)
        raise HTTPException(status_code=422, detail="Could not parse PDF.")

    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    raw_chunks = splitter.split_text(text)

    display_name = os.path.basename(file.filename or "upload.pdf")

    documents = [
        {"content": chunk, "source": display_name}
        for chunk in raw_chunks
    ]

    texts = [doc["content"] for doc in documents]
    embeddings = embed_texts(texts)
    vector_store.add(embeddings, documents)

    return {
        "file": display_name,
        "chunks": len(documents),
        "stored_vectors": len(embeddings),
    }
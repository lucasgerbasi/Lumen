from fastapi import APIRouter, UploadFile, File
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os

router = APIRouter()

PDF_DIR = "data/pdfs"
os.makedirs(PDF_DIR, exist_ok=True)


@router.post("/ingest/pdf")
async def ingest_pdf(file: UploadFile = File(...)):

    path = os.path.join(PDF_DIR, file.filename)

    with open(path, "wb") as f:
        f.write(await file.read())

    reader = PdfReader(path)

    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100
    )

    chunks = splitter.split_text(text)

    return {
        "file": file.filename,
        "chunks": len(chunks)
    }
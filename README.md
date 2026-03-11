# Lumen: Local Knowledge Engine

Lumen is a fully local RAG (Retrieval-Augmented Generation) application designed to help you query your documents securely. By ingesting PDFs and GitHub repositories, Lumen allows you to ask questions in plain English and receive answers grounded strictly in your own data, without any information ever leaving your machine.

---

## Core Features

* **Ingest PDFs:** Upload any PDF document. Lumen automatically extracts the text, splits it into manageable chunks, and indexes it using local embeddings.
* **Ingest GitHub Repositories:** Provide a repository URL to shallow-clone the codebase. Lumen parses supported text and code files, indexing the architecture for technical queries.
* **Contextual Q&A:** Your questions are embedded and matched against your indexed content using vector similarity. A local LLM then generates and streams an answer based specifically on those retrieved sources.
* **Source Management:** View all currently indexed materials, monitor chunk counts, delete individual sources, or clear the entire vector store as needed.

---

## Architecture & Stack

Lumen is built to be lightweight and modular, relying entirely on local inference rather than third-party cloud providers.

| Component | Technology | Description |
| --- | --- | --- |
| **Frontend** | Vanilla HTML/CSS/JS | A single-file interface requiring no build steps. |
| **Backend** | FastAPI (Python) | High-performance routing and API endpoints. |
| **Embeddings** | `all-minilm` | Fast, local vectorization handled via Ollama. |
| **LLM** | `phi3:mini` | Local chat generation handled via Ollama (easily swappable). |
| **Vector Store** | FAISS | In-memory `IndexFlatL2` similarity search. |
| **Utilities** | `pypdf`, `LangChain`, `GitPython` | Robust document parsing, text splitting, and cloning. |

---

## Setup Instructions

### Prerequisites

* Python 3.9 or higher
* [Ollama](https://ollama.com/) installed and running locally

### 1. Clone the Repository

```bash
git clone https://github.com/lucasgerbasi/Lumen.git
cd lumen
```

### 2. Install Dependencies

```bash
pip install fastapi uvicorn pypdf langchain-text-splitters faiss-cpu gitpython ollama
```

### 3. Pull Required Models

```bash
ollama pull all-minilm   # Embedding model (~90 MB)
ollama pull phi3:mini    # Language model (~2.2 GB)
```

### 4. Run the Application

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`. To access the UI, open `index.html` directly in your browser. No separate frontend server is required.

---

## Performance & Hardware Guidelines

For optimal performance, Lumen's models should fit entirely within your GPU's VRAM. If responses take more than a minute, your system is likely offloading to system RAM or disk.

| Hardware Profile | Recommended Model | Required VRAM |
| --- | --- | --- |
| **GPU (6GB+ VRAM)** | `phi3:mini` | ~2.2 GB |
| **GPU (4GB VRAM)** | `qwen2.5:0.5b` | ~0.5 GB |
| **CPU Only** | `qwen2.5:0.5b` | N/A |

**Concurrent Loading:** To prevent Ollama from swapping models between embedding and chat requests, keep both resident in memory by setting:

```bash
OLLAMA_MAX_LOADED_MODELS=2
```

---

## Configuration

### Changing Models

* **LLM:** Edit the `MODEL` constant in `app/services/llm_service.py`. *(Alternatives: `qwen2.5:0.5b`, `gemma2:2b`, `llama3.2:1b`)*
* **Embeddings:** Edit the `MODEL` constant in `app/services/embedding_service.py`. If you change this, also update the `dim` parameter in `app/store.py` to match the new model's output dimension.

### CORS

By default the backend allows:

* Requests from `index.html` opened directly as a local file (`origin: null`)
* Any `http://localhost` or `https://localhost` origin on any port

This covers all typical local development setups with no configuration needed. To additionally allow a specific remote or LAN origin, pass it via the `ALLOWED_ORIGINS` environment variable:

```bash
ALLOWED_ORIGINS="http://192.168.1.50:3000" uvicorn app.main:app
```

Multiple origins are comma-separated. All other origins are blocked with a 403.

---

## API Reference

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/ingest/pdf` | Upload and index a PDF via multipart form data. |
| `POST` | `/ingest/github?repo_url=…` | Clone and index a remote repository. |
| `GET` | `/sources` | List all currently indexed sources with type and chunk count. |
| `DELETE` | `/sources/{key}` | Remove a specific source from the index by its key. |
| `DELETE` | `/sources` | Clear the entire vector store. |
| `POST` | `/ask/stream?question=…` | Submit a query and stream the LLM's response. |

---

## Project Structure

```
lumen/
├── index.html                   # Single-file frontend interface
├── app/
│   ├── main.py                  # FastAPI application and CORS configuration
│   ├── store.py                 # Singleton VectorStore initialization
│   ├── api/
│   │   ├── routes.py            # Core API endpoints
│   │   └── pdf_ingest.py        # PDF upload handling
│   └── services/
│       ├── vector_store.py      # FAISS wrapper with delete functionality
│       ├── embedding_service.py # Ollama embedding integration
│       ├── llm_service.py       # Ollama chat generation and streaming
│       ├── github_loader.py     # Repository cloning and URL validation
│       └── repo_parser.py       # File extraction and text chunking
└── data/
    ├── pdfs/                    # Uploaded PDFs (gitignored)
    └── repos/                   # Cloned repositories (gitignored)
```

---

## Current Limitations

* **Ephemeral Storage:** The FAISS vector store is in-memory. All indexed data is lost when the server restarts.
* **No Authentication:** Lumen is designed for local personal use. Do not expose the server publicly without adding authentication.
* **Repository Hosts:** Ingestion is restricted to `github.com`, `gitlab.com`, and `bitbucket.org`.
* **PDF Size Limit:** Uploads are capped at 20 MB.

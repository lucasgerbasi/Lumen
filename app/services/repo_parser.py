import os
from langchain_text_splitters import RecursiveCharacterTextSplitter

SUPPORTED_EXTENSIONS = {".py", ".md", ".txt", ".json", ".yaml", ".yml"}
MAX_FILE_SIZE = 512 * 1024   # 512 KB per file
MAX_TOTAL_FILES = 500


def extract_files(repo_path: str, repo_name: str) -> list[dict]:
    documents = []
    base = os.path.realpath(repo_path)
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    file_count = 0

    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if not d.startswith('.')]

        for file in files:
            if file_count >= MAX_TOTAL_FILES:
                break

            if not any(file.endswith(ext) for ext in SUPPORTED_EXTENSIONS):
                continue

            file_path = os.path.join(root, file)
            real_path = os.path.realpath(file_path)

            if not real_path.startswith(base + os.sep):
                continue  # symlink escape

            if os.path.getsize(real_path) > MAX_FILE_SIZE:
                continue

            try:
                with open(real_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                # Store as "repo_name/relative/path" so list_sources can roll up
                # all chunks to the repo_name key easily.
                # Use forward slashes always — os.path.relpath uses backslashes on Windows.
                rel_path = os.path.relpath(real_path, base).replace("\\", "/")
                source_key = f"{repo_name}/{rel_path}"
                chunks = splitter.split_text(content)

                for chunk in chunks:
                    documents.append({"path": source_key, "content": chunk})

                file_count += 1

            except Exception:
                continue

    return documents
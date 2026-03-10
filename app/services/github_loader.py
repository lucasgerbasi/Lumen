from __future__ import annotations
from git import Repo
from fastapi import HTTPException
from urllib.parse import urlparse
import ipaddress
import socket
import shutil
import re
import os

REPO_DIR = "data/repos"

_ALLOWED_HOSTS = {"github.com", "gitlab.com", "bitbucket.org"}
_REPO_NAME_RE = re.compile(r'^[a-zA-Z0-9_.\-]{1,100}$')


def _validate_repo_url(url: str) -> str:
    try:
        parsed = urlparse(url)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid URL.")

    if parsed.scheme != "https":
        raise HTTPException(status_code=400, detail="Only HTTPS URLs are allowed.")

    host = parsed.hostname or ""

    if host not in _ALLOWED_HOSTS:
        raise HTTPException(
            status_code=400,
            detail=f"Host '{host}' is not an allowed git provider."
        )

    try:
        resolved_ip = socket.gethostbyname(host)
        ip = ipaddress.ip_address(resolved_ip)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise HTTPException(status_code=400, detail="Resolved IP is not a public address.")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Could not resolve host.")

    return url


def clone_repo(repo_url: str) -> tuple[str, str]:
    """
    Clone the repo and return (local_path, repo_name).
    repo_name is the sanitised directory name used as the source key.
    """
    _validate_repo_url(repo_url)

    os.makedirs(REPO_DIR, exist_ok=True)

    raw_name = repo_url.rstrip("/").split("/")[-1]
    raw_name = re.sub(r'\.git$', '', raw_name)

    if not _REPO_NAME_RE.match(raw_name):
        raise HTTPException(status_code=400, detail="Invalid repository name.")

    local_path = os.path.realpath(os.path.join(REPO_DIR, raw_name))
    base = os.path.realpath(REPO_DIR)

    if not local_path.startswith(base + os.sep):
        raise HTTPException(status_code=400, detail="Invalid repository path.")

    if os.path.exists(local_path):
        return local_path, raw_name

    try:
        Repo.clone_from(repo_url, local_path, depth=1)
    except Exception:
        raise HTTPException(status_code=422, detail="Failed to clone repository.")

    return local_path, raw_name


def delete_repo_clone(repo_name: str) -> bool:
    """
    Delete the cloned repo directory from disk.
    Returns True if it existed and was removed, False otherwise.
    """
    # Sanitise before using in a path
    if not _REPO_NAME_RE.match(repo_name):
        return False

    local_path = os.path.realpath(os.path.join(REPO_DIR, repo_name))
    base = os.path.realpath(REPO_DIR)

    if not local_path.startswith(base + os.sep):
        return False

    if os.path.exists(local_path):
        shutil.rmtree(local_path)
        return True

    return False
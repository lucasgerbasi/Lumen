from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
import os
import re

app = FastAPI(title="AI Knowledge Engine")

# Allows opening index.html directly as a file (origin: null) and any
# localhost port.
_ENV_ORIGINS = os.getenv("ALLOWED_ORIGINS", "")
_EXTRA_ORIGINS = [o.strip() for o in _ENV_ORIGINS.split(",") if o.strip()]
_LOCALHOST_RE = re.compile(r'^https?://localhost(:\d+)?$')


def _is_allowed_origin(origin: str) -> bool:
    if not origin or origin == "null":
        return True
    if _LOCALHOST_RE.match(origin):
        return True
    return origin in _EXTRA_ORIGINS


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.middleware("http")
async def enforce_cors(request: Request, call_next):
    origin = request.headers.get("origin", "")
    if origin and not _is_allowed_origin(origin):
        from fastapi.responses import Response
        return Response(status_code=403, content="CORS origin not allowed")
    response = await call_next(request)
    return response


app.include_router(router)
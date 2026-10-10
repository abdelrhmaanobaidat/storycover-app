import time
import uuid

from fastapi import FastAPI, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from . import __version__, gemini, storage
from .config import settings

app = FastAPI(title="StoryCover", version=__version__)

REQUESTS = Counter("http_requests_total", "HTTP requests", ["method", "path", "status"])
LATENCY = Histogram("http_request_duration_seconds", "Request latency", ["path"])
COVERS = Counter("covers_generated_total", "Story covers generated")


@app.middleware("http")
async def record_metrics(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    path = request.scope.get("route").path if request.scope.get("route") else request.url.path
    LATENCY.labels(path).observe(time.perf_counter() - start)
    REQUESTS.labels(request.method, path, response.status_code).inc()
    return response


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    return HTMLResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/", response_class=HTMLResponse)
def index():
    return INDEX_HTML


@app.post("/api/generate")
async def generate(title: str = Form(...), photo: UploadFile = Form(...)):
    if not photo.content_type or not photo.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Upload must be an image")

    data = await photo.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty upload")
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="Image too large")

    try:
        cover, mime = gemini.generate_cover(data, photo.content_type, title.strip())
    except gemini.CoverGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    ext = mime.split("/")[-1]
    name = f"covers/{uuid.uuid4().hex}.{ext}"
    url = storage.upload_cover(name, cover, mime)

    COVERS.inc()
    return JSONResponse({"title": title, "object": name, "url": url})


INDEX_HTML = """<!doctype html>
<title>StoryCover</title>
<main style="max-width:32rem;margin:4rem auto;font-family:system-ui">
  <h1>StoryCover</h1>
  <p>Upload a photo and a story name to generate a book cover.</p>
  <form method="post" action="/api/generate" enctype="multipart/form-data">
    <p><input name="title" placeholder="Story name" required></p>
    <p><input type="file" name="photo" accept="image/*" required></p>
    <p><button type="submit">Generate cover</button></p>
  </form>
</main>
"""

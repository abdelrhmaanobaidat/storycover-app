import time
import uuid

from fastapi import FastAPI, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
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
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


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
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>StoryCover</title>
<style>
  :root { color-scheme: light dark; }
  * { box-sizing: border-box; }
  body {
    margin: 0; min-height: 100vh; display: grid; place-items: center;
    font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
    background: linear-gradient(160deg, #f5f3ff, #eef2ff);
    color: #1e1b2e; padding: 2rem 1rem;
  }
  .card {
    width: 100%; max-width: 30rem; background: #fff; border-radius: 16px;
    box-shadow: 0 10px 40px rgba(30, 27, 46, .12); padding: 2rem;
  }
  h1 { margin: 0 0 .25rem; font-size: 1.6rem; }
  p.lead { margin: 0 0 1.5rem; color: #5b5676; }
  label { display: block; font-size: .85rem; font-weight: 600; margin-bottom: .35rem; }
  input[type=text], input[type=file] {
    width: 100%; padding: .6rem .7rem; margin-bottom: 1rem; border: 1px solid #d6d3e6;
    border-radius: 9px; font-size: 1rem; background: #fbfaff;
  }
  button {
    width: 100%; padding: .7rem; border: 0; border-radius: 9px; background: #6d5efc;
    color: #fff; font-size: 1rem; font-weight: 600; cursor: pointer;
  }
  button:disabled { opacity: .6; cursor: default; }
  .result { margin-top: 1.5rem; text-align: center; }
  .result img { width: 100%; border-radius: 12px; box-shadow: 0 6px 24px rgba(30, 27, 46, .18); }
  .status { margin-top: 1rem; text-align: center; color: #5b5676; }
  .status.error { color: #c0392b; }
  a.again { display: inline-block; margin-top: 1rem; color: #6d5efc; }
</style>
</head>
<body>
  <main class="card">
    <h1>StoryCover</h1>
    <p class="lead">Upload a photo and a story name, and a cover is generated for you.</p>
    <form id="form">
      <label for="title">Story name</label>
      <input id="title" name="title" type="text" placeholder="The Brave Little Cat" required>
      <label for="photo">Photo</label>
      <input id="photo" name="photo" type="file" accept="image/*" required>
      <button id="go" type="submit">Generate cover</button>
    </form>
    <div id="status" class="status"></div>
    <div id="result" class="result"></div>
  </main>
  <script>
    const form = document.getElementById('form');
    const statusEl = document.getElementById('status');
    const resultEl = document.getElementById('result');
    const go = document.getElementById('go');
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      resultEl.innerHTML = '';
      statusEl.className = 'status';
      statusEl.textContent = 'Generating your cover, this can take a few seconds.';
      go.disabled = true;
      try {
        const res = await fetch('/api/generate', { method: 'POST', body: new FormData(form) });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Something went wrong');
        statusEl.textContent = '';
        const img = document.createElement('img');
        img.alt = data.title;
        img.src = data.url;
        const again = document.createElement('a');
        again.className = 'again';
        again.href = '#';
        again.textContent = 'Make another';
        again.onclick = () => { location.reload(); return false; };
        resultEl.append(img, again);
      } catch (err) {
        statusEl.className = 'status error';
        statusEl.textContent = err.message;
      } finally {
        go.disabled = false;
      }
    });
  </script>
</body>
</html>
"""

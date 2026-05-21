"""
GLM-OCR upload website.

Run:
    python webapp.py
Then open:
    http://localhost:8000

Supports:
- Multiple files at once (drag several, or pick several)
- Images (png, jpg, webp, etc.)
- PDFs (each page is rendered to an image and OCR'd separately)
"""

import io
import os
import time
from typing import List

import fitz  # PyMuPDF
import torch
import uvicorn
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from PIL import Image
from transformers import AutoModelForImageTextToText, AutoProcessor

MODEL = "zai-org/GLM-OCR"
MAX_LONG_EDGE = int(os.environ.get("OCR_MAX_LONG_EDGE", "1280"))
PDF_RENDER_DPI = int(os.environ.get("OCR_PDF_DPI", "200"))
MAX_FILES_PER_REQUEST = int(os.environ.get("OCR_MAX_FILES", "10"))
DEVICE = os.environ.get("OCR_DEVICE") or ("mps" if torch.backends.mps.is_available() else "cpu")
DTYPE = torch.float16 if DEVICE == "mps" else torch.float32

print(f"[startup] device={DEVICE} dtype={DTYPE} max_long_edge={MAX_LONG_EDGE}")
print("[startup] loading model (first run downloads weights, can take a few minutes)...")
_t0 = time.time()
processor = AutoProcessor.from_pretrained(MODEL, trust_remote_code=True)
model = (
    AutoModelForImageTextToText.from_pretrained(MODEL, torch_dtype=DTYPE, trust_remote_code=True)
    .to(DEVICE)
    .eval()
)
print(f"[startup] model ready in {time.time() - _t0:.1f}s")

app = FastAPI(title="GLM-OCR Web")


def run_ocr(image: Image.Image, prompt: str) -> tuple[str, float]:
    if max(image.size) > MAX_LONG_EDGE:
        w, h = image.size
        scale = MAX_LONG_EDGE / max(w, h)
        image = image.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": prompt},
            ],
        }
    ]
    inputs = processor.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
    ).to(DEVICE)

    t1 = time.time()
    with torch.inference_mode():
        out = model.generate(**inputs, max_new_tokens=2048, do_sample=False, temperature=0.0)
    gen = out[:, inputs["input_ids"].shape[1] :]
    text = processor.batch_decode(gen, skip_special_tokens=True)[0]
    return text, time.time() - t1


def pdf_to_images(raw: bytes) -> List[Image.Image]:
    """Render every page of a PDF to a PIL image."""
    images: List[Image.Image] = []
    doc = fitz.open(stream=raw, filetype="pdf")
    try:
        zoom = PDF_RENDER_DPI / 72.0
        matrix = fitz.Matrix(zoom, zoom)
        for page in doc:
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            images.append(img)
    finally:
        doc.close()
    return images


def load_units(upload: UploadFile, raw: bytes) -> List[tuple[str, Image.Image]]:
    """Return a list of (label, image) units for one uploaded file.

    PDFs become one unit per page; images become a single unit.
    """
    name = upload.filename or "upload"
    is_pdf = name.lower().endswith(".pdf") or (upload.content_type or "").lower() == "application/pdf"
    if is_pdf:
        images = pdf_to_images(raw)
        return [(f"{name} — page {i + 1}/{len(images)}", img) for i, img in enumerate(images)]
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    return [(name, img)]


INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>GLM-OCR</title>
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>
  :root { color-scheme: light dark; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         max-width: 880px; margin: 40px auto; padding: 0 16px; line-height: 1.5; }
  h1 { margin-bottom: 4px; }
  .sub { color: #777; margin-top: 0; }
  .drop { border: 2px dashed #888; border-radius: 12px; padding: 30px;
          text-align: center; cursor: pointer; transition: background 0.15s; }
  .drop.hover { background: rgba(0,128,255,0.08); border-color: #08f; }
  .row { display: flex; gap: 12px; align-items: center; margin: 16px 0; flex-wrap: wrap; }
  input[type=text] { flex: 1; min-width: 260px; padding: 8px 10px; font-size: 14px;
                     border-radius: 8px; border: 1px solid #888; }
  button { padding: 10px 18px; font-size: 15px; border-radius: 8px; border: 0;
           background: #08f; color: white; cursor: pointer; }
  button:disabled { opacity: 0.5; cursor: wait; }
  .list { list-style: none; padding: 0; margin: 12px 0 0; text-align: left; }
  .list li { display: flex; justify-content: space-between; gap: 8px; padding: 6px 0;
             border-bottom: 1px solid rgba(127,127,127,0.2); font-size: 14px; }
  .list .rm { background: transparent; color: #c00; padding: 0 6px; }
  pre { background: rgba(127,127,127,0.12); padding: 14px; border-radius: 8px;
        white-space: pre-wrap; word-break: break-word; }
  .meta { color: #777; font-size: 13px; }
  .err { color: #c00; }
  .result { margin-top: 20px; padding-top: 12px; border-top: 1px solid rgba(127,127,127,0.3); }
  .result h3 { margin: 0 0 6px; font-size: 15px; }
  .result .meta { margin-bottom: 6px; }
</style>
</head>
<body>
  <h1>GLM-OCR</h1>
  <p class="sub">Upload images or PDFs. Up to 10 files at a time.</p>

  <div id="drop" class="drop">
    <p><strong>Drop files here</strong> or click to choose<br>
       <span class="meta">Images (png/jpg/webp…) or PDFs. PDFs are split per page.</span></p>
    <input id="file" type="file" accept="image/*,application/pdf" multiple style="display:none" />
    <ul id="list" class="list"></ul>
  </div>

  <div class="row">
    <input id="prompt" type="text" value="Text Recognition:" />
    <button id="go" disabled>Run OCR</button>
    <button id="reset" type="button" style="background:#666">Reset</button>
  </div>

  <p id="status" class="meta"></p>
  <div id="results"></div>

<script>
const MAX_FILES = 10;
const drop = document.getElementById('drop');
const file = document.getElementById('file');
const listEl = document.getElementById('list');
const go = document.getElementById('go');
const status = document.getElementById('status');
const results = document.getElementById('results');
const promptEl = document.getElementById('prompt');
const resetBtn = document.getElementById('reset');
let chosen = [];

function renderList() {
  listEl.innerHTML = '';
  chosen.forEach((f, i) => {
    const li = document.createElement('li');
    const left = document.createElement('span');
    left.textContent = (i + 1) + '. ' + f.name + '  (' + Math.round(f.size / 1024) + ' KB)';
    const rm = document.createElement('button');
    rm.textContent = '✕';
    rm.className = 'rm';
    rm.title = 'Remove';
    rm.onclick = (e) => { e.stopPropagation(); chosen.splice(i, 1); renderList(); };
    li.appendChild(left);
    li.appendChild(rm);
    listEl.appendChild(li);
  });
  go.disabled = chosen.length === 0;
}

function addFiles(files) {
  const incoming = Array.from(files || []);
  for (const f of incoming) {
    if (chosen.length >= MAX_FILES) {
      status.textContent = 'Max ' + MAX_FILES + ' files. Extra files ignored.';
      status.classList.add('err');
      break;
    }
    chosen.push(f);
  }
  renderList();
}

function resetAll() {
  chosen = [];
  file.value = '';
  renderList();
  results.innerHTML = '';
  status.textContent = '';
  status.classList.remove('err');
  promptEl.value = 'Text Recognition:';
}
resetBtn.addEventListener('click', resetAll);

drop.addEventListener('click', (e) => {
  if (e.target.tagName === 'BUTTON') return;
  file.click();
});
file.addEventListener('change', e => addFiles(e.target.files));
drop.addEventListener('dragover', e => { e.preventDefault(); drop.classList.add('hover'); });
drop.addEventListener('dragleave', () => drop.classList.remove('hover'));
drop.addEventListener('drop', e => {
  e.preventDefault(); drop.classList.remove('hover');
  addFiles(e.dataTransfer.files);
});

function appendResult(label, text, seconds, isError) {
  const div = document.createElement('div');
  div.className = 'result';
  const h = document.createElement('h3');
  h.textContent = label;
  const meta = document.createElement('div');
  meta.className = 'meta';
  meta.textContent = isError ? 'Failed' : ('Done in ' + seconds.toFixed(1) + 's');
  const pre = document.createElement('pre');
  pre.textContent = text;
  if (isError) pre.classList.add('err');
  div.appendChild(h);
  div.appendChild(meta);
  div.appendChild(pre);
  results.appendChild(div);
}

go.addEventListener('click', async () => {
  if (chosen.length === 0) return;
  go.disabled = true;
  results.innerHTML = '';
  status.classList.remove('err');
  status.textContent = 'Uploading ' + chosen.length + ' file(s)…';

  const fd = new FormData();
  for (const f of chosen) fd.append('files', f);
  fd.append('prompt', promptEl.value || 'Text Recognition:');

  try {
    const r = await fetch('/ocr', { method: 'POST', body: fd });
    const j = await r.json();
    if (!r.ok) throw new Error(j.error || ('HTTP ' + r.status));
    status.textContent = 'Finished ' + j.results.length + ' unit(s) in '
                         + j.total_seconds.toFixed(1) + 's';
    for (const item of j.results) {
      appendResult(item.label, item.error ? item.error : item.text, item.seconds, !!item.error);
    }
  } catch (err) {
    status.textContent = 'Error: ' + err.message;
    status.classList.add('err');
  } finally {
    go.disabled = chosen.length === 0;
  }
});
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return INDEX_HTML


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "device": DEVICE}


@app.post("/ocr")
async def ocr(
    files: List[UploadFile] = File(...),
    prompt: str = Form("Text Recognition:"),
) -> JSONResponse:
    if len(files) > MAX_FILES_PER_REQUEST:
        return JSONResponse(
            {"error": f"Too many files. Max {MAX_FILES_PER_REQUEST} per request."},
            status_code=400,
        )

    units: List[tuple[str, Image.Image]] = []
    for upload in files:
        raw = await upload.read()
        try:
            units.extend(load_units(upload, raw))
        except Exception as e:
            units.append((f"{upload.filename or 'upload'} (failed to read)", None))  # type: ignore
            # store the error message on the placeholder via a sentinel below
            units[-1] = (units[-1][0], e)  # type: ignore

    results = []
    total_start = time.time()
    for label, payload in units:
        if isinstance(payload, Exception):
            results.append({"label": label, "error": f"Could not load: {payload}", "seconds": 0.0})
            continue
        try:
            text, seconds = run_ocr(payload, prompt)
            results.append({"label": label, "text": text, "seconds": seconds})
        except Exception as e:
            results.append({"label": label, "error": f"OCR failed: {e}", "seconds": 0.0})

    return JSONResponse(
        {
            "results": results,
            "total_seconds": time.time() - total_start,
            "prompt": prompt,
        }
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

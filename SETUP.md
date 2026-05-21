# Setup guide — run GLM-OCR locally on your machine

This is a step-by-step walkthrough of exactly how this project was set up,
written so anyone can clone the repo and reproduce it. No prior experience
with PyTorch or HuggingFace required.

It covers two ways to use the OCR:

1. **Terminal** — `python run_ocr.py path/to/image.png`
2. **Website** — drag-and-drop upload at `http://localhost:8000`

---

## 1. What you need

| Requirement | Why | How to check |
|---|---|---|
| **Python 3.10+** | The code uses modern type hints | `python --version` |
| **macOS or Linux** | Tested on Apple Silicon (M-series) with MPS GPU; works on CPU too | — |
| **~6 GB free disk** | 2.5 GB for the OCR model + a few GB for Python packages | — |
| **Internet on first run** | To download the model from HuggingFace. After that, everything works offline. | — |
| **git** | To clone this repo | `git --version` |

If you're on Windows, the same instructions work but commands like
`source .venv/bin/activate` become `.venv\Scripts\activate`.

---

## 2. Clone the repo

```bash
git clone https://github.com/venkatesbonthala2932/GLM-OCR.git
cd GLM-OCR
```

---

## 3. Create a virtual environment

A "venv" keeps this project's Python packages separate from the rest of your
system so nothing conflicts.

```bash
python3 -m venv .venv
source .venv/bin/activate
```

After activation your shell prompt should show `(.venv)` at the front.
**Every time you open a new terminal to work on this project, run that
`source` line again.**

---

## 4. Install dependencies

Two steps — the OCR base, then the webapp extras:

```bash
# (a) Install the GLM-OCR base package + the heavy layout/model deps
#     (torch, transformers, torchvision, opencv, etc.)
pip install -e ".[layout]"

# (b) Install the extras needed by webapp.py and the test tooling
pip install -r requirements-webapp.txt
```

This downloads roughly 3–4 GB of Python packages. Grab a coffee.

> **Apple Silicon note:** PyTorch will use your Mac's GPU automatically
> through MPS (Metal Performance Shaders). On Intel Macs or Linux without
> a CUDA GPU it falls back to CPU — still works, just slower.

---

## 5. First-time model download (one-time, ~2.5 GB)

The OCR model itself isn't in this repo — it's downloaded the first time
you run any OCR command. To trigger the download proactively:

```bash
python -c "from transformers import AutoModelForImageTextToText, AutoProcessor; \
AutoProcessor.from_pretrained('zai-org/GLM-OCR', trust_remote_code=True); \
AutoModelForImageTextToText.from_pretrained('zai-org/GLM-OCR', trust_remote_code=True)"
```

The model is cached at `~/.cache/huggingface/hub/models--zai-org--GLM-OCR/`
and reused forever after. **You only do this once per machine.**

After this is cached you can use the OCR fully offline — unplug the
internet and it will still work.

---

## 6. Way A — Run OCR from the terminal

The fastest way to test that everything works:

```bash
python run_ocr.py examples/source/code.png
```

What happens:
1. The script loads the model (~15–30 s on first run, faster on later runs).
2. It opens the image, resizes if needed, runs OCR.
3. Recognized text is printed to the terminal.

To try your own image:

```bash
python run_ocr.py /path/to/your_photo.jpg
```

Optional environment variables:

| Variable | Default | Meaning |
|---|---|---|
| `OCR_DEVICE` | `mps` on Mac, else `cpu` | Force device, e.g. `OCR_DEVICE=cpu` |
| `OCR_MAX_LONG_EDGE` | `1280` | Resize cap. Raise to `1800` for very detailed images |

---

## 7. Way B — Run the upload website

This is the friendlier option: a webpage where you drag images or PDFs and
get the OCR text back in the browser.

```bash
python webapp.py
```

On the first start you'll see:

```
[startup] device=mps dtype=torch.float16 max_long_edge=1280
[startup] loading model (first run downloads weights, can take a few minutes)...
[startup] model ready in 17.3s
INFO: Uvicorn running on http://0.0.0.0:8000
```

Open **http://localhost:8000** in your browser. You'll see:

- A drag-and-drop box (or click to choose files).
- A prompt field — leave it as `Text Recognition:` for normal text;
  use `Formula Recognition:` for math, `Chart Recognition:` for charts.
- A **Run OCR** button and a **Reset** button.

**What's supported:**

- Multiple files at once (up to 10).
- Image formats: PNG, JPG, WebP, etc.
- **PDFs** — each page is rendered to an image and OCR'd separately;
  you get one result block per page.

**Environment variables for tuning:**

| Variable | Default | What it does |
|---|---|---|
| `OCR_MAX_FILES` | `10` | Cap on files per upload |
| `OCR_PDF_DPI` | `200` | PDF render quality (higher = sharper but slower) |
| `OCR_MAX_LONG_EDGE` | `1280` | Image resize cap |
| `OCR_DEVICE` | auto | Force `cpu` if MPS misbehaves |

Example for a very detailed PDF:

```bash
OCR_PDF_DPI=300 OCR_MAX_LONG_EDGE=1800 python webapp.py
```

Stop the server with `Ctrl+C` in the terminal.

---

## 8. Optional — Run the benchmark

To verify the OCR is working correctly across different content types
(code, paper, table, handwriting, PDF), there's a benchmark that runs the
OCR over the repo's sample images and writes a Markdown report:

```bash
python tests/benchmark/run_benchmark.py
```

This takes about 5 minutes (model load + 8 sample images). When done you
get `tests/benchmark/OCR_REPORT.md` with timing and the full OCR output
for each sample.

To turn the report into a PDF:

```bash
python tests/benchmark/md_to_pdf.py
```

That writes `tests/benchmark/OCR_REPORT.pdf`.

---

## 9. Troubleshooting

### "Form data requires python-multipart to be installed"

You skipped the `requirements-webapp.txt` install step. Run:

```bash
pip install python-multipart
```

### "ModuleNotFoundError: No module named 'torch'"

The `pip install -e ".[layout]"` step didn't complete — make sure your
venv is active (`(.venv)` in your prompt) and re-run that command.

### Model loading is very slow / fails on first run

Your internet connection is being throttled by HuggingFace's anonymous
rate limit. Set a free HuggingFace token:

1. Sign up at https://huggingface.co (free).
2. Create a read token at https://huggingface.co/settings/tokens.
3. `export HF_TOKEN=hf_xxxxxxxxxxxx` and re-run.

### OCR output is empty or random garbage

You're probably feeding it a script the model wasn't trained on
(e.g. Hindi, Tamil, Arabic). GLM-OCR is strong on Chinese and English;
other scripts need a different model.

### "Out of memory" on large PDFs

Lower the PDF rendering quality:

```bash
OCR_PDF_DPI=120 python webapp.py
```

### How to know I'm running offline

After the first model download, force offline mode to confirm:

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 python webapp.py
```

If it still works, you're fully offline.

---

## 10. File map — what each file does

| File | Purpose |
|---|---|
| `webapp.py` | The upload website (FastAPI) |
| `run_ocr.py` | One-shot terminal OCR script |
| `make_receipt.py` | Helper for receipt-style test images |
| `tests/benchmark/run_benchmark.py` | Runs OCR over sample images and writes a report |
| `tests/benchmark/md_to_pdf.py` | Converts the Markdown report to PDF |
| `tests/benchmark/OCR_REPORT.md` | The latest report (auto-generated) |
| `tests/benchmark/OCR_REPORT.pdf` | PDF version of the report |
| `requirements-webapp.txt` | Extra Python packages for the webapp |
| `glmocr/` | Upstream GLM-OCR SDK (unchanged except CORS in `server.py`) |
| `examples/source/` | Sample images and a sample PDF for testing |

---

## 11. Re-clone-and-run cheat sheet

For a teammate who just wants to copy-paste:

```bash
git clone https://github.com/venkatesbonthala2932/GLM-OCR.git
cd GLM-OCR
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[layout]"
pip install -r requirements-webapp.txt
python webapp.py
# open http://localhost:8000
```

That's it.

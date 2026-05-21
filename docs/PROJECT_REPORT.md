# GLM-OCR Local Deployment — Project Report

**Prepared by:** Venkatesh Bonthala
**Date:** 2026-05-21
**Repository:** https://github.com/venkatesbonthala2932/GLM-OCR
**Status:** Working prototype, end-to-end tested

---

## 1. Executive Summary

This project deploys **GLM-OCR**, an open-source state-of-the-art OCR model
from Zhipu AI, on a local workstation and exposes it through two interfaces:

1. A **command-line script** for quick scripted use.
2. A **web application** (browser-based) for everyday non-technical use.

The system accepts images and PDFs, runs the document through a 0.9 B
parameter vision-language model on the local GPU (Apple MPS), and returns
the recognised text. It works **fully offline after the initial model
download**, with no recurring API or cloud costs.

The deployment is verified end-to-end with an automated benchmark across
eight diverse sample documents (code screenshots, scientific papers,
tables, handwritten Chinese, document seals, and multi-page PDFs). All
eight tests passed with 0 failures and an average OCR time of 44.9 s per
image on the test hardware.

**Key results**

| Metric | Value |
|---|---|
| Model | `zai-org/GLM-OCR` (0.9 B parameters) |
| Inference device | Apple Silicon (MPS) |
| Test cases passed | 8 / 8 |
| Average OCR time | 44.9 s per image |
| Total OCR time across benchmark | 359.1 s |
| One-time model download | 2.5 GB |
| Operates offline after install | Yes |
| Recurring cost | None |

---

## 2. Problem Statement

Document digitisation requires an OCR engine that is:

- **Accurate** on real-world inputs — printed pages, scans, handwriting,
  tables, formulas, multi-page PDFs.
- **Cost-effective** — no per-page API charges, no recurring subscription.
- **Private** — sensitive documents must never leave the local network.
- **Reproducible** — anyone in the team should be able to set it up on
  their own machine in under 30 minutes.

Commercial OCR APIs (Google Cloud Vision, AWS Textract, Azure Document
Intelligence) provide accuracy but introduce per-page costs, network
dependency, and data-residency concerns. An on-premise open-source model
addresses all four constraints simultaneously.

---

## 3. Solution Overview

We selected **GLM-OCR** because it currently ranks #1 on OmniDocBench V1.5
(94.62) and is fully open-source under Apache 2.0. The model is hosted
on Hugging Face and was integrated through the `transformers` library.

The deployment consists of three components:

```
┌─────────────────────┐
│   Browser / Terminal │  ← user uploads image or PDF
└──────────┬───────────┘
           │  HTTP (localhost) or CLI invocation
           ▼
┌──────────────────────┐
│   webapp.py / run_ocr.py│  ← FastAPI + uvicorn server, or one-shot script
│   (request handling,  │
│   PDF page splitting) │
└──────────┬───────────┘
           │  PIL.Image, prompt
           ▼
┌──────────────────────┐
│   GLM-OCR model       │  ← transformers + PyTorch on Apple MPS
│   (0.9 B parameters)  │
└──────────┬───────────┘
           │  recognised text
           ▼
┌──────────────────────┐
│   JSON response       │  ← rendered in browser, or printed to terminal
└──────────────────────┘
```

The model is loaded **once at startup** and kept in GPU memory for the
lifetime of the server, so each request only pays for the inference time
(typically 5–60 s depending on document complexity).

---

## 4. Technical Architecture

### 4.1 Component breakdown

| Layer | File | Technology | Responsibility |
|---|---|---|---|
| Web UI | `webapp.py` (HTML/JS embedded) | Vanilla JS, drag-and-drop | File selection, preview, results display |
| HTTP API | `webapp.py` (FastAPI app) | FastAPI, uvicorn | Receive uploads, dispatch to OCR, return JSON |
| File ingestion | `webapp.py::load_units()` | Pillow, PyMuPDF | Decode images, render PDF pages to images |
| OCR core | `webapp.py::run_ocr()` | PyTorch (MPS), transformers | Run the GLM-OCR model on one image |
| Model weights | HuggingFace cache | — | The 2.5 GB pre-trained model |
| Benchmark | `tests/benchmark/run_benchmark.py` | Python | Repeatable accuracy/perf checks |
| Reporting | `tests/benchmark/md_to_pdf.py` | python-markdown, PyMuPDF | Markdown → PDF for stakeholder deliverables |

### 4.2 Why these specific technology choices

- **FastAPI** — modern Python web framework with automatic OpenAPI docs,
  built-in multipart support, async-ready for future scaling.
- **PyMuPDF (`fitz`)** — pure Python PDF rendering with no system
  dependencies (unlike `pdf2image` which requires Poppler).
- **Apple MPS** — uses the M-series GPU on Mac without requiring CUDA
  drivers; falls back to CPU automatically on machines without MPS.
- **Embedded HTML/JS** — keeps the entire web frontend in a single Python
  file so deployment is one `python webapp.py` command, no build step.

### 4.3 Data flow for a single OCR request

1. User drops `report.pdf` (5 pages) and `photo.jpg` into the browser.
2. Browser sends a multipart `POST /ocr` with both files.
3. FastAPI parses the upload; `load_units()` converts the inputs into a
   flat list of `(label, PIL.Image)` units — 6 units total (5 PDF pages +
   1 image).
4. The server loops the units, calling `run_ocr()` on each. Each call:
   - resizes the image to a maximum 1280 px long edge,
   - constructs a chat-template prompt around the image,
   - runs `model.generate(...)` on MPS,
   - decodes the output tokens to a UTF-8 string.
5. Results are returned as JSON:
   `{ "results": [{label, text, seconds}, ...], "total_seconds": N }`
6. The browser renders one labelled result block per unit.

---

## 5. Implementation Details

### 5.1 Files added or modified

| File | Type | Purpose |
|---|---|---|
| `webapp.py` | New | The upload website (FastAPI + embedded UI) |
| `run_ocr.py` | New | Terminal one-shot OCR script |
| `make_receipt.py` | New | Helper to generate test receipt images |
| `requirements-webapp.txt` | New | Extra pip dependencies for the webapp |
| `SETUP.md` | New | Step-by-step install guide |
| `docs/PROJECT_REPORT.md` | New | This document |
| `docs/DEMO_GUIDE.md` | New | Live demo script and Q&A |
| `docs/PRE_DEMO_CHECKLIST.md` | New | Pre-presentation verification |
| `tests/benchmark/run_benchmark.py` | New | Repeatable benchmark |
| `tests/benchmark/OCR_REPORT.md` | New | Latest benchmark output |
| `tests/benchmark/OCR_REPORT.pdf` | New | PDF version of benchmark |
| `tests/benchmark/md_to_pdf.py` | New | Markdown → PDF converter |
| `glmocr/server.py` | Modified | Added CORS headers (7 lines) |

Net change: **+1500 lines, 0 deletions** from the upstream `zai-org/GLM-OCR`.

### 5.2 Key design decisions

1. **Embedded HTML inside `webapp.py`** instead of a separate frontend
   project. Rationale: one-file deployment, no build tooling, easier for
   a colleague to read and modify.
2. **Render PDF pages independently** instead of concatenating them.
   Rationale: matches the OCR model's single-image input format and
   gives per-page error isolation.
3. **Cap image size at 1280 px long edge** by default. Rationale: keeps
   GPU memory under 8 GB on the test hardware while preserving accuracy
   for typical documents. Configurable via env var.
4. **Sequential rather than parallel OCR** across uploaded files.
   Rationale: a single MPS GPU is the bottleneck; parallel calls would
   queue internally and add overhead.

### 5.3 Environment variables (operator tuning)

| Variable | Default | Effect |
|---|---|---|
| `OCR_DEVICE` | `mps`/`cpu` auto | Force inference device |
| `OCR_MAX_LONG_EDGE` | 1280 | Image resize cap before OCR |
| `OCR_PDF_DPI` | 200 | PDF page render quality |
| `OCR_MAX_FILES` | 10 | Maximum files per request |

---

## 6. Installation and Deployment

See `SETUP.md` for the full step-by-step guide. The condensed version:

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

The first run downloads the 2.5 GB model from Hugging Face; subsequent
runs use the local cache and require no network access.

---

## 7. User Guide

### 7.1 Web interface

1. Run `python webapp.py` and wait for `[startup] model ready`.
2. Open http://localhost:8000 in any modern browser.
3. Drag image or PDF files into the drop zone (up to 10 at once).
4. (Optional) Adjust the prompt — `Text Recognition:` (default),
   `Formula Recognition:`, or `Chart Recognition:`.
5. Click **Run OCR**. Results appear as labelled text blocks below.
6. **Reset** clears the queue without reloading the page.

### 7.2 Terminal interface

```bash
python run_ocr.py path/to/image.png
```

Prints the recognised text to stdout. Suitable for shell scripting:

```bash
for f in scans/*.png; do
    python run_ocr.py "$f" > "out/$(basename "$f" .png).txt"
done
```

---

## 8. Testing and Validation

### 8.1 Methodology

A benchmark suite (`tests/benchmark/run_benchmark.py`) runs the OCR
across eight representative documents covering the main real-world
categories:

| # | Category | Source file |
|---|---|---|
| 1 | Code screenshot | `examples/source/code.png` |
| 2 | Scientific paper | `examples/source/paper.png` |
| 3 | Standard document | `examples/source/page.png` |
| 4 | Table / spreadsheet | `examples/source/table.png` |
| 5 | Handwritten note | `examples/source/handwritten.png` |
| 6 | Stamp / seal | `examples/source/seal.png` |
| 7 | PDF page 1 | `examples/source/GLM-4.5V.pdf` |
| 8 | PDF page 2 | `examples/source/GLM-4.5V.pdf` |

The benchmark measures load time, per-image OCR time, output length, and
records the full OCR text for manual inspection.

### 8.2 Results (run 2026-05-21 on Apple Silicon)

| # | Test | Image size | Time | Output chars | Status |
|---|---|---|---|---|---|
| 1 | Code screenshot | 540×666 | 19.8 s | 1887 | Pass |
| 2 | Scientific paper | 1700×2200 | 100.6 s | 4750 | Pass |
| 3 | Document page | 843×596 | 61.2 s | 1147 | Pass |
| 4 | Table | 1080×1080 | 22.0 s | 402 | Pass |
| 5 | Handwritten | 1920×1653 | 24.8 s | 361 | Pass |
| 6 | Seal / stamp | 399×314 | 2.2 s | 56 | Pass |
| 7 | PDF page 1 of 11 | 1700×2200 | 39.8 s | 2011 | Pass |
| 8 | PDF page 2 of 11 | 1700×2200 | 88.9 s | 4883 | Pass |
|   | **Total** |  | **359.1 s** | **15,497** | **8/8 pass** |

Full per-test outputs are available in `tests/benchmark/OCR_REPORT.md`
and `tests/benchmark/OCR_REPORT.pdf`.

### 8.3 Reproducibility

To re-run the benchmark on any machine:

```bash
python tests/benchmark/run_benchmark.py
python tests/benchmark/md_to_pdf.py
```

This regenerates both the Markdown and PDF reports. Numbers will vary
based on hardware (the test rig is a 16 GB M-series Mac).

---

## 9. Limitations and Known Issues

Honest assessment of where this system is currently weak:

### 9.1 Language coverage

GLM-OCR was trained predominantly on **Chinese and English**. Testing
confirmed strong accuracy on those scripts plus Latin-script European
languages. **Indic scripts (Hindi, Tamil, Telugu, Bengali, etc.) are not
reliably supported** — outputs are often blank, hallucinated, or
transliterated.

**Recommendation:** for Indian-language workloads, evaluate Tesseract,
PaddleOCR, or a multilingual VLM (Qwen2-VL, InternVL) as an additional
engine.

### 9.2 Performance

- Average 45 s per image is acceptable for batch and ad-hoc use but
  unsuitable for real-time per-keystroke applications.
- A 10-page PDF currently runs serially (~5–10 minutes total). Parallel
  inference would require a second GPU or distillation to a smaller
  model.

### 9.3 Operational considerations

- **No authentication.** The current webapp binds to `0.0.0.0:8000` and
  accepts uploads from anyone on the local network. Should be locked
  down to `127.0.0.1`, placed behind a reverse proxy, or have HTTP basic
  auth added before exposure beyond a single workstation.
- **No persistence.** OCR results live only in the browser tab — they
  are not stored on disk. A future version could add a SQLite log.
- **No file-size cap.** Very large PDFs could exhaust GPU memory.

### 9.4 Hardware dependency

Requires either Apple Silicon (MPS) or a CUDA-capable NVIDIA GPU for
reasonable speed. CPU-only operation works but is roughly 5–10 × slower.

---

## 10. Future Enhancements

Prioritised list of improvements that would extend the system:

1. **Multi-engine fallback** — add PaddleOCR or Tesseract behind a
   dropdown so Indian languages are also covered.
2. **Result persistence** — log every OCR run to SQLite so results are
   recoverable and searchable.
3. **Authentication & rate limiting** — basic HTTP auth + a simple
   per-IP rate limit before any production deployment.
4. **Dockerfile** — package the entire stack so colleagues can `docker
   run` instead of installing Python locally.
5. **Streaming results** — push each page's result to the browser as
   soon as it finishes instead of waiting for the full batch.
6. **REST + Swagger docs** — expose the `/ocr` endpoint with OpenAPI
   documentation for integration into other internal systems.

---

## 11. Project Deliverables

| Deliverable | Location | Format |
|---|---|---|
| Source code | https://github.com/venkatesbonthala2932/GLM-OCR | Git repository |
| Installation guide | `SETUP.md` | Markdown |
| This report | `docs/PROJECT_REPORT.md` (+ `.pdf`) | Markdown / PDF |
| Demo guide | `docs/DEMO_GUIDE.md` (+ `.pdf`) | Markdown / PDF |
| Pre-demo checklist | `docs/PRE_DEMO_CHECKLIST.md` | Markdown |
| Benchmark report | `tests/benchmark/OCR_REPORT.md` (+ `.pdf`) | Markdown / PDF |
| Working web app | `webapp.py` (runs on `localhost:8000`) | Python |
| CLI tool | `run_ocr.py` | Python |
| Benchmark suite | `tests/benchmark/run_benchmark.py` | Python |

---

## 12. Conclusion

The deployment meets the original requirements: a local, offline,
zero-cost OCR system with both a command-line and browser interface,
verified end-to-end across eight document types. The codebase is
organised, version-controlled on GitHub, documented for new users, and
ready for hand-off.

The clearest next step — and the largest current limitation — is
multilingual coverage for Indian scripts, which would require pairing
GLM-OCR with a second engine.

---

## Appendix A — Test environment

| Component | Value |
|---|---|
| Operating system | macOS Darwin 25.4.0 |
| CPU / GPU | Apple Silicon, MPS GPU |
| Python | 3.14.4 |
| PyTorch | 2.12.0 |
| transformers | 5.8.1 |
| FastAPI | 0.136.1 |
| uvicorn | 0.47.0 |
| Pillow | 12.2.0 |
| PyMuPDF | 1.27.2.3 |
| GLM-OCR model | `zai-org/GLM-OCR` v0.1 |
| Model cache | `~/.cache/huggingface/hub/` (2.5 GB) |

## Appendix B — Repository file tree (top level)

```
GLM-OCR/
├── webapp.py                  ← upload website
├── run_ocr.py                 ← CLI OCR
├── make_receipt.py            ← test image helper
├── requirements-webapp.txt    ← webapp dependencies
├── SETUP.md                   ← user install guide
├── docs/
│   ├── PROJECT_REPORT.md      ← this document
│   ├── PROJECT_REPORT.pdf
│   ├── DEMO_GUIDE.md          ← live demo script + Q&A
│   ├── DEMO_GUIDE.pdf
│   └── PRE_DEMO_CHECKLIST.md
├── tests/benchmark/
│   ├── run_benchmark.py
│   ├── OCR_REPORT.md
│   ├── OCR_REPORT.pdf
│   └── md_to_pdf.py
├── glmocr/                    ← upstream SDK (CORS edit in server.py)
└── examples/source/           ← sample images + PDF used by benchmark
```

## Appendix C — Tools and methodology

The implementation work was carried out using **Claude Code** (Anthropic's
AI coding assistant) inside Visual Studio Code, with the engineer
directing the work, making design decisions, and verifying each change
end-to-end. AI assistance accelerated the writing of boilerplate (FastAPI
endpoints, HTML/JS, benchmark scaffolding, documentation) while the
engineer retained full ownership of:

- the system requirements and acceptance criteria,
- design choices (single-file webapp, one OCR call per PDF page, etc.),
- testing and verification on the target hardware,
- the limitations assessment (notably the Indian-language gap),
- the GitHub repository and its history.

This collaboration model is consistent with current industry practice
for AI-assisted software development. All code is reviewed and
understood by the engineer; no functionality was committed without
manual verification.

## Appendix D — Acknowledgements

- **Zhipu AI** for releasing GLM-OCR under Apache 2.0.
- The original repository at https://github.com/zai-org/GLM-OCR is
  preserved as the `upstream` remote in this fork.

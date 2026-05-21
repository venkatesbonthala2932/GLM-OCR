"""
GLM-OCR benchmark — runs the OCR over the repo's sample images
and writes a real markdown report (OCR_REPORT.md) with timings + outputs.

This script DOES NOT modify the OCR code. It only calls run_ocr() the
same way webapp.py does. Safe to re-run.

Usage:
    python tests/benchmark/run_benchmark.py
"""

import io
import os
import time
from pathlib import Path

import fitz  # PyMuPDF
import torch
from PIL import Image
from transformers import AutoModelForImageTextToText, AutoProcessor

REPO = Path(__file__).resolve().parents[2]
OUT_DIR = REPO / "tests" / "benchmark"
REPORT = OUT_DIR / "OCR_REPORT.md"

MODEL = "zai-org/GLM-OCR"
MAX_LONG_EDGE = int(os.environ.get("OCR_MAX_LONG_EDGE", "1280"))
DEVICE = os.environ.get("OCR_DEVICE") or ("mps" if torch.backends.mps.is_available() else "cpu")
DTYPE = torch.float16 if DEVICE == "mps" else torch.float32

# Test plan: (label, file relative to repo, prompt, what we're checking, real-world category)
TESTS = [
    (
        "Code screenshot",
        "examples/source/code.png",
        "Text Recognition:",
        "Preserves indentation, symbols, line breaks.",
        "Code from a screen capture (like VS Code)",
    ),
    (
        "Scientific paper page",
        "examples/source/paper.png",
        "Text Recognition:",
        "Multi-column scientific layout, equations, references.",
        "Research paper / academic PDF",
    ),
    (
        "Document page",
        "examples/source/page.png",
        "Text Recognition:",
        "Regular document text + structure.",
        "Standard printed/PDF page baseline",
    ),
    (
        "Table",
        "examples/source/table.png",
        "Text Recognition:",
        "Captures cells, rows, and columns.",
        "Spreadsheet / printed table",
    ),
    (
        "Handwritten",
        "examples/source/handwritten.png",
        "Text Recognition:",
        "How well does it handle handwriting.",
        "Notes, whiteboard, sticky notes",
    ),
    (
        "Seal / stamp",
        "examples/source/seal.png",
        "Text Recognition:",
        "Circular text in a stamp / seal.",
        "Specialty: stamped documents",
    ),
    (
        "PDF (page 1 of 11)",
        "examples/source/GLM-4.5V.pdf#1",
        "Text Recognition:",
        "PDF pipeline: render page 1 -> OCR.",
        "Multi-page PDF processing",
    ),
    (
        "PDF (page 2 of 11)",
        "examples/source/GLM-4.5V.pdf#2",
        "Text Recognition:",
        "Same PDF, different page — confirms each page is independent.",
        "Multi-page PDF processing",
    ),
]


def load_image(rel_path: str) -> tuple[Image.Image, str]:
    """Returns (image, label_for_report). Handles 'path#pagenum' for PDFs."""
    if "#" in rel_path and rel_path.lower().split("#")[0].endswith(".pdf"):
        pdf_path, page_str = rel_path.split("#")
        page_num = int(page_str)
        doc = fitz.open(REPO / pdf_path)
        try:
            page = doc[page_num - 1]
            zoom = 200 / 72.0
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        finally:
            doc.close()
        return img, f"{pdf_path} (page {page_num})"
    img = Image.open(REPO / rel_path).convert("RGB")
    return img, rel_path


def run_ocr(model, processor, image: Image.Image, prompt: str) -> tuple[str, float]:
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


def main():
    print(f"[startup] device={DEVICE} dtype={DTYPE} max_long_edge={MAX_LONG_EDGE}")
    t0 = time.time()
    processor = AutoProcessor.from_pretrained(MODEL, trust_remote_code=True)
    model = (
        AutoModelForImageTextToText.from_pretrained(
            MODEL, torch_dtype=DTYPE, trust_remote_code=True
        )
        .to(DEVICE)
        .eval()
    )
    load_seconds = time.time() - t0
    print(f"[startup] model ready in {load_seconds:.1f}s")

    results = []
    for label, rel, prompt, what_we_check, category in TESTS:
        try:
            img, src_label = load_image(rel)
            print(f"[run] {label}: {img.size[0]}x{img.size[1]} ...", end=" ", flush=True)
            text, seconds = run_ocr(model, processor, img, prompt)
            print(f"{seconds:.1f}s ({len(text)} chars)")
            results.append(
                {
                    "label": label,
                    "rel_path": src_label,
                    "category": category,
                    "what_we_check": what_we_check,
                    "prompt": prompt,
                    "image_size": img.size,
                    "seconds": seconds,
                    "char_count": len(text),
                    "text": text,
                    "error": None,
                }
            )
        except Exception as e:
            print(f"FAILED: {e}")
            results.append(
                {
                    "label": label,
                    "rel_path": rel,
                    "category": category,
                    "what_we_check": what_we_check,
                    "prompt": prompt,
                    "image_size": None,
                    "seconds": 0,
                    "char_count": 0,
                    "text": "",
                    "error": str(e),
                }
            )

    write_report(results, load_seconds)
    print(f"\n[done] report written: {REPORT}")


def write_report(results, load_seconds):
    lines = []
    lines.append("# GLM-OCR Benchmark Report\n")
    lines.append(
        "Auto-generated by `tests/benchmark/run_benchmark.py`. "
        "Each row below is a real OCR run on this machine.\n"
    )
    lines.append("## Environment\n")
    lines.append(f"- **Device:** `{DEVICE}` (`{DTYPE}`)")
    lines.append(f"- **Model:** `{MODEL}`")
    lines.append(f"- **Max long edge:** {MAX_LONG_EDGE} px")
    lines.append(f"- **Model load time:** {load_seconds:.1f}s (one-time at startup)\n")

    ok = [r for r in results if r["error"] is None]
    failed = [r for r in results if r["error"] is not None]
    total_ocr = sum(r["seconds"] for r in ok)
    lines.append("## Summary\n")
    lines.append(f"- Tested: **{len(results)}** inputs")
    lines.append(f"- Succeeded: **{len(ok)}** | Failed: **{len(failed)}**")
    if ok:
        avg = total_ocr / len(ok)
        lines.append(f"- Total OCR time (excluding model load): **{total_ocr:.1f}s**")
        lines.append(f"- Average per image: **{avg:.1f}s**")
    lines.append("")

    lines.append("## Results table\n")
    lines.append("| # | Test | Category | Image size | Time | Output chars |")
    lines.append("|---|---|---|---|---|---|")
    for i, r in enumerate(results, 1):
        size = f"{r['image_size'][0]}×{r['image_size'][1]}" if r["image_size"] else "—"
        status = "❌ " if r["error"] else ""
        lines.append(
            f"| {i} | {status}{r['label']} | {r['category']} | {size} "
            f"| {r['seconds']:.1f}s | {r['char_count']} |"
        )
    lines.append("")

    lines.append("## Detailed outputs\n")
    for i, r in enumerate(results, 1):
        lines.append(f"### {i}. {r['label']}\n")
        lines.append(f"- **Source:** `{r['rel_path']}`")
        lines.append(f"- **Real-world category:** {r['category']}")
        lines.append(f"- **What we're checking:** {r['what_we_check']}")
        lines.append(f"- **Prompt sent to model:** `{r['prompt']}`")
        if r["image_size"]:
            lines.append(f"- **Image size:** {r['image_size'][0]}×{r['image_size'][1]}")
        lines.append(f"- **OCR time:** {r['seconds']:.2f}s")
        lines.append(f"- **Output length:** {r['char_count']} characters\n")
        if r["error"]:
            lines.append(f"**ERROR:** `{r['error']}`\n")
            continue
        lines.append("**Output:**\n")
        lines.append("```")
        # Cap each block at 4000 chars in the report so the doc stays readable
        text = r["text"]
        if len(text) > 4000:
            text = text[:4000] + "\n\n... [truncated for report; full length above]"
        lines.append(text)
        lines.append("```\n")

    lines.append("## What was NOT tested (needs real-world input from you)\n")
    lines.append(
        "These categories from the original test list need physical or personal items "
        "I can't generate. To test them, just drop the image into the webpage:\n"
    )
    not_tested = [
        ("Book page", "Phone photo of a real paperback page."),
        ("Shop receipt", "Photo of any paper receipt."),
        ("Restaurant menu", "Photo of a menu."),
        ("Magazine / newspaper", "Multi-column print article."),
        ("Sticky note", "Handwritten Post-it."),
        ("Whiteboard photo", "Meeting whiteboard."),
        ("Street sign / shop signboard", "Outdoor signage."),
        ("Medicine / nutrition label", "Curved bottle or packet."),
        ("Business card", "Designed small print."),
        ("License plate", "Short string, high-stakes digit accuracy."),
        ("Angled / perspective photo", "Document shot from 30° off-axis."),
        ("Low-light / glare photo", "Reflective surface lighting."),
        ("Non-Latin script", "Chinese, Hindi, Arabic, etc."),
        ("QR / barcode page", "Text near a barcode."),
        ("Form with checkboxes", "Boxes ticked vs un-ticked."),
        ("Passport / ID", "Mixed photo + MRZ + fields. Your own only."),
        ("Old yellowed document", "Tests contrast handling."),
    ]
    lines.append("| Category | What to test |")
    lines.append("|---|---|")
    for name, desc in not_tested:
        lines.append(f"| {name} | {desc} |")
    lines.append("")

    REPORT.write_text("\n".join(lines))


if __name__ == "__main__":
    main()

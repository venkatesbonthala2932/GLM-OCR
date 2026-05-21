"""
Render OCR_REPORT.md to OCR_REPORT.pdf.

Pipeline:
    Markdown -> HTML (python-markdown) -> PDF (PyMuPDF Story + DocumentWriter).

PyMuPDF Story handles HTML + CSS + Unicode (incl. CJK with the right font).
We register a macOS system CJK font so Chinese sample outputs render
correctly without any external system libraries.

Usage:
    python tests/benchmark/md_to_pdf.py
"""

from pathlib import Path

import fitz  # PyMuPDF
import markdown

HERE = Path(__file__).resolve().parent
SRC = HERE / "OCR_REPORT.md"
DST = HERE / "OCR_REPORT.pdf"

# macOS bundled fonts good for Chinese characters.
CJK_FONT_CANDIDATES = [
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
]

CSS_TEXT = """
body { font-size: 10pt; line-height: 1.4; color: #222; }
h1 { font-size: 22pt; margin-bottom: 6pt; color: #036; }
h2 { font-size: 14pt; margin-top: 14pt; color: #036; }
h3 { font-size: 11pt; margin-top: 10pt; color: #048; }
p  { margin: 4pt 0; }
table { border-collapse: collapse; width: 100%; }
th, td { border: 1px solid #999; padding: 3pt 5pt; font-size: 9pt; text-align: left; }
th { background-color: #e8eef5; }
code { background-color: #f0f0f0; padding: 0 2pt; }
pre  { background-color: #f5f5f5; border: 1px solid #ddd;
       padding: 6pt; font-size: 8.5pt; white-space: pre-wrap; }
ul, ol { margin: 4pt 0 6pt 14pt; }
li { margin: 1pt 0; }
"""


def find_cjk_font() -> Path | None:
    for p in CJK_FONT_CANDIDATES:
        if Path(p).exists():
            return Path(p)
    return None


def main() -> None:
    if not SRC.exists():
        raise SystemExit(f"missing source: {SRC}")
    md_text = SRC.read_text()
    html_body = markdown.markdown(md_text, extensions=["tables", "fenced_code"])
    html_doc = (
        f"<html><head><style>{CSS_TEXT}</style></head>"
        f"<body>{html_body}</body></html>"
    )

    archive = fitz.Archive()
    user_css = ""
    cjk = find_cjk_font()
    if cjk:
        archive.add(str(cjk.parent), path=cjk.parent.name)
        user_css = (
            f"* {{ font-family: sans-serif, '{cjk.stem}'; }} "
            f"pre, code {{ font-family: monospace, '{cjk.stem}'; }}"
        )
        print(f"[font] using {cjk}")
    else:
        print("[font] no CJK font found — Chinese text may render as boxes")

    story = fitz.Story(html=html_doc, user_css=user_css, archive=archive)

    page_rect = fitz.paper_rect("a4")
    margin = 40
    where = fitz.Rect(margin, margin, page_rect.width - margin, page_rect.height - margin)

    writer = fitz.DocumentWriter(str(DST))
    more = 1
    pages = 0
    while more:
        device = writer.begin_page(page_rect)
        more, _ = story.place(where)
        story.draw(device, None)
        writer.end_page()
        pages += 1
    writer.close()

    size_kb = DST.stat().st_size // 1024
    print(f"wrote {DST} ({pages} pages, {size_kb} KB)")


if __name__ == "__main__":
    main()

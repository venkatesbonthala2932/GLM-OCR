"""
Render a Markdown file to PDF.

Defaults to tests/benchmark/OCR_REPORT.md -> OCR_REPORT.pdf for the
benchmark, but accepts any Markdown file as an argument.

Pipeline:
    Markdown -> HTML (python-markdown) -> PDF (PyMuPDF Story + DocumentWriter).

Handles Unicode incl. CJK via a registered macOS system font, so the
generated PDFs render cleanly across all sample languages.

Usage:
    python tests/benchmark/md_to_pdf.py                 # default report
    python tests/benchmark/md_to_pdf.py docs/REPORT.md  # any file
    python tests/benchmark/md_to_pdf.py in.md out.pdf   # custom output
"""

import sys
from pathlib import Path

import fitz  # PyMuPDF
import markdown

DEFAULT_SRC = (
    Path(__file__).resolve().parent / "OCR_REPORT.md"
)

CJK_FONT_CANDIDATES = [
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
]

CSS_TEXT = """
body { font-size: 10pt; line-height: 1.45; color: #1a1a1a; }
h1 { font-size: 22pt; color: #003366; margin-bottom: 8pt;
     border-bottom: 2px solid #003366; padding-bottom: 4pt; }
h2 { font-size: 15pt; color: #003366; margin-top: 18pt;
     border-bottom: 1px solid #999; padding-bottom: 2pt; }
h3 { font-size: 12pt; color: #044084; margin-top: 12pt; }
h4 { font-size: 10.5pt; color: #044084; margin-top: 8pt; }
p  { margin: 4pt 0; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0; }
th, td { border: 1px solid #888; padding: 3pt 6pt;
         font-size: 9pt; text-align: left; vertical-align: top; }
th { background-color: #e8eef5; font-weight: bold; }
code { background-color: #f0f0f0; padding: 0 2pt; font-size: 9pt; }
pre  { background-color: #f5f5f5; border: 1px solid #ddd;
       padding: 6pt; font-size: 8.5pt; white-space: pre-wrap; }
ul, ol { margin: 4pt 0 6pt 14pt; }
li { margin: 1pt 0; }
blockquote { border-left: 3px solid #999; padding-left: 8pt;
             margin: 6pt 0; color: #444; }
"""


def find_cjk_font():
    for p in CJK_FONT_CANDIDATES:
        if Path(p).exists():
            return Path(p)
    return None


def render(src: Path, dst: Path) -> None:
    if not src.exists():
        raise SystemExit(f"missing source: {src}")
    md_text = src.read_text()
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

    story = fitz.Story(html=html_doc, user_css=user_css, archive=archive)
    page_rect = fitz.paper_rect("a4")
    margin = 40
    where = fitz.Rect(margin, margin, page_rect.width - margin, page_rect.height - margin)

    writer = fitz.DocumentWriter(str(dst))
    more = 1
    pages = 0
    while more:
        device = writer.begin_page(page_rect)
        more, _ = story.place(where)
        story.draw(device, None)
        writer.end_page()
        pages += 1
    writer.close()
    print(f"wrote {dst} ({pages} pages, {dst.stat().st_size // 1024} KB)")


def main(argv: list[str]) -> None:
    if len(argv) == 1:
        src = DEFAULT_SRC
        dst = src.with_suffix(".pdf")
    elif len(argv) == 2:
        src = Path(argv[1]).resolve()
        dst = src.with_suffix(".pdf")
    elif len(argv) == 3:
        src = Path(argv[1]).resolve()
        dst = Path(argv[2]).resolve()
    else:
        raise SystemExit("usage: md_to_pdf.py [SOURCE.md] [OUTPUT.pdf]")
    render(src, dst)


if __name__ == "__main__":
    main(sys.argv)

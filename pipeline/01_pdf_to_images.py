"""
01_pdf_to_images.py

Converts each page of a gamebook PDF into a PNG image.
These images are what we'll feed to Claude Vision in the next step.

Supports two layouts (set in parse_config.json):
  split_pages: false (default) — one PNG per PDF page (single-page scans)
  split_pages: true            — two PNGs per PDF page (two-page book spreads)
    Left half  → page-001.png, page-003.png, ...
    Right half → page-002.png, page-004.png, ...

Output: books/<book-id>/pages/page-NNN.png
"""

import fitz  # pymupdf
import json
import sys
from pathlib import Path


def load_config(book_id: str, root: Path) -> dict:
    config_path = root / "books" / book_id / "parse_config.json"
    if config_path.exists():
        return json.loads(config_path.read_text(encoding="utf-8"))
    return {}


def pdf_to_images(book_id: str, dpi: int = 200):
    root = Path(__file__).parent.parent
    config = load_config(book_id, root)

    # PDF filename: default to <book-id>.pdf, override via parse_config
    pdf_name = config.get("pdf_filename", f"{book_id}.pdf")
    pdf_path = root / "books" / book_id / pdf_name
    output_dir = root / "books" / book_id / "pages"

    if not pdf_path.exists():
        print(f"ERROR: PDF not found at {pdf_path}")
        sys.exit(1)

    split = config.get("split_pages", False)
    output_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    total_pdf = len(doc)
    total_out = total_pdf * 2 if split else total_pdf
    mode = "split (2 halves per PDF page)" if split else "single"
    print(f"PDF: {pdf_name}  |  {total_pdf} pages  |  mode: {mode}  |  DPI: {dpi}")
    print(f"Output: {total_out} images -> {output_dir}\n")

    scale = dpi / 72
    matrix = fitz.Matrix(scale, scale)
    out_idx = 1  # running output page counter

    for i, page in enumerate(doc):
        if not split:
            out_path = output_dir / f"page-{out_idx:03d}.png"
            if not out_path.exists():
                pix = page.get_pixmap(matrix=matrix)
                pix.save(str(out_path))
                print(f"  [{out_idx}/{total_out}] {out_path.name}")
            else:
                print(f"  [{out_idx}/{total_out}] {out_path.name} already exists, skipping")
            out_idx += 1
        else:
            # Split at horizontal midpoint using PDF-coordinate clip rects.
            # get_pixmap(clip=...) accepts a Rect in page units (points, 72dpi).
            w = page.rect.width
            mid = w / 2
            h = page.rect.height

            for side, x0, x1 in [("L", 0, mid), ("R", mid, w)]:
                out_path = output_dir / f"page-{out_idx:03d}.png"
                if not out_path.exists():
                    clip = fitz.Rect(x0, 0, x1, h)
                    pix = page.get_pixmap(matrix=matrix, clip=clip)
                    pix.save(str(out_path))
                    print(f"  [{out_idx}/{total_out}] {out_path.name}  (PDF page {i+1} {side})")
                else:
                    print(f"  [{out_idx}/{total_out}] {out_path.name} already exists, skipping")
                out_idx += 1

    doc.close()
    print(f"\nDone. {out_idx - 1} images saved to {output_dir}")


if __name__ == "__main__":
    book_id = sys.argv[1] if len(sys.argv) > 1 else "magusok-tornya"
    pdf_to_images(book_id)

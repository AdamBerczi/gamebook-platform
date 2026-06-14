"""
01_pdf_to_images.py

Converts each page of a gamebook PDF into a PNG image.
These images are what we'll feed to Claude Vision in the next step.

Why pymupdf (fitz)?
  - Self-contained: no external tools like poppler needed
  - Fast and accurate rendering
  - Handles older scanned PDFs well

Output: books/<book-id>/pages/page-001.png, page-002.png, ...
"""

import fitz  # pymupdf
import sys
from pathlib import Path


def pdf_to_images(pdf_path: Path, output_dir: Path, dpi: int = 200):
    """
    Render each PDF page as a PNG at the given DPI.

    DPI 200 is a sweet spot: high enough for Claude to read text clearly,
    low enough that files stay small and API calls stay fast.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    total = len(doc)
    print(f"PDF has {total} pages. Rendering at {dpi} DPI...")

    # fitz uses a matrix to scale the rendering.
    # 72 DPI is PDF's native unit, so we scale by dpi/72.
    scale = dpi / 72
    matrix = fitz.Matrix(scale, scale)

    for i, page in enumerate(doc):
        # Zero-padded filename so files sort correctly (page-001, page-002, ...)
        out_path = output_dir / f"page-{i+1:03d}.png"

        if out_path.exists():
            print(f"  [{i+1}/{total}] {out_path.name} already exists, skipping")
            continue

        pixmap = page.get_pixmap(matrix=matrix)
        pixmap.save(str(out_path))
        print(f"  [{i+1}/{total}] Saved {out_path.name}")

    doc.close()
    print(f"\nDone. {total} images saved to {output_dir}")


if __name__ == "__main__":
    # Default to Mágusok Tornya; pass a different book ID as argument to reuse
    book_id = sys.argv[1] if len(sys.argv) > 1 else "magusok-tornya"

    root = Path(__file__).parent.parent  # gamebook-platform/
    pdf_path = root / "books" / book_id / f"{book_id}.pdf"
    output_dir = root / "books" / book_id / "pages"

    if not pdf_path.exists():
        print(f"ERROR: PDF not found at {pdf_path}")
        sys.exit(1)

    pdf_to_images(pdf_path, output_dir)

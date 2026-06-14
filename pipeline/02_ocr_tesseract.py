"""
02_ocr_tesseract.py

OCR all page images using Tesseract (free, no API tokens).
Drop-in replacement for 02_ocr_pages.py (Claude Vision).

Setup (one-time):
  1. Install Tesseract via winget:
       winget install UB-Mannheim.TesseractOCR
  2. Download the Hungarian model to ~/tessdata/:
       Invoke-WebRequest https://github.com/tesseract-ocr/tessdata_best/raw/main/hun.traineddata
                         -OutFile "$env:USERPROFILE\\tessdata\\hun.traineddata"
  3. pip install pytesseract pillow

Output: books/<book-id>/raw-text/page-001.txt, page-002.txt, ...

Usage:
  python 02_ocr_tesseract.py                  # processes magusok-tornya
  python 02_ocr_tesseract.py a-demon-szeme
"""

import sys
import os
import time
from pathlib import Path

import pytesseract
from PIL import Image

# ── Tesseract path ──────────────────────────────────────────────────────────
TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
TESSDATA_DIR  = str(Path.home() / "tessdata")

# Language: Hungarian + English fallback for numbers/latin words
LANG = "hun+eng"

# Tesseract page-segmentation mode 1: automatic page segmentation with OSD.
# Mode 3 (fully automatic) also works well for single-column book pages.
PSM = 3

# DPI hint — matches the 200 DPI we render at in 01_pdf_to_images.py
DPI = 200


def setup_tesseract():
    if not Path(TESSERACT_CMD).exists():
        print(f"ERROR: Tesseract not found at {TESSERACT_CMD}")
        print("Install with: winget install UB-Mannheim.TesseractOCR")
        sys.exit(1)
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
    os.environ["TESSDATA_PREFIX"] = TESSDATA_DIR

    # Verify Hungarian model is available
    langs = pytesseract.get_languages(config="")
    if "hun" not in langs:
        print(f"ERROR: Hungarian language model not found in {TESSDATA_DIR}")
        print("Download: Invoke-WebRequest https://github.com/tesseract-ocr/tessdata_best/raw/main/hun.traineddata -OutFile $env:USERPROFILE\\tessdata\\hun.traineddata")
        sys.exit(1)


def ocr_page(image_path: Path) -> str:
    img = Image.open(image_path)
    config = f"--psm {PSM} --dpi {DPI}"
    text = pytesseract.image_to_string(img, lang=LANG, config=config)
    return text.strip()


def ocr_all_pages(book_id: str):
    setup_tesseract()

    root       = Path(__file__).parent.parent
    pages_dir  = root / "books" / book_id / "pages"
    output_dir = root / "books" / book_id / "raw-text"
    output_dir.mkdir(parents=True, exist_ok=True)

    page_images = sorted(pages_dir.glob("page-*.png"))
    if not page_images:
        print(f"ERROR: No page images found in {pages_dir}")
        print("Run 01_pdf_to_images.py first.")
        sys.exit(1)

    total = len(page_images)
    print(f"Found {total} pages. Starting OCR with Tesseract ({LANG})...")
    print(f"tessdata: {TESSDATA_DIR}")
    print("(Already-processed pages will be skipped)\n")

    t0 = time.time()
    for i, img_path in enumerate(page_images):
        out_path = output_dir / img_path.with_suffix(".txt").name

        if out_path.exists():
            print(f"  [{i+1:3d}/{total}] {img_path.name} already done, skipping")
            continue

        t1 = time.time()
        text = ocr_page(img_path)
        elapsed = time.time() - t1

        out_path.write_text(text, encoding="utf-8")
        print(f"  [{i+1:3d}/{total}] {img_path.name}  {len(text):5d} chars  ({elapsed:.1f}s)")

    total_time = time.time() - t0
    print(f"\nDone in {total_time:.0f}s. Text files saved to {output_dir}")


if __name__ == "__main__":
    book_id = sys.argv[1] if len(sys.argv) > 1 else "magusok-tornya"
    ocr_all_pages(book_id)

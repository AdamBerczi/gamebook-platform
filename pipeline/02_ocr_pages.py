"""
02_ocr_pages.py

Sends each page image to Claude Vision and saves the extracted text.

Why Claude Vision instead of Tesseract?
  - Hungarian diacritics (á, é, ő, ű, etc.) are handled correctly
  - Better at interpreting scanned book layouts (columns, headers, section numbers)
  - ~$0.20 for the whole book vs. hours of manual error correction

Output: books/<book-id>/raw-text/page-001.txt, page-002.txt, ...

Usage:
  python 02_ocr_pages.py                    # processes magusok-tornya
  python 02_ocr_pages.py magusok-tornya     # same, explicit
  ANTHROPIC_API_KEY=sk-... python 02_ocr_pages.py
"""

import anthropic
import base64
import sys
import time
from pathlib import Path


# The prompt tells Claude exactly what we want: raw text, preserve structure,
# don't interpret or summarize — just transcribe faithfully.
OCR_PROMPT = """Transcribe all text from this gamebook page image exactly as it appears.

Rules:
- Preserve section numbers (e.g. "42.", "117.") on their own line
- Preserve paragraph breaks
- Keep Hungarian characters (á, é, í, ó, ö, ő, ü, ű) correct
- Do NOT add commentary, summaries, or formatting like markdown
- If a word is unclear, transcribe your best guess — do not skip it
- Include everything: headers, footnotes, page numbers, all body text

Output only the transcribed text, nothing else."""


def ocr_page(client: anthropic.Anthropic, image_path: Path) -> str:
    """Send one page image to Claude and return the transcribed text."""
    with open(image_path, "rb") as f:
        image_data = base64.standard_b64encode(f.read()).decode("utf-8")

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",  # Fast and cheap; plenty capable for OCR
        max_tokens=4096,                    # A full page of text fits well within this
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": image_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": OCR_PROMPT,
                    },
                ],
            }
        ],
    )

    return message.content[0].text


def ocr_all_pages(book_id: str):
    root = Path(__file__).parent.parent
    pages_dir = root / "books" / book_id / "pages"
    output_dir = root / "books" / book_id / "raw-text"
    output_dir.mkdir(parents=True, exist_ok=True)

    page_images = sorted(pages_dir.glob("page-*.png"))
    if not page_images:
        print(f"ERROR: No page images found in {pages_dir}")
        print("Run 01_pdf_to_images.py first.")
        sys.exit(1)

    client = anthropic.Anthropic()  # Reads ANTHROPIC_API_KEY from environment
    total = len(page_images)
    print(f"Found {total} pages. Starting OCR with Claude Vision...")
    print("(Already-processed pages will be skipped)\n")

    for i, img_path in enumerate(page_images):
        out_path = output_dir / img_path.with_suffix(".txt").name

        if out_path.exists():
            print(f"  [{i+1}/{total}] {img_path.name} already done, skipping")
            continue

        print(f"  [{i+1}/{total}] Processing {img_path.name}...", end=" ", flush=True)
        text = ocr_page(client, img_path)
        out_path.write_text(text, encoding="utf-8")
        print(f"OK ({len(text)} chars)")

        # Small pause to stay well within API rate limits
        if i < total - 1:
            time.sleep(0.5)

    print(f"\nDone. Text files saved to {output_dir}")


if __name__ == "__main__":
    book_id = sys.argv[1] if len(sys.argv) > 1 else "magusok-tornya"
    ocr_all_pages(book_id)

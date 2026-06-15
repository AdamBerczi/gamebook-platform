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
OCR_PROMPT_DEFAULT = """Transcribe all text from this gamebook page image exactly as it appears.

Rules:
- Preserve section numbers (e.g. "42.", "117.") on their own line
- Preserve paragraph breaks
- Keep Hungarian characters (á, é, í, ó, ö, ő, ü, ű) correct
- Do NOT add commentary, summaries, or formatting like markdown
- If a word is unclear, transcribe your best guess — do not skip it
- Include everything: headers, footnotes, page numbers, all body text

Output only the transcribed text, nothing else."""

OCR_PROMPT_TWO_COLUMN = """Transcribe all text from this gamebook page image exactly as it appears.

IMPORTANT — TWO-COLUMN LAYOUT:
Many pages have two side-by-side columns of text. When you see two columns:
1. Transcribe the ENTIRE LEFT column from top to bottom first
2. Then transcribe the ENTIRE RIGHT column from top to bottom
Do NOT read across both columns row by row.

Rules:
- Each section number (e.g. "42.", "117.") must appear on its own line
- A section number is a 1-3 digit number followed by a period, e.g. "5.", "42.", "300."
- Preserve paragraph breaks within each section
- Keep Hungarian characters (á, é, í, ó, ö, ő, ü, ű) correct
- Do NOT add commentary, summaries, or formatting like markdown
- If a word is unclear, transcribe your best guess — do not skip it
- Include all navigation choices like "lapozz a 42-re!" exactly as written

Output only the transcribed text, nothing else."""


def load_prompt(book_id: str, root: Path) -> str:
    """Return the OCR prompt — book-specific if parse_config.json defines one."""
    config_path = root / "books" / book_id / "parse_config.json"
    if config_path.exists():
        import json
        config = json.loads(config_path.read_text(encoding="utf-8"))
        key = config.get("ocr_prompt")
        if key == "two_column":
            return OCR_PROMPT_TWO_COLUMN
    return OCR_PROMPT_DEFAULT


def ocr_page(client: anthropic.Anthropic, image_path: Path, prompt: str) -> str:
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
                        "text": prompt,
                    },
                ],
            }
        ],
    )

    return message.content[0].text


def ocr_all_pages(book_id: str, force: bool = False):
    root = Path(__file__).parent.parent
    pages_dir = root / "books" / book_id / "pages"
    output_dir = root / "books" / book_id / "raw-text"
    output_dir.mkdir(parents=True, exist_ok=True)

    page_images = sorted(pages_dir.glob("page-*.png"))
    if not page_images:
        print(f"ERROR: No page images found in {pages_dir}")
        print("Run 01_pdf_to_images.py first.")
        sys.exit(1)

    prompt = load_prompt(book_id, root)
    prompt_label = "two-column" if prompt == OCR_PROMPT_TWO_COLUMN else "default"

    client = anthropic.Anthropic()  # Reads ANTHROPIC_API_KEY from environment
    total = len(page_images)
    print(f"Found {total} pages. OCR prompt: {prompt_label}. Force: {force}")
    print("(Already-processed pages will be skipped unless --force)\n")

    for i, img_path in enumerate(page_images):
        out_path = output_dir / img_path.with_suffix(".txt").name

        if out_path.exists() and not force:
            print(f"  [{i+1}/{total}] {img_path.name} already done, skipping")
            continue

        print(f"  [{i+1}/{total}] Processing {img_path.name}...", end=" ", flush=True)
        text = ocr_page(client, img_path, prompt)
        out_path.write_text(text, encoding="utf-8")
        print(f"OK ({len(text)} chars)")

        # Small pause to stay well within API rate limits
        if i < total - 1:
            time.sleep(0.5)

    print(f"\nDone. Text files saved to {output_dir}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("book_id", nargs="?", default="magusok-tornya")
    parser.add_argument("--force", action="store_true",
                        help="Re-process pages that already have output files")
    args = parser.parse_args()
    ocr_all_pages(args.book_id, force=args.force)

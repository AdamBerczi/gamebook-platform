"""
04_clean_text.py

Sends each raw OCR text file through Claude to fix Hungarian OCR errors.

Why a separate cleanup step rather than fixing in the OCR prompt?
  - We already have 94 pages of raw text; no need to re-send images
  - Cleanup is cheaper (text-only, no vision) and faster
  - Keeping raw-text/ untouched means we can re-clean with a better prompt later

Input:  books/<book-id>/raw-text/page-NNN.txt
Output: books/<book-id>/cleaned-text/page-NNN.txt

Usage:
  python 04_clean_text.py                  # processes magusok-tornya
  python 04_clean_text.py magusok-tornya
"""

import anthropic
import sys
import time
from pathlib import Path


CLEAN_PROMPT = """You are correcting OCR errors in a page from a Hungarian gamebook (Fighting Fantasy / Harcos Képzelet series).

Fix all OCR transcription errors in the text below. Rules:
- Correct garbled, doubled, or missing letters caused by imperfect scanning
- Fix Hungarian diacritics where clearly wrong (á é í ó ö ő ü ű)
- Keep ALL proper nouns exactly as they appear (character names, place names)
- Keep ALL section numbers exactly as they are (e.g. "42.", "117.")
- Keep ALL navigation phrases exactly: "lapozz a X-re", "lapozz a X-ra", etc.
- Keep ALL game stat phrases exactly: "életerő", "támadási képesség", "védettségi szint", "szerencse", "varázserő"
- Keep ALL spell names exactly as they appear
- Do NOT rewrite, summarize, or change the story — only fix transcription errors
- Do NOT add or remove paragraphs
- Output ONLY the corrected text, nothing else

Text to correct:
"""


def clean_page(client: anthropic.Anthropic, raw_text: str) -> str:
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": CLEAN_PROMPT + raw_text
        }]
    )
    return message.content[0].text


def clean_all_pages(book_id: str):
    root = Path(__file__).parent.parent
    raw_dir     = root / "books" / book_id / "raw-text"
    cleaned_dir = root / "books" / book_id / "cleaned-text"
    cleaned_dir.mkdir(parents=True, exist_ok=True)

    pages = sorted(raw_dir.glob("page-*.txt"))
    if not pages:
        print(f"ERROR: No raw text files in {raw_dir}. Run 02_ocr_pages.py first.")
        sys.exit(1)

    client = anthropic.Anthropic()
    total = len(pages)
    print(f"Cleaning {total} pages with Claude...\n")

    for i, page_path in enumerate(pages):
        out_path = cleaned_dir / page_path.name

        if out_path.exists():
            print(f"  [{i+1}/{total}] {page_path.name} already cleaned, skipping")
            continue

        raw_text = page_path.read_text(encoding="utf-8")
        print(f"  [{i+1}/{total}] Cleaning {page_path.name}...", end=" ", flush=True)

        cleaned = clean_page(client, raw_text)
        out_path.write_text(cleaned, encoding="utf-8")
        print(f"OK")

        if i < total - 1:
            time.sleep(0.3)

    print(f"\nDone. Cleaned text saved to {cleaned_dir}")
    print("Now run: python 03_parse_sections.py")


if __name__ == "__main__":
    book_id = sys.argv[1] if len(sys.argv) > 1 else "magusok-tornya"
    clean_all_pages(book_id)

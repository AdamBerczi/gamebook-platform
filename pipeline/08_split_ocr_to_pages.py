"""
Pipeline step 08: Split a combined OCR text file into per-page raw-text files.

Usage (run from a fresh terminal, not from Claude Code):
    python pipeline/08_split_ocr_to_pages.py [book-id]

The input file is the combined OCR text at:
    D:\\Code\\OCR\\23 - A démon szeme.txt   (for a-demon-szeme)

Pages are separated by "--- PAGE N ---" markers.
Output goes to books/<book-id>/raw-text/page-NNN.txt, replacing the old files.

After running this script, run 03_parse_sections.py to rebuild sections.json:
    python pipeline/03_parse_sections.py a-demon-szeme
"""

import re
import sys
from pathlib import Path

# Adjust this path if the source file is elsewhere
OCR_SOURCES = {
    "a-demon-szeme": Path(r"D:\Code\OCR\23 - A démon szeme.txt"),
}

def split_and_save(book_id: str):
    src = OCR_SOURCES.get(book_id)
    if src is None:
        print(f"No OCR source configured for '{book_id}'.")
        print(f"Known books: {list(OCR_SOURCES.keys())}")
        sys.exit(1)

    if not src.exists():
        print(f"Source file not found: {src}")
        sys.exit(1)

    out_dir = Path(__file__).parent.parent / "books" / book_id / "raw-text"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Reading: {src}")
    text = src.read_text(encoding="utf-8")

    # Split on page markers, keeping the marker as a separator
    # Pattern: "--- PAGE N ---" on its own line
    page_pattern = re.compile(r"^--- PAGE (\d+) ---\s*$", re.MULTILINE)
    matches = list(page_pattern.finditer(text))

    if not matches:
        print("ERROR: No '--- PAGE N ---' markers found in file.")
        sys.exit(1)

    print(f"Found {len(matches)} pages in source file.")

    pages = {}
    for i, m in enumerate(matches):
        page_num = int(m.group(1))
        content_start = m.end()
        content_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        page_text = text[content_start:content_end].strip()
        pages[page_num] = page_text

    written = 0
    for page_num, page_text in sorted(pages.items()):
        out_path = out_dir / f"page-{page_num:03d}.txt"
        out_path.write_text(page_text, encoding="utf-8")
        written += 1

    print(f"Written {written} page files to: {out_dir}")
    print()
    print("Next steps:")
    print(f"  python pipeline/03_parse_sections.py {book_id}")
    print(f"  (rebuilds sections.json with correct section numbers, text, choices, enemies)")
    print()
    print("After that, re-run events extraction (uses Claude API — run from fresh terminal):")
    print(f"  python pipeline/07_extract_events.py {book_id}")


if __name__ == "__main__":
    book_id = sys.argv[1] if len(sys.argv) > 1 else "a-demon-szeme"
    split_and_save(book_id)

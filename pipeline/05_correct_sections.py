"""
05_correct_sections.py

Sends each section's text through Claude Sonnet for careful Hungarian
proofreading. Fixes OCR artifacts that slipped through the initial
cleanup pass (character substitutions, merged/split words, diacritics).

Preserves:
  - Proper nouns (Világcsavargó, Bairbas, Braildont-sziget, etc.)
  - Game stat terms (életerő, támadási képesség, védettségi szint, etc.)
  - Section numbers and navigation phrases (lapozz a X-re!)
  - Enemy stat blocks exactly as-is

Usage:
  python pipeline/05_correct_sections.py [book-id]

Reads:  books/<book-id>/sections.json
Writes: books/<book-id>/sections.json  (in-place, with backup)
"""

import json
import os
import sys
import time
import shutil
from pathlib import Path
import anthropic

BOOK_ID = sys.argv[1] if len(sys.argv) > 1 else "magusok-tornya"
ROOT    = Path(__file__).parent.parent
BOOK    = ROOT / "books" / BOOK_ID

SYSTEM = """Te egy gondos magyar korrektor vagy. Kaptál egy szöveget, amely egy szkennelt, OCR-rel feldolgozott kalandkönyvből származik.

Feladatod: javítsd ki az összes helyesírási és OCR-hibát (karakterfelcserélések, összevont/szétszakadt szavak, hiányzó ékezetek).

TARTSD MEG változatlanul:
- Tulajdonneveket (Világcsavargó, Bairbas, Braildont-sziget, Kék-tenger, Iylithes, stb.)
- Játékszabály-kifejezéseket (életerő, támadási képesség, védettségi szint, varázserő, szerencse)
- Szakaszszámokat és navigációs mondatokat (pl. "lapozz a 42-re!")
- Ellenség-statisztika blokkokat pontosan
- [Image ...] jelzéseket

Csak a javított szöveget add vissza, semmi mást."""

def correct_section(client, text: str) -> str:
    if not text or len(text) < 20:
        return text
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=SYSTEM,
        messages=[{"role": "user", "content": text}]
    )
    return resp.content[0].text.strip()

def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set. Run from a fresh terminal.")
        sys.exit(1)

    sections_path = BOOK / "sections.json"
    backup_path   = BOOK / "sections.json.bak"

    print(f"Loading {sections_path} ...")
    with open(sections_path, encoding="utf-8") as f:
        data = json.load(f)

    # Backup original
    shutil.copy(sections_path, backup_path)
    print(f"Backup saved to {backup_path}")

    client   = anthropic.Anthropic(api_key=api_key)
    sections = data["sections"]
    total    = len(sections)
    done     = 0

    print(f"Correcting {total} sections with claude-sonnet-4-6 ...")
    for sid, sec in sorted(sections.items(), key=lambda x: int(x[0])):
        original = sec.get("text", "")
        if not original:
            continue

        try:
            corrected = correct_section(client, original)
            sec["text"] = corrected
            done += 1
            if done % 10 == 0:
                print(f"  {done}/{total} done...")
                # Save progress periodically
                with open(sections_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"  ERROR on section {sid}: {e}")
            time.sleep(5)

        time.sleep(0.3)  # rate limit courtesy

    # Final save
    with open(sections_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\nDone. {done}/{total} sections corrected.")
    print(f"Original backed up at {backup_path}")

if __name__ == "__main__":
    main()

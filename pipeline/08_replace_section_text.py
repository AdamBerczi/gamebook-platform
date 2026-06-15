"""
Pipeline step 08: Replace garbled section text with clean OCR text.

Usage:
    python pipeline/08_replace_section_text.py [--dry-run] [--book-id a-demon-szeme]

Reads a new OCR text file, extracts section blocks, matches them to
existing sections.json by content similarity, and replaces the text field.

Sections that cannot be confidently matched are skipped and reported.
"""

import re
import json
import unicodedata
import argparse
from pathlib import Path
from difflib import SequenceMatcher

# ── Config ─────────────────────────────────────────────────────────────────
BOOK_ID = "a-demon-szeme"
OCR_FILE = Path(r"D:\Code\OCR\23 - A démon szeme.txt")
BOOK_DIR = Path(__file__).parent.parent / "books" / BOOK_ID
SECTIONS_FILE = BOOK_DIR / "sections.json"

# Similarity threshold: if best-match sim < this, skip and report
MATCH_THRESHOLD = 0.30
# If labeled number matches content AND sim > this, trust the label
TRUST_THRESHOLD = 0.45


# ── Helpers ────────────────────────────────────────────────────────────────

def strip_diacritics(s):
    """Remove diacritics for fuzzy matching (Hungarian ő → o, etc.)."""
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )

def normalize(text):
    """Lowercase, strip diacritics, collapse whitespace for comparison."""
    t = strip_diacritics(text.lower())
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"[^a-z0-9 ]", "", t)
    return t.strip()

def similarity(a, b):
    """Rough token-overlap similarity (fast, good enough for matching)."""
    na, nb = normalize(a), normalize(b)
    if not na or not nb:
        return 0.0
    # Use first 400 chars for speed; sections share opening sentences
    return SequenceMatcher(None, na[:400], nb[:400]).ratio()


# ── Step 1: load raw OCR text and strip everything before page 13 ──────────

def load_ocr_text(path):
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    # Find "--- PAGE 13 ---" and keep everything from there
    m = re.search(r"--- PAGE 13 ---", raw)
    if not m:
        raise ValueError("Could not find '--- PAGE 13 ---' in OCR file")
    text = raw[m.start():]
    # Remove all page markers
    text = re.sub(r"--- PAGE \d+ ---\n?", "\n", text)
    return text


# ── Step 2: extract blocks by section-number markers ───────────────────────

def extract_blocks(text):
    """
    Returns dict {claimed_num: raw_block_text}.
    Finds lines that are just "N." (1-3 digits, optional whitespace).
    Also finds inline starts: "N. Uppercase..." at line start.
    Handles two-column starts "N. M." by creating separate entries.
    """
    # Pattern: line(s) with section numbers
    # Single standalone:  "42."
    # Double standalone:  "42. 45."  → two columns (mixed)
    # Inline start:       "42. Valami szöveg..." (number at line start before text)
    single = re.compile(r"^(\d{1,3})\.\s*$", re.MULTILINE)
    double = re.compile(r"^(\d{1,3})\.\s+(\d{1,3})\.\s*$", re.MULTILINE)
    # Inline: number.space then a letter (uppercase or lowercase) — exclude page refs like "lapozz a 42-re"
    inline = re.compile(r"^(\d{1,3})\.\s+([A-ZÁÉÍÓÖŐÜŰA-Z\[—\-])", re.MULTILINE)

    # Find all markers, sorted by position
    markers = []
    double_positions = set()

    for m in double.finditer(text):
        markers.append((m.start(), int(m.group(1)), int(m.group(2)), "double"))
        double_positions.add(m.start())

    for m in single.finditer(text):
        if m.start() not in double_positions:
            markers.append((m.start(), int(m.group(1)), None, "single"))

    standalone_positions = {p for p, *_ in markers}

    for m in inline.finditer(text):
        num = int(m.group(1))
        if 1 <= num <= 300 and m.start() not in standalone_positions:
            # Avoid false positives: "Ha lapozz a 42-re" style lines
            line = text[m.start(): text.find("\n", m.start())]
            if "lapozz" not in line.lower() and "re!" not in line.lower():
                markers.append((m.start(), num, None, "inline"))
                standalone_positions.add(m.start())

    markers.sort(key=lambda x: x[0])

    # Build blocks: from end of marker to start of next marker
    blocks = {}  # {num: (text, is_mixed)}

    for i, (pos, num1, num2, kind) in enumerate(markers):
        # Find end of the header line
        header_end = text.find("\n", pos) + 1

        # Find start of next marker
        if i + 1 < len(markers):
            next_pos = markers[i + 1][0]
        else:
            next_pos = len(text)

        block = text[header_end:next_pos].strip()

        if kind == "double":
            # Two-column: flag both as mixed
            blocks[num1] = (block, True)
            blocks[num2] = (block, True)  # same raw block, will be flagged
        else:
            blocks[num1] = (block, False)

    return blocks


# ── Step 3: load existing sections ─────────────────────────────────────────

def load_sections(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data


# ── Step 4: match OCR blocks to existing sections ──────────────────────────

def clean_block(raw):
    """Light cleanup: remove obvious OCR artifacts, collapse whitespace."""
    text = raw
    # Remove stray single chars on their own lines (OCR noise)
    text = re.sub(r"^\s*[a-záéíóöőüű!§,\.]{1,2}\s*$", "", text, flags=re.MULTILINE | re.IGNORECASE)
    # Collapse multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def match_blocks_to_sections(blocks, existing_sections):
    """
    For each OCR block, find the best-matching existing section.
    Returns list of dicts with match info.
    """
    results = []

    # Build index of existing section texts (id → text)
    existing = {
        int(sid): sdata["text"]
        for sid, sdata in existing_sections.items()
    }

    used_sids = set()  # avoid double-assignment

    for claimed_num, (raw_block, is_mixed) in sorted(blocks.items()):
        if not (1 <= claimed_num <= 300):
            continue

        block_text = clean_block(raw_block)

        if not block_text or len(block_text) < 20:
            results.append({
                "claimed": claimed_num,
                "matched": None,
                "sim": 0.0,
                "status": "TOO_SHORT",
                "mixed": is_mixed,
                "new_text": None,
            })
            continue

        # Check similarity against the claimed section first
        claimed_sim = similarity(block_text, existing.get(claimed_num, ""))

        # Also check a window of ±5 neighbours (handles misread numbers)
        best_num = claimed_num
        best_sim = claimed_sim

        for delta in range(-5, 6):
            candidate = claimed_num + delta
            if candidate in existing and candidate != claimed_num:
                s = similarity(block_text, existing[candidate])
                if s > best_sim:
                    best_sim = s
                    best_num = candidate

        if best_sim < MATCH_THRESHOLD:
            status = "NO_MATCH"
            matched = None
        elif best_num != claimed_num and best_sim > claimed_sim + 0.05:
            # The block fits a different section better → probable misread number
            status = "RELABELED"
            matched = best_num
        elif best_num == claimed_num and claimed_sim >= TRUST_THRESHOLD:
            status = "OK"
            matched = claimed_num
        elif is_mixed:
            status = "MIXED"
            matched = claimed_num
        else:
            status = "LOW_SIM"
            matched = claimed_num

        if matched in used_sids and status == "OK":
            status = "DUPLICATE"
            matched = None

        if matched is not None:
            used_sids.add(matched)

        results.append({
            "claimed": claimed_num,
            "matched": matched,
            "sim": round(best_sim, 3),
            "status": status,
            "mixed": is_mixed,
            "new_text": block_text if matched is not None else None,
        })

    return results


# ── Step 5: apply updates ──────────────────────────────────────────────────

RELABEL_MIN_SIM = 0.55  # minimum similarity to apply a RELABELED block

def apply_updates(data, results, dry_run=False):
    sections = data["sections"]
    updated = 0
    skipped = []

    for r in results:
        apply = False
        if r["status"] == "OK" and r["matched"] is not None and r["new_text"]:
            apply = True
        elif r["status"] == "RELABELED" and r["matched"] is not None and r["new_text"]:
            if r["sim"] >= RELABEL_MIN_SIM:
                apply = True

        if apply:
            sid = str(r["matched"])
            if not dry_run:
                sections[sid]["text"] = r["new_text"]
            updated += 1
        else:
            skipped.append(r)

    return updated, skipped


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Analyse but don't write changes")
    parser.add_argument("--book-id", default=BOOK_ID)
    args = parser.parse_args()

    global BOOK_DIR, SECTIONS_FILE
    if args.book_id != BOOK_ID:
        BOOK_DIR = Path(__file__).parent.parent / "books" / args.book_id
        SECTIONS_FILE = BOOK_DIR / "sections.json"

    print(f"Loading OCR text from: {OCR_FILE}")
    text = load_ocr_text(OCR_FILE)
    print(f"  Loaded {len(text):,} chars after page 13")

    print(f"\nExtracting section blocks...")
    blocks = extract_blocks(text)
    print(f"  Found {len(blocks)} section number markers")

    print(f"\nLoading existing sections from: {SECTIONS_FILE}")
    data = load_sections(SECTIONS_FILE)
    existing_sections = data["sections"]
    print(f"  {len(existing_sections)} sections in JSON")

    print(f"\nMatching blocks to sections...")
    results = match_blocks_to_sections(blocks, existing_sections)

    # ── Summary ─────────────────────────────────────────────────────────
    status_counts = {}
    for r in results:
        status_counts[r["status"]] = status_counts.get(r["status"], 0) + 1

    print(f"\n{'-'*60}")
    print("MATCH SUMMARY")
    print(f"{'-'*60}")
    for status, count in sorted(status_counts.items()):
        print(f"  {status:<15} {count}")
    print(f"{'-'*60}")

    # Show non-OK entries
    non_ok = [r for r in results if r["status"] != "OK"]
    if non_ok:
        print(f"\nNon-OK sections (will be SKIPPED):")
        for r in sorted(non_ok, key=lambda x: x["claimed"]):
            mixed_flag = " [2-col]" if r["mixed"] else ""
            print(f"  Sec {r['claimed']:>3}  {r['status']:<12}  sim={r['sim']:.2f}{mixed_flag}"
                  + (f"  -> best match: {r['matched']}" if r["matched"] and r["matched"] != r["claimed"] else ""))

    ok_count = status_counts.get("OK", 0)
    print(f"\n{'DRY RUN — ' if args.dry_run else ''}Will update {ok_count} sections.")

    if not args.dry_run:
        updated, skipped = apply_updates(data, results, dry_run=False)
        with open(SECTIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Saved {SECTIONS_FILE}")
        print(f"Updated: {updated}  |  Skipped: {len(skipped)}")
    else:
        print("(No changes written — dry run)")


if __name__ == "__main__":
    main()

"""
Pipeline step 09: Merge new-parse sections with backup, then repair garbled text.

Strategy:
  1. Start with backup_path (300 garbled sections from old pipeline)
  2. Overwrite with new_parse_path (160 clean sections from new OCR)
  3. For the remaining ~140 backup-only sections, attempt text replacement
     from the new OCR using content similarity (may fix garbled text for some)
  4. Write merged output to sections.json

Usage:
    python pipeline/09_merge_sections.py [--dry-run]
"""

import re
import json
import unicodedata
import argparse
from pathlib import Path
from difflib import SequenceMatcher

BOOK_ID = "a-demon-szeme"
BOOK_DIR = Path(__file__).parent.parent / "books" / BOOK_ID
BACKUP_PATH = Path(r"D:\Code\sections_backup.json")
OCR_FILE = Path(r"D:\Code\OCR\23 - A démon szeme.txt")
OUT_PATH = BOOK_DIR / "sections.json"

# Similarity thresholds for text replacement
TRUST_THRESHOLD = 0.45
RELABEL_MIN_SIM = 0.55


# ── Helpers ─────────────────────────────────────────────────────────────────

def strip_diacritics(s):
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")

def normalize(text):
    t = strip_diacritics(text.lower())
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"[^a-z0-9 ]", "", t)
    return t.strip()

def similarity(a, b):
    na, nb = normalize(a), normalize(b)
    if not na or not nb:
        return 0.0
    return SequenceMatcher(None, na[:400], nb[:400]).ratio()


# ── OCR block extraction (same as 08_replace_section_text.py) ───────────────

def load_ocr_text(path):
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    m = re.search(r"--- PAGE 13 ---", raw)
    if not m:
        raise ValueError("Could not find '--- PAGE 13 ---' in OCR file")
    text = raw[m.start():]
    text = re.sub(r"--- PAGE \d+ ---\n?", "\n", text)
    return text


def extract_blocks(text):
    single = re.compile(r"^(\d{1,3})\.\s*$", re.MULTILINE)
    double = re.compile(r"^(\d{1,3})\.\s+(\d{1,3})\.\s*$", re.MULTILINE)
    inline = re.compile(r"^(\d{1,3})\.\s+([A-ZÁÉÍÓÖŐÜŰA-Z\[—\-])", re.MULTILINE)

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
            line = text[m.start(): text.find("\n", m.start())]
            if "lapozz" not in line.lower() and "re!" not in line.lower():
                markers.append((m.start(), num, None, "inline"))
                standalone_positions.add(m.start())

    markers.sort(key=lambda x: x[0])

    blocks = {}
    for i, (pos, num1, num2, kind) in enumerate(markers):
        header_end = text.find("\n", pos) + 1
        next_pos = markers[i + 1][0] if i + 1 < len(markers) else len(text)
        block = text[header_end:next_pos].strip()

        if kind == "double":
            blocks[num1] = (block, True)
            blocks[num2] = (block, True)
        else:
            blocks[num1] = (block, False)

    return blocks


def clean_block(raw):
    text = raw
    text = re.sub(r"^\s*[a-záéíóöőüű!§,\.]{1,2}\s*$", "", text,
                  flags=re.MULTILINE | re.IGNORECASE)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def match_blocks(blocks, target_sections):
    """Match OCR blocks to sections that need text repair."""
    results = {}  # section_id -> (matched_block_text, sim, status)

    for sec_id, sec_data in target_sections.items():
        claimed = int(sec_id)
        old_text = sec_data.get("text", "")

        best_num = None
        best_sim = 0.0
        best_text = None
        best_mixed = False

        # Check block at claimed number + ±5 neighbours
        for delta in range(-5, 6):
            candidate = claimed + delta
            if candidate in blocks:
                raw_b, is_mixed = blocks[candidate]
                cleaned = clean_block(raw_b)
                if len(cleaned) < 20:
                    continue
                s = similarity(old_text, cleaned)
                if s > best_sim:
                    best_sim = s
                    best_num = candidate
                    best_text = cleaned
                    best_mixed = is_mixed

        if best_text is None or best_sim < 0.30:
            status = "NO_MATCH"
        elif best_mixed:
            status = "MIXED"
        elif best_num == claimed and best_sim >= TRUST_THRESHOLD:
            status = "OK"
        elif best_num != claimed and best_sim >= RELABEL_MIN_SIM:
            status = "RELABELED"
        elif best_sim >= TRUST_THRESHOLD:
            status = "OK"
        else:
            status = "LOW_SIM"

        results[sec_id] = {
            "sim": round(best_sim, 3),
            "status": status,
            "new_text": best_text if status in ("OK", "RELABELED") else None,
        }

    return results


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    # 1. Load backup (300 sections, garbled)
    print(f"Loading backup from: {BACKUP_PATH}")
    with open(BACKUP_PATH, encoding="utf-8") as f:
        backup = json.load(f)
    print(f"  {len(backup['sections'])} sections in backup")

    # 2. Load new parse (160 clean sections)
    print(f"Loading new parse from: {OUT_PATH}")
    with open(OUT_PATH, encoding="utf-8") as f:
        new_parse = json.load(f)
    new_sections = new_parse["sections"]
    print(f"  {len(new_sections)} sections in new parse")

    # 3. Build merged output: start from backup, overwrite with new parse
    # Exception: if new parse has >5 choices but backup has fewer, the new parse
    # likely absorbed text from adjacent sections (two-column OCR mixing) — keep backup.
    merged = {}
    new_overwrite = 0
    new_parse_rejected = []
    for sid, sec_data in backup["sections"].items():
        if sid in new_sections:
            new_sec = new_sections[sid]
            new_choices = len(new_sec.get("choices", []))
            backup_choices = len(sec_data.get("choices", []))
            # Reject new parse if choices look wrong vs backup:
            # 1. Too many (absorbed adjacent section content via two-column mixing)
            # 2. Too few (fragmented OCR dropped choices that backup captured)
            too_many = new_choices > 5 and new_choices > backup_choices + 1
            too_few = backup_choices >= 2 and new_choices < backup_choices - 1
            if too_many or too_few:
                merged[sid] = sec_data
                new_parse_rejected.append(int(sid))
            else:
                # Use new parse data, but preserve events from backup if present
                if sec_data.get("events") and not new_sec.get("events"):
                    new_sec = dict(new_sec)
                    new_sec["events"] = sec_data["events"]
                merged[sid] = new_sec
                new_overwrite += 1
        else:
            # Keep backup data
            merged[sid] = sec_data

    backup_only = {sid: sec for sid, sec in merged.items() if sid not in new_sections}
    print(f"\nMerge result: {len(merged)} sections total")
    print(f"  Overwritten by new parse: {new_overwrite}")
    print(f"  New parse rejected (mixed content): {len(new_parse_rejected)} {new_parse_rejected}")
    print(f"  Kept from backup only:    {len(backup_only)}")

    # 4. Attempt text repair on backup-only sections using new OCR
    print(f"\nLoading OCR text for repair pass...")
    ocr_text = load_ocr_text(OCR_FILE)
    blocks = extract_blocks(ocr_text)
    print(f"  {len(blocks)} OCR blocks extracted")

    repair_results = match_blocks(blocks, backup_only)

    repaired = 0
    no_match = 0
    for sid, res in repair_results.items():
        if res["status"] in ("OK", "RELABELED") and res["new_text"]:
            if not args.dry_run:
                merged[sid]["text"] = res["new_text"]
            repaired += 1
        elif res["status"] == "NO_MATCH":
            no_match += 1

    print(f"\nRepair pass on {len(backup_only)} backup-only sections:")
    print(f"  Repaired (clean OCR text found): {repaired}")
    print(f"  No match (garbled text kept):    {no_match}")
    print(f"  Other (low sim / mixed):         {len(backup_only) - repaired - no_match}")

    # Show which sections still have garbled text
    garbled = [sid for sid, res in repair_results.items()
               if res["status"] not in ("OK", "RELABELED")]
    if garbled:
        print(f"\n  Sections still garbled ({len(garbled)}): "
              f"{sorted(int(s) for s in garbled)[:20]}{'...' if len(garbled) > 20 else ''}")

    # 5. Write output
    output = {
        "book_id": backup["book_id"],
        "title": backup["title"],
        "author": backup["author"],
        "year": backup["year"],
        "total_sections": backup["total_sections"],
        "sections": merged,
    }

    if not args.dry_run:
        with open(OUT_PATH, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"\nWritten {len(merged)} sections to {OUT_PATH}")
    else:
        print(f"\n[DRY RUN] Would write {len(merged)} sections to {OUT_PATH}")


if __name__ == "__main__":
    main()

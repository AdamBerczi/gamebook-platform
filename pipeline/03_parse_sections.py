"""
03_parse_sections.py

Parses raw OCR text files into a structured sections.json.

Design principle: this script is GENERIC. All book-specific knowledge
(section count, navigation phrases, ending markers) lives in
books/<book-id>/parse_config.json — not here.

To add a new book later:
  1. Run 01 and 02 to get raw text
  2. Write a parse_config.json for the new book
  3. Run: python 03_parse_sections.py <new-book-id>

Output schema (sections.json):
  {
    "book_id": "magusok-tornya",
    "title": "...",
    "total_sections": 300,
    "sections": {
      "1": {
        "id": 1,
        "text": "...",
        "choices": [
          { "text": "Ha jobbra méssz", "target": 42 }
        ],
        "is_ending": false,
        "has_combat": false,
        "has_luck_test": false
      },
      ...
    }
  }
"""

import json
import re
import sys
from pathlib import Path


def load_config(book_dir: Path) -> dict:
    config_path = book_dir / "parse_config.json"
    if not config_path.exists():
        print(f"ERROR: No parse_config.json found at {config_path}")
        print("Create one before running this script.")
        sys.exit(1)
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


def load_raw_text(book_dir: Path, config: dict) -> str:
    """
    Concatenate text files in page order, starting from first_content_page.
    Uses cleaned-text/<page>.txt when available, raw-text/<page>.txt otherwise.
    This lets partial cleanup runs still improve what they covered.
    """
    cleaned_dir = book_dir / "cleaned-text"
    raw_dir     = book_dir / "raw-text"
    first_page  = config["parsing"]["first_content_page"]

    pages = sorted(raw_dir.glob("page-*.txt"))
    cleaned_count = sum(1 for p in pages if (cleaned_dir / p.name).exists())
    print(f"  (cleaned: {cleaned_count}/{len(pages)} pages — rest from raw-text/)")
    if not pages:
        print(f"ERROR: No raw text files found in {raw_dir}")
        print("Run 02_ocr_pages.py first.")
        sys.exit(1)

    chunks = []
    for page_path in pages:
        page_num = int(re.search(r"page-(\d+)", page_path.name).group(1))
        if page_num < first_page:
            continue
        # Prefer cleaned version if it exists for this specific page
        clean_path = cleaned_dir / page_path.name
        chosen = clean_path if clean_path.exists() else page_path
        chunks.append(chosen.read_text(encoding="utf-8"))

    return "\n".join(chunks)


def split_into_raw_sections(full_text: str, config: dict) -> dict[int, str]:
    """
    Split the full OCR text into a dict of { section_number: raw_text }.

    A section starts when we see a line that is exactly "N." where N is
    a plausible section number (1 to total_sections).

    Also tries relaxed variants to handle OCR errors:
      "N,"  — period OCR'd as comma
      "N"   — period dropped entirely (standalone digit line)

    Any text before the first recognized header is captured as section 1
    (many books start the first content page without repeating "1.").
    """
    total = config["total_sections"]
    header_re  = re.compile(config["parsing"]["section_header_regex"], re.MULTILINE)
    # Relaxed fallback: N, or bare N on its own line
    relaxed_re = re.compile(r"^(\d{1,3})[,]?$")

    def match_header(line):
        """Return section number if line is a section header, else None."""
        stripped = line.strip()
        m = header_re.match(stripped)
        if m:
            return int(m.group(1))
        m = relaxed_re.match(stripped)
        if m:
            return int(m.group(1))
        return None

    lines = full_text.splitlines()

    sections_raw = {}
    current_id = None
    current_lines = []
    pre_header_lines = []   # text before the very first section header

    for line in lines:
        candidate = match_header(line)
        if candidate is not None and 1 <= candidate <= total:
            if current_id is None and not sections_raw:
                # First header found — save anything before it as section 1
                # (only if there's meaningful text and section 1 not yet set)
                pre_text = "\n".join(pre_header_lines).strip()
                if pre_text and candidate != 1:
                    sections_raw[1] = pre_text
            # Save the previous section
            if current_id is not None:
                sections_raw[current_id] = "\n".join(current_lines).strip()
            current_id = candidate
            current_lines = []
            continue

        if current_id is None:
            pre_header_lines.append(line)
        else:
            current_lines.append(line)

    # Don't forget the last section
    if current_id is not None:
        sections_raw[current_id] = "\n".join(current_lines).strip()

    return sections_raw


def extract_choices(text: str, config: dict) -> list[dict]:
    """
    Find all navigation choices in a section's text.

    Hungarian gamebooks use patterns like:
      "Ha jobbra méssz, lapozz a 42-re!"
      "Ha balra, lapozz a 17-ra!"

    We extract: the sentence leading up to "lapozz", and the target number.
    """
    choices = []

    # Match any sentence ending with a navigation phrase and section number.
    # We look for an optional "Ha ..." prefix, then the navigation phrase.
    pattern = re.compile(
        # Matches many OCR variants of "lapozz":
        #   lapozz a 42-re      (normal)
        #   lapozz az 42-re     (article "az" before vowel-starting numbers)
        #   lapozza 42-re       (OCR merged article "a" into verb)
        #   lapozza a 42-re     (redundant but occurs)
        #   laporz a 42-re      (OCR misread double-z as rz)
        r"([^.!?\n]*?)\s*[Ll]apo[rz]z[a]?\s+(?:az?\s+)?(\d+)[.-](re|ra|es|ös|as|ás)?[^!]*!",
        re.IGNORECASE
    )

    for m in pattern.finditer(text):
        choice_text = m.group(1).strip().lstrip("–-•* ").strip()
        target = int(m.group(2))
        choices.append({
            "text": choice_text if choice_text else None,
            "target": target
        })

    return choices


def extract_enemies(text: str) -> list[dict]:
    """
    Find enemy stat blocks embedded in section text.

    Handles many OCR variants seen in this book:
      - "védettségi szint" / "védettsége szint" / "védettsegi szint" / "védettségi szente"
      - "támadási képesség" / "támádási képesség"
      - "életerő" / "életero" / "életerő"
      - Names ending with ": életerő..." or ", az alábbi tulajdonságokkal: életerő..."
    """
    enemies = []

    # Flexible pattern: name (anything ending in colon) + three stats
    # Handles OCR variants: "védetsségi/védeusegi szini", "sérülési képesség", etc.
    stat_pattern = re.compile(
        r"([^\n:]{3,40}):\s*"
        r"él[e]?ter[oő]\s+(\d+)\s*(?:\([^)]+\))?\s*,\s*"  # életerő N (optional parenthetical)
        r"(?:tám[aá]d[aá]si|s[eé]r[uü]l[eé]si|csata)\s+k[eé]pess[eé]g\s+(\d+)\s*,\s*"
        r"véd\w{0,10}\s+\w{2,6}\s+(\d+)",
        re.IGNORECASE
    )

    # Also match the "tulajdonságokkal: életerő..." pattern
    alt_pattern = re.compile(
        r"([^\n,]{3,40}),\s*az\s+al[aá]bbi\s+tulajdons[aá]gokkal:\s*"
        r"él[e]?ter[oő]\s+(\d+)\s*(?:\([^)]+\))?\s*,\s*"
        r"(?:tám[aá]d[aá]si|s[eé]r[uü]l[eé]si|csata)\s+k[eé]pess[eé]g\s+(\d+)\s*,\s*"
        r"véd\w{0,10}\s+\w{2,6}\s+(\d+)",
        re.IGNORECASE
    )

    damage_pattern = re.compile(r"(\d+[-–]\d+)\s*él[e]?ter[oő]pont")

    found_names = set()

    for pattern in [stat_pattern, alt_pattern]:
        for m in pattern.finditer(text):
            name = m.group(1).strip().rstrip(':,. ')
            if name.lower() in found_names:
                continue
            found_names.add(name.lower())

            enemy = {
                "name":              name,
                "eletero":           int(m.group(2)),
                "tamadasi_kepesseg": int(m.group(3)),
                "vedettsegi_szint":  int(m.group(4)),
                "damage":            None,
            }
            nearby = text[m.start():m.start() + 300]
            dm = damage_pattern.search(nearby)
            if dm:
                enemy["damage"] = dm.group(1)
            enemies.append(enemy)

    return enemies


def classify_section(text: str, choices: list, config: dict) -> dict:
    """
    Detect flags about this section's content.
    Returns a dict of boolean flags.
    """
    parsing = config["parsing"]

    is_ending = any(
        phrase.lower() in text.lower()
        for phrase in parsing["ending_phrases"]
    )

    has_combat = any(
        phrase.lower() in text.lower()
        for phrase in parsing["combat_hint_phrases"]
    )

    has_luck_test = any(
        phrase.lower() in text.lower()
        for phrase in parsing["luck_test_phrases"]
    )

    return {
        "is_ending": is_ending,
        "has_combat": has_combat,
        "has_luck_test": has_luck_test,
    }


def parse_sections(book_id: str):
    root = Path(__file__).parent.parent
    book_dir = root / "books" / book_id

    print(f"Loading config for '{book_id}'...")
    config = load_config(book_dir)

    print(f"Loading raw OCR text (starting from page {config['parsing']['first_content_page']})...")
    full_text = load_raw_text(book_dir, config)

    print("Splitting into sections...")
    sections_raw = split_into_raw_sections(full_text, config)
    print(f"  Found {len(sections_raw)} sections (expected {config['total_sections']})")

    print("Parsing choices and classifying sections...")
    sections_out = {}
    for section_id, raw_text in sorted(sections_raw.items()):
        choices = extract_choices(raw_text, config)
        flags = classify_section(raw_text, choices, config)

        enemies = extract_enemies(raw_text)

        sections_out[str(section_id)] = {
            "id": section_id,
            "text": raw_text,
            "choices": choices,
            "enemies": enemies,
            **flags,
        }

    output = {
        "book_id": config["book_id"],
        "title": config["title"],
        "author": config["author"],
        "year": config["year"],
        "total_sections": config["total_sections"],
        "sections": sections_out,
    }

    out_path = book_dir / "sections.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nDone. Written to {out_path}")
    _print_stats(sections_out, config)


def _print_stats(sections: dict, config: dict):
    """Print a summary so we can quickly spot parsing problems."""
    total_expected = config["total_sections"]
    found = len(sections)
    missing = sorted(set(range(1, total_expected + 1)) - {s["id"] for s in sections.values()})
    endings = sum(1 for s in sections.values() if s["is_ending"])
    combat = sum(1 for s in sections.values() if s["has_combat"])
    luck = sum(1 for s in sections.values() if s["has_luck_test"])
    # Section equal to total_sections is often the back cover — exclude from warning
    no_choices = [
        s["id"] for s in sections.values()
        if not s["choices"] and not s["is_ending"] and s["id"] != total_expected
    ]

    print(f"\n--- Parse Summary ---")
    print(f"  Sections found:    {found} / {total_expected}")
    print(f"  Missing sections:  {len(missing)} {missing[:10]}{'...' if len(missing) > 10 else ''}")
    print(f"  Dead ends:         {endings}")
    print(f"  Combat sections:   {combat}")
    print(f"  Luck test sections:{luck}")
    print(f"  No choices (non-ending): {len(no_choices)} {no_choices[:10]}")


if __name__ == "__main__":
    book_id = sys.argv[1] if len(sys.argv) > 1 else "magusok-tornya"
    parse_sections(book_id)

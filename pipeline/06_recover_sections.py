"""
06_recover_sections.py

Recover sections whose headers were lost or misread in OCR.

Root cause identified: two-column layout causes:
  1. Some section headers at column tops to be dropped (e.g. "4." missing)
  2. Some multi-digit headers to lose their leading digit (e.g. "52." -> "2.", "53." -> "3.")

Strategy:
  A. Build an ordered sequence of ALL header occurrences in the OCR text.
  B. Detect "suspicious" duplicates: a second "N." that appears after a section number
     much larger than N is likely a misread of "?N." (e.g. "52." misread as "2.").
  C. Re-assign suspicious duplicates to the most plausible missing section ID.
  D. For remaining gaps (missing sections between consecutive valid headers), extract
     the content by splitting on the current section's own choices/endings.
  E. Merge all recovered sections into sections.json.

Usage:
  python pipeline/06_recover_sections.py a-demon-szeme
"""

import json
import re
import sys
from pathlib import Path


# ── helpers ───────────────────────────────────────────────────────────────────

def load_config(book_dir):
    with open(book_dir / "parse_config.json", encoding="utf-8") as f:
        return json.load(f)


def load_raw_text(book_dir, config):
    cleaned_dir = book_dir / "cleaned-text"
    raw_dir = book_dir / "raw-text"
    first_page = config["parsing"]["first_content_page"]
    pages = sorted(raw_dir.glob("page-*.txt"))
    chunks = []
    for page_path in pages:
        page_num = int(re.search(r"page-(\d+)", page_path.name).group(1))
        if page_num < first_page:
            continue
        clean_path = cleaned_dir / page_path.name
        chosen = clean_path if clean_path.exists() else page_path
        chunks.append(chosen.read_text(encoding="utf-8"))
    return "\n".join(chunks)


def find_all_headers(full_text, config):
    """
    Return list of (section_id, line_index) for every header match,
    in line order. Includes duplicate IDs.
    """
    total = config["total_sections"]
    header_re = re.compile(config["parsing"]["section_header_regex"], re.MULTILINE)
    relaxed_re = re.compile(r"^(\d{1,3})[,]?$")

    def match_header(line):
        stripped = line.strip()
        m = header_re.match(stripped)
        if m:
            return int(m.group(1))
        m = relaxed_re.match(stripped)
        if m:
            return int(m.group(1))
        return None

    occurrences = []
    for i, line in enumerate(full_text.splitlines()):
        n = match_header(line)
        if n is not None and 1 <= n <= total:
            occurrences.append((n, i))
    return occurrences


def resolve_headers(occurrences, total, missing_ids, all_sections_ids):
    """
    Given all raw header occurrences in line order, produce a clean list of
    (section_id, line_index) that makes the best sense.

    Rules:
      1. If a section_id appears only once, keep it.
      2. If it appears multiple times:
         a. The FIRST occurrence is kept as the "real" section.
         b. Later occurrences where the preceding section ID is >> the candidate ID
            are "suspicious". We try to remap them to a nearby section.
            (We try both missing AND already-found sections, because we need
             the correct headers for accurate block splitting.)
    """
    result = []
    used_ids = set()

    prev_id = 0
    for idx, (sec_id, line_no) in enumerate(occurrences):
        suspicious = (sec_id in used_ids) and (prev_id > sec_id + 5)

        if not suspicious:
            result.append((sec_id, line_no))
            used_ids.add(sec_id)
            prev_id = sec_id
        else:
            remapped = False
            for tens in [10, 100]:
                candidate = (prev_id // tens) * tens + sec_id
                if candidate not in used_ids and 1 <= candidate <= total:
                    status = "missing" if candidate in missing_ids else "found"
                    print(f"    REMAP: '{sec_id}.' at line {line_no} (after sec {prev_id}) "
                          f"-> section {candidate} [{status}]")
                    result.append((candidate, line_no))
                    used_ids.add(candidate)
                    prev_id = candidate
                    remapped = True
                    break
            if not remapped:
                print(f"    SKIP duplicate '{sec_id}.' at line {line_no} (prev={prev_id}, already used)")

    return result


def extract_choices(text):
    choices = []
    pattern = re.compile(
        r"([^.!?\n]*?)\s*[Ll]apo[rz]z[a]?\s+(?:az?\s+)?(\d+)[.-](re|ra|es|os|as|as)?[^!]*!",
        re.IGNORECASE
    )
    for m in pattern.finditer(text):
        choice_text = m.group(1).strip().lstrip("-.•* ").strip()
        target = int(m.group(2))
        choices.append({"text": choice_text or None, "target": target})
    return choices


def extract_enemies(text):
    enemies = []
    stat_pattern = re.compile(
        r"([^\n:]{3,40}):\s*él[e]?ter[oő]\s+(\d+)\s*,\s*"
        r"tám[aá]d[aá]si\s+képesség\s+(\d+)\s*,\s*"
        r"véd[e]?ttsé?g[ie]?\s+\w+\s+(\d+)",
        re.IGNORECASE,
    )
    damage_pattern = re.compile(r"(\d+[-–]\d+)\s*él[e]?ter[oő]pont")
    for m in stat_pattern.finditer(text):
        name = m.group(1).strip().rstrip(":,. ")
        enemy = {
            "name": name,
            "eletero": int(m.group(2)),
            "tamadasi_kepesseg": int(m.group(3)),
            "vedettsegi_szint": int(m.group(4)),
            "damage": None,
        }
        nearby = text[m.start(): m.start() + 300]
        dm = damage_pattern.search(nearby)
        if dm:
            enemy["damage"] = dm.group(1)
        enemies.append(enemy)
    return enemies


def classify(text, config):
    parsing = config["parsing"]
    return {
        "is_ending": any(p.lower() in text.lower() for p in parsing["ending_phrases"]),
        "has_combat": any(p.lower() in text.lower() for p in parsing["combat_hint_phrases"]),
        "has_luck_test": any(p.lower() in text.lower() for p in parsing["luck_test_phrases"]),
    }


def make_section(section_id, text, config):
    text = text.strip()
    choices = extract_choices(text)
    enemies = extract_enemies(text)
    flags = classify(text, config)
    return {"id": section_id, "text": text, "choices": choices, "enemies": enemies, **flags}


def split_gap(gap_text, missing_ids, config):
    """
    Split gap_text into len(missing_ids) chunks.
    A chunk boundary is detected after a group of navigation/ending lines.
    """
    if len(missing_ids) == 1:
        return {missing_ids[0]: gap_text.strip()}

    lines = gap_text.splitlines()
    nav_re = re.compile(r"[Ll]apo[rz]z[a]?\s+(?:az?\s+)?\d+", re.IGNORECASE)
    end_re = re.compile(
        "|".join(re.escape(p) for p in config["parsing"]["ending_phrases"]),
        re.IGNORECASE,
    )

    split_positions = []
    i = 0
    while i < len(lines):
        if nav_re.search(lines[i]) or end_re.search(lines[i]):
            j = i
            while j < len(lines) and (nav_re.search(lines[j]) or end_re.search(lines[j]) or not lines[j].strip()):
                j += 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines):
                split_positions.append(j)
            i = j
        else:
            i += 1

    needed = len(missing_ids) - 1
    if len(split_positions) >= needed:
        split_positions = split_positions[:needed]
        splits = [0] + split_positions + [len(lines)]
        return {
            sec_id: "\n".join(lines[splits[k]: splits[k + 1]]).strip()
            for k, sec_id in enumerate(missing_ids)
        }
    elif split_positions:
        # Partial split: use what we have, assign remaining to consecutive sections
        print(f"    WARN: gap {missing_ids}: {len(split_positions)} split points for {needed} needed — partial split")
        splits = [0] + split_positions + [len(lines)]
        result = {}
        for k in range(len(splits) - 1):
            if k < len(missing_ids):
                result[missing_ids[k]] = "\n".join(lines[splits[k]: splits[k + 1]]).strip()
        for k in range(len(splits) - 1, len(missing_ids)):
            result[missing_ids[k]] = ""
        return result
    else:
        print(f"    WARN: gap {missing_ids}: no split points (all content assigned to first)")
        result = {missing_ids[0]: gap_text.strip()}
        for sec_id in missing_ids[1:]:
            result[sec_id] = ""
        return result


def section_ends_at(block_lines, known_choices, config, is_ending=False):
    """
    Given the OCR block text for section N (which may include N+1, N+2, ...),
    find the line index where section N's OWN content ends.

    Strategy: find the FIRST navigation/ending block in the text.
    In Hungarian gamebooks, all of a section's choices appear at the END, in one
    consecutive cluster. The first such cluster belongs to section N; everything
    after it belongs to the missing next section(s).

    We use known_choices (choice TARGETS from sections.json) only to validate
    we found the right cluster — not to pick the LAST nav line.
    """
    nav_re = re.compile(r"[Ll]apo[rz]z[a]?\s+(?:az?\s+)?(\d+)", re.IGNORECASE)
    end_re = re.compile(
        "|".join(re.escape(p) for p in config["parsing"]["ending_phrases"]),
        re.IGNORECASE,
    )
    choice_targets = set(c["target"] for c in (known_choices or []))

    # Find all nav/ending clusters (a cluster ends at the first blank line after nav lines)
    # We collect them all so we can pick the right one.
    clusters = []  # list of (start, end_exclusive) where end is exclusive
    j = 0
    while j < len(block_lines):
        if nav_re.search(block_lines[j]) or end_re.search(block_lines[j]):
            start = j
            end = j + 1
            j += 1
            # Extend cluster only over consecutive non-blank nav lines
            while j < len(block_lines) and (
                nav_re.search(block_lines[j]) or end_re.search(block_lines[j])
            ):
                end = j + 1
                j += 1
            clusters.append((start, end))
        else:
            j += 1

    if not clusters:
        return len(block_lines)  # no nav found

    # If this section is an ending, use the FIRST ending phrase as the split point.
    # Don't try to match nav-choice targets (they may be contaminated by the next section).
    if is_ending:
        for start, end in clusters:
            cluster_text = " ".join(block_lines[start:end])
            if end_re.search(cluster_text):
                split = end
                while split < len(block_lines) and not block_lines[split].strip():
                    split += 1
                return split
        is_ending = False  # fall through to nav logic

    if choice_targets:
        # Find the first nav cluster that contains at least one known choice target.
        # Then do AT MOST ONE extension past a blank if the very next non-blank line
        # is also a nav line for a remaining known target.
        # (Handles sections like 40 where two choices are separated by a blank line,
        # without over-extending into the next section's paragraph content.)
        for c_start, c_end in clusters:
            cluster_targets = set()
            for line in block_lines[c_start:c_end]:
                m = nav_re.search(line)
                if m:
                    cluster_targets.add(int(m.group(1)))
            if not (cluster_targets & choice_targets):
                continue

            remaining = choice_targets - cluster_targets
            split = c_end

            # ONE extension only: if the very next non-blank line is a nav for a remaining target,
            # consume it and any consecutive nav lines that follow (same cluster).
            if remaining:
                j = split
                while j < len(block_lines) and not block_lines[j].strip():
                    j += 1
                if j < len(block_lines):
                    m = nav_re.search(block_lines[j])
                    if m and int(m.group(1)) in remaining:
                        # Extend: consume this nav line and any consecutive nav/ending lines
                        split = j + 1
                        while split < len(block_lines) and (
                            nav_re.search(block_lines[split]) or end_re.search(block_lines[split])
                        ):
                            split += 1

            # Skip trailing blanks
            while split < len(block_lines) and not block_lines[split].strip():
                split += 1

            if split < len(block_lines):
                return split
            break  # cluster left no content — fall through

    # Fallback: use the first nav cluster
    cluster_start, cluster_end = clusters[0]
    split = cluster_end
    while split < len(block_lines) and not block_lines[split].strip():
        split += 1
    return split


# ── main ──────────────────────────────────────────────────────────────────────

def recover_sections(book_id):
    root = Path(__file__).parent.parent
    book_dir = root / "books" / book_id

    print(f"Loading config and OCR text for '{book_id}'...")
    config = load_config(book_dir)
    full_text = load_raw_text(book_dir, config)
    lines = full_text.splitlines()
    total = config["total_sections"]

    # Load existing sections.json
    sections_path = book_dir / "sections.json"
    with open(sections_path, encoding="utf-8") as f:
        data = json.load(f)
    existing = data["sections"]
    found_ids = set(int(k) for k in existing.keys())
    missing = sorted(set(range(1, total + 1)) - found_ids)
    print(f"  Currently {len(found_ids)} sections, {len(missing)} missing")

    # Find all raw header occurrences
    print("Finding all header occurrences...")
    occurrences = find_all_headers(full_text, config)
    print(f"  {len(occurrences)} raw header matches")

    # Resolve to clean sequence (filter duplicates, remap misread numbers)
    print("Resolving header sequence...")
    resolved = resolve_headers(occurrences, total, set(missing), set(int(k) for k in existing.keys()))
    resolved.sort(key=lambda x: x[1])
    print(f"  {len(resolved)} resolved headers")

    # Build section blocks: (sec_id, start_line, end_line)
    blocks = []
    for i, (sec_id, start_line) in enumerate(resolved):
        end_line = resolved[i + 1][1] if i + 1 < len(resolved) else len(lines)
        blocks.append((sec_id, start_line, end_line))

    # Handle pre-header content (before first recognized header)
    first_header_line = resolved[0][1] if resolved else len(lines)
    pre_text = "\n".join(lines[:first_header_line]).strip()
    first_known_id = resolved[0][0] if resolved else total
    if 1 not in found_ids and pre_text and first_known_id > 1:
        pre_gap = [n for n in range(1, first_known_id) if n in missing]
        if pre_gap:
            print(f"  Processing pre-header gap: {pre_gap}")
            recovered = split_gap(pre_text, pre_gap, config)
            for sec_id, text in recovered.items():
                if text.strip():
                    existing[str(sec_id)] = make_section(sec_id, text, config)
                    print(f"    OK section {sec_id} ({len(text)} chars)")

    # STEP 1: Add content for blocks that were resolved (remapped) but not yet in sections.json
    recovered_count = 0
    missing_set = set(missing)
    for cur_id, cur_start, cur_end in blocks:
        if cur_id not in missing_set:
            continue
        # This section was resolved (found in OCR at a remapped header) but not yet stored
        block_text = "\n".join(lines[cur_start + 1: cur_end]).strip()
        if block_text:
            existing[str(cur_id)] = make_section(cur_id, block_text, config)
            missing_set.discard(cur_id)
            recovered_count += 1
            print(f"  OK resolved section {cur_id} from block ({len(block_text)} chars)")

    # Refresh missing after block additions
    missing = sorted(missing_set)

    # Process each block gap
    for i, (cur_id, cur_start, cur_end) in enumerate(blocks):
        if i + 1 >= len(blocks):
            break
        next_id = blocks[i + 1][0]
        gap_ids = [n for n in range(cur_id + 1, next_id) if n in missing_set]
        if not gap_ids:
            continue

        # All lines in this block (after the header)
        block_lines = lines[cur_start + 1: cur_end]

        # Find where the CURRENT section's own content ends
        # Use known choices from sections.json if current section is found
        known_choices = existing.get(str(cur_id), {}).get("choices", []) if str(cur_id) in existing else []
        cur_is_ending = existing.get(str(cur_id), {}).get("is_ending", False) if str(cur_id) in existing else False

        # Special case: if current section was OVERWRITTEN by a misread
        # (e.g. section 2 content was replaced by section 52 content),
        # then known_choices are from the WRONG section. We need a better split point.
        # Heuristic: if the block contains "Kalandod véget ért!" or lapozz patterns
        # for DIFFERENT targets than known_choices, use the first nav block only.

        split_at = section_ends_at(block_lines, known_choices, config, is_ending=cur_is_ending)
        gap_content = "\n".join(block_lines[split_at:]).strip()

        if not gap_content:
            # Fallback 1: section N has no own nav choices (e.g. a shop section).
            # Look for a blank-line boundary followed by new paragraph content.
            # The first "text paragraph → blank → text paragraph → nav" pattern
            # suggests the second paragraph belongs to the missing section.
            blank_split = None
            prev_non_blank = False
            for j, line in enumerate(block_lines):
                is_nav = bool(re.search(r"[Ll]apo[rz]z[a]?\s+(?:az?\s+)?\d+", line))
                is_end = any(p.lower() in line.lower() for p in config["parsing"]["ending_phrases"])
                is_blank = not line.strip()
                if not is_blank and not is_nav and not is_end:
                    if prev_non_blank is False:
                        prev_non_blank = True
                elif is_blank and prev_non_blank:
                    # First blank line after content — check if followed by more non-nav content
                    k = j + 1
                    while k < len(block_lines) and not block_lines[k].strip():
                        k += 1
                    if k < len(block_lines) and not re.search(r"[Ll]apo[rz]z[a]?\s+(?:az?\s+)?\d+", block_lines[k]):
                        blank_split = k
                        break
                    prev_non_blank = False
                elif is_nav or is_end:
                    prev_non_blank = False

            if blank_split is not None:
                gap_content = "\n".join(block_lines[blank_split:]).strip()
                if gap_content:
                    print(f"  Gap {gap_ids} after sec {cur_id} (blank-split at {cur_start+1+blank_split}, {len(gap_content)} chars)")
                    recovered = split_gap(gap_content, gap_ids, config)
                    for sec_id, text in recovered.items():
                        if text.strip():
                            existing[str(sec_id)] = make_section(sec_id, text, config)
                            missing_set.discard(sec_id)
                            recovered_count += 1
                            print(f"    OK section {sec_id} ({len(text)} chars)")
                        else:
                            print(f"    -- section {sec_id}: empty")
                    continue

            print(f"  Gap {gap_ids} after sec {cur_id}: no content found (skip)")
            continue

        print(f"  Gap {gap_ids} after sec {cur_id} (split at line {cur_start+1+split_at}, {len(gap_content)} chars)")
        recovered = split_gap(gap_content, gap_ids, config)
        for sec_id, text in recovered.items():
            if text.strip():
                existing[str(sec_id)] = make_section(sec_id, text, config)
                missing_set.discard(sec_id)
                recovered_count += 1
                print(f"    OK section {sec_id} ({len(text)} chars)")
            else:
                print(f"    -- section {sec_id}: empty")

    # Save
    data["sections"] = existing
    with open(sections_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    new_total = len(existing)
    still_missing = sorted(set(range(1, total + 1)) - set(int(k) for k in existing.keys()))
    print(f"\nDone. {new_total} sections (was {len(found_ids)}), recovered {recovered_count}.")
    print(f"Still missing: {len(still_missing)}")
    if still_missing:
        print(f"  {still_missing}")


if __name__ == "__main__":
    book_id = sys.argv[1] if len(sys.argv) > 1 else "a-demon-szeme"
    recover_sections(book_id)

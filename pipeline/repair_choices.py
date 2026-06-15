"""Repair dropped / mis-numbered navigation choices in a-demon-szeme.

Built from diagnose_choices.py findings. Two repair classes:

  ADD     - the prose references a section the parser never turned into a
            choice. We add a choice whose text is the conditional clause that
            precedes "lapozz a N..." in the prose.
  RETARGET- the choice text is right but the target number is wrong (OCR
            misread the digits). We overwrite the target, matching choices to
            text references positionally.

Section 271 is left untouched: two-column OCR merged several sections into one
blob and it needs manual reconstruction from the PDF.

Dry run by default. Pass --apply to write sections.json.

Usage: python pipeline/repair_choices.py [--apply]
"""
import json, io, re, sys

APPLY = "--apply" in sys.argv
book = "a-demon-szeme"
path = f"books/{book}/sections.json"
d = json.load(io.open(path, encoding="utf-8"))
sections = d["sections"]

NAV = re.compile(
    r"(?:lapozz|menj|t[eé]rj|fordulj|ugorj|olvasd)\s+(?:el\s+)?"
    r"(?:a[zZ]?\s+)?(\d{1,3})",
    re.IGNORECASE,
)
# A nav line typically reads: "Ha <feltétel>, lapozz a 178-ra!"
LINE_NAV = re.compile(
    r"([^\n]*?)(?:lapozz|menj|t[eé]rj|fordulj|ugorj|olvasd)\s+(?:el\s+)?"
    r"(?:a[zZ]?\s+)?(\d{1,3})",
    re.IGNORECASE,
)

# sections needing a target rewrite instead of an added choice.
# {section_id: {wrong_target: correct_target}}
RETARGET = {
    "197": {144: 74, 212: 257},
}
SKIP = {"271"}  # corrupted two-column merge — manual PDF fix required


def text_refs(txt):
    return [int(m) for m in NAV.findall(txt)]


def choice_text_for(txt, target):
    """Find the conditional clause preceding 'lapozz a <target>' in the prose.

    Falls back to a clean generic label when the prose at that point is itself
    OCR-damaged (lowercase fragment, stray punctuation, mid-word start)."""
    fallback = f"Lapozz a {target}-re!"
    for m in LINE_NAV.finditer(txt):
        if int(m.group(2)) != target:
            continue
        clause = m.group(1)
        # keep only the tail after the last sentence break, tidy it
        clause = re.split(r"[.!?]\s+|\n", clause)[-1]
        clause = clause.lstrip(" \t[]§\"'.,;:!?")  # drop leading OCR cruft
        clause = clause.rstrip(" ,").strip()
        # accept only a clean conditional clause: starts capitalised, no obvious
        # OCR garbage. Otherwise use the generic label.
        if re.match(r"^(Ha|Amennyiben|Vagy)\b", clause):
            return clause
        return fallback
    return fallback


added, retargeted = [], []
for k in sorted(sections, key=int):
    if k in SKIP:
        continue
    v = sections[k]
    txt = v.get("text", "")
    choices = v.get("choices", [])
    tgts = [c["target"] for c in choices if c.get("target") is not None]

    if k in RETARGET:
        for c in choices:
            if c.get("target") in RETARGET[k]:
                old = c["target"]
                c["target"] = RETARGET[k][old]
                retargeted.append((k, old, c["target"], c.get("text", "")))
        continue

    refs = [r for r in text_refs(txt) if str(r) in sections]
    missing = [r for r in refs if r not in tgts]
    for tgt in missing:
        ctext = choice_text_for(txt, tgt)
        choices.append({"text": ctext, "target": tgt})
        added.append((k, tgt, ctext))
    if missing:
        v["choices"] = choices

print(f"=== repair_choices ({'APPLY' if APPLY else 'DRY RUN'}) ===\n")
print(f"ADD: {len(added)} new choices across "
      f"{len(set(a[0] for a in added))} sections")
for k, tgt, ctext in added:
    print(f"  sec {k:>3}  -> {tgt:>3}   text: {ctext!r}")
print(f"\nRETARGET: {len(retargeted)} choices")
for k, old, new, ctext in retargeted:
    print(f"  sec {k:>3}  {old} -> {new}   text: {ctext!r}")
print(f"\nSKIPPED (manual): {sorted(SKIP)}")

if APPLY:
    with io.open(path, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    print(f"\nWrote {path}")
else:
    print("\n(dry run — pass --apply to write)")

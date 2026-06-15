"""Diagnose choice/target mismatches in a book's sections.json.

For each section, extract every navigation reference embedded in the prose
("lapozz a 178-ra", "lapozz az 5-re", "vissza a 12-re", etc.) and compare it
against the parsed `choices[].target` list.

Reports:
  - MISSING: a section number referenced in the text that has no matching choice
  - EXTRA:   a choice target that is not referenced anywhere in the text
  - reachability before/after applying the missing links (what a repair would fix)

Read-only. No files are modified.

Usage: python pipeline/diagnose_choices.py [book-id]
"""
import json, io, re, sys
from collections import deque

book = sys.argv[1] if len(sys.argv) > 1 else "a-demon-szeme"
path = f"books/{book}/sections.json"
d = json.load(io.open(path, encoding="utf-8"))
sections = d["sections"]

# Hungarian nav phrases that introduce a section number. The suffix (-ra/-re/
# -ba/-be/-hoz/-ig/-nal etc.) follows vowel harmony, so just grab the number
# after the trigger word and an optional article.
NAV = re.compile(
    r"(?:lapozz|menj|t[eé]rj|fordulj|ugorj|olvasd)\s+(?:el\s+)?"
    r"(?:a[zZ]?\s+)?(\d{1,3})",
    re.IGNORECASE,
)


def text_refs(txt):
    return [int(m) for m in NAV.findall(txt)]


def choice_targets(v):
    return [c["target"] for c in v.get("choices", []) if c.get("target") is not None]


def reachable(adj, start="1"):
    seen = {start}
    q = deque([start])
    while q:
        n = q.popleft()
        for t in adj.get(n, ()):
            if t not in seen:
                seen.add(t)
                q.append(t)
    return seen


def build_adj(use_text_refs):
    adj = {}
    for k, v in sections.items():
        ts = set(str(t) for t in choice_targets(v))
        if use_text_refs:
            ts |= set(str(t) for t in text_refs(v.get("text", "")) if str(t) in sections)
        adj[k] = ts
    return adj


missing_total = []
extra_total = []
for k in sorted(sections, key=int):
    v = sections[k]
    refs = [r for r in text_refs(v.get("text", "")) if str(r) in sections]
    tgts = choice_targets(v)
    missing = [r for r in refs if r not in tgts]
    extra = [t for t in tgts if t not in refs]
    if missing:
        missing_total.append((k, missing, refs, tgts))
    if extra:
        extra_total.append((k, extra, refs, tgts))

print(f"=== {book}: choice/text reference diagnostic ===\n")
print(f"Sections with MISSING links (in text, not in choices): {len(missing_total)}")
for k, missing, refs, tgts in missing_total:
    print(f"  sec {k:>3}: missing {missing}  (text refs {refs} vs choice targets {tgts})")

print(f"\nSections with EXTRA choice targets (not in text): {len(extra_total)}")
for k, extra, refs, tgts in extra_total:
    print(f"  sec {k:>3}: extra {extra}  (text refs {refs} vs choice targets {tgts})")

before = reachable(build_adj(False))
after = reachable(build_adj(True))
unreach_before = sorted((set(sections) - before), key=int)
unreach_after = sorted((set(sections) - after), key=int)
print(f"\nReachable from sec 1 (choices only):       {len(before)}  unreachable: {unreach_before}")
print(f"Reachable if missing text-refs added:      {len(after)}  unreachable: {unreach_after}")
fixed = sorted((before ^ after), key=int)
print(f"Sections that become reachable after fix:  {fixed}")

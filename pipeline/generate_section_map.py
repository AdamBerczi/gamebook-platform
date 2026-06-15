"""
Generate section_map.json for a book.
Usage: python pipeline/generate_section_map.py [book-id]

Produces books/<book-id>/section_map.json with:
- Per-section reachability, type, incoming/outgoing edges
- Summary of issues: unreachable sections, dead ends, missing enemies, etc.
Useful for validating navigation logic and spotting data bugs.
"""
import json
import sys
import re
from collections import deque, defaultdict
from datetime import date

book_id = sys.argv[1] if len(sys.argv) > 1 else "magusok-tornya"

sections_path = f"books/{book_id}/sections.json"
with open(sections_path, encoding="utf-8") as f:
    data = json.load(f)

# Support both list and dict section formats
raw = data.get("sections", data)
if isinstance(raw, list):
    secs = {str(s["id"]): s for s in raw}
else:
    secs = raw  # already keyed by string id

# ── Build graph ──────────────────────────────────────────────────────────────
outgoing = defaultdict(list)   # int -> [int, ...]
incoming = defaultdict(list)   # int -> [int, ...]

for sid_str, s in secs.items():
    sid = int(sid_str)
    for c in s.get("choices", []):
        t = c.get("target")
        if isinstance(t, int):
            outgoing[sid].append(t)
            incoming[t].append(sid)
    # puzzle_fail_target is an implicit outgoing edge (shown when player gives up)
    pft = s.get("puzzle_fail_target")
    if isinstance(pft, int):
        outgoing[sid].append(pft)
        incoming[pft].append(sid)

# ── BFS reachability from section 1 ─────────────────────────────────────────
reachable = set()
queue = deque([1])
while queue:
    node = queue.popleft()
    if node in reachable:
        continue
    reachable.add(node)
    for t in outgoing.get(node, []):
        if t not in reachable:
            queue.append(t)

# ── Classify each section ────────────────────────────────────────────────────
DEATH_PHRASES = ["Kalandod véget ért", "kalandod véget ért", "véget ért!"]

def classify(sid, s):
    text = s.get("text", "")
    targets = [c["target"] for c in s.get("choices", []) if isinstance(c.get("target"), int)]
    is_ending = s.get("is_ending", False) or any(p in text for p in DEATH_PHRASES)
    has_puzzle = s.get("has_puzzle", False)
    has_return = s.get("has_return", False)
    has_chase  = s.get("has_chase",  False)

    flags = []
    if s.get("has_combat"):   flags.append("combat")
    if s.get("has_luck_test"): flags.append("luck_test")
    if s.get("has_shop"):     flags.append("shop")
    if has_puzzle:            flags.append("puzzle")
    if has_return:            flags.append("return")
    if has_chase:             flags.append("chase")
    if is_ending:             flags.append("ending")
    if not flags:             flags.append("normal")

    # Detect issues
    issues = []
    if sid not in reachable:
        issues.append("unreachable")
    if not incoming[sid] and sid != 1:
        issues.append("no_incoming_edges")
    # puzzle, return, and chase sections navigate dynamically — they're not dead ends
    if not targets and not is_ending and not has_puzzle and not has_return and not has_chase:
        issues.append("unexpected_dead_end")
    if not text.strip():
        issues.append("empty_text")
    if s.get("has_combat") and not s.get("enemies"):
        issues.append("combat_missing_enemy_stats")
    if len(targets) != len(set(targets)):
        issues.append("duplicate_choice_targets")
    # Dangling targets (point outside 1-300)
    total = int(data.get("total_sections", 300))
    bad = [t for t in targets if t < 1 or t > total]
    if bad:
        issues.append(f"out_of_range_targets:{bad}")

    return flags, issues, targets

section_map = {}
for sid_str, s in secs.items():
    sid = int(sid_str)
    flags, issues, targets = classify(sid, s)
    section_map[sid] = {
        "flags":      flags,
        "reachable":  sid in reachable,
        "choices":    targets,
        "incoming":   sorted(set(incoming[sid])),
        "issues":     issues,
    }
    # Attach enemies summary for combat sections
    if s.get("enemies"):
        section_map[sid]["enemies"] = [
            {"name": e.get("name"), "hp": e.get("eletero"), "damage": e.get("damage")}
            for e in s["enemies"]
        ]

# ── Summary ──────────────────────────────────────────────────────────────────
all_sids = sorted(section_map)
unreachable_sids  = [s for s in all_sids if not section_map[s]["reachable"]]
dead_end_sids     = [s for s in all_sids if "unexpected_dead_end" in section_map[s]["issues"]]
no_enemy_sids     = [s for s in all_sids if "combat_missing_enemy_stats" in section_map[s]["issues"]]
all_issue_sids    = [s for s in all_sids if section_map[s]["issues"]]

output = {
    "book_id":   book_id,
    "generated": str(date.today()),
    "summary": {
        "total_sections":      len(section_map),
        "reachable":           len(reachable),
        "unreachable":         len(unreachable_sids),
        "unexpected_dead_ends": len(dead_end_sids),
        "combat_missing_stats": len(no_enemy_sids),
        "sections_with_issues": len(all_issue_sids),
    },
    "issue_index": {
        "unreachable":             unreachable_sids,
        "unexpected_dead_ends":    dead_end_sids,
        "combat_missing_enemy_stats": no_enemy_sids,
        "all_sections_with_issues": {str(s): section_map[s]["issues"] for s in all_issue_sids},
    },
    "sections": {str(s): section_map[s] for s in all_sids},
}

out_path = f"books/{book_id}/section_map.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"Generated {out_path}")
print(f"  Total: {len(section_map)}  Reachable: {len(reachable)}  Unreachable: {len(unreachable_sids)}")
print(f"  Unexpected dead ends: {dead_end_sids}")
print(f"  Combat missing stats: {no_enemy_sids}")
if unreachable_sids:
    print(f"  Unreachable: {unreachable_sids}")

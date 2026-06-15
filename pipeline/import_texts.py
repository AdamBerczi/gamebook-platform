"""
Import edited sections_text.txt back into sections.json (text only) and rules.json (prologue).
Only fields that actually changed are updated; choices, events, enemies etc. are untouched.
Usage: python pipeline/import_texts.py [book-id]
"""
import json, re, sys

book_id = sys.argv[1] if len(sys.argv) > 1 else "a-demon-szeme"
src_path = f"books/{book_id}/sections_text.txt"

with open(src_path, encoding="utf-8") as f:
    content = f.read()

# Parse blocks: find each === NNN === header and extract text until the next header
header_re = re.compile(r'^=== (\d+).*?===$', re.MULTILINE)
matches = list(header_re.finditer(content))
blocks = {}
for i, m in enumerate(matches):
    sid_str = m.group(1)
    text_start = m.end()
    text_end   = matches[i + 1].start() if i + 1 < len(matches) else len(content)
    blocks[sid_str] = content[text_start:text_end].strip()

# Update rules.json prologue (block "000")
if "000" in blocks:
    rules_path = f"books/{book_id}/rules.json"
    with open(rules_path, encoding="utf-8") as f:
        rules = json.load(f)
    new_prologue = blocks.pop("000")
    if new_prologue != rules.get("prologue", ""):
        rules["prologue"] = new_prologue
        with open(rules_path, "w", encoding="utf-8") as f:
            json.dump(rules, f, ensure_ascii=False, indent=2)
        print("  Updated: prologue in rules.json")
    else:
        print("  Unchanged: prologue")

# Update sections.json text fields
sections_path = f"books/{book_id}/sections.json"
with open(sections_path, encoding="utf-8") as f:
    data = json.load(f)
raw = data.get("sections", data)
secs = {str(s["id"]): s for s in raw} if isinstance(raw, list) else raw

changed = 0
for sid_str, new_text in blocks.items():
    canonical = str(int(sid_str))  # strip leading zeros: "007" → "7"
    if canonical not in secs:
        print(f"  Warning: section {canonical} not found in sections.json")
        continue
    if new_text != secs[canonical].get("text", ""):
        secs[canonical]["text"] = new_text
        changed += 1

if changed:
    with open(sections_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  Updated: {changed} section texts in sections.json")
else:
    print("  Unchanged: all section texts")

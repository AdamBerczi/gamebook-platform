"""
Import edited .txt files back into sections.json (text field only) and rules.json (prologue).
Only sections whose text changed are updated; all other fields (choices, events, etc.) are untouched.
Usage: python pipeline/import_texts.py [book-id]
"""
import json, os, sys

book_id = sys.argv[1] if len(sys.argv) > 1 else "a-demon-szeme"
texts_dir = f"books/{book_id}/texts"

if not os.path.isdir(texts_dir):
    print(f"No texts directory found at {texts_dir}")
    print(f"Run: python pipeline/export_texts.py {book_id}")
    sys.exit(1)

# Import prologue into rules.json
prologue_path = f"{texts_dir}/000_elozmenyek.txt"
if os.path.exists(prologue_path):
    rules_path = f"books/{book_id}/rules.json"
    with open(rules_path, encoding="utf-8") as f:
        rules = json.load(f)
    with open(prologue_path, encoding="utf-8") as f:
        new_prologue = f.read()
    if new_prologue != rules.get("prologue", ""):
        rules["prologue"] = new_prologue
        with open(rules_path, "w", encoding="utf-8") as f:
            json.dump(rules, f, ensure_ascii=False, indent=2)
        print("  Updated: prologue in rules.json")
    else:
        print("  Unchanged: prologue")

# Import section texts into sections.json
sections_path = f"books/{book_id}/sections.json"
with open(sections_path, encoding="utf-8") as f:
    data = json.load(f)
raw = data.get("sections", data)
secs = {str(s["id"]): s for s in raw} if isinstance(raw, list) else raw

changed = 0
missing = []
for fname in sorted(f for f in os.listdir(texts_dir) if f.endswith(".txt") and f != "000_elozmenyek.txt"):
    sid_str = str(int(fname.replace(".txt", "")))  # "007" → "7"
    if sid_str not in secs:
        missing.append(fname)
        continue
    with open(f"{texts_dir}/{fname}", encoding="utf-8") as f:
        new_text = f.read()
    if new_text != secs[sid_str].get("text", ""):
        secs[sid_str]["text"] = new_text
        changed += 1

if changed:
    with open(sections_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  Updated: {changed} section texts in sections.json")
else:
    print("  Unchanged: all section texts")

if missing:
    print(f"  Warning: {len(missing)} .txt files had no matching section: {missing}")

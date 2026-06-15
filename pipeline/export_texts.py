"""
Export section texts + prologue to individual .txt files for manual review and editing.
Usage: python pipeline/export_texts.py [book-id]

Creates:
  books/<book-id>/texts/000_elozmenyek.txt  ← prologue from rules.json
  books/<book-id>/texts/001.txt ... 300.txt ← section text from sections.json

Edit any file, then run import_texts.py to write changes back.
"""
import json, os, sys

book_id = sys.argv[1] if len(sys.argv) > 1 else "a-demon-szeme"
texts_dir = f"books/{book_id}/texts"
os.makedirs(texts_dir, exist_ok=True)

# Export prologue from rules.json
rules_path = f"books/{book_id}/rules.json"
with open(rules_path, encoding="utf-8") as f:
    rules = json.load(f)
prologue = rules.get("prologue", "")
prologue_path = f"{texts_dir}/000_elozmenyek.txt"
with open(prologue_path, "w", encoding="utf-8") as f:
    f.write(prologue)

# Export section texts
sections_path = f"books/{book_id}/sections.json"
with open(sections_path, encoding="utf-8") as f:
    data = json.load(f)
raw = data.get("sections", data)
secs = {str(s["id"]): s for s in raw} if isinstance(raw, list) else raw

count = 0
for sid_str, sec in sorted(secs.items(), key=lambda x: int(x[0])):
    sid = int(sid_str)
    text = sec.get("text", "")
    out_path = f"{texts_dir}/{sid:03d}.txt"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)
    count += 1

print(f"Exported {count} sections + prologue to {texts_dir}/")
print(f"Edit any .txt file, then run: python pipeline/import_texts.py {book_id}")

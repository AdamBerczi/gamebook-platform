"""
Export all section texts + prologue to a single editable text file.
Usage: python pipeline/export_texts.py [book-id]

Creates books/<book-id>/sections_text.txt with format:
  === 000 ELŐZMÉNYEK ===
  [prologue text]

  === 001 ===
  [section 1 text]

  === 002 ===
  ...

Edit the file freely, then run import_texts.py to write changes back.
Only the text inside each block is imported; section headers are delimiters only.
"""
import json, sys

book_id = sys.argv[1] if len(sys.argv) > 1 else "a-demon-szeme"
out_path = f"books/{book_id}/sections_text.txt"

with open(f"books/{book_id}/rules.json", encoding="utf-8") as f:
    rules = json.load(f)
with open(f"books/{book_id}/sections.json", encoding="utf-8") as f:
    data = json.load(f)

raw = data.get("sections", data)
secs = {str(s["id"]): s for s in raw} if isinstance(raw, list) else raw

lines = []

prologue = rules.get("prologue", "")
lines.append("=== 000 ELŐZMÉNYEK ===")
lines.append(prologue)
lines.append("")

for sid_str, sec in sorted(secs.items(), key=lambda x: int(x[0])):
    sid = int(sid_str)
    lines.append(f"=== {sid:03d} ===")
    lines.append(sec.get("text", ""))
    lines.append("")

with open(out_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"Exported {len(secs)} sections + prologue to {out_path}")
print(f"Edit the file, then run: python pipeline/import_texts.py {book_id}")

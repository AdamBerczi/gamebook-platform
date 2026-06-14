"""
07_extract_events.py

Use Claude Haiku to extract structured game events from each section's text.
Events capture mechanics beyond basic combat/choices:
  - Pre-combat damage to player ("veszítesz 7 életerőpontot")
  - Combat special rules (regeneration, multi-attack, stat drain, no-flee)
  - Automatic stat changes on enter (fall damage, curses)
  - Automatic item gain/loss (not from choices)
  - Gold transactions
  - Rest/sleep that restores stats

Output added to sections.json under each section's "events" key.

Usage:
  python pipeline/07_extract_events.py a-demon-szeme
"""

import json
import sys
import time
from pathlib import Path

import anthropic

SYSTEM_PROMPT = """You extract structured game events from Hungarian gamebook section text.

Return ONLY a JSON array. Use [] if there are no special events beyond basic combat.

─── EVENT KINDS ───────────────────────────────────────────────────────────────

STAT_CHANGE — automatic stat change when entering the section (not in combat):
{"kind":"STAT_CHANGE","stat":"eletero","amount":-7,"timing":"on_enter","reason":"fall"}
{"kind":"STAT_CHANGE","stat":"eletero","formula":"-1d6","timing":"on_enter","reason":"fall"}
- stat: eletero | tamadasi_kepesseg | vedettsegi_szint | szerencse | varazserő
- amount: negative = loss, positive = gain; use formula instead for dice rolls
- formula: e.g. "-1d6" means roll d6 and subtract that many HP
- timing: "on_enter" (default) | "on_combat_win"

COMBAT — special rules beyond basic attack/defend:
{"kind":"COMBAT","special_rules":[...]}
Special rule objects:
  {"type":"enemy_regenerate","target":"EnemyName","amount":2}
    — enemy heals N HP after every attack the player makes against it
  {"type":"multi_attack","target":"EnemyName","count":2}
    — enemy attacks N times per round instead of once
  {"type":"stat_drain","target":"EnemyName","stat":"tamadasi_kepesseg","amount":1}
    — each successful enemy hit permanently reduces the player's stat by N
  {"type":"player_pre_damage","stat":"eletero","amount":-7,"reason":"knocked down"}
    — player takes fixed damage BEFORE combat begins (part of combat setup)
  {"type":"player_pre_damage","stat":"eletero","formula":"-1d6","reason":"..."}
    — player takes rolled damage before combat
  {"type":"no_flee"}
    — player cannot flee this combat

ITEM_GAIN — player automatically receives items (NOT via choice):
{"kind":"ITEM_GAIN","items":[{"name":"Kulcs","note":"arany kulcs"}],"timing":"on_enter"}
- timing: "on_enter" | "on_combat_win"

ITEM_LOSE — player automatically loses items (toll, consumed, stolen):
{"kind":"ITEM_LOSE","items":["item name"],"timing":"on_enter"}

GOLD_CHANGE — automatic gold gain or loss:
{"kind":"GOLD_CHANGE","amount":20,"timing":"on_enter"}
- positive = gain, negative = loss

REST — sleeping or resting that restores stats:
{"kind":"REST","restores":["varazserő","szerencse"]}

─── RULES ──────────────────────────────────────────────────────────────────────

1. ONLY include AUTOMATIC effects, not choice-dependent ones.
   If something only happens on ONE specific choice branch → skip it.
   If something is conditional on having an item → skip it.

2. Do NOT repeat what's already in the "enemies" or "choices" fields.
   Basic combat (attack/defend) is already handled — only extract EXCEPTIONS.

3. A COMBAT event is only needed if there are special_rules.
   If combat is standard, return [] (not a bare COMBAT event).

4. Be conservative: if the text is ambiguous → omit rather than guess.

5. Section text may be garbled Hungarian OCR — do your best with context."""


def build_user_message(section):
    payload = {
        "text": section.get("text", "").strip(),
        "has_combat": section.get("has_combat", False),
        "is_ending": section.get("is_ending", False),
        "enemies": [
            {"name": e.get("name"), "damage": e.get("damage")}
            for e in section.get("enemies", [])
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def extract_events(client, section):
    text = section.get("text", "").strip()
    if not text:
        return []

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_user_message(section)}],
    )

    raw = response.content[0].text.strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(lines[1:])
    raw = raw.rstrip("`").strip()

    try:
        events = json.loads(raw)
        if not isinstance(events, list):
            print(f"    WARN: got non-list: {raw[:80]}")
            return []
        return events
    except json.JSONDecodeError as e:
        print(f"    WARN: JSON parse error ({e}): {raw[:120]}")
        return []


def extract_all_events(book_id):
    root = Path(__file__).parent.parent
    book_dir = root / "books" / book_id
    sections_path = book_dir / "sections.json"

    with open(sections_path, encoding="utf-8") as f:
        data = json.load(f)

    sections = data["sections"]
    total = len(sections)
    already_done = sum(1 for s in sections.values() if "events" in s)
    to_process = total - already_done

    print(f"Book '{book_id}': {total} sections, {already_done} already done, {to_process} to process")
    if to_process == 0:
        print("All sections already have events. Done.")
        return

    client = anthropic.Anthropic()
    processed = 0
    non_empty = 0

    for sid, section in sorted(sections.items(), key=lambda x: int(x[0])):
        if "events" in section:
            continue

        events = extract_events(client, section)
        section["events"] = events
        processed += 1

        if events:
            non_empty += 1
            kinds = [e.get("kind", "?") for e in events]
            print(f"  Sec {sid:3}: {kinds}")
        else:
            # Overwrite the same line for quiet sections
            print(f"  Sec {sid:3}: []", end="\r")

        # Checkpoint every 20 sections
        if processed % 20 == 0:
            with open(sections_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"\n  -- checkpoint: {processed}/{to_process} processed --")

        time.sleep(0.05)   # gentle throttle

    # Final save
    with open(sections_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\nDone. {processed} processed, {non_empty} had events.")


if __name__ == "__main__":
    book_id = sys.argv[1] if len(sys.argv) > 1 else "a-demon-szeme"
    extract_all_events(book_id)

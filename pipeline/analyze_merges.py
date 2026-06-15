"""
Automated merge-detection pass for A Démon Szeme sections 36-300.
Flags: too-many-choices, is_ending+choices, has_combat+no-enemies,
empty events, "Kalandod véget ért!" buried in text, duplicate targets,
choice-navigation text embedded in body mid-sentence.
"""
import json, re, sys

with open('books/a-demon-szeme/sections.json', encoding='utf-8') as f:
    data = json.load(f)
secs = data['sections']

DEATH = 'Kalandod véget ért'
NAV   = re.compile(r'lapozz (a |az )?\d+', re.IGNORECASE)

results = {}

for sid_str, s in secs.items():
    sid = int(sid_str)
    if sid < 36:
        continue

    text     = s.get('text', '')
    choices  = s.get('choices', [])
    events   = s.get('events', [])
    enemies  = s.get('enemies', [])
    targets  = [c['target'] for c in choices]
    flags    = []

    # ── Hard red flags ──────────────────────────────────────────────────────
    if s.get('is_ending') and choices:
        flags.append('ENDING_WITH_CHOICES')

    if s.get('has_combat') and not enemies:
        flags.append('COMBAT_NO_ENEMIES')

    for ev in events:
        if ev.get('kind') == 'STAT_CHANGE':
            if not ev.get('formula') and not ev.get('amount'):
                flags.append('STAT_CHANGE_EMPTY')
                break

    if len(set(targets)) < len(targets):
        flags.append('DUPLICATE_TARGETS')

    # ── Death phrase buried in non-ending section ────────────────────────────
    if DEATH in text and not s.get('is_ending'):
        flags.append('DEATH_IN_TEXT')

    # ── Choice count anomalies ───────────────────────────────────────────────
    if len(choices) > 4:
        flags.append(f'MANY_CHOICES_{len(choices)}')
    elif len(choices) == 4 and not s.get('has_shop'):
        flags.append('CHOICES_4')

    # ── Kalandod véget ért in text AND has choices (merge) ──────────────────
    if DEATH in text and choices:
        flags.append('DEATH_AND_CHOICES')

    if flags:
        results[sid] = {
            'flags': flags,
            'choices': targets,
            'has_combat': s.get('has_combat'),
            'is_ending': s.get('is_ending'),
            'enemies': [(e.get('name'), e.get('eletero')) for e in enemies],
            'events': [(e['kind'], e.get('stat',''), e.get('amount',''), e.get('formula','')) for e in events],
            'text_head': text[:200].replace('\n', ' '),
        }

# Print report
print(f'Flagged sections (36-300): {len(results)}\n')
for sid in sorted(results):
    r = results[sid]
    print(f'=== Sec {sid} | {" | ".join(r["flags"])} ===')
    print(f'  choices : {r["choices"]}')
    if r['enemies']:   print(f'  enemies : {r["enemies"]}')
    if r['events']:    print(f'  events  : {r["events"]}')
    print(f'  text    : {r["text_head"]}')
    print()

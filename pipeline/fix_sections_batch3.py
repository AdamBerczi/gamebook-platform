"""
Batch fix for A Démon Szeme sections 36-300.
Fixes OCR merge artifacts, wrong flags, missing enemy stats, duplicate choices.
"""
import json, re

with open('books/a-demon-szeme/sections.json', encoding='utf-8') as f:
    data = json.load(f)
s = data['sections']

def ch(targets):
    return [{'target': t} for t in targets]

# ─────────────────────────────────────────────────────────────────────────────
# A) Clear has_combat flag where no actual combat exists
# ─────────────────────────────────────────────────────────────────────────────
no_combat = [
    '62',   # xinaf gives headband — item gain
    '63',   # resting while fighting noises fade
    '66',   # artifact dialogue (puzzle choices)
    '67',   # artifact dialogue (same as 66)
    '79',   # xinaf transformation after spell — conversation
    '107',  # post-combat victory aftermath
    '110',  # fled, took 1 HP hit, now face monster at sec 5
    '122',  # resting/camping choices
    '138',  # black knight death ending (is_ending=True already)
    '171',  # xinaf transformation — duplicate of 79
    '172',  # looting dead body — item gain
    '173',  # not enough MP, explaining to alien
    '183',  # csontvázharcos post-combat — item gain
    '193',  # cliff climbing — nav section
    '209',  # Élőhalott öregember — enemy will be added below
    '224',  # sleeping/waking up in hut — no combat
    '239',  # desert luck test — will get has_luck_test
    '242',  # post-combat (black knight dead) — item loot
    '255',  # parchment vitrine — explore choices
    '260',  # not enough MP, explaining to alien
    '271',  # book-drain dice roll — STAT_CHANGE event handles it
    '279',  # acid wall (2 HP + perm TK-1) — no combat
]
for sid in no_combat:
    s[sid]['has_combat'] = False

# ─────────────────────────────────────────────────────────────────────────────
# B) Luck test sections (clear has_combat, set has_luck_test, fix choices)
# ─────────────────────────────────────────────────────────────────────────────
s['61']['has_combat'] = False   # already has has_luck_test=True from prior session
s['158']['has_combat'] = False
s['158']['has_luck_test'] = True
s['158']['choices'] = ch([205, 120])   # success=205, failure=120

s['210']['has_combat'] = False
s['210']['has_luck_test'] = True
# choices [271, 87] already correct — success=271, failure=87

s['239']['has_luck_test'] = True
# choices [290, 127] already correct — success=290, failure=127

# ─────────────────────────────────────────────────────────────────────────────
# C) Death endings — truncate merged text, clear choices
# ─────────────────────────────────────────────────────────────────────────────
DEATH = 'Kalandod véget ért'

def truncate_at_death(sec):
    text = sec.get('text', '')
    idx = text.find(DEATH)
    if idx >= 0:
        excl = text.find('!', idx + len(DEATH))
        if excl >= 0:
            sec['text'] = text[:excl+1].strip()
    sec['choices'] = []
    sec['is_ending'] = True

# Death sections with merged choice blocks after them
for sid in ['68', '75', '82', '87', '120', '140', '152', '191',
            '201', '245', '252', '270', '297']:
    truncate_at_death(s[sid])

# Clear has_combat from death sections where it crept in from merge
for sid in ['82', '87', '191']:
    s[sid]['has_combat'] = False

# Sec 120: remove STAT_CHANGE with amount=0 (AI extraction error)
s['120']['events'] = [
    e for e in s['120'].get('events', [])
    if not (e.get('kind') == 'STAT_CHANGE' and e.get('amount') == 0 and not e.get('formula'))
]
# Sec 140: same — empty varazserő change
s['140']['events'] = [
    e for e in s['140'].get('events', [])
    if not (e.get('kind') == 'STAT_CHANGE' and e.get('amount') == 0 and not e.get('formula'))
]
# Sec 252: remove -999 HP event (old cursedMask hack)
s['252']['events'] = [
    e for e in s['252'].get('events', [])
    if not (e.get('kind') == 'STAT_CHANGE' and e.get('amount') == -999)
]
# Sec 270: same — remove -999 HP event
s['270']['events'] = [
    e for e in s['270'].get('events', [])
    if not (e.get('kind') == 'STAT_CHANGE' and e.get('amount') == -999)
]

# ─────────────────────────────────────────────────────────────────────────────
# D) Sections wrongly marked is_ending=True
# ─────────────────────────────────────────────────────────────────────────────
# Sec 144: first visit to cliff face — has real choices [28, 85]
s['144']['is_ending'] = False
# choices [28, 85] already correct

# Sec 179: examining coffin mechanism — has real choices
s['179']['is_ending'] = False
s['179']['choices'] = ch([217, 281, 219])  # mechanism, examine dead, too scared

# Sec 187: Fekete lovag combat — is a real combat section (not a death)
s['187']['is_ending'] = False
# (enemy stats added below in Group F)

# Sec 222: searching for tracks — not a death, merged text caused wrong flag
s['222']['is_ending'] = False
s['222']['has_combat'] = False
s['222']['choices'] = ch([72, 32, 134])

# Sec 276: alien shapeshifter dialogue — continues after tying up alien
s['276']['is_ending'] = False
# choices [251, 161, 56] already correct

# ─────────────────────────────────────────────────────────────────────────────
# E) Fix excess / wrong choices from merge artifacts
# ─────────────────────────────────────────────────────────────────────────────
s['36']['choices']  = ch([58, 121, 146])       # cave hub: remove merged mask section
s['40']['choices']  = ch([116, 221])            # flag-conditional: remove dying-xinaf merge
s['51']['choices']  = ch([105, 276])            # Alakváltó combat: win/lose only
s['55']['choices']  = ch([21, 115])             # bookcase/chest puzzle: remove nav hub merge
s['55']['events']   = [                         # remove spurious varazserő=0 STAT_CHANGE
    e for e in s['55'].get('events', [])
    if not (e.get('kind') == 'STAT_CHANGE' and e.get('amount') == 0 and not e.get('formula'))
]
s['66']['choices']  = ch([235, 156, 11, 180])  # remove duplicate 180
s['78']['choices']  = ch([109, 203, 261])       # statue hub: remove merged xinaf text
s['78']['has_combat'] = False
s['94']['choices']  = ch([197])                 # cliff descent: only one choice (river)
s['96']['choices']  = ch([234, 140])            # FOLYÓ puzzle: have necklace or not
s['104']['choices'] = ch([91, 132])             # forest rest stop: hut or woodland
s['114']['choices'] = ch([265, 191])            # Pikkelyes rém combat: win/lose
s['118']['choices'] = ch([52, 104])             # navigation hub: deduplicate 104
s['122']['choices'] = ch([48, 233, 170])        # camping: deduplicate 170
s['123']['choices'] = ch([218, 190, 169])       # dining room: remove extra 190s
s['124']['choices'] = ch([190])                 # TÜKÖR puzzle: all routes → 190
s['146']['choices'] = ch([97])                  # forest trail: both options → 97
s['147']['choices'] = ch([255, 44, 299])        # mummy room: remove parse artifact 204
s['162']['choices'] = ch([251, 56])             # xinaf dialogue: remove ground-floor merge
s['163']['choices'] = ch([281, 179])            # old man in coffin: search/examine only
s['183']['has_combat'] = False
s['183']['events']  = [                         # remove spurious VS-6 event
    e for e in s['183'].get('events', [])
    if not (e.get('kind') == 'STAT_CHANGE' and e.get('stat') == 'vedettsegi_szint')
]
s['189']['choices'] = ch([36])                  # fell back: only choice is 36
s['209']['choices'] = ch([194, 90])             # öregember combat: deduplicate 90
s['218']['choices'] = ch([23, 169])             # broken dining room: remove merged section
s['248']['choices'] = ch([52, 202, 104])        # nav hub: deduplicate 104
s['249']['choices'] = ch([100, 49])             # Amorf fight: win/lose; remove old-man merge
s['255']['choices'] = ch([69, 44, 299])         # parchment room: remove merged choices
s['264']['choices'] = ch([67, 297])             # wrong-answer spider: win/lose; remove puzzle merge
s['271']['choices'] = ch([87, 169])             # book-drain: died→87, survived→169
s['272']['choices'] = ch([194, 90])             # öregember combat: win/lose; strip massive merge
s['277']['choices'] = ch([37, 101])             # double-bottom chest: put on mask or pocket
s['285']['choices'] = ch([67, 103])             # cautious spider: win/lose; strip alien merge

# ─────────────────────────────────────────────────────────────────────────────
# F) Add missing enemy stats (combat text was in section but enemies[] was empty)
# ─────────────────────────────────────────────────────────────────────────────

# Alakváltó (shapeshifter) — secs 51 and 195
# Stats from text: ÉL 28, TK 18, VS 18, damage 3-8; regenerates 2 HP/hit
alakvalto = {
    'name': 'Alakváltó',
    'eletero': 28,
    'tamadasi_kepesseg': 18,
    'vedettsegi_szint': 18,
    'damage': '3-8'
}
s['51']['enemies'] = [alakvalto]
# Strip merged tail from sec 51 text (after "lapozz a 276-ra!")
text51 = s['51']['text']
cutoff = text51.find('276-ra!')
if cutoff >= 0:
    s['51']['text'] = text51[:cutoff + len('276-ra!')].strip()
# Add/update COMBAT event with enemy_regenerate
evs51 = [e for e in s['51'].get('events', []) if e.get('kind') != 'COMBAT']
evs51.append({'kind': 'COMBAT', 'special_rules': [{'type': 'enemy_regenerate', 'amount': 2}]})
s['51']['events'] = evs51

s['195']['enemies'] = [alakvalto]
# Sec 195 already has COMBAT event — update its special_rules
updated = False
for e in s['195'].get('events', []):
    if e.get('kind') == 'COMBAT':
        e['special_rules'] = [{'type': 'enemy_regenerate', 'amount': 2}]
        updated = True
        break
if not updated:
    s['195'].setdefault('events', []).append(
        {'kind': 'COMBAT', 'special_rules': [{'type': 'enemy_regenerate', 'amount': 2}]}
    )

# Fekete lovag (black knight) — sec 187
# Stats from text: ÉL 38, TK 22, VS 25, damage 2-12; stat_drain TK-1 per hit
fekete_lovag = {
    'name': 'Fekete lovag',
    'eletero': 38,
    'tamadasi_kepesseg': 22,
    'vedettsegi_szint': 25,
    'damage': '2-12'
}
s['187']['enemies'] = [fekete_lovag]
# Make on_enter STAT_CHANGEs permanent (ambush damage)
for e in s['187'].get('events', []):
    if e.get('kind') == 'STAT_CHANGE':
        e['permanent'] = True
        if 'timing' not in e:
            e['timing'] = 'on_enter'
# Replace/add COMBAT event with stat_drain
s['187']['events'] = [e for e in s['187']['events'] if e.get('kind') != 'COMBAT']
s['187']['events'].append({
    'kind': 'COMBAT',
    'special_rules': [{'type': 'stat_drain', 'stat': 'tamadasi_kepesseg', 'amount': 1}]
})
# Strip merged Ayrabdir death text after "lapozz a 82-re!"
text187 = s['187']['text']
cutoff187 = text187.find('82-re!')
if cutoff187 >= 0:
    s['187']['text'] = text187[:cutoff187 + len('82-re!')].strip()

# Élőhalott öregember (undead elder) — sec 209
# Same stats as sec 86: ÉL 30, TK 17, VS 22, damage 1-3; also casts spells
elohalt = {
    'name': 'Élőhalott öregember',
    'eletero': 30,
    'tamadasi_kepesseg': 17,
    'vedettsegi_szint': 22,
    'damage': '1-3'
}
s['209']['enemies'] = [elohalt]

# Ayrabdir (night creature) — sec 259
# Stats from text: ÉL 18, TK 12, VS 17, damage 2-7
ayrabdir = {
    'name': 'Ayrabdir',
    'eletero': 18,
    'tamadasi_kepesseg': 12,
    'vedettsegi_szint': 17,
    'damage': '2-7'
}
s['259']['enemies'] = [ayrabdir]

# Óriáspók (giant spider) — secs 264 and 285
# Stats from text: ÉL 22, TK 16, VS 20, damage 1-6
oriaspok = {
    'name': 'Óriáspók',
    'eletero': 22,
    'tamadasi_kepesseg': 16,
    'vedettsegi_szint': 20,
    'damage': '1-6'
}
s['264']['enemies'] = [oriaspok]
s['285']['enemies'] = [oriaspok]
# Strip merged alien+puzzle text from sec 264 after "lapozz a 297-re!"
text264 = s['264']['text']
cut264 = text264.find('297-re!')
if cut264 >= 0:
    s['264']['text'] = text264[:cut264 + len('297-re!')].strip()
# Strip merged alien text from sec 285 after "lapozz a 103-ra!"
text285 = s['285']['text']
cut285 = text285.find('103-ra!')
if cut285 >= 0:
    s['285']['text'] = text285[:cut285 + len('103-ra!')].strip()

# ─────────────────────────────────────────────────────────────────────────────
# Save
# ─────────────────────────────────────────────────────────────────────────────
with open('books/a-demon-szeme/sections.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

# ─────────────────────────────────────────────────────────────────────────────
# Verification summary
# ─────────────────────────────────────────────────────────────────────────────
print('=== Batch 3 fix summary ===')
verify = {
    '36':  ('choices', [58, 121, 146]),
    '40':  ('choices', [116, 221]),
    '51':  ('enemies+choices', None),
    '55':  ('choices', [21, 115]),
    '61':  ('has_luck_test', True),
    '66':  ('choices', [235, 156, 11, 180]),
    '68':  ('is_ending+choices', None),
    '82':  ('is_ending+choices', None),
    '87':  ('is_ending+choices', None),
    '94':  ('choices', [197]),
    '96':  ('choices', [234, 140]),
    '104': ('choices', [91, 132]),
    '114': ('choices', [265, 191]),
    '118': ('choices', [52, 104]),
    '120': ('is_ending+choices', None),
    '122': ('choices', [48, 233, 170]),
    '123': ('choices', [218, 190, 169]),
    '124': ('choices', [190]),
    '140': ('is_ending+choices', None),
    '144': ('is_ending=False', None),
    '146': ('choices', [97]),
    '147': ('choices', [255, 44, 299]),
    '152': ('is_ending+choices', None),
    '158': ('has_luck_test+choices', None),
    '162': ('choices', [251, 56]),
    '163': ('choices', [281, 179]),
    '187': ('enemies+is_ending=F', None),
    '189': ('choices', [36]),
    '191': ('is_ending+choices', None),
    '195': ('enemies', None),
    '201': ('is_ending+choices', None),
    '209': ('enemies+choices', None),
    '210': ('has_luck_test', True),
    '218': ('choices', [23, 169]),
    '222': ('is_ending=F+choices', None),
    '239': ('has_luck_test', True),
    '245': ('is_ending+choices', None),
    '248': ('choices', [52, 202, 104]),
    '249': ('choices', [100, 49]),
    '252': ('is_ending+choices', None),
    '255': ('choices', [69, 44, 299]),
    '259': ('enemies', None),
    '264': ('enemies+choices', None),
    '270': ('is_ending+choices', None),
    '271': ('choices', [87, 169]),
    '272': ('choices', [194, 90]),
    '276': ('is_ending=False', None),
    '277': ('choices', [37, 101]),
    '285': ('enemies+choices', None),
    '297': ('is_ending+choices', None),
}
for sid, (label, expected) in sorted(verify.items(), key=lambda x: int(x[0])):
    sec = data['sections'][sid]
    ch_actual = [c['target'] for c in sec.get('choices', [])]
    end = sec.get('is_ending', False)
    lt = sec.get('has_luck_test', False)
    en = [(e.get('name'), e.get('eletero')) for e in sec.get('enemies', [])]
    print(f"  Sec {sid:>3} [{label}]: choices={ch_actual} ending={end} luck={lt} enemies={en}")
print('\nDone.')

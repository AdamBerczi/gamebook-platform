# Gamebook Platform — Project Memory

A reusable platform for playing Hungarian "Harcos Képzelet" gamebooks in a web browser.
Designed for personal use and as a learning project. Built step by step — ask before large decisions.

---

## Project Goals

- Personal use + learning Claude / vibe coding
- Reusable pipeline: drop in a new PDF → OCR it → play it in browser
- MVP first: playable game, no images, no fancy features
- Clean architecture — 30-40 books may eventually be added

---

## Books

**Mágusok Tornya** (vol. 22) — Jonathan Graves, 1997
- 300 numbered sections (all 300 present)
- Stats: Életerő, Támadási képesség, Védettségi szint, Szerencse, Varázserő
- Race system: Ember (baseline), Felfödi ember, Óriás, Manó, Tünder
- 11 attack spells, 12 defense spells; 16-entry weapon damage table

**A Démon Szeme** (vol. 23) — Anthony Parker, 1998
- 300 numbered sections (all 300 recovered — 06_recover_sections.py + manual patches)
- Same 5 stats, different races: Ember, Barbár, Oggun, Ork, Tündér
- No spell system; different damage table entries
- Two-column OCR layout caused many sections to be merged/dropped — fixed with custom recovery pipeline
- `pipeline/06_recover_sections.py` — splits merged OCR blocks using nav-choice cluster detection
- `pipeline/patch_missing_sections.py` — manually patches 6 sections from screenshots (41, 42, 83, 89, 225, 257)
- `pipeline/07_extract_events.py` — uses Claude Haiku to extract structured events from each section

---

## Project Structure

```
/gamebook-platform
  /pipeline
    01_pdf_to_images.py       ← PDF → PNG pages
    02_ocr_pages.py           ← PNG → raw text (Claude Vision)
    03_parse_sections.py      ← raw text → sections.json (generic)
    04_clean_text.py          ← Hungarian spellcheck pass (Claude Haiku)
    05_correct_sections.py    ← OCR correction pass (Claude Sonnet)
    06_recover_sections.py    ← two-column OCR gap recovery (a-demon-szeme specific)
    07_extract_events.py      ← structured events extraction (Claude Haiku)
    patch_missing_sections.py ← manual patch of 6 OCR-absent sections
  /books
    index.json                ← multi-book manifest
    /magusok-tornya
      sections.json, rules.json, cover.png, parse_config.json
    /a-demon-szeme
      sections.json, rules.json, cover.png, parse_config.json
  index.html       ← single-page app shell (all screens + modals)
  game.js          ← all game logic
  style.css        ← all styles
  manifest.json, icon-192.png, icon-512.png  ← PWA
  CLAUDE.md        ← this file
```

---

## Tech Stack

- **Python** — OCR pipeline scripts
- **Vanilla HTML/JS/CSS** — frontend (no framework)
- **JSON** — data format between pipeline and frontend
- **Claude Vision API** (`claude-haiku-4-5-20251001`) — OCR of scanned pages
- **Claude Sonnet API** (`claude-sonnet-4-6`) — Hungarian OCR correction pass (pipeline/05)
- **PWA** — installable on iOS home screen
- **localStorage** — save/load game slots (key: `hk_saves`, max 10 slots)
- **Cloudflare Pages** — hosting (repo root = site root, no build step)

### Python libraries
- `pymupdf` (fitz) — renders PDF pages to PNG
- `anthropic` — Claude API client
- `Pillow` — generates PWA icons and book cover art

### Environment
- Windows 11, PowerShell
- `ANTHROPIC_API_KEY` set in both Windows User environment variables AND `C:\Users\adamb\.claude\settings.json`
- The settings.json entry means Claude Code sessions can run API scripts directly (no fresh terminal needed)

---

## User Background

- Basic Python and C from years ago, learning fast
- Wants explanations of decisions, not just generated code
- Step-by-step approach preferred

---

## How to Run Locally

```powershell
cd D:\Code\gamebook-platform
python -m http.server 8000
# then open http://localhost:8000/
```

## Hosting (Cloudflare Pages)

- Repo root is the site root — `index.html` is at `/`
- No build step: output directory = `/`
- Two emails allowlisted in Cloudflare Access
- After any code change: `git push` → Cloudflare auto-deploys

---

## Pipeline Scripts (run in order for a new book)

```powershell
python pipeline\01_pdf_to_images.py [book-id]    # PDF → PNG pages
python pipeline\02_ocr_pages.py     [book-id]    # PNG → raw text (Claude Vision)
python pipeline\04_clean_text.py    [book-id]    # raw text → cleaned text (Claude Haiku)
python pipeline\03_parse_sections.py [book-id]   # cleaned text → sections.json
python pipeline\05_correct_sections.py [book-id] # sections.json → OCR-corrected (Claude Sonnet)
python pipeline\07_extract_events.py [book-id]   # adds events array to all sections (Claude Haiku)
```

All scripts default to `magusok-tornya` if no book ID given. All are resumable (skip already-done work).

Scripts 05 and 07 require `ANTHROPIC_API_KEY` and must run from a **fresh terminal** (not Claude Code session).

For two-column OCR books like a-demon-szeme, also run:
```powershell
python pipeline\06_recover_sections.py a-demon-szeme   # recovers sections from merged OCR gaps
python pipeline\patch_missing_sections.py               # applies hard-coded patches from screenshots
```

---

## GitHub

Repository: https://github.com/AdamBerczi/gamebook-platform

`sections.json` and `rules.json` **are** committed so anyone can clone and play without running the pipeline.

PDF, raw pages, OCR text are **gitignored** (copyright + regeneratable).

---

## Features Implemented

### Frontend
- **Main menu**: book grid loaded from `books/index.json`; shows cover art, series/volume, description; click to load book
- **Character creation**: race selection grid + stat rolling; ← Vissza returns to menu; book title/author shown dynamically
- Prologue screen ("Előzmények") between character creation and section 1
- Game screen: sidebar (desktop) + collapsible drawer (mobile)
- Sidebar: HP/MP bars, all 5 stats, inventory list, race badge, new game button
- Mobile: sticky HP in topbar, slide-up stats drawer
- PWA manifest + tower icons (icon-192.png, icon-512.png) for iOS home screen

### Spellbook viewer
- Sidebar button opens modal with Támadó / Védő tabs
- Each spell shows: name, VE cost (badge), damage, full description
- Unaffordable spells are dimmed (opacity) based on current varázserő

### Spell selection (combat)
- In combat, clicking ✦ Varázslat shows a scrollable spell picker list
- All 11 attack spells shown; unaffordable ones are grayed out and disabled
- Click a spell → confirm screen with description → Elsütés! or ← Vissza
- Multi-enemy: target selection step inserted after confirm
- Replaces the old random 2d6 roll mechanic

### Save / Load system
- Sidebar button opens modal
- Save: type a name (pre-filled with current section), click Mentés
- Saves stored in `localStorage` key `hk_saves` (max 10 slots, newest first)
- Each slot records: name, bookId, bookTitle, section, timestamp, full character + inventory
- Load: click Betöltés on any slot (only works if matching book is loaded)
- Delete: click Törlés on any slot

### Luck test system
- Detects `has_luck_test` sections, shows 2d6 roll UI
- Luck −1 on use (win or lose)
- Routes to choices[0] (success) or choices[1] (failure)

### Combat system (single and multi-foe)
- Initiative: 1d6 each, player vs the group
- **Multi-foe rule**: ALL living enemies attack every round; player picks ONE target per round
- Attack: 2d6 + attack skill vs enemy defense
- Damage: looked up from `rules.damage_table` by range string
- HP bars for player and each enemy; dead enemies get strikethrough
- Target selection buttons when multiple enemies alive (shows current HP)
- Victory routes to section choices; death → new game prompt

### Magic combat system
- Available when player has Varázskőnyv and varázserő > 0
- Roll 2d6 → pick attack spell → show spell card (name, cost, damage, description) → confirm
- Fixed damage spells: apply directly
- Special spells: Vakság (−5 enemy attack), Fullasztás (enemy skips turns, tracked per-enemy),
  Ártó Szem (−5 enemy defense), Erős Karok (+4 player attack), Kettős Csapás (2× damage 4 rounds),
  Halálvarázs (instant kill), Ködpatkány (12 dmg simplified)
- Spell target selection when multiple enemies alive
- MP deducted on cast; "no MP" path falls back to sword

### Interactive inventory
- Items with actions show a pill label in sidebar (dob / iszik / eszik)
- **Weapons** (damage note "X-Y veszteséget okoz"): roll damage button, result from damage table
- **Potions** (note "N életerőpontot gyógyít"): Megiszom button heals HP, removes when qty=0, disabled if full
- **Food/rations** ("Étel és ital"): "Rest & eat" mechanic — consumes 1 day, restores +4 Varázserő
- **Speed potion** ("Gyorsító ital"): combat-only button; sets `combat.speedPotion = true`; grants a second attack each round for that combat
- **Stat-bonus items** (Amulett, shop armor/potions with `stat_bonus` field): bonuses applied immediately on acquisition; reverted when item is removed/traded

### Shop system (platform-generic)
- Sections with `has_shop: true` and a `shop: { items: [...] }` block render a 🏪 Bolt UI above the choices
- Each shop item: `{ item, note, effect, price, currency, unique, stat_bonus }` 
- Buy button deducts gold, adds item to inventory, applies any `stat_bonus` immediately
- `unique: true` items show "Megvan" once owned and disable the buy button
- Gold balance shown live in shop header; updates after each purchase

### Quest item requirements (platform-generic)
- Choices with `requires: ["Item name"]` are **disabled + locked** (🔒 badge) if the player lacks the item
- Locked choices are still visible so the player knows what they're missing
- Multiple items can be required: `requires: ["A", "B"]` — all must be present

### Item exchange (platform-generic)
- Sections with `takes_items: ["Name"]` automatically remove those items on first visit (reverts any stat bonuses)
- Sections with `gives_items: [{item, note, effect, stat_bonus}]` automatically add those items on first visit
- First-visit detection: `state.history.filter(x => x === id).length === 1`
- Exchanges only fire once; revisiting the section does nothing

### Stat bonus items (platform-generic)
- Items can carry `stat_bonus: { stat_key: value }` (both in rules.json starting_equipment and shop items)
- `applyItemStatBonus(item)` — adds values to `current` and `max` stats
- `revertItemStatBonus(item)` — subtracts values; called when item is removed or fully consumed
- `addItemToInventory(itemDef)` — canonical function for adding items (handles qty stacking, stat bonus, renderInventory)
- `removeItemByName(name)` — canonical function for removing items (handles stat revert)

### Structured events system (platform-generic, added Session 9/10)
Each section's `events` array holds typed event objects processed by `applyEvents(sectionData, timing)`:

| Kind | When | Effect |
|------|------|--------|
| `STAT_CHANGE` | on_enter (first visit) | `player[stat] += amount` or rolls formula; shows toast |
| `ITEM_GAIN` | on_enter (first visit) | adds items to inventory |
| `ITEM_LOSE` | on_enter (first visit) | removes items from inventory |
| `GOLD_CHANGE` | on_enter (first visit) | adds/deducts gold |
| `REST` | on_enter (first visit) | restores listed stats to `state.character.base` values |
| `COMBAT` | combat init | reads `special_rules` array (see below) |

`COMBAT` special rules (stamped onto enemy objects at combat start by `renderCombatBlock`):
- `enemy_regenerate` → `enemy._regenerate = N` — heals N HP after each player hit
- `multi_attack` → `enemy._multiAttack = N` — attacks N times per round
- `stat_drain` → `enemy._statDrain = {stat, amount}` — permanently reduces player stat on each hit
- `player_pre_damage` → applies HP/stat loss to player before combat begins
- `no_flee` → sets `state.combat.noFlee = true`

Combat rule application:
- `resolvePlayerAttackOn`: after dealing damage, checks `enemy._regenerate` and heals
- `resolveAllEnemiesAttack`: wraps single attack in `for (let atk = 0; atk < (enemy._multiAttack||1); atk++)` loop; applies `_statDrain` after each successful hit

`calcDamage(damageRange)` — handles all damage edge cases:
- Normalises en-dash/em-dash/box-drawing chars to hyphen
- Looks up formula in `rules.damage_table`; falls back to uniform N–M roll for unknown ranges
- If damageRange is null/missing → rolls 1d6

### Mobile layout fix (Session 10)
- `#screen-menu` and `#screen-create` changed from `min-height: 100dvh` to `height: 100dvh; overflow-y: auto` — screens scroll internally as fixed-height viewports
- `#btn-start` (character creation "Kaland kezdése") gets `position: sticky; bottom: 1rem` on mobile (≤720px) — always visible regardless of scroll position

---

## Data: sections.json

Full schema per section:
```json
{
  "id": 1,
  "text": "...",
  "choices": [{ "text": "...", "target": 42, "requires": ["Item name"] }],
  "enemies": [{ "name": "...", "eletero": 20, "tamadasi_kepesseg": 15, "vedettsegi_szint": 14, "damage": "1-6" }],
  "is_ending": false,
  "has_combat": false,
  "has_luck_test": false,
  "events": [],
  "has_shop": true,
  "shop": { "items": [{ "item": "...", "note": "...", "price": 10, "currency": "arany", "unique": true, "stat_bonus": {} }] },
  "takes_items": ["Item name"],
  "gives_items": [{ "item": "...", "note": "...", "qty": 1, "stat_bonus": {} }],
  "gold_cost": 5
}
```

### magusok-tornya sections.json
- 300/300 sections
- 18 sections with enemy stat blocks; section 4 is the only multi-foe section
- Section 246 has garbled OCR mid-text — needs manual PDF check
- Section 67: shop; Section 131: item exchange (Amulett → Tengeri kagyló + Sziromkesztyű)
- `events: []` on all sections (not yet extracted — run `07_extract_events.py magusok-tornya` when needed)

### a-demon-szeme sections.json
- 300/300 sections
- 82 of 300 sections have non-empty `events` arrays (extracted by `07_extract_events.py`)
- **Session 11 OCR rebuild**: replaced all text with clean new OCR source (`D:\Code\OCR\23 - A démon szeme.txt`)
  - 147 sections: fully clean new OCR text (correct text, choices, enemies from new parse)
  - 13 sections: backup text kept (new parse had two-column mixing artifacts with >5 choices)
  - 140 sections: backup text kept (new OCR two-column mixing prevented new parse from finding these)
  - Section 1 choices now correctly route to [122, 207, **294**] (was wrongly 89 in old pipeline)
  - Two-column pages are the remaining source of errors; ~140 sections may have wrong section numbers
  - `pipeline/08_split_ocr_to_pages.py` — splits new OCR file into per-page raw-text files
  - `pipeline/09_merge_sections.py` — merges new parse + backup, preserves events, rejects mixed sections
- Key verified events:
  - Sec 5 & 195: Alakváltó `enemy_regenerate` +2 HP after each player hit
  - Sec 45 & 46: Sopa lovag `multi_attack` (2×/round) + `stat_drain` (TK)
  - Sec 83: `player_pre_damage` −7 HP (ambush knockdown before combat)
  - Sec 104: REST + GOLD_CHANGE −1 (meal costs)
- Known data quirks:
  - Sec 55: large permanent stat bonuses (+5 TK, +3 HP, +4 Szerencse) from ancient writing — legitimate
  - Sec 81: `stat_drain` target "fekete lovag" won't match actual enemy "Goreel fejvadász" — harmless
  - Sec 36/37: uses unknown types `enemy_first_always` / `initiative_always_loses` (cursed mask) — ignored by engine
  - Sec 284: uses unknown type `player_stat_penalty` for temporary −5 TK/VS — ignored by engine (future work)

## Data: rules.json

- 5 stats with roll formulas
- 5 races: Ember (baseline, no modifiers), Felfödi ember, Óriás, Manó, Tünder
- Starting equipment (8 items): Varázskard (2-7), Gyógyító ital ×2 (15 HP), Gyorsító ital, Varázsgyűrű, Amulett (+3 all stats / −2 dmg), Étel és ital, Varázskőnyv, Aranypénz ×200
- Amulett has `stat_bonus: {eletero:3, tamadasi_kepesseg:3, vedettsegi_szint:3, szerencse:3, varazserő:3}`
- Combat rules, luck test rules
- 16-entry damage table
- 11 attack spells, 12 defense spells

---

## Known Issues / Future Work

### magusok-tornya
- Section 246: text garbled mid-sentence from OCR artifact — needs manual fix from PDF
- Some `has_combat` sections (27 total) still lack extracted enemy stats — unusual formats
- Magic defense spells not yet implemented (enemy mages don't appear in extracted data)
- `05_correct_sections.py` created but not yet run on this book
- `07_extract_events.py` not yet run on this book

### a-demon-szeme
- **Flee button not blocked** when `state.combat.noFlee = true` — flag is set but UI doesn't gate the button yet
- Unknown event types to implement:
  - `enemy_first_always` / `initiative_always_loses` (sec 36/37) — cursed mask forces player to always lose initiative
  - `player_stat_penalty` (sec 284) — temporary −5 TK/VS during one specific combat
- Sec 81: `stat_drain` target "fekete lovag" should be "Goreel fejvadász" — harmless now but worth fixing

### General
- `05_correct_sections.py` (OCR Sonnet correction) not yet run on either book
- Inventory item quantities on books other than magusok-tornya may need checking

---

## Adding a Second Book (checklist)

1. Place PDF in `books/<book-id>/<book-id>.pdf`
2. Write `books/<book-id>/parse_config.json` (copy magusok-tornya's as template)
3. Run the 5 pipeline scripts with the new book-id
4. Write `books/<book-id>/rules.json` for that book's stat/race/spell system
5. Generate `books/<book-id>/cover.png` (copy and adapt the Pillow script used for magusok-tornya)
6. Add an entry to `books/index.json` with all fields (id, title, author, year, series, volume, cover, sections, rules, description)
7. Everything else (combat, magic, luck, inventory, save/load, menus) carries over automatically

---

## Session Log

### Session 1 — Project Setup
- Created folder structure, moved PDF, wrote CLAUDE.md

### Session 2 — OCR Pipeline
- Wrote `01_pdf_to_images.py` and `02_ocr_pages.py`
- Chose Claude Vision over Tesseract for Hungarian diacritics
- Set ANTHROPIC_API_KEY in Windows User environment permanently

### Session 3 — Section Parser
- Wrote `03_parse_sections.py` (generic, driven by parse_config.json)
- Wrote `books/magusok-tornya/parse_config.json`
- 299/300 sections parsed

### Session 4 — Rules Extraction
- Hand-crafted `rules.json` from OCR of pages 3-12
- Stats, races, combat, luck, damage table, 11 attack spells, 12 defense spells

### Session 5 — Frontend + Combat/Luck Systems
- Built full frontend: character creation, prologue, game screen
- Luck test system integrated
- Combat system integrated
- Wrote `04_clean_text.py` for Hungarian spellcheck pass

### Session 6 — Text Cleanup + GitHub
- Ran 04_clean_text.py on all 94 pages
- Re-ran parser: 18 enemies extracted (up from 8)
- Pushed to GitHub

### Session 7 — Magic, Icons, Multi-foe, Inventory, QA
- Added magic combat system (spell rolling, target selection, special effects)
- Created PWA icons (tower silhouette, icon-192/512.png)
- Added interactive inventory (weapon damage roll, potion drink, food/rest mechanic)
- Implemented multi-foe combat (all enemies attack each round, target selection)
- QA pass: fixed section 67 choice texts, added section 267 from scanned photo,
  fixed false-positive ')' choices in sections 147/204/257, fixed missing choice in 211
- Added Ember (human) baseline race with no modifiers to rules.json

### Session 8 — Main Menu, Spellbook, Spell Picker, Save/Load, Cloudflare fix
- Fixed Cloudflare Pages hosting: moved all frontend files from `frontend/` to repo root
- Created `books/index.json` multi-book manifest
- Generated `books/magusok-tornya/cover.png` (400×560px, Pillow)
- Created `pipeline/05_correct_sections.py` — Claude Sonnet OCR correction script
- Rewrote `index.html`: added `#screen-menu`, spellbook modal, save/load modal, sidebar action buttons
- Rewrote `game.js`: menu system, dynamic book loading, spellbook viewer, spell picker (player choice),
  save/load with localStorage, back-to-menu navigation
- Updated `style.css`: all new UI components (book cards, modals, spell picker, save slots)

### Session 9 — Second Book: A Démon Szeme (vol. 23)
- Added all 300 sections via custom two-column OCR recovery pipeline (`06_recover_sections.py`)
- Manual patches for 6 OCR-absent sections from screenshots (`patch_missing_sections.py`)
- Fixed `calcDamage()`: handles null damage, en-dash normalisation, unknown ranges (uniform roll)
- Added structured events system: `applyEvents()`, `getCombatEvents()`, `COMBAT` special rules
- Implemented `enemy_regenerate`, `multi_attack`, `stat_drain`, `player_pre_damage`, `no_flee` in combat engine
- Wrote and ran `07_extract_events.py` — 82/300 sections got non-empty events
- Key combat rules verified: Alakváltó regeneration (sec 5/195), Sopa lovag double-attack (sec 45/46)

### Session 10 — Mobile button fix + events deployment
- Deployed enriched a-demon-szeme sections.json (all 300 events) to Cloudflare Pages
- Fixed mobile "Kaland kezdése" not reachable: character creation content (1203px) overflowed 812px viewport
  - `#screen-create` and `#screen-menu`: changed `min-height: 100dvh` → `height: 100dvh; overflow-y: auto`
  - `#btn-start` on mobile: `position: sticky; bottom: 1rem` so button is always visible
- Fix confirmed in preview; committed and pushed

### Session 11 — OCR text rebuild for A Démon Szeme
- User provided better OCR file: `D:\Code\OCR\23 - A démon szeme.txt` (94 pages, sections start at page 13)
- Split OCR into per-page files with `08_split_ocr_to_pages.py`; re-ran `03_parse_sections.py` → 160/300 sections (two-column pages cause missing headers)
- Built `09_merge_sections.py`: merges new parse (160 clean) + old backup (300 sections from git)
  - Rejects new-parse data where >5 choices (two-column mixing artifact) — 13 sections reverted to backup
  - Preserves events from backup for sections overwritten by new parse
- Final result: 300 sections, 147 with fully clean new OCR text, 82 with events, section 1→294 routing fixed

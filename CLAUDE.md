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

## First Book

**Mágusok Tornya** (Tower of Magicians) — Jonathan Graves, 1997
- 300 numbered sections (all 300 now present)
- Full combat system with spells, items, dice rolls
- Stats: Életerő (HP), Támadási képesség (Attack), Védettségi szint (Defense), Szerencse (Luck), Varázserő (Magic)
- Race system: Ember (baseline), Felfödi ember, Óriás, Manó, Tünder
- Spell tables: 11 attack spells, 12 defense spells
- Weapon damage table (16 entries)

---

## Project Structure

```
/gamebook-platform
  /pipeline        ← OCR, parsing, cleanup scripts (Python)
  /frontend        ← HTML/JS/CSS web interface
  /books
    /magusok-tornya
      /pages/                  ← 94 PNG images (gitignored)
      /raw-text/               ← per-page OCR output (gitignored)
      /cleaned-text/           ← spellchecked OCR output (gitignored)
      magusok-tornya.pdf       ← source PDF (gitignored)
      parse_config.json        ← book-specific parser config
      sections.json            ← 300 parsed sections (committed)
      rules.json               ← stats, races, combat, spells (committed)
  CLAUDE.md        ← this file
```

---

## Tech Stack

- **Python** — OCR pipeline scripts
- **Vanilla HTML/JS/CSS** — frontend (no framework)
- **JSON** — data format between pipeline and frontend
- **Claude Vision API** (`claude-haiku-4-5-20251001`) — OCR of scanned pages
- **Claude Haiku text API** — Hungarian spellcheck/correction pass
- **PWA** — installable on iOS home screen

### Python libraries
- `pymupdf` (fitz) — renders PDF pages to PNG
- `anthropic` — Claude API client
- `Pillow` — generates PWA icons

### Environment
- Windows 11, PowerShell
- `ANTHROPIC_API_KEY` set permanently in Windows User environment variables
- Pipeline scripts must be run from a **fresh terminal** (not from Claude Code session)

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
# then open http://localhost:8000/frontend/
```

---

## Pipeline Scripts (run in order for a new book)

```powershell
python pipeline\01_pdf_to_images.py [book-id]   # PDF → PNG pages
python pipeline\02_ocr_pages.py     [book-id]   # PNG → raw text (Claude Vision)
python pipeline\04_clean_text.py    [book-id]   # raw text → cleaned text (Claude Haiku)
python pipeline\03_parse_sections.py [book-id]  # cleaned text → sections.json
```

All scripts default to `magusok-tornya` if no book ID given. All are resumable (skip already-done files).

---

## GitHub

Repository: https://github.com/AdamBerczi/gamebook-platform

`sections.json` and `rules.json` **are** committed so anyone can clone and play without running the pipeline.

PDF, raw pages, OCR text are **gitignored** (copyright + regeneratable).

---

## Features Implemented

### Frontend
- Character creation screen: 5 races, stat rolling with re-roll, race stat modifiers shown
- Prologue screen ("Előzmények") between character creation and section 1
- Game screen: sidebar (desktop) + collapsible drawer (mobile)
- Sidebar: HP/MP bars, all 5 stats, inventory list, race badge, new game button
- Mobile: sticky HP in topbar, slide-up stats drawer
- PWA manifest + tower icons (icon-192.png, icon-512.png) for iOS home screen

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
- **Food/rations** ("Étel és ital"): food has no usage in any of the 300 sections, so added
  "Rest & eat" mechanic — consumes 1 day, restores +4 Varázserő

---

## Data: sections.json

- 300/300 sections (section 267 manually added from scanned page photo)
- Schema per section: `{id, text, choices: [{text, target}], enemies: [{name, eletero, tamadasi_kepesseg, vedettsegi_szint, damage}], is_ending, has_combat, has_luck_test}`
- 18 sections with extracted enemy stat blocks
- Section 4 is the only multi-foe section (Világcsavargó + Kereskedő)
- Section 246 has garbled OCR mid-text — needs manual PDF check

## Data: rules.json

- 5 stats with roll formulas
- 5 races: Ember (baseline, no modifiers), Felfödi ember, Óriás, Manó, Tünder
- Starting equipment (7 items)
- Combat rules, luck test rules
- 16-entry damage table
- 11 attack spells, 12 defense spells

---

## Known Issues / Future Work

- Section 246: text garbled mid-sentence from OCR artifact — needs manual fix from PDF
- Some `has_combat` sections (27 total) still lack extracted enemy stats (only 18 parsed) — unusual formats
- Magic defense spells not yet implemented (enemy mages don't appear in extracted data yet)
- Frontend book URL is hardcoded — for a second book, change the two constants at top of `game.js`,
  or implement `?book=` URL parameter routing

---

## Adding a Second Book (checklist)

1. Place PDF in `books/<book-id>/<book-id>.pdf`
2. Write `books/<book-id>/parse_config.json` (copy magusok-tornya's as template)
3. Run the 4 pipeline scripts with the new book-id
4. Write `books/<book-id>/rules.json` for that book's stat/race/spell system
5. Change the two URL constants at the top of `frontend/game.js`
6. Everything else (combat, magic, luck, inventory) carries over automatically

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

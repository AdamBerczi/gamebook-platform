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
  /books
    index.json                 ← multi-book manifest (id, title, cover, sections, rules URLs)
    /magusok-tornya
      /pages/                  ← 94 PNG images (gitignored)
      /raw-text/               ← per-page OCR output (gitignored)
      /cleaned-text/           ← spellchecked OCR output (gitignored)
      magusok-tornya.pdf       ← source PDF (gitignored)
      parse_config.json        ← book-specific parser config
      sections.json            ← 300 parsed sections (committed)
      rules.json               ← stats, races, combat, spells (committed)
      cover.png                ← 400×560px book cover art (Pillow-generated)
  index.html       ← single-page app shell (all screens + modals)
  game.js          ← all game logic
  style.css        ← all styles
  manifest.json    ← PWA manifest
  icon-192.png     ← PWA icon
  icon-512.png     ← PWA icon
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
```

All scripts default to `magusok-tornya` if no book ID given. All are resumable (skip already-done files).

Script 05 requires `ANTHROPIC_API_KEY` set in environment and must run from a fresh terminal (not Claude Code session). Creates a `.bak` backup before modifying.

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

---

## Data: sections.json

- 300/300 sections (section 267 manually added from scanned page photo)
- Schema per section:
  ```
  {
    id, text,
    choices: [{ text, target, requires?: ["item"] }],
    enemies: [{ name, eletero, tamadasi_kepesseg, vedettsegi_szint, damage }],
    is_ending, has_combat, has_luck_test,
    has_shop?: true,
    shop?: { items: [{ item, note?, effect?, price, currency, unique?, stat_bonus? }] },
    takes_items?: ["Item name"],
    gives_items?: [{ item, note?, effect?, qty?, stat_bonus? }],
    gold_cost?: number
  }
  ```
- 18 sections with extracted enemy stat blocks
- Section 4 is the only multi-foe section (Világcsavargó + Kereskedő)
- Section 246 has garbled OCR mid-text — needs manual PDF check
- Section 67: shop with 9 items (Kötél, Buzogány, Pallos, Gyógyital, Extra Gyógyital, Bronzmajzs, Acélpajzs, Bross, Sárkányvér)
- Section 131: item exchange — takes Amulett, gives Tengeri kagyló + Sziromkesztyű
- Requires implemented on: 252 (Kötél), 220 (Amulett), 55/198/298 (Tengeri kagyló / Varázsgyűrű), 109/234 (Sziromkesztyű), 265 (Gyorsító ital)

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

- Section 246: text garbled mid-sentence from OCR artifact — needs manual fix from PDF
- Some `has_combat` sections (27 total) still lack extracted enemy stats (only 18 parsed) — unusual formats
- Magic defense spells not yet implemented (enemy mages don't appear in extracted data yet)
- OCR correction pipeline (`05_correct_sections.py`) created but not yet run on magusok-tornya

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

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
- 300 numbered sections
- Full combat system with spells, items, dice rolls
- Stats: Életerő (HP), Támadási képesség (Attack), Védettségi szint (Defense), Szerencse (Luck), Varázserő (Magic)
- Race system: Human, Giant, Gnome, Elf (with stat modifiers)
- Spell tables: 11 attack spells, 12 defense spells
- Weapon damage table
- PDF located at: `books/magusok-tornya/magusok-tornya.pdf`

---

## Project Structure

```
/gamebook-platform
  /engine          ← combat, dice, rules logic (Python) [NOT STARTED]
  /pipeline        ← OCR, parsing, validation scripts (Python)
  /frontend        ← HTML/JS/CSS web interface [NOT STARTED]
  /books
    /magusok-tornya
      magusok-tornya.pdf      ← source PDF (94 pages, fully scanned, no text layer)
      /pages                  ← 94 PNG images rendered from PDF (200 DPI) — DONE
      /raw-text               ← per-page .txt files from Claude Vision OCR — IN PROGRESS
      book.json               ← metadata [NOT STARTED]
      sections.json           ← all 300 parsed sections [NOT STARTED]
      rules.json              ← combat stats, spells, weapons [NOT STARTED]
  CLAUDE.md        ← this file — update after each session
```

---

## Tech Stack

- **Python** — backend engine and OCR pipeline
- **Vanilla HTML/JS/CSS** — frontend (no framework for MVP)
- **JSON** — data format between pipeline and frontend
- **No database** — file-based is fine for MVP

### Python libraries installed
- `pymupdf` (fitz) — renders PDF pages to images (chosen over pdf2image: no external deps)
- `anthropic` — Claude Vision API client
- `pdfplumber` — installed but not used (PDF has no text layer)

### Key facts about the PDF
- 94 pages total
- Fully scanned — zero text layer on any page
- OCR approach: Claude Vision (`claude-haiku-4-5-20251001`) — better Hungarian accuracy than Tesseract

---

## User Background

- Basic Python and C from years ago, learning fast
- Wants explanations of decisions, not just generated code
- Wants to understand what's being built

---

## Session Log

### Session 1 — Project Setup
- Created `/gamebook-platform` folder structure
- Moved PDF into `books/magusok-tornya/`
- Wrote CLAUDE.md

### Session 6 — Text Cleanup + GitHub Sync
- Ran `04_clean_text.py` — all 94 pages cleaned with Claude Haiku Hungarian spellcheck
- Re-ran parser — 299/300 sections, 18 enemy stat blocks extracted (up from 8)
- Updated and pushed `sections.json` and `CLAUDE.md` to GitHub
- Repo: https://github.com/AdamBerczi/gamebook-platform

### Session 5 — Frontend + Combat/Luck Systems

- Wrote `frontend/index.html`, `frontend/style.css`, `frontend/game.js`, `frontend/manifest.json`
- PWA-ready (iOS home screen installable)
- Character creation screen: race selection with stat modifiers, dice rolling
- Prologue screen ("Előzmények") shown between character creation and section 1
- Sidebar: HP/MP bars, all stats, inventory, race badge
- Mobile: collapsible stats drawer, sticky HP in topbar
- **Luck test system**: detects `has_luck_test` sections, shows roll UI, luck -1 on use, routes to success/fail choice
- **Combat system**: parses enemy stats from section text, initiative roll, attack/defense resolution, HP bars, damage from rules.json table, victory/death outcomes
- Wrote `pipeline/04_clean_text.py` — sends OCR pages through Claude Haiku for Hungarian spellcheck
- Updated `03_parse_sections.py`: uses cleaned-text/ per-page where available, falls back to raw-text/; also extracts enemy stats into `enemies` field in sections.json
- **Partial cleanup done**: 9/94 pages cleaned (API key not available in Claude Code session)
- **To complete cleanup**: run `python pipeline\04_clean_text.py` from a fresh terminal — skips already-done pages

**To run the game**: `python -m http.server 8000` from `D:\Code\gamebook-platform`, then open `http://localhost:8000/frontend/`

### Session 4 — Rules Extraction
- Read rule pages (3-12) from raw OCR text
- Wrote `books/magusok-tornya/rules.json` with full game rules:
  - 5 character stats with roll formulas (életerő, támadási képesség, védettségi szint, szerencse, varázserő)
  - 4 races with stat modifiers (felfödi ember, óriás, manó, tünder)
  - Starting equipment
  - Combat rules (initiative, attack roll, flee rules)
  - Luck test rules
  - Damage table (16 entries, d6-based formulas)
  - 11 attack spells with cost/damage/description
  - 12 defense spells with cost/protects-against/activation roll/description
- Updated `parse_config.json` first_content_page from 9 to 12 (rules end at page 12)

### Session 3 — Section Parser

- Wrote `pipeline/03_parse_sections.py` — generic parser driven by per-book config
- Wrote `books/magusok-tornya/parse_config.json` — book-specific patterns (reusable model for future books)
- Parsed 299/300 sections successfully into `books/magusok-tornya/sections.json`
- Tuned OCR variant handling: `laporz`, `lapozza`, `lapozz az`, ending phrase typos
- 2 sections need manual fixes: 246 (cut off), 267 (missing entirely)
- **sections.json schema:** `{ book_id, title, author, year, total_sections, sections: { "N": { id, text, choices: [{text, target}], is_ending, has_combat, has_luck_test } } }`

### Session 2 — OCR Pipeline
- Confirmed PDF is fully scanned (no text layer on any of 94 pages)
- Decided on Claude Vision over Tesseract (better Hungarian diacritics, ~$0.20 total cost)
- Installed `pymupdf` and `anthropic` Python packages
- Wrote `pipeline/01_pdf_to_images.py` — renders all 94 pages to PNG at 200 DPI ✅ DONE
- Wrote `pipeline/02_ocr_pages.py` — sends each page to Claude Vision, saves .txt files
- Ran `01_pdf_to_images.py` successfully — 94 PNGs in `books/magusok-tornya/pages/` ✅ DONE
- Set `ANTHROPIC_API_KEY` permanently in Windows User environment variables ✅ DONE
- `02_ocr_pages.py` is ready to run — user needs to run it from a **fresh terminal** since
  the key was set after this Claude Code session started

---

## Known Manual Fixes Needed

- **Section 267** — missing entirely from all 94 OCR pages. Likely a bad scan. Find it in the PDF manually and add to sections.json.
- **Section 246** — text cuts off mid-sentence, no navigation link. Same cause. Check PDF page for the missing ending.

---

## Immediate Next Step

Build the frontend — a simple HTML page that loads `sections.json` and lets you play through the book.

---

## Decisions & Reasoning

| Decision | Reason |
|---|---|
| JSON as data format | Simple, human-readable, no DB needed for MVP |
| Vanilla JS frontend | No framework overhead; easier to understand for learning |
| Python pipeline | Good library support for PDF/OCR; readable code |
| File-based storage | Sufficient for single-user local play |
| Separate `rules.json` | Combat rules differ per book; keeps sections.json clean |
| pymupdf over pdf2image | Self-contained, no poppler install needed on Windows |
| Claude Vision over Tesseract | Hungarian diacritics handled correctly; ~$0.20 for whole book |
| 200 DPI for page images | Sweet spot: clear enough for Vision, small enough to be fast |
| claude-haiku-4-5 for OCR | Fast and cheap; more than capable for transcription |

---

## TODO

- [x] Create project folder structure
- [x] Render PDF pages to images (01_pdf_to_images.py)
- [x] Write OCR script (02_ocr_pages.py)
- [x] Run OCR — 94 pages processed
- [x] Review OCR output quality — very good
- [x] Write section parser (03_parse_sections.py)
- [x] sections.json produced — 299/300 sections (enemies field added)
- [x] rules.json produced — stats, races, combat, spells, damage table
- [x] Frontend built — character creation, prologue, section display, choices
- [x] Luck test system integrated
- [x] Combat system integrated (initiative, attack, damage, HP bars)
- [x] Run full text cleanup (94/94 pages done via `pipeline\04_clean_text.py`)
- [x] Re-run parser after cleanup — 299/300 sections, 18 enemies extracted
- [ ] Fix sections 246 and 267 manually
- [ ] iOS home screen icons (icon-192.png, icon-512.png)
- [ ] Magic combat system (spell selection, defense spells, activation rolls)

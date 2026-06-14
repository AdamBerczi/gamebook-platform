"""
Patch the 6 sections that the recovery script couldn't handle automatically.
Content sourced directly from book page screenshots.
"""
import json
from pathlib import Path

path = Path(__file__).parent.parent / "books" / "a-demon-szeme" / "sections.json"
with open(path, encoding="utf-8") as f:
    data = json.load(f)

secs = data["sections"]

# ── SECTION 41 ───────────────────────────────────────────────────────────────
# OCR block had 41+42 interleaved due to two-column layout.
# Section 41 text extracted from OCR lines 429-430 + choices from lines 439-440.
secs["41"] = {
    "id": 41,
    "text": (
        "Folytatod a szint átfésülését, ám nem sokkal később ráébredsz, immáron semmi "
        "hasznosítható nyom nincs, ahol folytathatnád a kutatást.\n\n"
        "Ha visszatérsz a szoborhoz, lapozz a 10-re!\n"
        "Ha a lyukhoz térsz vissza, lapozz a 273-ra!"
    ),
    "choices": [
        {"text": "Ha visszatérsz a szoborhoz,", "target": 10},
        {"text": "Ha a lyukhoz térsz vissza,", "target": 273},
    ],
    "enemies": [],
    "is_ending": False,
    "has_combat": False,
    "has_luck_test": False,
}

# ── SECTION 42 (screenshot) ──────────────────────────────────────────────────
secs["42"] = {
    "id": 42,
    "text": (
        "A rém véresen hanyatlik vissza a hullámok közé, s hamarosan csupán néhány "
        "vércsepp emlékeztet a csatára. Fegyveredet kézben tartva folytatod az utadat, "
        "s nem sokkal később egy szétözödött testet pillantasz meg az egyik szikla tetején. "
        "Hegyesedő füle, érdekes arca egyértelművé teszi: egy xinaf hever előtted.\n\n"
        "Még él, bár talán csak a varázsererejének köszönhetően. A sebei túl súlyosak ahhoz, "
        "hogy teljesen meggyógyíthassa magát, ám hihetetlen szívóssággal kapaszkodik az életbe.\n\n"
        "Amikor meghallja a lépteidet, feléd fordítja a fejét, és nyöszörögni kezd:\n"
        "– Segíts, és én minden kívánságodat teljesítem!\n\n"
        "Ha segítesz neki, lapozz a 223-ra!\n"
        "Ha végzel vele, lapozz a 295-re!\n"
        "Ha előbb a xinaf nevét kérdezed, lapozz a 119-re!\n"
        "Ha megpróbálod kikérdezni, lapozz a 182-re!"
    ),
    "choices": [
        {"text": "Ha segítesz neki,", "target": 223},
        {"text": "Ha végzel vele,", "target": 295},
        {"text": "Ha előbb a xinaf nevét kérdezed,", "target": 119},
        {"text": "Ha megpróbálod kikérdezni,", "target": 182},
    ],
    "enemies": [],
    "is_ending": False,
    "has_combat": False,
    "has_luck_test": False,
}

# ── SECTION 83 (screenshot) ──────────────────────────────────────────────────
secs["83"] = {
    "id": 83,
    "text": (
        "Hirtelen egy nehéz test veti rád magát, és a földre dönt (veszítesz 7 életerőpontot). "
        "A chindon az, gyorsabbnak bizonyult nálad. Mire talpra ugrasz, már két ellenféllel "
        "kell szembenézned.\n\n"
        "Goreel fejvadász: életerő 23, támadási képesség 19, védettségi szint 20. "
        "A fejvadász 1-6 életerőpont veszteséget okoz a buzogányával.\n"
        "Chindon: életerő 18, támadási képesség 16, védettségi szint 14. "
        "A szörnyeteg 2-12 életerőpont veszteséget okoz a mancsaival és a harapásaival. "
        "(Ne feledd, ellenfeleid mindketten támadhatnak rád a körben, "
        "te azonban csak egyikükre támadhattsz!)\n\n"
        "Ha sikerült legyőznöd ellenfeleidet, lapozz a 43-ra!\n"
        "Ha veszítettél, lapozz a 263-ra!"
    ),
    "choices": [
        {"text": "Ha sikerült legyőznöd ellenfeleidet,", "target": 43},
        {"text": "Ha veszítettél,", "target": 263},
    ],
    "enemies": [
        {"name": "Goreel fejvadász", "eletero": 23, "tamadasi_kepesseg": 19, "vedettsegi_szint": 20, "damage": "1-6"},
        {"name": "Chindon", "eletero": 18, "tamadasi_kepesseg": 16, "vedettsegi_szint": 14, "damage": "2-12"},
    ],
    "is_ending": False,
    "has_combat": True,
    "has_luck_test": False,
}

# ── SECTION 89 (screenshot) ──────────────────────────────────────────────────
secs["89"] = {
    "id": 89,
    "text": (
        "Gyengéden megrázogatod az idegen vállát. Az kinyitja a szemeit, majd csodálkozva néz rád.\n"
        "– Nem félsz tőlem? – kérdezi. – Pedig én mindenkit megölök, aki a közelembe jön.\n\n"
        "Ha fegyvert rántasz, lapozz az 5-re!\n"
        "Ha tovább hallgatsz, lapozz a 254-re!"
    ),
    "choices": [
        {"text": "Ha fegyvert rántasz,", "target": 5},
        {"text": "Ha tovább hallgatsz,", "target": 254},
    ],
    "enemies": [],
    "is_ending": False,
    "has_combat": False,
    "has_luck_test": False,
}

# ── SECTION 225 (screenshot) ─────────────────────────────────────────────────
secs["225"] = {
    "id": 225,
    "text": (
        "Rendkívül fáradt vagy, ezért az álom pillanatok alatt elnyom. Álmod nyugodt, semmi sem "
        "zavarja, s amikor ismét kinyitod a szemed, már kora reggel van. Odakintről madárcsicsergés "
        "szűrődik be. Felkelsz az ágyból, megreggelizel (ne feledd el módosítani a készleteidet), "
        "majd kilépész a kunyhóból.\n\n"
        "Az épület előtt hatalmas mancsnyomokat találsz. Valami óriási szörnyeteg éjjel itt járt, "
        "ám a kunyhó belsejében biztonságban voltál tőle.\n\n"
        "Ha követed a lány nyomait, lapozz a 77-re!\n"
        "Ha tovább haladsz észak felé, lapozz a 146-ra!"
    ),
    "choices": [
        {"text": "Ha követed a lány nyomait,", "target": 77},
        {"text": "Ha tovább haladsz észak felé,", "target": 146},
    ],
    "enemies": [],
    "is_ending": False,
    "has_combat": False,
    "has_luck_test": False,
}

# ── SECTION 257 (screenshot) ─────────────────────────────────────────────────
secs["257"] = {
    "id": 257,
    "text": (
        "Az öreg hosszan néz rád, majd hirtelen elégedetlenül felmordul, és felemeli a kezét. "
        "A következő pillanatban mágikus támadás zúdul rád.\n\n"
        "Élőhalott öregember: életerő 30, támadási képesség 17, védettségi szint 22, varázserő 30. "
        "Az öregember 1-3 életerőpont veszteséget okoz az üteseivel, ám először a varázsereje "
        "segítségével próbál meg elpusztítani.\n\n"
        "Ha sikerült legyőznöd ellenfeledet, lapozz a 194-re!\n"
        "Ha veszítettél, lapozz a 90-re!"
    ),
    "choices": [
        {"text": "Ha sikerült legyőznöd ellenfeledet,", "target": 194},
        {"text": "Ha veszítettél,", "target": 90},
    ],
    "enemies": [
        {"name": "Élőhalott öregember", "eletero": 30, "tamadasi_kepesseg": 17, "vedettsegi_szint": 22, "damage": "1-3"},
    ],
    "is_ending": False,
    "has_combat": True,
    "has_luck_test": False,
}

data["sections"] = secs
with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

total = len(secs)
missing = sorted(set(range(1, 301)) - {int(k) for k in secs})
print(f"Done. {total}/300 sections.")
if missing:
    print(f"Still missing: {missing}")
else:
    print("All 300 sections present!")

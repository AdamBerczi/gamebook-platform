import json, sys

with open(r'books/a-demon-szeme/sections.json', encoding='utf-8') as f:
    data = json.load(f)
s = data['sections']

# Sec 3: trideon death only
s['3']['text'] = (
    'A trideon csápjai a legváratlanabb irányokból csapnak le rád. Ha az egyiket sikerül '
    'hárítanod, a másik biztosan eltalál, és fájdalmas sebet ejt testeden. Már bánod, hogy '
    'engedtél a kapzsiságodnak; ha nem akartad mindenáron azt a gömböt, akkor most nem lennél '
    'ekkora bajban. Aztán, amikor a három csáp egyszerre lendül támadásba, már képtelen vagy '
    'időben hárítani. Kalandod véget ért!'
)
s['3']['is_ending'] = True
s['3']['has_combat'] = False
s['3']['choices'] = []
s['3']['events'] = []

# Sec 6: fényoszlop section only (choices 128, 299)
s['6']['text'] = (
    'A fényoszlop folyamatosan pulzál, mintha egy lüktető szívet néznél. '
    'Az oszlop belsejében úszó csillagok lassan változtatják a helyüket; a látvány lenyűgöző.'
)
s['6']['choices'] = [{'target': 128}, {'target': 299}]

# Sec 10: statue room only (choices 20, 109, 203, 41)
s['10']['text'] = (
    'Hamarosan ismét ott állsz a csigalépcső túloldalán, a hatalmas szobor előtt, '
    'mely egy démonszerű lényt ábrázol. A szobor két oldalán egy-egy ajtó látható.'
)
s['10']['has_combat'] = False
s['10']['choices'] = [{'target': 20}, {'target': 109}, {'target': 203}, {'target': 41}]
s['10']['events'] = []
s['10']['enemies'] = []

# Sec 11: puzzle — magic artifact drains HP + riddle (answer: FOLYÓ → section 96)
s['11']['text'] = (
    'Természetesen elfogadod az ajánlatot. Megérinted a varázstárgyat, mely azonnal nekilát '
    'az erőd elszívásának. (7 életerőpontot maradandóan elveszítettél!)\n\n'
    '— A negyedik betű az ipszilon — mondja a hang, majd ismét felhangzik a fenyegető versike:\n\n'
    'Nincsen pihenésem, nincsen maradásom,\n'
    'ágyban fekszem, még sincs soha megnyugvásom.\n\n'
    'A vándornak útját állhatom kevélyen,\n'
    'de többször könnyítem s megrövidítem.\n'
    'Hideg kebelemből sok állat éltét szívja,\n'
    's lettem már soknak gyászos, hideg sírja.'
)
s['11']['has_puzzle'] = True
s['11']['puzzle_fail_target'] = 140
s['11']['has_combat'] = False
s['11']['choices'] = []
s['11']['enemies'] = []
s['11']['events'] = [{
    'kind': 'STAT_CHANGE', 'timing': 'on_enter',
    'stat': 'eletero', 'amount': -7, 'permanent': True,
    'reason': 'varázstárgy elszívja az erődet'
}]

# Sec 12: Élőhalott öregember combat only (strip csontvázharcos death)
s['12']['text'] = (
    'Amikor kiejted a szádon a varázstárgy nevét, az öregember tekintete elfelhősödik, '
    'a következő pillanatban mágikus hatalmát használva rád támad.'
)
s['12']['is_ending'] = False

# Sec 15: Ayrabdir combat only (strip cliff scene)
s['15']['text'] = (
    'Az óvatosság a túlélés legfontosabb eszköze, gondolod magadban, miközben gyakorlott '
    'mozdulatokkal némi zsineget, harangvirágból készült csengettyűket és néhány facöveket '
    'veszel elő a hátizsákodból. A bokrok ágaira erősített vékony zsineg szinte észrevehetetlen, '
    'a csengőket pedig elrejtik a levelek. A csapda időben jelezni fogja, ha éjjel valaki meg '
    'akar lepni, hacsak nem repül az illető.\n\n'
    'Immáron nyugodtan hajtod álomra a fejed.\n\n'
    'Az elővigyázatosságod meghozza az eredményét. Halk csengőszóra riadsz, és a kardod után '
    'kapsz. Alig néhány lépésnyire tőled egy éjfekete vadállat, egy ayrabdir vicsorít, majd '
    'könnyű, nesztelen mozdulattal rád veti magát, ám felkészülten fogadod.'
)
s['15']['choices'] = [{'target': 53}, {'target': 188}]

# Sec 21: trim text to wyvernbőr book puzzle only
s['21']['text'] = (
    'Kíváncsian lapozol bele a könyvbe; a vastag, Wyvernbőrből készült fedele felkelti az '
    'érdeklődésedet. Az első oldalak üresek, ám hamarosan egy apró versikére bukkansz:\n\n'
    'Ha rám nézel, visszanézek,\n'
    'ha rám nevetsz, kinevetlek.\n'
    'Tiszta, igaz és hű vagyok,\n'
    'kedvedért én nem hazudok.'
)

# Sec 24: trim text to statue-interaction only
s['24']['text'] = (
    'Nincs legyőzhetetlen ellenfél. A lábaid előtt heverő, vérbe fagyott szörnyeteg a legjobb '
    'példa erre. Miután nem kell további fenyegetéstől tartanod, figyelmed ismét a szobor felé fordul.'
)

# Sec 26: Vérégetés spell section only (strip old-man conversation)
s['26']['text'] = (
    'A pergamen hirtelen fellángol, miközben egy ősi, erőteljes varázslat formálódik az '
    'elmédben: a Vérégetés. Ezt a varázslatot akkor mondhatod el, ha a varázserőd értéke '
    'pontosan nulla (ha ennél akár eggyel is több, akkor nem használható). Hatásával az '
    'életerődből pontokat áldozhatsz fel a varázserő ideiglenes növelésére. Azaz, ha az '
    'aktuális életerődből feláldozol X pontot (ezt le kell vonnod), akkor a varázserőd X '
    'ponttal növekedik. Az így nyert varázserő ugyanúgy felhasználható, mint az eredeti, '
    'az életerő pedig a szokásos módszerekkel visszagyógyítható. A változások nem maradandóak!\n\n'
    'A varázslatot írd fel a Kalandlapodra, hogy szükség esetén mindig kéznél legyen!'
)
s['26']['has_combat'] = False
s['26']['choices'] = [{'target': 149}]
s['26']['events'] = []

# Sec 32: renegade-search section only (strip chase mechanic that belongs to sec 33)
s['32']['text'] = (
    'Úgy gondolod, egy remete aligha tudhat túl sokat a toronyról, ezért ismét nekikezdesz '
    'a nyomkeresésnek. Elég sok időt szánsz rá, de hiába, fáradozásod ezúttal hiábavaló. '
    'Ráadásul mire visszatérsz oda, ahol az öregembert láttad, az sincs sehol. Kénytelen vagy '
    'visszatérni a romokhoz. Késő délutánra jár már az idő, amikor megérkezel a toronyhoz.'
)
s['32']['choices'] = [{'target': 122}, {'target': 207}]

# Sec 33: competing-dice escape mechanic
# choices[0]=caught(83), choices[1]=escaped(168)
s['33']['has_chase'] = True
s['33']['chase'] = {
    'player_rolls': 10,
    'dice_sides': 6,
    'enemy_rolls': 10,
    'enemy_label': 'fejvadász és állata',
    'description': (
        'Dobj tízszer a hatoldalú kockával, és add össze az értékeket! '
        'Ez az általad megtett távolság. A fejvadász és állata szintén dob tízszer. '
        'Ha az ő távolságuk nagyobb, utolérnek.'
    )
}

# Sec 34: abandoned-building exploration only (strip csontvázharcos fight)
s['34']['text'] = (
    'Az épület meglehetősen régóta elhagyatottan állhat, a nyomok erre utalnak. '
    'Ám minden idegszáladdal érzed, hogy valahonnan figyel valaki, bármerre is járj. '
    'Az épület három nagyobb helyiségre tagolódik, melyeket egy jókora folyosó köt össze.'
)
s['34']['has_combat'] = False
s['34']['choices'] = [{'target': 123}, {'target': 249}, {'target': 186}, {'target': 289}]
s['34']['events'] = []
s['34']['enemies'] = []

# Sec 35: csontvázharcos — fix text (remove sec 34's last choice from body) + add -8 HP event
s['35']['text'] = (
    'Kétségbeesetten próbálsz elhajolni a csatabárd elől, de nem vagy elég fürge. '
    'A nehéz fegyver az oldaladba vág, súlyos sebet okozva ezáltal (veszítesz 8 életerőpontot). '
    'Minden erődet összeszedve szembefordulsz ellenfeleddel, hogy összemérd vele a tudásodat. '
    'Szerencsére a többi halott harcos nem mozdul, mert ennyivel aligha bírnál.'
)
s['35']['events'] = [{'kind': 'STAT_CHANGE', 'timing': 'on_enter', 'stat': 'eletero', 'amount': -8}]

with open('books/a-demon-szeme/sections.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print('Done — summary:')
for sid in ['3','6','10','11','12','15','21','24','26','32','33','34','35']:
    sec = data['sections'][sid]
    ch = [c['target'] for c in sec.get('choices', [])]
    evs = [(e['kind'], e.get('amount',''), e.get('permanent','')) for e in sec.get('events', [])]
    sys.stdout.write(
        f'  {sid}: choices={ch} events={evs}'
        f' puzzle={sec.get("has_puzzle")} chase={sec.get("has_chase")}'
        f' ending={sec.get("is_ending")} combat={sec.get("has_combat")}\n'
    )

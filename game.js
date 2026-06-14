const BOOKS_INDEX_URL = '/books/index.json';
const SAVES_KEY       = 'hk_saves';

// ── STATE ──────────────────────────────────────────────────────────────────

let rules    = null;
let sections = null;
let bookMeta = null;   // current book entry from index.json

let state = {
  currentSection: 1,
  selectedRace:   'ember',
  character: {
    base: {}, current: {}, max: {},
    race: null,
    inventory: [],
  },
  history: [],
  combat: null,
};

// ── DICE ───────────────────────────────────────────────────────────────────

function d6()  { return Math.floor(Math.random() * 6) + 1; }
function d6x(n){ let t = 0; for (let i = 0; i < n; i++) t += d6(); return t; }
function roll2d6() { return d6() + d6(); }

function rollFormula(formula) {
  const m = formula.match(/(\d+)d(\d+)\s*([+-]\s*\d+)?/);
  if (!m) return 0;
  const [, count, sides, modifier] = m;
  let total = 0;
  for (let i = 0; i < parseInt(count); i++)
    total += Math.floor(Math.random() * parseInt(sides)) + 1;
  if (modifier) total += parseInt(modifier.replace(/\s/g, ''));
  return total;
}

function rollDamage(formula) {
  formula = formula.trim();
  if (formula.includes('*')) {
    const [f, mul] = formula.split('*');
    return rollDamage(f) * parseInt(mul);
  }
  if (formula.includes('/')) {
    const [f, div] = formula.split('/');
    const parts = div.split('+');
    const base  = Math.round(rollDamage(f) / parseInt(parts[0]));
    return base + (parts[1] ? parseInt(parts[1]) : 0);
  }
  const m = formula.match(/(?:(\d+)d(\d+)|d(\d+))(?:\+(\d+))?/);
  if (!m) return parseInt(formula) || 0;
  const count = parseInt(m[1] || '1');
  const sides = parseInt(m[2] || m[3]);
  const bonus = parseInt(m[4] || '0');
  return d6x(count) + bonus;
}

function damageFormulaForRange(range) {
  if (!range || !rules) return null;
  const entry = rules.damage_table.find(r => r.range === range);
  return entry ? entry.formula : null;
}

// ── MAIN MENU ──────────────────────────────────────────────────────────────

async function init() {
  try {
    const resp = await fetch(BOOKS_INDEX_URL);
    const index = await resp.json();
    buildBookMenu(index.books);
  } catch (e) {
    document.getElementById('book-grid').innerHTML =
      '<p style="color:var(--text-muted);padding:1rem">Hiba: nem sikerült betölteni a könyvlistát.</p>';
  }
  showScreen('menu');
}

function buildBookMenu(books) {
  const grid = document.getElementById('book-grid');
  grid.innerHTML = '';
  books.forEach(book => {
    const card = document.createElement('div');
    card.className = 'book-card';
    card.innerHTML = `
      <div class="book-card-cover">
        <img src="${book.cover}" alt="${book.title}" loading="lazy">
      </div>
      <div class="book-card-info">
        <div class="book-card-series">${book.series} · ${book.volume}. kötet</div>
        <div class="book-card-title">${book.title}</div>
        <div class="book-card-author">${book.author}, ${book.year}</div>
        <div class="book-card-desc">${book.description}</div>
        <button class="btn-primary book-card-btn">Kaland kezdése</button>
      </div>
    `;
    card.querySelector('.book-card-btn').addEventListener('click', () => loadBook(book));
    grid.appendChild(card);
  });
}

async function loadBook(book) {
  bookMeta = book;
  showLoading(true);
  try {
    const [rulesResp, sectionsResp] = await Promise.all([
      fetch(book.rules),
      fetch(book.sections),
    ]);
    rules    = await rulesResp.json();
    sections = await sectionsResp.json();
  } catch (e) {
    alert('Hiba: nem sikerült betölteni a könyv adatait.');
    showLoading(false);
    return;
  }
  showLoading(false);

  // Update create screen labels
  document.getElementById('create-subtitle').textContent = `${book.series} · ${book.volume}. kötet`;
  document.getElementById('create-title').textContent    = book.title;
  document.getElementById('create-author').textContent   = book.author;

  state.selectedRace = Object.keys(rules.races)[0];
  buildCharacterCreation();
  showScreen('create');
}

// ── CHARACTER CREATION ──────────────────────────────────────────────────────

const STAT_LABELS = {
  eletero:           'Életerő',
  tamadasi_kepesseg: 'Támadás',
  vedettsegi_szint:  'Védettség',
  szerencse:         'Szerencse',
  varazserő:         'Varázserő',
};

let rolledStats = {};

function rollStats() {
  for (const [key, stat] of Object.entries(rules.stats))
    rolledStats[key] = rollFormula(stat.roll);
}

function buildCharacterCreation() {
  rollStats();
  buildRaceGrid();
  renderStatRolls();
  wireCreationButtons();
}

function buildRaceGrid() {
  const grid = document.getElementById('race-grid');
  grid.innerHTML = '';
  for (const [key, race] of Object.entries(rules.races)) {
    const modLines = Object.entries(race.modifiers)
      .map(([s, v]) => `${STAT_LABELS[s] || s} ${v > 0 ? '+' : ''}${v}`)
      .join(', ');
    const card = document.createElement('div');
    card.className = 'race-card' + (state.selectedRace === key ? ' selected' : '');
    card.dataset.race = key;
    card.innerHTML = `
      <div class="race-card-name">${race.label}</div>
      <div class="race-card-desc">${race.description}</div>
      <div class="race-card-mods">${modLines || 'Nincs módosító'}</div>
    `;
    card.addEventListener('click', () => selectRace(key));
    grid.appendChild(card);
  }
}

function selectRace(key) {
  state.selectedRace = key;
  document.querySelectorAll('.race-card').forEach(c =>
    c.classList.toggle('selected', c.dataset.race === key));
  renderStatRolls();
}

function getModifiedStats() {
  const mods = rules.races[state.selectedRace]?.modifiers || {};
  const out  = {};
  for (const key of Object.keys(rolledStats))
    out[key] = rolledStats[key] + (mods[key] || 0);
  return out;
}

function renderStatRolls() {
  const grid = document.getElementById('stats-roll-grid');
  const mods = rules.races[state.selectedRace]?.modifiers || {};
  grid.innerHTML = '';
  for (const [key, label] of Object.entries(STAT_LABELS)) {
    const base  = rolledStats[key] || 0;
    const mod   = mods[key] || 0;
    const final = base + mod;
    let modHtml = '';
    if (mod !== 0) {
      const cls = mod > 0 ? 'pos' : 'neg';
      modHtml = `<span class="stat-roll-mod ${cls}">${mod > 0 ? '+' : ''}${mod}</span>`;
    }
    const item = document.createElement('div');
    item.className = 'stat-roll-item';
    item.innerHTML = `<span class="stat-roll-label">${label}</span>
                      <span class="stat-roll-value">${final}${modHtml}</span>`;
    grid.appendChild(item);
  }
}

function wireCreationButtons() {
  // Re-wire (remove old listeners by replacing elements)
  const reroll = document.getElementById('btn-reroll');
  const start  = document.getElementById('btn-start');
  const back   = document.getElementById('btn-back-to-menu');
  reroll.onclick = () => { rollStats(); renderStatRolls(); };
  start.onclick  = startGame;
  back.onclick   = () => showScreen('menu');
}

function startGame() {
  const modified = getModifiedStats();
  state.character.base    = { ...modified };
  state.character.current = { ...modified };
  state.character.max     = { ...modified };
  state.character.race    = state.selectedRace;
  state.character.inventory = buildStartingInventory();
  state.currentSection = 1;
  state.history = [];
  state.combat  = null;

  document.getElementById('sidebar-book-title').textContent = bookMeta?.title ?? '—';
  document.getElementById('mobile-book-title').textContent  = bookMeta?.title ?? '—';

  buildGameSidebar();
  showScreen('game');
  showPrologue();
}

function buildStartingInventory() {
  return rules.starting_equipment.map(item => ({
    name: item.item,
    qty:  item.quantity ?? 1,
    unit: item.unit    ?? null,
    note: item.note    ?? item.effect ?? null,
  }));
}

// ── PROLOGUE ─────────────────────────────────────────────────────────────────

const PROLOGUE_TEXT = `Előzmények

Jó nevű tolvaj vagy, ám az utóbbi időben egyre jobban izgat a mágia titokzatossága és hatalma. Tisztában vagy vele, hogy egy varázsló inasának hosszú éveket kell eltöltenie tanulással. Van egy egyszerűbb út is: a Mágusok Tornya, ahol szinte napok alatt elsajátíthatnád azt a tudáshalmazt, ami a mágia irányításához szükséges.

Hosszas gondolkodás után úgy döntesz, hogy inasnak szegődsz el Bairbas varázslóhoz, aki állítólag már járt a Mágusok Tornyában. Talán sikerül kihúznod belőle, te miként léphetnél oda be.

Hónapokat töltesz a varázslónál, közben óvatos kérdéseket teszel fel mesterédnek, aki semmit sem sejt céljaidról. Megtudod, hogy a varázsló a dolgozószobájában őriz egy könyvet, ami számos kérdésre választ ad.

Amikor a mestered nincs otthon, beosonsz a dolgozószobájába. A Tudások Könyvét kinyitva találod az asztalon, s amikor kimondod a kérdésed, a pergamenlapokon megjelenik a válasz: a Braildont-szigeten van egy üvegkulcs, aminek a segítségével bejuthatsz a Mágusok Tornyába.

Itt az alkalom, gondolod magadban.`;

function showPrologue() {
  const wrap    = document.getElementById('section-wrap');
  const numEl   = document.getElementById('section-number');
  const textEl  = document.getElementById('section-text');
  const choices = document.getElementById('choices');

  numEl.textContent  = 'Előzmények';
  textEl.textContent = PROLOGUE_TEXT;
  choices.innerHTML  = '';

  const btn = document.createElement('button');
  btn.className = 'choice-btn';
  btn.innerHTML = `<span>Kaland kezdése</span><span class="choice-arrow">→ 1</span>`;
  btn.addEventListener('click', () => loadSection(1));
  choices.appendChild(btn);

  wrap.classList.add('visible');
  document.getElementById('main').scrollTo({ top: 0 });
}

// ── GAME SIDEBAR ──────────────────────────────────────────────────────────────

function buildGameSidebar() {
  const race = rules.races[state.character.race];
  document.getElementById('race-badge').textContent = race?.label ?? '—';
  renderInventory();
  renderStats();
}

function renderStats() {
  const c = state.character.current;
  const m = state.character.max;

  const setBar = (key, barId) => {
    const pct = Math.max(0, Math.min(100, (c[key] / m[key]) * 100));
    const el  = document.getElementById(barId);
    if (el) el.style.width = pct + '%';
  };
  setBar('eletero',   'bar-eletero');
  setBar('varazserő', 'bar-varazserő');

  for (const key of Object.keys(STAT_LABELS)) {
    const el = document.getElementById(`val-${key}`);
    if (el) el.textContent = c[key] ?? '—';
  }

  const mobileHp = document.getElementById('mobile-hp');
  if (mobileHp) mobileHp.textContent = `${c.eletero} ÉL`;

  renderDrawerStats();
}

function renderDrawerStats() {
  const drawer = document.getElementById('drawer-stats');
  if (!drawer) return;
  const c = state.character.current;
  drawer.innerHTML = Object.entries(STAT_LABELS).map(([key, label]) => `
    <div class="drawer-stat-row">
      <span class="drawer-stat-label">${label}</span>
      <span class="drawer-stat-value">${c[key] ?? '—'}</span>
    </div>
  `).join('');
}

function renderInventory() {
  const list = document.getElementById('inventory-list');
  if (!list) return;
  list.innerHTML = '';

  state.character.inventory.forEach((item, idx) => {
    const action = getItemAction(item);
    const qtyStr = item.qty > 1
      ? `<span class="inventory-qty">×${item.qty}${item.unit ? ' ' + item.unit : ''}</span>`
      : '';
    const hint = action ? `<span class="item-hint">${action.hint}</span>` : '';

    const li = document.createElement('li');
    li.className = 'inventory-item' + (action ? ' has-action' : '');
    li.innerHTML = `
      <div class="inventory-item-row" data-idx="${idx}">
        <span>${item.name}</span>
        <div class="inventory-item-meta">${qtyStr}${hint}</div>
      </div>
      <div class="item-action-panel hidden" id="item-panel-${idx}"></div>
    `;
    if (action) {
      li.querySelector('.inventory-item-row').addEventListener('click', () => toggleItemPanel(idx, item, action));
    }
    list.appendChild(li);
  });
}

// ── INVENTORY ACTIONS ─────────────────────────────────────────────────────────

function getItemAction(item) {
  const note = item.note || '';
  const dmgMatch  = note.match(/(\d+-\d+)\s*veszteség/i);
  if (dmgMatch) return { type: 'weapon', damage: dmgMatch[1], hint: 'dob' };
  const healMatch = note.match(/(\d+)\s*életerőpontot?\s*gyógyít/i);
  if (healMatch) return { type: 'potion', heal: parseInt(healMatch[1]), hint: 'iszik' };
  const name = item.name.toLowerCase();
  if (name.includes('étel') || name.includes('élelem') || name.includes('kenyér') || name.includes('ennivaló'))
    return { type: 'food', hint: 'eszik' };
  return null;
}

function toggleItemPanel(idx, item, action) {
  const panel   = document.getElementById(`item-panel-${idx}`);
  const wasOpen = !panel.classList.contains('hidden');
  document.querySelectorAll('.item-action-panel').forEach(p => p.classList.add('hidden'));
  if (!wasOpen) {
    panel.classList.remove('hidden');
    renderItemPanel(panel, item, action, idx);
  }
}

function renderItemPanel(panel, item, action, idx) {
  if (action.type === 'weapon') {
    const formula = damageFormulaForRange(action.damage);
    panel.innerHTML = `
      <div class="item-panel-label">Sebzés: ${action.damage}</div>
      <button class="item-panel-btn" id="item-roll-${idx}">Sebzés dobása</button>
      <div class="item-panel-result hidden" id="item-res-${idx}"></div>
    `;
    document.getElementById(`item-roll-${idx}`).addEventListener('click', () => {
      const dmg = formula ? rollDamage(formula) : d6();
      const el  = document.getElementById(`item-res-${idx}`);
      el.classList.remove('hidden');
      el.textContent = `${dmg} pont sebzés`;
    });
  } else if (action.type === 'potion') {
    const cur  = state.character.current.eletero;
    const max  = state.character.max.eletero;
    const full = cur >= max;
    panel.innerHTML = `
      <div class="item-panel-label">+${action.heal} Életerő (max: ${max})</div>
      <button class="item-panel-btn" id="item-drink-${idx}" ${full ? 'disabled' : ''}>
        ${full ? 'Életerőd már teljes' : 'Megiszom'}
      </button>
    `;
    document.getElementById(`item-drink-${idx}`).addEventListener('click', () => {
      state.character.current.eletero = Math.min(max, cur + action.heal);
      consumeItem(idx);
    });
  } else if (action.type === 'food') {
    const mpCur = state.character.current['varazserő'];
    const mpMax = state.character.max['varazserő'];
    const full  = mpCur >= mpMax;
    panel.innerHTML = `
      <div class="item-panel-label">Pihenés és étkezés — +4 Varázserő</div>
      <button class="item-panel-btn" id="item-eat-${idx}" ${full ? 'disabled' : ''}>
        ${full ? 'Varázserőd már teljes' : `Elfogyaszt (marad: ${item.qty - 1} nap)`}
      </button>
    `;
    document.getElementById(`item-eat-${idx}`).addEventListener('click', () => {
      state.character.current['varazserő'] = Math.min(mpMax, mpCur + 4);
      consumeItem(idx);
    });
  }
}

function consumeItem(idx) {
  const item = state.character.inventory[idx];
  item.qty--;
  if (item.qty <= 0) state.character.inventory.splice(idx, 1);
  renderStats();
  renderInventory();
}

// ── SECTION LOADING ───────────────────────────────────────────────────────────

function loadSection(id) {
  const data = sections.sections[String(id)];
  state.combat = null;
  if (!data) { showSectionError(id); return; }
  state.currentSection = id;
  state.history.push(id);
  renderSection(data);
  renderStats();
  document.getElementById('main').scrollTo({ top: 0, behavior: 'smooth' });
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function renderSection(data) {
  const wrap      = document.getElementById('section-wrap');
  const numEl     = document.getElementById('section-number');
  const textEl    = document.getElementById('section-text');
  const choicesEl = document.getElementById('choices');

  numEl.textContent   = `${data.id}. szakasz`;
  textEl.textContent  = data.text;
  choicesEl.innerHTML = '';

  if (data.is_ending) { renderEnding(choicesEl); wrap.classList.add('visible'); return; }
  if (data.enemies?.length > 0) { renderCombatBlock(choicesEl, data); wrap.classList.add('visible'); return; }
  if (data.has_luck_test && data.choices.length >= 2) { renderLuckTestBlock(choicesEl, data); wrap.classList.add('visible'); return; }
  renderChoices(choicesEl, data.choices);
  wrap.classList.add('visible');
}

function renderChoices(container, choices) {
  choices.forEach(choice => {
    const btn = document.createElement('button');
    btn.className = 'choice-btn';
    const label = choice.text || `Lapozz a ${choice.target}. szakaszra`;
    btn.innerHTML = `<span>${label}</span><span class="choice-arrow">→ ${choice.target}</span>`;
    btn.addEventListener('click', () => loadSection(choice.target));
    container.appendChild(btn);
  });
}

function renderEnding(container) {
  const endDiv = document.createElement('div');
  endDiv.className = 'choice-btn dead-end';
  endDiv.textContent = 'A kaland véget ért.';
  container.appendChild(endDiv);
  const btn = document.createElement('button');
  btn.className = 'btn-secondary';
  btn.style.marginTop = '1rem';
  btn.textContent = 'Új kaland kezdése';
  btn.addEventListener('click', () => showScreen('menu'));
  container.appendChild(btn);
}

function showSectionError(id) {
  const wrap = document.getElementById('section-wrap');
  document.getElementById('section-number').textContent = `${id}. szakasz`;
  document.getElementById('section-text').textContent   = `Ez a szakasz (${id}) hiányzik az adatokból.`;
  document.getElementById('choices').innerHTML = '';
  wrap.classList.add('visible');
}

// ── LUCK TEST ─────────────────────────────────────────────────────────────────

function renderLuckTestBlock(container, data) {
  const block = document.createElement('div');
  block.className = 'system-block luck-block';
  block.innerHTML = `
    <div class="system-block-title">Szerencsepróba</div>
    <div class="system-block-desc">Dobj 2 kockával! Ha az eredmény kisebb vagy egyenlő a szerencse értékeddel, sikerült a próba. Szerencséd 1 ponttal csökken.</div>
    <div class="luck-current">Jelenlegi szerencse: <strong id="luck-display">${state.character.current.szerencse}</strong></div>
    <button class="btn-roll" id="btn-luck-roll">Dobás (2d6)</button>
    <div class="roll-result hidden" id="luck-result"></div>
  `;
  container.appendChild(block);
  document.getElementById('btn-luck-roll').addEventListener('click', () => {
    const roll   = roll2d6();
    const luck   = state.character.current.szerencse;
    const passed = roll <= luck;
    state.character.current.szerencse = Math.max(0, luck - 1);
    renderStats();
    const resultEl = document.getElementById('luck-result');
    resultEl.classList.remove('hidden');
    resultEl.innerHTML = `
      <span class="roll-dice">${roll}</span>
      <span class="roll-vs">vs ${luck}</span>
      <span class="roll-outcome ${passed ? 'success' : 'failure'}">${passed ? 'Sikeres!' : 'Sikertelen'}</span>
    `;
    document.getElementById('btn-luck-roll').disabled = true;
    setTimeout(() => {
      block.remove();
      const target = passed ? data.choices[0] : data.choices[1];
      if (target) loadSection(target.target);
      else renderChoices(container, data.choices);
    }, 1800);
  });
}

// ── COMBAT SYSTEM ─────────────────────────────────────────────────────────────

function renderCombatBlock(container, data) {
  state.combat = {
    enemies:            data.enemies.map(e => ({ ...e, currentHp: e.eletero })),
    sectionData:        data,
    doubleDamageRounds: 0,
    playerAttackBonus:  0,
  };
  const block = document.createElement('div');
  block.className = 'system-block combat-block';
  block.id = 'combat-block';
  container.appendChild(block);
  renderCombatUI(block);
}

function renderCombatUI(block) {
  const combat = state.combat;
  const player = state.character.current;
  const enemyRows = combat.enemies.map((e, i) => `
    <div class="combatant enemy-side" id="combatant-enemy-${i}">
      <div class="combatant-name ${e.currentHp <= 0 ? 'dead' : ''}">${e.name}</div>
      <div class="combatant-hp">
        <div class="combatant-hp-bar-wrap">
          <div class="combatant-hp-bar enemy-bar" id="enemy-hp-bar-${i}"
            style="width: ${e.currentHp <= 0 ? 0 : 100}%"></div>
        </div>
        <span id="enemy-hp-val-${i}">${Math.max(0, e.currentHp)} ÉL</span>
      </div>
      <div class="combatant-stat">Tám: ${e.tamadasi_kepesseg} &nbsp;|&nbsp; Véd: ${e.vedettsegi_szint}</div>
    </div>
  `).join('');

  block.innerHTML = `
    <div class="system-block-title">Harc</div>
    <div class="combat-layout">
      <div class="combatant player-side">
        <div class="combatant-name">Te</div>
        <div class="combatant-hp">
          <div class="combatant-hp-bar-wrap">
            <div class="combatant-hp-bar player-bar" id="player-hp-bar"
              style="width: ${Math.max(0,(player.eletero/state.character.max.eletero)*100)}%"></div>
          </div>
          <span id="player-hp-val">${player.eletero} ÉL</span>
        </div>
        <div class="combatant-stat">Tám: ${player.tamadasi_kepesseg} &nbsp;|&nbsp; Véd: ${player.vedettsegi_szint}</div>
      </div>
      <div class="combat-vs">VS</div>
      <div class="combat-enemies-col">${enemyRows}</div>
    </div>
    <div class="combat-log" id="combat-log"></div>
    <div class="combat-actions" id="combat-actions">
      <button class="btn-roll" id="btn-initiative">Kezdeményezés dobása</button>
    </div>
  `;
  document.getElementById('btn-initiative').addEventListener('click', rollInitiative);
}

function livingEnemies() {
  return state.combat.enemies.map((e, i) => ({ ...e, idx: i })).filter(e => e.currentHp > 0);
}

function rollInitiative() {
  const playerRoll = d6();
  const enemyRoll  = d6();
  const names = livingEnemies().map(e => e.name).join(' & ');
  addCombatLog(`Kezdeményezés: te ${playerRoll}, ${names} ${enemyRoll}`);
  if (playerRoll >= enemyRoll) { addCombatLog('Te támadsz először!'); showPlayerTurn(); }
  else { addCombatLog(`${names} támad először!`); showEnemyTurn(); }
}

function showPlayerTurn() {
  const actions     = document.getElementById('combat-actions');
  const alive       = livingEnemies();
  const multiTarget = alive.length > 1;

  if (canCastSpell()) {
    actions.innerHTML = `
      <div class="combat-action-row">
        <button class="btn-roll" id="btn-attack">⚔ Kard</button>
        <button class="btn-roll btn-magic" id="btn-spell">✦ Varázslat</button>
      </div>`;
    document.getElementById('btn-attack').addEventListener('click', () =>
      multiTarget ? showTargetButtons('sword') : resolvePlayerAttackOn(alive[0].idx));
    document.getElementById('btn-spell').addEventListener('click', () => showSpellPicker(multiTarget));
  } else {
    actions.innerHTML = `<button class="btn-roll" id="btn-attack">⚔ Támadás</button>`;
    document.getElementById('btn-attack').addEventListener('click', () =>
      multiTarget ? showTargetButtons('sword') : resolvePlayerAttackOn(alive[0].idx));
  }
}

function showTargetButtons(mode) {
  const actions = document.getElementById('combat-actions');
  const alive   = livingEnemies();
  const label   = mode === 'spell' ? 'Kire sütsz varázslatot?' : 'Kit támadsz?';
  actions.innerHTML = `
    <div class="target-label">${label}</div>
    ${alive.map(e => `
      <button class="btn-roll target-btn" data-idx="${e.idx}">${e.name} (${e.currentHp} ÉL)</button>
    `).join('')}
  `;
  actions.querySelectorAll('.target-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const idx = parseInt(btn.dataset.idx);
      if (mode === 'spell') {
        const { spell, cost } = state.combat._pendingSpell;
        delete state.combat._pendingSpell;
        resolveSpellDamage(spell, cost, idx);
      } else {
        resolvePlayerAttackOn(idx);
      }
    });
  });
}

function showEnemyTurn() {
  const actions = document.getElementById('combat-actions');
  const count   = livingEnemies().length;
  actions.innerHTML = `<button class="btn-roll" id="btn-enemy-turn">${count > 1 ? count + ' ellenfél támad' : 'Ellenfél támad'} (2d6 × ${count})</button>`;
  document.getElementById('btn-enemy-turn').addEventListener('click', resolveAllEnemiesAttack);
}

// ── MAGIC SYSTEM ──────────────────────────────────────────────────────────────

function canCastSpell() {
  const hasBook = state.character.inventory.some(i => i.name === 'Varázskőnyv');
  return hasBook && state.character.current['varazserő'] > 0;
}

// Player picks which spell to cast (replaces the old random 2d6 roll)
function showSpellPicker(multiTarget) {
  const actions = document.getElementById('combat-actions');
  const mp      = state.character.current['varazserő'];

  const spellRows = rules.attack_spells.map(spell => {
    const cost      = spell.cost === 'mind' ? mp : spell.cost;
    const canAfford = mp >= cost;
    const dmgLabel  = isNaN(parseInt(spell.damage)) ? 'különleges' : `${spell.damage} pont`;
    return `
      <button class="spell-pick-row ${canAfford ? '' : 'unaffordable'}"
              data-roll="${spell.roll}" ${canAfford ? '' : 'disabled'}>
        <div class="spell-pick-name">${spell.name}</div>
        <div class="spell-pick-meta">${cost} VE &nbsp;·&nbsp; ${dmgLabel}</div>
      </button>`;
  }).join('');

  actions.innerHTML = `
    <div class="spell-picker-wrap">
      <div class="spell-picker-header">
        <span class="spell-choice-label">Varázserő: <strong>${mp}</strong></span>
        <button class="btn-secondary" id="btn-spell-cancel">Vissza</button>
      </div>
      <div class="spell-picker-list">${spellRows}</div>
    </div>`;

  document.getElementById('btn-spell-cancel').addEventListener('click', showPlayerTurn);
  actions.querySelectorAll('.spell-pick-row:not([disabled])').forEach(btn => {
    btn.addEventListener('click', () => {
      const roll  = parseInt(btn.dataset.roll);
      const spell = rules.attack_spells.find(s => s.roll === roll);
      showSpellConfirm(spell, multiTarget);
    });
  });
}

function showSpellConfirm(spell, multiTarget) {
  const actions = document.getElementById('combat-actions');
  const mp      = state.character.current['varazserő'];
  const cost    = spell.cost === 'mind' ? mp : spell.cost;

  actions.innerHTML = `
    <div class="spell-result">
      <div class="spell-name">${spell.name}</div>
      <div class="spell-meta">Kész: ${cost} VE &nbsp;·&nbsp; Sebzés: ${spell.damage}</div>
      <div class="spell-desc">${spell.description}</div>
      <div class="spell-confirm-row">
        <button class="btn-secondary" id="btn-spell-back">← Vissza</button>
        <button class="btn-roll btn-magic" id="btn-cast-confirm">Elsütés!</button>
      </div>
    </div>`;

  document.getElementById('btn-spell-back').addEventListener('click', () => showSpellPicker(multiTarget));
  document.getElementById('btn-cast-confirm').addEventListener('click', () => {
    if (multiTarget) {
      state.combat._pendingSpell = { spell, cost };
      showTargetButtons('spell');
    } else {
      resolveSpellDamage(spell, cost, livingEnemies()[0].idx);
    }
  });
}

function resolveSpellDamage(spell, cost, targetIdx) {
  const enemy  = state.combat.enemies[targetIdx];
  const player = state.character.current;
  player['varazserő'] = Math.max(0, player['varazserő'] - cost);
  renderStats();

  let dmg = 0;
  const numericDmg = parseInt(spell.damage);
  if (!isNaN(numericDmg)) {
    dmg = numericDmg;
    addCombatLog(`${spell.name}: ${dmg} pont sebzés!`);
  } else {
    dmg = applySpellEffect(spell, enemy, player);
    if (dmg > 0) addCombatLog(`${spell.name}: ${dmg} pont sebzés.`);
  }

  enemy.currentHp -= dmg;
  updateEnemyHpBar(targetIdx);

  if (enemy.currentHp <= 0) {
    addCombatLog(`${enemy.name} elesett!`);
    markEnemyDead(targetIdx);
    if (livingEnemies().length === 0) { combatVictory(); return; }
  }
  setTimeout(showEnemyTurn, 800);
}

function applySpellEffect(spell, enemy, player) {
  switch (spell.name) {
    case 'Ködpatkány':
      return 12;
    case 'Vakság':
      enemy.tamadasi_kepesseg = Math.max(0, enemy.tamadasi_kepesseg - 5);
      addCombatLog(`${enemy.name} megvakult! Támadása −5 pontra csökkent.`);
      return 0;
    case 'Fullasztás':
      enemy.skipTurns = (enemy.skipTurns || 0) + 2;
      addCombatLog(`${enemy.name} fuldokol! Kihagyja a következő 2 körét.`);
      return 0;
    case 'Ártó Szem':
      enemy.vedettsegi_szint = Math.max(0, enemy.vedettsegi_szint - 5);
      addCombatLog(`${enemy.name} megremeg! Védettsége −5 pontra csökkent.`);
      return 0;
    case 'Erős Karok':
      player.tamadasi_kepesseg += 4;
      addCombatLog('Izmaid felpumpálódnak! +4 támadóerő.');
      return 0;
    case 'Kettős Csapás':
      state.combat.doubleDamageRounds = (state.combat.doubleDamageRounds || 0) + 4;
      addCombatLog('Kettős Csapás aktív! A következő 4 körben duplán hat a sebzés.');
      return 0;
    case 'Halálvarázs':
      addCombatLog(`${enemy.name} teste elöregszik és összeomlik!`);
      return enemy.currentHp + 999;
    default:
      return 10;
  }
}

function resolvePlayerAttackOn(targetIdx) {
  const roll   = roll2d6();
  const combat = state.combat;
  const enemy  = combat.enemies[targetIdx];
  const player = state.character.current;
  const power  = roll + player.tamadasi_kepesseg;

  addCombatLog(`Támadás ${enemy.name} ellen: ${roll} + ${player.tamadasi_kepesseg} = ${power} vs ${enemy.vedettsegi_szint}`);

  if (power > enemy.vedettsegi_szint) {
    let dmg = calcDamage(enemy.damage);
    if (combat.doubleDamageRounds > 0) {
      dmg *= 2;
      combat.doubleDamageRounds--;
      addCombatLog(`Kettős Csapás! (még ${combat.doubleDamageRounds} kör)`);
    }
    enemy.currentHp -= dmg;
    addCombatLog(`Találat! ${enemy.name} ${dmg} életerőt veszít. (marad: ${Math.max(0, enemy.currentHp)})`);
    updateEnemyHpBar(targetIdx);
    if (enemy.currentHp <= 0) {
      addCombatLog(`${enemy.name} elesett!`);
      markEnemyDead(targetIdx);
      if (livingEnemies().length === 0) { combatVictory(); return; }
    }
  } else {
    addCombatLog(`Kihagytad ${enemy.name}-t.`);
  }
  setTimeout(showEnemyTurn, 800);
}

async function resolveAllEnemiesAttack() {
  const combat = state.combat;
  const player = state.character.current;
  const alive  = livingEnemies();
  document.getElementById('combat-actions').innerHTML = '';

  for (const e of alive) {
    await new Promise(r => setTimeout(r, 600));
    if (e.skipTurns > 0) {
      state.combat.enemies[e.idx].skipTurns--;
      addCombatLog(`${e.name} fuldokol — kihagyja a kört!`);
      continue;
    }
    const roll  = roll2d6();
    const power = roll + e.tamadasi_kepesseg;
    addCombatLog(`${e.name}: ${roll} + ${e.tamadasi_kepesseg} = ${power} vs ${player.vedettsegi_szint}`);
    if (power > player.vedettsegi_szint) {
      const dmg = calcDamage(e.damage);
      player.eletero -= dmg;
      addCombatLog(`Találat! ${dmg} életerőt veszítesz. (marad: ${Math.max(0, player.eletero)})`);
      renderStats();
      updatePlayerHpBar();
      if (player.eletero <= 0) { combatDeath(); return; }
    } else {
      addCombatLog(`${e.name} elvétette a csapást.`);
    }
  }
  await new Promise(r => setTimeout(r, 400));
  showPlayerTurn();
}

function calcDamage(damageRange) {
  if (!damageRange) return 1;
  const formula = damageFormulaForRange(damageRange);
  return formula ? rollDamage(formula) : 1;
}

function updateEnemyHpBar(idx) {
  const enemy = state.combat.enemies[idx];
  const pct   = Math.max(0, (enemy.currentHp / enemy.eletero) * 100);
  const bar   = document.getElementById(`enemy-hp-bar-${idx}`);
  const val   = document.getElementById(`enemy-hp-val-${idx}`);
  if (bar) bar.style.width = pct + '%';
  if (val) val.textContent = `${Math.max(0, enemy.currentHp)} ÉL`;
}

function markEnemyDead(idx) {
  const nameEl = document.querySelector(`#combatant-enemy-${idx} .combatant-name`);
  if (nameEl) nameEl.classList.add('dead');
  updateEnemyHpBar(idx);
}

function updatePlayerHpBar() {
  const player = state.character.current;
  const pct    = Math.max(0, (player.eletero / state.character.max.eletero) * 100);
  const bar    = document.getElementById('player-hp-bar');
  const val    = document.getElementById('player-hp-val');
  if (bar) bar.style.width = pct + '%';
  if (val) val.textContent = `${Math.max(0, player.eletero)} ÉL`;
}

function addCombatLog(msg) {
  const log = document.getElementById('combat-log');
  if (!log) return;
  const line = document.createElement('div');
  line.className = 'log-line';
  line.textContent = msg;
  log.appendChild(line);
  log.scrollTop = log.scrollHeight;
}

function combatVictory() {
  addCombatLog('Győzelem!');
  const actions = document.getElementById('combat-actions');
  actions.innerHTML = '';
  const data = state.combat.sectionData;
  const victoryChoices = data.choices.filter(c =>
    !c.text || c.text.toLowerCase().includes('győz') ||
    !c.text.toLowerCase().includes('veszít'));
  renderChoices(actions, victoryChoices.length > 0 ? victoryChoices : data.choices);
}

function combatDeath() {
  addCombatLog('Meghaltál. A kaland véget ért.');
  const actions = document.getElementById('combat-actions');
  actions.innerHTML = `
    <div class="choice-btn dead-end">Életerőd nullára csökkent. Kalandod véget ért.</div>
    <button class="btn-secondary" style="margin-top:1rem">Főmenü</button>
  `;
  actions.querySelector('.btn-secondary').addEventListener('click', () => showScreen('menu'));
}

// ── SPELLBOOK MODAL ───────────────────────────────────────────────────────────

function showSpellbookModal() {
  renderSpellbookTab('attack');
  document.getElementById('spellbook-modal').classList.remove('hidden');
}

function renderSpellbookTab(tab) {
  const body   = document.getElementById('spellbook-body');
  const spells = tab === 'attack' ? rules.attack_spells : rules.defense_spells;
  const mp     = state.character.current?.['varazserő'] ?? Infinity;

  body.innerHTML = spells.map(spell => {
    const cost      = spell.cost === 'mind' ? 'Összes VE' : `${spell.cost} VE`;
    const canAfford = spell.cost === 'mind'
      ? mp >= (spell.cost_min ?? 0)
      : mp >= spell.cost;

    if (tab === 'attack') {
      const dmgLabel = isNaN(parseInt(spell.damage)) ? 'különleges' : `${spell.damage} pont sebzés`;
      return `
        <div class="spellbook-entry ${canAfford ? '' : 'unaffordable'}">
          <div class="spellbook-entry-header">
            <span class="spellbook-spell-name">${spell.name}</span>
            <span class="spellbook-spell-cost">${cost}</span>
          </div>
          <div class="spellbook-spell-damage">${dmgLabel}</div>
          <div class="spellbook-spell-desc">${spell.description}</div>
        </div>`;
    } else {
      return `
        <div class="spellbook-entry ${canAfford ? '' : 'unaffordable'}">
          <div class="spellbook-entry-header">
            <span class="spellbook-spell-name">${spell.name}</span>
            <span class="spellbook-spell-cost">${cost}</span>
          </div>
          <div class="spellbook-spell-damage">Véd: ${spell.protects_against} &nbsp;·&nbsp; Dobás: 1–${spell.activation_roll.split('-')[1]}</div>
          <div class="spellbook-spell-desc">${spell.description}</div>
        </div>`;
    }
  }).join('');

  // Update tab active state
  document.querySelectorAll('.modal-tab').forEach(t => {
    t.classList.toggle('active', t.dataset.tab === tab);
  });
}

// ── SAVE / LOAD SYSTEM ────────────────────────────────────────────────────────

function getSaves() {
  try { return JSON.parse(localStorage.getItem(SAVES_KEY) || '[]'); }
  catch { return []; }
}

function putSaves(saves) {
  localStorage.setItem(SAVES_KEY, JSON.stringify(saves));
}

function saveGame(name) {
  const saves = getSaves();
  const slot  = {
    name,
    bookId:    bookMeta?.id ?? 'unknown',
    bookTitle: bookMeta?.title ?? '—',
    section:   state.currentSection,
    timestamp: Date.now(),
    character: JSON.parse(JSON.stringify(state.character)),
    history:   [...state.history],
  };
  // Replace existing save with same name, otherwise prepend
  const idx = saves.findIndex(s => s.name === name);
  if (idx >= 0) saves[idx] = slot;
  else saves.unshift(slot);
  putSaves(saves.slice(0, 10)); // max 10 saves
}

function loadSave(slot) {
  if (!rules || !sections || slot.bookId !== bookMeta?.id) {
    alert('Ehhez a mentéshez először válaszd ki a megfelelő könyvet!');
    return;
  }
  state.character     = JSON.parse(JSON.stringify(slot.character));
  state.history       = [...slot.history];
  state.currentSection = slot.section;
  state.combat        = null;

  buildGameSidebar();
  closeModal('saveload-modal');
  showScreen('game');
  loadSection(slot.section);
}

function showSaveLoadModal() {
  renderSaveLoadBody();
  document.getElementById('saveload-modal').classList.remove('hidden');
}

function renderSaveLoadBody() {
  const body  = document.getElementById('saveload-body');
  const saves = getSaves();
  const inGame = document.getElementById('screen-game').classList.contains('active');

  let saveSection = '';
  if (inGame) {
    saveSection = `
      <div class="saveload-section">
        <div class="saveload-section-title">Játék mentése</div>
        <div class="save-input-row">
          <input class="save-name-input" id="save-name-input" type="text"
            placeholder="Mentés neve..." maxlength="32"
            value="Szakasz ${state.currentSection}">
          <button class="btn-primary save-btn" id="btn-do-save">Mentés</button>
        </div>
      </div>
      <div class="sidebar-divider" style="margin:1rem 0"></div>`;
  }

  const slotRows = saves.length === 0
    ? '<div class="saveload-empty">Még nincsenek mentett játékok.</div>'
    : saves.map((s, i) => {
        const date = new Date(s.timestamp).toLocaleDateString('hu-HU', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
        return `
          <div class="save-slot">
            <div class="save-slot-info">
              <div class="save-slot-name">${s.name}</div>
              <div class="save-slot-meta">${s.bookTitle} · ${s.section}. szakasz · ${date}</div>
            </div>
            <div class="save-slot-actions">
              <button class="item-panel-btn" data-load="${i}">Betöltés</button>
              <button class="item-panel-btn danger" data-delete="${i}">Törlés</button>
            </div>
          </div>`;
      }).join('');

  body.innerHTML = `
    ${saveSection}
    <div class="saveload-section">
      <div class="saveload-section-title">Mentett játékok</div>
      ${slotRows}
    </div>`;

  body.querySelector('#btn-do-save')?.addEventListener('click', () => {
    const name = document.getElementById('save-name-input').value.trim() || `Szakasz ${state.currentSection}`;
    saveGame(name);
    renderSaveLoadBody();
  });

  body.querySelectorAll('[data-load]').forEach(btn => {
    btn.addEventListener('click', () => loadSave(saves[parseInt(btn.dataset.load)]));
  });

  body.querySelectorAll('[data-delete]').forEach(btn => {
    btn.addEventListener('click', () => {
      const updated = getSaves();
      updated.splice(parseInt(btn.dataset.delete), 1);
      putSaves(updated);
      renderSaveLoadBody();
    });
  });
}

// ── MODALS ────────────────────────────────────────────────────────────────────

function closeModal(id) {
  document.getElementById(id).classList.add('hidden');
}

function initModals() {
  // Spellbook
  document.getElementById('btn-spellbook').addEventListener('click', showSpellbookModal);
  document.getElementById('btn-close-spellbook').addEventListener('click', () => closeModal('spellbook-modal'));
  document.querySelectorAll('.modal-tab').forEach(tab => {
    tab.addEventListener('click', () => renderSpellbookTab(tab.dataset.tab));
  });

  // Save/Load
  document.getElementById('btn-save-load').addEventListener('click', showSaveLoadModal);
  document.getElementById('btn-close-saveload').addEventListener('click', () => closeModal('saveload-modal'));

  // Close modals on overlay click
  document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', e => {
      if (e.target === overlay) overlay.classList.add('hidden');
    });
  });
}

// ── MOBILE DRAWER ─────────────────────────────────────────────────────────────

function initDrawer() {
  const toggle  = document.getElementById('btn-stats-toggle');
  const overlay = document.getElementById('drawer-overlay');
  const drawer  = document.getElementById('mobile-drawer');
  const open    = () => { overlay.classList.add('visible'); drawer.classList.add('open'); };
  const close   = () => { overlay.classList.remove('visible'); drawer.classList.remove('open'); };
  toggle.addEventListener('click', open);
  overlay.addEventListener('click', close);
}

// ── UI HELPERS ────────────────────────────────────────────────────────────────

function showScreen(name) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  document.getElementById(`screen-${name}`).classList.add('active');
}

function showLoading(on) {
  document.getElementById('loading').classList.toggle('visible', on);
}

// ── INIT ──────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('btn-new-game')?.addEventListener('click', () => showScreen('menu'));
  initDrawer();
  initModals();
  init();
});

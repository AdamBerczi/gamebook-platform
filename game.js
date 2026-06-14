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
    const bust = `?v=${Date.now()}`;
    const [rulesResp, sectionsResp] = await Promise.all([
      fetch(book.rules + bust),
      fetch(book.sections + bust),
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
  const race = rules.races[state.selectedRace] || {};
  const mods = race.modifiers || {};
  const out  = {};
  for (const key of Object.keys(rolledStats)) {
    let val = rolledStats[key] + (mods[key] || 0);
    if (race.varazserő_halve && key === 'varazserő') val = Math.floor(val / 2);
    out[key] = val;
  }
  return out;
}

function renderStatRolls() {
  const grid = document.getElementById('stats-roll-grid');
  const race = rules.races[state.selectedRace] || {};
  const mods = race.modifiers || {};
  grid.innerHTML = '';
  for (const [key, label] of Object.entries(STAT_LABELS)) {
    const base  = rolledStats[key] || 0;
    const mod   = mods[key] || 0;
    let final   = base + mod;
    let modHtml = '';
    if (race.varazserő_halve && key === 'varazserő') {
      final = Math.floor(final / 2);
      modHtml = `<span class="stat-roll-mod neg">÷2</span>`;
    } else if (mod !== 0) {
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
  state.character.race      = state.selectedRace;
  state.character.inventory = [];   // filled on first visit to section 1

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
    name:       item.item,
    qty:        item.quantity  ?? 1,
    unit:       item.unit      ?? null,
    note:       item.note      ?? item.effect ?? null,
    stat_bonus: item.stat_bonus ?? null,
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
  textEl.textContent = rules.prologue || PROLOGUE_TEXT;
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

function getItemTooltip(item) {
  const parts = [];
  if (item.note) parts.push(item.note);
  if (item.stat_bonus) {
    const STAT_NAMES = { eletero: 'Életerő', tamadasi_kepesseg: 'Támadás', vedettsegi_szint: 'Védettség', szerencse: 'Szerencse', 'varazserő': 'Varázserő' };
    parts.push(Object.entries(item.stat_bonus).map(([k, v]) => `+${v} ${STAT_NAMES[k] ?? k}`).join(', '));
  }
  return parts.join(' · ') || null;
}

function renderInventory() {
  const list = document.getElementById('inventory-list');
  if (!list) return;
  list.innerHTML = '';

  state.character.inventory.forEach((item, idx) => {
    const action  = getItemAction(item);
    const tooltip = getItemTooltip(item);
    const qtyStr  = item.qty > 1
      ? `<span class="inventory-qty">×${item.qty}${item.unit ? ' ' + item.unit : ''}</span>`
      : '';
    const hint = action ? `<span class="item-hint">${action.hint}</span>` : '';

    const li = document.createElement('li');
    li.className = 'inventory-item' + (action ? ' has-action' : '');
    if (tooltip) li.dataset.tooltip = tooltip;
    li.innerHTML = `
      <div class="inventory-item-row" data-idx="${idx}">
        <span>${item.name}</span>
        <div class="inventory-item-meta">${qtyStr}${hint}</div>
      </div>
      ${tooltip ? `<div class="item-tooltip-box">${tooltip}</div>` : ''}
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
  const healMatch = note.match(/(\d+)\s*életerőpontot?\s*gyógyít/i);
  if (healMatch) return { type: 'potion', heal: parseInt(healMatch[1]), hint: 'iszik' };
  const name = item.name.toLowerCase();
  if (name.includes('gyorsító')) return { type: 'gyorsito', hint: 'iszik' };
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
  if (action.type === 'potion') {
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
  } else if (action.type === 'gyorsito') {
    const inCombat = !!state.combat;
    const alreadyActive = inCombat && state.combat.speedPotion;
    panel.innerHTML = `
      <div class="item-panel-label">Körönként két támadás ebben a harcban</div>
      <button class="item-panel-btn" id="item-gyorsito-${idx}" ${!inCombat || alreadyActive ? 'disabled' : ''}>
        ${!inCombat ? 'Csak harcban használható' : alreadyActive ? 'Már aktív' : 'Beiszom'}
      </button>
    `;
    document.getElementById(`item-gyorsito-${idx}`).addEventListener('click', () => {
      state.combat.speedPotion = true;
      consumeItem(idx);
      addCombatLog('⚡ Gyorsító ital: mostantól körönként kétszer támadhatsz!');
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
  if (item.qty <= 0) {
    revertItemStatBonus(item);
    state.character.inventory.splice(idx, 1);
  }
  renderStats();
  renderInventory();
}

// ── Item stat bonus helpers ───────────────────────────────────────────────────

function applyItemStatBonus(item) {
  if (!item.stat_bonus) return;
  for (const [stat, val] of Object.entries(item.stat_bonus)) {
    state.character.current[stat] = (state.character.current[stat] || 0) + val;
    state.character.max[stat]     = (state.character.max[stat]     || 0) + val;
  }
}

function revertItemStatBonus(item) {
  if (!item.stat_bonus) return;
  for (const [stat, val] of Object.entries(item.stat_bonus)) {
    state.character.current[stat] = (state.character.current[stat] || 0) - val;
    state.character.max[stat]     = (state.character.max[stat]     || 0) - val;
  }
}

function addItemToInventory(itemDef) {
  const existing = state.character.inventory.find(i => i.name === itemDef.item);
  if (existing && !itemDef.unique) {
    existing.qty += itemDef.quantity ?? 1;
  } else if (!existing) {
    const newItem = {
      name:       itemDef.item,
      qty:        itemDef.quantity  ?? 1,
      unit:       itemDef.unit      ?? null,
      note:       itemDef.note      ?? itemDef.effect ?? null,
      stat_bonus: itemDef.stat_bonus ?? null,
    };
    state.character.inventory.push(newItem);
    if (newItem.stat_bonus) applyItemStatBonus(newItem);
  }
  showItemToast(itemDef.item, true);
  renderInventory();
  renderStats();
}

function removeItemByName(name) {
  const idx = state.character.inventory.findIndex(i => i.name === name);
  if (idx === -1) return;
  revertItemStatBonus(state.character.inventory[idx]);
  state.character.inventory.splice(idx, 1);
  showItemToast(name, false);
  renderInventory();
  renderStats();
}

// ── SECTION LOADING ───────────────────────────────────────────────────────────

function loadSection(id) {
  const data = sections.sections[String(id)];
  state.combat = null;
  if (!data) { showSectionError(id); return; }
  state.currentSection = id;
  state.history.push(id);
  if (data.gold_cost) deductGold(data.gold_cost);

  // First-visit item exchanges (takes_items / gives_items)
  const firstVisit = state.history.filter(x => x === id).length === 1;
  if (firstVisit) {
    // Section 1: hand out starting equipment from rules.json
    if (id === 1 && rules.starting_equipment?.length) {
      for (const eq of buildStartingInventory()) {
        addItemToInventory({ item: eq.name, quantity: eq.qty, unit: eq.unit, note: eq.note, stat_bonus: eq.stat_bonus });
      }
    }
    if (data.takes_items?.length) {
      for (const name of data.takes_items) removeItemByName(name);
    }
    if (data.gives_items?.length) {
      for (const gi of data.gives_items) addItemToInventory(gi);
    }
  }

  renderSection(data);
  renderStats();
  document.getElementById('main').scrollTo({ top: 0, behavior: 'smooth' });
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function deductGold(amount) {
  const gold = state.character.inventory.find(i => i.name === 'Aranypénz');
  if (!gold) return;
  const actual = Math.min(amount, gold.qty);
  gold.qty -= actual;
  if (gold.qty <= 0) state.character.inventory = state.character.inventory.filter(i => i.name !== 'Aranypénz');
  showGoldToast(actual, gold.qty >= 0 ? gold.qty : 0);
  renderInventory();
}

function showGoldToast(spent, remaining) {
  const existing = document.getElementById('gold-toast');
  if (existing) existing.remove();
  const toast = document.createElement('div');
  toast.id = 'gold-toast';
  toast.className = 'gold-toast';
  toast.innerHTML = `<span class="gold-toast-icon">🪙</span> −${spent} arany <span class="gold-toast-remain">(marad: ${remaining})</span>`;
  document.getElementById('main').appendChild(toast);
  setTimeout(() => toast.classList.add('gold-toast-show'), 10);
  setTimeout(() => { toast.classList.remove('gold-toast-show'); setTimeout(() => toast.remove(), 400); }, 3000);
}

let _itemToastQueue = [];
function showItemToast(name, gained) {
  _itemToastQueue.push({ name, gained });
  if (_itemToastQueue.length > 1) return; // already draining
  drainItemToastQueue();
}
function drainItemToastQueue() {
  if (!_itemToastQueue.length) return;
  const { name, gained } = _itemToastQueue[0];
  const existing = document.getElementById('item-toast');
  if (existing) existing.remove();
  const toast = document.createElement('div');
  toast.id = 'item-toast';
  toast.className = 'item-toast ' + (gained ? 'item-toast-gain' : 'item-toast-loss');
  toast.innerHTML = `${gained ? '＋' : '－'} ${name}`;
  document.getElementById('main').appendChild(toast);
  setTimeout(() => toast.classList.add('item-toast-show'), 10);
  setTimeout(() => {
    toast.classList.remove('item-toast-show');
    setTimeout(() => { toast.remove(); _itemToastQueue.shift(); drainItemToastQueue(); }, 350);
  }, 1800);
}

function renderSection(data) {
  const wrap      = document.getElementById('section-wrap');
  const numEl     = document.getElementById('section-number');
  const textEl    = document.getElementById('section-text');
  const choicesEl = document.getElementById('choices');

  numEl.textContent   = `${data.id}. szakasz`;
  textEl.textContent  = data.text;
  choicesEl.innerHTML = '';
  loadSectionIllustration(data.id);

  if (data.is_ending) { renderEnding(choicesEl); wrap.classList.add('visible'); return; }
  if (data.enemies?.length > 0) { renderCombatBlock(choicesEl, data); wrap.classList.add('visible'); return; }
  if (data.has_luck_test && data.choices.length >= 2) { renderLuckTestBlock(choicesEl, data); wrap.classList.add('visible'); return; }
  if (data.has_shop) renderShopBlock(choicesEl, data);
  renderChoices(choicesEl, data.choices);
  wrap.classList.add('visible');
}

function loadSectionIllustration(id) {
  const wrap = document.getElementById('section-illustration');
  const img  = document.getElementById('section-illustration-img');
  if (!wrap || !img || !bookMeta?.images) return;
  wrap.classList.add('hidden');
  img.src = '';
  img.onload  = () => wrap.classList.remove('hidden');
  img.onerror = () => wrap.classList.add('hidden');
  img.src = `${bookMeta.images}/${id}.jpg`;
}

function renderChoices(container, choices) {
  choices.forEach(choice => {
    const btn   = document.createElement('button');
    const label = choice.text || `Lapozz a ${choice.target}. szakaszra`;
    const reqs  = choice.requires ?? [];
    const missing = reqs.filter(n => !state.character.inventory.some(i => i.name === n));
    const locked  = missing.length > 0;

    btn.className = 'choice-btn' + (locked ? ' choice-locked' : '');
    if (locked) {
      btn.disabled = true;
      btn.innerHTML = `<span>${label}</span><span class="choice-arrow choice-lock-tag">🔒 ${missing.join(', ')}</span>`;
    } else {
      btn.innerHTML = `<span>${label}</span><span class="choice-arrow">→ ${choice.target}</span>`;
      btn.addEventListener('click', () => loadSection(choice.target));
    }
    container.appendChild(btn);
  });
}

// ── SHOP SYSTEM ──────────────────────────────────────────────────────────────

function renderShopBlock(container, data) {
  const block = document.createElement('div');
  block.className = 'system-block shop-block';
  block.id = 'shop-block';
  container.appendChild(block);
  refreshShopBlock(block, data.shop.items);
}

function refreshShopBlock(block, items) {
  const gold = state.character.inventory.find(i => i.name === 'Aranypénz');
  const goldAmt = gold?.qty ?? 0;
  block.innerHTML = `
    <div class="shop-header">
      <span class="shop-title">🏪 Bolt</span>
      <span class="shop-gold">🪙 ${goldAmt} arany</span>
    </div>
    <div class="shop-items-grid"></div>
  `;
  const grid = block.querySelector('.shop-items-grid');
  items.forEach((shopItem, idx) => {
    const owned    = shopItem.unique && state.character.inventory.some(i => i.name === shopItem.item);
    const canAfford = goldAmt >= shopItem.price;
    const desc = shopItem.note ?? shopItem.effect ?? '';
    const row = document.createElement('div');
    row.className = 'shop-item-row';
    row.innerHTML = `
      <div class="shop-item-info">
        <span class="shop-item-name">${shopItem.item}</span>
        ${desc ? `<span class="shop-item-desc">${desc}</span>` : ''}
      </div>
      <div class="shop-item-buy">
        <span class="shop-item-price">🪙 ${shopItem.price}</span>
        <button class="shop-buy-btn" data-idx="${idx}"
          ${owned || !canAfford ? 'disabled' : ''}>
          ${owned ? 'Megvan' : !canAfford ? 'Kevés arany' : 'Megvesz'}
        </button>
      </div>
    `;
    grid.appendChild(row);
  });
  grid.querySelectorAll('.shop-buy-btn:not([disabled])').forEach(btn => {
    btn.addEventListener('click', () => {
      buyShopItem(items[parseInt(btn.dataset.idx)]);
      refreshShopBlock(block, items);
    });
  });
}

function buyShopItem(shopItem) {
  deductGold(shopItem.price);
  addItemToInventory({
    item:       shopItem.item,
    quantity:   shopItem.quantity ?? 1,
    note:       shopItem.note   ?? null,
    effect:     shopItem.effect ?? null,
    stat_bonus: shopItem.stat_bonus ?? null,
    unique:     shopItem.unique ?? false,
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
    enemies:             data.enemies.map(e => ({ ...e, currentHp: e.eletero })),
    sectionData:         data,
    playerAttackBonus:   0,   // current active bonus (Erős Karok)
    strongArmAttacksLeft: 0,  // remaining player attacks with the bonus
    speedPotion:         false, // Gyorsító ital: two attacks per round
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
      <div class="combatant-stat" id="enemy-stat-${i}">Tám: ${e.tamadasi_kepesseg} &nbsp;|&nbsp; Véd: ${e.vedettsegi_szint}</div>
      <div class="enemy-status-badges" id="enemy-status-${i}"></div>
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
      } else if (mode === 'sword2') {
        resolvePlayerAttackOn(idx, true);
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
    dmg = applySpellEffect(spell, enemy, player, targetIdx);
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

function applySpellEffect(spell, enemy, player, targetIdx) {
  switch (spell.name) {

    // DoT: 3 dmg/round for 4 rounds — ticks at the START of each enemy phase
    case 'Ködpatkány':
      enemy.fogRatRounds = 4;
      addCombatLog(`Ködpatkány materializálódik! ${enemy.name} körönként 3 ÉL veszteséget szenved el 4 körön át.`);
      updateEnemyStatusBadges(targetIdx);
      return 0;

    // −5 attack for 3 of the enemy's attacks, then reverts
    case 'Vakság':
      enemy._blindAttackMalus = 5;
      enemy.tamadasi_kepesseg = Math.max(0, enemy.tamadasi_kepesseg - 5);
      enemy.blindedRounds = 3;
      addCombatLog(`${enemy.name} megvakult! Támadása −5, elveszíti a kezdeményezést. (3 körig tart)`);
      updateEnemyStatusBadges(targetIdx);
      updateEnemyStatLine(targetIdx);
      return 0;

    // Skip 2 turns entirely
    case 'Fullasztás':
      enemy.skipTurns = (enemy.skipTurns || 0) + 2;
      addCombatLog(`${enemy.name} fuldokol! Kihagyja a következő 2 körét.`);
      updateEnemyStatusBadges(targetIdx);
      return 0;

    // −5 defense for 2 of the enemy's attacks, then reverts
    case 'Ártó Szem':
      enemy._artóSzemDefMalus = 5;
      enemy.vedettsegi_szint = Math.max(0, enemy.vedettsegi_szint - 5);
      enemy.artóSzemRounds = 2;
      addCombatLog(`${enemy.name} megremeg! Védelme −5, elveszíti a kezdeményezést. (2 körig tart)`);
      updateEnemyStatusBadges(targetIdx);
      updateEnemyStatLine(targetIdx);
      return 0;

    // +4 player attack for 5 of the player's sword attacks, then reverts
    case 'Erős Karok':
      // Cancel any previous Erős Karok first
      player.tamadasi_kepesseg -= state.combat.playerAttackBonus;
      state.combat.playerAttackBonus = 4;
      state.combat.strongArmAttacksLeft = 5;
      player.tamadasi_kepesseg += 4;
      addCombatLog(`Izmaid felpumpálódnak! +4 támadóerő a következő 5 csapásra.`);
      renderStats();
      return 0;

    // Target takes double damage from sword for 4 rounds
    case 'Kettős Csapás':
      enemy.doubleDamageRounds = 4;
      addCombatLog(`${enemy.name} ${enemy.doubleDamageRounds} körön át duplán veszi a sebzést!`);
      updateEnemyStatusBadges(targetIdx);
      return 0;

    // Instant kill — doesn't work on undead
    case 'Halálvarázs':
      if (enemy.undead) {
        addCombatLog(`A Halálvarázs nem hat ${enemy.name}-re (holtán-túli lény)!`);
        return 0;
      }
      addCombatLog(`${enemy.name} teste rendkívüli gyorsasággal elöregszik és összeomlik!`);
      return enemy.currentHp + 999;

    // Savgömb: elveszíti életerőpontjai felét
    case 'Savgömb': {
      const savDmg = Math.floor(enemy.currentHp / 2);
      addCombatLog(`Savgömb felrobban! ${enemy.name} elveszíti életerőpontjai felét (${savDmg} pont).`);
      return savDmg;
    }

    // Láthatatlan Harcos: automatikusan 5 pont sebzés körönként 5 körön át → DoT
    case 'Láthatatlan Harcos':
      enemy.fogRatRounds = 5;
      enemy._fogRatDmg   = 5;
      addCombatLog(`Láthatatlan Harcos materializálódik! ${enemy.name} körönként 5 ÉL veszteséget szenved el 5 körön át.`);
      updateEnemyStatusBadges(targetIdx);
      return 0;

    // Tűzlehelet: 2 körön át fele annyi sebzés, ahány ÉL van a varázslónak → egyszerűsítve: ÉL/4
    case 'Tűzlehelet': {
      const fireDmg = Math.max(1, Math.floor(player.eletero / 4));
      addCombatLog(`Tűzlehelet! ${enemy.name} ${fireDmg} pont tűzsebzést szenved el.`);
      return fireDmg;
    }

    // Erősítés/Gyengítés: +4 játékos támadás ÉS −4 ellenfél támadás, 5 körig
    case 'Erősítés/Gyengítés':
      player.tamadasi_kepesseg -= state.combat.playerAttackBonus;
      state.combat.playerAttackBonus = 4;
      state.combat.strongArmAttacksLeft = 5;
      player.tamadasi_kepesseg += 4;
      enemy._blindAttackMalus = (enemy._blindAttackMalus || 0) + 4;
      enemy.tamadasi_kepesseg = Math.max(0, enemy.tamadasi_kepesseg - 4);
      enemy.blindedRounds = Math.max(enemy.blindedRounds || 0, 5);
      addCombatLog(`Erősítés: +4 támadóerőd. Gyengítés: ${enemy.name} −4 támadás 5 körig.`);
      renderStats();
      updateEnemyStatLine(targetIdx);
      return 0;

    // Empátia Pajzs: a következő 3 körben az ellenfél visszakap fél sebzést
    case 'Empátia Pajzs':
      state.combat.empátiaPajzsRounds = 3;
      addCombatLog(`Empátia Pajzs aktív! A következő 3 körben az ellenfél sebzésének felét visszaszenvedi.`);
      return 0;

    default:
      return 0;
  }
}

// Re-render the Tám/Véd stat line under an enemy combatant
function updateEnemyStatLine(idx) {
  const e  = state.combat.enemies[idx];
  const el = document.getElementById(`enemy-stat-${idx}`);
  if (el) el.innerHTML = `Tám: ${e.tamadasi_kepesseg} &nbsp;|&nbsp; Véd: ${e.vedettsegi_szint}`;
}

// Render coloured status badges (Ködpatkány, Vakság, Ártó Szem, Kettős Csapás, Fullasztás)
function updateEnemyStatusBadges(idx) {
  const e   = state.combat.enemies[idx];
  const el  = document.getElementById(`enemy-status-${idx}`);
  if (!el) return;
  const badges = [];
  if (e.fogRatRounds   > 0) badges.push(`<span class="status-badge badge-dot">🐀 Ködpatkány ×${e.fogRatRounds}</span>`);
  if (e.blindedRounds  > 0) badges.push(`<span class="status-badge badge-debuff">👁 Vak ×${e.blindedRounds}</span>`);
  if (e.artóSzemRounds > 0) badges.push(`<span class="status-badge badge-debuff">🎯 Ártó Szem ×${e.artóSzemRounds}</span>`);
  if (e.doubleDamageRounds > 0) badges.push(`<span class="status-badge badge-amp">⚡ 2× sebzés ×${e.doubleDamageRounds}</span>`);
  if ((e.skipTurns     || 0) > 0) badges.push(`<span class="status-badge badge-stun">💨 Fullaszt ×${e.skipTurns}</span>`);
  el.innerHTML = badges.join('');
}

function resolvePlayerAttackOn(targetIdx, secondAttack = false) {
  const roll   = roll2d6();
  const combat = state.combat;
  const enemy  = combat.enemies[targetIdx];
  const player = state.character.current;
  const power  = roll + player.tamadasi_kepesseg;

  addCombatLog(`Támadás ${enemy.name} ellen: ${roll} + ${player.tamadasi_kepesseg} = ${power} vs ${enemy.vedettsegi_szint}`);

  // Consume one Erős Karok charge per attack (hit or miss)
  if (combat.strongArmAttacksLeft > 0) {
    combat.strongArmAttacksLeft--;
    if (combat.strongArmAttacksLeft === 0) {
      player.tamadasi_kepesseg -= combat.playerAttackBonus;
      combat.playerAttackBonus = 0;
      addCombatLog(`Az Erős Karok hatása lejárt. Támadóerőd visszaállt.`);
      renderStats();
    }
  }

  if (power > enemy.vedettsegi_szint) {
    let dmg = calcDamage(enemy.damage);
    // Per-enemy Kettős Csapás: only sword damage is doubled (not spells)
    if ((enemy.doubleDamageRounds || 0) > 0) {
      dmg *= 2;
      enemy.doubleDamageRounds--;
      updateEnemyStatusBadges(targetIdx);
      addCombatLog(`Kettős Csapás! ${dmg} pont (${enemy.doubleDamageRounds > 0 ? 'még ' + enemy.doubleDamageRounds + ' kör' : 'lejárt'})`);
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

  // Gyorsító ital: second swing this round (only once per round)
  const stillAlive = livingEnemies();
  if (combat.speedPotion && !secondAttack && stillAlive.length > 0) {
    addCombatLog('⚡ Gyorsító ital: második csapás!');
    setTimeout(() => {
      if (stillAlive.length > 1) {
        showTargetButtons('sword2');
      } else {
        resolvePlayerAttackOn(stillAlive[0].idx, true);
      }
    }, 800);
  } else {
    setTimeout(showEnemyTurn, 800);
  }
}

async function resolveAllEnemiesAttack() {
  const combat = state.combat;
  const player = state.character.current;
  const alive  = livingEnemies();
  document.getElementById('combat-actions').innerHTML = '';

  // ── Ködpatkány DoT: ticks once per round before enemies attack ──
  for (const e of alive) {
    const enemy = combat.enemies[e.idx];
    if ((enemy.fogRatRounds || 0) > 0) {
      await new Promise(r => setTimeout(r, 400));
      const dot = enemy._fogRatDmg || 3;
      enemy.currentHp -= dot;
      enemy.fogRatRounds--;
      updateEnemyHpBar(e.idx);
      updateEnemyStatusBadges(e.idx);
      const dotName = enemy._fogRatDmg === 5 ? '⚔️ Láthatatlan Harcos' : '🐀 Ködpatkány';
      addCombatLog(`${dotName}: ${enemy.name} ${dot} ÉL veszteség. (még ${enemy.fogRatRounds} kör)`);
      if (enemy.currentHp <= 0) {
        addCombatLog(`${enemy.name} elesett!`);
        markEnemyDead(e.idx);
      }
    }
  }

  // Check if all died from DoT
  if (livingEnemies().length === 0) { combatVictory(); return; }

  // ── Each living enemy attacks ──
  for (const e of livingEnemies()) {
    const enemy = combat.enemies[e.idx];
    await new Promise(r => setTimeout(r, 600));

    // Fullasztás: skip turn
    if ((enemy.skipTurns || 0) > 0) {
      enemy.skipTurns--;
      updateEnemyStatusBadges(e.idx);
      addCombatLog(`${enemy.name} fuldokol — kihagyja a kört! (még ${enemy.skipTurns})`);
      continue;
    }

    const roll  = roll2d6();
    const power = roll + enemy.tamadasi_kepesseg;
    addCombatLog(`${enemy.name}: ${roll} + ${enemy.tamadasi_kepesseg} = ${power} vs ${player.vedettsegi_szint}`);

    if (power > player.vedettsegi_szint) {
      let dmg = calcDamage(enemy.damage);
      const hasAmulett = state.character.inventory.some(i => i.name === 'Amulett');
      if (hasAmulett && dmg > 0) {
        dmg = Math.max(0, dmg - 2);
        addCombatLog(`Amulett: 2 pont sebzés elnyelve.`);
      }
      player.eletero -= dmg;
      addCombatLog(`Találat! ${dmg} életerőt veszítesz. (marad: ${Math.max(0, player.eletero)})`);
      renderStats();
      updatePlayerHpBar();
      if (player.eletero <= 0) { combatDeath(); return; }
      // Empátia Pajzs: reflect half damage back to attacker
      if ((state.combat.empátiaPajzsRounds || 0) > 0) {
        const reflect = Math.floor(dmg / 2);
        enemy.currentHp -= reflect;
        state.combat.empátiaPajzsRounds--;
        addCombatLog(`🛡 Empátia Pajzs: ${reflect} pont visszaverve ${enemy.name}-re. (még ${state.combat.empátiaPajzsRounds} kör)`);
        updateEnemyHpBar(e.idx);
        if (enemy.currentHp <= 0) { addCombatLog(`${enemy.name} elesett!`); markEnemyDead(e.idx); }
      }
    } else {
      addCombatLog(`${enemy.name} elvétette a csapást.`);
    }

    // ── Tick timed debuffs after each enemy attack ──
    // Vakság: expires after 3 of the enemy's attacks
    if ((enemy.blindedRounds || 0) > 0) {
      enemy.blindedRounds--;
      if (enemy.blindedRounds === 0) {
        enemy.tamadasi_kepesseg += (enemy._blindAttackMalus || 5);
        enemy._blindAttackMalus = 0;
        addCombatLog(`${enemy.name} látása visszatér. Támadóereje visszaállt.`);
        updateEnemyStatLine(e.idx);
      }
      updateEnemyStatusBadges(e.idx);
    }
    // Ártó Szem: expires after 2 of the enemy's attacks
    if ((enemy.artóSzemRounds || 0) > 0) {
      enemy.artóSzemRounds--;
      if (enemy.artóSzemRounds === 0) {
        enemy.vedettsegi_szint += (enemy._artóSzemDefMalus || 5);
        enemy._artóSzemDefMalus = 0;
        addCombatLog(`${enemy.name} védelme visszaállt.`);
        updateEnemyStatLine(e.idx);
      }
      updateEnemyStatusBadges(e.idx);
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

const SECTIONS_URL = '/books/magusok-tornya/sections.json';
const RULES_URL    = '/books/magusok-tornya/rules.json';

// ── STATE ──────────────────────────────────────────────────────────────────

let rules    = null;
let sections = null;

let state = {
  currentSection: 1,
  selectedRace: 'felfodi_ember',
  character: {
    base: {}, current: {}, max: {},
    race: null,
    inventory: [],
  },
  history: [],
  combat: null,   // active combat state, null when not in combat
};

// ── BOOT ───────────────────────────────────────────────────────────────────

async function init() {
  showLoading(true);
  try {
    const [rulesResp, sectionsResp] = await Promise.all([
      fetch(RULES_URL),
      fetch(SECTIONS_URL),
    ]);
    rules    = await rulesResp.json();
    sections = await sectionsResp.json();
  } catch (e) {
    document.getElementById('loading').textContent =
      'Hiba: nem sikerült betölteni az adatokat. Indítsd el a szervert: python -m http.server 8000';
    showLoading(true);
    return;
  }
  showLoading(false);
  buildCharacterCreation();
  showScreen('create');
}

// ── DICE ───────────────────────────────────────────────────────────────────

function d6() { return Math.floor(Math.random() * 6) + 1; }
function d6x(n) { let t = 0; for (let i = 0; i < n; i++) t += d6(); return t; }
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

// Evaluate a damage formula string like "d6+2", "d6/2+1", "2d6+2"
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

// Given a damage range string like "3-8", find the matching formula from rules
function damageFormulaForRange(range) {
  if (!range || !rules) return null;
  const entry = rules.damage_table.find(r => r.range === range);
  return entry ? entry.formula : null;
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
  const races = rules.races;
  grid.innerHTML = '';
  for (const [key, race] of Object.entries(races)) {
    const modLines = Object.entries(race.modifiers)
      .map(([s, v]) => `${STAT_LABELS[s] || s} ${v > 0 ? '+' : ''}${v}`)
      .join(', ');
    const card = document.createElement('div');
    card.className = 'race-card' + (state.selectedRace === key ? ' selected' : '');
    card.dataset.race = key;
    card.innerHTML = `
      <div class="race-card-name">${race.label}</div>
      <div class="race-card-desc">${race.description}</div>
      <div class="race-card-mods">${modLines}</div>
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
  const out = {};
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
  document.getElementById('btn-reroll').addEventListener('click', () => {
    rollStats(); renderStatRolls();
  });
  document.getElementById('btn-start').addEventListener('click', startGame);
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

// ── GAME SCREEN ───────────────────────────────────────────────────────────────

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
    const el = document.getElementById(barId);
    if (el) el.style.width = pct + '%';
  };
  setBar('eletero',  'bar-eletero');
  setBar('varazserő','bar-varazserő');

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
  list.innerHTML = state.character.inventory.map(item => {
    const qtyStr = item.qty > 1
      ? `<span class="inventory-qty">×${item.qty}${item.unit ? ' ' + item.unit : ''}</span>`
      : '';
    return `<li><span>${item.name}</span>${qtyStr}</li>`;
  }).join('');
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

  numEl.textContent  = `${data.id}. szakasz`;
  textEl.textContent = data.text;
  choicesEl.innerHTML = '';

  if (data.is_ending) {
    renderEnding(choicesEl);
    wrap.classList.add('visible');
    return;
  }

  // ── Combat block ──
  if (data.enemies && data.enemies.length > 0) {
    renderCombatBlock(choicesEl, data);
    wrap.classList.add('visible');
    return;
  }

  // ── Luck test block ──
  if (data.has_luck_test && data.choices.length >= 2) {
    renderLuckTestBlock(choicesEl, data);
    wrap.classList.add('visible');
    return;
  }

  // ── Normal choices ──
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
  btn.addEventListener('click', () => showScreen('create'));
  container.appendChild(btn);
}

function showSectionError(id) {
  const wrap = document.getElementById('section-wrap');
  document.getElementById('section-number').textContent = `${id}. szakasz`;
  document.getElementById('section-text').textContent =
    `Ez a szakasz (${id}) hiányzik az adatokból.`;
  document.getElementById('choices').innerHTML = '';
  wrap.classList.add('visible');
}

// ── LUCK TEST SYSTEM ──────────────────────────────────────────────────────────
//
// How it works in the book:
//   "Tegyél Szerencsepróbát!"
//   "Ha sikerült a dobás, lapozz a X-re!"
//   "Ha nem, lapozz a Y-ra!"
//
// We show a "Roll Luck" button. Success = choices[0], Failure = choices[1].
// Luck decreases by 1 regardless of outcome.

function renderLuckTestBlock(container, data) {
  const block = document.createElement('div');
  block.className = 'system-block luck-block';
  block.innerHTML = `
    <div class="system-block-title">Szerencsepróba</div>
    <div class="system-block-desc">Dobj 2 kockával! Ha az eredmény kisebb vagy egyenlő a szerencse értékeddel, sikerült a próba. Akár sikerült, akár nem — szerencséd 1 ponttal csökken.</div>
    <div class="luck-current">Jelenlegi szerencse: <strong id="luck-display">${state.character.current.szerencse}</strong></div>
    <button class="btn-roll" id="btn-luck-roll">Dobás (2d6)</button>
    <div class="roll-result hidden" id="luck-result"></div>
  `;
  container.appendChild(block);

  document.getElementById('btn-luck-roll').addEventListener('click', () => {
    const roll   = roll2d6();
    const luck   = state.character.current.szerencse;
    const passed = roll <= luck;

    // Luck always decreases by 1
    state.character.current.szerencse = Math.max(0, luck - 1);
    renderStats();

    const resultEl = document.getElementById('luck-result');
    resultEl.classList.remove('hidden');
    resultEl.innerHTML = `
      <span class="roll-dice">${roll}</span>
      <span class="roll-vs">vs ${luck}</span>
      <span class="roll-outcome ${passed ? 'success' : 'failure'}">${passed ? 'Sikeres!' : 'Sikertelen'}</span>
    `;

    // Disable the roll button
    document.getElementById('btn-luck-roll').disabled = true;

    // Show the relevant choice
    setTimeout(() => {
      block.remove();
      const targetChoice = passed ? data.choices[0] : data.choices[1];
      if (targetChoice) {
        loadSection(targetChoice.target);
      } else {
        renderChoices(container, data.choices);
      }
    }, 1800);
  });
}

// ── COMBAT SYSTEM ─────────────────────────────────────────────────────────────
//
// Combat flow:
//   1. Show enemy stats
//   2. Roll initiative (player 1d6 vs enemy 1d6)
//   3. Winner attacks: roll 2d6 + attack vs defender's defense
//   4. If hit: roll damage, apply to defender's HP
//   5. Loser attacks (if alive)
//   6. Repeat until someone reaches 0 HP
//   7. Player wins → enable victory choice; Player dies → game over

function renderCombatBlock(container, data) {
  // Build combat state for all enemies
  state.combat = {
    enemies: data.enemies.map(e => ({ ...e, currentHp: e.eletero })),
    currentEnemyIndex: 0,
    log: [],
    sectionData: data,
  };

  const block = document.createElement('div');
  block.className = 'system-block combat-block';
  block.id = 'combat-block';
  container.appendChild(block);

  renderCombatUI(block);
}

function renderCombatUI(block) {
  const combat  = state.combat;
  const enemy   = combat.enemies[combat.currentEnemyIndex];
  const player  = state.character.current;

  block.innerHTML = `
    <div class="system-block-title">Harc</div>

    <div class="combat-entities">
      <div class="combatant player-side">
        <div class="combatant-name">Te</div>
        <div class="combatant-hp">
          <div class="combatant-hp-bar-wrap">
            <div class="combatant-hp-bar player-bar" id="player-hp-bar"
              style="width: ${Math.max(0,(player.eletero/state.character.max.eletero)*100)}%"></div>
          </div>
          <span id="player-hp-val">${player.eletero} ÉL</span>
        </div>
        <div class="combatant-stat">Támadás: ${player.tamadasi_kepesseg} &nbsp;|&nbsp; Védettség: ${player.vedettsegi_szint}</div>
      </div>

      <div class="combat-vs">VS</div>

      <div class="combatant enemy-side">
        <div class="combatant-name">${enemy.name}</div>
        <div class="combatant-hp">
          <div class="combatant-hp-bar-wrap">
            <div class="combatant-hp-bar enemy-bar" id="enemy-hp-bar"
              style="width: 100%"></div>
          </div>
          <span id="enemy-hp-val">${enemy.currentHp} ÉL</span>
        </div>
        <div class="combatant-stat">Támadás: ${enemy.tamadasi_kepesseg} &nbsp;|&nbsp; Védettség: ${enemy.vedettsegi_szint}</div>
      </div>
    </div>

    <div class="combat-log" id="combat-log"></div>

    <div class="combat-actions" id="combat-actions">
      <button class="btn-roll" id="btn-initiative">Kezdeményezés dobása</button>
    </div>
  `;

  document.getElementById('btn-initiative').addEventListener('click', rollInitiative);
}

function rollInitiative() {
  const playerRoll = d6();
  const enemyRoll  = d6();
  const combat = state.combat;
  const enemy  = combat.enemies[combat.currentEnemyIndex];

  addCombatLog(`Kezdeményezés: te ${playerRoll}, ${enemy.name} ${enemyRoll}`);

  if (playerRoll >= enemyRoll) {
    addCombatLog('Te támadsz először!');
    showAttackButton('player');
  } else {
    addCombatLog(`${enemy.name} támad először!`);
    resolveEnemyAttack();
  }
}

function showAttackButton(who) {
  const actions = document.getElementById('combat-actions');
  if (who === 'player') {
    actions.innerHTML = `<button class="btn-roll" id="btn-attack">Támadás (2d6)</button>`;
    document.getElementById('btn-attack').addEventListener('click', resolvePlayerAttack);
  } else {
    actions.innerHTML = `<button class="btn-roll" id="btn-enemy-attack">Ellenfél támad (2d6)</button>`;
    document.getElementById('btn-enemy-attack').addEventListener('click', resolveEnemyAttack);
  }
}

function resolvePlayerAttack() {
  const roll   = roll2d6();
  const combat = state.combat;
  const enemy  = combat.enemies[combat.currentEnemyIndex];
  const player = state.character.current;
  const power  = roll + player.tamadasi_kepesseg;

  addCombatLog(`Dobás: ${roll} + ${player.tamadasi_kepesseg} = ${power} vs ${enemy.vedettsegi_szint}`);

  if (power > enemy.vedettsegi_szint) {
    const dmg = calcDamage(enemy.damage);
    enemy.currentHp -= dmg;
    addCombatLog(`Találat! ${enemy.name} ${dmg} életerőt veszít. (marad: ${Math.max(0, enemy.currentHp)})`);
    updateEnemyHpBar();

    if (enemy.currentHp <= 0) {
      combat.currentEnemyIndex++;
      if (combat.currentEnemyIndex >= combat.enemies.length) {
        combatVictory();
      } else {
        const next = combat.enemies[combat.currentEnemyIndex];
        addCombatLog(`${enemy.name} elesett! Következő ellenfél: ${next.name}`);
        setTimeout(() => renderCombatUI(document.getElementById('combat-block')), 1200);
      }
      return;
    }
  } else {
    addCombatLog('Kihagytad a célpontot.');
  }

  setTimeout(() => showAttackButton('enemy'), 800);
}

function resolveEnemyAttack() {
  const roll   = roll2d6();
  const combat = state.combat;
  const enemy  = combat.enemies[combat.currentEnemyIndex];
  const player = state.character.current;
  const power  = roll + enemy.tamadasi_kepesseg;

  addCombatLog(`${enemy.name} dobása: ${roll} + ${enemy.tamadasi_kepesseg} = ${power} vs ${player.vedettsegi_szint}`);

  if (power > player.vedettsegi_szint) {
    const dmg = calcDamage(enemy.damage);
    player.eletero -= dmg;
    addCombatLog(`Találat! ${dmg} életerőt veszítesz. (marad: ${Math.max(0, player.eletero)})`);
    renderStats();
    updatePlayerHpBar();

    if (player.eletero <= 0) {
      combatDeath();
      return;
    }
  } else {
    addCombatLog('Elkerülted az ütést.');
  }

  setTimeout(() => showAttackButton('player'), 800);
}

function calcDamage(damageRange) {
  if (!damageRange) return 1;
  const formula = damageFormulaForRange(damageRange);
  return formula ? rollDamage(formula) : 1;
}

function updateEnemyHpBar() {
  const combat = state.combat;
  const enemy  = combat.enemies[combat.currentEnemyIndex];
  const pct    = Math.max(0, (enemy.currentHp / enemy.eletero) * 100);
  const bar    = document.getElementById('enemy-hp-bar');
  const val    = document.getElementById('enemy-hp-val');
  if (bar) bar.style.width = pct + '%';
  if (val) val.textContent = `${Math.max(0, enemy.currentHp)} ÉL`;
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

  // Show the "victory" choices (first choice = victory path in most sections)
  const data = state.combat.sectionData;
  const victoryChoices = data.choices.filter(c =>
    !c.text || c.text.toLowerCase().includes('győz') ||
    !c.text.toLowerCase().includes('veszít'));

  if (victoryChoices.length > 0) {
    renderChoices(actions, victoryChoices);
  } else {
    renderChoices(actions, data.choices);
  }
}

function combatDeath() {
  addCombatLog('Meghaltál. A kaland véget ért.');
  const actions = document.getElementById('combat-actions');
  actions.innerHTML = `
    <div class="choice-btn dead-end">Életerőd nullára csökkent. Kalandod véget ért.</div>
    <button class="btn-secondary" style="margin-top:1rem">Új kaland</button>
  `;
  actions.querySelector('.btn-secondary').addEventListener('click', () => showScreen('create'));
}

// ── MOBILE DRAWER ─────────────────────────────────────────────────────────────

function initDrawer() {
  const toggle  = document.getElementById('btn-stats-toggle');
  const overlay = document.getElementById('drawer-overlay');
  const drawer  = document.getElementById('mobile-drawer');

  const open  = () => { overlay.classList.add('visible'); drawer.classList.add('open'); };
  const close = () => { overlay.classList.remove('visible'); drawer.classList.remove('open'); };

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
  document.getElementById('btn-new-game')?.addEventListener('click', () => {
    rollStats();
    renderStatRolls();
    showScreen('create');
  });
  initDrawer();
  init();
});

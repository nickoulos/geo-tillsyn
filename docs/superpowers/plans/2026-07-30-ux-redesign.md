# Geo-Tillsyn v0.5 UX-redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the floating demo panel in the Origo plugin with a docked caseworker side panel (one click runs all three checks), a timeline pill map control, and an injected design-token stylesheet.

**Architecture:** The 800-line `src/geotillsyn.js` is split by responsibility: pure logic modules (`.mjs`, testable with `node --test`) for i18n, dossier rendering, rule-model evaluation and timeline math; DOM component modules (`.js`) for the panel and timeline pill; `geotillsyn.js` keeps only Origo wiring (projections, overlay layer, fetches, click handling). Styles are one CSS string injected as a `<style>` tag from the bundle — no webpack loaders needed.

**Tech Stack:** Vanilla JS, webpack 5 (`externals: ['Origo']`), `node --test` (Node ≥ 18.17), no new dependencies.

## Global Constraints

- **No backend changes.** Endpoints already exist: `/api/olovligt`, `/api/lovavvikelse`, `/api/lovavvikelse/geometri`, `/api/strandskydd` on `http://localhost:8464`.
- **Neutrality rule (legal):** the UI never generates a guilt-word or an all-clear the backend didn't send. Headlines are composed only from backend fields; when nothing composable exists, show "Se underlag" — never "Inget att anmärka".
- **Statutory terms stay Swedish verbatim** in both languages (SFS titles, "friggebod", lagrum). Only our own UI chrome is translated.
- **The decision is always the caseworker's:** footer text "Beslutet fattas alltid av handläggaren." is always visible.
- Keys in JS object literals must be ASCII (`ejFaststallt`, not `ejFastställt`); displayed strings are full Swedish.
- All commits in `geo-tillsyn` repo, message style `feat(origo): …` / `test(origo): …` / `docs(origo): …`, each ending with the Claude Co-Authored-By trailer.
- Working directory for all commands: `C:\Users\N.KOULOS\Documents\personal\4sight\Gov4tech\geo-tillsyn\origo-plugin` (repo root is one level up).

## File Structure

```
origo-plugin/
  src/
    geotillsyn.js      MODIFY  Origo wiring only: plugin component, projections,
                               overlay+legend, fetch orchestration, state
    i18n.mjs           CREATE  TEXTS (sv/en), FALT_LABEL, faltLabel, formatTal, teckenTal
    dossier.mjs        CREATE  escapeHtml, formatVarde, composeHeadline, renderCheckBody
    regelverk.mjs      CREATE  regelverkVid, renderKontextSammanfattning, renderKontextDetalj
    tidslinje-logik.mjs CREATE narmasteAr, stegAr, tickPosition
    styles.mjs         CREATE  cssText(), injectStyles() — design tokens + full stylesheet
    panel.js           CREATE  side-panel DOM component (states: empty/loading/result/info/error)
    timeline.js        CREATE  timeline-pill DOM component
  tests/
    i18n.test.mjs      CREATE
    dossier.test.mjs   CREATE
    regelverk.test.mjs CREATE
    tidslinje-logik.test.mjs CREATE
    styles.test.mjs    CREATE
  package.json         MODIFY  add "test": "node --test tests/"
  tasks/webpack.common.js MODIFY resolve.extensions += '.mjs'
```

---

### Task 1: Test infra + i18n module

**Files:**
- Create: `src/i18n.mjs`, `tests/i18n.test.mjs`
- Modify: `package.json` (test script), `tasks/webpack.common.js` (resolve `.mjs`)

**Interfaces:**
- Produces: `TEXTS` (object `{sv, en}` — every key listed below exists in both), `FALT_LABEL` (`{sv, en}`), `faltLabel(key, sprak) -> string`, `formatTal(n, sprak) -> string` (one decimal max, `,` for sv / `.` for en), `teckenTal(n, sprak) -> string` (`formatTal` plus leading `+` when n > 0).

- [ ] **Step 1: Write the failing test**

`tests/i18n.test.mjs`:

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import { TEXTS, FALT_LABEL, faltLabel, formatTal, teckenTal } from '../src/i18n.mjs';

test('sv och en har exakt samma nycklar', () => {
  assert.deepEqual(Object.keys(TEXTS.en).sort(), Object.keys(TEXTS.sv).sort());
  assert.deepEqual(Object.keys(FALT_LABEL.en).sort(), Object.keys(FALT_LABEL.sv).sort());
});

test('checkTitel finns för alla tre kontroller på båda språken', () => {
  for (const sprak of ['sv', 'en']) {
    for (const key of ['olovligt', 'lovavvikelse', 'strandskydd']) {
      assert.equal(typeof TEXTS[sprak].checkTitel[key], 'string');
      assert.equal(typeof TEXTS[sprak].checkUndertitel[key], 'string');
    }
  }
});

test('faltLabel: känd nyckel översätts, okänd faller tillbaka till nyckeln', () => {
  assert.equal(faltLabel('area_diff_m2', 'sv'), 'Areaavvikelse');
  assert.equal(faltLabel('area_diff_m2', 'en'), 'Area difference');
  assert.equal(faltLabel('helt_okand_nyckel', 'sv'), 'helt_okand_nyckel');
});

test('formatTal: svensk decimalkomma, engelsk punkt, max en decimal', () => {
  assert.equal(formatTal(90.3, 'sv'), '90,3');
  assert.equal(formatTal(90.3, 'en'), '90.3');
  assert.equal(formatTal(38.42, 'sv'), '38,4');
  assert.equal(formatTal(15, 'sv'), '15');
});

test('teckenTal: plus-prefix på positiva, minus följer med negativa', () => {
  assert.equal(teckenTal(90.3, 'sv'), '+90,3');
  assert.equal(teckenTal(-4.2, 'sv'), '-4,2');
  assert.equal(teckenTal(0, 'sv'), '0');
});

test('rubrik-funktionerna komponerar neutrala rubriker', () => {
  const t = TEXTS.sv;
  assert.equal(t.rubrikOlovligt(1998, 2001), 'Uppförd 1998–2001 enligt ortofoto');
  assert.equal(t.rubrikOlovligtRegister(1999), 'nybyggnadsår 1999 i registret');
  assert.equal(t.rubrikAvvikelse('+90,3', '+38,4'), '+90,3 m² (+38,4 %) mot godkänt lov');
  assert.equal(t.rubrikStrandskydd(2, 5), '2 av 5 byggnader berör strandskyddszon');
});
```

- [ ] **Step 2: Add test script + webpack `.mjs` resolution, run test to verify it fails**

In `package.json` scripts add `"test": "node --test tests/"`.
In `tasks/webpack.common.js` change `extensions: ['*', '.js']` to `extensions: ['*', '.js', '.mjs']`.

Run: `npm test`
Expected: FAIL — `Cannot find module '../src/i18n.mjs'`

- [ ] **Step 3: Write `src/i18n.mjs`**

Port `TEXTS` and `FALT_LABEL` from current `geotillsyn.js` (keep every existing `FALT_LABEL` entry verbatim, plus add `lov_hittat: 'Lov hittat i arkivet'` / `'Permit found in archive'`), replace the old panel-chrome keys with the new set. Full sv block (en mirrors it — translate chrome, keep statutory terms):

```js
export const TEXTS = {
  sv: {
    appNamn: 'Geo-Tillsyn',
    appKontext: 'Sundsvall · pilot',
    panelAria: 'Geo-Tillsyn analyspanel',
    sprakKnapp: 'EN',
    sprakKnappAria: 'Switch to English',
    kollapsAria: 'Fäll ihop panelen',
    oppnaAria: 'Öppna Geo-Tillsyn-panelen',
    knappTooltip: 'Geo-Tillsyn',
    tomRubrik: 'Granska en fastighet',
    tomText: 'Klicka på en fastighet i kartan så granskar Geo-Tillsyn den mot '
      + 'ortofotohistorik, bygglov och strandskydd.',
    fastighet: 'Fastighet',
    saknarBeteckning: 'beteckning saknas',
    ingenFastighet: 'Ingen fastighetsbeteckning på denna punkt',
    checkTitel: {
      olovligt: 'Byggnad utan lov',
      lovavvikelse: 'Avvikelse från bygglov',
      strandskydd: 'Strandskydd'
    },
    checkUndertitel: {
      olovligt: 'Ortofotohistorik mot byggnadsregistret',
      lovavvikelse: 'Verkligt läge mot godkänt lov',
      strandskydd: 'Byggnader mot skyddszoner'
    },
    analyserar: 'Analyserar…',
    seUnderlag: 'Se underlag',
    fakta: 'Fakta',
    bedomning: 'Bedömning',
    kallor: 'Källor',
    osakerheter: 'Osäkerheter',
    beslutText: 'Beslutet fattas alltid av handläggaren.',
    forsokIgen: 'Försök igen',
    felHamtning: 'Kunde inte hämta analysen',
    ejFaststallt: '»Ej fastställt«',
    inga: 'inga',
    ja: 'Ja',
    nej: 'Nej',
    godkantLage: 'Godkänt läge',
    verkligtLage: 'Verkligt läge',
    tidslinjeAria: 'Tidslinje',
    sliderAria: 'Välj årtal för ortofoto och regelverk',
    foregAr: 'Föregående årgång',
    nastaAr: 'Nästa årgång',
    regelverk: 'Regelverk',
    regelverkAria: 'Visa regelverket för valt år',
    lag: 'Lag',
    lovbefrielser: 'Lovbefrielser',
    ingaLovbefrielser: 'inga lovbefrielser',
    strandskydd: 'Strandskydd',
    ssKort: 'strandskydd gäller',
    ssKortInte: 'inget generellt strandskydd',
    ssGaller: '<b>gäller</b> inom zon (dispens krävs — lovbefrielse ger inte dispens)',
    ssFinnsInte: (d) => `<b>fanns inte än</b> (generellt strandskydd infördes ${d})`,
    preskription: 'Preskription',
    preskriptionText: (ar, slut, harLopt) =>
      `åtgärd från ${ar} — tioårsregeln löper ut <b>${slut}</b> `
      + `(${harLopt ? 'har löpt ut' : 'löper ännu'}; strandskydd preskriberas aldrig)`,
    regelmodellEjLaddad: 'regelmodell ej laddad',
    rubrikOlovligt: (sista, forsta) => `Uppförd ${sista}–${forsta} enligt ortofoto`,
    rubrikOlovligtRegister: (ar) => `nybyggnadsår ${ar} i registret`,
    rubrikAvvikelse: (diff, pct) => `${diff} m² (${pct} %) mot godkänt lov`,
    rubrikStrandskydd: (traffar, totalt) => `${traffar} av ${totalt} byggnader berör strandskyddszon`
  },
  en: { /* same keys; chrome translated, e.g.
    appKontext: 'Sundsvall · pilot', tomRubrik: 'Inspect a property',
    tomText: 'Click a property on the map and Geo-Tillsyn checks it against the '
      + 'orthophoto record, building permits and shoreline protection.',
    checkTitel: { olovligt: 'Building without permit',
      lovavvikelse: 'Deviation from permit', strandskydd: 'Shoreline protection' },
    checkUndertitel: { olovligt: 'Orthophoto record vs building register',
      lovavvikelse: 'Actual vs approved position', strandskydd: 'Buildings vs protected zones' },
    seUnderlag: 'See underlying data', beslutText: 'The decision is always the caseworker\'s.',
    forsokIgen: 'Try again', felHamtning: 'Could not fetch the analysis',
    ingaLovbefrielser: 'no permit exemptions', ssKort: 'shoreline protection applies',
    ssKortInte: 'no general shoreline protection',
    rubrikOlovligt: (sista, forsta) => `Erected ${sista}–${forsta} according to orthophotos`,
    rubrikOlovligtRegister: (ar) => `construction year ${ar} in the register`,
    rubrikAvvikelse: (diff, pct) => `${diff} m² (${pct} %) vs approved permit`,
    rubrikStrandskydd: (traffar, totalt) => `${traffar} of ${totalt} buildings touch a protection zone`,
    sprakKnapp: 'SV', sprakKnappAria: 'Byt till svenska',
    …and direct ports of the existing en entries (lag: 'Act', ssGaller, preskriptionText, …) */ }
};

export const FALT_LABEL = { sv: { /* existing sv map + lov_hittat */ },
                            en: { /* existing en map + lov_hittat */ } };

export function faltLabel(key, sprak) {
  const map = FALT_LABEL[sprak] || FALT_LABEL.sv;
  return map[key] || key;
}

export function formatTal(n, sprak) {
  const rundat = Math.round(n * 10) / 10;
  const s = String(rundat);
  return sprak === 'sv' ? s.replace('.', ',') : s;
}

export function teckenTal(n, sprak) {
  return (n > 0 ? '+' : '') + formatTal(n, sprak);
}
```

(The `en` block must be written out in full in the implementation — every sv key mirrored; the plan elides only for brevity here. The i18n key-parity test enforces completeness.)

- [ ] **Step 4: Run tests, verify pass** — `npm test` → all i18n tests PASS.

- [ ] **Step 5: Commit**

```bash
git add package.json tasks/webpack.common.js src/i18n.mjs tests/i18n.test.mjs
git commit -m "feat(origo): i18n-modul med node --test-infra (UX-redesign steg 1)"
```

---

### Task 2: Dossier module — headlines + check-card body

**Files:**
- Create: `src/dossier.mjs`, `tests/dossier.test.mjs`

**Interfaces:**
- Consumes: `faltLabel`, `teckenTal` from `./i18n.mjs`.
- Produces:
  - `escapeHtml(value) -> string`
  - `formatVarde(value, t) -> string` (HTML; booleans → `<span class="gt-badge">Ja/Nej</span>`, null/undefined → `t.ejFaststallt`, arrays/objects as before)
  - `composeHeadline(checkKey, data, t, sprak) -> string` (**plain text**, from backend fields only; fallback `t.seUnderlag`; `data.meddelande` wins if present; 'lovavvikelse' appends ` · ${dnr}` when present)
  - `renderCheckBody(data, t, sprak) -> string` (HTML: visible amber uncertainties, `<details class="gt-sektion">` **Fakta** (collapsed, sources inside), **Bedömning** (open); `data.meddelande` short-circuits to a single info row + uncertainties)

- [ ] **Step 1: Write the failing test** — `tests/dossier.test.mjs`:

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import { TEXTS } from '../src/i18n.mjs';
import { escapeHtml, formatVarde, composeHeadline, renderCheckBody } from '../src/dossier.mjs';

const t = TEXTS.sv;

const FALL3 = {
  byggnad_id: 'BAL-4711', lov_hittat: true, dnr: 'BYGG 2009-0417',
  beslutsdatum: '2009-06-12', pbl_vid_beslut: 'ÄPBL (1987:10)',
  godkand_area_m2: 235.1, verklig_area_m2: 325.4,
  area_diff_m2: 90.3, area_diff_procent: 38.4,
  rattelse_preskriberad: true, sanktionsavgift_mojlig: false,
  osakerheter: ['Lovarkivet är syntetiskt'],
  kallor: [{ beskrivning: 'Lovarkiv, ärende BYGG 2009-0417', url: 'https://example.se/lov' }],
  hamtad: '2026-07-30T10:00:00Z'
};

test('escapeHtml neutraliserar HTML', () => {
  assert.equal(escapeHtml('<b onclick="x">&'), '&lt;b onclick=&quot;x&quot;&gt;&amp;');
});

test('formatVarde: boolean blir badge, null blir Ej fastställt', () => {
  assert.equal(formatVarde(true, t), '<span class="gt-badge">Ja</span>');
  assert.equal(formatVarde(false, t), '<span class="gt-badge">Nej</span>');
  assert.equal(formatVarde(null, t), t.ejFaststallt);
});

test('composeHeadline lovavvikelse: fakta-rubrik med tecken och dnr', () => {
  assert.equal(composeHeadline('lovavvikelse', FALL3, t, 'sv'),
    '+90,3 m² (+38,4 %) mot godkänt lov · BYGG 2009-0417');
});

test('composeHeadline olovligt: intervall + register, aldrig skuld-ord', () => {
  const data = { sista_ar_utan: 1998, forsta_ar_med: 2001, bal_nybyggnadsar: 1999 };
  assert.equal(composeHeadline('olovligt', data, t, 'sv'),
    'Uppförd 1998–2001 enligt ortofoto · nybyggnadsår 1999 i registret');
});

test('composeHeadline strandskydd: träffar av totalt', () => {
  const data = { antal_traffar: 2, antal_byggnader: 5 };
  assert.equal(composeHeadline('strandskydd', data, t, 'sv'),
    '2 av 5 byggnader berör strandskyddszon');
});

test('composeHeadline: saknade fält ger Se underlag — aldrig ett friande påstående', () => {
  assert.equal(composeHeadline('olovligt', {}, t, 'sv'), t.seUnderlag);
  assert.equal(composeHeadline('lovavvikelse', { lov_hittat: true }, t, 'sv'), t.seUnderlag);
});

test('composeHeadline: backendens meddelande vinner', () => {
  assert.equal(composeHeadline('lovavvikelse',
    { lov_hittat: false, meddelande: 'Inget lov i arkivet' }, t, 'sv'), 'Inget lov i arkivet');
});

test('renderCheckBody: Fakta hopfälld, Bedömning öppen, källa klickbar, osäkerhet synlig', () => {
  const html = renderCheckBody(FALL3, t, 'sv');
  assert.match(html, /<details class="gt-sektion"><summary>Fakta<\/summary>/);
  assert.match(html, /<details class="gt-sektion" open><summary>Bedömning<\/summary>/);
  assert.match(html, /href="https:\/\/example\.se\/lov"/);
  assert.match(html, /gt-osakerhet/);
  assert.match(html, /Lovarkivet är syntetiskt/);
  assert.doesNotMatch(html, /hamtad|lov_hittat|punkt/); // skip-set respekteras
});

test('renderCheckBody: meddelande-svar renderas som info, inte som tom dossier', () => {
  const html = renderCheckBody({ meddelande: 'Inget lov i arkivet', osakerheter: ['x'] }, t, 'sv');
  assert.match(html, /Inget lov i arkivet/);
  assert.doesNotMatch(html, /<details/);
});
```

- [ ] **Step 2: Run to verify fail** — `npm test` → FAIL, module missing.

- [ ] **Step 3: Implement `src/dossier.mjs`**

Port `escapeHtml`, skip/assessment sets, `renderFaltRad`, `renderKallor`, `renderOsakerheter` from current `geotillsyn.js`, with these changes:

```js
import { faltLabel, teckenTal } from './i18n.mjs';

const HOPPA_OVER = new Set(['kallor', 'osakerheter', 'meddelande', 'fel', 'hamtad',
  'punkt', 'traffar', 'juridisk_not', 'korsjamforelse', 'lov_hittat']);

const BEDOMNING_FALT = new Set(['bal_forenligt', 'bygglov_kravdes', 'lovbefrielse',
  'rattelse_preskriberad', 'sanktionsavgift_mojlig', 'matningskritiskt',
  'matningskritiska', 'inom_strandskydd', 'pbl_vid_beslut', 'overgangsregel_tillampad',
  'dispens_kravs_idag', 'preskriberas', 'gallde_vid_uppforande']);

export function escapeHtml(value) { /* as today */ }

export function formatVarde(value, t) {
  if (value === null || value === undefined) return t.ejFaststallt;
  if (typeof value === 'boolean') return `<span class="gt-badge">${value ? t.ja : t.nej}</span>`;
  if (Array.isArray(value)) { /* as today, but t.inga for empty */ }
  if (typeof value === 'object') return escapeHtml(JSON.stringify(value));
  return escapeHtml(String(value));
}

function rad(key, value, t, sprak) {
  return `<div class="gt-rad"><span class="gt-rad__etikett">${escapeHtml(faltLabel(key, sprak))}</span>`
    + `<span class="gt-rad__varde">${formatVarde(value, t)}</span></div>`;
}

export function composeHeadline(checkKey, data, t, sprak) {
  if (data && typeof data.meddelande === 'string' && data.meddelande) return data.meddelande;
  if (!data) return t.seUnderlag;
  if (checkKey === 'olovligt'
      && data.sista_ar_utan != null && data.forsta_ar_med != null) {
    let s = t.rubrikOlovligt(data.sista_ar_utan, data.forsta_ar_med);
    if (data.bal_nybyggnadsar != null) s += ` · ${t.rubrikOlovligtRegister(data.bal_nybyggnadsar)}`;
    return s;
  }
  if (checkKey === 'lovavvikelse'
      && typeof data.area_diff_m2 === 'number' && typeof data.area_diff_procent === 'number') {
    let s = t.rubrikAvvikelse(teckenTal(data.area_diff_m2, sprak), teckenTal(data.area_diff_procent, sprak));
    if (data.dnr) s += ` · ${data.dnr}`;
    return s;
  }
  if (checkKey === 'strandskydd'
      && typeof data.antal_traffar === 'number' && typeof data.antal_byggnader === 'number') {
    return t.rubrikStrandskydd(data.antal_traffar, data.antal_byggnader);
  }
  return t.seUnderlag;
}

export function renderCheckBody(data, t, sprak) {
  if (data.meddelande) {
    return `<div class="gt-info">${escapeHtml(data.meddelande)}</div>${renderOsakerheter(data.osakerheter, t)}`;
  }
  const fakta = []; const bedomning = [];
  Object.keys(data).forEach((key) => {
    if (HOPPA_OVER.has(key)) return;
    (BEDOMNING_FALT.has(key) ? bedomning : fakta).push(rad(key, data[key], t, sprak));
  });
  if (Array.isArray(data.traffar)) { /* nested per-building rows into fakta, as today
    but using rad() and a `<div class="gt-traff">#N byggnad_id</div>` header */ }
  if (data.korsjamforelse) { /* keyed rows into bedomning, as today via rad-style markup */ }
  const sektion = (rubrik, inre, oppen) =>
    `<details class="gt-sektion"${oppen ? ' open' : ''}><summary>${escapeHtml(rubrik)}</summary>`
    + `<div class="gt-sektion__inner">${inre || '<div class="gt-info">—</div>'}</div></details>`;
  return renderOsakerheter(data.osakerheter, t)
    + sektion(t.fakta, fakta.join('') + renderKallor(data.kallor, t), false)
    + sektion(t.bedomning, bedomning.join(''), true);
}
```

`renderKallor` as today but class-based (no inline style): `<div class="gt-kallor"><span class="gt-kallor__rubrik">Källor</span><ul>…</ul></div>`. `renderOsakerheter` becomes `<div class="gt-osakerhet"><ul>…</ul></div>` (empty string when none).

- [ ] **Step 4: Run tests, verify pass** — `npm test`.
- [ ] **Step 5: Commit** — `git add src/dossier.mjs tests/dossier.test.mjs && git commit -m "feat(origo): dossier-modul - neutrala rubriker + kontrollkorts-innehall"`

---

### Task 3: Regelverk module

**Files:**
- Create: `src/regelverk.mjs`, `tests/regelverk.test.mjs`

**Interfaces:**
- Consumes: `escapeHtml` from `./dossier.mjs`.
- Produces: `regelverkVid(regler, isoDate) -> {pbl, befrielser, ssGaller, tioarSlut}` (port verbatim), `renderKontextSammanfattning(regler, isoDate, t) -> string` (one-line HTML: law name bold · exemption list or `t.ingaLovbefrielser` · `t.ssKort`/`t.ssKortInte`), `renderKontextDetalj(regler, isoDate, t) -> string` (the four detail rows as today minus the leading date row, `gt-rad`-style markup).

- [ ] **Step 1: Failing test** — `tests/regelverk.test.mjs` with an inline fixture:

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import { TEXTS } from '../src/i18n.mjs';
import { regelverkVid, renderKontextSammanfattning, renderKontextDetalj } from '../src/regelverk.mjs';

const t = TEXTS.sv;
const REGLER = {
  pbl_versioner: [
    { namn: 'ÄPBL', sfs: '1987:10', fran: '1987-07-01', till: '2011-05-01' },
    { namn: 'PBL', sfs: '2010:900', fran: '2011-05-02', till: null }
  ],
  lovbefrielser: [
    { namn: 'friggebod', max_kvm: 15, fran: '2008-01-01', till: null },
    { namn: 'attefallshus', max_kvm: 30, fran: '2014-07-02', till: null }
  ],
  strandskydd: { generellt_fran: '1975-07-01' },
  preskription: { pbl_tioarsregel: { ar: 10 } }
};

test('regelverkVid: rätt lag och befrielser vid datum', () => {
  const r = regelverkVid(REGLER, '2015-07-01');
  assert.equal(r.pbl.namn, 'PBL');
  assert.equal(r.befrielser.length, 2);
  assert.equal(r.ssGaller, true);
  assert.equal(r.tioarSlut, 2025);
});

test('sammanfattning: lag + befrielser + strandskydd på en rad', () => {
  const html = renderKontextSammanfattning(REGLER, '2015-07-01', t);
  assert.match(html, /<b>PBL<\/b>/);
  assert.match(html, /friggebod 15/);
  assert.match(html, /strandskydd gäller/);
});

test('sammanfattning före 1975: inget generellt strandskydd', () => {
  const html = renderKontextSammanfattning(REGLER, '1960-07-01', t);
  assert.match(html, /inget generellt strandskydd/);
});

test('detalj: fyra rader (lag, lovbefrielser, strandskydd, preskription)', () => {
  const html = renderKontextDetalj(REGLER, '2015-07-01', t);
  assert.equal((html.match(/gt-rad/g) || []).length >= 4, true);
  assert.match(html, /tioårsregeln/);
});
```

- [ ] **Step 2: Verify fail** — `npm test`.
- [ ] **Step 3: Implement** — port `within`/`regelverkVid`/`renderKontext` from `geotillsyn.js`; split rendering into the two functions; row markup `<div class="gt-rad"><span class="gt-rad__etikett">…</span><span class="gt-rad__varde">…</span></div>`; `new Date().getFullYear()` stays for preskription-idag.
- [ ] **Step 4: Verify pass** — `npm test`.
- [ ] **Step 5: Commit** — `feat(origo): regelverk-modul - sammanfattning + detalj for tidslinjepillen`

---

### Task 4: Timeline logic module

**Files:**
- Create: `src/tidslinje-logik.mjs`, `tests/tidslinje-logik.test.mjs`

**Interfaces:**
- Produces: `narmasteAr(years, varde) -> number` (nearest available year), `stegAr(years, aktuellt, riktning) -> number` (±1 step, clamped), `tickPosition(years, ar) -> number` (0–100 percent, proportional to year value).

- [ ] **Step 1: Failing test**

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import { narmasteAr, stegAr, tickPosition } from '../src/tidslinje-logik.mjs';

const YEARS = [1960, 1975, 1998, 1999, 2001, 2007, 2023];

test('narmasteAr snappar till närmaste tillgängliga årgång', () => {
  assert.equal(narmasteAr(YEARS, 1961), 1960);
  assert.equal(narmasteAr(YEARS, 1990), 1998);   // 15 från 1975, 8 från 1998
  assert.equal(narmasteAr(YEARS, 2023), 2023);
});

test('stegAr klampar i ändarna', () => {
  assert.equal(stegAr(YEARS, 1960, -1), 1960);
  assert.equal(stegAr(YEARS, 1998, 1), 1999);
  assert.equal(stegAr(YEARS, 2023, 1), 2023);
});

test('tickPosition är proportionell mot årtal (ärliga luckor)', () => {
  assert.equal(tickPosition(YEARS, 1960), 0);
  assert.equal(tickPosition(YEARS, 2023), 100);
  assert.ok(Math.abs(tickPosition(YEARS, 1998) - (38 / 63) * 100) < 0.01);
});
```

- [ ] **Step 2: Verify fail.** — `npm test`
- [ ] **Step 3: Implement** (exactly):

```js
export function narmasteAr(years, varde) {
  return years.reduce((best, y) => (Math.abs(y - varde) < Math.abs(best - varde) ? y : best), years[0]);
}
export function stegAr(years, aktuellt, riktning) {
  const i = years.indexOf(aktuellt);
  return years[Math.min(Math.max(i + riktning, 0), years.length - 1)];
}
export function tickPosition(years, ar) {
  const min = years[0]; const max = years[years.length - 1];
  return max === min ? 0 : ((ar - min) / (max - min)) * 100;
}
```

- [ ] **Step 4: Verify pass.** — `npm test`
- [ ] **Step 5: Commit** — `feat(origo): tidslinje-logik (snap, steg, proportionella ticks)`

---

### Task 5: Design-token stylesheet

**Files:**
- Create: `src/styles.mjs`, `tests/styles.test.mjs`

**Interfaces:**
- Produces: `STYLE_ID = 'gt-styles'`, `cssText() -> string`, `injectStyles(doc) -> void` (idempotent: no duplicate style tag).

- [ ] **Step 1: Failing test**

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import { cssText, STYLE_ID } from '../src/styles.mjs';

test('stylesheet innehåller tokens och alla huvudkomponenter', () => {
  const css = cssText();
  for (const sel of ['--gt-accent', '.gt-panel', '.gt-kort', '.gt-tidslinje',
    '.gt-tab', '.gt-legend', '.gt-skelett', '.gt-osakerhet', '.gt-badge',
    '.gt-sektion', '.gt-rad', '.gt-panel__fot']) {
    assert.ok(css.includes(sel), `saknar ${sel}`);
  }
});

test('STYLE_ID är stabilt (idempotent injektion bygger på det)', () => {
  assert.equal(STYLE_ID, 'gt-styles');
});
```

- [ ] **Step 2: Verify fail.** — `npm test`
- [ ] **Step 3: Implement `src/styles.mjs`** — full stylesheet:

```js
export const STYLE_ID = 'gt-styles';

export function cssText() {
  return `
.gt-panel, .gt-tidslinje, .gt-tab, .gt-legend {
  --gt-accent: #1e4ed8;
  --gt-accent-mork: #173db0;
  --gt-accent-ljus: #eaf0fe;
  --gt-ink: #16202e;
  --gt-ink-svag: #5a6a7e;
  --gt-yta: #ffffff;
  --gt-yta-svag: #f5f7fa;
  --gt-kant: #dde3ec;
  --gt-varning-bg: #fdf6e7;
  --gt-varning-kant: #ecd9a8;
  --gt-varning-ink: #7a5b16;
  --gt-fel-ink: #a03030;
  --gt-fel-bg: #fdf0f0;
  --gt-radie: 8px;
  --gt-skugga: 0 1px 2px rgba(22,32,46,.08), 0 4px 16px rgba(22,32,46,.10);
  font-family: -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  color: var(--gt-ink);
  font-size: 13px;
  line-height: 1.5;
  box-sizing: border-box;
}
.gt-panel *, .gt-tidslinje *, .gt-tab *, .gt-legend * { box-sizing: inherit; }

/* ---------- sidopanel ---------- */
.gt-panel {
  position: absolute; top: 0; right: 0; bottom: 0;
  width: 380px; max-width: 92vw;
  display: flex; flex-direction: column;
  background: var(--gt-yta);
  border-left: 1px solid var(--gt-kant);
  box-shadow: -8px 0 24px rgba(22,32,46,.10);
  z-index: 40;
  transition: transform .2s ease;
}
.gt-panel--kollapsad { transform: translateX(100%); box-shadow: none; }
.gt-panel__huvud {
  display: flex; align-items: center; justify-content: space-between;
  gap: .5rem; padding: .8rem 1rem;
  border-bottom: 1px solid var(--gt-kant); background: var(--gt-yta);
}
.gt-panel__titelgrupp { display: flex; align-items: center; gap: .6rem; min-width: 0; }
.gt-panel__logo {
  display: grid; place-items: center; width: 32px; height: 32px;
  border-radius: var(--gt-radie); background: var(--gt-accent); color: #fff; flex: none;
}
.gt-panel__logo svg { width: 18px; height: 18px; }
.gt-panel__titel { margin: 0; font-size: 15px; font-weight: 700; letter-spacing: -.01em; }
.gt-panel__kontext { display: block; font-size: 11px; color: var(--gt-ink-svag); }
.gt-panel__knappar { display: flex; gap: .35rem; }
.gt-panel__kropp { flex: 1; overflow-y: auto; padding: .9rem 1rem; scrollbar-width: thin; }
.gt-panel__fot {
  display: flex; align-items: center; gap: .55rem;
  padding: .7rem 1rem; font-size: 12px; font-weight: 600;
  border-top: 1px solid var(--gt-kant); background: var(--gt-yta-svag);
  color: var(--gt-ink);
}
.gt-panel__fot svg { width: 16px; height: 16px; flex: none; color: var(--gt-accent); }

/* ---------- knappar ---------- */
.gt-knapp {
  cursor: pointer; font: inherit; font-weight: 600;
  border: 1px solid var(--gt-kant); border-radius: 6px;
  background: var(--gt-yta); color: var(--gt-ink);
  padding: .25rem .55rem; transition: background .15s ease, border-color .15s ease;
}
.gt-knapp:hover { background: var(--gt-yta-svag); border-color: #c4cdda; }
.gt-knapp:focus-visible, .gt-tidslinje input:focus-visible {
  outline: 2px solid var(--gt-accent); outline-offset: 1px;
}
.gt-knapp--primar { background: var(--gt-accent); border-color: var(--gt-accent); color: #fff; }
.gt-knapp--primar:hover { background: var(--gt-accent-mork); border-color: var(--gt-accent-mork); }
.gt-knapp--ikon { padding: .25rem .45rem; line-height: 1; }

/* kollapsad flik */
.gt-tab {
  position: absolute; top: 50%; right: 0; transform: translateY(-50%);
  writing-mode: vertical-rl; padding: .8rem .4rem;
  background: var(--gt-accent); color: #fff; font-weight: 700; font-size: 12px;
  border: none; border-radius: var(--gt-radie) 0 0 var(--gt-radie);
  cursor: pointer; z-index: 41; box-shadow: var(--gt-skugga);
}

/* ---------- tomläge ---------- */
.gt-tom { text-align: center; padding: 2.2rem 1rem; color: var(--gt-ink-svag); }
.gt-tom svg { width: 44px; height: 44px; color: var(--gt-accent); opacity: .85; }
.gt-tom h3 { margin: .8rem 0 .3rem; font-size: 14px; color: var(--gt-ink); }
.gt-tom p { margin: 0 auto; max-width: 30ch; font-size: 12.5px; }

/* ---------- fastighetsrubrik ---------- */
.gt-fastighet { margin-bottom: .8rem; }
.gt-fastighet__etikett {
  font-size: 10.5px; font-weight: 700; letter-spacing: .08em;
  text-transform: uppercase; color: var(--gt-ink-svag);
}
.gt-fastighet__namn { font-size: 17px; font-weight: 700; letter-spacing: -.01em; }
.gt-fastighet__namn--saknas { font-weight: 400; color: var(--gt-ink-svag); font-style: italic; }

/* ---------- kontrollkort ---------- */
.gt-kort {
  border: 1px solid var(--gt-kant); border-radius: var(--gt-radie);
  background: var(--gt-yta); margin-bottom: .7rem; overflow: hidden;
}
.gt-kort__huvud {
  display: flex; align-items: center; gap: .6rem; padding: .6rem .75rem .1rem;
}
.gt-kort__ikon {
  display: grid; place-items: center; width: 28px; height: 28px; flex: none;
  border-radius: 6px; background: var(--gt-accent-ljus); color: var(--gt-accent);
}
.gt-kort__ikon svg { width: 16px; height: 16px; }
.gt-kort__huvud h3 { margin: 0; font-size: 13px; font-weight: 700; }
.gt-kort__under { display: block; font-size: 11px; color: var(--gt-ink-svag); }
.gt-kort__status { padding: .45rem .75rem .6rem; }
.gt-rubrikrad { font-size: 13px; font-weight: 600; }
.gt-kort__innehall { border-top: 1px solid var(--gt-kant); background: var(--gt-yta-svag); }
.gt-info { color: var(--gt-ink-svag); font-size: 12.5px; padding: .1rem 0; }

/* skelett-laddare */
.gt-skelett { display: block; height: 12px; border-radius: 4px;
  background: linear-gradient(90deg, #edf0f5 25%, #f7f9fc 45%, #edf0f5 65%);
  background-size: 200% 100%; animation: gt-skimmer 1.2s infinite linear; }
.gt-skelett + .gt-skelett { margin-top: .45rem; width: 70%; }
@keyframes gt-skimmer { to { background-position: -200% 0; } }

/* fel + info-lägen */
.gt-kort__fel { color: var(--gt-fel-ink); background: var(--gt-fel-bg);
  border-radius: 6px; padding: .5rem .6rem; font-size: 12.5px;
  display: flex; align-items: center; justify-content: space-between; gap: .6rem; }

/* ---------- dossier-innehåll ---------- */
.gt-sektion { border-top: 1px solid var(--gt-kant); }
.gt-sektion summary {
  cursor: pointer; list-style: none; display: flex; align-items: center; gap: .4rem;
  padding: .5rem .75rem; font-size: 11px; font-weight: 700;
  letter-spacing: .08em; text-transform: uppercase; color: var(--gt-ink-svag);
  user-select: none;
}
.gt-sektion summary::-webkit-details-marker { display: none; }
.gt-sektion summary::after { content: '▸'; margin-left: auto; font-size: 10px;
  transition: transform .15s ease; }
.gt-sektion[open] summary::after { transform: rotate(90deg); }
.gt-sektion__inner { padding: 0 .75rem .6rem; }
.gt-rad { display: flex; justify-content: space-between; gap: 1rem;
  padding: .22rem 0; border-bottom: 1px dashed var(--gt-kant); font-size: 12.5px; }
.gt-rad:last-child { border-bottom: none; }
.gt-rad__etikett { color: var(--gt-ink-svag); }
.gt-rad__varde { text-align: right; font-weight: 600; overflow-wrap: anywhere; }
.gt-traff { font-weight: 700; margin-top: .5rem; font-size: 12px; }
.gt-badge { display: inline-block; padding: .05rem .45rem; border-radius: 999px;
  background: var(--gt-accent-ljus); color: var(--gt-accent-mork);
  font-size: 11px; font-weight: 700; }
.gt-osakerhet { margin: .4rem 0; padding: .45rem .6rem .45rem .5rem;
  background: var(--gt-varning-bg); border: 1px solid var(--gt-varning-kant);
  border-left: 3px solid var(--gt-varning-ink);
  border-radius: 6px; color: var(--gt-varning-ink); font-size: 12px; }
.gt-osakerhet ul { margin: 0; padding-left: 1rem; }
.gt-kallor { margin-top: .4rem; font-size: 12px; }
.gt-kallor__rubrik { font-weight: 700; color: var(--gt-ink-svag); font-size: 11px;
  letter-spacing: .06em; text-transform: uppercase; }
.gt-kallor ul { margin: .15rem 0 0; padding-left: 1rem; }
.gt-kallor a { color: var(--gt-accent); text-decoration: none; }
.gt-kallor a:hover { text-decoration: underline; }

/* ---------- tidslinjepill ---------- */
.gt-tidslinje {
  position: absolute; bottom: 1.1rem; left: 50%; transform: translateX(-50%);
  width: min(560px, 60vw);
  background: var(--gt-yta); border: 1px solid var(--gt-kant);
  border-radius: 14px; box-shadow: var(--gt-skugga);
  padding: .55rem .8rem .5rem; z-index: 39;
  transition: left .2s ease;
}
.gt-oppen .gt-tidslinje { left: calc(50% - 190px); }
@media (max-width: 900px) { .gt-oppen .gt-tidslinje { display: none; } }
.gt-tidslinje__rad { display: flex; align-items: center; gap: .6rem; }
.gt-tidslinje__ar { font-size: 20px; font-weight: 800; letter-spacing: -.02em;
  min-width: 3.1rem; text-align: right; font-variant-numeric: tabular-nums; }
.gt-tidslinje__spar { position: relative; flex: 1; padding-bottom: 7px; }
.gt-tidslinje__slider { width: 100%; margin: 0; accent-color: var(--gt-accent); }
.gt-tidslinje__ticks { position: absolute; left: 8px; right: 8px; bottom: 0; height: 5px; }
.gt-tick { position: absolute; width: 2px; height: 5px; border-radius: 1px;
  background: #b9c3d2; transform: translateX(-50%); }
.gt-tick--aktiv { background: var(--gt-accent); }
.gt-tidslinje__regeltoggle {
  display: flex; align-items: center; gap: .45rem; width: 100%;
  margin-top: .45rem; padding: .3rem .45rem;
  border: none; border-top: 1px solid var(--gt-kant); background: none;
  font: inherit; font-size: 12px; color: var(--gt-ink-svag);
  cursor: pointer; text-align: left;
}
.gt-tidslinje__regeltoggle:hover { color: var(--gt-ink); }
.gt-tidslinje__regeltoggle .gt-chevron { margin-left: auto; transition: transform .15s ease; }
.gt-tidslinje__regeltoggle[aria-expanded="true"] .gt-chevron { transform: rotate(180deg); }
.gt-tidslinje__regeldetalj { padding: .2rem .45rem .35rem; font-size: 12.5px; }

/* ---------- kartlegend (Fall 3-overlay) ---------- */
.gt-legend { position: absolute; bottom: 1.1rem; left: 1.1rem; z-index: 39;
  display: flex; gap: .8rem; align-items: center;
  background: var(--gt-yta); border: 1px solid var(--gt-kant); border-radius: 8px;
  box-shadow: var(--gt-skugga); padding: .35rem .7rem; font-size: 12px; }
.gt-legend__prov { display: inline-block; width: 14px; height: 3px; border-radius: 2px;
  margin-right: .35rem; vertical-align: middle; }
`;
}

export function injectStyles(doc = document) {
  if (doc.getElementById(STYLE_ID)) return;
  const style = doc.createElement('style');
  style.id = STYLE_ID;
  style.textContent = cssText();
  doc.head.appendChild(style);
}
```

- [ ] **Step 4: Verify pass.** — `npm test`
- [ ] **Step 5: Commit** — `feat(origo): design-token-stylesheet (injicerad, inga inline-stilar)`

---

### Task 6: Panel DOM component

**Files:**
- Create: `src/panel.js`

**Interfaces:**
- Consumes: `escapeHtml` from `./dossier.mjs`.
- Produces: `skapaPanel(opts) -> panel` where `opts = { t, onSprak, onKollaps, onRetry(checkKey) }` and `panel` exposes:
  - `el` (aside), `tabEl` (collapsed-tab button)
  - `setCollapsed(kollapsad: boolean)`
  - `visaTomlage()`
  - `startaAnalys()` — renders property placeholder + three skeleton cards
  - `setFastighet(namn: string|null)` — null ⇒ italic `t.ingenFastighet`
  - `setCardLoading(key)`, `setCardResult(key, { headline, body })`, `setCardInfo(key, text)`, `setCardError(key, message)` — `key ∈ {'olovligt','lovavvikelse','strandskydd'}`
  - `uppdateraTexter(t)` — swaps chrome labels (title texts, footer, empty state, card titles) without touching card result content

No unit tests (DOM module — verified via `node --check`, bundle build and browser pass in Task 9).

- [ ] **Step 1: Implement `src/panel.js`**

```js
import { escapeHtml } from './dossier.mjs';

const CHECK_KEYS = ['olovligt', 'lovavvikelse', 'strandskydd'];

const IKONER = {
  logo: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 6v15l7-3 8 3 7-3V3l-7 3-8-3-7 3z"/><path d="M8 3v15M16 6v15"/></svg>',
  olovligt: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/></svg>',
  lovavvikelse: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M9 15l2 2 4-4"/></svg>',
  strandskydd: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12c2-2 4-2 6 0s4 2 6 0 4-2 6 0"/><path d="M2 18c2-2 4-2 6 0s4 2 6 0 4-2 6 0"/><path d="M2 6c2-2 4-2 6 0s4 2 6 0 4-2 6 0"/></svg>',
  vag: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v18"/><path d="M5 7l7-4 7 4"/><path d="M3 12h4l2 5 2-9 2 7 2-3h6"/></svg>',
  pin: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0z"/><circle cx="12" cy="10" r="3"/></svg>'
};

export function skapaPanel({ t, onSprak, onKollaps, onRetry }) {
  let texts = t;
  const el = document.createElement('aside');
  el.className = 'gt-panel';
  el.setAttribute('role', 'region');

  const tabEl = document.createElement('button');
  tabEl.className = 'gt-tab';
  tabEl.type = 'button';
  tabEl.hidden = true;

  function kortSkal(key) {
    return `<section class="gt-kort" data-check="${key}">
      <div class="gt-kort__huvud">
        <span class="gt-kort__ikon">${IKONER[key]}</span>
        <div><h3>${escapeHtml(texts.checkTitel[key])}</h3>
          <span class="gt-kort__under">${escapeHtml(texts.checkUndertitel[key])}</span></div>
      </div>
      <div class="gt-kort__status"></div>
      <div class="gt-kort__innehall" hidden></div>
    </section>`;
  }

  function render() {
    el.setAttribute('aria-label', texts.panelAria);
    tabEl.textContent = texts.appNamn;
    tabEl.setAttribute('aria-label', texts.oppnaAria);
    el.innerHTML = `
      <header class="gt-panel__huvud">
        <div class="gt-panel__titelgrupp">
          <span class="gt-panel__logo">${IKONER.logo}</span>
          <div><h2 class="gt-panel__titel">${escapeHtml(texts.appNamn)}</h2>
            <span class="gt-panel__kontext">${escapeHtml(texts.appKontext)}</span></div>
        </div>
        <div class="gt-panel__knappar">
          <button class="gt-knapp gt-sprak" type="button" aria-label="${escapeHtml(texts.sprakKnappAria)}">${escapeHtml(texts.sprakKnapp)}</button>
          <button class="gt-knapp gt-knapp--ikon gt-kollaps" type="button" aria-label="${escapeHtml(texts.kollapsAria)}">›</button>
        </div>
      </header>
      <div class="gt-panel__kropp"></div>
      <footer class="gt-panel__fot">${IKONER.vag}<span>${escapeHtml(texts.beslutText)}</span></footer>`;
    el.querySelector('.gt-sprak').addEventListener('click', onSprak);
    el.querySelector('.gt-kollaps').addEventListener('click', onKollaps);
  }

  function kropp() { return el.querySelector('.gt-panel__kropp'); }
  function kort(key) { return el.querySelector(`.gt-kort[data-check="${key}"]`); }

  function visaTomlage() {
    kropp().innerHTML = `<div class="gt-tom">${IKONER.pin}
      <h3>${escapeHtml(texts.tomRubrik)}</h3><p>${escapeHtml(texts.tomText)}</p></div>`;
  }

  function startaAnalys() {
    kropp().innerHTML = `
      <div class="gt-fastighet">
        <span class="gt-fastighet__etikett">${escapeHtml(texts.fastighet)}</span>
        <div class="gt-fastighet__namn"><span class="gt-skelett" style="width:9rem"></span></div>
      </div>
      ${CHECK_KEYS.map(kortSkal).join('')}`;
    CHECK_KEYS.forEach(setCardLoading);
  }

  function setFastighet(namn) {
    const elF = kropp().querySelector('.gt-fastighet__namn');
    if (!elF) return;
    if (namn) { elF.textContent = namn; elF.classList.remove('gt-fastighet__namn--saknas'); }
    else { elF.textContent = texts.ingenFastighet; elF.classList.add('gt-fastighet__namn--saknas'); }
  }

  function setCardLoading(key) {
    const k = kort(key); if (!k) return;
    k.querySelector('.gt-kort__status').innerHTML =
      '<span class="gt-skelett"></span><span class="gt-skelett"></span>';
    const inneh = k.querySelector('.gt-kort__innehall');
    inneh.hidden = true; inneh.innerHTML = '';
  }

  function setCardResult(key, { headline, body }) {
    const k = kort(key); if (!k) return;
    k.querySelector('.gt-kort__status').innerHTML =
      `<div class="gt-rubrikrad">${escapeHtml(headline)}</div>`;
    const inneh = k.querySelector('.gt-kort__innehall');
    inneh.innerHTML = body; inneh.hidden = false;
  }

  function setCardInfo(key, text) {
    const k = kort(key); if (!k) return;
    k.querySelector('.gt-kort__status').innerHTML =
      `<div class="gt-info">${escapeHtml(text)}</div>`;
    const inneh = k.querySelector('.gt-kort__innehall');
    inneh.hidden = true; inneh.innerHTML = '';
  }

  function setCardError(key, message) {
    const k = kort(key); if (!k) return;
    k.querySelector('.gt-kort__status').innerHTML =
      `<div class="gt-kort__fel"><span>${escapeHtml(message)}</span>
        <button class="gt-knapp gt-knapp--primar" type="button">${escapeHtml(texts.forsokIgen)}</button></div>`;
    k.querySelector('.gt-kort__fel .gt-knapp').addEventListener('click', () => onRetry(key));
    const inneh = k.querySelector('.gt-kort__innehall');
    inneh.hidden = true; inneh.innerHTML = '';
  }

  function setCollapsed(kollapsad) {
    el.classList.toggle('gt-panel--kollapsad', kollapsad);
    tabEl.hidden = !kollapsad;
  }

  function uppdateraTexter(nyaT) {
    texts = nyaT;
    // Chrome only: header/footer labels + card titles. Card status/innehåll
    // is owned by the wiring layer, which re-renders results after language switch.
    el.querySelector('.gt-panel__titel').textContent = texts.appNamn;
    el.querySelector('.gt-panel__kontext').textContent = texts.appKontext;
    const sprakKnapp = el.querySelector('.gt-sprak');
    sprakKnapp.textContent = texts.sprakKnapp;
    sprakKnapp.setAttribute('aria-label', texts.sprakKnappAria);
    el.querySelector('.gt-kollaps').setAttribute('aria-label', texts.kollapsAria);
    el.querySelector('.gt-panel__fot span').textContent = texts.beslutText;
    el.setAttribute('aria-label', texts.panelAria);
    tabEl.textContent = texts.appNamn;
    tabEl.setAttribute('aria-label', texts.oppnaAria);
    CHECK_KEYS.forEach((key) => {
      const k = kort(key); if (!k) return;
      k.querySelector('h3').textContent = texts.checkTitel[key];
      k.querySelector('.gt-kort__under').textContent = texts.checkUndertitel[key];
    });
    const tom = kropp().querySelector('.gt-tom');
    if (tom) visaTomlage();
    const fastEtikett = kropp().querySelector('.gt-fastighet__etikett');
    if (fastEtikett) fastEtikett.textContent = texts.fastighet;
  }

  render();
  visaTomlage();
  return { el, tabEl, setCollapsed, visaTomlage, startaAnalys, setFastighet,
    setCardLoading, setCardResult, setCardInfo, setCardError, uppdateraTexter };
}
```

- [ ] **Step 2: Syntax check** — `node --check src/panel.js` → OK.
- [ ] **Step 3: Commit** — `feat(origo): sidopanel-komponent (tomlage, skelett, kort-tillstand, kollaps)`

---

### Task 7: Timeline pill DOM component

**Files:**
- Create: `src/timeline.js`

**Interfaces:**
- Consumes: `narmasteAr`, `stegAr`, `tickPosition` from `./tidslinje-logik.mjs`; `escapeHtml` from `./dossier.mjs`.
- Produces: `skapaTidslinje(opts) -> tidslinje` where `opts = { years, startAr, t, onArByte(ar) }` and `tidslinje` exposes: `el`, `setAr(ar)` (updates slider/year/active tick, does **not** re-fire `onArByte`), `setKontext(sammanfattningHtml, detaljHtml)`, `uppdateraTexter(t)`.

- [ ] **Step 1: Implement `src/timeline.js`**

```js
import { narmasteAr, stegAr, tickPosition } from './tidslinje-logik.mjs';
import { escapeHtml } from './dossier.mjs';

const CHEVRON = '<svg class="gt-chevron" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M6 9l6 6 6-6"/></svg>';

export function skapaTidslinje({ years, startAr, t, onArByte }) {
  let texts = t;
  let aktuelltAr = years.includes(startAr) ? startAr : years[years.length - 1];
  const min = years[0];
  const max = years[years.length - 1];

  const el = document.createElement('div');
  el.className = 'gt-tidslinje';
  el.setAttribute('role', 'group');
  el.innerHTML = `
    <div class="gt-tidslinje__rad">
      <button class="gt-knapp gt-knapp--ikon" type="button" data-riktning="-1">‹</button>
      <div class="gt-tidslinje__spar">
        <input class="gt-tidslinje__slider" type="range" min="${min}" max="${max}"
               step="1" value="${aktuelltAr}">
        <div class="gt-tidslinje__ticks">${years.map((y) =>
          `<span class="gt-tick" data-ar="${y}" style="left:${tickPosition(years, y)}%" title="${y}"></span>`).join('')}</div>
      </div>
      <button class="gt-knapp gt-knapp--ikon" type="button" data-riktning="1">›</button>
      <span class="gt-tidslinje__ar">${aktuelltAr}</span>
    </div>
    <button class="gt-tidslinje__regeltoggle" type="button" aria-expanded="false">
      <span class="gt-regel-sammanfattning"></span>${CHEVRON}
    </button>
    <div class="gt-tidslinje__regeldetalj" hidden></div>`;

  const slider = el.querySelector('.gt-tidslinje__slider');
  const arEl = el.querySelector('.gt-tidslinje__ar');
  const toggle = el.querySelector('.gt-tidslinje__regeltoggle');
  const detalj = el.querySelector('.gt-tidslinje__regeldetalj');

  function setAr(ar) {
    aktuelltAr = ar;
    slider.value = String(ar);
    arEl.textContent = String(ar);
    el.querySelectorAll('.gt-tick').forEach((tick) => {
      tick.classList.toggle('gt-tick--aktiv', Number(tick.dataset.ar) === ar);
    });
  }

  slider.addEventListener('input', () => {
    const ar = narmasteAr(years, Number(slider.value));
    if (ar !== aktuelltAr) { setAr(ar); onArByte(ar); }
    else slider.value = String(ar); // snappa tillbaka mellan årgångar
  });
  el.querySelectorAll('[data-riktning]').forEach((knapp) => {
    knapp.addEventListener('click', () => {
      const ar = stegAr(years, aktuelltAr, Number(knapp.dataset.riktning));
      if (ar !== aktuelltAr) { setAr(ar); onArByte(ar); }
    });
  });
  toggle.addEventListener('click', () => {
    const oppen = toggle.getAttribute('aria-expanded') === 'true';
    toggle.setAttribute('aria-expanded', String(!oppen));
    detalj.hidden = oppen;
  });

  function setKontext(sammanfattningHtml, detaljHtml) {
    el.querySelector('.gt-regel-sammanfattning').innerHTML = sammanfattningHtml;
    detalj.innerHTML = detaljHtml;
  }

  function uppdateraTexter(nyaT) {
    texts = nyaT;
    el.setAttribute('aria-label', texts.tidslinjeAria);
    slider.setAttribute('aria-label', texts.sliderAria);
    el.querySelector('[data-riktning="-1"]').setAttribute('aria-label', texts.foregAr);
    el.querySelector('[data-riktning="1"]').setAttribute('aria-label', texts.nastaAr);
    toggle.setAttribute('aria-label', texts.regelverkAria);
  }

  uppdateraTexter(t);
  setAr(aktuelltAr);
  return { el, setAr, setKontext, uppdateraTexter };
}
```

- [ ] **Step 2: Syntax check** — `node --check src/timeline.js` → OK.
- [ ] **Step 3: Commit** — `feat(origo): tidslinjepill (snap-slider, arliga ticks, regelverks-expander)`

---

### Task 8: Rewire `geotillsyn.js` — one click runs all checks

**Files:**
- Modify: `src/geotillsyn.js` (full rewrite of panel/timeline/fall sections; keep EPSG-3014 block, GetFeatureInfo, overlay drawing verbatim where noted)

**Interfaces:**
- Consumes everything produced in Tasks 1–7.
- Produces: same external contract as today — `GeoTillsyn(options)` Origo component; options unchanged (`owsUrl`, `fastighetLayer`, `fbetProperty`, `arslager`, `reglerUrl`, `startAr`, `sprak`, `apiUrl`).

Key changes (keep the file's existing header comment, append a v0.5 paragraph):

1. **Imports:** `TEXTS` from `./i18n.mjs`; `composeHeadline`, `renderCheckBody`, `escapeHtml` from `./dossier.mjs`; `renderKontextSammanfattning`, `renderKontextDetalj` from `./regelverk.mjs`; `injectStyles` from `./styles.mjs`; `skapaPanel` from `./panel.js`; `skapaTidslinje` from `./timeline.js`. Delete the in-file copies of everything now in modules (TEXTS, FALT_LABEL, escapeHtml, formatVarde, render*, regelverkVid, renderKontext, fallKnappStil, byggPanelInnehall, kopplaPanelHandlers, buildPanel).
2. **Checks constant** (replaces `FALL_ENDPOINTS`):

```js
const CHECKS = [
  { key: 'olovligt', path: '/api/olovligt', radie: 100 },
  { key: 'lovavvikelse', path: '/api/lovavvikelse', radie: 100 },
  { key: 'strandskydd', path: '/api/strandskydd', radie: 150 }
];
```

3. **State:** `let kollapsad = false; let senastePunkt3014 = null; const senasteData = {};` (per check key). Delete `valtFall`.
4. **onAdd:** `injectStyles(); panel = skapaPanel({...}); tidslinje = skapaTidslinje({...});` append `panel.el`, `panel.tabEl`, `tidslinje.el`, and a legend div (`class="gt-legend"`, hidden) to `document.getElementById(viewer.getId())`; add class `gt-oppen` to that container when panel open (toggle in `setKollapsad`). Attach `map.on('singleclick', pahandlaKlick)` **once** — the handler returns early when `kollapsad` is true. The Origo nav button's click toggles collapse (replaces old `toggleActive`).
5. **Click flow:**

```js
async function pahandlaKlick(evt) {
  if (kollapsad) return;
  panel.startaAnalys();
  identify(evt); // async; skriver via panel.setFastighet — behåll buildGetFeatureInfoUrl
  const punkt = transformTill3014(evt.coordinate);
  if (!punkt) {
    CHECKS.forEach((c) => panel.setCardError(c.key, `${t().felHamtning} (EPSG:3014)`));
    return;
  }
  senastePunkt3014 = punkt;
  CHECKS.forEach((c) => korOchRendera(c, punkt));
}

async function korOchRendera(check, [e3014, n3014]) {
  panel.setCardLoading(check.key);
  let data; let status = 0;
  try {
    const url = `${apiUrl}${check.path}?easting=${encodeURIComponent(e3014)}`
      + `&northing=${encodeURIComponent(n3014)}&radie_m=${encodeURIComponent(check.radie)}`;
    const resp = await fetch(url);
    status = resp.status;
    data = await resp.json();
  } catch (err) {
    console.error(`geotillsyn: ${check.path} misslyckades`, err);
    panel.setCardError(check.key, t().felHamtning);
    return;
  }
  if (status === 404 && data && data.fel) {              // ärligt "hittades inte"
    delete senasteData[check.key];
    panel.setCardInfo(check.key, data.fel);
    if (check.key === 'lovavvikelse') { clearOverlay(); visaLegend(false); }
    return;
  }
  if (status >= 400) {
    panel.setCardError(check.key, (data && data.fel) || `HTTP ${status}`);
    return;
  }
  senasteData[check.key] = data;
  renderaKort(check.key);
  if (check.key === 'lovavvikelse') {
    if (data.lov_hittat) hamtaFall3Geometri(e3014, n3014, check.radie);
    else { clearOverlay(); visaLegend(false); }
  }
}

function renderaKort(key) {
  const data = senasteData[key];
  if (!data) return;
  panel.setCardResult(key, {
    headline: composeHeadline(key, data, t(), aktivtSprak),
    body: renderCheckBody(data, t(), aktivtSprak)
  });
}
```

`identify()` keeps its fetch logic but ends with `panel.setFastighet(feat ? (feat.properties[fbetProperty] || null) : null)` (no HTML string building). Retry callback: `onRetry: (key) => { const check = CHECKS.find((c) => c.key === key); if (check && senastePunkt3014) korOchRendera(check, senastePunkt3014); }`.

6. **Overlay + legend:** keep `initOverlayLayer`, `ritaFall3Overlay`, `hamtaFall3Geometri`, `clearOverlay` verbatim, except: after successful `ritaFall3Overlay` with features call `visaLegend(true)`; add

```js
function visaLegend(visa) {
  legendEl.hidden = !visa;
  if (visa) legendEl.innerHTML =
    `<span><span class="gt-legend__prov" style="background:rgba(40,80,255,1)"></span>${escapeHtml(t().godkantLage)}</span>`
    + `<span><span class="gt-legend__prov" style="background:rgba(230,40,40,1)"></span>${escapeHtml(t().verkligtLage)}</span>`;
}
```

(The two rgba literals are the overlay stroke colors already used — keep them in sync.)

7. **Timeline wiring:** `visaAr(year)` keeps the layer-switch loop and warning verbatim; the context part becomes:

```js
const isoDate = `${year}-07-01`;
tidslinje.setAr(year);
tidslinje.setKontext(
  regler ? renderKontextSammanfattning(regler, isoDate, t())
         : `<b>${year}</b> (${escapeHtml(t().regelmodellEjLaddad)})`,
  regler ? renderKontextDetalj(regler, isoDate, t()) : ''
);
```

`skapaTidslinje({ years, startAr: aktuelltAr, t: t(), onArByte: visaAr })`.

8. **Collapse + language:**

```js
function setKollapsad(ny) {
  kollapsad = ny;
  panel.setCollapsed(ny);
  document.getElementById(viewer.getId()).classList.toggle('gt-oppen', !ny);
}
// onKollaps: () => setKollapsad(true); tabEl click + nav-knappen: () => setKollapsad(!kollapsad)
function bytSprak() {
  aktivtSprak = aktivtSprak === 'sv' ? 'en' : 'sv';
  panel.uppdateraTexter(t());
  tidslinje.uppdateraTexter(t());
  Object.keys(senasteData).forEach(renderaKort);
  visaAr(aktuelltAr);          // regelkontext + legend på nytt språk
  if (!legendEl.hidden) visaLegend(true);
}
```

`panel.tabEl.addEventListener('click', () => setKollapsad(false));` in onAdd. Initial state: `setKollapsad(false)` (panel open on load — the empty state IS the onboarding).

- [ ] **Step 1: Rewrite the file** per above. Keep EPSG-3014 registration block, `projicera`, `transformTill3014`, `buildGetFeatureInfoUrl`, `getOl` unchanged.
- [ ] **Step 2: Syntax + tests** — `node --check src/geotillsyn.js && npm test` → OK, all pass.
- [ ] **Step 3: Build** — `npm run build` → webpack OK; `node --check build/js/geotillsyn.min.js` → OK.
- [ ] **Step 4: Grep the bundle sanity-checks**

```bash
grep -c "api/lovavvikelse/geometri\|gt-panel\|gt-tidslinje\|EPSG:3014" build/js/geotillsyn.min.js
```

Expected: all present (non-zero).

- [ ] **Step 5: Commit** — `feat(origo): v0.5 UX - dockad panel, ett-klicks granskning, tidslinjepill, legend`

---

### Task 9: Deploy bundle to demo, docs, manual verification

**Files:**
- Modify: `origo-plugin/build/plugins/geotillsyn.min.js` (copy of the built bundle — this path is what `index.html` loads; note `build/` is git-ignored, so this is a local file operation, not a commit)
- Modify: `B-LIVE-STATUS.md` (append v0.5 section), `README.md` (Nuläge paragraph)

- [ ] **Step 1: Copy bundle** — `Copy-Item build/js/geotillsyn.min.js build/plugins/geotillsyn.min.js -Force`
- [ ] **Step 2: Update docs** — B-LIVE-STATUS.md gets a "## v0.5 UX-redesign (2026-07-30)" section describing panel/one-click/timeline/legend and the unchanged run instructions; README "Nuläge" updated from hello-world text to the v0.5 description.
- [ ] **Step 3: Manual browser pass (human or screenshot-capable runner), checklist:**
  1. Start backend `geo-tillsyn-mcp --host 0.0.0.0 --port 8464` and `npx http-server build -p 9967 -c-1 --cors`; open `http://localhost:9967/index.html`.
  2. Panel open on load with empty state; footer visible; SV default.
  3. Click ALNÖ-USLAND 1:45 → FBET appears, three cards skeleton → results; Avvikelse headline reads `+90,3 m² (+38,4 %) mot godkänt lov · <dnr>`; blue/red overlay + legend chip.
  4. Click empty water → cards show honest 404-info states, no red error styling.
  5. Stop backend, click again → error cards with "Försök igen"; restart backend, retry works per card.
  6. Timeline: drag → snaps to real years, orthophoto switches, "Regelverk"-summary updates; expander shows detail rows; ‹ › step.
  7. EN toggle: chrome + cards + regelverk + legend switch; statutory terms stay Swedish.
  8. Collapse → tab at right edge; map full-width; clicks do nothing while collapsed; reopen restores previous results.
- [ ] **Step 4: Commit docs** — `docs(origo): v0.5 UX-redesign - status + README`

---

## Self-review notes

- **Spec coverage:** §1 panel/collapse/click-always-on → Tasks 6+8; §2 empty state/parallel checks/cards/neutrality/footer/errors → Tasks 1-2, 6, 8; §3 timeline pill/ticks/regelverk expander → Tasks 3, 4, 7, 8; §4 tokens/stylesheet/legend → Tasks 5, 8; §5 testing → per-task `npm test` + Task 9 checklist.
- **Type consistency check:** `skapaPanel` API names used in Task 8 match Task 6 (`startaAnalys`, `setCardLoading`, `setCardResult`, `setCardInfo`, `setCardError`, `setFastighet`, `setCollapsed`, `uppdateraTexter`, `tabEl`); `skapaTidslinje` API matches Task 7 (`setAr`, `setKontext`, `uppdateraTexter`); i18n keys referenced in dossier/panel/timeline all exist in the Task 1 key list.
- The `en` TEXTS block is elided in Task 1's listing for space but is **required in full**; the key-parity test makes omission a test failure, not a silent gap.

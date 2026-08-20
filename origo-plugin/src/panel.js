/**
 * Sidopanel-komponenten: dockad fullhöjdspanel med produktidentitet,
 * tomläge, fastighetsrubrik, tre kontrollkort (skelett/resultat/info/fel)
 * och den alltid synliga beslutsfoten. Ingen affärslogik — bara DOM och
 * tillstånd; innehållet (rubriker, dossier-HTML) ägs av wiring-lagret.
 */

import { escapeHtml } from './dossier.mjs';

const CHECK_KEYS = ['olovligt', 'lovavvikelse', 'strandskydd'];

const IKONER = {
  logo: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 6v15l7-3 8 3 7-3V3l-7 3-8-3-7 3z"/><path d="M8 3v15M16 6v15"/></svg>',
  olovligt: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/></svg>',
  lovavvikelse: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M9 15l2 2 4-4"/></svg>',
  strandskydd: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12c2-2 4-2 6 0s4 2 6 0 4-2 6 0"/><path d="M2 18c2-2 4-2 6 0s4 2 6 0 4-2 6 0"/><path d="M2 6c2-2 4-2 6 0s4 2 6 0 4-2 6 0"/></svg>',
  vag: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v18"/><path d="M5 7l7-4 7 4"/><path d="M3 12h4l2 5 2-9 2 7 2-3h6"/></svg>',
  pin: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0z"/><circle cx="12" cy="10" r="3"/></svg>',
  snedbild: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7l4-4h10l4 4v13H3z"/><path d="M3 7h18"/><circle cx="12" cy="14" r="3.5"/></svg>',
  radar: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4.5"/><path d="M12 12l6.5-6.5"/><circle cx="12" cy="12" r="1"/></svg>',
  lock: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="10.5" width="16" height="10" rx="2"/><path d="M7.5 10.5V7a4.5 4.5 0 0 1 9 0v3.5"/><circle cx="12" cy="15" r="1.4" fill="currentColor" stroke="none"/></svg>'
};

// Underlagsläget styr chippens ton — aldrig ett utfall, bara hur säkert
// underlaget är. Samma fem lägen som dossier.mjs underlagsLage().
const UNDERLAG_TEXTNYCKEL = {
  finns: 'underlagFinns', osakert: 'underlagOsakert', inget: 'underlagInget',
  hamtar: 'underlagHamtar', fel: 'underlagFel'
};

export function skapaPanel({ t, onSprak, onKollaps, onRetry, onRadar, onRadarVal, onRadarTillbaka }) {
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
          <button class="gt-knapp gt-radarknapp" type="button" aria-label="${escapeHtml(texts.radarKnappAria)}" title="${escapeHtml(texts.radarKnappAria)}">${IKONER.radar}<span>${escapeHtml(texts.radarKnapp)}</span></button>
          <button class="gt-knapp gt-sprak" type="button" aria-label="${escapeHtml(texts.sprakKnappAria)}">${escapeHtml(texts.sprakKnapp)}</button>
          <button class="gt-knapp gt-knapp--ikon gt-kollaps" type="button" aria-label="${escapeHtml(texts.kollapsAria)}">›</button>
        </div>
      </header>
      <div class="gt-panel__kropp"></div>
      <footer class="gt-panel__fot">${IKONER.vag}<span>${escapeHtml(texts.beslutText)}</span></footer>`;
    el.querySelector('.gt-sprak').addEventListener('click', onSprak);
    el.querySelector('.gt-kollaps').addEventListener('click', onKollaps);
    el.querySelector('.gt-radarknapp').addEventListener('click', () => onRadar && onRadar());
  }

  // Radarn är aktiv när en skanning finns att gå tillbaka till: analysvyn får
  // då en "Till radarlistan"-rad överst.
  let radarAktiv = false;

  function kropp() { return el.querySelector('.gt-panel__kropp'); }
  function kort(key) { return el.querySelector(`.gt-kort[data-check="${key}"]`); }

  function visaTomlage() {
    kropp().innerHTML = `<div class="gt-tom">${IKONER.pin}
      <h3>${escapeHtml(texts.tomRubrik)}</h3><p>${escapeHtml(texts.tomText)}</p></div>`;
  }

  function setCardLoading(key) {
    const k = kort(key);
    if (!k) return;
    k.querySelector('.gt-kort__status').innerHTML =
      '<span class="gt-skelett"></span><span class="gt-skelett"></span>';
    const inneh = k.querySelector('.gt-kort__innehall');
    inneh.hidden = true;
    inneh.innerHTML = '';
  }

  function radarTillbakaRad() {
    if (!radarAktiv) return '';
    return `<button type="button" class="gt-knapp gt-radar__tillbaka">‹ ${escapeHtml(texts.radarTillbaka)}</button>`;
  }

  function kopplaRadarTillbaka() {
    const knapp = kropp().querySelector('.gt-radar__tillbaka');
    if (knapp) knapp.addEventListener('click', () => onRadarTillbaka && onRadarTillbaka());
  }

  // `coords` = [E, N] i kartans egen projektion (SWEREF 99 TM / EPSG:3006) —
  // klickpunkten rakt av, ingen transform. Visas bara som referens; alla
  // API-anrop går fortfarande i EPSG:3014 (se geotillsyn.js).
  function granskadPunktRad(coords) {
    if (!Array.isArray(coords) || coords.length < 2) return '';
    const e = Math.round(coords[0]);
    const n = Math.round(coords[1]);
    return `<div class="gt-fastighet__punkt">`
      + `<span class="gt-fastighet__punkt-etikett">${escapeHtml(texts.granskadPunkt)}</span>`
      + ` · E ${e} · N ${n} (SWEREF 99 TM)</div>`;
  }

  function beslutBlock() {
    return `<section class="gt-beslut">
      <div class="gt-kort__huvud">
        <span class="gt-kort__ikon">${IKONER.lock}</span>
        <div><h3>${escapeHtml(texts.beslutRubrik)}</h3></div>
      </div>
      <div class="gt-beslut__falt">${escapeHtml(texts.beslutTomt)}</div>
      <div class="gt-beslut__under">${escapeHtml(texts.beslutUnder)}</div>
    </section>`;
  }

  /**
   * @param {number[]} [coords] Klickpunkten i kartans egen projektion
   *   (SWEREF 99 TM), för den granskade-punkt-raden i fastighetsrubriken.
   */
  function startaAnalys(coords) {
    kropp().innerHTML = `
      ${radarTillbakaRad()}
      <div class="gt-fastighet">
        <span class="gt-fastighet__etikett">${escapeHtml(texts.fastighet)}</span>
        <div class="gt-fastighet__namn"><span class="gt-skelett" style="width:9rem"></span></div>
        ${granskadPunktRad(coords)}
      </div>
      <div class="gt-sammanfattning"></div>
      ${CHECK_KEYS.map(kortSkal).join('')}
      ${beslutBlock()}
      <section class="gt-snedbild" hidden>
        <div class="gt-kort__huvud">
          <span class="gt-kort__ikon">${IKONER.snedbild}</span>
          <div><h3>${escapeHtml(texts.snedbildRubrik)}</h3>
            <span class="gt-kort__under">${escapeHtml(texts.snedbildUnder)}</span></div>
        </div>
        <div class="gt-snedbild__status"></div>
        <div class="gt-snedbild__bilder"></div>
      </section>`;
    CHECK_KEYS.forEach(setCardLoading);
    kopplaRadarTillbaka();
  }

  /* --- tillsynsradar: kandidatlista för hela den synliga vyn --- */

  function radarSkal() {
    return `<section class="gt-radar">
      <div class="gt-kort__huvud">
        <span class="gt-kort__ikon">${IKONER.radar}</span>
        <div><h3>${escapeHtml(texts.radarRubrik)}</h3>
          <span class="gt-kort__under">${escapeHtml(texts.radarUnder)}</span></div>
      </div>
      <div class="gt-radar__status"></div>
      <div class="gt-radar__innehall"></div>
    </section>`;
  }

  function radarEl() { return kropp().querySelector('.gt-radar'); }

  function setRadarLoading() {
    radarAktiv = true;
    kropp().innerHTML = radarSkal();
    radarEl().querySelector('.gt-radar__status').innerHTML =
      '<span class="gt-skelett"></span><span class="gt-skelett"></span>';
  }

  /**
   * @param {string} rubrik Rubrikraden (t.ex. "3 kandidater av 57 byggnader i vyn").
   * @param {string} html Listans HTML (radar.mjs). Varje `.gt-radar__val` bär
   *   data-e/data-n (EPSG:3014) och klick går till onRadarVal(e, n).
   */
  function setRadarResult(rubrik, html) {
    radarAktiv = true;
    if (!radarEl()) kropp().innerHTML = radarSkal();
    const r = radarEl();
    r.querySelector('.gt-radar__status').innerHTML =
      `<div class="gt-rubrikrad">${escapeHtml(rubrik)}</div>`;
    const inneh = r.querySelector('.gt-radar__innehall');
    inneh.innerHTML = html;
    inneh.querySelectorAll('.gt-radar__val').forEach((knapp) => {
      knapp.addEventListener('click', () => {
        const e = Number(knapp.dataset.e);
        const n = Number(knapp.dataset.n);
        if (Number.isFinite(e) && Number.isFinite(n) && onRadarVal) onRadarVal(e, n);
      });
    });
  }

  function setRadarInfo(text) {
    radarAktiv = true;
    if (!radarEl()) kropp().innerHTML = radarSkal();
    const r = radarEl();
    r.querySelector('.gt-radar__status').innerHTML = `<div class="gt-info">${escapeHtml(text)}</div>`;
    r.querySelector('.gt-radar__innehall').innerHTML = '';
  }

  function setRadarError(message) {
    if (!radarEl()) kropp().innerHTML = radarSkal();
    const r = radarEl();
    r.querySelector('.gt-radar__status').innerHTML =
      `<div class="gt-kort__fel"><span>${escapeHtml(message)}</span>
        <button class="gt-knapp gt-knapp--primar" type="button">${escapeHtml(texts.forsokIgen)}</button></div>`;
    r.querySelector('.gt-kort__fel .gt-knapp').addEventListener('click', () => onRadar && onRadar());
    r.querySelector('.gt-radar__innehall').innerHTML = '';
  }

  /* --- snedbilder (MapSpace): fyra riktningar, bilder proxas via backend --- */

  function snedbildEl() { return kropp().querySelector('.gt-snedbild'); }

  function setSnedbilderLoading() {
    const s = snedbildEl();
    if (!s) return;
    s.hidden = false;
    s.querySelector('.gt-snedbild__status').innerHTML =
      `<div class="gt-info">${escapeHtml(texts.snedbildLaddar)}</div>`;
    s.querySelector('.gt-snedbild__bilder').innerHTML = '';
  }

  function setSnedbilderInfo(text) {
    const s = snedbildEl();
    if (!s) return;
    s.hidden = false;
    s.querySelector('.gt-snedbild__status').innerHTML =
      `<div class="gt-info">${escapeHtml(text)}</div>`;
    s.querySelector('.gt-snedbild__bilder').innerHTML = '';
  }

  /**
   * @param {object} data Svar från /api/snedbild ({tillganglig, bilder, ar, viewer_url}).
   * @param {(riktning: string, datum: string) => string} bildUrl Bygger bild-URL:en
   *   (backend-proxy — nyckeln lämnar aldrig servern).
   */
  function setSnedbilder(data, bildUrl) {
    const s = snedbildEl();
    if (!s) return;
    s.hidden = false;
    if (!data || !data.tillganglig) {
      setSnedbilderInfo(texts.snedbildSaknas);
      return;
    }
    const riktningar = texts.riktning || {};
    const bilder = (data.bilder || []).map((b) => {
      const namn = riktningar[b.riktning] || b.riktning;
      const alt = texts.snedbildAlt(namn, b.datum);
      return `<figure class="gt-snedbild__fig">
        <a href="${escapeHtml(bildUrl(b.riktning, b.datum))}" target="_blank" rel="noopener noreferrer">
          <img src="${escapeHtml(bildUrl(b.riktning, b.datum))}" alt="${escapeHtml(alt)}" loading="lazy"></a>
        <figcaption><b>${escapeHtml(namn)}</b> · ${escapeHtml(b.datum)}${b.copyright ? ` · © ${escapeHtml(b.copyright)}` : ''}</figcaption>
      </figure>`;
    }).join('');
    const lank = data.viewer_url
      ? `<a class="gt-knapp gt-snedbild__oppna" href="${escapeHtml(data.viewer_url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(texts.snedbildOppna)} ↗</a>`
      : '';
    s.querySelector('.gt-snedbild__status').innerHTML = lank;
    s.querySelector('.gt-snedbild__bilder').innerHTML = `<div class="gt-snedbild__grid">${bilder}</div>`;
  }

  function setFastighet(namn) {
    const elF = kropp().querySelector('.gt-fastighet__namn');
    if (!elF) return;
    if (namn) {
      elF.textContent = namn;
      elF.classList.remove('gt-fastighet__namn--saknas');
    } else {
      elF.textContent = texts.ingenFastighet;
      elF.classList.add('gt-fastighet__namn--saknas');
    }
  }

  /**
   * @param {{tal: string, under: string, badge: (string|null)}} headline
   *   Display-rubriken från dossier.mjs composeHeadline: stort tal, en
   *   underrad komponerad enbart av fält backend skickat, och en valfri
   *   neutral badge.
   * @param {number} [osakerheter] Antal osäkerheter i kortets body — styr om
   *   en "N osäkerheter"-chip visas som fäller upp/ner den redan renderade
   *   `.gt-osakerhet[hidden]`-blocket (renderCheckBody döljer den som default).
   */
  function setCardResult(key, { headline, body, osakerheter }) {
    const k = kort(key);
    if (!k) return;
    const h = headline || {};
    const badgeHtml = h.badge ? `<span class="gt-kort__badge">${escapeHtml(h.badge)}</span>` : '';
    const underHtml = h.under ? `<div class="gt-kort__underrad">${escapeHtml(h.under)}</div>` : '';
    const n = osakerheter || 0;
    const chipHtml = n > 0
      ? `<button type="button" class="gt-osakerhet-chip" aria-expanded="false">${escapeHtml(texts.osakerheterChip(n))}</button>`
      : '';
    k.querySelector('.gt-kort__status').innerHTML =
      `<div class="gt-kort__tal">${escapeHtml(h.tal)}${badgeHtml}</div>${underHtml}${chipHtml}`;
    const inneh = k.querySelector('.gt-kort__innehall');
    inneh.innerHTML = body;
    inneh.hidden = false;
    const chip = k.querySelector('.gt-osakerhet-chip');
    if (chip) {
      chip.addEventListener('click', () => {
        const block = inneh.querySelector('.gt-osakerhet');
        if (!block) return;
        block.hidden = !block.hidden;
        chip.setAttribute('aria-expanded', String(!block.hidden));
      });
    }
  }

  /**
   * Sammanfattningsraden: en chip per kontroll med kontrollens namn och dess
   * underlagsläge (aldrig ett utfall). Klick scrollar till kortet.
   * @param {Object<string,string>} [lagen] key -> underlagsLage()-resultat.
   */
  function setSammanfattning(lagen) {
    const container = kropp().querySelector('.gt-sammanfattning');
    if (!container) return;
    if (!lagen) { container.innerHTML = ''; return; }
    container.innerHTML = CHECK_KEYS.map((key) => {
      const lage = lagen[key];
      if (!lage) return '';
      const textnyckel = UNDERLAG_TEXTNYCKEL[lage] || 'underlagInget';
      return `<button type="button" class="gt-chip gt-chip--${escapeHtml(lage)}" data-check="${key}">
        <span class="gt-chip__namn">${escapeHtml(texts.checkTitel[key])}</span>
        <span class="gt-chip__lage">${escapeHtml(texts[textnyckel])}</span>
      </button>`;
    }).join('');
    container.querySelectorAll('.gt-chip').forEach((chip) => {
      chip.addEventListener('click', () => {
        const target = kort(chip.dataset.check);
        if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
    });
  }

  /**
   * Kandidatraden under strandskyddskortets rubrik: "N andra byggnader inom
   * 150 m berör zonen" + knappen "Visa kandidater i kartan". antalAndra<=0
   * döljer raden (inga andra kandidater att visa).
   * @param {number} antalAndra
   * @param {(() => void)|null} onVisa
   */
  function setStrandskyddKandidater(antalAndra, onVisa) {
    const k = kort('strandskydd');
    if (!k) return;
    const status = k.querySelector('.gt-kort__status');
    let rad = status.querySelector('.gt-kort__kandidatrad');
    if (rad) rad.remove();
    if (!antalAndra || antalAndra <= 0) return;
    rad = document.createElement('div');
    rad.className = 'gt-kort__kandidatrad';
    rad.innerHTML = `<span>${escapeHtml(texts.andraByggnader(antalAndra))}</span>`
      + `<button type="button" class="gt-knapp gt-kort__visakandidater">${escapeHtml(texts.visaKandidater)}</button>`;
    status.appendChild(rad);
    rad.querySelector('button').addEventListener('click', () => onVisa && onVisa());
  }

  function setCardInfo(key, text) {
    const k = kort(key);
    if (!k) return;
    k.querySelector('.gt-kort__status').innerHTML =
      `<div class="gt-info">${escapeHtml(text)}</div>`;
    const inneh = k.querySelector('.gt-kort__innehall');
    inneh.hidden = true;
    inneh.innerHTML = '';
  }

  function setCardError(key, message) {
    const k = kort(key);
    if (!k) return;
    k.querySelector('.gt-kort__status').innerHTML =
      `<div class="gt-kort__fel"><span>${escapeHtml(message)}</span>
        <button class="gt-knapp gt-knapp--primar" type="button">${escapeHtml(texts.forsokIgen)}</button></div>`;
    k.querySelector('.gt-kort__fel .gt-knapp').addEventListener('click', () => onRetry(key));
    const inneh = k.querySelector('.gt-kort__innehall');
    inneh.hidden = true;
    inneh.innerHTML = '';
  }

  function setCollapsed(kollapsad) {
    el.classList.toggle('gt-panel--kollapsad', kollapsad);
    tabEl.hidden = !kollapsad;
  }

  function uppdateraTexter(nyaT) {
    texts = nyaT;
    // Endast chrome: rubriker, fot, korttitlar. Kortens status/innehåll ägs av
    // wiring-lagret, som renderar om resultaten efter språkbytet.
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
      const k = kort(key);
      if (!k) return;
      k.querySelector('h3').textContent = texts.checkTitel[key];
      k.querySelector('.gt-kort__under').textContent = texts.checkUndertitel[key];
    });
    if (kropp().querySelector('.gt-tom')) visaTomlage();
    const fastEtikett = kropp().querySelector('.gt-fastighet__etikett');
    if (fastEtikett) fastEtikett.textContent = texts.fastighet;
    const punktEtikett = kropp().querySelector('.gt-fastighet__punkt-etikett');
    if (punktEtikett) punktEtikett.textContent = texts.granskadPunkt;
    const beslut = kropp().querySelector('.gt-beslut');
    if (beslut) {
      beslut.querySelector('h3').textContent = texts.beslutRubrik;
      beslut.querySelector('.gt-beslut__falt').textContent = texts.beslutTomt;
      beslut.querySelector('.gt-beslut__under').textContent = texts.beslutUnder;
    }
    const sned = snedbildEl();
    if (sned) {
      sned.querySelector('h3').textContent = texts.snedbildRubrik;
      sned.querySelector('.gt-kort__under').textContent = texts.snedbildUnder;
    }
    const radarKnapp = el.querySelector('.gt-radarknapp');
    radarKnapp.querySelector('span').textContent = texts.radarKnapp;
    radarKnapp.setAttribute('aria-label', texts.radarKnappAria);
    radarKnapp.setAttribute('title', texts.radarKnappAria);
    const radar = radarEl();
    if (radar) {
      radar.querySelector('h3').textContent = texts.radarRubrik;
      radar.querySelector('.gt-kort__under').textContent = texts.radarUnder;
    }
    const tillbaka = kropp().querySelector('.gt-radar__tillbaka');
    if (tillbaka) tillbaka.textContent = `‹ ${texts.radarTillbaka}`;
  }

  render();
  visaTomlage();
  return { el, tabEl, setCollapsed, visaTomlage, startaAnalys, setFastighet,
    setCardLoading, setCardResult, setCardInfo, setCardError, uppdateraTexter,
    setSammanfattning, setStrandskyddKandidater,
    setSnedbilderLoading, setSnedbilderInfo, setSnedbilder,
    setRadarLoading, setRadarResult, setRadarInfo, setRadarError };
}

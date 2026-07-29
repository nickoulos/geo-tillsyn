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

  function setCardLoading(key) {
    const k = kort(key);
    if (!k) return;
    k.querySelector('.gt-kort__status').innerHTML =
      '<span class="gt-skelett"></span><span class="gt-skelett"></span>';
    const inneh = k.querySelector('.gt-kort__innehall');
    inneh.hidden = true;
    inneh.innerHTML = '';
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
    if (namn) {
      elF.textContent = namn;
      elF.classList.remove('gt-fastighet__namn--saknas');
    } else {
      elF.textContent = texts.ingenFastighet;
      elF.classList.add('gt-fastighet__namn--saknas');
    }
  }

  function setCardResult(key, { headline, body }) {
    const k = kort(key);
    if (!k) return;
    k.querySelector('.gt-kort__status').innerHTML =
      `<div class="gt-rubrikrad">${escapeHtml(headline)}</div>`;
    const inneh = k.querySelector('.gt-kort__innehall');
    inneh.innerHTML = body;
    inneh.hidden = false;
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
  }

  render();
  visaTomlage();
  return { el, tabEl, setCollapsed, visaTomlage, startaAnalys, setFastighet,
    setCardLoading, setCardResult, setCardInfo, setCardError, uppdateraTexter };
}

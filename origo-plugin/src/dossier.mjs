/**
 * Dossier-rendering: neutrala rubriker + kontrollkortens innehåll
 * (Fakta/Bedömning/Källor/Osäkerheter) från valfritt backend-svar.
 *
 * Neutralitetsregeln: UI:t komponerar aldrig ett skuld-ord eller ett friande
 * påstående som backend inte skickat. Rubriker byggs enbart av fält backend
 * faktiskt skickat; saknas komponerbara fält visas "Se underlag".
 */

import { faltLabel, teckenTal } from './i18n.mjs';

// Nycklar som visas separat (rubrik, osäkerheter, källor) eller är metadata
// och alltså inte ska upprepas generiskt i Fakta/Bedömning-listorna.
const HOPPA_OVER = new Set(['kallor', 'osakerheter', 'meddelande', 'fel', 'hamtad',
  'punkt', 'traffar', 'juridisk_not', 'korsjamforelse', 'lov_hittat']);

// Fält som hör hemma under "Bedömning" (juridisk tolkning) snarare än
// "Fakta" (rådata/mätvärden). Allt annat okänt fält hamnar i Fakta.
const BEDOMNING_FALT = new Set(['bal_forenligt', 'bygglov_kravdes', 'lovbefrielse',
  'rattelse_preskriberad', 'sanktionsavgift_mojlig', 'matningskritiskt',
  'matningskritiska', 'inom_strandskydd', 'pbl_vid_beslut', 'overgangsregel_tillampad',
  'dispens_kravs_idag', 'preskriberas', 'gallde_vid_uppforande']);

export function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (ch) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[ch]));
}

export function formatVarde(value, t) {
  if (value === null || value === undefined) return t.ejFaststallt;
  if (typeof value === 'boolean') {
    return `<span class="gt-badge">${value ? t.ja : t.nej}</span>`;
  }
  if (Array.isArray(value)) {
    if (value.length === 0) return t.inga;
    if (value.every((v) => typeof v === 'object' && v !== null)) {
      return value.map((v) => escapeHtml(JSON.stringify(v))).join('; ');
    }
    return value.map((v) => escapeHtml(String(v))).join(', ');
  }
  if (typeof value === 'object') return escapeHtml(JSON.stringify(value));
  return escapeHtml(String(value));
}

function rad(key, value, t, sprak) {
  return `<div class="gt-rad"><span class="gt-rad__etikett">${escapeHtml(faltLabel(key, sprak))}</span>`
    + `<span class="gt-rad__varde">${formatVarde(value, t)}</span></div>`;
}

function renderKallor(kallor, t) {
  if (!Array.isArray(kallor) || kallor.length === 0) return '';
  const items = kallor.map((k) => {
    const beskrivning = escapeHtml(k && k.beskrivning ? k.beskrivning : '');
    const url = k && k.url ? String(k.url) : null;
    if (url && /^https?:\/\//i.test(url)) {
      return `<li><a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${beskrivning}</a></li>`;
    }
    return `<li>${beskrivning}</li>`;
  }).join('');
  return `<div class="gt-kallor"><span class="gt-kallor__rubrik">${escapeHtml(t.kallor)}</span>`
    + `<ul>${items}</ul></div>`;
}

function renderOsakerheter(osakerheter, t) {
  if (!Array.isArray(osakerheter) || osakerheter.length === 0) return '';
  const items = osakerheter.map((o) => `<li>${escapeHtml(String(o))}</li>`).join('');
  return `<div class="gt-osakerhet" role="note" aria-label="${escapeHtml(t.osakerheter)}">`
    + `<ul>${items}</ul></div>`;
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
    return `<div class="gt-info">${escapeHtml(data.meddelande)}</div>`
      + renderOsakerheter(data.osakerheter, t);
  }

  const fakta = [];
  const bedomning = [];
  Object.keys(data).forEach((key) => {
    if (HOPPA_OVER.has(key)) return;
    (BEDOMNING_FALT.has(key) ? bedomning : fakta).push(rad(key, data[key], t, sprak));
  });

  // Fall 7: träffar-listan renderas nästlat per byggnad, inte generiskt.
  if (Array.isArray(data.traffar)) {
    data.traffar.forEach((traff, idx) => {
      const rader = Object.keys(traff)
        .filter((key) => key !== 'byggnad_id')
        .map((key) => rad(key, traff[key], t, sprak))
        .join('');
      fakta.push(`<div class="gt-traff">#${idx + 1} ${escapeHtml(faltLabel('byggnad_id', sprak))}: `
        + `${escapeHtml(String(traff.byggnad_id))}</div>${rader}`);
    });
  }

  if (data.korsjamforelse) {
    Object.keys(data.korsjamforelse).forEach((key) => {
      bedomning.push(`<div class="gt-rad"><span class="gt-rad__etikett">${escapeHtml(key)}</span>`
        + `<span class="gt-rad__varde">${formatVarde(data.korsjamforelse[key], t)}</span></div>`);
    });
  }

  const sektion = (rubrik, inre, oppen) =>
    `<details class="gt-sektion"${oppen ? ' open' : ''}><summary>${escapeHtml(rubrik)}</summary>`
    + `<div class="gt-sektion__inner">${inre || '<div class="gt-info">—</div>'}</div></details>`;

  return renderOsakerheter(data.osakerheter, t)
    + sektion(t.fakta, fakta.join('') + renderKallor(data.kallor, t), false)
    + sektion(t.bedomning, bedomning.join(''), true);
}

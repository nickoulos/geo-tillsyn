/**
 * Dossier-rendering: neutrala rubriker + kontrollkortens innehåll
 * (Fakta/Bedömning/Källor/Osäkerheter) från valfritt backend-svar.
 *
 * Neutralitetsregeln: UI:t komponerar aldrig ett skuld-ord eller ett friande
 * påstående som backend inte skickat. Rubriker byggs enbart av fält backend
 * faktiskt skickat; saknas komponerbara fält visas "Se underlag".
 */

import { faltLabel, meddelandeText, teckenTal, vardeLabel } from './i18n.mjs';

// Nycklar som visas separat (rubrik, osäkerheter, källor) eller är metadata
// och alltså inte ska upprepas generiskt i Fakta/Bedömning-listorna.
const HOPPA_OVER = new Set(['kallor', 'osakerheter', 'meddelande', 'fel', 'hamtad',
  'punkt', 'traffar', 'juridisk_not', 'korsjamforelse', 'lov_hittat', 'rattigheter',
  'snedbilder']);

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

// Ett backend-meddelande på tråden: {kod, params} — allt annat är rådata.
function arMeddelande(v) {
  return typeof v === 'object' && v !== null && typeof v.kod === 'string';
}

/**
 * @param {*} value Värdet från backend.
 * @param {object} t Aktiv textkatalog.
 * @param {string} sprak 'sv' | 'en'.
 * @param {string} [falt] Fältnamnet, när värdet är en uppräkning (t.ex. `laege`)
 *   vars koder ska översättas via VARDE_LABEL.
 */
export function formatVarde(value, t, sprak, falt) {
  if (value === null || value === undefined) return t.ejFaststallt;
  if (typeof value === 'boolean') {
    return `<span class="gt-badge">${value ? t.ja : t.nej}</span>`;
  }
  if (arMeddelande(value)) return escapeHtml(meddelandeText(value, sprak));
  if (Array.isArray(value)) {
    if (value.length === 0) return t.inga;
    if (value.every(arMeddelande)) {
      return value.map((v) => escapeHtml(meddelandeText(v, sprak))).join(' ');
    }
    if (value.every((v) => typeof v === 'object' && v !== null)) {
      return value.map((v) => escapeHtml(JSON.stringify(v))).join('; ');
    }
    return value.map((v) => escapeHtml(String(v))).join(', ');
  }
  if (typeof value === 'object') return escapeHtml(JSON.stringify(value));
  if (falt) return escapeHtml(vardeLabel(falt, String(value), sprak));
  return escapeHtml(String(value));
}

// Rättigheter/gemensamhetsanläggningar: en rad per objekt — typ, akt, ändamål,
// fastighet. Identifierare (aktbeteckning, fastighet) står kvar ordagrant.
export function renderRattigheter(rattigheter, t, sprak) {
  if (!Array.isArray(rattigheter)) return '';
  const etikett = escapeHtml(faltLabel('rattigheter', sprak));
  if (rattigheter.length === 0) {
    return `<div class="gt-rad"><span class="gt-rad__etikett">${etikett}</span>`
      + `<span class="gt-rad__varde">${escapeHtml(t.inga)}</span></div>`;
  }
  const typer = t.rattighetTyp || {};
  const items = rattigheter.map((r) => {
    const typ = escapeHtml(typer[r.typ] || r.typ || '');
    const akt = r.aktbeteckning ? ` <b>${escapeHtml(r.aktbeteckning)}</b>` : '';
    const detalj = r.andamal || r.beskrivning;
    const detaljDel = detalj ? ` — ${escapeHtml(detalj)}` : '';
    const fast = r.fastighet ? ` <span class="gt-rattighet__fast">(${escapeHtml(r.fastighet)})</span>` : '';
    return `<li>${typ}${akt}${detaljDel}${fast}</li>`;
  }).join('');
  return `<div class="gt-rad gt-rad--block"><span class="gt-rad__etikett">${etikett}</span>`
    + `<ul class="gt-rattigheter">${items}</ul></div>`;
}

function rad(key, value, t, sprak, vardeFalt) {
  return `<div class="gt-rad"><span class="gt-rad__etikett">${escapeHtml(faltLabel(key, sprak))}</span>`
    + `<span class="gt-rad__varde">${formatVarde(value, t, sprak, vardeFalt)}</span></div>`;
}

export function renderKallor(kallor, t, sprak) {
  if (!Array.isArray(kallor) || kallor.length === 0) return '';
  const items = kallor.map((k) => {
    const beskrivning = escapeHtml(k ? meddelandeText(k.beskrivning, sprak) : '');
    const url = k && k.url ? String(k.url) : null;
    if (url && /^https?:\/\//i.test(url)) {
      return `<li><a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${beskrivning}</a></li>`;
    }
    return `<li>${beskrivning}</li>`;
  }).join('');
  return `<div class="gt-kallor"><span class="gt-kallor__rubrik">${escapeHtml(t.kallor)}</span>`
    + `<ul>${items}</ul></div>`;
}

export function renderOsakerheter(osakerheter, t, sprak) {
  if (!Array.isArray(osakerheter) || osakerheter.length === 0) return '';
  const items = osakerheter
    .map((o) => `<li>${escapeHtml(meddelandeText(o, sprak))}</li>`).join('');
  return `<div class="gt-osakerhet" role="note" aria-label="${escapeHtml(t.osakerheter)}">`
    + `<ul>${items}</ul></div>`;
}

export function composeHeadline(checkKey, data, t, sprak) {
  if (data && data.meddelande) return meddelandeText(data.meddelande, sprak);
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
    return `<div class="gt-info">${escapeHtml(meddelandeText(data.meddelande, sprak))}</div>`
      + renderOsakerheter(data.osakerheter, t, sprak);
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
        .map((key) => rad(key, traff[key], t, sprak, key === 'laege' ? 'laege' : undefined))
        .join('');
      fakta.push(`<div class="gt-traff">#${idx + 1} ${escapeHtml(faltLabel('byggnad_id', sprak))}: `
        + `${escapeHtml(String(traff.byggnad_id))}</div>${rader}`);
    });
  }

  if (Array.isArray(data.rattigheter)) {
    fakta.push(renderRattigheter(data.rattigheter, t, sprak));
  }

  // Korskontrollen OCR vs register: fältnamnen är våra egna (dnr, beslutsdatum,
  // byggnadsarea_m2) och utfallen en uppräkning — båda ska översättas.
  if (data.korsjamforelse) {
    Object.keys(data.korsjamforelse).forEach((key) => {
      bedomning.push(rad(key, data.korsjamforelse[key], t, sprak, 'korsjamforelse'));
    });
  }

  const sektion = (rubrik, inre, oppen) =>
    `<details class="gt-sektion"${oppen ? ' open' : ''}><summary>${escapeHtml(rubrik)}</summary>`
    + `<div class="gt-sektion__inner">${inre || '<div class="gt-info">—</div>'}</div></details>`;

  return renderOsakerheter(data.osakerheter, t, sprak)
    + sektion(t.fakta, fakta.join('') + renderKallor(data.kallor, t, sprak), false)
    + sektion(t.bedomning, bedomning.join(''), true);
}

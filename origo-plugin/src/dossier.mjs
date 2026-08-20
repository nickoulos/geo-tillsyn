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
  'snedbilder', 'resonemang']);

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

export function renderOsakerheter(osakerheter, t, sprak, hidden = false) {
  if (!Array.isArray(osakerheter) || osakerheter.length === 0) return '';
  const items = osakerheter
    .map((o) => `<li>${escapeHtml(meddelandeText(o, sprak))}</li>`).join('');
  return `<div class="gt-osakerhet"${hidden ? ' hidden' : ''} role="note" aria-label="${escapeHtml(t.osakerheter)}">`
    + `<ul>${items}</ul></div>`;
}

// Fall 7: träffen som gäller den klickade byggnaden — den enda träffen
// display-rubriken och osäkerhetsbedömningen får bygga på. `vald_byggnad_id`
// null betyder "ingen specifik byggnad vald" (t.ex. äldre svar) och faller
// tillbaka på den första träffen; en satt men obekräftad vald_byggnad_id som
// inte finns bland träffarna betyder "utanför zon" och ger ingen träff alls.
function valdTraff(data) {
  if (!data || !Array.isArray(data.traffar)) return null;
  if (data.vald_byggnad_id == null) return data.traffar[0] || null;
  return data.traffar.find((traff) => traff.byggnad_id === data.vald_byggnad_id) || null;
}

function headlineOlovligt(data, t) {
  if (data.forsta_ar_med == null) return { tal: t.seUnderlag, under: '', badge: null };
  const tal = data.sista_ar_utan != null
    ? `${data.sista_ar_utan} → ${data.forsta_ar_med}`
    : `→ ${data.forsta_ar_med}`;
  const underDelar = [t.forstSynligOrtofoto];
  if (data.bal_nybyggnadsar != null) underDelar.push(t.registretSager(data.bal_nybyggnadsar));
  const badge = data.bal_forenligt === false ? t.avviker : null;
  return { tal, under: underDelar.join(' · '), badge };
}

function headlineLovavvikelse(data, t, sprak) {
  if (typeof data.area_diff_m2 !== 'number' || typeof data.area_diff_procent !== 'number') {
    return { tal: t.seUnderlag, under: '', badge: null };
  }
  const tal = `${teckenTal(data.area_diff_m2, sprak)} m²`;
  const underDelar = [`${teckenTal(data.area_diff_procent, sprak)} % ${t.motGodkantLov}`];
  if (data.dnr) underDelar.push(data.dnr);
  return { tal, under: underDelar.join(' · '), badge: null };
}

function headlineStrandskydd(data, t) {
  if (!data || !Array.isArray(data.traffar)) return { tal: t.seUnderlag, under: '', badge: null };
  if (data.vald_byggnad_id != null && !data.traffar.some((tr) => tr.byggnad_id === data.vald_byggnad_id)) {
    // Vald byggnad finns, men berör ingen av zonens träffar.
    return { tal: t.utanforStrandskydd, under: '', badge: null };
  }
  const traff = valdTraff(data);
  if (!traff) return { tal: t.seUnderlag, under: '', badge: null };
  const tal = traff.laege === 'inom' ? t.inomStrandskydd : t.delvisInomStrandskydd;
  const underDelar = [];
  const zonRef = Array.isArray(traff.zon_referenser) ? traff.zon_referenser[0] : traff.zon_referenser;
  if (zonRef) underDelar.push(t.zon(zonRef));
  if (traff.byggnads_ar != null) underDelar.push(t.uppford(traff.byggnads_ar));
  if (traff.preskriberas === false) underDelar.push(t.ingenPreskriptionKort);
  if (traff.dispens_kravs_idag === true) underDelar.push(t.dispensKravs);
  return { tal, under: underDelar.join(' · '), badge: null };
}

/**
 * @returns {{tal: string, under: string, badge: (string|null)}} Display-rubriken:
 *   ett stort tal/uttryck (`tal`), en underrad komponerad enbart av fält
 *   backend faktiskt skickat (`under`), och en valfri neutral badge (`badge`,
 *   t.ex. "avviker" — aldrig ett skuld- eller friande omdöme). Saknas
 *   komponerbara fält: `{tal: t.seUnderlag, under: '', badge: null}`.
 */
export function composeHeadline(checkKey, data, t, sprak) {
  if (data && data.meddelande) {
    return { tal: meddelandeText(data.meddelande, sprak), under: '', badge: null };
  }
  if (!data) return { tal: t.seUnderlag, under: '', badge: null };
  if (checkKey === 'olovligt') return headlineOlovligt(data, t);
  if (checkKey === 'lovavvikelse') return headlineLovavvikelse(data, t, sprak);
  if (checkKey === 'strandskydd') return headlineStrandskydd(data, t);
  return { tal: t.seUnderlag, under: '', badge: null };
}

/**
 * Underlagsläge för sammanfattningschipsen — beskriver ALDRIG ett utfall,
 * bara om/hur säkert underlag finns: 'finns' | 'osakert' | 'inget' | 'hamtar' | 'fel'.
 * @param {object} [status] `{typ: 'fel'|'info'|'laddar'}` — wiring-lagrets syn
 *   på kortets läge, samma som driver setCardError/setCardInfo/setCardLoading.
 */
export function underlagsLage(checkKey, data, status) {
  if (status && status.typ === 'fel') return 'fel';
  if (status && status.typ === 'info') return 'inget';
  if (status && status.typ === 'laddar') return 'hamtar';
  if (!data) return 'hamtar';
  if (checkKey === 'olovligt') {
    return (data.matningskritiskt || data.forsta_ar_med == null) ? 'osakert' : 'finns';
  }
  if (checkKey === 'lovavvikelse') {
    return (Array.isArray(data.matningskritiska) && data.matningskritiska.length > 0) ? 'osakert' : 'finns';
  }
  if (checkKey === 'strandskydd') {
    const traffar = Array.isArray(data.traffar) ? data.traffar : [];
    if (data.vald_byggnad_id != null
        && !traffar.some((tr) => tr.byggnad_id === data.vald_byggnad_id)) {
      // Vald byggnad finns men berör ingen av zonens träffar (traffar kan
      // vara tom eller icke-tom här — headlineStrandskydd komponerar
      // "Utanför zon" oavsett) — underlag finns, det säger bara nej.
      return 'finns';
    }
    const traff = valdTraff(data);
    // Ingen träff alls att komponera från (samma svar som ger composeHeadline
    // "Se underlag") — inget underlag, inte "finns".
    if (!traff) return 'inget';
    const osakert = (Array.isArray(traff.atgarder) && traff.atgarder.length > 0) || traff.byggnads_ar == null;
    return osakert ? 'osakert' : 'finns';
  }
  return 'finns';
}

/**
 * Resonemangskedjan: fråga -> lagrum -> svar, i den ordning motorn gick.
 * Svaren är rådata (bool/str/null) och renderas som badge/text/»Ej fastställt«;
 * sista noden är alltid beslutet, vars svar aldrig kommer från backend.
 */
export function renderResonemang(noder, t, sprak) {
  if (!Array.isArray(noder) || noder.length === 0) return '';
  const steg = noder.map((nod, i) => {
    const fraga = escapeHtml(meddelandeText(nod.fraga, sprak));
    const svar = formatVarde(nod.svar === undefined ? null : nod.svar, t, sprak,
      typeof nod.svar === 'string' ? 'laege' : undefined);
    return `<li class="gt-kedja__steg">
      <span class="gt-kedja__nr">${i + 1}</span>
      <span class="gt-kedja__innehall"><span class="gt-kedja__fraga">${fraga}</span>
        <span class="gt-kedja__lagrum">${escapeHtml(nod.lagrum || '')}</span></span>
      <span class="gt-kedja__svar">${svar}</span>
    </li>`;
  }).join('');
  return `<ol class="gt-kedja">${steg}</ol>`;
}

export function renderCheckBody(data, t, sprak) {
  if (data.meddelande) {
    return `<div class="gt-info">${escapeHtml(meddelandeText(data.meddelande, sprak))}</div>`
      + renderOsakerheter(data.osakerheter, t, sprak, true);
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
        .map((key) => (key === 'rattigheter'
          ? renderRattigheter(traff[key], t, sprak)
          : rad(key, traff[key], t, sprak, key === 'laege' ? 'laege' : undefined)))
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

  const resonemang = renderResonemang(data.resonemang, t, sprak);
  return renderOsakerheter(data.osakerheter, t, sprak, true)
    + sektion(t.fakta, fakta.join('') + renderKallor(data.kallor, t, sprak), false)
    + sektion(t.bedomning, bedomning.join(''), true)
    + (resonemang ? sektion(t.resonemang, resonemang, false) : '');
}

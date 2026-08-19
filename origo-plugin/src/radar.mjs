/**
 * Tillsynsradar-rendering: kandidatlistan för en skannad zon.
 *
 * Samma neutralitetsregel som dossiern: UI:t komponerar inga skuld-ord.
 * Rangordning, poäng och grunder kommer från backend (öppen poängmodell);
 * listan är kandidater för granskning — handläggaren beslutar.
 */

import { escapeHtml, renderKallor, renderOsakerheter } from './dossier.mjs';
import { meddelandeText } from './i18n.mjs';

/**
 * Kartvyns extent (i kartans projektion) -> bbox i EPSG:3014 [minE, minN, maxE, maxN].
 * @param {number[]} extent [minX, minY, maxX, maxY] i kartprojektionen.
 * @param {(xy: number[]) => number[]} projicera Transform kart-CRS -> EPSG:3014.
 */
export function bboxFranExtent(extent, projicera) {
  const [x1, y1] = projicera([extent[0], extent[1]]);
  const [x2, y2] = projicera([extent[2], extent[3]]);
  return [Math.min(x1, x2), Math.min(y1, y2), Math.max(x1, x2), Math.max(y1, y2)];
}

export function renderRadarRubrik(data, t) {
  return t.radarRubrikRad(data.antal_traffar || 0, data.antal_byggnader || 0);
}

function renderKandidat(k, t, sprak) {
  const fastighet = k.fastighet
    ? `<span class="gt-radar__fastighet">${escapeHtml(k.fastighet)}</span>`
    : `<span class="gt-radar__fastighet gt-radar__fastighet--saknas">${escapeHtml(t.saknarBeteckning)}</span>`;
  const ar = k.byggnads_ar != null ? String(k.byggnads_ar) : t.ejFaststallt;
  const grunder = (k.grunder || [])
    .map((g) => `<li>${escapeHtml(meddelandeText(g, sprak))}</li>`).join('');
  const e = k.centroid ? k.centroid.easting : '';
  const n = k.centroid ? k.centroid.northing : '';
  return `<li class="gt-radar__rad" data-rang="${escapeHtml(k.rang)}">
    <button type="button" class="gt-radar__val" data-e="${escapeHtml(e)}" data-n="${escapeHtml(n)}"
      aria-label="${escapeHtml(t.radarOppnaAria(k.rang))}">
      <span class="gt-radar__rang">${escapeHtml(k.rang)}</span>
      <span class="gt-radar__kropp">
        ${fastighet}
        <span class="gt-radar__meta">${escapeHtml(k.byggnad_id)} · ${escapeHtml(t.radarAr)} ${ar}</span>
      </span>
      <span class="gt-radar__poang">${escapeHtml(k.poang)} ${escapeHtml(t.radarPoangEnhet)}</span>
    </button>
    <details class="gt-radar__grunder"><summary>${escapeHtml(t.radarVisaGrunder)}</summary>
      <ul>${grunder}</ul></details>
  </li>`;
}

export function renderRadarLista(data, t, sprak) {
  const kandidater = data.kandidater || [];
  const not = data.juridisk_not
    ? `<div class="gt-radar__not">${escapeHtml(meddelandeText(data.juridisk_not, sprak))}</div>`
    : '';
  if (kandidater.length === 0) {
    return `<div class="gt-info">${escapeHtml(t.radarIngaKandidater)}</div>${not}`
      + renderOsakerheter(data.osakerheter, t, sprak)
      + renderKallor(data.kallor, t, sprak);
  }
  const trunkering = data.kandidater_trunkerade_till
    ? `<div class="gt-info">${escapeHtml(t.radarTrunkerad(kandidater.length, data.antal_traffar))}</div>`
    : '';
  const modell = Array.isArray(data.poangmodell) && data.poangmodell.length
    ? `<details class="gt-sektion"><summary>${escapeHtml(t.radarPoangmodell)}</summary>
        <div class="gt-sektion__inner"><ul class="gt-radar__modell">${
  data.poangmodell.map((m) => `<li>${escapeHtml(meddelandeText(m, sprak))}</li>`).join('')
}</ul></div></details>`
    : '';
  return `<ol class="gt-radar__lista">${kandidater.map((k) => renderKandidat(k, t, sprak)).join('')}</ol>`
    + trunkering + not + modell
    + renderOsakerheter(data.osakerheter, t, sprak)
    + renderKallor(data.kallor, t, sprak);
}

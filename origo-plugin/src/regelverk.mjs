/**
 * Minimal evaluator över regler.json (spegel av regelverk_core.py) +
 * rendering av regelkontexten för tidslinjepillen: en sammanfattningsrad
 * (hopfälld) och en detaljvy (expanderad).
 */

import { escapeHtml } from './dossier.mjs';

function within(rule, isoDate) {
  return rule.fran <= isoDate && (!rule.till || isoDate <= rule.till);
}

export function regelverkVid(regler, isoDate) {
  const pbl = regler.pbl_versioner.find((v) => within(v, isoDate)) || null;
  const befrielser = regler.lovbefrielser.filter((r) => within(r, isoDate));
  const ssGaller = isoDate >= regler.strandskydd.generellt_fran;
  const year = Number(isoDate.slice(0, 4));
  const tioarSlut = year + regler.preskription.pbl_tioarsregel.ar;
  return { pbl, befrielser, ssGaller, tioarSlut };
}

export function renderKontextSammanfattning(regler, isoDate, t) {
  const r = regelverkVid(regler, isoDate);
  const lag = r.pbl ? `<b>${escapeHtml(r.pbl.namn)}</b>` : '—';
  const bef = r.befrielser.length
    ? r.befrielser.map((b) => `${escapeHtml(b.namn)} ${escapeHtml(b.max_kvm)} m²`).join(', ')
    : t.ingaLovbefrielser;
  const ss = r.ssGaller ? t.ssKort : t.ssKortInte;
  return `${lag} · ${bef} · ${ss}`;
}

export function renderKontextDetalj(regler, isoDate, t) {
  const r = regelverkVid(regler, isoDate);
  const idag = new Date().getFullYear();
  const rad = (etikett, vardeHtml) =>
    `<div class="gt-rad"><span class="gt-rad__etikett">${escapeHtml(etikett)}</span>`
    + `<span class="gt-rad__varde">${vardeHtml}</span></div>`;

  const rows = [];
  rows.push(rad(t.lag, r.pbl
    ? `<b>${escapeHtml(r.pbl.namn)}</b> (${escapeHtml(r.pbl.sfs)})`
    : '—'));
  const bef = r.befrielser
    .map((b) => `${escapeHtml(b.namn)} ${escapeHtml(b.max_kvm)} m²`)
    .join(', ');
  rows.push(rad(t.lovbefrielser, bef || t.inga));
  rows.push(rad(t.strandskydd, r.ssGaller
    ? t.ssGaller
    : t.ssFinnsInte(escapeHtml(regler.strandskydd.generellt_fran))));
  const preskriberad = idag > r.tioarSlut;
  rows.push(rad(t.preskription,
    t.preskriptionText(escapeHtml(isoDate.slice(0, 4)), escapeHtml(r.tioarSlut), preskriberad)));
  return rows.join('');
}

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

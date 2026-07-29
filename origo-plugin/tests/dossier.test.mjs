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
  assert.doesNotMatch(html, /hamtad|lov_hittat|punkt/);
});

test('renderCheckBody: meddelande-svar renderas som info, inte som tom dossier', () => {
  const html = renderCheckBody({ meddelande: 'Inget lov i arkivet', osakerheter: ['x'] }, t, 'sv');
  assert.match(html, /Inget lov i arkivet/);
  assert.doesNotMatch(html, /<details/);
});

test('renderCheckBody: fall 7-träffar renderas nästlat med byggnads-rubrik', () => {
  const data = {
    antal_traffar: 1, antal_byggnader: 2,
    traffar: [{ byggnad_id: 'BAL-1', byggnads_ar: 1982, dispens_kravs_idag: true }],
    osakerheter: [], kallor: []
  };
  const html = renderCheckBody(data, t, 'sv');
  assert.match(html, /gt-traff/);
  assert.match(html, /BAL-1/);
  assert.match(html, /Dispens krävs idag/);
});

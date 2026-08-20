import test from 'node:test';
import assert from 'node:assert/strict';
import { TEXTS } from '../src/i18n.mjs';
import {
  escapeHtml, formatVarde, composeHeadline, underlagsLage, renderCheckBody
} from '../src/dossier.mjs';

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

test('composeHeadline lovavvikelse: display-tal + underrad med tecken och dnr', () => {
  assert.deepEqual(composeHeadline('lovavvikelse', FALL3, t, 'sv'), {
    tal: '+90,3 m²', under: '+38,4 % mot godkänt lov · BYGG 2009-0417', badge: null
  });
});

test('composeHeadline olovligt: intervall, aldrig skuld-ord, badge endast vid bal_forenligt===false', () => {
  const data = { sista_ar_utan: 2002, forsta_ar_med: 2007, bal_nybyggnadsar: 2014, bal_forenligt: false };
  assert.deepEqual(composeHeadline('olovligt', data, t, 'sv'), {
    tal: '2002 → 2007', under: 'först synlig i ortofoto · registret säger 2014', badge: 'avviker'
  });
  // Ingen bal_forenligt-uppgift alls -> ingen badge (aldrig gissa ett skuld-ord).
  const utanForenlighet = { sista_ar_utan: 1998, forsta_ar_med: 2001 };
  assert.equal(composeHeadline('olovligt', utanForenlighet, t, 'sv').badge, null);
  // bal_forenligt === true -> fortfarande ingen badge.
  const forenlig = { ...data, bal_forenligt: true };
  assert.equal(composeHeadline('olovligt', forenlig, t, 'sv').badge, null);
});

test('composeHeadline olovligt: sista_ar_utan null ger pilform utan undre gräns', () => {
  const data = { sista_ar_utan: null, forsta_ar_med: 2007 };
  assert.deepEqual(composeHeadline('olovligt', data, t, 'sv'), {
    tal: '→ 2007', under: 'först synlig i ortofoto', badge: null
  });
});

test('composeHeadline olovligt: forsta_ar_med saknas -> Se underlag (ingen komponerbar tal)', () => {
  assert.deepEqual(composeHeadline('olovligt', { sista_ar_utan: 1998 }, t, 'sv'),
    { tal: t.seUnderlag, under: '', badge: null });
});

test('composeHeadline strandskydd: väljer träffen som matchar vald_byggnad_id', () => {
  const data = {
    vald_byggnad_id: 'BAL-2', antal_traffar: 2, antal_byggnader: 5,
    traffar: [
      { byggnad_id: 'BAL-1', laege: 'delvis' },
      { byggnad_id: 'BAL-2', laege: 'inom', zon_referenser: ['2281K-ÖVR-241'], byggnads_ar: 2014, preskriberas: false }
    ]
  };
  assert.deepEqual(composeHeadline('strandskydd', data, t, 'sv'), {
    tal: 'Inom strandskydd', under: 'zon 2281K-ÖVR-241 · uppförd 2014 · ingen preskription', badge: null
  });
});

test('composeHeadline strandskydd: vald_byggnad_id null faller tillbaka på traffar[0]', () => {
  const data = {
    vald_byggnad_id: null, antal_traffar: 1, antal_byggnader: 3,
    traffar: [{ byggnad_id: 'BAL-9', laege: 'delvis' }]
  };
  assert.equal(composeHeadline('strandskydd', data, t, 'sv').tal, 'Delvis inom strandskydd');
});

test('composeHeadline strandskydd: vald byggnad finns men är inte en träff -> Utanför strandskydd', () => {
  const data = {
    vald_byggnad_id: 'BAL-9', antal_traffar: 1, antal_byggnader: 3,
    traffar: [{ byggnad_id: 'BAL-1', laege: 'inom' }]
  };
  assert.deepEqual(composeHeadline('strandskydd', data, t, 'sv'),
    { tal: 'Utanför strandskydd', under: '', badge: null });
});

test('composeHeadline strandskydd: dispens krävs idag läggs till i underraden', () => {
  const data = {
    vald_byggnad_id: 'BAL-1', traffar: [
      { byggnad_id: 'BAL-1', laege: 'inom', dispens_kravs_idag: true }
    ]
  };
  assert.equal(composeHeadline('strandskydd', data, t, 'sv').under, 'dispens krävs idag');
});

test('composeHeadline: saknade fält ger Se underlag — aldrig ett friande påstående', () => {
  assert.deepEqual(composeHeadline('olovligt', {}, t, 'sv'), { tal: t.seUnderlag, under: '', badge: null });
  assert.deepEqual(composeHeadline('lovavvikelse', { lov_hittat: true }, t, 'sv'),
    { tal: t.seUnderlag, under: '', badge: null });
  assert.deepEqual(composeHeadline('strandskydd', {}, t, 'sv'), { tal: t.seUnderlag, under: '', badge: null });
});

test('composeHeadline: backendens meddelande vinner', () => {
  assert.deepEqual(composeHeadline('lovavvikelse',
    { lov_hittat: false, meddelande: 'Inget lov i arkivet' }, t, 'sv'),
  { tal: 'Inget lov i arkivet', under: '', badge: null });
});

/* --- underlagsLage: underlagsbeskrivning, aldrig ett utfall --- */

test('underlagsLage: status styr fel/inget/hamtar oavsett data', () => {
  assert.equal(underlagsLage('olovligt', { forsta_ar_med: 2007 }, { typ: 'fel' }), 'fel');
  assert.equal(underlagsLage('olovligt', null, { typ: 'info' }), 'inget');
  assert.equal(underlagsLage('olovligt', null, { typ: 'laddar' }), 'hamtar');
  assert.equal(underlagsLage('olovligt', null, null), 'hamtar');
});

test('underlagsLage olovligt: matningskritiskt eller saknad datering -> osakert', () => {
  assert.equal(underlagsLage('olovligt', { forsta_ar_med: 2007, matningskritiskt: true }, null), 'osakert');
  assert.equal(underlagsLage('olovligt', { forsta_ar_med: null }, null), 'osakert');
  assert.equal(underlagsLage('olovligt', { forsta_ar_med: 2007 }, null), 'finns');
});

test('underlagsLage lovavvikelse: icke-tom matningskritiska -> osakert', () => {
  assert.equal(underlagsLage('lovavvikelse', { matningskritiska: ['a'] }, null), 'osakert');
  assert.equal(underlagsLage('lovavvikelse', { matningskritiska: [] }, null), 'finns');
  assert.equal(underlagsLage('lovavvikelse', {}, null), 'finns');
});

test('underlagsLage strandskydd: vald träffens atgarder eller saknad datering -> osakert', () => {
  const medAtgard = { vald_byggnad_id: 'BAL-1', traffar: [{ byggnad_id: 'BAL-1', atgarder: ['x'] }] };
  assert.equal(underlagsLage('strandskydd', medAtgard, null), 'osakert');
  const utanDatering = { vald_byggnad_id: 'BAL-1', traffar: [{ byggnad_id: 'BAL-1', byggnads_ar: null }] };
  assert.equal(underlagsLage('strandskydd', utanDatering, null), 'osakert');
  const klart = { vald_byggnad_id: 'BAL-1', traffar: [{ byggnad_id: 'BAL-1', byggnads_ar: 2014, atgarder: [] }] };
  assert.equal(underlagsLage('strandskydd', klart, null), 'finns');
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

/* --- backendens meddelanden: {kod, params} översätts vid rendering --- */

const OSAKERHET = { kod: 'runner.lovarkiv_syntetiskt', params: {} };

test('renderCheckBody: osäkerheter som meddelandekod översätts till valt språk', () => {
  const data = { area_m2: 12, osakerheter: [OSAKERHET], kallor: [] };
  assert.match(renderCheckBody(data, TEXTS.sv, 'sv'), /SYNTETISKT testarkiv/);
  const en = renderCheckBody(data, TEXTS.en, 'en');
  assert.match(en, /SYNTHETIC test archive/);
  assert.doesNotMatch(en, /testarkiv/);
});

test('composeHeadline: meddelande som kod översätts, ren sträng passerar', () => {
  const data = { lov_hittat: false, meddelande: { kod: 'runner.inget_lov_i_arkivet', params: {} } };
  assert.match(composeHeadline('lovavvikelse', data, TEXTS.en, 'en').tal, /No case in the \(test\) archive/);
  assert.match(composeHeadline('lovavvikelse', data, TEXTS.sv, 'sv').tal, /Inget ärende i \(test\)arkivet/);
});

test('renderKallor: kod-beskrivning översätts, författningsnamn står kvar ordagrant', () => {
  const data = {
    area_m2: 12,
    osakerheter: [],
    kallor: [
      { beskrivning: { kod: 'kalla.ortofoto_tidslinje', params: {} }, url: 'https://example.se/a' },
      { beskrivning: 'Miljöbalken 7 kap. (SFS 1998:808)', url: 'https://example.se/b' }
    ]
  };
  const en = renderCheckBody(data, TEXTS.en, 'en');
  assert.match(en, /Orthophoto timeline 1960–2023 \(WMS\)/);
  assert.match(en, /Miljöbalken 7 kap\. \(SFS 1998:808\)/);
});

test('korsjamforelse: fältnamn får etikett och utfallet översätts — inga råa nycklar', () => {
  const data = {
    area_m2: 12, osakerheter: [], kallor: [],
    korsjamforelse: { dnr: 'överens', beslutsdatum: 'avviker', byggnadsarea_m2: 'saknas' }
  };
  const en = renderCheckBody(data, TEXTS.en, 'en');
  assert.match(en, /Case number/);
  assert.match(en, /Decision date/);
  assert.match(en, /Building area/);
  assert.match(en, /Matches/);
  assert.match(en, /Differs/);
  assert.match(en, /Missing from the document/);
  assert.doesNotMatch(en, /överens|avviker/);

  const sv = renderCheckBody(data, TEXTS.sv, 'sv');
  assert.match(sv, /Diarienummer/);
  assert.match(sv, /Beslutsdatum/);
});

test('träffarnas laege är en uppräkning, inte fritext', () => {
  const data = {
    antal_traffar: 1, antal_byggnader: 2, osakerheter: [], kallor: [],
    traffar: [{ byggnad_id: 'BAL-1', laege: 'inom', atgarder: [OSAKERHET] }]
  };
  const en = renderCheckBody(data, TEXTS.en, 'en');
  assert.match(en, /Inside zone/);
  assert.match(en, /SYNTHETIC test archive/);
  assert.doesNotMatch(en, />inom</);
});

test('traffar_trunkerade_till har en etikett — aldrig en rå nyckel i panelen', () => {
  const data = { traffar_trunkerade_till: 15, osakerheter: [], kallor: [] };
  assert.match(renderCheckBody(data, TEXTS.en, 'en'), /Hit list truncated to/);
  assert.match(renderCheckBody(data, TEXTS.sv, 'sv'), /Träfflistan trunkerad till/);
});

test('formatVarde: meddelandelista renderas som text, inte som JSON', () => {
  const html = formatVarde([OSAKERHET], TEXTS.en, 'en');
  assert.doesNotMatch(html, /\{|kod|params/);
  assert.match(html, /SYNTHETIC test archive/);
});

test('renderRattigheter: en rad per rättighet, identifierare ordagrant, inga = "inga"', async () => {
  const { renderRattigheter } = await import('../src/dossier.mjs');
  const html = renderRattigheter([
    { typ: 'Ledningsrätt', aktbeteckning: '2281-80/58', andamal: 'VATTEN OCH AVLOPP', fastighet: 'ALNÖ-VI 3:112' },
    { typ: 'Gemensamhetsanläggning', aktbeteckning: '2281K-F-50', andamal: 'SPILLVATTENLEDNING', fastighet: '' }
  ], t, 'sv');
  assert.match(html, /Ledningsrätt <b>2281-80\/58<\/b> — VATTEN OCH AVLOPP <span class="gt-rattighet__fast">\(ALNÖ-VI 3:112\)<\/span>/);
  assert.match(html, /Gemensamhetsanläggning <b>2281K-F-50<\/b> — SPILLVATTENLEDNING<\/li>/);
  assert.match(html, /Rättigheter och gemensamhetsanläggningar/);
  const en = renderRattigheter([{ typ: 'Ledningsrätt', aktbeteckning: 'X' }], TEXTS.en, 'en');
  assert.match(en, /Utility easement \(ledningsrätt\) <b>X<\/b>/);
  assert.match(renderRattigheter([], t, 'sv'), /inga/);
});

test('renderCheckBody: rattigheter och snedbilder renderas inte generiskt (JSON-dump)', () => {
  const data = { ...FALL3, rattigheter: [{ typ: 'Officialservitut', aktbeteckning: 'S-1' }],
    snedbilder: { tillganglig: true, riktningar: ['N'], ar: [2018], viewer_url: 'https://x' } };
  const html = renderCheckBody(data, t, 'sv');
  assert.ok(html.includes('Officialservitut <b>S-1</b>'));
  assert.ok(!html.includes('viewer_url'));
  assert.ok(!html.includes('"tillganglig"'));
});

test('renderCheckBody: rättigheter per fall 7-träff renderas som lista, inte JSON', () => {
  const data = {
    antal_traffar: 1, antal_byggnader: 2, osakerheter: [], kallor: [],
    traffar: [{
      byggnad_id: 'BAL-1', laege: 'inom',
      rattigheter: [{ typ: 'Officialservitut', aktbeteckning: '2281-91/12', andamal: 'VÄG', lager: 'Lantmateriet:rk_rattighet_y' }]
    }]
  };
  const html = renderCheckBody(data, TEXTS.sv, 'sv');
  assert.match(html, /gt-rattigheter/);
  assert.match(html, /2281-91\/12/);
  assert.match(html, /VÄG/);
  assert.doesNotMatch(html, /aktbeteckning&quot;/);
  assert.doesNotMatch(html, /\{&quot;typ/);
});

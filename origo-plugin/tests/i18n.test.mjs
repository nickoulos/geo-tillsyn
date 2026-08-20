import test from 'node:test';
import assert from 'node:assert/strict';
import {
  TEXTS, FALT_LABEL, MEDDELANDEN, VARDE_LABEL,
  faltLabel, formatTal, meddelandeText, teckenTal, vardeLabel
} from '../src/i18n.mjs';

test('sv och en har exakt samma nycklar', () => {
  assert.deepEqual(Object.keys(TEXTS.en).sort(), Object.keys(TEXTS.sv).sort());
  assert.deepEqual(Object.keys(FALT_LABEL.en).sort(), Object.keys(FALT_LABEL.sv).sort());
  assert.deepEqual(Object.keys(MEDDELANDEN.en).sort(), Object.keys(MEDDELANDEN.sv).sort());
  assert.deepEqual(Object.keys(VARDE_LABEL.en).sort(), Object.keys(VARDE_LABEL.sv).sort());
  for (const falt of Object.keys(VARDE_LABEL.sv)) {
    assert.deepEqual(
      Object.keys(VARDE_LABEL.en[falt]).sort(),
      Object.keys(VARDE_LABEL.sv[falt]).sort(),
      `värdena för ${falt} skiljer sig mellan språken`
    );
  }
});

test('varje meddelandekod renderar en icke-tom sträng på båda språken', () => {
  // Parametrarna nedan täcker varje kod som tar sådana; koder utan parametrar
  // klarar ett tomt objekt.
  const params = {
    'datering.argangar_utan_bild': { ar: [1998, 2002] },
    'datering.for_fa_argangar': { antal: 2, minst: 3 },
    'datering.argangar_utan_innehall': { ar: [2012] },
    'datering.otydliga_argangar': { ar: [2007, 2013] },
    'datering.syns_i_aldsta': { ar: 1960 },
    'juridik.byggnadsar_ar_ikrafttradandear': { ar: 1975, generellt_fran: '1975-07-01' },
    'juridik.matningskritisk_areaavvikelse': { diff_m2: 0.5, band_m2: 2.0 },
    'juridik.matningskritisk_avstand': { band_m: 0.5 },
    'lovtolk.ocr_ej_tillganglig': { feltyp: 'ImportError' },
    'lovtolk.lag_konfidens': { konfidens: 0.42 },
    'runner.regellager_otillgangligt': { lager: 'Lansstyrelsen:UtvidgatStrandskydd_yta' },
    'server.bbox_ogiltig': { detalj: 'x' },
    'radar.poang_delvis': { andel: 0.42 },
    'radar.poang_gallde_vid_uppforande': { ar: 2014 },
    'radar.poang_fore_strandskydd': { ar: 1960 },
    'radar.poang_ar_ikrafttradandear': { ar: 1975 },
    'radar.kallkonflikt_upphavt': { referens: '521-1234-2019 (2019-05-02)' },
    'radar.fastighetslager_otillgangligt': { lager: 'X:y' },
    'radar.zon_for_stor': { area_km2: 5.2, max_km2: 4.0 },
    'runner.strandskyddslager_otillgangligt': { lager: 'X:y' },
    'runner.granslager_otillgangligt': { lager: 'X:y' },
    'runner.upphavt_strandskydd_konflikt': { byggnad_id: 'bal_byggnad_yta.1', referens: '521-1234-2019 (2019-05-02)' },
    'runner.rattighetslager_otillgangligt': { lager: 'X:y' },
    'runner.hojd_granska_snedbilder': { ar: [2018, 2022] },
    'geodata.snapshot_anvant': { lager: 'X:y', hamtad: '2026-08-19T10:00:00Z' },
    'geodata.cache_anvant': { lager: 'X:y', hamtad: '2026-08-19T10:00:00Z' },
    'runner.lov_byggnad_koppling_osaker': { avstand_m: 12.4 },
    'runner.ingen_byggnad_hittad': { radie_m: 100, easting: 1, northing: 2 },
    'runner.inget_arende_matchar': { easting: 1, northing: 2 },
    'kalla.lovarkiv_syntetiskt': { dnr: 'SBN 2009-0412' },
    'kalla.skannad_handling': { dnr: 'SBN 2009-0412' },
    'server.parametrar_ogiltiga': { detalj: "'easting'" }
  };
  for (const sprak of ['sv', 'en']) {
    for (const kod of Object.keys(MEDDELANDEN.sv)) {
      const text = meddelandeText({ kod, params: params[kod] || {} }, sprak);
      assert.equal(typeof text, 'string');
      assert.ok(text.length > 0, `${kod} (${sprak}) gav tom text`);
      assert.ok(!text.includes('undefined'), `${kod} (${sprak}) lämnade undefined: ${text}`);
    }
  }
});

test('meddelandeText: ren sträng passerar ordagrant (författningsnamn, lagernamn)', () => {
  assert.equal(
    meddelandeText('Miljöbalken 7 kap. (SFS 1998:808)', 'en'),
    'Miljöbalken 7 kap. (SFS 1998:808)'
  );
  assert.equal(meddelandeText('SundsvallsKommun:bal_byggnad_yta (WFS)', 'en'),
    'SundsvallsKommun:bal_byggnad_yta (WFS)');
});

test('meddelandeText: okänd kod faller tillbaka på koden, aldrig på tomhet', () => {
  assert.equal(meddelandeText({ kod: 'inte.en.riktig.kod', params: {} }, 'en'),
    'inte.en.riktig.kod');
  assert.equal(meddelandeText(null, 'en'), '');
});

test('meddelandeText: tal följer språkets decimaltecken', () => {
  const m = { kod: 'juridik.matningskritisk_avstand', params: { band_m: 0.5 } };
  assert.match(meddelandeText(m, 'sv'), /±0,5 m/);
  assert.match(meddelandeText(m, 'en'), /±0\.5 m/);
});

test('meddelandeText översätter faktiskt — svenskan läcker inte in i engelskan', () => {
  const koder = [
    'datering.ingen_bortom_referensar',
    'juridik.strandskydd_preskriberas_aldrig',
    'runner.bygglovsregister_saknas',
    'runner.lovarkiv_syntetiskt'
  ];
  for (const kod of koder) {
    const en = meddelandeText({ kod, params: {} }, 'en');
    assert.notEqual(en, meddelandeText({ kod, params: {} }, 'sv'));
    // Svenska särtecken utanför författningsnamn förråder en oöversatt sträng.
    assert.ok(!/[åä]/.test(en.replace(/MÖD|ÄPBL|Miljöbalken/g, '')),
      `${kod} ser oöversatt ut på engelska: ${en}`);
  }
});

test('vardeLabel: uppräkningar översätts, okänt värde passerar oförändrat', () => {
  assert.equal(vardeLabel('laege', 'inom', 'en'), 'Inside zone');
  assert.equal(vardeLabel('laege', 'delvis', 'sv'), 'Delvis inom zon');
  assert.equal(vardeLabel('korsjamforelse', 'överens', 'en'), 'Matches');
  assert.equal(vardeLabel('korsjamforelse', 'avviker', 'en'), 'Differs');
  assert.equal(vardeLabel('laege', 'nytt_varde', 'en'), 'nytt_varde');
});

test('checkTitel finns för alla tre kontroller på båda språken', () => {
  for (const sprak of ['sv', 'en']) {
    for (const key of ['olovligt', 'lovavvikelse', 'strandskydd']) {
      assert.equal(typeof TEXTS[sprak].checkTitel[key], 'string');
      assert.equal(typeof TEXTS[sprak].checkUndertitel[key], 'string');
    }
  }
});

test('faltLabel: känd nyckel översätts, okänd faller tillbaka till nyckeln', () => {
  assert.equal(faltLabel('area_diff_m2', 'sv'), 'Areaavvikelse');
  assert.equal(faltLabel('area_diff_m2', 'en'), 'Area difference');
  assert.equal(faltLabel('helt_okand_nyckel', 'sv'), 'helt_okand_nyckel');
});

test('formatTal: svensk decimalkomma, engelsk punkt, max en decimal', () => {
  assert.equal(formatTal(90.3, 'sv'), '90,3');
  assert.equal(formatTal(90.3, 'en'), '90.3');
  assert.equal(formatTal(38.42, 'sv'), '38,4');
  assert.equal(formatTal(15, 'sv'), '15');
});

test('teckenTal: plus-prefix på positiva, minus följer med negativa', () => {
  assert.equal(teckenTal(90.3, 'sv'), '+90,3');
  assert.equal(teckenTal(-4.2, 'sv'), '-4,2');
  assert.equal(teckenTal(0, 'sv'), '0');
});

test('nya v0.7 Task 2-nycklar krockar inte med befintliga forstSynlig/ingenPreskription', () => {
  // forstSynlig är sedan tidigare en funktion (biografins gap-etikett);
  // ingenPreskription en sträng med MÖD-referens (biografins klocketikett).
  // Task 2 lägger nya, egna nycklar i stället för att skriva över dem.
  assert.equal(typeof TEXTS.sv.forstSynlig, 'function');
  assert.equal(TEXTS.sv.forstSynlig(1998, 2001), 'först synlig 1998–2001');
  assert.equal(TEXTS.sv.ingenPreskription, 'ingen preskription · MÖD 2021:6');
  assert.equal(typeof TEXTS.sv.forstSynligOrtofoto, 'string');
  assert.equal(TEXTS.sv.forstSynligOrtofoto, 'först synlig i ortofoto');
  assert.equal(TEXTS.en.forstSynligOrtofoto, 'first visible in orthophoto');
  assert.equal(TEXTS.sv.ingenPreskriptionKort, 'ingen preskription');
  assert.equal(TEXTS.en.ingenPreskriptionKort, 'no limitation period');
});

test('osakerheterChip/registretSager/zon/uppford/andraByggnader komponerar tal på båda språken', () => {
  assert.equal(TEXTS.sv.osakerheterChip(6), '6 osäkerheter');
  assert.equal(TEXTS.en.osakerheterChip(6), '6 uncertainties');
  assert.equal(TEXTS.sv.registretSager(2014), 'registret säger 2014');
  assert.equal(TEXTS.sv.zon('2281K-ÖVR-241'), 'zon 2281K-ÖVR-241');
  assert.equal(TEXTS.sv.uppford(2014), 'uppförd 2014');
  assert.equal(TEXTS.sv.andraByggnader(27), '27 andra byggnader inom 150 m berör zonen');
  assert.equal(TEXTS.en.andraByggnader(27), '27 other buildings within 150 m touch the zone');
});

test('rubrik-funktionerna komponerar neutrala rubriker', () => {
  const t = TEXTS.sv;
  assert.equal(t.rubrikOlovligt(1998, 2001), 'Uppförd 1998–2001 enligt ortofoto');
  assert.equal(t.rubrikOlovligtRegister(1999), 'nybyggnadsår 1999 i registret');
  assert.equal(t.rubrikAvvikelse('+90,3', '+38,4'), '+90,3 m² (+38,4 %) mot godkänt lov');
  assert.equal(t.rubrikStrandskydd(2, 5), '2 av 5 byggnader berör strandskyddszon');
});

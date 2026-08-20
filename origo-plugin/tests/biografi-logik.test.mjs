import test from 'node:test';
import assert from 'node:assert/strict';
import {
  skapaDoman, xSkala, arVidX, klassificeraAr, lagBand, lovbefrielseBand,
  strandskyddBand, registerGap, klockor
} from '../src/biografi-logik.mjs';

const REGLER = {
  pbl_versioner: [
    { namn: 'Byggnadslagen/byggnadsstadgan', sfs: '1947:385 / 1959:612', fran: '1948-01-01', till: '1987-06-30' },
    { namn: 'Äldre plan- och bygglagen (ÄPBL)', sfs: '1987:10', fran: '1987-07-01', till: '2011-05-01' },
    { namn: 'Plan- och bygglagen', sfs: '2010:900', fran: '2011-05-02', till: null }
  ],
  lovbefrielser: [
    { namn: 'friggebod', fran: '1979-07-01', till: '2007-12-31', max_kvm: 10 },
    { namn: 'friggebod', fran: '2008-01-01', till: '2025-11-30', max_kvm: 15 }
  ],
  strandskydd: { generellt_fran: '1975-07-01' },
  preskription: {
    pbl_tioarsregel: { ar: 10, lagrum: 'PBL 11 kap. 20 § 2 st' },
    byggsanktionsavgift: { ar: 5, lagrum: 'PBL 11 kap. 58 §' },
    strandskydd: { preskriberas: false }
  }
};

/* ---------- skapaDoman / xSkala ---------- */

test('skapaDoman: 1960 -> innevarande år + 1', () => {
  assert.deepEqual(skapaDoman(2026), { fran: 1960, till: 2027 });
});

test('xSkala: linjär, ändpunkterna landar på 0 och bredden', () => {
  const skala = xSkala({ fran: 1960, till: 2020 }, 1000);
  assert.equal(skala(1960), 0);
  assert.equal(skala(2020), 1000);
  assert.equal(skala(1990), 500);
});

test('xSkala: bara år tolkas som 1 januari (samma som ISO-datumet)', () => {
  const skala = xSkala({ fran: 2000, till: 2001 }, 1000);
  assert.equal(skala(2000), skala('2000-01-01'));
});

test('xSkala: ISO-datum mitt i året hamnar mellan årets ändpunkter', () => {
  const skala = xSkala({ fran: 2000, till: 2002 }, 1000);
  const midjuli = skala('2000-07-02');
  assert.ok(midjuli > skala('2000-01-01') && midjuli < skala('2001-01-01'));
});

test('arVidX: inversen av xSkala — pixel 0/bredd landar på fran/till', () => {
  const doman = { fran: 1960, till: 2020 };
  assert.equal(arVidX(doman, 1000, 0), 1960);
  assert.equal(arVidX(doman, 1000, 1000), 2020);
  assert.equal(arVidX(doman, 1000, 500), 1990);
});

test('arVidX och xSkala är varandras inverser', () => {
  const doman = { fran: 1960, till: 2027 };
  const skala = xSkala(doman, 1600);
  for (const x of [0, 137, 800, 1599]) {
    assert.ok(Math.abs(skala(arVidX(doman, 1600, x)) - x) < 1e-9);
  }
});

/* ---------- klassificeraAr ---------- */

test('klassificeraAr: null-data -> alla år okänd', () => {
  const map = klassificeraAr(null, [2007, 2010]);
  assert.equal(map.get(2007), 'okand');
  assert.equal(map.get(2010), 'okand');
  assert.equal(map.size, 2);
});

test('klassificeraAr: narvaro_per_ar + uteslutna_ar, saknad nyckel -> okand', () => {
  const olovligt = {
    narvaro_per_ar: { 2007: 'narvaro', 2010: 'franvaro', 2021: 'otydlig' },
    uteslutna_ar: [1998]
  };
  const map = klassificeraAr(olovligt, [1998, 2007, 2010, 2021, 2020]);
  assert.equal(map.get(1998), 'utesluten');
  assert.equal(map.get(2007), 'narvaro');
  assert.equal(map.get(2010), 'franvaro');
  assert.equal(map.get(2021), 'otydlig');
  assert.equal(map.get(2020), 'okand');
});

test('klassificeraAr: uteslutna_ar tar företräde framför narvaro_per_ar', () => {
  const olovligt = { narvaro_per_ar: { 1998: 'narvaro' }, uteslutna_ar: [1998] };
  const map = klassificeraAr(olovligt, [1998]);
  assert.equal(map.get(1998), 'utesluten');
});

/* ---------- lagBand / lovbefrielseBand / strandskyddBand ---------- */

test('lagBand: en post per pbl-version, till null för öppen slutpunkt', () => {
  const band = lagBand(REGLER);
  assert.equal(band.length, 3);
  assert.deepEqual(band[0], { namn: 'Byggnadslagen/byggnadsstadgan', sfs: '1947:385 / 1959:612', fran: '1948-01-01', till: '1987-06-30' });
  assert.equal(band[2].till, null);
});

test('lovbefrielseBand: en post per lovbefrielse-post', () => {
  const band = lovbefrielseBand(REGLER);
  assert.equal(band.length, 2);
  assert.deepEqual(band[0], { namn: 'friggebod', max_kvm: 10, fran: '1979-07-01', till: '2007-12-31' });
});

test('strandskyddBand: fran = generellt_fran', () => {
  assert.deepEqual(strandskyddBand(REGLER), { fran: '1975-07-01' });
});

/* ---------- registerGap ---------- */

test('registerGap: null-data -> null', () => {
  assert.equal(registerGap(null), null);
});

test('registerGap: bal_forenligt true -> null (ingen gap ritas)', () => {
  const gap = registerGap({ bal_forenligt: true, forsta_ar_med: 2007, bal_nybyggnadsar: 2014 });
  assert.equal(gap, null);
});

test('registerGap: bal_forenligt false -> gap med avviker=true', () => {
  const gap = registerGap({ bal_forenligt: false, forsta_ar_med: 2007, bal_nybyggnadsar: 2014 });
  assert.deepEqual(gap, { fran: 2007, till: 2014, avviker: true });
});

test('registerGap: bal_forenligt false men saknar datering -> null', () => {
  assert.equal(registerGap({ bal_forenligt: false, forsta_ar_med: null, bal_nybyggnadsar: 2014 }), null);
});

/* ---------- klockor ---------- */

test('klockor: null-data -> tom lista', () => {
  assert.deepEqual(klockor(null, null, REGLER), []);
});

test('klockor: ingen datering (forsta_ar_med saknas) -> tom lista', () => {
  assert.deepEqual(klockor({ forsta_ar_med: null }, null, REGLER), []);
});

test('klockor: rättelse + sanktion utan strandskydd', () => {
  const olovligt = {
    forsta_ar_med: 2007, sista_ar_utan: 2001,
    rattelse_preskriberad: true, sanktionsavgift_mojlig: false
  };
  const k = klockor(olovligt, null, REGLER);
  assert.equal(k.length, 2);
  const rattelse = k.find((x) => x.nyckel === 'rattelse');
  assert.deepEqual(rattelse, {
    nyckel: 'rattelse', startSaker: 2007, startOsaker: 2001,
    slutSaker: 2017, slutOsaker: 2011, oandlig: false,
    ar: 10, lagrum: 'PBL 11 kap. 20 § 2 st', status: true
  });
  // sanktionsavgift_mojlig: false betyder att femårsfönstret är förbrukat
  // (utgången) — omvänd polaritet mot rattelse_preskriberad, normaliserad i
  // klockor() till samma "true = utgången"-tecken. Se dedikerade
  // polaritetstester nedan.
  const sanktion = k.find((x) => x.nyckel === 'sanktion');
  assert.deepEqual(sanktion, {
    nyckel: 'sanktion', startSaker: 2007, startOsaker: 2001,
    slutSaker: 2012, slutOsaker: 2006, oandlig: false,
    ar: 5, lagrum: 'PBL 11 kap. 58 §', status: true
  });
});

/* ---------- klockor: sanktionsklockans polaritet ----------
 * sanktionsavgift_mojlig är omvänt mot rattelse_preskriberad: true betyder
 * att avgiften fortfarande KAN tas ut (klockan löper), false att fönstret är
 * förbrukat (utgången). klockor() normaliserar sanktion-status till samma
 * "true = utgången" tecken som rattelse, så den delade render-mappningen i
 * biografi.js (status===true -> "utgången", status===false -> "löper till")
 * ger rätt etikett för båda klockorna. */

test('klockor: polaritet — rattelse_preskriberad true -> status true (utgången)', () => {
  const olovligt = { forsta_ar_med: 2007, rattelse_preskriberad: true, sanktionsavgift_mojlig: null };
  const k = klockor(olovligt, null, REGLER);
  assert.equal(k.find((x) => x.nyckel === 'rattelse').status, true);
});

test('klockor: polaritet — sanktionsavgift_mojlig false -> status true (utgången)', () => {
  const olovligt = { forsta_ar_med: 2007, rattelse_preskriberad: null, sanktionsavgift_mojlig: false };
  const k = klockor(olovligt, null, REGLER);
  assert.equal(k.find((x) => x.nyckel === 'sanktion').status, true);
});

test('klockor: polaritet — sanktionsavgift_mojlig true -> status false (löper)', () => {
  const olovligt = { forsta_ar_med: 2007, rattelse_preskriberad: null, sanktionsavgift_mojlig: true };
  const k = klockor(olovligt, null, REGLER);
  assert.equal(k.find((x) => x.nyckel === 'sanktion').status, false);
});

test('klockor: polaritet — sanktionsavgift_mojlig null -> status null (bevaras)', () => {
  const olovligt = { forsta_ar_med: 2007, rattelse_preskriberad: null, sanktionsavgift_mojlig: null };
  const k = klockor(olovligt, null, REGLER);
  assert.equal(k.find((x) => x.nyckel === 'sanktion').status, null);
});

test('klockor: status null (backend har inte beräknat) bevaras som null', () => {
  const olovligt = { forsta_ar_med: 2007, sista_ar_utan: null, rattelse_preskriberad: null, sanktionsavgift_mojlig: null };
  const k = klockor(olovligt, null, REGLER);
  assert.equal(k[0].status, null);
  assert.equal(k[0].startOsaker, 2007); // ingen osäkerhet -> samma som startSaker
});

test('klockor: strandskydd-klocka tillkommer när träffen inte är utanför', () => {
  const olovligt = { forsta_ar_med: 2007, sista_ar_utan: 2001, rattelse_preskriberad: true, sanktionsavgift_mojlig: false };
  const traff = { laege: 'inom', preskriberas: false };
  const k = klockor(olovligt, traff, REGLER);
  assert.equal(k.length, 3);
  const ss = k.find((x) => x.nyckel === 'strandskydd');
  assert.deepEqual(ss, {
    nyckel: 'strandskydd', startSaker: 2007, startOsaker: 2001,
    slutSaker: null, slutOsaker: null, oandlig: true,
    ar: null, lagrum: null, status: false
  });
});

test('klockor: ingen strandskydd-klocka när träffens läge är utanför', () => {
  const olovligt = { forsta_ar_med: 2007, sista_ar_utan: 2001, rattelse_preskriberad: true, sanktionsavgift_mojlig: false };
  const traff = { laege: 'utanfor', preskriberas: false };
  const k = klockor(olovligt, traff, REGLER);
  assert.equal(k.some((x) => x.nyckel === 'strandskydd'), false);
});

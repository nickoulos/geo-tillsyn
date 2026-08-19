/**
 * Ren logik för fastighetsbiografin: en gemensam x-axel (1960 -> innevarande
 * år + 1) och fyra spårs data — Verklighet (ortofotoårgångarnas närvaro),
 * Register & lov (BAL-registret mot dateringsintervallet), Rättighet
 * (lagregim/lovbefrielser/strandskydd från regler.json) och Klockor
 * (preskriptionsfönstren från dateringsintervallets slut).
 *
 * Neutralitetsregel: den här modulen räknar bara *var* något ritas (datum +
 * antal år från regler.json) — den avgör aldrig *om* något gäller. Alla
 * utfallsetiketter (preskriberad, avviker, ...) kommer verbatim från
 * backend-fält och skickas igenom oförändrade.
 */

// Bara år tolkas som 1 januari det året — dokumenterat kontrakt för xSkala.
function fractionalYear(isoDateOrYear) {
  if (typeof isoDateOrYear === 'number') return isoDateOrYear;
  const parts = String(isoDateOrYear).split('-');
  const year = Number(parts[0]);
  const month = Number(parts[1] || '1');
  const day = Number(parts[2] || '1');
  const startOfYear = Date.UTC(year, 0, 1);
  const startOfNextYear = Date.UTC(year + 1, 0, 1);
  const current = Date.UTC(year, month - 1, day);
  const daysInYear = (startOfNextYear - startOfYear) / 86400000;
  return year + (current - startOfYear) / 86400000 / daysInYear;
}

export function skapaDoman(idagAr) {
  return { fran: 1960, till: idagAr + 1 };
}

export function xSkala(doman, bredd) {
  const { fran, till } = doman;
  const spann = till - fran;
  return (isoDateOrYear) => {
    if (spann === 0) return 0;
    return ((fractionalYear(isoDateOrYear) - fran) / spann) * bredd;
  };
}

// Inversen av xSkala: pixel -> år (fractional) — driver klick/drag-snappning
// på axeln (narmasteAr(years, arVidX(...)) i biografi.js).
export function arVidX(doman, bredd, x) {
  const { fran, till } = doman;
  if (bredd === 0) return fran;
  return fran + (x / bredd) * (till - fran);
}

const NARVARO_VARDEN = new Set(['narvaro', 'franvaro', 'otydlig']);

export function klassificeraAr(olovligt, years) {
  const narvaroPerAr = (olovligt && olovligt.narvaro_per_ar) || null;
  const uteslutna = new Set((olovligt && olovligt.uteslutna_ar) || []);
  const map = new Map();
  years.forEach((year) => {
    if (uteslutna.has(year)) {
      map.set(year, 'utesluten');
      return;
    }
    const varde = narvaroPerAr ? narvaroPerAr[String(year)] : undefined;
    map.set(year, NARVARO_VARDEN.has(varde) ? varde : 'okand');
  });
  return map;
}

export function lagBand(regler) {
  return (regler.pbl_versioner || []).map((v) => ({
    namn: v.namn, sfs: v.sfs, fran: v.fran, till: v.till || null
  }));
}

export function lovbefrielseBand(regler) {
  return (regler.lovbefrielser || []).map((b) => ({
    namn: b.namn, max_kvm: b.max_kvm, fran: b.fran, till: b.till || null
  }));
}

export function strandskyddBand(regler) {
  return { fran: regler.strandskydd.generellt_fran };
}

// Gapet ritas bara när backend uttryckligen flaggat avvikelse — se
// neutralitetsregeln överst i filen: bal_forenligt === true (eller saknas)
// betyder "ingen gap", inte "gap men grönt".
export function registerGap(olovligt) {
  if (!olovligt) return null;
  if (olovligt.bal_forenligt !== false) return null;
  if (olovligt.forsta_ar_med == null || olovligt.bal_nybyggnadsar == null) return null;
  return { fran: olovligt.forsta_ar_med, till: olovligt.bal_nybyggnadsar, avviker: true };
}

function klocka(nyckel, startSaker, startOsaker, ar, lagrum, oandlig, status) {
  return {
    nyckel,
    startSaker,
    startOsaker,
    slutSaker: oandlig ? null : startSaker + ar,
    slutOsaker: oandlig ? null : startOsaker + ar,
    oandlig,
    ar: oandlig ? null : ar,
    lagrum: oandlig ? null : lagrum,
    status: status === undefined ? null : status
  };
}

export function klockor(olovligt, strandskyddTraff, regler) {
  if (!olovligt || olovligt.forsta_ar_med == null) return [];
  const startSaker = olovligt.forsta_ar_med;
  const startOsaker = olovligt.sista_ar_utan != null ? olovligt.sista_ar_utan : startSaker;
  const tioar = regler.preskription.pbl_tioarsregel;
  const femar = regler.preskription.byggsanktionsavgift;

  const resultat = [
    klocka('rattelse', startSaker, startOsaker, tioar.ar, tioar.lagrum, false, olovligt.rattelse_preskriberad),
    klocka('sanktion', startSaker, startOsaker, femar.ar, femar.lagrum, false, olovligt.sanktionsavgift_mojlig)
  ];

  if (strandskyddTraff && strandskyddTraff.laege !== 'utanfor') {
    resultat.push(klocka('strandskydd', startSaker, startOsaker, null, null, true, strandskyddTraff.preskriberas));
  }

  return resultat;
}

/**
 * Fastighetsbiografin: den nedre biografistripen som ersätter tidslinjepillen
 * (src/timeline.js, borttagen). En SVG med fyra spår över en gemensam
 * x-axel (1960 -> innevarande år + 1): Verklighet (ortofotohistorik),
 * Register & lov (BAL-registret mot dateringsintervallet), Rättighet
 * (lagregim/lovbefrielser/strandskydd ur regler.json) och Klockor
 * (preskriptionsfönstren). Cursor-strecket = valt år; ‹ ›, klick/drag på
 * axeln och klick på en Verklighet-punkt flyttar det.
 *
 * Rent DOM- och tillståndslager: all datering/klassificering kommer från
 * biografi-logik.mjs (ren, testad). Ingen egen juridik ritas här — statusar
 * (preskriberad, avviker, ...) kommer verbatim från backend-fält; klockornas
 * årtal/lagrum kommer från regler.json, aldrig hårdkodade i UI-texten.
 *
 * Spåren är fasta pixelhöjder (inte proportionella andelar) — stripen är en
 * projektorkomponent, och varje spårs innehåll (upp till tre klockstaplar,
 * tre rättighetsrader, dubbla etiketter i Register & lov) har en egen
 * platskrävande layout som en jämn fjärdedelning inte skulle rymma.
 */

import { stegAr, narmasteAr } from './tidslinje-logik.mjs';
import {
  skapaDoman, xSkala, arVidX, klassificeraAr, lagBand, lovbefrielseBand,
  strandskyddBand, registerGap, klockor
} from './biografi-logik.mjs';
import { formatTal } from './i18n.mjs';

const SVG_NS = 'http://www.w3.org/2000/svg';

// Spårens höjder (px) — Klockor och Rättighet är störst eftersom de kan
// behöva rita flest samtidiga element (tre klockstaplar; tre rättighetsrader).
const LANE_H = [56, 44, 72, 58]; // Verklighet, Register & lov, Rättighet, Klockor
const KROPP_H = LANE_H.reduce((a, b) => a + b, 0); // 230
const LANE_TOP = [];
(() => {
  let cursor = 0;
  for (const h of LANE_H) { LANE_TOP.push(cursor); cursor += h; }
})();

const AXEL_H = 14; // egen smal remsa under spåren, inte inräknad i LANE_H
const H = KROPP_H + AXEL_H; // SVG-höjd (kroppen, inkl. axel)
const KONTROLLRAD_H = 40; // ‹ › år Regelverk-knapp kollaps — separat rad under SVG:n
const TOTAL_H = H + KONTROLLRAD_H;
const KOLLAPSAD_H = 40;

const CHEVRON = '<svg class="gt-chevron" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M6 9l6 6 6-6"/></svg>';

function el(tag, attrs = {}, ns = SVG_NS) {
  const node = document.createElementNS(ns, tag);
  Object.entries(attrs).forEach(([k, v]) => {
    if (v !== null && v !== undefined) node.setAttribute(k, v);
  });
  return node;
}

function titel(text) {
  const t = el('title');
  t.textContent = text;
  return t;
}

function within(fran, till, isoDate) {
  return fran <= isoDate && (!till || isoDate <= till);
}

// Grov textbreddsuppskattning (inget canvas-mätning i SVG) — tillräckligt
// träffsäker för att avgöra inuti/efter/klampning; aldrig pixelexakt.
function textbredd(text, storlek) {
  return text.length * (storlek || 9.5) * 0.56;
}

function skrivText(lager, text, x, y, cls, ankare) {
  const t = el('text', { x, y, class: cls, 'text-anchor': ankare || 'start' });
  t.textContent = text;
  lager.appendChild(t);
  return t;
}

// En etikett som hör till ett band/en stapel [xStart,xEnd]: ligger inuti om
// den får plats där, annars direkt efter — och klampas mot högerkanten så
// den aldrig sticker ut ur SVG:n (V2: ingen text får överlappa en annan).
function etikettForBand(lager, text, xStart, xEnd, y, cls, bredd, storlek) {
  const bandBredd = xEnd - xStart;
  const tb = textbredd(text, storlek);
  if (bandBredd >= tb + 8) {
    skrivText(lager, text, xStart + 6, y, `${cls} gt-bio-etikett--inuti`, 'start');
    return;
  }
  let x = xEnd + 4;
  let ankare = 'start';
  if (x + tb > bredd - 2) { x = bredd - 2; ankare = 'end'; }
  skrivText(lager, text, x, y, cls, ankare);
}

// Klockornas etikett: till höger om stapelns slut om det får plats, annars
// innanför stapeln (ankare vid slutet), annars före stapelns start.
function etikettForKlocka(lager, text, xBarStart, xBarEnd, y, cls, bredd, storlek) {
  const tb = textbredd(text, storlek);
  if (xBarEnd + 4 + tb <= bredd - 2) {
    skrivText(lager, text, xBarEnd + 4, y, cls, 'start');
    return;
  }
  if (xBarEnd - xBarStart >= tb + 8) {
    skrivText(lager, text, xBarEnd - 4, y, `${cls} gt-bio-etikett--inuti`, 'end');
    return;
  }
  skrivText(lager, text, Math.max(2, xBarStart - 4), y, cls, 'end');
}

// En centrerad etikett (markörer i Verklighet/Register) — klampas mot
// kanterna i stället för att sticka ut.
function etikettCentrerad(lager, text, x, y, cls, bredd, storlek) {
  const tb = textbredd(text, storlek);
  let ankare = 'middle';
  let px = x;
  if (x - tb / 2 < 2) { ankare = 'start'; px = 2; }
  else if (x + tb / 2 > bredd - 2) { ankare = 'end'; px = bredd - 2; }
  skrivText(lager, text, px, y, cls, ankare);
}

export function skapaBiografi({ years, startAr, regler, t, sprak, onArByte, onRegelverk }) {
  let texts = t;
  let aktivSprak = sprak;
  let cursorAr = years.includes(startAr) ? startAr : years[years.length - 1];
  let kollapsad = false;
  let data = { olovligt: null, lovavvikelse: null, strandskyddTraff: null };
  let bredd = 0;
  const idagAr = new Date().getFullYear();
  const domain = skapaDoman(idagAr);

  const root = document.createElement('div');
  root.className = 'gt-biografi';
  root.setAttribute('role', 'group');
  root.innerHTML = '\
    <div class="gt-biografi__kropp">\
      <div class="gt-biografi__etiketter">\
        <span class="gt-biografi__etikett"></span>\
        <span class="gt-biografi__etikett"></span>\
        <span class="gt-biografi__etikett"></span>\
        <span class="gt-biografi__etikett"></span>\
      </div>\
      <div class="gt-biografi__svgwrap">\
        <svg class="gt-biografi__svg" xmlns="' + SVG_NS + '"></svg>\
        <div class="gt-biografi__regelpop" hidden></div>\
      </div>\
    </div>\
    <div class="gt-biografi__rad">\
      <button class="gt-knapp gt-knapp--ikon" type="button" data-riktning="-1">‹</button>\
      <span class="gt-biografi__ar"></span>\
      <button class="gt-knapp gt-knapp--ikon" type="button" data-riktning="1">›</button>\
      <button class="gt-knapp gt-biografi__regelknapp" type="button"></button>\
      <button class="gt-knapp gt-knapp--ikon gt-biografi__kollaps" type="button" aria-expanded="true">' + CHEVRON + '</button>\
    </div>';

  const svg = root.querySelector('.gt-biografi__svg');
  const svgwrap = root.querySelector('.gt-biografi__svgwrap');
  const popover = root.querySelector('.gt-biografi__regelpop');
  const arEl = root.querySelector('.gt-biografi__ar');
  const regelKnapp = root.querySelector('.gt-biografi__regelknapp');
  const kollapsKnapp = root.querySelector('.gt-biografi__kollaps');
  const etikettEls = root.querySelectorAll('.gt-biografi__etikett');
  etikettEls.forEach((etikettEl, i) => {
    etikettEl.style.flex = 'none';
    etikettEl.style.height = `${LANE_H[i]}px`;
  });

  function velj(ar) {
    if (ar === cursorAr) return;
    cursorAr = ar;
    render();
    onArByte(ar);
    if (!popover.hidden) onRegelverk(cursorAr);
  }

  /* ---------- axel: klick/drag snappar till närmaste ortofotoårgång ---------- */

  const axisHit = el('rect', { class: 'gt-bio-axishit', fill: 'transparent' });
  let drar = false;
  function arFranPekare(evt) {
    const rect = svg.getBoundingClientRect();
    const skalfaktor = rect.width ? bredd / rect.width : 1;
    const x = (evt.clientX - rect.left) * skalfaktor;
    return narmasteAr(years, arVidX(domain, bredd, x));
  }
  axisHit.addEventListener('pointerdown', (evt) => {
    drar = true;
    try { axisHit.setPointerCapture(evt.pointerId); } catch (err) { /* jsdom/headless saknar ibland stöd */ }
    velj(arFranPekare(evt));
  });
  axisHit.addEventListener('pointermove', (evt) => {
    if (!drar) return;
    velj(arFranPekare(evt));
  });
  function slappDrag(evt) {
    drar = false;
    try { axisHit.releasePointerCapture(evt.pointerId); } catch (err) { /* se ovan */ }
  }
  axisHit.addEventListener('pointerup', slappDrag);
  axisHit.addEventListener('pointercancel', slappDrag);

  /* ---------- Spår 1: Verklighet ---------- */

  function ritaVerklighet(lager, skala) {
    const laneTop = LANE_TOP[0];
    const yDot = laneTop + 14;
    const klasser = klassificeraAr(data.olovligt, years);
    const poang = (data.olovligt && data.olovligt.poang_per_ar) || {};

    years.forEach((year) => {
      const status = klasser.get(year);
      const x = skala(year);
      const cirkel = el('circle', { cx: x, cy: yDot, r: 6, class: `gt-bio-punkt gt-bio-punkt--${status}` });
      const p = poang[String(year)];
      cirkel.appendChild(titel(p !== undefined ? `${year}: ${formatTal(p, aktivSprak)}` : String(year)));
      cirkel.style.cursor = 'pointer';
      cirkel.addEventListener('click', () => velj(year));
      lager.appendChild(cirkel);
    });

    const { olovligt } = data;
    if (olovligt && olovligt.sista_ar_utan != null && olovligt.forsta_ar_med != null) {
      const x1 = skala(olovligt.sista_ar_utan);
      const x2 = skala(olovligt.forsta_ar_med);
      // Klammern ritas UNDER punktraden (inte ovanför — V3) så den alltid
      // ligger inom spårets 56 px, oavsett SVG:ns överkant.
      const yBrace = laneTop + 34;
      const brace = el('g', { class: 'gt-bio-klammer' });
      brace.appendChild(el('line', { x1, x2, y1: yBrace, y2: yBrace }));
      brace.appendChild(el('line', { x1, x2: x1, y1: yBrace - 3, y2: yBrace + 3 }));
      brace.appendChild(el('line', { x1: x2, x2, y1: yBrace - 3, y2: yBrace + 3 }));
      lager.appendChild(brace);
      const label = texts.forstSynlig(olovligt.sista_ar_utan, olovligt.forsta_ar_med);
      etikettCentrerad(lager, label, (x1 + x2) / 2, yBrace + 13, 'gt-bio-etikett', bredd);
    }
  }

  /* ---------- Spår 2: Register & lov ---------- */

  function ritaRegister(lager, skala) {
    const laneTop = LANE_TOP[1];
    const yC = laneTop + LANE_H[1] / 2;
    const { olovligt, lovavvikelse } = data;
    const gap = registerGap(olovligt);
    if (gap) {
      const x1 = skala(gap.fran);
      const x2 = skala(gap.till);
      lager.appendChild(el('line', { x1, x2, y1: yC, y2: yC, class: 'gt-bio-gap' }));
    }
    if (olovligt && olovligt.bal_nybyggnadsar != null) {
      const x = skala(olovligt.bal_nybyggnadsar);
      const s = 5;
      const romb = el('path', {
        d: `M ${x} ${yC - s} L ${x + s} ${yC} L ${x} ${yC + s} L ${x - s} ${yC} Z`,
        class: 'gt-bio-romb'
      });
      // Avvikelsen vävs in i registeretiketten (i stället för en separat
      // "avviker"-badge) — V2: en sammanslagen etikett kan aldrig kollidera
      // med sig själv.
      let etikett = texts.registerEtikett(olovligt.bal_nybyggnadsar);
      if (gap) etikett += ` · ${texts.avvikerBadge}`;
      romb.appendChild(titel(etikett));
      lager.appendChild(romb);
      // Register-etiketten OVANFÖR markören (V4).
      etikettCentrerad(lager, etikett, x, laneTop + 10, 'gt-bio-etikett', bredd);
    }
    if (lovavvikelse && lovavvikelse.beslutsdatum) {
      const x = skala(lovavvikelse.beslutsdatum);
      const ikon = el('rect', { x: x - 4, y: yC - 5, width: 8, height: 10, class: 'gt-bio-dokument' });
      const etikett = texts.lovEtikett(lovavvikelse.dnr || '');
      ikon.appendChild(titel(etikett));
      lager.appendChild(ikon);
      // Lov-etiketten UNDER sin markör (V4) — kolliderar aldrig med
      // registeretiketten som alltid ligger ovanför.
      etikettCentrerad(lager, etikett, x, laneTop + 40, 'gt-bio-etikett', bredd);
    }
  }

  /* ---------- Spår 3: Rättighet ---------- */

  function ritaRattighet(lager, skala) {
    if (!regler) return; // regler.json kunde inte hämtas — spåret lämnas tomt, inte trasigt
    const laneTop = LANE_TOP[2];
    const isoCursor = `${cursorAr}-07-01`;
    const radLag = { top: laneTop + 4, h: 18 };
    const radLov = { top: laneTop + 26, h: 14 };
    const radSs = { top: laneTop + 48, h: 12 };

    lagBand(regler).forEach((band) => {
      const x1 = skala(band.fran);
      const x2 = band.till ? skala(band.till) : bredd;
      const aktiv = within(band.fran, band.till, isoCursor);
      const rect = el('rect', {
        x: x1, y: radLag.top, width: Math.max(0, x2 - x1), height: radLag.h,
        class: `gt-bio-lagband${aktiv ? ' gt-bio-lagband--aktiv' : ''}`
      });
      rect.appendChild(titel(`${band.namn} (${band.sfs})`));
      lager.appendChild(rect);
      etikettForBand(lager, band.namn, x1, x2, radLag.top + radLag.h / 2 + 4,
        'gt-bio-etikett gt-bio-etikett--band', bredd, 11);
    });

    lovbefrielseBand(regler).forEach((b) => {
      const x1 = skala(b.fran);
      const x2 = b.till ? skala(b.till) : bredd;
      const rect = el('rect', {
        x: x1, y: radLov.top, width: Math.max(0, x2 - x1), height: radLov.h, class: 'gt-bio-lovbefrielse'
      });
      const etikett = `${b.namn} ${b.max_kvm} m²`;
      rect.appendChild(titel(etikett));
      lager.appendChild(rect);
      // Text bara om den faktiskt får plats i den egna stapeln — annars
      // räcker title (V5). Ett fast 60 px-tak (utan hänsyn till textens
      // egen bredd) lät långa etiketter ("attefallshus 30 m²") svämma över
      // i grannstapeln vid smalare fönster; måttet görs därför dynamiskt.
      if (x2 - x1 >= textbredd(etikett, 10.5) + 10) {
        skrivText(lager, etikett, x1 + 4, radLov.top + radLov.h - 4,
          'gt-bio-etikett gt-bio-etikett--lov gt-bio-etikett--inuti', 'start');
      }
    });

    const ss = strandskyddBand(regler);
    const xSs = skala(ss.fran);
    const ssRect = el('rect', {
      x: xSs, y: radSs.top, width: Math.max(0, bredd - xSs), height: radSs.h, class: 'gt-bio-strandskydd'
    });
    const ssAr = ss.fran.slice(0, 4);
    const ssEtikett = `${texts.strandskydd} (${ssAr}–)`;
    ssRect.appendChild(titel(ssEtikett));
    lager.appendChild(ssRect);
    skrivText(lager, ssEtikett, xSs + 4, radSs.top + radSs.h - 3,
      'gt-bio-etikett gt-bio-etikett--band gt-bio-etikett--inuti', 'start');
  }

  /* ---------- Spår 4: Klockor ---------- */

  function ritaKlockor(lager, skala) {
    if (!regler) return; // regler.json kunde inte hämtas — inga preskriptionsår att räkna ut
    const laneTop = LANE_TOP[3];
    const rader = klockor(data.olovligt, data.strandskyddTraff, regler);
    const NAMN = { rattelse: texts.rattelse, sanktion: texts.sanktion, strandskydd: texts.strandskydd };
    const radH = 18;
    const barH = 8;

    rader.forEach((k, i) => {
      const rowTop = laneTop + 2 + i * radH;
      const y = rowTop + radH / 2 + 1; // stapelns mittlinje
      const barTop = y - barH / 2;
      const xStartSaker = skala(k.startSaker);
      const xStartOsaker = skala(k.startOsaker);
      const xSlutSaker = k.oandlig ? bredd : skala(k.slutSaker);
      const xSlutOsaker = k.oandlig ? bredd : skala(k.slutOsaker);

      function stapel(x1, x2, osaker) {
        if (x2 <= x1) return;
        lager.appendChild(el('rect', {
          x: x1, y: barTop, width: x2 - x1, height: barH,
          class: `gt-bio-klockstapel${osaker ? ' gt-bio-klockstapel--osaker' : ''}`
        }));
      }
      stapel(xStartOsaker, xStartSaker, true);
      stapel(xStartSaker, xSlutOsaker, false);
      if (!k.oandlig) stapel(xSlutOsaker, xSlutSaker, true);

      if (k.oandlig) {
        lager.appendChild(el('path', {
          d: `M ${bredd - 8} ${y - 5} L ${bredd} ${y} L ${bredd - 8} ${y + 5} Z`,
          class: 'gt-bio-pil'
        }));
      }

      let etikett = NAMN[k.nyckel] || k.nyckel;
      if (k.nyckel === 'strandskydd') {
        if (k.status === false) etikett = `${NAMN.strandskydd} · ${texts.ingenPreskription}`;
      } else {
        // Namn + antal år + lagrum kommer alla från regler.json — stripen
        // hårdkodar aldrig "10 år"/"5 år" i UI-texten (endast ordet "år").
        etikett = `${NAMN[k.nyckel]} ${k.ar} ${texts.radarAr} · ${k.lagrum}`;
        if (k.status === true) etikett += ` · ${texts.utgangen(k.slutSaker)}`;
        else if (k.status === false) etikett += ` · ${texts.loperTill(k.slutSaker)}`;
      }
      // Etikett ovanför den egna stapeln — 18 px radhöjd räcker för bägge
      // utan att kliva in i nästa klockas rad (V2/V6).
      etikettForKlocka(lager, etikett, xStartOsaker, xSlutSaker, rowTop + 9, 'gt-bio-etikett', bredd);
    });
  }

  /* ---------- axel + cursor + idag ---------- */

  function ritaAxel(lager, skala) {
    lager.appendChild(el('line', { x1: 0, x2: bredd, y1: KROPP_H, y2: KROPP_H, class: 'gt-bio-axel-linje' }));
    years.forEach((year) => {
      const x = skala(year);
      const tick = el('line', {
        x1: x, x2: x, y1: KROPP_H, y2: KROPP_H + 5,
        class: `gt-bio-tick${year === cursorAr ? ' gt-bio-tick--aktiv' : ''}`
      });
      tick.appendChild(titel(String(year)));
      lager.appendChild(tick);
    });
    skrivText(lager, String(domain.fran), 2, H - 2, 'gt-bio-etikett', 'start');
    skrivText(lager, String(domain.till), bredd - 2, H - 2, 'gt-bio-etikett', 'end');

    const idagIso = new Date().toISOString().slice(0, 10);
    const xIdag = skala(idagIso);
    const idagLinje = el('line', { x1: xIdag, x2: xIdag, y1: 0, y2: KROPP_H, class: 'gt-bio-idag' });
    idagLinje.appendChild(titel(texts.idagLabel));
    lager.appendChild(idagLinje);
  }

  function ritaCursor(lager, skala) {
    const x = skala(cursorAr);
    lager.appendChild(el('line', { x1: x, x2: x, y1: 0, y2: KROPP_H, class: 'gt-bio-cursor' }));
    const txt = String(cursorAr);
    const pillBredd = Math.max(30, textbredd(txt, 11) + 14);
    let pillX = x - pillBredd / 2;
    if (pillX < 2) pillX = 2;
    if (pillX + pillBredd > bredd - 2) pillX = bredd - 2 - pillBredd;
    lager.appendChild(el('rect', { x: pillX, y: 2, width: pillBredd, height: 16, rx: 8, class: 'gt-bio-cursorpill' }));
    skrivText(lager, txt, pillX + pillBredd / 2, 14, 'gt-bio-cursorpill-text', 'middle');
  }

  // Omväxlande spårbakgrund (V1) — samma mönster som etikettkolumnens
  // :nth-child(even), fast ritad i SVG:n så bakgrunden täcker hela bredden.
  function ritaLanebakgrunder(lager) {
    LANE_TOP.forEach((top, i) => {
      lager.appendChild(el('rect', {
        x: 0, y: top, width: bredd, height: LANE_H[i],
        class: `gt-bio-lanebakgrund${i % 2 === 1 ? ' gt-bio-lanebakgrund--alt' : ''}`
      }));
      if (i > 0) {
        lager.appendChild(el('line', { x1: 0, x2: bredd, y1: top, y2: top, class: 'gt-bio-laneseparator' }));
      }
    });
  }

  function defsHatch() {
    const defs = el('defs');
    const pattern = el('pattern', {
      id: 'gt-bio-hatch', width: 5, height: 5, patternUnits: 'userSpaceOnUse', patternTransform: 'rotate(45)'
    });
    pattern.appendChild(el('rect', { width: 5, height: 5, class: 'gt-bio-hatch-bg' }));
    pattern.appendChild(el('line', { x1: 0, y1: 0, x2: 0, y2: 5, class: 'gt-bio-hatch-line' }));
    defs.appendChild(pattern);
    return defs;
  }

  function render() {
    if (kollapsad) return;
    bredd = svgwrap.clientWidth || 600;
    svg.setAttribute('viewBox', `0 0 ${bredd} ${H}`);
    svg.setAttribute('width', '100%');
    svg.setAttribute('height', H);
    svg.textContent = '';

    const skala = xSkala(domain, bredd);
    svg.appendChild(defsHatch());

    const lagerBakgrund = el('g', { class: 'gt-bio-lager-bakgrund' });
    ritaLanebakgrunder(lagerBakgrund);
    svg.appendChild(lagerBakgrund);

    const lagerAxel = el('g', { class: 'gt-bio-lager-axel' });
    const lagerRattighet = el('g', { class: 'gt-bio-lager-rattighet' });
    const lagerRegister = el('g', { class: 'gt-bio-lager-register' });
    const lagerVerklighet = el('g', { class: 'gt-bio-lager-verklighet' });
    const lagerKlockor = el('g', { class: 'gt-bio-lager-klockor' });
    const lagerCursor = el('g', { class: 'gt-bio-lager-cursor' });

    ritaAxel(lagerAxel, skala);
    ritaRattighet(lagerRattighet, skala);
    ritaRegister(lagerRegister, skala);
    ritaVerklighet(lagerVerklighet, skala);
    ritaKlockor(lagerKlockor, skala);
    ritaCursor(lagerCursor, skala);

    svg.appendChild(lagerAxel);
    svg.appendChild(lagerRattighet);
    svg.appendChild(lagerRegister);
    svg.appendChild(lagerVerklighet);
    svg.appendChild(lagerKlockor);
    svg.appendChild(lagerCursor);

    // Osynlig träffyta över axelremsan sist (överst i z-ordning) — klick/drag
    // snappar till närmaste ortofotoårgång (spec §2).
    axisHit.setAttribute('x', 0);
    axisHit.setAttribute('y', KROPP_H - 4);
    axisHit.setAttribute('width', bredd);
    axisHit.setAttribute('height', AXEL_H + 4);
    svg.appendChild(axisHit);

    arEl.textContent = String(cursorAr);
    regelKnapp.textContent = `${texts.regelverk} ${cursorAr}`;
  }

  /* ---------- interaktion ---------- */

  root.querySelectorAll('[data-riktning]').forEach((knapp) => {
    knapp.addEventListener('click', () => velj(stegAr(years, cursorAr, Number(knapp.dataset.riktning))));
  });

  regelKnapp.addEventListener('click', () => {
    // Stängs popovern ska den bara stängas — den ska inte trigga en ny
    // renderKontextDetalj-hämtning som ändå kastas bort (reviewer-fynd).
    const oppnas = popover.hidden;
    popover.hidden = !popover.hidden;
    if (oppnas) onRegelverk(cursorAr);
  });

  kollapsKnapp.addEventListener('click', () => setKollapsad(!kollapsad));

  if (typeof ResizeObserver !== 'undefined') {
    const ro = new ResizeObserver(() => render());
    ro.observe(svgwrap);
  } else if (typeof window !== 'undefined') {
    window.addEventListener('resize', () => render());
  }

  /* ---------- publikt API ---------- */

  function setAr(ar) {
    if (ar === cursorAr) return;
    cursorAr = ar;
    render();
  }

  function setData(nyData) {
    data = { olovligt: null, lovavvikelse: null, strandskyddTraff: null, ...nyData };
    render();
  }

  // --gt-biografi-hojd sätts på den gemensamma föräldern (Origo-rotens
  // element) — inte på .gt-biografi själv — så att .gt-legend (ett syskon)
  // kan följa med när stripen fälls ihop/ut (minor reviewer-fynd).
  function setKollapsad(ny) {
    kollapsad = ny;
    root.classList.toggle('gt-biografi--kollapsad', ny);
    kollapsKnapp.setAttribute('aria-expanded', String(!ny));
    if (root.parentElement) {
      root.parentElement.style.setProperty('--gt-biografi-hojd', ny ? `${KOLLAPSAD_H}px` : `${TOTAL_H}px`);
    }
    if (!ny) render();
  }

  function uppdateraTexter(nyaT, nySprak) {
    texts = nyaT;
    if (nySprak) aktivSprak = nySprak;
    root.setAttribute('aria-label', texts.biografiAria);
    kollapsKnapp.setAttribute('aria-label', kollapsad ? texts.biografiOppnaAria : texts.biografiKollapsAria);
    root.querySelector('[data-riktning="-1"]').setAttribute('aria-label', texts.foregAr);
    root.querySelector('[data-riktning="1"]').setAttribute('aria-label', texts.nastaAr);
    regelKnapp.setAttribute('aria-label', texts.regelverkAria);
    const namn = [texts.sparVerklighet, texts.sparRegister, texts.sparRattighet, texts.sparKlockor];
    etikettEls.forEach((etikettEl, i) => { etikettEl.textContent = namn[i]; });
    if (!kollapsad) render();
  }

  uppdateraTexter(texts, aktivSprak);
  // Första ritning: containern kan sakna layout-bredd tills nästa frame.
  if (typeof requestAnimationFrame === 'function') requestAnimationFrame(render);
  else render();

  return { el: root, setAr, setData, setKollapsad, uppdateraTexter };
}

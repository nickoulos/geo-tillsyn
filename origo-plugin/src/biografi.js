/**
 * Fastighetsbiografin: den nedre biografistripen som ersätter tidslinjepillen
 * (src/timeline.js, borttagen). En SVG med fyra spår över en gemensam
 * x-axel (1960 -> innevarande år + 1): Verklighet (ortofotohistorik),
 * Register & lov (BAL-registret mot dateringsintervallet), Rättighet
 * (lagregim/lovbefrielser/strandskydd ur regler.json) och Klockor
 * (preskriptionsfönstren). Cursor-strecket = valt år; ‹ › och klick på en
 * Verklighet-punkt flyttar det, precis som tidslinjepillen gjorde.
 *
 * Rent DOM- och tillståndslager: all datering/klassificering kommer från
 * biografi-logik.mjs (ren, testad). Ingen egen juridik ritas här — statusar
 * (preskriberad, avviker, ...) kommer verbatim från backend-fält.
 */

import { stegAr } from './tidslinje-logik.mjs';
import {
  skapaDoman, xSkala, klassificeraAr, lagBand, lovbefrielseBand,
  strandskyddBand, registerGap, klockor
} from './biografi-logik.mjs';
import { formatTal } from './i18n.mjs';

const SVG_NS = 'http://www.w3.org/2000/svg';
const H = 130; // SVG-höjd (kroppen); + 40 px kontrollrad = 170 px totalt
const AXEL_H = 16;
const KROPP_H = H - AXEL_H;
// Spåren är olika höga: Klockor kan behöva rita upp till tre staplar (rättelse,
// sanktion, strandskydd) och behöver mer rum än en enda punktrad gör.
const LANE_ANDEL = [0.24, 0.19, 0.27, 0.30];
const LANE_H = LANE_ANDEL.map((a) => a * KROPP_H);
const LANE_TOP = [];
LANE_H.reduce((top, h) => { LANE_TOP.push(top); return top + h; }, 0);
const LANE_Y = LANE_TOP.map((top, i) => top + LANE_H[i] / 2);

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

// Komponenten tar emot textkatalogen (`t`), inte en språkkod — men
// tooltipens decimaltal ska följa språkets konvention. `sprakKnapp` (knappen
// som visar VÄXLA-TILL-språket) avslöjar vilket språk som faktiskt är
// aktivt: en katalog som erbjuder "EN" är själv svensk.
function harledSprak(texts) {
  return texts.sprakKnapp === 'EN' ? 'sv' : 'en';
}

export function skapaBiografi({ years, startAr, regler, t, onArByte, onRegelverk }) {
  let texts = t;
  let cursorAr = years.includes(startAr) ? startAr : years[years.length - 1];
  let kollapsad = false;
  let data = { olovligt: null, lovavvikelse: null, strandskyddTraff: null };
  let bredd = 0;
  const idagAr = new Date().getFullYear();
  const domain = skapaDoman(idagAr);

  const root = document.createElement('div');
  root.className = 'gt-biografi';
  root.setAttribute('role', 'group');
  root.innerHTML = `
    <div class="gt-biografi__kropp">
      <div class="gt-biografi__etiketter">
        <span class="gt-biografi__etikett"></span>
        <span class="gt-biografi__etikett"></span>
        <span class="gt-biografi__etikett"></span>
        <span class="gt-biografi__etikett"></span>
      </div>
      <div class="gt-biografi__svgwrap">
        <svg class="gt-biografi__svg" xmlns="${SVG_NS}"></svg>
        <div class="gt-biografi__regelpop" hidden></div>
      </div>
    </div>
    <div class="gt-biografi__rad">
      <button class="gt-knapp gt-knapp--ikon" type="button" data-riktning="-1">‹</button>
      <span class="gt-biografi__ar"></span>
      <button class="gt-knapp gt-knapp--ikon" type="button" data-riktning="1">›</button>
      <button class="gt-knapp gt-biografi__regelknapp" type="button"></button>
      <button class="gt-knapp gt-knapp--ikon gt-biografi__kollaps" type="button" aria-expanded="true">${CHEVRON}</button>
    </div>`;

  const svg = root.querySelector('.gt-biografi__svg');
  const svgwrap = root.querySelector('.gt-biografi__svgwrap');
  const popover = root.querySelector('.gt-biografi__regelpop');
  const arEl = root.querySelector('.gt-biografi__ar');
  const regelKnapp = root.querySelector('.gt-biografi__regelknapp');
  const kollapsKnapp = root.querySelector('.gt-biografi__kollaps');
  const etikettEls = root.querySelectorAll('.gt-biografi__etikett');

  function velj(ar) {
    if (ar === cursorAr) return;
    cursorAr = ar;
    render();
    onArByte(ar);
    if (!popover.hidden) onRegelverk(cursorAr);
  }

  /* ---------- Spår 1: Verklighet ---------- */

  function ritaVerklighet(lager, skala) {
    const y = LANE_Y[0];
    const klasser = klassificeraAr(data.olovligt, years);
    const poang = (data.olovligt && data.olovligt.poang_per_ar) || {};
    const sprak = harledSprak(texts);

    years.forEach((year) => {
      const status = klasser.get(year);
      const x = skala(year);
      const cirkel = el('circle', { cx: x, cy: y, r: 5, class: `gt-bio-punkt gt-bio-punkt--${status}` });
      const p = poang[String(year)];
      cirkel.appendChild(titel(p !== undefined ? `${year}: ${formatTal(p, sprak)}` : String(year)));
      cirkel.style.cursor = 'pointer';
      cirkel.addEventListener('click', () => velj(year));
      lager.appendChild(cirkel);
    });

    const { olovligt } = data;
    if (olovligt && olovligt.sista_ar_utan != null && olovligt.forsta_ar_med != null) {
      const x1 = skala(olovligt.sista_ar_utan);
      const x2 = skala(olovligt.forsta_ar_med);
      // Klammern måste rymmas ovanför punktraden men innanför SVG:ns överkant
      // (y=0) — spår 1 har inte 16 px ledigt ovanför sin centrumlinje.
      const yBrace = Math.max(8, y - LANE_H[0] / 2 + 8);
      const brace = el('g', { class: 'gt-bio-klammer' });
      brace.appendChild(el('line', { x1, x2, y1: yBrace, y2: yBrace }));
      brace.appendChild(el('line', { x1, x2: x1, y1: yBrace - 3, y2: yBrace + 3 }));
      brace.appendChild(el('line', { x1: x2, x2, y1: yBrace - 3, y2: yBrace + 3 }));
      const label = el('text', { x: (x1 + x2) / 2, y: yBrace - 5, class: 'gt-bio-etikett', 'text-anchor': 'middle' });
      label.textContent = texts.forstSynlig(olovligt.sista_ar_utan, olovligt.forsta_ar_med);
      brace.appendChild(label);
      lager.appendChild(brace);
    }
  }

  /* ---------- Spår 2: Register & lov ---------- */

  function ritaRegister(lager, skala) {
    const y = LANE_Y[1];
    const { olovligt, lovavvikelse } = data;
    const gap = registerGap(olovligt);
    if (gap) {
      const x1 = skala(gap.fran);
      const x2 = skala(gap.till);
      const linje = el('line', { x1, x2, y1: y, y2: y, class: 'gt-bio-gap' });
      lager.appendChild(linje);
      const label = el('text', { x: (x1 + x2) / 2, y: y - 8, class: 'gt-bio-etikett gt-bio-etikett--avviker', 'text-anchor': 'middle' });
      label.textContent = texts.avvikerBadge;
      lager.appendChild(label);
    }
    if (olovligt && olovligt.bal_nybyggnadsar != null) {
      const x = skala(olovligt.bal_nybyggnadsar);
      const rombStorlek = 5;
      const romb = el('path', {
        d: `M ${x} ${y - rombStorlek} L ${x + rombStorlek} ${y} L ${x} ${y + rombStorlek} L ${x - rombStorlek} ${y} Z`,
        class: 'gt-bio-romb'
      });
      romb.appendChild(titel(texts.registerEtikett(olovligt.bal_nybyggnadsar)));
      lager.appendChild(romb);
      const label = el('text', { x, y: y + 18, class: 'gt-bio-etikett', 'text-anchor': 'middle' });
      label.textContent = texts.registerEtikett(olovligt.bal_nybyggnadsar);
      lager.appendChild(label);
    }
    if (lovavvikelse && lovavvikelse.beslutsdatum) {
      const x = skala(lovavvikelse.beslutsdatum);
      const ikon = el('rect', { x: x - 4, y: y - 12, width: 8, height: 10, class: 'gt-bio-dokument' });
      ikon.appendChild(titel(texts.lovEtikett(lovavvikelse.dnr || '')));
      lager.appendChild(ikon);
      const label = el('text', { x, y: y - 15, class: 'gt-bio-etikett', 'text-anchor': 'middle' });
      label.textContent = texts.lovEtikett(lovavvikelse.dnr || '');
      lager.appendChild(label);
    }
  }

  /* ---------- Spår 3: Rättighet ---------- */

  function ritaRattighet(lager, skala) {
    if (!regler) return; // regler.json kunde inte hämtas — spåret lämnas tomt, inte trasigt
    const y0 = LANE_Y[2] - LANE_H[2] / 2 + 4;
    const bandHojd = LANE_H[2] - 8;
    const isoCursor = `${cursorAr}-07-01`;

    lagBand(regler).forEach((band) => {
      const x1 = skala(band.fran);
      const x2 = band.till ? skala(band.till) : bredd;
      const aktiv = within(band.fran, band.till, isoCursor);
      const rect = el('rect', {
        x: x1, y: y0, width: Math.max(0, x2 - x1), height: bandHojd,
        class: `gt-bio-lagband${aktiv ? ' gt-bio-lagband--aktiv' : ''}`
      });
      rect.appendChild(titel(`${band.namn} (${band.sfs})`));
      lager.appendChild(rect);
      if (x2 - x1 > 40) {
        const label = el('text', { x: x1 + 4, y: y0 + bandHojd / 2 + 4, class: 'gt-bio-etikett gt-bio-etikett--band' });
        label.textContent = band.namn;
        lager.appendChild(label);
      }
    });

    const lovY = y0 + bandHojd - 5;
    lovbefrielseBand(regler).forEach((b) => {
      const x1 = skala(b.fran);
      const x2 = b.till ? skala(b.till) : bredd;
      const rect = el('rect', { x: x1, y: lovY, width: Math.max(0, x2 - x1), height: 4, class: 'gt-bio-lovbefrielse' });
      rect.appendChild(titel(`${b.namn} ${b.max_kvm} m²`));
      lager.appendChild(rect);
    });

    const ss = strandskyddBand(regler);
    const xSs = skala(ss.fran);
    const ssRect = el('rect', {
      x: xSs, y: y0, width: Math.max(0, bredd - xSs), height: bandHojd, class: 'gt-bio-strandskydd'
    });
    ssRect.appendChild(titel(texts.strandskydd));
    lager.appendChild(ssRect);
  }

  /* ---------- Spår 4: Klockor ---------- */

  function ritaKlockor(lager, skala) {
    if (!regler) return; // regler.json kunde inte hämtas — inga preskriptionsår att räkna ut
    const rader = klockor(data.olovligt, data.strandskyddTraff, regler);
    const NAMN = { rattelse: texts.rattelseNamn, sanktion: texts.sanktionNamn, strandskydd: texts.strandskydd };
    const radAvstand = 14; // mellanrum mellan klockornas rader — rymmer etiketten ovanför stapeln
    rader.forEach((k, i) => {
      const y = LANE_Y[3] - (rader.length - 1) * (radAvstand / 2) + i * radAvstand;
      const xStartSaker = skala(k.startSaker);
      const xStartOsaker = skala(k.startOsaker);
      const xSlutSaker = k.oandlig ? bredd : skala(k.slutSaker);
      const xSlutOsaker = k.oandlig ? bredd : skala(k.slutOsaker);

      if (xStartOsaker < xStartSaker) {
        lager.appendChild(el('line', {
          x1: xStartOsaker, x2: xStartSaker, y1: y, y2: y, class: 'gt-bio-klocka gt-bio-klocka--osaker'
        }));
      }
      lager.appendChild(el('line', {
        x1: xStartSaker, x2: xSlutOsaker, y1: y, y2: y, class: 'gt-bio-klocka'
      }));
      if (!k.oandlig && xSlutOsaker < xSlutSaker) {
        lager.appendChild(el('line', {
          x1: xSlutOsaker, x2: xSlutSaker, y1: y, y2: y, class: 'gt-bio-klocka gt-bio-klocka--osaker'
        }));
      }
      if (k.oandlig) {
        lager.appendChild(el('path', {
          d: `M ${bredd - 7} ${y - 4} L ${bredd} ${y} L ${bredd - 7} ${y + 4}`,
          class: 'gt-bio-pil'
        }));
      }

      let etikett = NAMN[k.nyckel] || k.nyckel;
      if (k.nyckel === 'strandskydd') {
        if (k.status === false) etikett = `${NAMN.strandskydd} · ${texts.ingenPreskription}`;
      } else if (k.status === true) {
        etikett = `${NAMN[k.nyckel]} · ${texts.utgangen(k.slutSaker)}`;
      } else if (k.status === false) {
        etikett = `${NAMN[k.nyckel]} · ${texts.loperTill(k.slutSaker)}`;
      }
      const label = el('text', { x: xStartSaker, y: y - 4, class: 'gt-bio-etikett' });
      label.textContent = etikett;
      lager.appendChild(label);
    });
  }

  /* ---------- axel + cursor + idag ---------- */

  function ritaAxel(lager, skala) {
    lager.appendChild(el('line', { x1: 0, x2: bredd, y1: H - AXEL_H, y2: H - AXEL_H, class: 'gt-bio-axel-linje' }));
    years.forEach((year) => {
      const x = skala(year);
      const tick = el('line', {
        x1: x, x2: x, y1: H - AXEL_H, y2: H - AXEL_H + 5,
        class: `gt-bio-tick${year === cursorAr ? ' gt-bio-tick--aktiv' : ''}`
      });
      tick.appendChild(titel(String(year)));
      lager.appendChild(tick);
    });
    const label = el('text', { x: 2, y: H - 3, class: 'gt-bio-etikett' });
    label.textContent = String(domain.fran);
    lager.appendChild(label);
    const labelSlut = el('text', { x: bredd - 2, y: H - 3, class: 'gt-bio-etikett', 'text-anchor': 'end' });
    labelSlut.textContent = String(domain.till);
    lager.appendChild(labelSlut);

    const idagIso = new Date().toISOString().slice(0, 10);
    const xIdag = skala(idagIso);
    const idagLinje = el('line', { x1: xIdag, x2: xIdag, y1: 0, y2: H - AXEL_H, class: 'gt-bio-idag' });
    idagLinje.appendChild(titel(texts.idagLabel));
    lager.appendChild(idagLinje);
  }

  function ritaCursor(lager, skala) {
    const x = skala(cursorAr);
    lager.appendChild(el('line', { x1: x, x2: x, y1: 0, y2: H - AXEL_H, class: 'gt-bio-cursor' }));
  }

  function render() {
    if (kollapsad) return;
    bredd = svgwrap.clientWidth || 600;
    svg.setAttribute('viewBox', `0 0 ${bredd} ${H}`);
    svg.setAttribute('width', '100%');
    svg.setAttribute('height', H);
    svg.textContent = '';

    const skala = xSkala(domain, bredd);
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

    arEl.textContent = String(cursorAr);
    regelKnapp.textContent = `${texts.regelverk} ${cursorAr}`;
  }

  /* ---------- interaktion ---------- */

  root.querySelectorAll('[data-riktning]').forEach((knapp) => {
    knapp.addEventListener('click', () => velj(stegAr(years, cursorAr, Number(knapp.dataset.riktning))));
  });

  regelKnapp.addEventListener('click', () => {
    popover.hidden = !popover.hidden;
    onRegelverk(cursorAr);
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

  function setKollapsad(ny) {
    kollapsad = ny;
    root.classList.toggle('gt-biografi--kollapsad', ny);
    kollapsKnapp.setAttribute('aria-expanded', String(!ny));
    if (!ny) render();
  }

  function uppdateraTexter(nyaT) {
    texts = nyaT;
    root.setAttribute('aria-label', texts.biografiAria);
    kollapsKnapp.setAttribute('aria-label', kollapsad ? texts.biografiOppnaAria : texts.biografiKollapsAria);
    root.querySelector('[data-riktning="-1"]').setAttribute('aria-label', texts.foregAr);
    root.querySelector('[data-riktning="1"]').setAttribute('aria-label', texts.nastaAr);
    regelKnapp.setAttribute('aria-label', texts.regelverkAria);
    const namn = [texts.sparVerklighet, texts.sparRegister, texts.sparRattighet, texts.sparKlockor];
    etikettEls.forEach((etikettEl, i) => { etikettEl.textContent = namn[i]; });
    if (!kollapsad) render();
  }

  uppdateraTexter(texts);
  // Första ritning: containern kan sakna layout-bredd tills nästa frame.
  if (typeof requestAnimationFrame === 'function') requestAnimationFrame(render);
  else render();

  return { el: root, setAr, setData, setKollapsad, uppdateraTexter };
}

/**
 * Tidslinjepillen: flytande kartkontroll med ‹ ›-steg, proportionell slider
 * som snappar till faktiska fotoårgångar (luckorna visas ärligt som ticks)
 * och en expanderbar regelverkssektion (sammanfattningsrad + detalj).
 */

import { narmasteAr, stegAr, tickPosition } from './tidslinje-logik.mjs';

const CHEVRON = '<svg class="gt-chevron" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M6 9l6 6 6-6"/></svg>';

export function skapaTidslinje({ years, startAr, t, onArByte }) {
  let aktuelltAr = years.includes(startAr) ? startAr : years[years.length - 1];
  const min = years[0];
  const max = years[years.length - 1];

  const el = document.createElement('div');
  el.className = 'gt-tidslinje';
  el.setAttribute('role', 'group');
  el.innerHTML = `
    <div class="gt-tidslinje__rad">
      <button class="gt-knapp gt-knapp--ikon" type="button" data-riktning="-1">‹</button>
      <div class="gt-tidslinje__spar">
        <input class="gt-tidslinje__slider" type="range" min="${min}" max="${max}"
               step="1" value="${aktuelltAr}">
        <div class="gt-tidslinje__ticks">${years.map((y) =>
    `<span class="gt-tick" data-ar="${y}" style="left:${tickPosition(years, y)}%" title="${y}"></span>`).join('')}</div>
      </div>
      <button class="gt-knapp gt-knapp--ikon" type="button" data-riktning="1">›</button>
      <span class="gt-tidslinje__ar">${aktuelltAr}</span>
    </div>
    <button class="gt-tidslinje__regeltoggle" type="button" aria-expanded="false">
      <span class="gt-regel-sammanfattning"></span>${CHEVRON}
    </button>
    <div class="gt-tidslinje__regeldetalj" hidden></div>`;

  const slider = el.querySelector('.gt-tidslinje__slider');
  const arEl = el.querySelector('.gt-tidslinje__ar');
  const toggle = el.querySelector('.gt-tidslinje__regeltoggle');
  const detalj = el.querySelector('.gt-tidslinje__regeldetalj');

  function setAr(ar) {
    aktuelltAr = ar;
    slider.value = String(ar);
    arEl.textContent = String(ar);
    el.querySelectorAll('.gt-tick').forEach((tick) => {
      tick.classList.toggle('gt-tick--aktiv', Number(tick.dataset.ar) === ar);
    });
  }

  slider.addEventListener('input', () => {
    const ar = narmasteAr(years, Number(slider.value));
    if (ar !== aktuelltAr) {
      setAr(ar);
      onArByte(ar);
    } else {
      slider.value = String(ar); // snappa tillbaka mellan årgångar
    }
  });
  el.querySelectorAll('[data-riktning]').forEach((knapp) => {
    knapp.addEventListener('click', () => {
      const ar = stegAr(years, aktuelltAr, Number(knapp.dataset.riktning));
      if (ar !== aktuelltAr) {
        setAr(ar);
        onArByte(ar);
      }
    });
  });
  toggle.addEventListener('click', () => {
    const oppen = toggle.getAttribute('aria-expanded') === 'true';
    toggle.setAttribute('aria-expanded', String(!oppen));
    detalj.hidden = oppen;
  });

  function setKontext(sammanfattningHtml, detaljHtml) {
    el.querySelector('.gt-regel-sammanfattning').innerHTML = sammanfattningHtml;
    detalj.innerHTML = detaljHtml;
  }

  function uppdateraTexter(nyaT) {
    el.setAttribute('aria-label', nyaT.tidslinjeAria);
    slider.setAttribute('aria-label', nyaT.sliderAria);
    el.querySelector('[data-riktning="-1"]').setAttribute('aria-label', nyaT.foregAr);
    el.querySelector('[data-riktning="1"]').setAttribute('aria-label', nyaT.nastaAr);
    toggle.setAttribute('aria-label', nyaT.regelverkAria);
  }

  uppdateraTexter(t);
  setAr(aktuelltAr);
  return { el, setAr, setKontext, uppdateraTexter };
}

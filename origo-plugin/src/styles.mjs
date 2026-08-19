/**
 * Design-tokens + hela stylesheeten för Geo-Tillsyn-UI:t, injicerad som en
 * <style>-tagg från bundlen (inga webpack-loaders, inga inline-stilar).
 * Tokens sätts på komponentrötterna (inte :root) för att inte läcka in i
 * Origos egna kontroller.
 */

export const STYLE_ID = 'gt-styles';

export function cssText() {
  return `
.gt-panel, .gt-biografi, .gt-tab, .gt-legend {
  --gt-accent: #1e4ed8;
  --gt-accent-mork: #173db0;
  --gt-accent-ljus: #eaf0fe;
  --gt-ink: #16202e;
  --gt-ink-svag: #5a6a7e;
  --gt-yta: #ffffff;
  --gt-yta-svag: #f5f7fa;
  --gt-kant: #dde3ec;
  --gt-varning-bg: #fdf6e7;
  --gt-varning-kant: #ecd9a8;
  --gt-varning-ink: #7a5b16;
  --gt-fel-ink: #a03030;
  --gt-fel-bg: #fdf0f0;
  --gt-radie: 8px;
  --gt-skugga: 0 1px 2px rgba(22,32,46,.08), 0 4px 16px rgba(22,32,46,.10);
  --gt-panel-bredd: 380px;
  font-family: -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  color: var(--gt-ink);
  font-size: 13px;
  line-height: 1.5;
  box-sizing: border-box;
}
.gt-panel *, .gt-biografi *, .gt-tab *, .gt-legend * { box-sizing: inherit; }

/* ---------- sidopanel ---------- */
.gt-panel {
  position: absolute; top: 0; right: 0; bottom: 0;
  width: var(--gt-panel-bredd); max-width: 92vw;
  display: flex; flex-direction: column;
  background: var(--gt-yta);
  border-left: 1px solid var(--gt-kant);
  box-shadow: -8px 0 24px rgba(22,32,46,.10);
  z-index: 40;
  transition: transform .2s ease;
}
.gt-panel--kollapsad { transform: translateX(100%); box-shadow: none; }
.gt-panel__huvud {
  display: flex; align-items: center; justify-content: space-between;
  gap: .5rem; padding: .8rem 1rem;
  border-bottom: 1px solid var(--gt-kant); background: var(--gt-yta);
}
.gt-panel__titelgrupp { display: flex; align-items: center; gap: .6rem; min-width: 0; }
.gt-panel__logo {
  display: grid; place-items: center; width: 32px; height: 32px;
  border-radius: var(--gt-radie); background: var(--gt-accent); color: #fff; flex: none;
}
.gt-panel__logo svg { width: 18px; height: 18px; }
.gt-panel__titel { margin: 0; font-size: 15px; font-weight: 700; letter-spacing: -.01em; }
.gt-panel__kontext { display: block; font-size: 11px; color: var(--gt-ink-svag); }
.gt-panel__knappar { display: flex; gap: .35rem; }
.gt-panel__kropp { flex: 1; overflow-y: auto; padding: .9rem 1rem; scrollbar-width: thin; }
.gt-panel__fot {
  display: flex; align-items: center; gap: .55rem;
  padding: .7rem 1rem; font-size: 12px; font-weight: 600;
  border-top: 1px solid var(--gt-kant); background: var(--gt-yta-svag);
  color: var(--gt-ink);
}
.gt-panel__fot svg { width: 16px; height: 16px; flex: none; color: var(--gt-accent); }

/* ---------- knappar ---------- */
.gt-knapp {
  cursor: pointer; font: inherit; font-weight: 600;
  border: 1px solid var(--gt-kant); border-radius: 6px;
  background: var(--gt-yta); color: var(--gt-ink);
  padding: .25rem .55rem; transition: background .15s ease, border-color .15s ease;
}
.gt-knapp:hover { background: var(--gt-yta-svag); border-color: #c4cdda; }
.gt-knapp:focus-visible {
  outline: 2px solid var(--gt-accent); outline-offset: 1px;
}
.gt-knapp--primar { background: var(--gt-accent); border-color: var(--gt-accent); color: #fff; }
.gt-knapp--primar:hover { background: var(--gt-accent-mork); border-color: var(--gt-accent-mork); }
.gt-knapp--ikon { padding: .25rem .45rem; line-height: 1; }

/* kollapsad flik */
.gt-tab {
  position: absolute; top: 50%; right: 0; transform: translateY(-50%);
  writing-mode: vertical-rl; padding: .8rem .4rem;
  background: var(--gt-accent); color: #fff; font-weight: 700; font-size: 12px;
  border: none; border-radius: var(--gt-radie) 0 0 var(--gt-radie);
  cursor: pointer; z-index: 41; box-shadow: var(--gt-skugga);
}

/* ---------- tomläge ---------- */
.gt-tom { text-align: center; padding: 2.2rem 1rem; color: var(--gt-ink-svag); }
.gt-tom svg { width: 44px; height: 44px; color: var(--gt-accent); opacity: .85; }
.gt-tom h3 { margin: .8rem 0 .3rem; font-size: 14px; color: var(--gt-ink); }
.gt-tom p { margin: 0 auto; max-width: 30ch; font-size: 12.5px; }

/* ---------- fastighetsrubrik ---------- */
.gt-snedbild { margin-top: .8rem; padding: .8rem; border: 1px solid var(--gt-kant); border-radius: var(--gt-radie); background: var(--gt-yta); }
.gt-snedbild__grid { display: grid; grid-template-columns: 1fr 1fr; gap: .5rem; margin-top: .5rem; }
.gt-snedbild__fig { margin: 0; }
.gt-snedbild__fig img { display: block; width: 100%; aspect-ratio: 1 / 1; object-fit: cover; border-radius: 6px; border: 1px solid var(--gt-kant); background: var(--gt-yta-svag); }
.gt-snedbild__fig figcaption { font-size: 11px; color: var(--gt-ink-svag); margin-top: .2rem; }
.gt-snedbild__oppna { display: inline-block; text-decoration: none; margin-top: .4rem; }
.gt-rad--block { display: block; }
.gt-rattigheter { margin: .2rem 0 0; padding-left: 1.1rem; }
.gt-rattigheter li { margin: .1rem 0; }
.gt-rattighet__fast { color: var(--gt-ink-svag); }
.gt-fastighet { margin-bottom: .8rem; }
.gt-fastighet__etikett {
  font-size: 10.5px; font-weight: 700; letter-spacing: .08em;
  text-transform: uppercase; color: var(--gt-ink-svag);
}
.gt-fastighet__namn { font-size: 17px; font-weight: 700; letter-spacing: -.01em; }
.gt-fastighet__namn--saknas { font-weight: 400; color: var(--gt-ink-svag); font-style: italic; }

/* ---------- kontrollkort ---------- */
.gt-kort {
  border: 1px solid var(--gt-kant); border-radius: var(--gt-radie);
  background: var(--gt-yta); margin-bottom: .7rem; overflow: hidden;
}
.gt-kort__huvud {
  display: flex; align-items: center; gap: .6rem; padding: .6rem .75rem .1rem;
}
.gt-kort__ikon {
  display: grid; place-items: center; width: 28px; height: 28px; flex: none;
  border-radius: 6px; background: var(--gt-accent-ljus); color: var(--gt-accent);
}
.gt-kort__ikon svg { width: 16px; height: 16px; }
.gt-kort__huvud h3 { margin: 0; font-size: 13px; font-weight: 700; }
.gt-kort__under { display: block; font-size: 11px; color: var(--gt-ink-svag); }
.gt-kort__status { padding: .45rem .75rem .6rem; }
.gt-rubrikrad { font-size: 13px; font-weight: 600; }
.gt-kort__innehall { border-top: 1px solid var(--gt-kant); background: var(--gt-yta-svag); }
.gt-info { color: var(--gt-ink-svag); font-size: 12.5px; padding: .1rem 0; }

/* skelett-laddare */
.gt-skelett { display: block; height: 12px; border-radius: 4px;
  background: linear-gradient(90deg, #edf0f5 25%, #f7f9fc 45%, #edf0f5 65%);
  background-size: 200% 100%; animation: gt-skimmer 1.2s infinite linear; }
.gt-skelett + .gt-skelett { margin-top: .45rem; width: 70%; }
@keyframes gt-skimmer { to { background-position: -200% 0; } }

/* fel-läge */
.gt-kort__fel { color: var(--gt-fel-ink); background: var(--gt-fel-bg);
  border-radius: 6px; padding: .5rem .6rem; font-size: 12.5px;
  display: flex; align-items: center; justify-content: space-between; gap: .6rem; }

/* ---------- dossier-innehåll ---------- */
.gt-sektion { border-top: 1px solid var(--gt-kant); }
.gt-sektion summary {
  cursor: pointer; list-style: none; display: flex; align-items: center; gap: .4rem;
  padding: .5rem .75rem; font-size: 11px; font-weight: 700;
  letter-spacing: .08em; text-transform: uppercase; color: var(--gt-ink-svag);
  user-select: none;
}
.gt-sektion summary::-webkit-details-marker { display: none; }
.gt-sektion summary::after { content: '▸'; margin-left: auto; font-size: 10px;
  transition: transform .15s ease; }
.gt-sektion[open] summary::after { transform: rotate(90deg); }
.gt-sektion__inner { padding: 0 .75rem .6rem; }
.gt-rad { display: flex; justify-content: space-between; gap: 1rem;
  padding: .22rem 0; border-bottom: 1px dashed var(--gt-kant); font-size: 12.5px; }
.gt-rad:last-child { border-bottom: none; }
.gt-rad__etikett { color: var(--gt-ink-svag); }
.gt-rad__varde { text-align: right; font-weight: 600; overflow-wrap: anywhere; }
.gt-traff { font-weight: 700; margin-top: .5rem; font-size: 12px; }
.gt-badge { display: inline-block; padding: .05rem .45rem; border-radius: 999px;
  background: var(--gt-accent-ljus); color: var(--gt-accent-mork);
  font-size: 11px; font-weight: 700; }
.gt-osakerhet { margin: .4rem 0; padding: .45rem .6rem .45rem .5rem;
  background: var(--gt-varning-bg); border: 1px solid var(--gt-varning-kant);
  border-left: 3px solid var(--gt-varning-ink);
  border-radius: 6px; color: var(--gt-varning-ink); font-size: 12px; }
.gt-osakerhet ul { margin: 0; padding-left: 1rem; }
.gt-kallor { margin-top: .4rem; font-size: 12px; }
.gt-kallor__rubrik { font-weight: 700; color: var(--gt-ink-svag); font-size: 11px;
  letter-spacing: .06em; text-transform: uppercase; }
.gt-kallor ul { margin: .15rem 0 0; padding-left: 1rem; }
.gt-kallor a { color: var(--gt-accent); text-decoration: none; }
.gt-kallor a:hover { text-decoration: underline; }

/* ---------- tillsynsradar ---------- */
.gt-radarknapp { display: inline-flex; align-items: center; gap: .3rem; }
.gt-radarknapp svg { width: 14px; height: 14px; color: var(--gt-accent); }
.gt-radar { border: 1px solid var(--gt-kant); border-radius: var(--gt-radie);
  background: var(--gt-yta); overflow: hidden; }
.gt-radar__status { padding: .5rem .8rem; }
.gt-radar__innehall { padding: 0 .8rem .6rem; }
.gt-radar__lista { list-style: none; margin: 0; padding: 0; }
.gt-radar__rad { border-top: 1px solid var(--gt-kant); }
.gt-radar__val { display: flex; align-items: center; gap: .6rem; width: 100%;
  padding: .5rem .1rem; border: none; background: none; cursor: pointer;
  font: inherit; color: inherit; text-align: left; border-radius: 6px; }
.gt-radar__val:hover { background: var(--gt-yta-svag); }
.gt-radar__val:focus-visible { outline: 2px solid var(--gt-accent); outline-offset: 1px; }
.gt-radar__rang { display: grid; place-items: center; flex: none; width: 26px; height: 26px;
  border-radius: 50%; background: var(--gt-accent); color: #fff; font-weight: 800; font-size: 12px; }
.gt-radar__kropp { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.gt-radar__fastighet { font-weight: 700; font-size: 13px; }
.gt-radar__fastighet--saknas { font-weight: 400; color: var(--gt-ink-svag); font-style: italic; }
.gt-radar__meta { font-size: 11.5px; color: var(--gt-ink-svag); overflow-wrap: anywhere; }
.gt-radar__poang { flex: none; font-weight: 800; font-variant-numeric: tabular-nums;
  color: var(--gt-accent-mork); font-size: 13px; }
.gt-radar__grunder { margin: 0 0 .4rem 2.1rem; font-size: 11.5px; color: var(--gt-ink-svag); }
.gt-radar__grunder summary { cursor: pointer; list-style: none; }
.gt-radar__grunder summary::-webkit-details-marker { display: none; }
.gt-radar__grunder summary::before { content: '▸ '; font-size: 10px; }
.gt-radar__grunder[open] summary::before { content: '▾ '; }
.gt-radar__grunder ul { margin: .2rem 0 0; padding-left: 1rem; }
.gt-radar__not { margin: .6rem 0 .3rem; padding: .5rem .6rem; font-size: 12px;
  background: var(--gt-accent-ljus); color: var(--gt-accent-mork); border-radius: 6px; }
.gt-radar__modell { margin: 0; padding-left: 1rem; font-size: 12px; }
.gt-radar__tillbaka { display: inline-block; margin-bottom: .7rem; }

/* ---------- fastighetsbiografin (biografi-stripen) ---------- */
/* --gt-biografi-hojd sätts av biografi.js på den gemensamma Origo-roten
   (föräldern till både .gt-biografi och .gt-legend) när stripen fälls
   ihop/ut, så legenden kan följa med. 284px = kropp(230) + axel(14) +
   kontrollrad(40); default här matchar det expanderade läget. */
.gt-biografi {
  position: absolute; left: 0; right: 0; bottom: 0; height: var(--gt-biografi-hojd, 284px);
  background: var(--gt-yta); border-top: 1px solid var(--gt-kant);
  box-shadow: 0 -4px 16px rgba(22,32,46,.08); z-index: 39;
  display: flex; flex-direction: column;
  transition: padding-right .2s ease, height .2s ease;
}
.gt-oppen .gt-biografi { padding-right: var(--gt-panel-bredd); }
.gt-biografi--kollapsad { height: 40px; }
@media (max-width: 900px) {
  .gt-biografi { height: 40px; }
  .gt-biografi .gt-biografi__kropp { display: none; }
}
.gt-biografi--kollapsad .gt-biografi__kropp { display: none; }
.gt-biografi__kropp { flex: 1; display: flex; overflow: hidden; }
.gt-biografi__etiketter {
  flex: none; width: 92px; display: flex; flex-direction: column;
  box-sizing: border-box; border-right: 1px solid var(--gt-kant);
}
.gt-biografi__etikett {
  display: flex; align-items: center; padding: 0 .5rem;
  font-size: 12px; font-weight: 700; letter-spacing: .02em;
  color: var(--gt-ink-svag); line-height: 1.2;
  border-bottom: 1px solid var(--gt-kant); box-sizing: border-box;
}
.gt-biografi__etikett:nth-child(even) { background: var(--gt-yta-svag); }
.gt-biografi__svgwrap { position: relative; flex: 1; min-width: 0; }
.gt-biografi__svg { display: block; width: 100%; height: 100%; }
.gt-biografi__regelpop {
  position: absolute; right: .5rem; bottom: 2.4rem; z-index: 2;
  width: min(320px, 90%); max-height: 65%; overflow-y: auto;
  background: var(--gt-yta); border: 1px solid var(--gt-kant); border-radius: var(--gt-radie);
  box-shadow: var(--gt-skugga); padding: .5rem .6rem; font-size: 12.5px;
}
.gt-regelrubrik { font-size: 12px; font-weight: 700; margin-bottom: .1rem; }
.gt-regelnot { font-size: 11px; color: var(--gt-ink-svag); margin-bottom: .35rem; }
.gt-biografi__rad {
  flex: none; display: flex; align-items: center; gap: .5rem;
  height: 40px; padding: 0 .8rem; border-top: 1px solid var(--gt-kant);
}
.gt-biografi__ar { font-size: 15px; font-weight: 800; letter-spacing: -.02em;
  min-width: 2.9rem; text-align: center; font-variant-numeric: tabular-nums; }
.gt-biografi__regelknapp { margin-left: auto; font-size: 12px; }
.gt-biografi--kollapsad .gt-biografi__regelknapp { display: none; }
.gt-biografi__kollaps .gt-chevron { transition: transform .15s ease; }
.gt-biografi__kollaps[aria-expanded="false"] .gt-chevron { transform: rotate(180deg); }

/* svg-innehåll: teckensnitt/färger styrs härifrån, inte inline i biografi.js */
.gt-biografi__svg text {
  font-family: inherit; -webkit-user-select: none; user-select: none;
}
.gt-biografi__svg text.gt-bio-etikett {
  font-size: 11px; fill: var(--gt-ink-svag);
}
.gt-biografi__svg text.gt-bio-etikett--inuti { fill: var(--gt-ink); font-weight: 600; }
.gt-biografi__svg text.gt-bio-etikett--band { fill: var(--gt-ink); font-size: 11px; font-weight: 600; }
.gt-biografi__svg text.gt-bio-etikett--lov { fill: #ffffff; font-size: 10.5px; font-weight: 700; }

/* omväxlande spårbakgrund (V1) — samma par som etikettkolumnens :nth-child */
.gt-bio-lanebakgrund { fill: var(--gt-yta); }
.gt-bio-lanebakgrund--alt { fill: var(--gt-yta-svag); }
.gt-bio-laneseparator { stroke: var(--gt-kant); stroke-width: 1; }

/* ---------- spår 1: Verklighet ---------- */
.gt-bio-punkt { stroke-width: 2; }
.gt-bio-punkt--narvaro { fill: var(--gt-accent); stroke: var(--gt-accent); }
.gt-bio-punkt--franvaro { fill: none; stroke: #b9c3d2; }
.gt-bio-punkt--otydlig { fill: var(--gt-varning-ink); stroke: var(--gt-varning-ink); }
.gt-bio-punkt--utesluten { fill: none; stroke: #b9c3d2; stroke-dasharray: 2 2; }
.gt-bio-punkt--okand { fill: none; stroke: #dde3ec; stroke-width: 1; }
.gt-bio-klammer line { stroke: var(--gt-ink-svag); stroke-width: 1; }

/* ---------- spår 2: Register & lov ---------- */
.gt-bio-gap { stroke: var(--gt-varning-ink); stroke-width: 2; stroke-dasharray: 4 3; }
.gt-bio-romb { fill: var(--gt-accent-mork); }
.gt-bio-dokument { fill: var(--gt-accent-ljus); stroke: var(--gt-accent); stroke-width: 1; }

/* ---------- spår 3: Rättighet ---------- */
.gt-bio-lagband { fill: var(--gt-accent-ljus); opacity: .45; }
.gt-bio-lagband--aktiv { opacity: 1; }
.gt-bio-lovbefrielse { fill: var(--gt-accent-mork); opacity: .85; }
.gt-bio-strandskydd { fill: rgba(40,150,120,.16); stroke: rgba(40,150,120,.5); stroke-width: 1; }

/* ---------- spår 4: Klockor ---------- */
.gt-bio-klockstapel { fill: var(--gt-ink); }
.gt-bio-klockstapel--osaker { fill: url(#gt-bio-hatch); stroke: var(--gt-ink-svag); stroke-width: .5; }
.gt-bio-hatch-bg { fill: var(--gt-yta); }
.gt-bio-hatch-line { stroke: var(--gt-ink-svag); stroke-width: 2; }
.gt-bio-pil { fill: var(--gt-ink); }

/* ---------- axel, cursor, idag ---------- */
.gt-bio-axishit { cursor: pointer; }
.gt-bio-axel-linje { stroke: var(--gt-kant); stroke-width: 1; }
.gt-bio-tick { stroke: #b9c3d2; stroke-width: 1.5; cursor: pointer; }
.gt-bio-tick--aktiv { stroke: var(--gt-accent); stroke-width: 2; }
.gt-bio-idag { stroke: var(--gt-ink-svag); stroke-width: 1; stroke-dasharray: 2 3; }
.gt-bio-cursor { stroke: var(--gt-accent); stroke-width: 2; }
.gt-bio-cursorpill { fill: var(--gt-accent); }
.gt-biografi__svg text.gt-bio-cursorpill-text { fill: #ffffff; font-size: 11px; font-weight: 800; font-variant-numeric: tabular-nums; }

/* staplade rader (etikett över värde) — för meningslånga värden som regelverket */
.gt-rad--stack { display: block; padding: .3rem 0; }
.gt-rad--stack .gt-rad__etikett { display: block; font-size: 10.5px; font-weight: 700;
  letter-spacing: .06em; text-transform: uppercase; }
.gt-rad--stack .gt-rad__varde { display: block; text-align: left; font-weight: 400; }

/* ---------- kartlegend (Fall 3-overlay) ---------- */
.gt-legend { position: absolute; bottom: calc(var(--gt-biografi-hojd, 284px) + 1.1rem); left: 1.1rem; z-index: 39;
  display: flex; gap: .8rem; align-items: center;
  background: var(--gt-yta); border: 1px solid var(--gt-kant); border-radius: 8px;
  box-shadow: var(--gt-skugga); padding: .35rem .7rem; font-size: 12px; }
.gt-legend[hidden] { display: none; }
.gt-legend__prov { display: inline-block; width: 14px; height: 3px; border-radius: 2px;
  margin-right: .35rem; vertical-align: middle; }
@media (max-width: 900px) { .gt-legend { bottom: calc(40px + 1.1rem); } }
`;
}

export function injectStyles(doc = document) {
  if (doc.getElementById(STYLE_ID)) return;
  const style = doc.createElement('style');
  style.id = STYLE_ID;
  style.textContent = cssText();
  doc.head.appendChild(style);
}

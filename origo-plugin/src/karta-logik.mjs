/**
 * Ren kartlogik för Task 4 (fastighetsbiografin, spec §4 "Kartan") — inget
 * Origo/OL-beroende, så den går att testa med `node --test` utan att mocka
 * 'Origo' (till skillnad från geotillsyn.js, som gör den faktiska fit()).
 */

// Kartan ska klara en biografi-strip (296 px) + marginal i botten och
// antingen den öppna panelen (420 px) eller den ihopfällda fliken i höger
// padding — se --gt-panel-bredd/--gt-biografi-hojd i styles.mjs.
export const AUTOZOOM_PADDING_HOGER_OPPEN = 460;
export const AUTOZOOM_PADDING_HOGER_STANGD = 40;
export const AUTOZOOM_PADDING_TOPP = 40;
export const AUTOZOOM_PADDING_VANSTER = 40;
export const AUTOZOOM_PADDING_BOTTEN = 336;
export const AUTOZOOM_DURATION = 400;
// 80 m-fallback runt klickpunkten när ingen overlägggeometri finns att zooma till.
export const AUTOZOOM_FALLBACK_HALV_SIDA = 40;
// Spec §4 "pixelgröt"-spärren: auto-zoom får aldrig gå finare än 0.1 m/px —
// en liten overlägg-extent (t.ex. en smal remsa) ska inte tvinga fram en
// upplösning där kartlagren blir olästbar pixelgröt.
export const AUTOZOOM_MIN_RESOLUTION = 0.1;

/**
 * `minResolution` för `map.getView().fit()` — se AUTOZOOM_MIN_RESOLUTION.
 * Egen funktion (istället för en hårdkodad literal i geotillsyn.js) så att
 * spärren är testbar utan Origo/OL-mock.
 * @returns {number}
 */
export function minResolutionForFit() {
  return AUTOZOOM_MIN_RESOLUTION;
}

/**
 * Padding för `map.getView().fit()` — höger sida beror på om panelen är
 * öppen eller ihopfälld till fliken; botten måste alltid clearance:a
 * biografi-stripen (296 px) plus marginal.
 * @param {boolean} panelOpen
 * @returns {[number, number, number, number]} [topp, höger, botten, vänster]
 */
export function paddingForFit(panelOpen) {
  return [
    AUTOZOOM_PADDING_TOPP,
    panelOpen ? AUTOZOOM_PADDING_HOGER_OPPEN : AUTOZOOM_PADDING_HOGER_STANGD,
    AUTOZOOM_PADDING_BOTTEN,
    AUTOZOOM_PADDING_VANSTER
  ];
}

/**
 * 80 m-fallback-ruta runt en klickpunkt (kartans egen CRS) — används när
 * ingen overlägggeometri kunde ritas (404/fel/inget lov).
 * @param {[number, number]} coordinate
 * @returns {[number, number, number, number]} extent [minX, minY, maxX, maxY]
 */
export function fallbackExtent([x, y]) {
  const h = AUTOZOOM_FALLBACK_HALV_SIDA;
  return [x - h, y - h, x + h, y + h];
}

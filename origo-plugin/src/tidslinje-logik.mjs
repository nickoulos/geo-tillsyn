/**
 * Ren tidslinjelogik: årgångarna är ojämnt fördelade (1960–2023), slidern är
 * proportionell mot årtal och snappar till närmaste tillgängliga årgång —
 * luckorna visas ärligt i stället för att jämnas ut.
 */

export function narmasteAr(years, varde) {
  return years.reduce((best, y) => (Math.abs(y - varde) < Math.abs(best - varde) ? y : best), years[0]);
}

export function stegAr(years, aktuellt, riktning) {
  const i = years.indexOf(aktuellt);
  return years[Math.min(Math.max(i + riktning, 0), years.length - 1)];
}

export function tickPosition(years, ar) {
  const min = years[0];
  const max = years[years.length - 1];
  return max === min ? 0 : ((ar - min) / (max - min)) * 100;
}

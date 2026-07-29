# Geo-Tillsyn v0.5 — UX-redesign: från demopanel till handläggarverktyg

**Datum:** 2026-07-30 · **Status:** Godkänd design
**Motiv:** Muntlig demo väger 70 % i utvärderingen. Dagens UI (flytande vit
låda med årsslider, rå nyckel/värde-text och knappar märkta "Fall 1/3/7")
kommunicerar prototyp, inte produkt. En testperson utan förhandskunskap
förstår inte vad som ska göras eller vad resultatet betyder.

## Mål

En handläggare (eller juryledamot) utan instruktion ska kunna:

1. förstå vad verktyget gör inom 5 sekunder (tom-tillstånd förklarar),
2. klicka på en fastighet och få en läsbar tillsynsrapport,
3. dra i tidslinjen och se både kartbild och regelverk följa med,
4. uppleva kvalitet: typografi, färg, rörelse, felhantering.

## Icke-mål

- Ingen backend-ändring (alla endpoints finns: `/api/olovligt`,
  `/api/lovavvikelse`, `/api/lovavvikelse/geometri`, `/api/strandskydd`).
- Ingen ramverksmigrering — fortsatt vanilla-JS Origo-plugin, samma
  webpack-bygge, `externals: ['Origo']`.
- Ingen ändring av den juridiska ramen: UI:t skriver aldrig ett skuld-ord
  som backend inte skickat; beslutet är alltid handläggarens.

## 1. Layout — dockad sidopanel

- Den flytande bottenlådan tas bort. Pluginet renderar en fullhöjds panel
  (~380 px) dockad till höger i kartvyn (absolut positionerad i
  viewer-elementet, ovanpå kartan; kartan behåller full storlek därunder).
- Panelhuvud: produktnamn "Geo-Tillsyn", kontext "Sundsvall · pilot",
  SV/EN-knapp.
- Panelen kan kollapsas till en smal flik ("‹ Geo-Tillsyn") så kartan kan
  ses i full bredd; verktygsknappen i Origo-navigationen togglar panelen.
- När panelen är öppen analyserar varje kartklick direkt — det separata
  "aktivera identifiera-läge"-steget försvinner.

## 2. Flöde — ett klick, hel granskning

- **Tom-tillstånd:** kort med ikon, "Klicka på en fastighet i kartan så
  granskar Geo-Tillsyn den" + en mening om vad som kontrolleras.
- **Vid klick:** fastighetsbeteckning (GetFeatureInfo, FBET) som rubrik +
  tre kontrollkort med skelett-laddare; de tre anropen körs parallellt
  (`Promise.allSettled`) — ett långsamt anrop blockerar inte de andra:
  - **Byggnad utan lov** ← `/api/olovligt` (radie 100 m)
  - **Avvikelse från bygglov** ← `/api/lovavvikelse` (radie 100 m) +
    `/api/lovavvikelse/geometri` för kartöverlägget
  - **Strandskydd** ← `/api/strandskydd` (radie 150 m)
- "Fall 1/3/7" försvinner helt ur UI:t (behålls som interna nycklar).
- **Kontrollkort:** ikon + klartexttitel + en faktabaserad rubrikrad
  komponerad enbart av fält backend skickat (t.ex. "+90,3 m² (+38,4 %) mot
  godkänt lov"), därunder hopfällbara sektioner **Fakta** (klickbara
  källor), **Bedömning** (»Ej fastställt« där så är), samt osäkerheter i
  bärnstensfärgad notis. Befintliga kurerade fältetiketter (SV/EN) behålls.
  Neutralitetsregel: inga statusord som "OK"/"olagligt" genereras av UI:t;
  om inget kan påvisas skrivs "Se underlag", inte "Inget att anmärka".
- **Sidfot, alltid synlig:** "Beslutet fattas alltid av handläggaren." som
  designat element (inte en textrad i flödet).
- **Fel:** backend nere → vänligt felkort med "Försök igen"-knapp per kort.
  Ingen fastighet på punkten → neutral rad i panelhuvudet, analysen körs
  ändå (punkten är input, inte fastigheten).

## 3. Tidslinje — riktig kartkontroll

- Kompakt flytande "pill" nere i kartytans mitt (justeras när panelen är
  öppen så den inte hamnar under panelen): ‹ › stegknappar, slider med
  tick-markeringar på faktiska fotoår (1960–2023, ojämnt — visas ärligt),
  stor årssiffra.
- Regelkontexten (Lag / Lovbefrielser / Strandskydd / Preskription vid valt
  datum) flyttar till en expanderbar "Regelverk YYYY"-sektion i pillen:
  en sammanfattningsrad hopfälld, full detalj vid expandering.
- Samma beteende som idag i sak: slidern byter synligt ortofotolager och
  omvärderar regelmodellen (`regler.json`-evaluatorn oförändrad).

## 4. Visuellt system

- En injicerad stylesheet (`<style>` från bundlen, design-tokens som
  CSS-variabler) ersätter alla inline-stilar.
- Tokens: systemtypsnittsstack, djupblå accent (≈ #1e4ed8), neutrala
  gråtoner, 8 px radie, diskreta kanter/skuggor, statusbadges,
  fokusmarkeringar, 150 ms transitions.
- Kartöverlägg Fall 3: behåller blå (godkänt) / röd (verkligt) med
  matchande legend-chip på kartan.

## 5. Teststrategi

- `npm run build` (webpack.prod) grönt + `node --check` på bundlen.
- Manuell verifiering i webbläsare mot live backend (`:8464`) och demo-
  servern (`:9967`): tom-tillstånd, klick på ALNÖ-USLAND 1:45, alla tre
  kort, overlay + legend, tidslinje, SV/EN, kollaps, felkort med backend
  avstängd.
- Backendens 130 hermetiska tester berörs inte.

## Öppna punkter

Inga — design godkänd av beställaren 2026-07-30.

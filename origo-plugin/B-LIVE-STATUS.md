# B-live — status och körning

**Datum:** 2026-07-23 · **Status:** Kopplat och verifierat till den grad som är
möjlig utan mänsklig webbläsarinteraktion. Screencast görs manuellt.

## v0.7 Fastighetsbiografi (2026-08-20)

"Tesen som en bild" (se `docs/superpowers/specs/2026-08-19-fastighetsbiografi-design.md`):
tidslinjepillen är borttagen och ersatt av en **biografi-strip** under
kartan, panelen visar **fynden först**, och kartan berättar (auto-zoom,
klickmarkör, skrafferat överlägg). Körinstruktionerna i "Kör demot" nedan
gäller oförändrat.

- **Backend (additivt):** `narvaro_per_ar`/`uteslutna_ar` på `/api/olovligt`,
  `vald_byggnad_id` + vald träff först i `traffar` på `/api/strandskydd`,
  nytt `GET /api/strandskydd/geometri` (radar-lite, aldrig ett MCP-verktyg).
- **Biografi-strip** (`src/biografi.js` + `src/biografi-logik.mjs`, ersätter
  `timeline.js`): fyra spår — **Verklighet** (ortofotohistorik per årgång),
  **Register & lov** (BAL-registret mot dateringsintervallet, "avviker"-gap
  endast vid `bal_forenligt === false`), **Rättighet** (lagregim +
  lovbefrielser i två rader + strandskydd, ur `regler.json`) och **Klockor**
  (rättelse/sanktion/strandskydd-preskription, endast efter klick) — över en
  gemensam 1960→innevarande år+1-axel. Cursor-drag/klick snappar till
  närmaste ortofotoårgång.
- **Panelen (fynden först):** sammanfattningschips (ett per kontroll, med
  *underlagsläge* — aldrig ett utfall), display-rubriker (22 px/800,
  t.ex. **+90,3 m²**) med underrad, en osäkerhetschip i stället för en öppen
  bärnstensvägg, strandskyddskortet ur fastighetsperspektiv (`vald_byggnad_id`)
  med kandidatrad, ett eget **Beslut**-block med avsiktligt tomt fält.
- **Kartan berättar:** auto-zoom till Fall 3-överlägget (eller en 80 m-ruta)
  med klicktoken (skyddar mot kapplöpning vid snabba omklick), klickmarkör,
  fyllt skrafferat överlägg, automatisk zonlager-toggle vid strandskyddsträff.
- **Visuell polish (task 6):** lovbefrielsestaplarna (friggebod/attefallshus/
  komplementbostadshus/komplementbyggnad) har nu en 1 px vit rand mellan
  intilliggande perioder och en kortare etikett ("attefall 25") när den fulla
  texten ("attefallshus 25 m²") inte får plats i stapeln — tidigare syntes
  ingen text alls på attefall-raden, bara en dold title-tooltip.
- **Verifieringssele:** `demo/autoklick.html` (se README.md) — headless
  Chrome 1600×900, fyra körningar granskade av människa/Fable: tomläge,
  komplementbyggnaden, huvudbyggnaden (+90,3 m² · +38,4 %), EN-läge
  (UI-chrome översatt, lagrum/SFS/MÖD-referenser kvar på svenska).
- 87/87 `npm test` gröna efter task 6-ändringarna; `npm run build` grön,
  `node --check build/js/geotillsyn.min.js` ren.
- En separat Tillsynsradar ("Skanna vyn"-knappen i panelhuvudet) tillkom i en
  annan session — se radar-dokumentationen för dess status, inte beskriven
  här.

## v0.5 UX-redesign (2026-07-30)

Handläggar-UX i stället för demopanel — samma backend, samma endpoints:

- **Dockad sidopanel** (höger, fullhöjd, kollapsbar till flik) med
  produktidentitet, tomläge som förklarar verktyget, SV/EN-knapp och alltid
  synlig fot: "Beslutet fattas alltid av handläggaren."
- **Ett klick, hel granskning:** fallväljaren "Fall 1/3/7" är borta. Ett
  kartklick kör `/api/olovligt`, `/api/lovavvikelse` (+ geometri-overlay)
  och `/api/strandskydd` parallellt och renderar tre kontrollkort
  ("Byggnad utan lov", "Avvikelse från bygglov", "Strandskydd") med neutral
  faktarubrik, hopfällbar Fakta (klickbara källor), öppen Bedömning och
  bärnstensfärgade osäkerheter. 404 = ärligt "hittades inte"-info; nätfel =
  felkort med "Försök igen" per kort.
- **Tidslinjepill** nere i kartytan: ‹ ›-steg, proportionell slider som
  snappar till de 18 faktiska fotoårgångarna (luckorna syns som ticks),
  expanderbar "Regelverk"-rad (sammanfattning + detalj ur regler.json).
- **Kartlegend** för Fall 3-överlägget (godkänt blått / verkligt rött).
- **Injicerad design-token-stylesheet** — inga inline-stilar.
- Källkoden är uppdelad i moduler (`i18n.mjs`, `dossier.mjs`,
  `regelverk.mjs`, `tidslinje-logik.mjs`, `styles.mjs`, `panel.js`,
  `timeline.js`); de rena modulerna testas med `npm test` (node --test).

Körinstruktionerna nedan gäller oförändrat.

## Vad som är gjort

Origo-pluginet (`src/geotillsyn.js`) är kopplat till geo-tillsyn-serverns
REST-seam så att ett kartklick kör en live tillsynsanalys och ritar Fall 3-
överlägget (godkänt läge blått, verkligt läge rött) på kartan.

- **Backend REST-seam** (`src/geo_tillsyn/server.py`, `@mcp.custom_route`, CORS):
  `/api/olovligt` (Fall 1), `/api/lovavvikelse` (Fall 3),
  `/api/strandskydd` (Fall 7), `/api/lovavvikelse/geometri` (GeoJSON för
  överlägget), `/api/health`. MCP-verktygen är oförändrade — Eneo-vägen
  regresserar inte. 130 hermetiska tester gröna.
- **Plugin** hämtar kompakt JSON, renderar dossiern i tre nivåer
  (Fakta med klickbara källor / Bedömning med »Ej fastställt« / Beslut =
  "Beslutet fattas av handläggaren") och ritar Fall 3-överlägget.
- **EPSG:3014** registreras via demo-configens `proj4Defs` (Origo kör
  `registerProjections` vid start) → överläggets GeoJSON (3014) reprojiceras
  korrekt till kartprojektionen (3006).

## Verifierat (2026-07-23)

- Bundle byggd (`npx webpack --config tasks/webpack.prod.js`), `node --check`
  ren, refererar alla fyra endpoints + `EPSG:3014` + `readFeatures`.
- Demo-sidan + alla assets (origo.js, css, geotillsyn.json, regler.json,
  plugin-bundle) serveras på `localhost:9967`.
- REST-seam live på `:8464`: `/api/health` → `{"status":"ok","tools":4}`;
  `/api/lovavvikelse` på protagonisten → +90,3 m² (+38,4 %);
  `/api/lovavvikelse/geometri` → GeoJSON-polygoner för godkänt + verkligt läge.
- CORS verifierat från webbläsarens origin (`localhost:9967`):
  `Access-Control-Allow-Origin: *`, OPTIONS-preflight → 204.

## Kör demot (för screencast)

1. `geo-tillsyn-mcp --host 0.0.0.0 --port 8464` (tesseract i PATH för OCR).
2. Servera pluginets `build/`-katalog på `localhost:9967`
   (`npx http-server build -p 9967 -c-1 --cors`), eller kör
   `npm start` i `origo-plugin/` (webpack-dev-server, port 9967).
3. Öppna `http://localhost:9967/index.html`, aktivera identifieringsknappen,
   välj fall i panelen, klicka protagonistfastigheten (ALNÖ-USLAND 1:45,
   kartan startar centrerad på Alnö). Fall 3 ritar blått/rött överlägg.

## Kvar (mänskligt)

- Faktisk webbläsarkörning + screencast (kräver mänsklig interaktion; all
  kod-/nätverksväg är verifierad).
- Byt ut `apiUrl` mot demo-värdens adress om servern inte kör på localhost.

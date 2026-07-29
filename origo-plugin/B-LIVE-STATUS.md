# B-live — status och körning

**Datum:** 2026-07-23 · **Status:** Kopplat och verifierat till den grad som är
möjlig utan mänsklig webbläsarinteraktion. Screencast görs manuellt.

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

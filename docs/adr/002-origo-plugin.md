# ADR-002: Origo-plugin som fristående UMD-bundle enligt barebone-mönstret

**Datum:** 2026-07-02 · **Status:** Accepterad

## Kontext

Spike B granskade Origo (origo-map/origo, klonad 2026-07-02) och det officiella
exempel-pluginet (origo-map/barebone-plugin) för att fastställa hur
Geo-Tillsyns handläggargränssnitt integreras.

Fynd:

- **Pluginmodellen är enkel och stabil**: ett plugin är en fristående
  JS-bundle (webpack, `externals: ['Origo']`) som exporterar en fabrik som
  returnerar `Origo.ui.Component` med livscykel `onInit`/`onAdd`/`render`.
- **Laddning utan att forka Origo**: värdsidan inkluderar `origo.js` + plugin-
  bundlen och kör `origo.on('load', viewer => viewer.addComponent(plugin))`.
  Ingen ändring i Origo-kärnan krävs — helt i linje med anbudets löfte.
- **API-yta som räcker för oss**: `viewer.getMap()` ger OpenLayers-kartan
  (klickhändelser, lager), `viewer.getProjection()` ger CRS,
  `Origo.ui.{Button,Modal,dom}` ger UI-primitiver; OL-versionen i kärnan
  återanvänds (inga egna karta-beroenden).
- **Befintligt Swiper-plugin (SigtunaGIS)** jämför två kartvyer — kandidat som
  grund/inspiration för blink-komparatorn i tidslinjen i stället för nybygge.
- Origos dev-miljö kör på Node (verifierat med Node 24 + npm 11 lokalt);
  barebone-pluginets sass-kedja (node-sass 9) är föråldrad — vi använder
  webpack utan node-sass.

## Beslut

1. Geo-Tillsyn-pluginet byggs som **fristående UMD-bundle enligt
   barebone-mönstret** (`origo-plugin/` i monorepot): egen webpack-konfig,
   `externals: ['Origo']`, ingen fork av Origo.
2. Panelen börjar som `Origo.ui`-komponenter (Sprint 2); väljer vi senare ett
   ramverk för dossier-/tidslinjevyn är valet fritt (Q&A 150436 F10 — React
   accepteras), men Origo-kärnans primitiver prövas först.
3. Kartinteraktion via OL-kartan från `viewer.getMap()`; punktuppslag mot
   GeoServer görs med **GetFeatureInfo-mönstret från Spike C** (WMS 1.3.0,
   axelordning N,E för EPSG:300x).
4. Utvärdera Swiper-pluginet som bas för årsjämförelsen innan egen
   implementation (rule of three).

## Konsekvenser

- Hello-world-skelett finns i `origo-plugin/src/geotillsyn.js` (knapp →
  klick → fastighetsbeteckning i modal) med webpack-tasks.
- Pluginet kan installeras av valfri Origo-kommun utan Geo-Tillsyn-backend —
  men fulla flödet (dossier) kräver Eneo-assistenten (Sprint 2).
- Kvarstår (Sprint 1-live): köra pluginet i lokal Origo-instans med Sundsvalls
  lagerkonfiguration och ta screencast till fredagsdemon.

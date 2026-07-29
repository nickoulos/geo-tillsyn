# origo-plugin

Handläggargränssnittet som plugin till [Origo](https://github.com/origo-map/origo),
byggt enligt [barebone-mönstret](https://github.com/origo-map/barebone-plugin)
(fristående bundle, `externals: ['Origo']`, ingen fork). Se
[ADR-002](../docs/adr/002-origo-plugin.md).

**Nuläge (v0.5):** dockad sidopanel med ett-klicks granskning — ett kartklick
kör alla tre kontrollerna (`/api/olovligt`, `/api/lovavvikelse`,
`/api/strandskydd`) parallellt och renderar kontrollkort med neutral rubrik,
Fakta/Bedömning/Källor och osäkerheter; tidslinjepill med regelverks-expander;
Fall 3-överlägg (godkänt/verkligt läge) med kartlegend; SV/EN.
Se `B-LIVE-STATUS.md` för körning och `npm test` för de rena modulerna.

## Utveckling

```bash
npm install
npm run build        # -> build/js/geotillsyn.min.js
```

## Användning i Origo

```html
<script src="js/origo.js"></script>
<script src="plugins/geotillsyn.min.js"></script>
<script>
  var origo = Origo('index.json');
  origo.on('load', function (viewer) {
    viewer.addComponent(GeoTillsyn({
      owsUrl: 'https://karta.sundsvall.se/geoserver/ows',
      fastighetLayer: 'SundsvallsKommun:Fastighet_yta'
    }));
  });
</script>
```

Lokal Origo-dev: klona `origo-map/origo` som syskonkatalog, `npm install`,
`npm start` (webpack-dev-server). Lägg bundlen i Origos `plugins/`-katalog
eller peka på dev-serverns build.

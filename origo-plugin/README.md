# origo-plugin

Handläggargränssnittet som plugin till [Origo](https://github.com/origo-map/origo),
byggt enligt [barebone-mönstret](https://github.com/origo-map/barebone-plugin)
(fristående bundle, `externals: ['Origo']`, ingen fork). Se
[ADR-002](../docs/adr/002-origo-plugin.md).

**Nuläge (Spike B):** hello-world — knapp i navigationen som togglar
"identifiera fastighet"-läge; klick på kartan → GetFeatureInfo mot
`karta.sundsvall.se` → fastighetsbeteckning i modal.
Kommande: dossier-vy (Sprint 2), tidslinje (Sprint 3), regelgraf-vy (Sprint 5).

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

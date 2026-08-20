# origo-plugin

Handläggargränssnittet som plugin till [Origo](https://github.com/origo-map/origo),
byggt enligt [barebone-mönstret](https://github.com/origo-map/barebone-plugin)
(fristående bundle, `externals: ['Origo']`, ingen fork). Se
[ADR-002](../docs/adr/002-origo-plugin.md).

**Nuläge (v0.7 — Fastighetsbiografi):** dockad sidopanel med ett-klicks
granskning — ett kartklick kör alla tre kontrollerna (`/api/olovligt`,
`/api/lovavvikelse`, `/api/strandskydd`) parallellt och renderar
fynden-först-kort (sammanfattningschips, display-rubriker, osäkerhetschip,
strandskydd ur fastighetsperspektiv, ett eget Beslut-block); biografi-strip
(`biografi.js`) under kartan ersätter den gamla tidslinjepillen med fyra spår
— Verklighet/Register & lov/Rättighet/Klockor — över en gemensam 1960–2027-
axel; kartan auto-zoomar och sätter en klickmarkör vid granskning; SV/EN.
Se `B-LIVE-STATUS.md` för körning, `npm test` för de rena modulerna och
avsnittet **Verifieringssele** nedan för headless-skärmdumpar.

## Utveckling

```bash
npm install
npm run build        # -> build/js/geotillsyn.min.js
npm test              # node --test för de rena modulerna
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

## Verifieringssele (`demo/autoklick.html`)

`demo/autoklick.html` är samma bootstrapping som `index.html`, men avsedd för
headless-verifiering: den centrerar kartan och skickar ett `singleclick`
automatiskt (~2,5 s + 1,5 s efter sidladdning) i stället för att vänta på en
mus. Ingår **inte** i webpack-bundlen — kopiera in den i `build/` innan en
headless-körning:

```bash
npm run build
cp build/js/geotillsyn.min.js build/plugins/geotillsyn.min.js
cp demo/autoklick.html build/autoklick.html
npx http-server build -p 9967 -c-1 --cors   # eller motsvarande statisk server
```

Query-parametrar:

- `?e=&n=` — klickpunkt i SWEREF 99 TM / EPSG:3006 (default: komplement-
  byggnaden E 624526.3 N 6917930.0).
- `?lang=en` — klickar språkknappen (`.gt-sprak`) direkt efter sidladdning,
  innan kartklicket, så hela flödet renderas på engelsk UI-text (lagrum/SFS
  förblir svenska — se `i18n.mjs`).

Exempel (huvudbyggnaden, headless Chrome, 1600×900):

```bash
chrome --headless=new --window-size=1600,900 --timeout=150000 \
  --virtual-time-budget=150000 \
  --screenshot=komplement.png \
  "http://localhost:9967/autoklick.html?e=624518.2&n=6917923.3"
```

`?radar=1` hanteras medvetet inte här — tillsynsradarns egen verifieringsväg
(`radar.mjs`) ägs av en annan del av arbetet; se radar-dokumentationen för den.

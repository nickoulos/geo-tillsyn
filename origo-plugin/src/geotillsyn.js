import Origo from 'Origo';
import { TEXTS, meddelandeText } from './i18n.mjs';
import { composeHeadline, renderCheckBody, escapeHtml } from './dossier.mjs';
import { renderKontextDetalj } from './regelverk.mjs';
import { renderRadarLista, renderRadarRubrik, bboxFranExtent } from './radar.mjs';
import { injectStyles } from './styles.mjs';
import { skapaPanel } from './panel.js';
import { skapaBiografi } from './biografi.js';

/**
 * Geo-Tillsyn Origo plugin.
 *
 * v0.2 — Tidslinje: a year slider that (1) switches the visible orthophoto
 * layer and (2) shows the legal context in force at that date, evaluated from
 * the same versioned rule model (regler.json) as mcp-regelverk.
 *
 * v0.3 — Språk: SV/EN toggle. Only the UI chrome (our own labels) is
 * translated; statutory names from regler.json (SFS titles, "friggebod",
 * lagrum) are official Swedish terms and stay verbatim in both languages.
 *
 * v0.6 — Språk, hela vägen: backendens osäkerheter, åtgärder, källbeskrivningar
 * och felmeddelanden kom tidigare som färdiga svenska meningar och överlevde
 * därför EN-läget oöversatta. `/api/*` skickar dem nu som `{kod, params}`
 * (src/geo_tillsyn/meddelanden.py) och i18n.mjs renderar dem — språkbytet
 * kräver ingen ny hämtning, och även info-/felkort renderas om. Uppräknade
 * värden (`laege`, korsjämförelsens utfall) översätts via VARDE_LABEL.
 * MCP-verktygens (Eneo) kontrakt är oförändrat: de får kvar ren svenska.
 *
 * v0.4 — B-live: kopplar pluginet till geo-tillsyn REST-backend
 * (src/geo_tillsyn/server.py). Beslutet är alltid handläggarens — pluginet
 * skriver aldrig ett skuld-ord som backend inte skickat.
 *
 * v0.5 — UX-redesign: den flytande bottenpanelen ersätts av en dockad
 * fullhöjds sidopanel (src/panel.js) och en tidslinjepill (src/timeline.js).
 * "Fall 1/3/7"-väljaren är borta: ett kartklick kör alla tre kontrollerna
 * parallellt och renderar ett kontrollkort per check med neutral rubrik
 * (src/dossier.mjs). Stilarna injiceras som design-tokens (src/styles.mjs).
 * Fall 3-överlägget (godkänt blått / verkligt rött) får en kartlegend.
 *
 * v0.7 — Tillsynsradar: "Skanna vyn" kör samma motor över hela den synliga
 * kartvyn (`/api/radar?bbox=`) och renderar en rangordnad kandidatlista
 * (src/radar.mjs) med numrerade markörer i kartan; klick på en kandidat
 * hoppar dit och kör den vanliga ett-klicks-granskningen. Poängmodellen är
 * backendens och redovisas öppet; listan är kandidater — handläggaren beslutar.
 */

const DEFAULT_ARSLAGER = {
  1960: 'Lantmateriet:HistoriskaOrtofoton1960_wms',
  1975: 'Lantmateriet:HistoriskaOrtofoton1975_wms',
  1998: 'Lantmateriet:HistoriskaOrtofoton1998_wms',
  1999: 'Lantmateriet:HistoriskaOrtofoton1999_wms',
  2001: 'Lantmateriet:HistoriskaOrtofoton2001_wms',
  2002: 'Lantmateriet:HistoriskaOrtofoton2002_wms',
  2007: 'Lantmateriet:Orto2007_wms',
  2010: 'Lantmateriet:Orto2010_wms',
  2011: 'Lantmateriet:Orto2011_wms',
  2012: 'Lantmateriet:Orto2012_wms',
  2013: 'Lantmateriet:Orto2013_wms',
  2015: 'Lantmateriet:Orto2015_wms',
  2016: 'Lantmateriet:Orto2016_wms',
  2017: 'Lantmateriet:Orto2017_wms',
  2019: 'Lantmateriet:Orto2019_wms',
  2020: 'Lantmateriet:Orto2020_wms',
  2021: 'Lantmateriet:Orto2021_wms',
  2023: 'Lantmateriet:Orto2023_wms'
};

// EPSG:3014 = SWEREF99 17 15 (kommunlagrens CRS på karta.sundsvall.se);
// backend-koordinaterna är alltid 3014, kartprojektionen i geotillsyn.json är
// 3006 — pluginet måste registrera 3014 hos proj4 innan Origo.ol.proj.transform
// (eller GeoJSON-läsningen) kan konvertera mellan dem.
const EPSG_3014_DEF = '+proj=tmerc +lat_0=0 +lon_0=17.25 +k=1 +x_0=150000 +y_0=0 '
  + '+ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs';

// Ett kartklick kör alla tre kontrollerna parallellt — inget fall-val i UI:t.
const CHECKS = [
  { key: 'olovligt', path: '/api/olovligt', radie: 100 },
  { key: 'lovavvikelse', path: '/api/lovavvikelse', radie: 100 },
  { key: 'strandskydd', path: '/api/strandskydd', radie: 150 }
];

// Overlay-färgerna (godkänt/verkligt läge) delas av kartlagret och legenden.
const FARG_GODKANT = 'rgba(40,80,255,1)';
const FARG_VERKLIG = 'rgba(230,40,40,1)';

const GeoTillsyn = function GeoTillsyn(options = {}) {
  const {
    owsUrl = 'https://karta.sundsvall.se/geoserver/ows',
    fastighetLayer = 'SundsvallsKommun:Fastighet_yta',
    fbetProperty = 'FBET',
    arslager = DEFAULT_ARSLAGER,
    reglerUrl = 'regler.json',
    startAr = 2023,
    sprak = 'sv',
    apiUrl = 'http://localhost:8464'
  } = options;

  const icon = '#ic_search_24px';
  const years = Object.keys(arslager).map(Number).sort((a, b) => a - b);
  let button;
  let viewer;
  let target;
  let regler = null;
  let panel = null;
  let biografi = null;
  let legendEl = null;
  let aktivtSprak = TEXTS[sprak] ? sprak : 'sv';
  let aktuelltAr = startAr;
  let kollapsad = false;
  let senastePunkt3014 = null;
  const senasteData = {};
  // Kortens info-/felläge sparas som backend skickade det ({kod, params} eller
  // ren text) så att språkväxlingen kan rendera om även dem — ett 404-svar är
  // lika mycket innehåll som ett resultat.
  const senasteStatus = {};
  let overlayLayer = null;
  let radarLayer = null;
  let senasteRadar = null;
  let radarTimers = [];

  function t() {
    return TEXTS[aktivtSprak];
  }

  /* --- Origo.ol-åtkomst: guarda mot avsaknad, krascha aldrig kartan --- */

  function getOl() {
    const ol = (Origo && Origo.ol) || (typeof window !== 'undefined' && window.ol) || null;
    if (!ol) {
      console.error('geotillsyn: hittar varken Origo.ol eller window.ol — '
        + 'REST-analysens karta-overlay kan inte ritas.');
    }
    return ol;
  }

  // Kontrollerar att EPSG:3014 (SWEREF99 17 15) går att projicera till/från.
  // Normalvägen är att Origo registrerar den åt oss: `proj4Defs` i kartkonfigu-
  // rationen körs genom `registerProjections` vid start. Origos UMD-bundle
  // exponerar däremot INTE `ol.proj` (bara geom/format/layer/source/style/...),
  // så vi kan varken läsa proj4-instansen eller fråga `ol.proj.get` — därför
  // verifieras registreringen med en riktig omprojektion i stället för en
  // API-koll. Saknas proj4Defs helt loggas ett tydligt fel och pluginet
  // fortsätter utan krasch, men klick-analysen och Fall 3-overlayen uteblir.
  let epsg3014Registrerad = false;
  function projicera(coordinate, from, till) {
    const ol = getOl();
    if (!ol) return null;
    if (ol.proj && typeof ol.proj.transform === 'function') {
      return ol.proj.transform(coordinate, from, till);
    }
    // GeoJSON-formatet gör samma omprojektion som ol.proj.transform, och är
    // det enda som Origo faktiskt exponerar.
    const obj = new ol.format.GeoJSON().writeGeometryObject(
      new ol.geom.Point(coordinate),
      { featureProjection: from, dataProjection: till }
    );
    return obj && obj.coordinates ? obj.coordinates : null;
  }

  function registreraEpsg3014() {
    const ol = getOl();
    if (!ol) return false;

    // Egen registrering först, om proj4 mot förmodan är exponerad.
    const proj4 = (ol.proj && ol.proj.proj4) || (typeof window !== 'undefined' && window.proj4) || null;
    if (proj4 && typeof proj4.defs === 'function') {
      try {
        proj4.defs('EPSG:3014', EPSG_3014_DEF);
      } catch (err) {
        console.error('geotillsyn: kunde inte registrera EPSG:3014 hos proj4', err);
      }
    }

    // Verifiera med en omprojektion: en okänd projektion ger antingen ett
    // undantag eller oförändrade koordinater — båda betyder "ej registrerad".
    try {
      const from = viewer.getProjection().getCode();
      const provpunkt = viewer.getMap().getView().getCenter();
      const ut = projicera(provpunkt, from, 'EPSG:3014');
      epsg3014Registrerad = !!ut
        && (Math.abs(ut[0] - provpunkt[0]) > 1 || Math.abs(ut[1] - provpunkt[1]) > 1);
    } catch (err) {
      epsg3014Registrerad = false;
    }

    if (!epsg3014Registrerad) {
      console.error('geotillsyn: EPSG:3014 är inte registrerad i kartan — lägg till den '
        + 'under `proj4Defs` i kartkonfigurationen. Klick-analys och Fall 3-overlay '
        + 'kommer inte fungera.');
    }
    return epsg3014Registrerad;
  }

  function buildGetFeatureInfoUrl(coordinate, crsCode, half = 40) {
    const [e, n] = coordinate;
    const params = new URLSearchParams({
      service: 'WMS',
      version: '1.3.0',
      request: 'GetFeatureInfo',
      layers: fastighetLayer,
      query_layers: fastighetLayer,
      crs: crsCode,
      bbox: `${n - half},${e - half},${n + half},${e + half}`,
      width: '81',
      height: '81',
      i: '40',
      j: '40',
      info_format: 'application/json',
      propertyName: fbetProperty,
      feature_count: '1'
    });
    return `${owsUrl}?${params.toString()}`;
  }

  async function identify(evt) {
    const crsCode = viewer.getProjection().getCode();
    const url = buildGetFeatureInfoUrl(evt.coordinate, crsCode);
    try {
      const resp = await fetch(url);
      const json = await resp.json();
      const feat = json.features && json.features[0];
      panel.setFastighet(feat ? (feat.properties[fbetProperty] || null) : null);
    } catch (err) {
      console.error('geotillsyn: GetFeatureInfo failed', err);
      panel.setFastighet(null);
    }
  }

  /* --- REST-analys: klick -> 3006->3014 -> alla /api/* parallellt --- */

  function transformTill3014(coordinate) {
    const ol = getOl();
    if (!ol || !epsg3014Registrerad) return null;
    const from = viewer.getProjection().getCode();
    try {
      return projicera(coordinate, from, 'EPSG:3014');
    } catch (err) {
      console.error('geotillsyn: koordinattransform till EPSG:3014 misslyckades', err);
      return null;
    }
  }

  function clearOverlay() {
    if (overlayLayer) overlayLayer.getSource().clear();
  }

  function visaLegend(visa) {
    if (!legendEl) return;
    legendEl.hidden = !visa;
    if (visa) {
      legendEl.innerHTML =
        `<span><span class="gt-legend__prov" style="background:${FARG_GODKANT}"></span>${escapeHtml(t().godkantLage)}</span>`
        + `<span><span class="gt-legend__prov" style="background:${FARG_VERKLIG}"></span>${escapeHtml(t().verkligtLage)}</span>`;
    }
  }

  // Ritar godkänt (blått) och verkligt (rött) läge från /api/lovavvikelse/geometri.
  // Reprojicerar EPSG:3014 -> kartans projektion via ol.format.GeoJSON, som
  // kräver att EPSG:3014 är registrerad hos proj4 (registreraEpsg3014 ovan).
  function ritaFall3Overlay(geometriData) {
    const ol = getOl();
    clearOverlay();
    visaLegend(false);
    if (!ol || !overlayLayer) return;
    if (!geometriData.lov_hittat) return;
    if (!epsg3014Registrerad) {
      console.error('geotillsyn: EPSG:3014 ej registrerad — Fall 3-overlay ritas inte.');
      return;
    }

    const featureProjection = viewer.getProjection().getCode();
    const format = new ol.format.GeoJSON();
    const lager = [
      { geom: geometriData.godkant_lage, farg: FARG_GODKANT, etikett: t().godkantLage },
      { geom: geometriData.verkligt_lage, farg: FARG_VERKLIG, etikett: t().verkligtLage }
    ];

    let nagotRitat = false;
    lager.forEach(({ geom, farg, etikett }) => {
      if (!geom) return;
      let features;
      try {
        features = format.readFeatures(
          { type: 'Feature', geometry: geom, properties: {} },
          { dataProjection: 'EPSG:3014', featureProjection }
        );
      } catch (err) {
        console.error('geotillsyn: kunde inte läsa/reprojicera overlay-geometri', err);
        return;
      }
      features.forEach((feature) => {
        feature.setStyle(new ol.style.Style({
          stroke: new ol.style.Stroke({ color: farg, width: 3 }),
          fill: new ol.style.Fill({ color: farg.replace(',1)', ',0.08)') }),
          text: new ol.style.Text({
            text: etikett,
            font: 'bold 12px sans-serif',
            fill: new ol.style.Fill({ color: farg }),
            stroke: new ol.style.Stroke({ color: 'rgba(255,255,255,0.9)', width: 3 }),
            offsetY: -8
          })
        }));
      });
      overlayLayer.getSource().addFeatures(features);
      if (features.length) nagotRitat = true;
    });
    visaLegend(nagotRitat);
  }

  async function hamtaFall3Geometri(e3014, n3014, radie) {
    const url = `${apiUrl}/api/lovavvikelse/geometri?easting=${encodeURIComponent(e3014)}`
      + `&northing=${encodeURIComponent(n3014)}&radie_m=${encodeURIComponent(radie)}`;
    try {
      const resp = await fetch(url);
      const json = await resp.json();
      if (!resp.ok) {
        console.error('geotillsyn: /api/lovavvikelse/geometri gav fel', json);
        return;
      }
      ritaFall3Overlay(json);
    } catch (err) {
      console.error('geotillsyn: fetch mot /api/lovavvikelse/geometri misslyckades', err);
    }
  }

  function renderaKort(key) {
    const status = senasteStatus[key];
    if (status) {
      const text = status.text !== undefined
        ? meddelandeText(status.text, aktivtSprak)
        : `${t().felHamtning}${status.suffix || ''}`;
      if (status.typ === 'info') panel.setCardInfo(key, text);
      else panel.setCardError(key, text);
      return;
    }
    const data = senasteData[key];
    if (!data) return;
    panel.setCardResult(key, {
      headline: composeHeadline(key, data, t(), aktivtSprak),
      body: renderCheckBody(data, t(), aktivtSprak)
    });
  }

  // Ett kort kan bara vara i ett läge — sätt status och rendera via renderaKort,
  // så att språkväxlingen tar samma väg som förstagångsrenderingen.
  function visaStatus(key, status) {
    delete senasteData[key];
    senasteStatus[key] = status;
    renderaKort(key);
    uppdateraBiografiData();
  }

  // Träffen i /api/strandskydd som gäller den klickade byggnaden — den enda
  // träff biografins Klockor-spår får rita en strandskyddsklocka för.
  function valdStrandskyddTraff() {
    const ss = senasteData.strandskydd;
    if (!ss || !ss.traffar || ss.vald_byggnad_id == null) return null;
    return ss.traffar.find((traff) => traff.byggnad_id === ss.vald_byggnad_id) || null;
  }

  // Biografi-stripen ritar om varje gång ett kort sätter/rensar sin data —
  // partiell data (t.ex. bara olovligt hunnit svara) är fine: stripen ritar
  // det underlag den har.
  function uppdateraBiografiData() {
    if (!biografi) return;
    biografi.setData({
      olovligt: senasteData.olovligt || null,
      lovavvikelse: senasteData.lovavvikelse || null,
      strandskyddTraff: valdStrandskyddTraff()
    });
  }

  async function korOchRendera(check, [e3014, n3014]) {
    delete senasteStatus[check.key];
    panel.setCardLoading(check.key);
    let data;
    let status = 0;
    try {
      const url = `${apiUrl}${check.path}?easting=${encodeURIComponent(e3014)}`
        + `&northing=${encodeURIComponent(n3014)}&radie_m=${encodeURIComponent(check.radie)}`;
      const resp = await fetch(url);
      status = resp.status;
      data = await resp.json();
    } catch (err) {
      console.error(`geotillsyn: ${check.path} misslyckades`, err);
      visaStatus(check.key, { typ: 'fel' });
      return;
    }
    if (status === 404 && data && data.fel) {
      // Ärligt "hittades inte"-svar (ingen byggnad/inget lov) — info, inte fel.
      visaStatus(check.key, { typ: 'info', text: data.fel });
      if (check.key === 'lovavvikelse') {
        clearOverlay();
        visaLegend(false);
      }
      return;
    }
    if (status >= 400) {
      visaStatus(check.key, {
        typ: 'fel',
        text: (data && data.fel) || `HTTP ${status}`
      });
      return;
    }
    senasteData[check.key] = data;
    renderaKort(check.key);
    uppdateraBiografiData();
    if (check.key === 'lovavvikelse') {
      if (data.lov_hittat) {
        hamtaFall3Geometri(e3014, n3014, check.radie);
      } else {
        clearOverlay();
        visaLegend(false);
      }
    }
  }

  /* --- snedbilder (MapSpace) via backend-proxy: /api/snedbild + /api/snedbild/bild --- */

  let senasteSnedbilder = null;

  function snedbildBildUrl([e3014, n3014]) {
    return (riktning, datum) => `${apiUrl}/api/snedbild/bild?easting=${encodeURIComponent(e3014)}`
      + `&northing=${encodeURIComponent(n3014)}&riktning=${encodeURIComponent(riktning)}`
      + (datum ? `&datum=${encodeURIComponent(datum.replace(/-/g, ''))}` : '');
  }

  function renderaSnedbilder() {
    if (!senastePunkt3014) return;
    if (senasteSnedbilder === 'fel') { panel.setSnedbilderInfo(t().snedbildFel); return; }
    if (senasteSnedbilder) panel.setSnedbilder(senasteSnedbilder, snedbildBildUrl(senastePunkt3014));
  }

  async function hamtaSnedbilder([e3014, n3014]) {
    panel.setSnedbilderLoading();
    senasteSnedbilder = null;
    try {
      const url = `${apiUrl}/api/snedbild?easting=${encodeURIComponent(e3014)}`
        + `&northing=${encodeURIComponent(n3014)}`;
      const resp = await fetch(url);
      const json = await resp.json();
      if (!resp.ok) {
        senasteSnedbilder = 'fel';
      } else {
        senasteSnedbilder = json;
      }
    } catch (err) {
      console.error('geotillsyn: /api/snedbild misslyckades', err);
      senasteSnedbilder = 'fel';
    }
    renderaSnedbilder();
  }

  /* --- tillsynsradar: skanna synlig vy -> /api/radar -> lista + markörer --- */

  function rensaRadarMarkorer() {
    radarTimers.forEach(clearTimeout);
    radarTimers = [];
    if (radarLayer) radarLayer.getSource().clear();
  }

  function radarMarkorStil(ol, rang) {
    return new ol.style.Style({
      image: new ol.style.Circle({
        radius: 11,
        fill: new ol.style.Fill({ color: 'rgba(30,78,216,0.92)' }),
        stroke: new ol.style.Stroke({ color: '#fff', width: 2 })
      }),
      text: new ol.style.Text({
        text: String(rang),
        font: 'bold 11px sans-serif',
        fill: new ol.style.Fill({ color: '#fff' })
      })
    });
  }

  // Kandidaterna dyker upp en efter en (rang 1 först) — samma data, men
  // skanningens resultat blir läsbart i rummet i stället för en klump.
  function ritaRadarMarkorer(data) {
    const ol = getOl();
    rensaRadarMarkorer();
    if (!ol || !radarLayer || !epsg3014Registrerad) return;
    const till = viewer.getProjection().getCode();
    (data.kandidater || []).forEach((k, i) => {
      if (!k.centroid) return;
      let xy;
      try {
        xy = projicera([k.centroid.easting, k.centroid.northing], 'EPSG:3014', till);
      } catch (err) {
        return;
      }
      if (!xy) return;
      const timer = setTimeout(() => {
        const f = new ol.Feature({ geometry: new ol.geom.Point(xy), rang: k.rang });
        f.setStyle(radarMarkorStil(ol, k.rang));
        radarLayer.getSource().addFeature(f);
      }, 120 * i);
      radarTimers.push(timer);
    });
  }

  function renderaRadar() {
    if (!senasteRadar) return;
    panel.setRadarResult(renderRadarRubrik(senasteRadar, t()),
      renderRadarLista(senasteRadar, t(), aktivtSprak));
  }

  async function korRadar() {
    if (kollapsad) setKollapsad(false);
    const map = viewer.getMap();
    const extent = map.getView().calculateExtent(map.getSize());
    const from = viewer.getProjection().getCode();
    let bbox;
    try {
      bbox = epsg3014Registrerad ? bboxFranExtent(extent, (xy) => projicera(xy, from, 'EPSG:3014')) : null;
    } catch (err) {
      bbox = null;
    }
    if (!bbox) {
      panel.setRadarError(`${t().radarFel} (EPSG:3014)`);
      return;
    }
    panel.setRadarLoading();
    rensaRadarMarkorer();
    clearOverlay();
    visaLegend(false);
    let data;
    let status = 0;
    try {
      const url = `${apiUrl}/api/radar?bbox=${bbox.map((v) => encodeURIComponent(v.toFixed(1))).join(',')}`;
      const resp = await fetch(url);
      status = resp.status;
      data = await resp.json();
    } catch (err) {
      console.error('geotillsyn: /api/radar misslyckades', err);
      panel.setRadarError(t().radarFel);
      return;
    }
    if (status === 400 && data && data.fel) {
      // För stor zon m.m.: ett deklarerat nej från backend, inte ett fel i UI:t.
      senasteRadar = null;
      panel.setRadarInfo(meddelandeText(data.fel, aktivtSprak));
      return;
    }
    if (status >= 400) {
      panel.setRadarError((data && data.fel) ? meddelandeText(data.fel, aktivtSprak) : `HTTP ${status}`);
      return;
    }
    senasteRadar = data;
    renderaRadar();
    ritaRadarMarkorer(data);
  }

  // Klick på en kandidat: centrera kartan där och kör den vanliga
  // ett-klicks-granskningen — radarn pekar, motorn granskar, handläggaren beslutar.
  function valjRadarKandidat(e3014, n3014) {
    const till = viewer.getProjection().getCode();
    let xy;
    try {
      xy = projicera([e3014, n3014], 'EPSG:3014', till);
    } catch (err) {
      xy = null;
    }
    if (!xy) return;
    const view = viewer.getMap().getView();
    view.animate({ center: xy, zoom: Math.max(view.getZoom() || 0, 16), duration: 500 });
    pahandlaKlick({ coordinate: xy });
  }

  function initRadarLayer() {
    const ol = getOl();
    if (!ol) return;
    radarLayer = new ol.layer.Vector({
      source: new ol.source.Vector(),
      name: 'geotillsyn-radar',
      zIndex: 51
    });
    viewer.getMap().addLayer(radarLayer);
  }

  async function pahandlaKlick(evt) {
    // Ett kartklick är alltid en analysbegäran: är panelen ihopfälld öppnas
    // den — ett klick får aldrig se ut att göra ingenting.
    if (kollapsad) setKollapsad(false);
    panel.startaAnalys();
    identify(evt);
    const punkt = transformTill3014(evt.coordinate);
    if (!punkt) {
      CHECKS.forEach((c) => visaStatus(c.key, { typ: 'fel', suffix: ' (EPSG:3014)' }));
      return;
    }
    senastePunkt3014 = punkt;
    CHECKS.forEach((c) => korOchRendera(c, punkt));
    hamtaSnedbilder(punkt);
  }

  // Ett enda namngivet vektorlager för Fall 3-overlayen (godkänt/verkligt läge);
  // rensas och återfylls vid varje nytt klick.
  function initOverlayLayer() {
    const ol = getOl();
    if (!ol) return;
    overlayLayer = new ol.layer.Vector({
      source: new ol.source.Vector(),
      name: 'geotillsyn-fall3-overlay',
      zIndex: 50
    });
    viewer.getMap().addLayer(overlayLayer);
  }

  /* --- biografi-stripen: årsstyrt ortofotolager + regelverkskontext --- */

  // Origo registrerar lagren under namnet UTAN workspace-prefix
  // ('Orto2023_wms', inte 'Lantmateriet:Orto2023_wms'), medan konfigurationen
  // och arslager använder det fullständiga namnet. Slå upp båda — annars
  // returnerar getLayer undefined och biografin byter aldrig ortofoto.
  function hittaLager(namn) {
    return viewer.getLayer(namn) || viewer.getLayer(namn.split(':').pop());
  }

  function visaAr(year) {
    aktuelltAr = year;
    let bytteLager = false;
    years.forEach((y) => {
      const layer = hittaLager(arslager[y]);
      if (layer) {
        layer.setVisible(y === year);
        if (y === year) bytteLager = true;
      }
    });
    if (!bytteLager) {
      console.warn(`geotillsyn: hittade inget ortofotolager för ${year} `
        + `(${arslager[year]}) — kartbilden byts inte.`);
    }
    if (biografi) biografi.setAr(year);
  }

  // "Regelverk YYYY"-knappen i biografi-stripen: samma detaljvy som förut
  // (renderKontextDetalj), nu i en popover inuti stripen i stället för
  // tidslinjepillens expanderande sektion.
  function renderRegelverkPopover(year) {
    if (!biografi) return;
    const pop = biografi.el.querySelector('.gt-biografi__regelpop');
    if (!pop) return;
    if (!regler) {
      pop.innerHTML = `<b>${year}</b> (${escapeHtml(t().regelmodellEjLaddad)})`;
      return;
    }
    const isoDate = `${year}-07-01`;
    pop.innerHTML = `<div class="gt-regelrubrik">${escapeHtml(t().regelverk)} ${year}</div>`
      + (t().statutNot ? `<div class="gt-regelnot">${escapeHtml(t().statutNot)}</div>` : '')
      + renderKontextDetalj(regler, isoDate, t());
  }

  /* --- panel-tillstånd + språk --- */

  function setKollapsad(ny) {
    kollapsad = ny;
    panel.setCollapsed(ny);
    const rot = document.getElementById(viewer.getId());
    if (rot) rot.classList.toggle('gt-oppen', !ny);
  }

  function bytSprak() {
    aktivtSprak = aktivtSprak === 'sv' ? 'en' : 'sv';
    panel.uppdateraTexter(t());
    if (biografi) biografi.uppdateraTexter(t());
    // Både resultat- och info-/felkort renderas om: allt backend skickade bär
    // meddelandekoder, så språkbytet kräver ingen ny hämtning.
    new Set([...Object.keys(senasteData), ...Object.keys(senasteStatus)])
      .forEach(renderaKort);
    renderaSnedbilder();
    if (senasteRadar && panel.el.querySelector('.gt-radar')) renderaRadar();
    visaAr(aktuelltAr);
    // Popovern håller inte koll på öppet/stängt själv utifrån — rendera om den
    // bara om den redan är synlig, annars låt den vänta tills den öppnas.
    if (biografi) {
      const pop = biografi.el.querySelector('.gt-biografi__regelpop');
      if (pop && !pop.hidden) renderRegelverkPopover(aktuelltAr);
    }
    if (legendEl && !legendEl.hidden) visaLegend(true);
  }

  return Origo.ui.Component({
    name: 'geotillsyn',
    onInit() {
      button = Origo.ui.Button({
        cls: 'o-geotillsyn padding-small icon-smaller round light box-shadow',
        click() {
          setKollapsad(!kollapsad);
        },
        icon,
        tooltipText: t().knappTooltip,
        tooltipPlacement: 'east'
      });
    },
    onAdd(evt) {
      viewer = evt.target;
      if (!target) target = `${viewer.getMain().getNavigation().getId()}`;
      this.addComponents([button]);
      this.render();

      injectStyles();
      panel = skapaPanel({
        t: t(),
        onSprak: bytSprak,
        onKollaps: () => setKollapsad(true),
        onRetry: (key) => {
          const check = CHECKS.find((c) => c.key === key);
          if (check && senastePunkt3014) korOchRendera(check, senastePunkt3014);
        },
        onRadar: korRadar,
        onRadarVal: valjRadarKandidat,
        onRadarTillbaka: renderaRadar
      });
      panel.tabEl.addEventListener('click', () => setKollapsad(false));
      legendEl = document.createElement('div');
      legendEl.className = 'gt-legend';
      legendEl.hidden = true;

      const rot = document.getElementById(viewer.getId());
      rot.appendChild(panel.el);
      rot.appendChild(panel.tabEl);
      rot.appendChild(legendEl);
      setKollapsad(false);

      registreraEpsg3014();
      initOverlayLayer();
      initRadarLayer();
      viewer.getMap().on('singleclick', pahandlaKlick);

      // Biografi-stripens Rättighet-spår läser regler.json vid varje ritning
      // (lagBand/lovbefrielseBand/strandskyddBand) — den byggs därför först när
      // svaret (eller ett tomt regler-läge efter ett fel) finns, i stället för
      // att försöka hålla en levande referens uppdaterad i efterhand.
      function initBiografi() {
        biografi = skapaBiografi({
          years, startAr: aktuelltAr, regler, t: t(), onArByte: visaAr, onRegelverk: renderRegelverkPopover
        });
        rot.appendChild(biografi.el);
        biografi.setAr(aktuelltAr);
        uppdateraBiografiData();
      }

      fetch(reglerUrl)
        .then((resp) => resp.json())
        .then((json) => {
          regler = json;
          initBiografi();
          visaAr(aktuelltAr);
        })
        .catch((err) => {
          console.error('geotillsyn: could not load regler.json', err);
          initBiografi();
          visaAr(aktuelltAr);
        });
    },
    render() {
      const el = Origo.ui.dom.html(button.render());
      document.getElementById(target).appendChild(el);
      this.dispatch('render');
    }
  });
};

export default GeoTillsyn;

import Origo from 'Origo';
import { TEXTS } from './i18n.mjs';
import { composeHeadline, renderCheckBody, escapeHtml } from './dossier.mjs';
import { renderKontextSammanfattning, renderKontextDetalj } from './regelverk.mjs';
import { injectStyles } from './styles.mjs';
import { skapaPanel } from './panel.js';
import { skapaTidslinje } from './timeline.js';

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
  let tidslinje = null;
  let legendEl = null;
  let aktivtSprak = TEXTS[sprak] ? sprak : 'sv';
  let aktuelltAr = startAr;
  let kollapsad = false;
  let senastePunkt3014 = null;
  const senasteData = {};
  let overlayLayer = null;

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
    const data = senasteData[key];
    if (!data) return;
    panel.setCardResult(key, {
      headline: composeHeadline(key, data, t(), aktivtSprak),
      body: renderCheckBody(data, t(), aktivtSprak)
    });
  }

  async function korOchRendera(check, [e3014, n3014]) {
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
      panel.setCardError(check.key, t().felHamtning);
      return;
    }
    if (status === 404 && data && data.fel) {
      // Ärligt "hittades inte"-svar (ingen byggnad/inget lov) — info, inte fel.
      delete senasteData[check.key];
      panel.setCardInfo(check.key, data.fel);
      if (check.key === 'lovavvikelse') {
        clearOverlay();
        visaLegend(false);
      }
      return;
    }
    if (status >= 400) {
      panel.setCardError(check.key, (data && data.fel) || `HTTP ${status}`);
      return;
    }
    senasteData[check.key] = data;
    renderaKort(check.key);
    if (check.key === 'lovavvikelse') {
      if (data.lov_hittat) {
        hamtaFall3Geometri(e3014, n3014, check.radie);
      } else {
        clearOverlay();
        visaLegend(false);
      }
    }
  }

  async function pahandlaKlick(evt) {
    // Ett kartklick är alltid en analysbegäran: är panelen ihopfälld öppnas
    // den — ett klick får aldrig se ut att göra ingenting.
    if (kollapsad) setKollapsad(false);
    panel.startaAnalys();
    identify(evt);
    const punkt = transformTill3014(evt.coordinate);
    if (!punkt) {
      CHECKS.forEach((c) => panel.setCardError(c.key, `${t().felHamtning} (EPSG:3014)`));
      return;
    }
    senastePunkt3014 = punkt;
    CHECKS.forEach((c) => korOchRendera(c, punkt));
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

  /* --- tidslinje --- */

  // Origo registrerar lagren under namnet UTAN workspace-prefix
  // ('Orto2023_wms', inte 'Lantmateriet:Orto2023_wms'), medan konfigurationen
  // och arslager använder det fullständiga namnet. Slå upp båda — annars
  // returnerar getLayer undefined och tidslinjen byter aldrig ortofoto.
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
    const isoDate = `${year}-07-01`;
    tidslinje.setAr(year);
    const detalj = regler
      ? `<div class="gt-regelrubrik">${escapeHtml(t().regelverk)} ${year}</div>`
        + (t().statutNot ? `<div class="gt-regelnot">${escapeHtml(t().statutNot)}</div>` : '')
        + renderKontextDetalj(regler, isoDate, t())
      : '';
    tidslinje.setKontext(
      regler ? renderKontextSammanfattning(regler, isoDate, t())
        : `<b>${year}</b> (${escapeHtml(t().regelmodellEjLaddad)})`,
      detalj
    );
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
    tidslinje.uppdateraTexter(t());
    Object.keys(senasteData).forEach(renderaKort);
    visaAr(aktuelltAr);
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
        }
      });
      panel.tabEl.addEventListener('click', () => setKollapsad(false));
      tidslinje = skapaTidslinje({ years, startAr: aktuelltAr, t: t(), onArByte: visaAr });
      legendEl = document.createElement('div');
      legendEl.className = 'gt-legend';
      legendEl.hidden = true;

      const rot = document.getElementById(viewer.getId());
      rot.appendChild(panel.el);
      rot.appendChild(panel.tabEl);
      rot.appendChild(tidslinje.el);
      rot.appendChild(legendEl);
      setKollapsad(false);

      registreraEpsg3014();
      initOverlayLayer();
      viewer.getMap().on('singleclick', pahandlaKlick);

      fetch(reglerUrl)
        .then((resp) => resp.json())
        .then((json) => {
          regler = json;
          visaAr(aktuelltAr);
        })
        .catch((err) => {
          console.error('geotillsyn: could not load regler.json', err);
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

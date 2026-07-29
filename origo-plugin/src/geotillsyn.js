import Origo from 'Origo';

/**
 * Geo-Tillsyn Origo plugin.
 *
 * v0.2 — Tidslinje: a year slider that (1) switches the visible orthophoto
 * layer and (2) shows the legal context in force at that date, evaluated from
 * the same versioned rule model (regler.json) as mcp-regelverk. The JS
 * evaluator below is a thin demo-side duplicate; in Sprint 3 the panel calls
 * the mcp-regelverk HTTP service instead and this duplicate is deleted.
 *
 * v0.3 — Språk: SV/EN toggle on the panel. Only the UI chrome (our own labels)
 * is translated; statutory names from regler.json (SFS titles, "friggebod",
 * lagrum) are official Swedish terms and stay verbatim in both languages.
 *
 * Also: "identify fastighet" button — map click -> WMS GetFeatureInfo
 * (the verified point-in-polygon on karta.sundsvall.se, docs/data-findings.md §1).
 *
 * v0.4 — B-live: kopplar pluginet till geo-tillsyn REST-backend
 * (src/geo_tillsyn/server.py, /api/olovligt, /api/lovavvikelse,
 * /api/strandskydd, /api/lovavvikelse/geometri). En liten segmented control i
 * panelen väljer vilket fall nästa kartklick analyserar (default Fall 3,
 * eftersom det är det enda med karta-overlay); klicket görs om till
 * EPSG:3014 och skickas till rätt endpoint. Svaret renderas som Fakta /
 * Bedömning / Beslut — samma tre-nivå-struktur som dossier.md. Fall 3 hämtar
 * även godkänt/verkligt läge som GeoJSON och ritar dem som ett eget
 * vektorlager (blå/röd kontur). Beslutet är alltid handläggarens — pluginet
 * skriver aldrig ett skuld-ord som backend inte skickat.
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

/* --- i18n: our own UI chrome only; statutory terms stay Swedish --- */

const TEXTS = {
  sv: {
    tidslinjeAria: 'Tidslinje',
    sliderAria: 'Välj årtal för ortofoto och regelverk',
    identifieraTooltip: 'Geo-Tillsyn: identifiera fastighet',
    sprakKnapp: 'EN',
    sprakKnappAria: 'Switch to English',
    lag: 'Lag',
    lovbefrielser: 'Lovbefrielser',
    inga: 'inga',
    strandskydd: 'Strandskydd',
    ssGaller: '<b>gäller</b> inom zon (dispens krävs — lovbefrielse ger inte dispens)',
    ssFinnsInte: (d) => `<b>fanns inte än</b> (generellt strandskydd infördes ${d})`,
    preskription: 'Preskription',
    preskriptionText: (ar, slut, harLopt) =>
      `åtgärd från ${ar} — tioårsregeln löper ut <b>${slut}</b> `
      + `(${harLopt ? 'har löpt ut' : 'löper ännu'}; strandskydd preskriberas aldrig)`,
    regelmodellEjLaddad: 'regelmodell ej laddad',
    fastighet: 'Fastighet',
    saknarBeteckning: '(saknar beteckning)',
    ingenFastighet: 'Ingen fastighet på denna punkt.',
    felHamtning: 'Fel vid hämtning.',
    modalTitel: 'Geo-Tillsyn',
    fall1Knapp: 'Fall 1',
    fall3Knapp: 'Fall 3',
    fall7Knapp: 'Fall 7',
    fallAria: 'Välj fall att analysera vid nästa kartklick',
    analyserar: 'Analyserar…',
    fakta: 'Fakta',
    bedomning: 'Bedömning',
    beslut: 'Beslut',
    beslutText: 'Beslutet fattas av handläggaren.',
    ejFastställt: '»Ej fastställt«',
    kallor: 'Källor',
    klickaKarta: 'Klicka på kartan för att köra Geo-Tillsyn-analysen.',
    godkantLage: 'Godkänt',
    verkligtLage: 'Verkligt',
    intePavisat: 'Ingen geometri att visa.'
  },
  en: {
    tidslinjeAria: 'Timeline',
    sliderAria: 'Select year for orthophoto and legislation',
    identifieraTooltip: 'Geo-Tillsyn: identify property',
    sprakKnapp: 'SV',
    sprakKnappAria: 'Byt till svenska',
    lag: 'Act',
    lovbefrielser: 'Permit exemptions',
    inga: 'none',
    strandskydd: 'Shoreline protection',
    ssGaller: '<b>applies</b> within zone (dispensation required — a permit exemption does not grant dispensation)',
    ssFinnsInte: (d) => `<b>did not yet exist</b> (general shoreline protection introduced ${d})`,
    preskription: 'Limitation',
    preskriptionText: (ar, slut, harLopt) =>
      `measure from ${ar} — the ten-year rule expires <b>${slut}</b> `
      + `(${harLopt ? 'has expired' : 'still running'}; shoreline protection never lapses)`,
    regelmodellEjLaddad: 'rule model not loaded',
    fastighet: 'Property',
    saknarBeteckning: '(no designation)',
    ingenFastighet: 'No property at this point.',
    felHamtning: 'Error while fetching.',
    modalTitel: 'Geo-Tillsyn',
    fall1Knapp: 'Case 1',
    fall3Knapp: 'Case 3',
    fall7Knapp: 'Case 7',
    fallAria: 'Select which case the next map click analyses',
    analyserar: 'Analysing…',
    fakta: 'Facts',
    bedomning: 'Assessment',
    beslut: 'Decision',
    beslutText: 'The decision is made by the caseworker.',
    ejFastställt: '»Not established«',
    kallor: 'Sources',
    klickaKarta: 'Click the map to run the Geo-Tillsyn analysis.',
    godkantLage: 'Approved',
    verkligtLage: 'Actual',
    intePavisat: 'No geometry to show.'
  }
};

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (ch) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[ch]));
}

/* --- Fall 1/3/7 REST-analys: dossier-rendering (Fakta/Bedömning/Beslut) --- */

// EPSG:3014 = SWEREF99 17 15 (kommunlagrens CRS på karta.sundsvall.se);
// backend-koordinaterna är alltid 3014, kartprojektionen i geotillsyn.json är
// 3006 — pluginet måste registrera 3014 hos proj4 innan Origo.ol.proj.transform
// (eller GeoJSON-läsningen) kan konvertera mellan dem.
const EPSG_3014_DEF = '+proj=tmerc +lat_0=0 +lon_0=17.25 +k=1 +x_0=150000 +y_0=0 '
  + '+ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs';

const FALL_ENDPOINTS = {
  fall1: { path: '/api/olovligt', defaultRadie: 100 },
  fall3: { path: '/api/lovavvikelse', defaultRadie: 100 },
  fall7: { path: '/api/strandskydd', defaultRadie: 150 }
};

// Nycklar som redan visas i "Fakta"-rubriken eller hanteras separat
// (osäkerheter, källor, meddelande, fel) och alltså inte ska upprepas
// generiskt i Fakta/Bedömning-listorna.
const DOSSIER_HOPPA_OVER = new Set([
  'kallor', 'osakerheter', 'meddelande', 'fel', 'hamtad', 'punkt', 'traffar',
  'juridisk_not', 'korsjamforelse'
]);

// Fält som hör hemma under "Bedömning" (juridisk tolkning) snarare än
// "Fakta" (rådata/mätvärden). Allt annat okänt fält hamnar i Fakta.
const BEDOMNING_FALT = new Set([
  'bal_forenligt', 'bygglov_kravdes', 'lovbefrielse', 'rattelse_preskriberad',
  'sanktionsavgift_mojlig', 'matningskritiskt', 'matningskritiska',
  'inom_strandskydd', 'pbl_vid_beslut', 'overgangsregel_tillampad',
  'dispens_kravs_idag', 'preskriberas', 'gallde_vid_uppforande'
]);

const FALT_LABEL = {
  sv: {
    byggnad_id: 'Byggnad', area_m2: 'Area',
    sista_ar_utan: 'Sista år utan byggnad (ortofoto)',
    forsta_ar_med: 'Första år med byggnad (ortofoto)',
    bal_nybyggnadsar: 'Nybyggnadsår (byggnadsregistret)',
    bal_forenligt: 'Förenligt med byggnadsregistret',
    bygglov_kravdes: 'Bygglov krävdes',
    lovbefrielse: 'Lovbefrielse',
    rattelse_preskriberad: 'Rättelse preskriberad (11 kap. 20 § PBL)',
    sanktionsavgift_mojlig: 'Byggsanktionsavgift möjlig (11 kap. 58 § PBL)',
    matningskritiskt: 'Mätningskritiskt',
    matningskritiska: 'Mätningskritiska punkter',
    inom_strandskydd: 'Inom strandskydd',
    poang_per_ar: 'Poäng per år (datering)',
    dnr: 'Diarienummer', beslutsdatum: 'Beslutsdatum',
    pbl_vid_beslut: 'Lag vid beslut', overgangsregel_tillampad: 'Övergångsregel tillämpad',
    godkand_area_m2: 'Godkänd area', verklig_area_m2: 'Verklig area',
    area_diff_m2: 'Areaavvikelse', area_diff_procent: 'Areaavvikelse (%)',
    utanfor_godkant_m2: 'Yta utanför godkänt läge',
    avstand_grans_godkant_m: 'Avstånd till gräns (godkänt läge)',
    avstand_grans_verklig_m: 'Avstånd till gräns (verkligt läge)',
    antal_traffar: 'Antal träffar', antal_byggnader: 'Antal byggnader',
    antal_utanfor: 'Antal utanför', radie_m: 'Sökradie',
    laege: 'Läge', byggnads_ar: 'Byggnadsår',
    dispens_kravs_idag: 'Dispens krävs idag', preskriberas: 'Preskriberas',
    gallde_vid_uppforande: 'Gällde vid uppförande', atgarder: 'Åtgärder',
    zon_referenser: 'Zonreferenser', andel_inom: 'Andel inom zon'
  },
  en: {
    byggnad_id: 'Building', area_m2: 'Area',
    sista_ar_utan: 'Last year without building (orthophoto)',
    forsta_ar_med: 'First year with building (orthophoto)',
    bal_nybyggnadsar: 'Construction year (building register)',
    bal_forenligt: 'Consistent with building register',
    bygglov_kravdes: 'Building permit required',
    lovbefrielse: 'Permit exemption',
    rattelse_preskriberad: 'Correction time-barred (ch. 11 §20 PBL)',
    sanktionsavgift_mojlig: 'Building sanction fee possible (ch. 11 §58 PBL)',
    matningskritiskt: 'Measurement-critical',
    matningskritiska: 'Measurement-critical points',
    inom_strandskydd: 'Within shoreline protection',
    poang_per_ar: 'Score per year (dating)',
    dnr: 'Case number', beslutsdatum: 'Decision date',
    pbl_vid_beslut: 'Act in force at decision', overgangsregel_tillampad: 'Transitional rule applied',
    godkand_area_m2: 'Approved area', verklig_area_m2: 'Actual area',
    area_diff_m2: 'Area difference', area_diff_procent: 'Area difference (%)',
    utanfor_godkant_m2: 'Area outside approved position',
    avstand_grans_godkant_m: 'Distance to boundary (approved position)',
    avstand_grans_verklig_m: 'Distance to boundary (actual position)',
    antal_traffar: 'Number of hits', antal_byggnader: 'Number of buildings',
    antal_utanfor: 'Number outside', radie_m: 'Search radius',
    laege: 'Position', byggnads_ar: 'Construction year',
    dispens_kravs_idag: 'Dispensation required today', preskriberas: 'Time-barred',
    gallde_vid_uppforande: 'In force at construction', atgarder: 'Measures',
    zon_referenser: 'Zone references', andel_inom: 'Share within zone'
  }
};

function faltLabel(key, sprak) {
  const map = FALT_LABEL[sprak] || FALT_LABEL.sv;
  return map[key] || key;
}

function formatVarde(value, sprak, t) {
  if (value === null || value === undefined) return t.ejFastställt;
  if (typeof value === 'boolean') return value ? 'Ja' : 'Nej';
  if (Array.isArray(value)) {
    if (value.length === 0) return t.inga;
    if (value.every((v) => typeof v === 'object' && v !== null)) {
      return value.map((v) => escapeHtml(JSON.stringify(v))).join('; ');
    }
    return value.map((v) => escapeHtml(String(v))).join(', ');
  }
  if (typeof value === 'object') return escapeHtml(JSON.stringify(value));
  return escapeHtml(String(value));
}

function renderFaltRad(key, value, sprak, t) {
  return `<div class="gt-row"><b>${escapeHtml(faltLabel(key, sprak))}:</b> `
    + `${formatVarde(value, sprak, t)}</div>`;
}

function renderKallor(kallor, t) {
  if (!Array.isArray(kallor) || kallor.length === 0) return '';
  const items = kallor.map((k) => {
    const beskrivning = escapeHtml(k && k.beskrivning ? k.beskrivning : '');
    const url = k && k.url ? String(k.url) : null;
    if (url && /^https?:\/\//i.test(url)) {
      return `<li><a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${beskrivning}</a></li>`;
    }
    return `<li>${beskrivning}</li>`;
  }).join('');
  return `<div class="gt-row"><b>${escapeHtml(t.kallor)}:</b></div>`
    + `<ul class="gt-kallor" style="margin:0.15rem 0 0.4rem 1.2rem;padding:0">${items}</ul>`;
}

function renderOsakerheter(osakerheter, t) {
  if (!Array.isArray(osakerheter) || osakerheter.length === 0) return '';
  const items = osakerheter.map((o) => `<li>${escapeHtml(String(o))}</li>`).join('');
  return `<ul class="gt-osakerheter" style="margin:0.15rem 0 0 1.2rem;padding:0;color:#7a4a00">${items}</ul>`;
}

// Bygger den generiska tre-nivå-dossieren (Fakta/Bedömning/Beslut) från valfritt
// backend-svar. Aldrig ett eget skuld-ord — bara nycklar backend faktiskt skickat.
function renderDossier(data, t, sprak) {
  if (data.meddelande) {
    return `<div class="gt-row">${escapeHtml(data.meddelande)}</div>`
      + renderOsakerheter(data.osakerheter, t);
  }

  const faktaRader = [];
  const bedomningRader = [];
  Object.keys(data).forEach((key) => {
    if (DOSSIER_HOPPA_OVER.has(key)) return;
    if (BEDOMNING_FALT.has(key)) {
      bedomningRader.push(renderFaltRad(key, data[key], sprak, t));
    } else {
      faktaRader.push(renderFaltRad(key, data[key], sprak, t));
    }
  });

  // Fall 7: träffar-listan renderas separat (nästlad struktur), inte generiskt.
  if (Array.isArray(data.traffar)) {
    data.traffar.forEach((traff, idx) => {
      const rader = Object.keys(traff)
        .map((key) => renderFaltRad(key, traff[key], sprak, t))
        .join('');
      faktaRader.push(`<div class="gt-row"><b>#${idx + 1} ${escapeHtml(faltLabel('byggnad_id', sprak))}: `
        + `${escapeHtml(traff.byggnad_id)}</b></div>${rader}`);
    });
  }

  if (data.korsjamforelse) {
    const rader = Object.keys(data.korsjamforelse)
      .map((key) => `<div class="gt-row">${escapeHtml(key)}: ${formatVarde(data.korsjamforelse[key], sprak, t)}</div>`)
      .join('');
    bedomningRader.push(rader);
  }

  const rubrikStil = 'style="margin:0.5rem 0 0.15rem;font-size:0.85rem"';
  const html = [];
  html.push(`<h4 class="gt-niva" ${rubrikStil}>${escapeHtml(t.fakta)}</h4>`);
  html.push(faktaRader.join('') || `<div class="gt-row">—</div>`);
  html.push(renderKallor(data.kallor, t));
  html.push(`<h4 class="gt-niva" ${rubrikStil}>${escapeHtml(t.bedomning)}</h4>`);
  html.push(bedomningRader.join('') || `<div class="gt-row">—</div>`);
  html.push(renderOsakerheter(data.osakerheter, t));
  html.push(`<h4 class="gt-niva" ${rubrikStil}>${escapeHtml(t.beslut)}</h4>`);
  html.push(`<div class="gt-row gt-beslut">${escapeHtml(t.beslutText)}</div>`);
  return html.join('');
}

/* --- minimal evaluator over regler.json (mirror of regelverk_core.py) --- */

function within(rule, isoDate) {
  return rule.fran <= isoDate && (!rule.till || isoDate <= rule.till);
}

function regelverkVid(regler, isoDate) {
  const pbl = regler.pbl_versioner.find((v) => within(v, isoDate)) || null;
  const befrielser = regler.lovbefrielser.filter((r) => within(r, isoDate));
  const ssGaller = isoDate >= regler.strandskydd.generellt_fran;
  const year = Number(isoDate.slice(0, 4));
  const tioarSlut = year + regler.preskription.pbl_tioarsregel.ar;
  return { pbl, befrielser, ssGaller, tioarSlut };
}

function renderKontext(regler, isoDate, t) {
  const r = regelverkVid(regler, isoDate);
  const idag = new Date().getFullYear();
  const rows = [];
  rows.push(`<b>${escapeHtml(isoDate)}</b>`);
  rows.push(r.pbl
    ? `${t.lag}: <b>${escapeHtml(r.pbl.namn)}</b> (${escapeHtml(r.pbl.sfs)})`
    : `${t.lag}: —`);
  const bef = r.befrielser
    .map((b) => `${escapeHtml(b.namn)} ${escapeHtml(b.max_kvm)} m²`)
    .join(', ');
  rows.push(`${t.lovbefrielser}: ${bef || t.inga}`);
  rows.push(r.ssGaller
    ? `${t.strandskydd}: ${t.ssGaller}`
    : `${t.strandskydd}: ${t.ssFinnsInte(escapeHtml(regler.strandskydd.generellt_fran))}`);
  const preskriberad = idag > r.tioarSlut;
  rows.push(`${t.preskription}: `
    + t.preskriptionText(escapeHtml(isoDate.slice(0, 4)), escapeHtml(r.tioarSlut), preskriberad));
  return rows.map((row) => `<div class="gt-row">${row}</div>`).join('');
}

/* ----------------------------------------------------------------------- */

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
  let active = false;
  let regler = null;
  let panelEl = null;
  let aktivtSprak = TEXTS[sprak] ? sprak : 'sv';
  let aktuelltAr = startAr;
  let valtFall = 'fall3';
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
    let content;
    try {
      const resp = await fetch(url);
      const json = await resp.json();
      const feat = json.features && json.features[0];
      content = feat
        ? `<b>${t().fastighet}:</b> ${escapeHtml(feat.properties[fbetProperty] || t().saknarBeteckning)}`
        : t().ingenFastighet;
    } catch (err) {
      console.error('geotillsyn: GetFeatureInfo failed', err);
      content = t().felHamtning;
    }
    // Skrivs in i panelen, INTE i en modal: Origos modal lägger en
    // helskärms-`o-modal-screen` över kartan som blockerar fallväljaren tills
    // den stängs — vid varje kartklick. Fastighetsbeteckningen hör dessutom
    // ihop med dossiern och ska synas samtidigt som den.
    const el = panelEl && panelEl.querySelector('.gt-fastighet');
    if (el) el.innerHTML = content;
  }

  /* --- REST-analys (Fall 1/3/7): klick -> 3006->3014 -> /api/* -> dossier --- */

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

  function analysPanelEl() {
    return panelEl && panelEl.querySelector('.gt-analys');
  }

  function visaAnalysStatus(html) {
    const el = analysPanelEl();
    if (el) el.innerHTML = html;
  }

  function clearOverlay() {
    if (overlayLayer) overlayLayer.getSource().clear();
  }

  // Ritar godkänt (blått) och verkligt (rött) läge från /api/lovavvikelse/geometri.
  // Reprojicerar EPSG:3014 -> kartans projektion via ol.format.GeoJSON, som
  // kräver att EPSG:3014 är registrerad hos proj4 (registreraEpsg3014 ovan).
  function ritaFall3Overlay(geometriData) {
    const ol = getOl();
    clearOverlay();
    if (!ol || !overlayLayer) return;
    if (!geometriData.lov_hittat) return;
    if (!epsg3014Registrerad) {
      console.error('geotillsyn: EPSG:3014 ej registrerad — Fall 3-overlay ritas inte.');
      return;
    }

    const featureProjection = viewer.getProjection().getCode();
    const format = new ol.format.GeoJSON();
    const lager = [
      { geom: geometriData.godkant_lage, farg: 'rgba(40,80,255,1)', etikett: t().godkantLage },
      { geom: geometriData.verkligt_lage, farg: 'rgba(230,40,40,1)', etikett: t().verkligtLage }
    ];

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
    });
  }

  async function hamtaFall3Geometri(e3014, n3014, defaultRadie) {
    const url = `${apiUrl}/api/lovavvikelse/geometri?easting=${encodeURIComponent(e3014)}`
      + `&northing=${encodeURIComponent(n3014)}&radie_m=${encodeURIComponent(defaultRadie)}`;
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

  async function korAnalys(evt) {
    const endpoint = FALL_ENDPOINTS[valtFall];
    if (!endpoint) return;

    if (valtFall !== 'fall3') clearOverlay();
    visaAnalysStatus(`<div class="gt-row">${escapeHtml(t().analyserar)}</div>`);

    const punkt3014 = transformTill3014(evt.coordinate);
    if (!punkt3014) {
      visaAnalysStatus(`<div class="gt-row gt-fel" style="color:#b00020">${escapeHtml(t().felHamtning)} `
        + '(EPSG:3014 ej tillgänglig — se konsolen)</div>');
      return;
    }
    const [e3014, n3014] = punkt3014;

    const url = `${apiUrl}${endpoint.path}?easting=${encodeURIComponent(e3014)}`
      + `&northing=${encodeURIComponent(n3014)}&radie_m=${encodeURIComponent(endpoint.defaultRadie)}`;

    let data;
    try {
      const resp = await fetch(url);
      data = await resp.json();
      if (!resp.ok) {
        const felmeddelande = data && data.fel ? data.fel : `HTTP ${resp.status}`;
        visaAnalysStatus(`<div class="gt-row gt-fel" style="color:#b00020">${escapeHtml(felmeddelande)}</div>`);
        return;
      }
    } catch (err) {
      console.error('geotillsyn: REST-analysen misslyckades', err);
      visaAnalysStatus(`<div class="gt-row gt-fel" style="color:#b00020">${escapeHtml(t().felHamtning)}</div>`);
      return;
    }

    visaAnalysStatus(renderDossier(data, t(), aktivtSprak));

    if (valtFall === 'fall3') {
      if (data.lov_hittat) {
        hamtaFall3Geometri(e3014, n3014, endpoint.defaultRadie);
      } else {
        clearOverlay();
      }
    }
  }

  async function pahandlaKlick(evt) {
    await identify(evt);
    await korAnalys(evt);
  }

  function toggleActive() {
    active = !active;
    const map = viewer.getMap();
    if (active) map.on('singleclick', pahandlaKlick);
    else map.un('singleclick', pahandlaKlick);
  }

  // Ett enda namngivet vektorlager för Fall 3-overlayen (godkänt/verkligt läge);
  // rensas och återfylls vid varje nytt klick (BUILD-steg 4: "Add/replace a
  // single named overlay layer on each run").
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
    const kontextEl = panelEl.querySelector('.gt-kontext');
    const isoDate = `${year}-07-01`;
    kontextEl.innerHTML = regler
      ? renderKontext(regler, isoDate, t())
      : `<div class="gt-row"><b>${year}</b> (${t().regelmodellEjLaddad})</div>`;
    panelEl.querySelector('.gt-ar').textContent = String(year);
  }

  function fallKnappStil(fall) {
    const aktiv = fall === valtFall;
    return [
      'cursor:pointer', `border:1px solid ${aktiv ? '#2854d8' : '#999'}`,
      `background:${aktiv ? '#2854d8' : '#fff'}`, `color:${aktiv ? '#fff' : '#222'}`,
      'border-radius:0.35rem', 'padding:0.15rem 0.6rem', 'font:inherit', 'font-weight:bold'
    ].join(';');
  }

  function byggPanelInnehall() {
    const startIndex = Math.max(years.indexOf(aktuelltAr), 0);
    return `
      <div style="display:flex;align-items:center;gap:0.75rem">
        <span class="gt-ar" style="font-size:1.4rem;font-weight:bold;min-width:3.2rem">${years[startIndex]}</span>
        <input class="gt-slider" type="range" min="0" max="${years.length - 1}"
               step="1" value="${startIndex}" style="flex:1"
               aria-label="${t().sliderAria}">
        <span style="color:#666">${years[0]}–${years[years.length - 1]}</span>
        <button class="gt-sprak" type="button" aria-label="${t().sprakKnappAria}"
                style="cursor:pointer;border:1px solid #999;background:#fff;border-radius:0.35rem;padding:0.15rem 0.5rem;font:inherit;font-weight:bold">${t().sprakKnapp}</button>
      </div>
      <div class="gt-kontext" style="margin-top:0.4rem;line-height:1.45"></div>
      <hr style="margin:0.5rem 0;border:none;border-top:1px solid #ddd">
      <div class="gt-fallval" role="group" aria-label="${t().fallAria}"
           style="display:flex;align-items:center;gap:0.4rem">
        <button class="gt-fallknapp" type="button" data-fall="fall1"
                style="${fallKnappStil('fall1')}">${t().fall1Knapp}</button>
        <button class="gt-fallknapp" type="button" data-fall="fall3"
                style="${fallKnappStil('fall3')}">${t().fall3Knapp}</button>
        <button class="gt-fallknapp" type="button" data-fall="fall7"
                style="${fallKnappStil('fall7')}">${t().fall7Knapp}</button>
      </div>
      <div class="gt-fastighet" style="margin-top:0.4rem"></div>
      <div class="gt-analys" style="margin-top:0.4rem;line-height:1.45;max-height:40vh;overflow-y:auto">
        <div class="gt-row">${escapeHtml(t().klickaKarta)}</div>
      </div>`;
  }

  function kopplaPanelHandlers() {
    panelEl.querySelector('.gt-slider').addEventListener('input', (evt) => {
      visaAr(years[Number(evt.target.value)]);
    });
    panelEl.querySelector('.gt-sprak').addEventListener('click', () => {
      aktivtSprak = aktivtSprak === 'sv' ? 'en' : 'sv';
      panelEl.setAttribute('aria-label', t().tidslinjeAria);
      panelEl.innerHTML = byggPanelInnehall();
      kopplaPanelHandlers();
      visaAr(aktuelltAr);
    });
    panelEl.querySelectorAll('.gt-fallknapp').forEach((knapp) => {
      knapp.addEventListener('click', () => {
        valtFall = knapp.getAttribute('data-fall');
        panelEl.querySelectorAll('.gt-fallknapp').forEach((b) => {
          b.setAttribute('style', fallKnappStil(b.getAttribute('data-fall')));
        });
      });
    });
  }

  function buildPanel() {
    const el = document.createElement('div');
    el.className = 'gt-panel';
    el.setAttribute('role', 'region');
    el.setAttribute('aria-label', t().tidslinjeAria);
    el.style.cssText = [
      'position:absolute', 'left:50%', 'bottom:2.5rem',
      'transform:translateX(-50%)', 'width:min(680px, 92%)',
      'background:rgba(255,255,255,0.96)', 'border-radius:0.5rem',
      'box-shadow:0 2px 8px rgba(0,0,0,0.35)', 'padding:0.6rem 1rem',
      'z-index:30', 'font-family:inherit', 'font-size:0.8rem'
    ].join(';');
    el.innerHTML = byggPanelInnehall();
    panelEl = el;
    kopplaPanelHandlers();
    return el;
  }

  return Origo.ui.Component({
    name: 'geotillsyn',
    onInit() {
      button = Origo.ui.Button({
        cls: 'o-geotillsyn padding-small icon-smaller round light box-shadow',
        click() {
          toggleActive();
        },
        icon,
        tooltipText: t().identifieraTooltip,
        tooltipPlacement: 'east'
      });
    },
    onAdd(evt) {
      viewer = evt.target;
      if (!target) target = `${viewer.getMain().getNavigation().getId()}`;
      this.addComponents([button]);
      this.render();
      buildPanel();
      document.getElementById(viewer.getId()).appendChild(panelEl);
      registreraEpsg3014();
      initOverlayLayer();
      fetch(reglerUrl)
        .then((resp) => resp.json())
        .then((json) => { regler = json; visaAr(aktuelltAr); })
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

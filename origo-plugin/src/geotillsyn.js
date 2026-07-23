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
    modalTitel: 'Geo-Tillsyn'
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
    modalTitel: 'Geo-Tillsyn'
  }
};

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (ch) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[ch]));
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
    sprak = 'sv'
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

  function t() {
    return TEXTS[aktivtSprak];
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
    const modal = Origo.ui.Modal({
      title: t().modalTitel,
      content,
      target: viewer.getId()
    });
    modal.render();
  }

  function toggleActive() {
    active = !active;
    const map = viewer.getMap();
    if (active) map.on('singleclick', identify);
    else map.un('singleclick', identify);
  }

  /* --- tidslinje --- */

  function visaAr(year) {
    aktuelltAr = year;
    years.forEach((y) => {
      const layer = viewer.getLayer(arslager[y]);
      if (layer) layer.setVisible(y === year);
    });
    const kontextEl = panelEl.querySelector('.gt-kontext');
    const isoDate = `${year}-07-01`;
    kontextEl.innerHTML = regler
      ? renderKontext(regler, isoDate, t())
      : `<div class="gt-row"><b>${year}</b> (${t().regelmodellEjLaddad})</div>`;
    panelEl.querySelector('.gt-ar').textContent = String(year);
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
      <div class="gt-kontext" style="margin-top:0.4rem;line-height:1.45"></div>`;
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

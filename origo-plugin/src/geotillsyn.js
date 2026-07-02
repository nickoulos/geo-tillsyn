import Origo from 'Origo';

/**
 * Geo-Tillsyn Origo plugin — Spike B hello-world.
 *
 * Adds a toolbar button that toggles "identify fastighet" mode: clicking the
 * map queries the configured WMS via GetFeatureInfo (the verified reliable
 * point-in-polygon on karta.sundsvall.se — see docs/data-findings.md §1) and
 * shows the property designation (FBET). The dossier panel, tidslinje and
 * regelgraf views build on this shell in Sprint 2-3.
 */
const GeoTillsyn = function GeoTillsyn(options = {}) {
  const {
    owsUrl = 'https://karta.sundsvall.se/geoserver/ows',
    fastighetLayer = 'SundsvallsKommun:Fastighet_yta',
    fbetProperty = 'FBET',
    buttonTooltip = 'Geo-Tillsyn: identifiera fastighet'
  } = options;

  const icon = '#ic_search_24px';
  let button;
  let viewer;
  let target;
  let active = false;
  let clickKey = null;

  // WMS 1.3.0 + EPSG:3006/3013/3014 use northing,easting axis order.
  // Verified against karta.sundsvall.se 2026-07-02 (Spike C).
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

  // WMS responses are untrusted input; modal content is rendered as HTML.
  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, (ch) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[ch]));
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
        ? `<b>Fastighet:</b> ${escapeHtml(feat.properties[fbetProperty] || '(saknar beteckning)')}`
        : 'Ingen fastighet på denna punkt.';
    } catch (err) {
      console.error('geotillsyn: GetFeatureInfo failed', err);
      content = 'Fel vid hämtning.';
    }
    const modal = Origo.ui.Modal({
      title: 'Geo-Tillsyn',
      content,
      target: viewer.getId()
    });
    modal.render();
  }

  function toggleActive() {
    active = !active;
    const map = viewer.getMap();
    if (active) {
      clickKey = map.on('singleclick', identify);
    } else if (clickKey) {
      Origo.ol.Observable.unByKey
        ? Origo.ol.Observable.unByKey(clickKey)
        : map.un('singleclick', identify);
      clickKey = null;
    }
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
        tooltipText: buttonTooltip,
        tooltipPlacement: 'east'
      });
    },
    onAdd(evt) {
      viewer = evt.target;
      if (!target) target = `${viewer.getMain().getNavigation().getId()}`;
      this.addComponents([button]);
      this.render();
    },
    render() {
      const el = Origo.ui.dom.html(button.render());
      document.getElementById(target).appendChild(el);
      this.dispatch('render');
    }
  });
};

export default GeoTillsyn;

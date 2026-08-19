import test from 'node:test';
import assert from 'node:assert/strict';
import { TEXTS } from '../src/i18n.mjs';
import { renderRadarLista, renderRadarRubrik, bboxFranExtent } from '../src/radar.mjs';

const RADAR = {
  zon: { bbox: [0, 0, 200, 200], crs: 'EPSG:3014' },
  antal_byggnader: 57,
  antal_traffar: 3,
  kandidater: [
    {
      rang: 1, byggnad_id: 'bal_byggnad_yta.38472', fastighet: 'ALNÖ-USLAND 1:45',
      centroid: { easting: 158140.4, northing: 6918389.3, crs: 'EPSG:3014' },
      laege: 'inom', andel_inom: 1, byggnads_ar: 2014, gallde_vid_uppforande: true,
      dispens_kravs_idag: true, preskriberas: false, poang: 6,
      grunder: [{ kod: 'radar.poang_inom', params: {} },
        { kod: 'radar.poang_gallde_vid_uppforande', params: { ar: 2014 } }]
    },
    {
      rang: 2, byggnad_id: 'bal_byggnad_yta.99', fastighet: null,
      centroid: { easting: 158200, northing: 6918400, crs: 'EPSG:3014' },
      laege: 'delvis', andel_inom: 0.4, byggnads_ar: null, gallde_vid_uppforande: null,
      dispens_kravs_idag: true, preskriberas: false, poang: 3,
      grunder: [{ kod: 'radar.poang_delvis', params: { andel: 0.4 } },
        { kod: 'radar.poang_ar_okant', params: {} }]
    }
  ],
  kandidater_trunkerade_till: 2,
  poangmodell: [{ kod: 'radar.modell_lage', params: {} }],
  juridisk_not: { kod: 'radar.juridisk_not', params: {} },
  osakerheter: [{ kod: 'runner.dispenser_ej_kontrollerade', params: {} }],
  kallor: [{ beskrivning: 'SundsvallsKommun:bal_byggnad_yta (WFS)', url: 'https://example.se/wfs' }],
  hamtad: '2026-08-19T10:00:00Z'
};

test('rubriken bär antal kandidater av antal byggnader', () => {
  assert.equal(renderRadarRubrik(RADAR, TEXTS.sv), '3 kandidater av 57 byggnader i vyn');
  assert.equal(renderRadarRubrik(RADAR, TEXTS.en), '3 candidates of 57 buildings in view');
});

test('listan: en rad per kandidat med rang, fastighet, år, poäng och grunder', () => {
  const html = renderRadarLista(RADAR, TEXTS.sv, 'sv');
  assert.match(html, /data-rang="1"/);
  assert.match(html, /ALNÖ-USLAND 1:45/);
  assert.match(html, /2014/);
  assert.match(html, /6 p/);
  assert.match(html, /helt inom strandskyddszon \(\+3\)/);
  // Okänd fastighet och okänt år redovisas, tystas inte.
  assert.match(html, /beteckning saknas/);
  assert.match(html, /»Ej fastställt«/);
  // Varje rad är en knapp som bär centroiden (EPSG:3014) för hopp i kartan.
  assert.match(html, /data-e="158140.4" data-n="6918389.3"/);
});

test('listan deklarerar trunkering, poängmodell, juridisk not, osäkerheter och källor', () => {
  const html = renderRadarLista(RADAR, TEXTS.sv, 'sv');
  assert.match(html, /Visar 2 av 3/);
  assert.match(html, /Läge: helt inom zon \+3/);
  assert.match(html, /handläggaren beslutar, alltid/);
  assert.match(html, /gt-osakerhet/);
  assert.match(html, /href="https:\/\/example.se\/wfs"/);
});

test('listan på engelska använder engelska meddelanden', () => {
  const html = renderRadarLista(RADAR, TEXTS.en, 'en');
  assert.match(html, /entirely within a shoreline protection zone/);
  assert.match(html, /Showing 2 of 3/);
});

test('tom kandidatlista ger ett ärligt tomläge', () => {
  const html = renderRadarLista({ ...RADAR, kandidater: [], antal_traffar: 0 }, TEXTS.sv, 'sv');
  assert.match(html, /Inga byggnader möter strandskyddszon i vyn/);
});

test('bboxFranExtent transformerar båda hörnen och sorterar min/max', () => {
  const proj = ([x, y]) => [x + 1000, y - 1000];
  assert.deepEqual(bboxFranExtent([10, 20, 30, 40], proj), [1010, -980, 1030, -960]);
  // Inverterad transform får inte ge ett inverterat bbox.
  const spegel = ([x, y]) => [-x, -y];
  assert.deepEqual(bboxFranExtent([10, 20, 30, 40], spegel), [-30, -40, -10, -20]);
});

test('HTML i backenddata neutraliseras', () => {
  const farlig = { ...RADAR, kandidater: [{ ...RADAR.kandidater[0], fastighet: '<img src=x onerror=1>' }] };
  const html = renderRadarLista(farlig, TEXTS.sv, 'sv');
  assert.doesNotMatch(html, /<img/);
});

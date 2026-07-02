# Spike C — data findings & candidate protagonist properties

> Working document (English during development). Produced 2026-07-02 by running
> `spikes/spike-c/find_candidates.py` live against `karta.sundsvall.se/geoserver/ows`.

> **DISCLAIMER — read before reusing:** the properties below are real, lawfully
> registered buildings drawn from open registry data. They are candidates as
> *realistic geography* for the demo. **All violation scenarios in the demo are
> fictional** and attached to *synthetic* permit data (`data/synthetic/`). Nothing
> here states or implies that any real property violates anything. Before the
> repo goes public, the team decides whether to keep or anonymise designations.

## 1. Critical infrastructure finding: INTERSECTS is dead on this GeoServer

- `CQL_FILTER=INTERSECTS(...)` and `DWITHIN(...)` silently return **0 matches** —
  even for a polygon covering all of Sweden, in every CRS interpretation tested.
  No error is raised; the filter just matches nothing.
- `CQL_FILTER=BBOX(geom, e1, n1, e2, n2, 'EPSG:3006')` **works** (attribute +
  bbox filters combine fine).
- **WMS GetFeatureInfo is the reliable point-in-polygon**: true geometric test,
  server-side, and with `propertyName=<attr>` it returns attributes *without*
  geometry (tiny responses — essential, strandskydd features are ~2 MB each).
  Pattern (EPSG:3006, WMS 1.3.0 axis order = northing,easting):

  ```
  ows?service=WMS&version=1.3.0&request=GetFeatureInfo
     &layers=L&query_layers=L&crs=EPSG:3006
     &bbox=N-40,E-40,N+40,E+40&width=81&height=81&i=40&j=40
     &info_format=application/json&propertyName=FBET
  ```

**Design consequence for `mcp-geodata`/`mcp-delta`:** never rely on WFS spatial
functions beyond BBOX on this server; implement point queries via GetFeatureInfo
and polygon overlay client-side (fetch small vector features by BBOX, compute
locally). Verify the same on other municipalities' servers before assuming.

Useful attributes discovered: buildings carry **`bal_nybyggnadsar` (build year)**
and `bal_tillbyggnadsar` (extension year); `UpphavdaStrandskydd_yta` carries
`Beslutsdat` (decision date of the lifted zone); detaljplan carries `AKTBET` +
`PLANKARTA`/`PLANHANDL` (links toward scanned plan PDFs).

## 2. Method

1. Fetch buildings with `bal_nybyggnadsar BETWEEN 2008 AND 2020` in three
   coastal strips (Alnö west coast, south coast Nolby–Juniskär, north shore).
   Result: **337 buildings** (99 + 140 + 112, live counts 2026-07-02).
2. For the 60 closest to build-year 2015: GetFeatureInfo point tests against
   strandskydd / utvidgat / upphävt / detaljplan / fastighet.
3. Score for demo value: inside strandskydd (+5), detaljplan coverage (+2),
   build year 2012–2017 (+2, appears inside the photo series and near the
   10-year preskription edge), komplementbyggnad (+1), attefall-sized 15–60 m²
   (+1), lifted zone (−2).

Full ranked list: `spikes/spike-c/out/candidates.json` (git-ignored; rerun the
script to regenerate).

## 3. Recommended protagonist: ALNÖ-USLAND 1:45 (score 9)

Waterfront property on Alnö's west coast, centroid **EPSG:3006 ≈ (624526, 6917930)**.

- **Komplementbyggnad 55.5 m², nybyggnadsår 2014** — attefall was introduced
  2014-07-02 with a 25 m² cap (30 m² from 2020): a 55 m² outbuilding is 2×
  the limit → exactly the legal question Fall 1 turns on.
- Same property: **new main house 325 m², also 2014** (replaced an older house).
- **Inside `Lansstyrelsen:Strandskydd_yta`** → Fall 7 geometry is real.
- **Visually verified change:** in `Orto2011_wms` the old orange-roofed house
  stands; in `Orto2015_wms` (and `ortofoto25cm` today) the plot is transformed —
  the redevelopment is clearly visible between the two photo years. The demo's
  "structure appears between photos" moment works on real imagery here.
- No detaljplan coverage (typical rural coast) → the demo must use the
  *utanför detaljplan* rule branch for Fall 1/3 — realistic and shows depth.
  (If we also want an *inside detaljplan* variant, the NOLBY 5/6 and SKOTTSUND
  areas on the south coast scored dp=yes.)

Runner-up candidates: ALNÖ-VI 3:100 (93 m² komplement 2014, in zone, 250 m
away), NJURUNDA PRÄSTBOL 1:117 (61.5 m² komplement 2014, in zone, south coast),
ALNÖ-VI 3:109 / ALNÖ-USLAND 7:1 / RÖKLAND 1:82 (houses 2015–2016 in zone).

## 4. Proposed Tillsynsradar demo zone: NW Alnö coastal strip

Bounding box **EPSG:3006 (624300, 6915900) – (625900, 6918200)** (~1.6 × 2.3 km).
Contains ≥5 of the top-scoring buildings incl. the protagonist and runner-up —
a natural, honest sweep area for the radar finale ("scan one zone, rank
candidates, the handläggare decides").

## 5. Caveats / follow-ups for Sprint 1 (Orestis)

- Tight-zoom GetMap (<150 m bbox) on the cascaded `Orto*_wms` layers deserves a
  QGIS sanity check: verify georeferencing consistency at high zoom between
  years before trusting pixel-level deltas (wide crops ±120 m verified OK;
  responses are deterministic — repeat fetch is byte-identical).
- Check 1975/1960 coverage over the radar zone via `HistoriskaOrtofoton1975metadata_wms`
  (needed for the "existed before 1975" strandskydd branch).
- Confirm registry vs imagery footprint alignment for the protagonist
  (bal_byggnad_yta polygon over Orto2015) — first input for mcp-delta.
- Encoding note: WFS JSON comes back with Windows-1252-ish artifacts in Swedish
  chars ("G�llande") in some clients — force UTF-8 handling in mcp servers.

# Data access — verified findings

> Working document (English during development; delivery docs will be in Swedish).
> Last verified: **2026-07-02** live against the endpoints below. Re-run the curl commands to re-verify.

## 1. Sundsvall GeoServer — OPEN, works today

Base endpoint: `https://karta.sundsvall.se/geoserver/ows`

### WFS layers verified present (GetCapabilities) and retrievable (GetFeature)

| Purpose | Layer | Notes |
|---|---|---|
| Property polygons | `SundsvallsKommun:Fastighet_yta` | **Better than boundary lines for click-to-select.** GetFeature returns MultiPolygon. |
| Property boundaries | `SundsvallsKommun:FastighetGrans_linje` | As listed in tender xlsx |
| Property designations | `SundsvallsKommun:FastighetBeteckning_punkt`, `FastighetBeteckningFullstandig_punkt` | For labels/search |
| Buildings (registry) | `SundsvallsKommun:bal_byggnad_yta`, `td_ovrigbyggnad_yta`, `td_byggnad_linje` | The "expected reality" layer for delta comparison |
| Addresses | `SundsvallsKommun:Adressplats_punkt`, `bal_adressplats_punkt` | |
| **Strandskydd** | `Lansstyrelsen:Strandskydd_yta` | Verified: returns MultiPolygon zones |
| **Strandskydd extended (300m)** | `Lansstyrelsen:UtvidgatStrandskydd_yta`, `UtvidgatStrandskydd_linje` | **Bonus find — not in tender xlsx.** Fall 7 nuance. |
| **Strandskydd revoked** | `Lansstyrelsen:UpphavdaStrandskydd_yta` | **Bonus find.** Areas where protection was lifted — must check before flagging violations. |
| Detaljplan (vectorised) | `RIGES:DetaljplanGallande_yta`, `DetaljplanGallande_minusNGP_yta`, `AnvandningsBestammelser_*`, `EgenskapsBestammelser_*`, `NGP_Detaljplan_yta` + NGP_* family | Full RIGES + NGP families present |
| Kulturmiljö | `Lansstyrelsen:Kulturmiljoprogram_yta`, `RiksintresseKulturmiljovard_yta`, `Byggnadsminnen_punkt`, `SundsvallsKommun:StenstansinventeringByggnader_yta` | For Fall 5 (vision) |
| Naturreservat | `Naturvardsverket:Naturreservat_yta` | Fall 7 naturvärden cross-check |
| Oblique photo footprints | `SundsvallsKommun:Snedbilder_yta` | Coverage polygons only; actual images via MapSpace (key pending) |

Also present: neighbouring municipalities' data under `KommunforbundetVn:*` (Ånge, Härnösand, Timrå…) incl. `Lansstyrelsen:Ange_Strandskydd_yta` — useful for the multi-municipality story.

### WMS orthophoto time series — THE TIMELINE IS ALREADY SERVED

**18 years available directly from the municipal GeoServer, no Lantmäteriet credentials needed:**

- Historical (grayscale): `Lantmateriet:HistoriskaOrtofoton1960_wms`, `...1975_wms` ← **1975 = strandskydd threshold year**, `...1998_wms`, `...1999_wms`, `...2001_wms`, `...2002_wms`
- Modern (colour): `Lantmateriet:Orto2007_wms`, `2010`, `2011`, `2012`, `2013`, `2015`, `2016`, `2017`, `2019`, `2020`, `2021`, `2023` (same naming pattern)
- Current: `Lantmateriet:ortofoto25cm`, `ortofoto50cm`, `Ortofoto_IR_wms` (infrared!)
- Coverage/metadata layers: `HistoriskaOrtofoton1960metadata_wms`, `...1975metadata_wms`, `ortofoto25cm_metadata` — use these to check WHERE each year has coverage before picking demo properties.
- Detaljplan WMS group: `Plandatabas_NGP` ✓

Verified with live GetMap (both returned real imagery, 2011 colour / 1975 grayscale):

```bash
curl "https://karta.sundsvall.se/geoserver/ows?service=WMS&version=1.3.0&request=GetMap&layers=Lantmateriet:Orto2011_wms&crs=EPSG:3014&bbox=6912000,149500,6913000,150500&width=512&height=512&format=image/png" -o orto2011.png
curl "https://karta.sundsvall.se/geoserver/ows?service=WMS&version=1.3.0&request=GetMap&layers=Lantmateriet:HistoriskaOrtofoton1975_wms&crs=EPSG:3014&bbox=6912000,149500,6913000,150500&width=512&height=512&format=image/png" -o orto1975.png
```

### CRS — careful

Layers declare mixed DefaultCRS: **EPSG:3006** (SWEREF99 TM), **EPSG:3013**, **EPSG:3014** (SWEREF99 17 15 — local zone for Sundsvall, false easting 150000). GetFeature on `Fastighet_yta` and `Strandskydd_yta` returned coordinates consistent with EPSG:3014 (x≈150 000, y≈6.91M, axis order northing,easting in WFS 2.0). **Rule: always request an explicit `srsName`/`crs` per call; normalise everything to EPSG:3006 internally.**

### Reproduce the capability check

```bash
curl "https://karta.sundsvall.se/geoserver/ows?service=WFS&request=GetCapabilities&version=2.0.0" -o wfs_caps.xml   # ~577 KB
curl "https://karta.sundsvall.se/geoserver/ows?service=WMS&request=GetCapabilities&version=1.3.0" -o wms_caps.xml   # ~1.9 MB
curl "https://karta.sundsvall.se/geoserver/ows?service=WFS&version=2.0.0&request=GetFeature&typeNames=Lansstyrelsen:Strandskydd_yta&count=1&outputFormat=application/json"
```

## 2. Not yet verified (pending)

| Source | Status | Action |
|---|---|---|
| Lantmäteriet direct APIs (STAC ortofoto download, Belägenhetsadress, Byggnad vektor) | Needs account `suns0011` credentials | Orestis — Sprint 0/1 |
| MapSpace snedbilder (actual oblique images) | Needs API key | Request sent? — Nikos, Sprint 0 |
| NGP Detaljplaner (national platform) | Needs consumer account; coverage incomplete anyway | Low priority — RIGES layers above cover the demo need |
| Scanned plan PDFs | URL pattern known: `https://karta.sundsvall.se/Detaljplan/SkannadHandling/2281K-DP-294.pdf` | Verify a handful of plan IDs when picking demo properties |
| Kommunens testärenden (mock bygglov cases promised by beställaren) | Not received | Ask in next kontakt with Sundsvall |

## 3. Consequences for the sprint plan

1. **Sprint 1 Spike C is de-risked**: property/building/strandskydd/detaljplan vectors AND the full orthophoto timeline are reachable through ONE open endpoint. No credential blockers for the vertical slice.
2. **1975 orthophotos are grayscale, lower quality** (verified visually) → confirms the design decision: blink comparator + human confirmation for old years; automated delta only on modern colour years.
3. `UpphavdaStrandskydd_yta` and `UtvidgatStrandskydd_yta` must be part of Fall 7 logic (a naive check against `Strandskydd_yta` alone would produce false positives/negatives — this nuance belongs in the regelgraf and in the pitch).
4. Use the `*metadata_wms` coverage layers when selecting the protagonist property — need a coastal spot covered by many years incl. 1975.

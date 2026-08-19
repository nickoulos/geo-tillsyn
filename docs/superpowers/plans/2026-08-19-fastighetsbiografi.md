# Geo-Tillsyn v0.7 Fastighetsbiografi — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Spec:** `docs/superpowers/specs/2026-08-19-fastighetsbiografi-design.md` — read it first; it is the source of truth for behaviour and wording.

**Goal:** Make the thesis "Verklighet vs Rättighet över Tid" visible as one picture (a four-lane biography strip under the map), put the findings first in the panel (display-size numbers, collapsed uncertainties, explicit empty Beslut block, property-perspective strandskydd card), make the map narrate (auto-zoom, click marker, hatched overlay, zone layer), and add radar-lite (ranked candidates in the zone) for the demo finale.

**Architecture:** Same split as v0.5: pure `.mjs` logic modules tested with `node --test`; DOM components in `.js`; `geotillsyn.js` = Origo wiring only; one injected stylesheet. Backend additions are small and additive (three new fields, one new GeoJSON endpoint) following the existing `fall3_geometri` / `custom_route` patterns, TDD with hermetic pytest.

**Tech Stack:** Python 3 (FastMCP/Starlette, shapely), vanilla JS, webpack 5 (`externals: ['Origo']`), `node --test`. No new dependencies.

## Global Constraints

- **Neutrality rule (legal):** the UI never generates a guilt-word or an all-clear the backend didn't send. Headlines/chips/strip labels are composed only from backend fields or `regler.json`; when nothing composable exists show "Se underlag". Summary chips describe *underlag* (evidence state), never an outcome.
- **Statutory terms stay Swedish verbatim** in both languages. Only UI chrome is translated. JS object keys ASCII.
- **MCP contracts additive only**; compact JSON stays ≤ 8 kB (strandskydd: `vald_byggnad_id` + reorder only; olovligt: two small dicts/lists).
- `/api/strandskydd/geometri` is map-only (like `/api/lovavvikelse/geometri`) — never registered as an MCP tool.
- Commit style `feat(origo): …` / `feat(webapi): …` / `test(...)` / `docs(...)`; each commit ends with `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- Backend commands run from repo root `C:\Users\N.KOULOS\Documents\personal\4sight\Gov4tech\geo-tillsyn` with `.venv\Scripts\python.exe -m pytest -q`. Plugin commands from `origo-plugin\` (`npm test`, `npm run build`).
- `origo-plugin/build/` is gitignored; after `npm run build` copy `build/js/geotillsyn.min.js` → `build/plugins/geotillsyn.min.js` (what `build/index.html` loads) when verifying in a browser.

## File Structure

```
src/geo_tillsyn/
  datering.py         MODIFY  DateringsResultat += narvaro_per_ar, uteslutna_ar
  runner.py           MODIFY  fall1 compact += narvaro_per_ar/uteslutna_ar;
                              analysera_punkt += vald_byggnad_id (vald träff först);
                              NEW rangordna_traffar(), fall7_geometri()
  server.py           MODIFY  NEW route /api/strandskydd/geometri
tests/
  test_datering.py    MODIFY  classification fields
  test_fall1_runner.py MODIFY new fields present
  test_runner.py      MODIFY  vald_byggnad_id + ordering; rangordna_traffar; fall7_geometri
  test_webapi.py      MODIFY  new route (200 / 404 / OPTIONS)

origo-plugin/src/
  biografi-logik.mjs  CREATE  xSkala, klassificeraAr, lagBand, lovbefrielseBand, klockor, registerGap
  biografi.js         CREATE  SVG strip component (replaces timeline.js)
  timeline.js         DELETE  (after biografi.js is wired)
  tidslinje-logik.mjs KEEP    (narmasteAr/stegAr reused)
  panel.js            MODIFY  summary chips, display headline, uncertainties chip,
                              strandskydd property perspective + radar button,
                              Beslut block, kandidatlista view
  dossier.mjs         MODIFY  composeHeadline -> {tal, under, badge}; underlagsLage()
  i18n.mjs            MODIFY  new strings (sv+en)
  styles.mjs          MODIFY  panel 420px, type scale, strip, chips, radar, beslut
  geotillsyn.js       MODIFY  wiring: strip, auto-zoom, click marker, hatch styles,
                              zone layer toggle, radar layer + list
origo-plugin/tests/
  biografi-logik.test.mjs CREATE
  dossier.test.mjs        MODIFY
  i18n.test.mjs           MODIFY
origo-plugin/demo/autoklick.html CREATE (dev harness, copied into build/ for headless checks)
origo-plugin/README.md, B-LIVE-STATUS.md MODIFY
```

---

### Task 1: Backend additions (hermetic, TDD)

**Files:** `src/geo_tillsyn/datering.py`, `runner.py`, `server.py`; tests as listed.

**Interfaces:**
- `DateringsResultat.narvaro_per_ar: dict[int, str]` values `'narvaro'|'franvaro'|'otydlig'` for every year in `poang_per_ar`; `uteslutna_ar: list[int]` = the content-less years (same list the `datering.argangar_utan_innehall` message carries). Both default-empty.
- Fall 1 compact JSON (`analysera_fall1_punkt`) gains `"narvaro_per_ar": {str(year): str}` and `"uteslutna_ar": [int]`.
- `analysera_punkt` (Fall 7) gains `"vald_byggnad_id": str | None` = `_valj_byggnad(byggnader, punkt, radie_m)` id (None if no buildings — do NOT raise; Fall 7 must keep working on empty radius). If the chosen building is a träff it is moved to index 0 of `traffar` (before truncation to `_MAX_TRAFFAR_I_SVAR`).
- `rangordna_traffar(traffar: list[dict]) -> list[dict]` pure: returns copies with `"rang"` (1-based) per spec §5 ordering: group (a) `gallde_vid_uppforande is True`, (b) `byggnads_ar is None`, (c) `gallde_vid_uppforande is False`; within group `laege == 'inom'` before `'delvis'`, then `byggnad_id` ascending.
- `fall7_geometri(ows_url, punkt, nu, radie_m=150.0, hamta_wfs=hamta_wfs_robust) -> dict` = GeoJSON FeatureCollection (`"crs"` note EPSG:3014 like `fall3_geometri`) of ALL träffar (no truncation) with polygon geometry and properties `{byggnad_id, laege, byggnads_ar, gallde_vid_uppforande, dispens_kravs_idag, preskriberas, har_atgarder: bool, rang}` plus top-level `"antal_traffar"`, `"vald_byggnad_id"`. Raises `ValueError(M("runner.ingen_byggnad_hittad", ...))` when no buildings in radius.
- Route `GET|OPTIONS /api/strandskydd/geometri` mirroring `api_lovavvikelse_geometri` (400/404/500 mapping, CORS, default radius 150).

- [ ] Step 1: Write failing tests (datering classification; fall1 fields; vald_byggnad_id + ordering; rangordna_traffar ordering incl. ties; fall7_geometri shape with the existing fake-WFS fixtures in `tests/`; webapi route 200/404/OPTIONS with monkeypatched `fall7_geometri`).
- [ ] Step 2: Implement minimal code; keep `_MAX_TRAFFAR_I_SVAR` semantics for the compact JSON.
- [ ] Step 3: `pytest -q` all green (≥ 164 + new). Check compact strandskydd JSON size on the existing 27-träff fixture still < 8 kB.
- [ ] Step 4: Commit `feat(webapi): narvaro_per_ar, vald_byggnad_id, /api/strandskydd/geometri (radar-lite)`.

---

### Task 2: Panel — findings first

**Files:** `origo-plugin/src/{dossier.mjs,i18n.mjs,panel.js,styles.mjs,geotillsyn.js}`, tests `dossier.test.mjs`, `i18n.test.mjs`.

**Interfaces:**
- `composeHeadline(checkKey, data, t, sprak)` now returns `{tal: string, under: string, badge: string|null}` (keep a `composeHeadlineText()` shim returning `tal + ' · ' + under` if any test/consumer still needs a string). Rules per spec §3: olovligt → `tal = "2002 → 2007"` (or "→ 2007" when `sista_ar_utan` null, per existing `rubrikOlovligt` wording), `under = "först synlig i ortofoto · registret säger 2014"`, `badge = t.avviker` iff `bal_forenligt === false`; lovavvikelse → `tal = "+90,3 m²"`, `under = "+38,4 % mot godkänt lov · SBN 2009-0412"`; strandskydd → based on the träff whose `byggnad_id === data.vald_byggnad_id` (fallback: `traffar[0]` only if `vald_byggnad_id` is null): `tal = t.inomStrandskydd | t.delvisInomStrandskydd | t.utanforStrandskydd`, `under = "zon 2281K-ÖVR-241 · uppförd 2014 · ingen preskription"` built only from present fields (`zon_referenser`, `byggnads_ar`, `preskriberas === false → t.ingenPreskription`, `dispens_kravs_idag === true → t.dispensKravs`); no composable fields → `{tal: t.seUnderlag, under: '', badge: null}`.
- `underlagsLage(checkKey, data, status) -> 'finns'|'osakert'|'inget'|'hamtar'|'fel'` pure (spec §3 rules).
- `panel.js`: `setSammanfattning({olovligt, lovavvikelse, strandskydd})` chips (clicking scrolls to card); `setCardResult(key, {headline:{tal,under,badge}, body, osakerheter: N})` renders the display headline + an "N osäkerheter ▸" toggle chip (the `.gt-osakerhet` block is hidden until toggled); `setStrandskyddKandidater(antalAndra, onVisa)` row + button under the strandskydd headline; a static **Beslut** block rendered by `startaAnalys()` after the three cards (lock icon, dashed empty field, sub-line); `visaKandidatlista(rader, {onValj, onHover, onTillbaka})` / `visaKort()` view switch (list UI used by Task 5 — implement the DOM now, wire later).
- `renderCheckBody` moves uncertainties into a container `.gt-osakerhet[hidden]` that the chip toggles.
- Type scale: panel 420 px, base 14 px, `.gt-kort__tal` 22 px/800 tabular-nums, `.gt-rad` 13.5 px, Bedömning open by default.
- i18n: `underlagFinns`, `underlagOsakert`, `underlagInget`, `underlagHamtar`, `underlagFel`, `osakerheterChip(n)`, `avviker`, `forstSynlig`, `registretSager(ar)`, `motGodkantLov`, `inomStrandskydd`, `delvisInomStrandskydd`, `utanforStrandskydd`, `zon(ref)`, `uppford(ar)`, `ingenPreskription`, `dispensKravs`, `andraByggnader(n)`, `visaKandidater`, `beslutRubrik`, `beslutTomt`, `beslutUnder`, `granskadPunkt`, plus radar strings for Task 5 (`kandidaterRubrik`, `kandidaterUnder`, `kandidaterForklaring`, `tillbaka`, `byggarOkant`). Both sv and en; test asserts key parity.

- [ ] Step 1: Failing tests for `composeHeadline` (all three checks incl. fallback and the `vald_byggnad_id` selection), `underlagsLage`, i18n parity.
- [ ] Step 2: Implement; update `geotillsyn.js` `renderaKort` to pass the object headline + count and to call `setSammanfattning` after each card settles.
- [ ] Step 3: `npm test` green, `npm run build` green, `node --check build/js/geotillsyn.min.js`.
- [ ] Step 4: Commit `feat(origo): fynden forst - sammanfattningschips, display-rubriker, osakerhetschip, beslut-block, strandskydd ur fastighetsperspektiv`.

---

### Task 3: Biography strip

**Files:** create `src/biografi-logik.mjs`, `src/biografi.js`, `tests/biografi-logik.test.mjs`; modify `styles.mjs`, `geotillsyn.js`; delete `timeline.js`.

**Interfaces (pure, `biografi-logik.mjs`):**
- `DOMAN = {fran: 1960, till: <currentYear+1>}` built by `skapaDoman(idagAr)`.
- `xSkala(doman, bredd)(isoDateOrYear) -> px` linear; years accepted as number or ISO string (use mid-year for bare years? No: bare year = Jan 1 — keep simple and documented).
- `klassificeraAr(olovligt|null, years) -> Map<year, 'narvaro'|'franvaro'|'otydlig'|'utesluten'|'okand'>` from `narvaro_per_ar` + `uteslutna_ar`; all `years` present; null data → all `'okand'`.
- `lagBand(regler) -> [{namn, sfs, fran, till|null}]`, `lovbefrielseBand(regler) -> [{namn, max_kvm, fran, till|null}]`, `strandskyddBand(regler) -> {fran}`.
- `registerGap(olovligt) -> {fran: forsta_ar_med, till: bal_nybyggnadsar, avviker: bal_forenligt === false} | null`.
- `klockor(olovligt, strandskyddTraff, regler) -> [{nyckel:'rattelse'|'sanktion'|'strandskydd', startSaker, startOsaker, slutSaker, slutOsaker, oandlig, status}]` where `status` is taken verbatim from backend (`rattelse_preskriberad`, `sanktionsavgift_mojlig`, `preskriberas`) and may be null; returns [] without dating interval. Strandskydd clock only if `strandskyddTraff && strandskyddTraff.laege !== 'utanfor'`.
- `biografi.js` `skapaBiografi({years, startAr, regler, t, onArByte, onRegelverk})` → `{el, setAr, setData({olovligt, lovavvikelse, strandskyddTraff}), setKollapsad, uppdateraTexter}`; renders SVG with four lanes + axis ticks + cursor + "idag" line; hover tooltip with `poang_per_ar`; click on a Verklighet dot → `setAr` + `onArByte`; cursor drag on axis; ‹ › buttons; collapse button; "Regelverk YYYY" button → `onRegelverk(year)` (wiring shows existing `renderKontextDetalj` in a popover inside the strip).
- Strip is positioned `absolute; left:0; right:0; bottom:0` inside the map root, height 170 px (collapsed 40 px); `.gt-oppen` no longer shifts it (it spans the map area, panel overlays right edge — strip right padding = panel width when open).

- [ ] Step 1: Failing tests for every pure function (incl. clocks with/without strandskydd, gap null when forenligt true, classification defaults).
- [ ] Step 2: Implement logic, then component, then wire in `geotillsyn.js` (`skapaBiografi` replaces `skapaTidslinje`; call `setData` when each card settles; `setAr` kept in sync with `visaAr`).
- [ ] Step 3: `npm test`, `npm run build`, `node --check`; headless screenshot (Task 6 harness) to eyeball lane rendering.
- [ ] Step 4: Commit `feat(origo): fastighetsbiografi - fyra spar (verklighet/register/rattighet/klockor) ersatter tidslinjepillen`.

---

### Task 4: Map behaviours

**Files:** `geotillsyn.js`, `styles.mjs`.

- Click marker vector layer (`geotillsyn-klick`): ring (r 9, stroke accent 2 px, white halo) + dot; cleared on new click.
- Auto-zoom: after `/api/lovavvikelse/geometri` success → `map.getView().fit(extentOf(godkant ∪ verkligt), {padding:[40, panelOpen?460:40, 210, 40], maxZoom: <zoom where resolution ≈ 0.1 m/px>, duration: 400})`; on 404/error → fit to 80 m square around the click with same padding.
- Overlay styles: stroke 3 px + semi-transparent fill (`rgba(30,78,216,.18)` / `rgba(200,40,40,.18)`); legend 13 px.
- When strandskydd result arrives and the vald träff is `inom|delvis`, set the `Lansstyrelsen:Strandskydd_yta` layer visible via `hittaLager(...)`.setVisible(true) (layer name from demo config — look it up in `demo/geotillsyn.json`).

- [ ] Step 1: Implement; keep all behaviour behind null-checks (OL may be missing in tests).
- [ ] Step 2: Build + headless screenshot shows zoomed footprint with marker + overlay.
- [ ] Step 3: Commit `feat(origo): kartan berattar - autozoom, klickmarkor, skrafferat overlagg, zonlager`.

---

### Task 5: Radar-lite

**Files:** `geotillsyn.js`, `panel.js` (wire the list from Task 2), `styles.mjs`, i18n.

- Button "Visa kandidater i kartan" → fetch `/api/strandskydd/geometri` (same point/radius 150) → draw features in layer `geotillsyn-radar` (amber fill `rgba(217,142,20,.25)`, stroke 2 px; numbered label = `rang` via `ol.style.Text`), then `panel.visaKandidatlista(rows)`; rows sorted by `rang`; hover row → highlight feature; click row → `pahandlaKlick({coordinate: centroid(feature) in map CRS})`; Tillbaka → `panel.visaKort()` (keep radar layer until next click clears it).
- Empty/404 → info row in the card.

- [ ] Step 1: Implement + build; headless screenshot of radar view via harness (harness gets a `?radar=1` flag that clicks the button after cards settle).
- [ ] Step 2: Commit `feat(origo): radar-lite - rangordnade kandidater i strandskyddszon`.

---

### Task 6: Harness, verification, docs

- `origo-plugin/demo/autoklick.html`: same as `build/index.html` but dispatches `singleclick` at a coordinate from `?e=&n=` (EPSG:3006), optional `?radar=1`, `?lang=en`. Copy into `build/` when running: `chrome --headless=new --window-size=1600,900 --timeout=120000 --virtual-time-budget=120000 --screenshot=... "http://localhost:9967/autoklick.html?e=624526&n=6917930"`.
- Capture: tomläge, komplementbyggnad (E 624526 N 6917930), huvudbyggnad (E 624518 N 6917923), radar, EN. Fix what looks wrong.
- Update `origo-plugin/README.md` + `B-LIVE-STATUS.md` (v0.7 section, run instructions unchanged). Update bid folder `Demomanus_45min_Foursight_Lab.md` VISAS lines to match the new UI (biografi-strip, chips, Beslut block, radar-lite wording).
- Commit `docs(origo): v0.7 fastighetsbiografi - status, README, demomanus`.

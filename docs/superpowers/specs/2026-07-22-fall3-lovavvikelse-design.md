# Fall 3 — Lovavvikelse (avvikelse från beviljat lov): vertical slice design

**Date:** 2026-07-22 · **Status:** approved by Nikos (chat) · **Repo:** geo-tillsyn

Fall 3 asks: *the building was erected differently from what the permit allows —
placement, area, height, appearance.* REALITY = the actual building (WFS +
ortofoto). RULE = the granted lov. DIFF = quantified deviation. TIME = when the
deviation was completed → which clocks run.

**Hard constraint:** no access to real bygglov/byggärenden this phase (Sokigo
Nova needs TRIP-avtal; e-Avrop F4: ByggR exports "återkommer"). The kommun
expects synthetic testärenden. Real permits, where they exist, are scanned
raster PDFs (`karta.sundsvall.se/Detaljplan/SkannadHandling/2281K-*.pdf`).

**Decisions taken in brainstorm (Nikos, 22 Jul):**
1. Both layers in this slice: structured mock-ByggR store **and** synthetic
   scanned situationsplan PDF with an OCR lov-tolk.
2. Lov-tolk = Tesseract OCR + per-field cross-check against the register —
   deterministic, no LLM, works in the zero-cost demo stack.

## 1. Lovarkiv (mock-ByggR store)

New module `src/geo_tillsyn/lovarkiv.py` + data at `data/synthetic/lovarkiv/`
(one JSON per ärende + one scanned handling PDF). Record schema (fields chosen
to survive a later swap to real ByggR exports):

```json
{
  "syntetisk": true,
  "anmarkning": "Syntetiskt testärende — inga verkliga byggärenden (prototypfas, inget PuB-avtal).",
  "dnr": "SBN 2009-0412",
  "fastighet": "ALNÖ-USLAND 1:45",
  "beslutsdatum": "2009-06-19",
  "laga_kraft": "2009-07-24",
  "atgard": "Nybyggnad av enbostadshus",
  "byggnadsarea_m2": 80.0,
  "hojd_m": null,
  "godkant_lage": {"crs": "EPSG:3014", "koordinater": [[e, n], ...]},
  "villkor": ["Byggnaden placeras minst 4,5 m från fastighetsgräns."],
  "handling": "data/synthetic/lovarkiv/sbn-2009-0412-situationsplan.pdf"
}
```

API: `hitta_lov(punkt | fastighet) -> LovBeslut | None`. `None` renders the
honest answer *"inget ärende i (test)arkivet"* — for the kommun's unseen
testfastigheter (Q&A F9) the engine must degrade gracefully, never invent a
permit. A missing lov is Fall 1 territory and the tool says so.

## 2. Synthetic scanned handling (raster-only PDF)

Generator `verktyg/generera_handling.py` (repo tool, not shipped in the
package): draws a situationsplan with Pillow — title block (dnr, fastighet,
skala, datum), north arrow, approved outline with printed dimensions and
distance-to-boundary measure, stamp "BEVILJAS" — then embeds the bitmap as a
**raster-only PDF** (no text layer), same nature as the real 2281K scans.
Deterministic (fixed seed, no timestamps in content).

**Mandatory:** every page carries a visible watermark
**"SYNTETISK TESTHANDLING — GEO-TILLSYN PROTOTYP"**. A document that imitates
a municipal record must never exist unlabeled; transparency is also a jury
asset. The generator refuses to render without the watermark text.

## 3. Lov-tolk (OCR + cross-check)

New module `src/geo_tillsyn/lovtolk.py`:

- Rasterize PDF page(s) via **pypdfium2** (pure wheel, no system deps).
- OCR via **pytesseract** → text + per-word confidences.
- Field extraction by regex over OCR text: `dnr`, `beslutsdatum`,
  `byggnadsarea` (BYA … m²), printed dimensions, distance figures. Output
  `TolkatDokument`: `{falt: {varde, konfidens}}` + raw text reference.
- **Cross-check vs register**, per field: `överens` / `avviker` / `saknas`.
  Two independent sources agreeing (or visibly conflicting) is the
  bevisstyrka idea from the concept made concrete.
- **Graceful absence:** if the tesseract binary is missing, the pipeline
  continues register-only and the dossier carries the osäkerhet
  *"OCR ej tillgänglig — handlingen ej maskinellt verifierad"*. The OCR
  callable is injected (like fetchers elsewhere) so tests are hermetic; real
  tesseract is exercised only in an opt-in integration test.

Environment note: tesseract is NOT currently installed on the dev machine —
install step in the plan (Windows: UB Mannheim build or choco, plus `swe`
traineddata).

## 4. Delta-motor (geometric comparison)

New module `src/geo_tillsyn/delta.py`. Inputs: approved polygon (lov),
actual polygon (`bal_byggnad_yta`, live WFS), fastighetsgräns
(`FastighetGrans_linje`, live WFS). All shapely, EPSG:3014. Outputs
(`DeltaResultat`):

- Δarea: m² and % (actual vs approved).
- Placement: centroid shift (m) + parts of the actual building outside the
  approved outline (m²).
- Min distance to fastighetsgräns: approved vs actual (the "2,3 m closer to
  the boundary" number).
- Every figure carries the measurement caveat; nothing hardcoded.

Protagonist scenario: the approved polygon in the synthetic lov is derived
from the real footprint (scaled −15 %, shifted +2,3 m away from the boundary)
so the demo numbers (*≈ +18 % area, 2,3 m closer*) come out of a real
computation against live WFS data — and the same engine runs unchanged on any
(lov, verklighet) pair.

## 5. Juridik (`fall3_lage` in juridik.py)

- **Which law governs the lov:** beslutsdatum 2009 on purpose → ÄPBL 1987:10
  via `regelverk_vid(..., arende_startdatum=...)` — the transition-rule work
  (PBL 2010:900 övergångsbest. p.2) on live display.
- **When was the deviation completed:** reuse `datera_byggnad` on the actual
  footprint → interval → both PBL clocks evaluated at interval bounds
  (11 kap. 20 § rättelse 10 yr; 11 kap. 58 § avgift 5 yr), conservative like
  Fall 1.
- **Väsentlighet is a HUMAN node:** the engine quantifies and classifies
  evidence strength; it never rules "väsentlig avvikelse". Deviations within
  the measurement band (±0,5 m distance, ±2 m² area) →
  `MEASUREMENT_CRITICAL` → manual survey recommended.
- Never a guilt word ("olovligt", "överträdelse") in Bedömningen — same test
  guard as Fall 1/7.

## 6. Dossier, runner, MCP, CLI

- `src/geo_tillsyn/fall3.py`: three-level dossier. **Fakta** with clickable
  källor — the handling PDF, the register record (marked syntetiskt), WFS
  layers, ortofoto years; the OCR-vs-register cross-check rendered per field.
  **Bedömning** with grund + osäkerheter (OCR confidence, mätosäkerhet,
  datering interval). **Beslut** structurally empty.
- `runner.py`: `_fall3_underlag`, `kor_fall3` (writes fall3_dossier.md +
  overlay PNG approved-vs-actual), `analysera_fall3_punkt` (compact JSON,
  < 8 kB, declared truncation).
- `server.py`: tool `analysera_lovavvikelse_vid_punkt(easting, northing,
  radie_m)` → Eneo re-sync brings the catalog to 4 tools (tenant + assistant
  enablement, known drill).
- `cli.py`: `--fall {7,1,3}`.

## 7. Testing & workflow

TDD, hermetic: fake WFS fetchers (as in Fall 1/7), injected fake OCR,
synthetic PDFs built in-test. New test files: `test_lovarkiv`, `test_lovtolk`,
`test_delta`, `test_fall3_juridik`, `test_fall3_dossier`, `test_fall3_runner`.
Live verification on the protagonist at the end (dossier into gitignored
`demo_ut/`).

Workflow per Nikos' standing instruction: **Fable writes specs/tests and
reviews; Sonnet subagents implement.**

## Out of scope (this slice)

- Snedbilder/höjd check (MapSpace key still pending) — höjd renders as
  "Ej fastställt — flygbilder ser inte fasader" osäkerhet.
- Origo overlay in the live map (B-live work item; the runner's PNG overlay
  is the slice-level equivalent).
- Real detaljplan OCR / planstridighet (different legal story, different
  property — future).

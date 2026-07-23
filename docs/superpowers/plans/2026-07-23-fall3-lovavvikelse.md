# Fall 3 — Lovavvikelse Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Vertical slice for Fall 3 (avvikelse från beviljat lov): mock-ByggR lovarkiv + synthetic scanned handling + OCR lov-tolk with register cross-check + geometric delta engine + time-aware juridik + three-level dossier + MCP tool.

**Architecture:** Same pattern as Fall 1/7 — pure core modules with injected fetchers/OCR, a runner that wires live WFS/WMS, compact MCP JSON < 8 kB. New modules: `lovarkiv` (store), `handling` (synthetic PDF drawing), `lovtolk` (OCR + cross-check), `delta` (geometry). `juridik` gains `fall3_lage` (shares PBL-clock logic with `fall1_lage` via an extracted helper). Spec: `docs/superpowers/specs/2026-07-22-fall3-lovavvikelse-design.md`.

**Tech Stack:** Python 3.12, shapely 2, Pillow, numpy, pypdfium2 (PDF→bitmap, pure wheel), pytesseract (OCR; binary optional at runtime), pytest, ruff.

## Global Constraints

- Every new source file starts with a Swedish module docstring + `SPDX-License-Identifier: AGPL-3.0-or-later`.
- Swedish domain naming (`hitta_lov`, `jamfor_lage`, `tolka_handling`), frozen dataclasses, ruff line-length 100.
- **Never a guilt word** in Bedömning/tool output: "olovligt", "överträdelse", "brott" are forbidden as conclusions (guard test in Task 6). The MCP tool NAME may contain "lovavvikelse" (it names the question, not the verdict).
- Tests are hermetic: injected fetchers (`hamta_wfs`, `hamta_wms`) and injected OCR callable. No network, no tesseract binary required to run the suite.
- MCP tool output < 8 kB, references only (no geometry, no imagery).
- CRS: `EPSG:3014` everywhere.
- Synthetic lov records MUST carry `"syntetisk": true`; the loader refuses records without it. Every generated handling page MUST carry the watermark `SYNTETISK TESTHANDLING — GEO-TILLSYN PROTOTYP`; the renderer refuses an empty watermark.
- Commit after each task, message style `feat(fall3): ...`, trailer `Co-Authored-By:` lines as in previous commits.
- Run `python -m pytest -q` (all tests, not just new ones) + `python -m ruff check src tests` before every commit.

---

### Task 1: Lovarkiv (mock-ByggR store)

**Files:**
- Create: `src/geo_tillsyn/lovarkiv.py`
- Create: `data/synthetic/lovarkiv/` (directory; protagonist record arrives in Task 8)
- Test: `tests/test_lovarkiv.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `LovBeslut` (frozen dataclass: `dnr: str, fastighet: str, beslutsdatum: str, laga_kraft: str | None, atgard: str, byggnadsarea_m2: float | None, hojd_m: float | None, godkant_lage: shapely.Polygon, villkor: list[str], handling: Path | None, anmarkning: str, kalla_fil: Path`) and `hitta_lov(katalog: Path, punkt: tuple[float, float] | None = None, fastighet: str | None = None, max_avstand_m: float = 100.0) -> LovBeslut | None`.

- [ ] **Step 1: Write the failing tests**

```python
"""Unit tests for the mock-ByggR lovarkiv (Fall 3).

SPDX-License-Identifier: AGPL-3.0-or-later
"""

import json

import pytest

from geo_tillsyn.lovarkiv import hitta_lov


def _lov_record(dnr="SBN 2009-0412", fastighet="ALNÖ-USLAND 1:45", koords=None, **extra):
    koords = koords or [[100.0, 100.0], [110.0, 100.0], [110.0, 108.0], [100.0, 108.0]]
    record = {
        "syntetisk": True,
        "anmarkning": "Syntetiskt testärende — inga verkliga byggärenden.",
        "dnr": dnr,
        "fastighet": fastighet,
        "beslutsdatum": "2009-06-19",
        "laga_kraft": "2009-07-24",
        "atgard": "Nybyggnad av enbostadshus",
        "byggnadsarea_m2": 80.0,
        "hojd_m": None,
        "godkant_lage": {"crs": "EPSG:3014", "koordinater": koords},
        "villkor": ["Byggnaden placeras minst 4,5 m från fastighetsgräns."],
        "handling": None,
    }
    record.update(extra)
    return record


def _skriv(katalog, namn, record):
    katalog.mkdir(parents=True, exist_ok=True)
    (katalog / namn).write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")


def test_hittar_lov_via_punkt_inom_avstand(tmp_path):
    _skriv(tmp_path, "a.json", _lov_record())

    lov = hitta_lov(tmp_path, punkt=(105.0, 104.0))

    assert lov is not None
    assert lov.dnr == "SBN 2009-0412"
    assert lov.godkant_lage.area == pytest.approx(80.0)
    assert lov.kalla_fil == tmp_path / "a.json"


def test_punkt_langt_bort_ger_none(tmp_path):
    _skriv(tmp_path, "a.json", _lov_record())

    assert hitta_lov(tmp_path, punkt=(5000.0, 5000.0)) is None


def test_hittar_via_fastighetsbeteckning(tmp_path):
    _skriv(tmp_path, "a.json", _lov_record())

    lov = hitta_lov(tmp_path, fastighet="ALNÖ-USLAND 1:45")

    assert lov is not None and lov.fastighet == "ALNÖ-USLAND 1:45"


def test_narmaste_valjs_vid_flera_traffar(tmp_path):
    _skriv(tmp_path, "nara.json", _lov_record(dnr="SBN 2009-0001"))
    fjarran = [[160.0, 100.0], [170.0, 100.0], [170.0, 108.0], [160.0, 108.0]]
    _skriv(tmp_path, "fjarran.json", _lov_record(dnr="SBN 2009-0002", koords=fjarran))

    lov = hitta_lov(tmp_path, punkt=(105.0, 104.0))

    assert lov.dnr == "SBN 2009-0001"


def test_record_utan_syntetisk_flagga_avvisas(tmp_path):
    record = _lov_record()
    del record["syntetisk"]
    _skriv(tmp_path, "a.json", record)

    with pytest.raises(ValueError, match="syntetisk"):
        hitta_lov(tmp_path, punkt=(105.0, 104.0))


def test_tom_katalog_ger_none(tmp_path):
    assert hitta_lov(tmp_path, punkt=(0.0, 0.0)) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_lovarkiv.py -q`
Expected: FAIL / error — `ModuleNotFoundError: No module named 'geo_tillsyn.lovarkiv'`

- [ ] **Step 3: Implement `src/geo_tillsyn/lovarkiv.py`**

```python
"""Lovarkiv: mock-ByggR-lager med syntetiska bygglovsärenden (Fall 3).

Prototypfasen har ingen åtkomst till riktiga byggärenden (Sokigo Nova kräver
TRIP-avtal) — arkivet håller SYNTETISKA testärenden och vägrar läsa poster som
inte uttryckligen är märkta `syntetisk: true`. Ett saknat lov är ett ärligt
svar (None), aldrig en gissning.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from shapely.geometry import Point, Polygon


@dataclass(frozen=True)
class LovBeslut:
    """One granted (synthetic) bygglov from the mock archive."""

    dnr: str
    fastighet: str
    beslutsdatum: str
    laga_kraft: str | None
    atgard: str
    byggnadsarea_m2: float | None
    hojd_m: float | None
    godkant_lage: Polygon
    villkor: list[str]
    handling: Path | None
    anmarkning: str
    kalla_fil: Path


def _las_record(fil: Path) -> LovBeslut:
    data = json.loads(fil.read_text(encoding="utf-8"))
    if data.get("syntetisk") is not True:
        raise ValueError(
            f"{fil.name}: posten saknar 'syntetisk: true' — arkivet läser enbart "
            "uttryckligen syntetiska testärenden i prototypfasen."
        )
    handling = data.get("handling")
    return LovBeslut(
        dnr=data["dnr"],
        fastighet=data["fastighet"],
        beslutsdatum=data["beslutsdatum"],
        laga_kraft=data.get("laga_kraft"),
        atgard=data["atgard"],
        byggnadsarea_m2=data.get("byggnadsarea_m2"),
        hojd_m=data.get("hojd_m"),
        godkant_lage=Polygon(data["godkant_lage"]["koordinater"]),
        villkor=list(data.get("villkor", [])),
        handling=(fil.parent / handling) if handling else None,
        anmarkning=data.get("anmarkning", ""),
        kalla_fil=fil,
    )


def hitta_lov(
    katalog: Path,
    punkt: tuple[float, float] | None = None,
    fastighet: str | None = None,
    max_avstand_m: float = 100.0,
) -> LovBeslut | None:
    """Find the (nearest) synthetic lov matching a point or a fastighet.

    Returns None when nothing matches — the caller renders that as the honest
    "inget ärende i (test)arkivet", never an invented permit.
    """
    kandidater: list[tuple[float, LovBeslut]] = []
    for fil in sorted(katalog.glob("*.json")):
        lov = _las_record(fil)
        if fastighet is not None and lov.fastighet == fastighet:
            kandidater.append((0.0, lov))
        elif punkt is not None:
            avstand = lov.godkant_lage.distance(Point(punkt))
            if avstand <= max_avstand_m:
                kandidater.append((avstand, lov))
    if not kandidater:
        return None
    return min(kandidater, key=lambda par: par[0])[1]
```

Note: the `handling` path in a record is stored RELATIVE to the record's directory (see `_las_record`).

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_lovarkiv.py -q` → all pass. Then `python -m pytest -q` (whole suite) and `python -m ruff check src tests`.

- [ ] **Step 5: Commit**

```bash
git add src/geo_tillsyn/lovarkiv.py tests/test_lovarkiv.py
git commit -m "feat(fall3): lovarkiv - mock-ByggR store som enbart laser syntetiska testarenden"
```

---

### Task 2: Synthetic scanned handling (situationsplan renderer)

**Files:**
- Create: `src/geo_tillsyn/handling.py`
- Test: `tests/test_handling.py`

**Interfaces:**
- Consumes: nothing new (Pillow only — `Image.save(..., format="PDF")` produces a raster-only PDF, no extra dependency).
- Produces: `rita_situationsplan(falt: dict[str, str], kontur: list[tuple[float, float]], vattenmarke: str) -> PIL.Image.Image` and `till_pdf_bytes(bild: Image) -> bytes`. `VATTENMARKE = "SYNTETISK TESTHANDLING — GEO-TILLSYN PROTOTYP"` exported constant. Field LABELS printed on the drawing are the contract the OCR regexes in Task 3 match: `DNR:`, `BESLUTSDATUM:`, `BYGGNADSAREA:` (value like `80,0 m2`), `AVSTAND TILL GRANS:` (value like `4,5 m`) — uppercase, no diacritics, one per line.

- [ ] **Step 1: Write the failing tests**

```python
"""Unit tests for the synthetic situationsplan renderer (Fall 3).

SPDX-License-Identifier: AGPL-3.0-or-later
"""

import pytest

from geo_tillsyn.handling import VATTENMARKE, rita_situationsplan, till_pdf_bytes

FALT = {
    "DNR": "SBN 2009-0412",
    "BESLUTSDATUM": "2009-06-19",
    "BYGGNADSAREA": "80,0 m2",
    "AVSTAND TILL GRANS": "4,5 m",
}
KONTUR = [(0.0, 0.0), (10.0, 0.0), (10.0, 8.0), (0.0, 8.0)]


def test_ritar_bild_med_deterministiskt_innehall():
    a = rita_situationsplan(FALT, KONTUR, VATTENMARKE)
    b = rita_situationsplan(FALT, KONTUR, VATTENMARKE)

    assert a.size == b.size
    assert a.tobytes() == b.tobytes()


def test_vagrar_rendera_utan_vattenmarke():
    with pytest.raises(ValueError, match="vattenmärke"):
        rita_situationsplan(FALT, KONTUR, "")


def test_vattenmarket_paverkar_bilden():
    med = rita_situationsplan(FALT, KONTUR, VATTENMARKE)
    annan = rita_situationsplan(FALT, KONTUR, "ANNAN MARKERING X")

    assert med.tobytes() != annan.tobytes()


def test_pdf_ar_raster_pdf():
    bild = rita_situationsplan(FALT, KONTUR, VATTENMARKE)
    pdf = till_pdf_bytes(bild)

    assert pdf.startswith(b"%PDF")
    # Raster-only: the page is one embedded image, no text operators.
    assert b"/Image" in pdf and b"Tj" not in pdf
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_handling.py -q`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement `src/geo_tillsyn/handling.py`**

```python
"""Syntetisk situationsplan: ritar en 'skannad' handling som raster-PDF (Fall 3).

Prototypen har inga riktiga bygglovshandlingar — vi ritar en fiktiv
situationsplan (Pillow) och packar den som raster-PDF, samma natur som
kommunens skannade 2281K-handlingar. Varje sida bär ett obligatoriskt
vattenmärke; en handling som liknar en myndighetshandling får aldrig
existera omärkt.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

from __future__ import annotations

import io

from PIL import Image, ImageDraw, ImageFont

VATTENMARKE = "SYNTETISK TESTHANDLING — GEO-TILLSYN PROTOTYP"

_BREDD, _HOJD = 1240, 1754  # ~A4 at 150 dpi
_MARGINAL = 60


def _font(storlek: int) -> ImageFont.ImageFont:
    # Deterministic across machines: Pillow's bundled bitmap font as fallback.
    try:
        return ImageFont.truetype("arial.ttf", storlek)
    except OSError:
        return ImageFont.load_default(storlek)


def rita_situationsplan(
    falt: dict[str, str],
    kontur: list[tuple[float, float]],
    vattenmarke: str,
) -> Image.Image:
    """Draw the synthetic situationsplan: title block, approved outline, stamp.

    `falt` keys are printed as `NYCKEL: värde`, one per line — these labels are
    the OCR contract for lovtolk (Task 3). `kontur` is the approved footprint
    in local metres; it is scaled to fit the drawing area.
    """
    if not vattenmarke.strip():
        raise ValueError("vattenmärke krävs — en omärkt syntetisk handling får inte renderas")

    bild = Image.new("L", (_BREDD, _HOJD), color=245)
    rita = ImageDraw.Draw(bild)

    # Title block
    rita.rectangle([_MARGINAL, _MARGINAL, _BREDD - _MARGINAL, 320], outline=0, width=3)
    rita.text((_MARGINAL + 20, _MARGINAL + 15), "SUNDSVALLS KOMMUN", font=_font(40), fill=0)
    rita.text(
        (_MARGINAL + 20, _MARGINAL + 65),
        "STADSBYGGNADSKONTORET — SITUATIONSPLAN",
        font=_font(28),
        fill=0,
    )
    y = _MARGINAL + 115
    for nyckel, varde in falt.items():
        rita.text((_MARGINAL + 20, y), f"{nyckel}: {varde}", font=_font(26), fill=0)
        y += 36

    # Approved outline, scaled into the drawing area
    xs = [p[0] for p in kontur]
    ys = [p[1] for p in kontur]
    bredd_m = max(xs) - min(xs) or 1.0
    hojd_m = max(ys) - min(ys) or 1.0
    rityta = (200, 420, _BREDD - 200, _HOJD - 400)
    skala = min((rityta[2] - rityta[0]) / bredd_m, (rityta[3] - rityta[1]) / hojd_m) * 0.6
    cx = (rityta[0] + rityta[2]) / 2 - (min(xs) + bredd_m / 2) * skala
    cy = (rityta[1] + rityta[3]) / 2 + (min(ys) + hojd_m / 2) * skala
    punkter = [(cx + x * skala, cy - y_ * skala) for x, y_ in kontur]
    rita.polygon(punkter, outline=0, width=4)
    rita.text((rityta[0], rityta[3] + 20), "GODKANT LAGE (SKALA EJ BINDANDE)", font=_font(24), fill=0)

    # Stamp
    rita.rectangle([_BREDD - 460, _HOJD - 330, _BREDD - _MARGINAL, _HOJD - 210], outline=0, width=5)
    rita.text((_BREDD - 430, _HOJD - 300), "BEVILJAS", font=_font(48), fill=0)

    # Mandatory watermark, twice for visibility
    for wy in (370, _HOJD - 120):
        rita.text((_MARGINAL, wy), vattenmarke, font=_font(30), fill=100)

    return bild


def till_pdf_bytes(bild: Image.Image) -> bytes:
    """Package the drawing as a raster-only, single-page PDF (no text layer)."""
    buf = io.BytesIO()
    bild.convert("L").save(buf, format="PDF", resolution=150.0)
    return buf.getvalue()
```

If the `Tj`-absence assertion fails because Pillow's PDF writer emits no text operators anyway (expected), keep the assertion — it guards the raster-only property against future refactors.

- [ ] **Step 4: Run tests, whole suite, ruff**

`python -m pytest tests/test_handling.py -q` → pass; `python -m pytest -q`; `python -m ruff check src tests`.

- [ ] **Step 5: Commit**

```bash
git add src/geo_tillsyn/handling.py tests/test_handling.py
git commit -m "feat(fall3): syntetisk situationsplan som raster-PDF med obligatoriskt vattenmarke"
```

---

### Task 3: Lov-tolk (OCR + register cross-check)

**Files:**
- Create: `src/geo_tillsyn/lovtolk.py`
- Modify: `pyproject.toml:9-15` (add `"pypdfium2>=4.30"` and `"pytesseract>=0.3.10"` to `dependencies`)
- Test: `tests/test_lovtolk.py`

**Interfaces:**
- Consumes: `handling.till_pdf_bytes`/`rita_situationsplan` (test fixtures build real PDFs), `lovarkiv.LovBeslut`.
- Produces:
  - `TolkatFalt` (frozen: `varde: str, konfidens: float`)
  - `TolkatDokument` (frozen: `tillganglig: bool, falt: dict[str, TolkatFalt], ratext: str, anmarkningar: list[str]`)
  - `tolka_handling(pdf_bytes: bytes, ocr: Callable[[Image], tuple[str, float]] | None = None) -> TolkatDokument` — `ocr` returns `(text, mean_word_confidence 0..1)`; default uses pytesseract, any exception ⇒ `tillganglig=False`.
  - `korsjamfor(tolkat: TolkatDokument, lov: LovBeslut) -> dict[str, str]` — per field `"överens" | "avviker" | "saknas"`.
- Field keys produced/compared: `"dnr"`, `"beslutsdatum"`, `"byggnadsarea_m2"`, `"avstand_grans_m"` (the last has no register counterpart yet ⇒ excluded from korsjamfor).

- [ ] **Step 1: Install the runtime OCR prerequisites (machine setup, not code)**

```powershell
pip install pypdfium2 pytesseract
winget install --id UB-Mannheim.TesseractOCR -e --accept-package-agreements --accept-source-agreements
```

If winget lacks the package, download the UB Mannheim installer manually — but do NOT block on it: the suite never needs the binary. Verify afterwards with `tesseract --version` (missing is acceptable; the pipeline degrades gracefully).

- [ ] **Step 2: Write the failing tests**

```python
"""Unit tests for the OCR lov-tolk + register cross-check (Fall 3).

Hermetic: OCR is injected; the PDF is built with handling.py so the
pypdfium2 rasterization path runs for real (pure-python wheel, no binary).

SPDX-License-Identifier: AGPL-3.0-or-later
"""

import json
from pathlib import Path

import pytest

from geo_tillsyn.handling import VATTENMARKE, rita_situationsplan, till_pdf_bytes
from geo_tillsyn.lovarkiv import hitta_lov
from geo_tillsyn.lovtolk import korsjamfor, tolka_handling

OCR_TEXT = """SUNDSVALLS KOMMUN
STADSBYGGNADSKONTORET — SITUATIONSPLAN
DNR: SBN 2009-0412
BESLUTSDATUM: 2009-06-19
BYGGNADSAREA: 80,0 m2
AVSTAND TILL GRANS: 4,5 m
BEVILJAS
"""


def _pdf() -> bytes:
    falt = {
        "DNR": "SBN 2009-0412",
        "BESLUTSDATUM": "2009-06-19",
        "BYGGNADSAREA": "80,0 m2",
        "AVSTAND TILL GRANS": "4,5 m",
    }
    kontur = [(0.0, 0.0), (10.0, 0.0), (10.0, 8.0), (0.0, 8.0)]
    return till_pdf_bytes(rita_situationsplan(falt, kontur, VATTENMARKE))


def _fake_ocr(_bild):
    return OCR_TEXT, 0.93


def test_extraherar_falt_ur_ocr_text():
    tolkat = tolka_handling(_pdf(), ocr=_fake_ocr)

    assert tolkat.tillganglig
    assert tolkat.falt["dnr"].varde == "SBN 2009-0412"
    assert tolkat.falt["beslutsdatum"].varde == "2009-06-19"
    assert tolkat.falt["byggnadsarea_m2"].varde == "80.0"
    assert tolkat.falt["avstand_grans_m"].varde == "4.5"
    assert tolkat.falt["dnr"].konfidens == pytest.approx(0.93)


def test_saknad_ocr_motor_ger_otillganglig_med_anmarkning():
    def trasig_ocr(_bild):
        raise RuntimeError("tesseract is not installed")

    tolkat = tolka_handling(_pdf(), ocr=trasig_ocr)

    assert not tolkat.tillganglig
    assert tolkat.falt == {}
    assert any("OCR ej tillgänglig" in a for a in tolkat.anmarkningar)


def test_lag_konfidens_flaggas():
    def osaker_ocr(_bild):
        return OCR_TEXT, 0.31

    tolkat = tolka_handling(_pdf(), ocr=osaker_ocr)

    assert tolkat.tillganglig
    assert any("konfidens" in a.lower() for a in tolkat.anmarkningar)


def _lov(tmp_path: Path, **extra):
    record = {
        "syntetisk": True,
        "anmarkning": "Syntetiskt testärende.",
        "dnr": "SBN 2009-0412",
        "fastighet": "ALNÖ-USLAND 1:45",
        "beslutsdatum": "2009-06-19",
        "atgard": "Nybyggnad av enbostadshus",
        "byggnadsarea_m2": 80.0,
        "godkant_lage": {
            "crs": "EPSG:3014",
            "koordinater": [[0.0, 0.0], [10.0, 0.0], [10.0, 8.0], [0.0, 8.0]],
        },
        "villkor": [],
        "handling": None,
    }
    record.update(extra)
    (tmp_path / "a.json").write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    return hitta_lov(tmp_path, fastighet="ALNÖ-USLAND 1:45")


def test_korsjamforelse_overens(tmp_path):
    tolkat = tolka_handling(_pdf(), ocr=_fake_ocr)

    resultat = korsjamfor(tolkat, _lov(tmp_path))

    assert resultat == {"dnr": "överens", "beslutsdatum": "överens", "byggnadsarea_m2": "överens"}


def test_korsjamforelse_avvikande_register(tmp_path):
    tolkat = tolka_handling(_pdf(), ocr=_fake_ocr)

    resultat = korsjamfor(tolkat, _lov(tmp_path, byggnadsarea_m2=95.0))

    assert resultat["byggnadsarea_m2"] == "avviker"


def test_korsjamforelse_saknat_falt(tmp_path):
    def ocr_utan_area(_bild):
        text = OCR_TEXT.replace("BYGGNADSAREA: 80,0 m2\n", "")
        return text, 0.9

    tolkat = tolka_handling(_pdf(), ocr=ocr_utan_area)

    resultat = korsjamfor(tolkat, _lov(tmp_path))

    assert resultat["byggnadsarea_m2"] == "saknas"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_lovtolk.py -q` → `ModuleNotFoundError: geo_tillsyn.lovtolk`

- [ ] **Step 4: Implement `src/geo_tillsyn/lovtolk.py` + pyproject deps**

```python
"""Lov-tolk: OCR av skannad handling + korskontroll mot registret (Fall 3).

Handlingen är en raster-PDF (som kommunens 2281K-skanningar). pypdfium2
rastrerar, tesseract läser; varje extraherat fält bär sin konfidens och
korskontrolleras mot mock-ByggR-posten — två oberoende källor i öppen
jämförelse (bevisstyrka). Saknas OCR-motorn fortsätter kedjan register-only
med en deklarerad osäkerhet; vi maskerar aldrig ett verktygsbortfall.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable

import pypdfium2 as pdfium
from PIL import Image

from geo_tillsyn.lovarkiv import LovBeslut

_KONFIDENS_GRANS = 0.5

# Label contract with handling.rita_situationsplan — uppercase, no diacritics.
_FALT_MONSTER: dict[str, re.Pattern] = {
    "dnr": re.compile(r"DNR:\s*(SBN\s*\d{4}-\d{4})"),
    "beslutsdatum": re.compile(r"BESLUTSDATUM:\s*(\d{4}-\d{2}-\d{2})"),
    "byggnadsarea_m2": re.compile(r"BYGGNADSAREA:\s*([\d]+[,.]?\d*)\s*m2"),
    "avstand_grans_m": re.compile(r"AVSTAND TILL GRANS:\s*([\d]+[,.]?\d*)\s*m"),
}


@dataclass(frozen=True)
class TolkatFalt:
    varde: str
    konfidens: float


@dataclass(frozen=True)
class TolkatDokument:
    tillganglig: bool
    falt: dict[str, TolkatFalt] = field(default_factory=dict)
    ratext: str = ""
    anmarkningar: list[str] = field(default_factory=list)


def _rasterisera(pdf_bytes: bytes) -> Image.Image:
    dokument = pdfium.PdfDocument(pdf_bytes)
    try:
        return dokument[0].render(scale=2.0).to_pil()
    finally:
        dokument.close()


def _tesseract_ocr(bild: Image.Image) -> tuple[str, float]:
    """Default OCR: tesseract via pytesseract, mean word confidence 0..1."""
    import pytesseract

    data = pytesseract.image_to_data(bild, output_type=pytesseract.Output.DICT)
    konfidenser = [int(k) for k in data["conf"] if str(k).lstrip("-").isdigit() and int(k) >= 0]
    text = pytesseract.image_to_string(bild)
    medel = (sum(konfidenser) / len(konfidenser) / 100.0) if konfidenser else 0.0
    return text, medel


def tolka_handling(
    pdf_bytes: bytes,
    ocr: Callable[[Image.Image], tuple[str, float]] | None = None,
) -> TolkatDokument:
    """OCR the scanned handling and extract the known fields with confidence."""
    bild = _rasterisera(pdf_bytes)
    try:
        text, konfidens = (ocr or _tesseract_ocr)(bild)
    except Exception as fel:
        return TolkatDokument(
            tillganglig=False,
            anmarkningar=[
                "OCR ej tillgänglig — handlingen har inte kunnat verifieras maskinellt "
                f"({type(fel).__name__})."
            ],
        )

    falt: dict[str, TolkatFalt] = {}
    for namn, monster in _FALT_MONSTER.items():
        traff = monster.search(text)
        if traff:
            varde = traff.group(1).replace(",", ".")
            falt[namn] = TolkatFalt(varde=varde, konfidens=konfidens)

    anmarkningar: list[str] = []
    if konfidens < _KONFIDENS_GRANS:
        anmarkningar.append(
            f"OCR-konfidensen är låg ({konfidens:.2f}) — extraherade fält bör "
            "kontrolleras mot handlingen manuellt."
        )
    return TolkatDokument(tillganglig=True, falt=falt, ratext=text, anmarkningar=anmarkningar)


def _normalisera(namn: str, varde) -> str:
    if namn == "byggnadsarea_m2":
        return f"{float(varde):.1f}"
    return re.sub(r"\s+", " ", str(varde)).strip()


def korsjamfor(tolkat: TolkatDokument, lov: LovBeslut) -> dict[str, str]:
    """Per-field comparison OCR vs register: överens / avviker / saknas."""
    register = {
        "dnr": lov.dnr,
        "beslutsdatum": lov.beslutsdatum,
        "byggnadsarea_m2": lov.byggnadsarea_m2,
    }
    resultat: dict[str, str] = {}
    for namn, registervarde in register.items():
        if registervarde is None:
            continue
        ocr_falt = tolkat.falt.get(namn)
        if ocr_falt is None:
            resultat[namn] = "saknas"
        elif _normalisera(namn, ocr_falt.varde) == _normalisera(namn, registervarde):
            resultat[namn] = "överens"
        else:
            resultat[namn] = "avviker"
    return resultat
```

In `pyproject.toml`, `dependencies` becomes:

```toml
dependencies = [
    "mcp>=1.0",
    "mcp-ogc",
    "numpy>=2.0",
    "pillow>=10.0",
    "pypdfium2>=4.30",
    "pytesseract>=0.3.10",
    "shapely>=2.0",
]
```

Then `pip install -e .[dev]` to pick up the new deps.

- [ ] **Step 5: Run tests, whole suite, ruff; commit**

```bash
python -m pytest tests/test_lovtolk.py -q && python -m pytest -q && python -m ruff check src tests
git add src/geo_tillsyn/lovtolk.py tests/test_lovtolk.py pyproject.toml
git commit -m "feat(fall3): lov-tolk - OCR med konfidens + korskontroll mot registret"
```

---

### Task 4: Delta-motor (geometric comparison)

**Files:**
- Create: `src/geo_tillsyn/delta.py`
- Test: `tests/test_delta.py`

**Interfaces:**
- Consumes: shapely only.
- Produces: `DeltaResultat` (frozen: `godkand_area_m2, verklig_area_m2, area_diff_m2, area_diff_procent: float; centroid_forskjutning_m: float; utanfor_godkant_m2: float; avstand_grans_godkant_m: float | None; avstand_grans_verklig_m: float | None; anmarkningar: list[str]`) and `jamfor_lage(godkant: Polygon, verkligt: Polygon, granser: list[BaseGeometry] | None = None) -> DeltaResultat`.

- [ ] **Step 1: Write the failing tests**

```python
"""Unit tests for the geometric delta engine (Fall 3).

Known-answer geometry: approved 10x8 m at origin; actual 10.9x8.7 m shifted
2 m east — area +18.5 %, centroid shift computable by hand.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

import pytest
from shapely.geometry import LineString, box

from geo_tillsyn.delta import jamfor_lage

GODKANT = box(0.0, 0.0, 10.0, 8.0)          # 80 m²
VERKLIGT = box(2.0, 0.0, 12.9, 8.7)          # 94.83 m², shifted east
GRANS = LineString([(16.0, -10.0), (16.0, 20.0)])  # boundary east of both


def test_areaskillnad_i_m2_och_procent():
    d = jamfor_lage(GODKANT, VERKLIGT)

    assert d.godkand_area_m2 == pytest.approx(80.0)
    assert d.verklig_area_m2 == pytest.approx(94.83)
    assert d.area_diff_m2 == pytest.approx(14.83)
    assert d.area_diff_procent == pytest.approx(18.5, abs=0.1)


def test_centroidforskjutning():
    d = jamfor_lage(GODKANT, VERKLIGT)

    # centroids: (5, 4) vs (7.45, 4.35) -> sqrt(2.45² + 0.35²)
    assert d.centroid_forskjutning_m == pytest.approx(2.4749, abs=0.001)


def test_yta_utanfor_godkant_lage():
    d = jamfor_lage(GODKANT, VERKLIGT)

    assert d.utanfor_godkant_m2 == pytest.approx(VERKLIGT.difference(GODKANT).area)
    assert d.utanfor_godkant_m2 > 0


def test_avstand_till_grans_godkant_vs_verkligt():
    d = jamfor_lage(GODKANT, VERKLIGT, granser=[GRANS])

    assert d.avstand_grans_godkant_m == pytest.approx(6.0)   # 16 - 10
    assert d.avstand_grans_verklig_m == pytest.approx(3.1)   # 16 - 12.9


def test_utan_granser_ar_avstanden_none_med_anmarkning():
    d = jamfor_lage(GODKANT, VERKLIGT)

    assert d.avstand_grans_godkant_m is None
    assert d.avstand_grans_verklig_m is None
    assert any("fastighetsgräns" in a for a in d.anmarkningar)


def test_identiska_lagen_ger_nollavvikelse():
    d = jamfor_lage(GODKANT, GODKANT, granser=[GRANS])

    assert d.area_diff_m2 == pytest.approx(0.0)
    assert d.centroid_forskjutning_m == pytest.approx(0.0)
    assert d.utanfor_godkant_m2 == pytest.approx(0.0)
```

- [ ] **Step 2: Run tests to verify they fail**

`python -m pytest tests/test_delta.py -q` → module not found.

- [ ] **Step 3: Implement `src/geo_tillsyn/delta.py`**

```python
"""Delta-motor: kvantifierad avvikelse godkänt läge vs verkligt läge (Fall 3).

Ren geometri (shapely, EPSG:3014): areaskillnad, förskjutning, yta utanför
godkänt läge, avstånd till fastighetsgräns. Motorn kvantifierar — den
kvalificerar aldrig (väsentlig/ringa är handläggarens fråga).

SPDX-License-Identifier: AGPL-3.0-or-later
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from shapely.geometry import Polygon
from shapely.geometry.base import BaseGeometry


@dataclass(frozen=True)
class DeltaResultat:
    godkand_area_m2: float
    verklig_area_m2: float
    area_diff_m2: float
    area_diff_procent: float
    centroid_forskjutning_m: float
    utanfor_godkant_m2: float
    avstand_grans_godkant_m: float | None
    avstand_grans_verklig_m: float | None
    anmarkningar: list[str] = field(default_factory=list)


def jamfor_lage(
    godkant: Polygon,
    verkligt: Polygon,
    granser: list[BaseGeometry] | None = None,
) -> DeltaResultat:
    """Quantify how the actual footprint deviates from the approved one."""
    anmarkningar: list[str] = []

    godkand_area = godkant.area
    verklig_area = verkligt.area
    diff = verklig_area - godkand_area
    procent = (diff / godkand_area * 100.0) if godkand_area else 0.0

    gc, vc = godkant.centroid, verkligt.centroid
    forskjutning = math.hypot(vc.x - gc.x, vc.y - gc.y)

    utanfor = verkligt.difference(godkant).area

    if granser:
        avstand_godkant = min(godkant.distance(g) for g in granser)
        avstand_verklig = min(verkligt.distance(g) for g in granser)
    else:
        avstand_godkant = avstand_verklig = None
        anmarkningar.append(
            "Ingen fastighetsgräns tillgänglig — avstånd till gräns har inte "
            "kunnat jämföras."
        )

    return DeltaResultat(
        godkand_area_m2=godkand_area,
        verklig_area_m2=verklig_area,
        area_diff_m2=diff,
        area_diff_procent=procent,
        centroid_forskjutning_m=forskjutning,
        utanfor_godkant_m2=utanfor,
        avstand_grans_godkant_m=avstand_godkant,
        avstand_grans_verklig_m=avstand_verklig,
        anmarkningar=anmarkningar,
    )
```

- [ ] **Step 4: Run tests, whole suite, ruff; commit**

```bash
python -m pytest tests/test_delta.py -q && python -m pytest -q && python -m ruff check src tests
git add src/geo_tillsyn/delta.py tests/test_delta.py
git commit -m "feat(fall3): delta-motor - kvantifierad avvikelse godkant vs verkligt lage"
```

---

### Task 5: `juridik.fall3_lage` (+ extract shared PBL-clock helper)

**Files:**
- Modify: `src/geo_tillsyn/juridik.py` (extract `_pbl_klockor` out of `fall1_lage` lines 243–268; append `Fall3Lage` + `fall3_lage`)
- Test: `tests/test_fall3_juridik.py` (new); `tests/test_fall1_juridik.py` must stay green unchanged.

**Interfaces:**
- Consumes: `_regelverk.regelverk_vid(datum, kontext, bedomningsdatum, arende_startdatum)` — with `arende_startdatum` before a transition it returns `overgangsbestammelser.tillampad_pga_arendestart == True` and `pbl_version` routed to the OLDER law (dict with keys `namn`, `sfs`, `tillsyn_lagrum`); `delta.DeltaResultat`; existing `_plus_ar`.
- Produces:
  - `_pbl_klockor(sista_ar_utan: int | None, forsta_ar_med: int, bedomningsdatum: date) -> tuple[bool | None, bool | None, list[str]]` — EXACTLY the current fall1 clock semantics (rättelse 10 yr, sanktionsavgift 5 yr, conservative at interval bounds), shared by `fall1_lage` and `fall3_lage`.
  - `Fall3Lage` (frozen: `pbl_vid_beslut: str | None; overgangsregel_tillampad: bool; tillsyn_lagrum: str | None; sista_ar_utan: int | None; forsta_ar_med: int | None; rattelse_preskriberad: bool | None; sanktionsavgift_mojlig: bool | None; matningskritiska: list[str]; atgarder: list[str]`)
  - `fall3_lage(beslutsdatum: date, sista_ar_utan: int | None, forsta_ar_med: int | None, bedomningsdatum: date, delta: DeltaResultat | None = None) -> Fall3Lage`
- Measurement bands: `_AREA_BAND_M2 = 2.0`, `_AVSTAND_BAND_M = 0.5` — a deviation whose magnitude is ≤ its band goes into `matningskritiska` ("inom mätosäkerheten — kan inte beläggas utan inmätning").

- [ ] **Step 1: Refactor — extract `_pbl_klockor`, keep fall1 green**

In `juridik.py`, add above `fall1_lage`:

```python
def _pbl_klockor(
    sista_ar_utan: int | None,
    forsta_ar_med: int,
    bedomningsdatum: date,
) -> tuple[bool | None, bool | None, list[str]]:
    """Both PBL clocks over the completion interval — conservative at the bounds.

    Returns (rattelse_preskriberad, sanktionsavgift_mojlig, atgarder); None
    where the interval straddles a clock's expiry.
    """
    atgarder: list[str] = []
    senaste = date(forsta_ar_med, 12, 31)
    tidigaste = date(sista_ar_utan + 1, 1, 1) if sista_ar_utan is not None else None

    if _plus_ar(senaste, 10) < bedomningsdatum:
        rattelse_preskriberad: bool | None = True
    elif tidigaste is not None and _plus_ar(tidigaste, 10) >= bedomningsdatum:
        rattelse_preskriberad = False
    else:
        rattelse_preskriberad = None
        atgarder.append(
            "PBL 11 kap. 20 §-klockan (10 år) löper ut någonstans inom "
            "dateringsintervallet — konstruktionsåret måste pinpointas för att avgöra "
            "om rättelse är preskriberad."
        )

    if tidigaste is not None and _plus_ar(tidigaste, 5) >= bedomningsdatum:
        sanktionsavgift_mojlig: bool | None = True
    elif _plus_ar(senaste, 5) < bedomningsdatum:
        sanktionsavgift_mojlig = False
    else:
        sanktionsavgift_mojlig = None
        atgarder.append(
            "PBL 11 kap. 58 §-klockan (5 år) löper ut någonstans inom "
            "dateringsintervallet — konstruktionsåret måste pinpointas för att avgöra "
            "om sanktionsavgift fortfarande är möjlig."
        )

    return rattelse_preskriberad, sanktionsavgift_mojlig, atgarder
```

Replace `fall1_lage` lines 243–268 with:

```python
    rattelse_preskriberad, sanktionsavgift_mojlig, klock_atgarder = _pbl_klockor(
        sista_ar_utan, forsta_ar_med, bedomningsdatum
    )
    atgarder.extend(klock_atgarder)
```

Run: `python -m pytest tests/test_fall1_juridik.py tests/test_juridik.py -q` → all green (behavior-preserving refactor). Commit separately:

```bash
git add src/geo_tillsyn/juridik.py
git commit -m "refactor(juridik): extrahera _pbl_klockor ur fall1_lage (delas med fall3)"
```

- [ ] **Step 2: Write the failing fall3 tests**

```python
"""Unit tests for fall3_lage: which law governs the lov + clocks + bands.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

from datetime import date

from geo_tillsyn.delta import DeltaResultat
from geo_tillsyn.juridik import fall3_lage

BEDOMNING = date(2026, 7, 23)


def _delta(area_diff=14.8, avstand_godkant=6.0, avstand_verklig=3.1):
    return DeltaResultat(
        godkand_area_m2=80.0,
        verklig_area_m2=80.0 + area_diff,
        area_diff_m2=area_diff,
        area_diff_procent=area_diff / 80.0 * 100.0,
        centroid_forskjutning_m=2.4,
        utanfor_godkant_m2=max(area_diff, 0.0),
        avstand_grans_godkant_m=avstand_godkant,
        avstand_grans_verklig_m=avstand_verklig,
    )


def test_lov_fran_2009_styrs_av_apbl_via_overgangsregeln():
    lage = fall3_lage(
        beslutsdatum=date(2009, 6, 19),
        sista_ar_utan=2007,
        forsta_ar_med=2010,
        bedomningsdatum=BEDOMNING,
        delta=_delta(),
    )

    assert lage.overgangsregel_tillampad is True
    assert "ÄPBL" in lage.pbl_vid_beslut
    assert lage.tillsyn_lagrum == "10 kap. ÄPBL"


def test_lov_fran_2015_styrs_av_pbl_2010():
    lage = fall3_lage(
        beslutsdatum=date(2015, 3, 2),
        sista_ar_utan=2013,
        forsta_ar_med=2016,
        bedomningsdatum=BEDOMNING,
        delta=_delta(),
    )

    assert lage.overgangsregel_tillampad is False
    assert "2010:900" in lage.pbl_vid_beslut


def test_klockorna_utvarderas_over_intervallet():
    lage = fall3_lage(
        beslutsdatum=date(2009, 6, 19),
        sista_ar_utan=2009,
        forsta_ar_med=2013,
        bedomningsdatum=BEDOMNING,
        delta=_delta(),
    )

    # senaste = 2013-12-31: +10 yr = 2023 < 2026 -> preskriberad; +5 yr < 2026 -> avgift borta
    assert lage.rattelse_preskriberad is True
    assert lage.sanktionsavgift_mojlig is False


def test_okand_datering_ger_none_och_atgard():
    lage = fall3_lage(
        beslutsdatum=date(2009, 6, 19),
        sista_ar_utan=None,
        forsta_ar_med=None,
        bedomningsdatum=BEDOMNING,
        delta=_delta(),
    )

    assert lage.rattelse_preskriberad is None
    assert lage.sanktionsavgift_mojlig is None
    assert any("datera" in a.lower() for a in lage.atgarder)


def test_liten_areaavvikelse_ar_matningskritisk():
    lage = fall3_lage(
        beslutsdatum=date(2009, 6, 19),
        sista_ar_utan=2007,
        forsta_ar_med=2010,
        bedomningsdatum=BEDOMNING,
        delta=_delta(area_diff=1.5),
    )

    assert any("area" in m.lower() for m in lage.matningskritiska)


def test_litet_avstandsdelta_ar_matningskritiskt():
    lage = fall3_lage(
        beslutsdatum=date(2009, 6, 19),
        sista_ar_utan=2007,
        forsta_ar_med=2010,
        bedomningsdatum=BEDOMNING,
        delta=_delta(avstand_godkant=4.5, avstand_verklig=4.2),
    )

    assert any("avstånd" in m.lower() or "gräns" in m.lower() for m in lage.matningskritiska)


def test_tydliga_avvikelser_ar_inte_matningskritiska():
    lage = fall3_lage(
        beslutsdatum=date(2009, 6, 19),
        sista_ar_utan=2007,
        forsta_ar_med=2010,
        bedomningsdatum=BEDOMNING,
        delta=_delta(),
    )

    assert lage.matningskritiska == []
```

- [ ] **Step 3: Run to verify failure, then implement**

`python -m pytest tests/test_fall3_juridik.py -q` fails on import. Append to `juridik.py`:

```python
_AREA_BAND_M2 = 2.0
_AVSTAND_BAND_M = 0.5


@dataclass(frozen=True)
class Fall3Lage:
    """The time-aware legal position of a suspected lovavvikelse (Fall 3)."""

    pbl_vid_beslut: str | None
    overgangsregel_tillampad: bool
    tillsyn_lagrum: str | None
    sista_ar_utan: int | None
    forsta_ar_med: int | None
    rattelse_preskriberad: bool | None
    sanktionsavgift_mojlig: bool | None
    matningskritiska: list[str] = field(default_factory=list)
    atgarder: list[str] = field(default_factory=list)


def fall3_lage(
    beslutsdatum: date,
    sista_ar_utan: int | None,
    forsta_ar_med: int | None,
    bedomningsdatum: date,
    delta=None,
) -> Fall3Lage:
    """Evaluate a lovavvikelse suspicion: which law governs the lov, both PBL
    clocks over the completion interval, and which deviations are inside the
    measurement band (and thus cannot be asserted without inmätning).

    PBL 2010:900 övergångsbest. p. 2: an ärende started before 2011-05-02 is
    governed by ÄPBL until finally decided — `arende_startdatum=beslutsdatum`
    routes `regelverk_vid` accordingly.
    """
    atgarder: list[str] = []

    resultat = _regelverk.regelverk_vid(
        bedomningsdatum,
        _regelverk.Kontext(),
        bedomningsdatum=bedomningsdatum,
        arende_startdatum=beslutsdatum,
    )
    version = resultat["pbl_version"]
    overgang = resultat["overgangsbestammelser"]["tillampad_pga_arendestart"]
    pbl_vid_beslut = f"{version['namn']} (SFS {version['sfs']})" if version else None
    tillsyn_lagrum = version["tillsyn_lagrum"] if version else None

    if forsta_ar_med is None:
        rattelse, sanktion = None, None
        atgarder.append(
            "Färdigställandet är inte daterat — datera via ortofoto-tidslinjen "
            "innan preskriptionsklockorna kan avgöras."
        )
    else:
        rattelse, sanktion, klock_atgarder = _pbl_klockor(
            sista_ar_utan, forsta_ar_med, bedomningsdatum
        )
        atgarder.extend(klock_atgarder)

    matningskritiska: list[str] = []
    if delta is not None:
        if abs(delta.area_diff_m2) <= _AREA_BAND_M2:
            matningskritiska.append(
                f"Areaavvikelsen ({delta.area_diff_m2:+.1f} m²) ligger inom "
                f"mätosäkerheten (±{_AREA_BAND_M2:.0f} m²) — kan inte beläggas utan inmätning."
            )
        if (
            delta.avstand_grans_godkant_m is not None
            and delta.avstand_grans_verklig_m is not None
            and abs(delta.avstand_grans_godkant_m - delta.avstand_grans_verklig_m)
            <= _AVSTAND_BAND_M
        ):
            matningskritiska.append(
                "Skillnaden i avstånd till fastighetsgräns ligger inom mätosäkerheten "
                f"(±{_AVSTAND_BAND_M:.1f} m) — kan inte beläggas utan inmätning."
            )
    if matningskritiska:
        atgarder.append(
            "Bedömningen är mätningskritisk — avvikelser inom mätosäkerheten måste "
            "verifieras genom inmätning innan handläggaren lägger fast slutsatsen."
        )

    return Fall3Lage(
        pbl_vid_beslut=pbl_vid_beslut,
        overgangsregel_tillampad=overgang,
        tillsyn_lagrum=tillsyn_lagrum,
        sista_ar_utan=sista_ar_utan,
        forsta_ar_med=forsta_ar_med,
        rattelse_preskriberad=rattelse,
        sanktionsavgift_mojlig=sanktion,
        matningskritiska=matningskritiska,
        atgarder=atgarder,
    )
```

- [ ] **Step 4: Run tests, whole suite, ruff; commit**

```bash
python -m pytest tests/test_fall3_juridik.py -q && python -m pytest -q && python -m ruff check src tests
git add src/geo_tillsyn/juridik.py tests/test_fall3_juridik.py
git commit -m "feat(fall3): fall3_lage - APBL-routing via arendestart + klockor + matband"
```

---

### Task 6: Fall 3 dossier builder

**Files:**
- Create: `src/geo_tillsyn/fall3.py`
- Test: `tests/test_fall3_dossier.py`

**Interfaces:**
- Consumes: `Dossier/Fakta/Bedomning/Kalla` from `dossier.py`; `LovBeslut`; `TolkatDokument` + `korsjamfor` result dict; `DeltaResultat`; `DateringsResultat`; `Fall3Lage`.
- Produces: `bygg_fall3_dossier(rubrik: str, byggnad_id: str, lov: LovBeslut, korsjamforelse: dict[str, str] | None, tolkat_anmarkningar: list[str], delta: DeltaResultat, datering: DateringsResultat, lage: Fall3Lage, lov_kalla: Kalla, handling_kalla: Kalla | None, byggnad_kalla: Kalla, grans_kalla: Kalla | None, tidslinje_kalla: Kalla, regelverk_kalla: Kalla, extra_osakerheter: list[str] | None = None) -> Dossier`.

Facts assembled (each with its källa): F1 lov (dnr/beslutsdatum/åtgärd + `anmarkning` visible → the syntetiskt disclaimer is IN the fact text); F2 OCR cross-check (only if `korsjamforelse` is not None; summarises per field); F3 area delta; F4 placement/boundary delta (only when boundary distances exist); F5 completion dating (same wording pattern as fall1's `_dateringsfakta`); F6 governing law (`pbl_vid_beslut`, notes övergångsregeln when `overgangsregel_tillampad`). Bedömning: quantified deviation summary + clock states, `grund` = indices of all facts, osäkerheter = `datering.anmarkningar + lage.matningskritiska + lage.atgarder + delta.anmarkningar + tolkat_anmarkningar + extra_osakerheter`. **Never** "olovligt"/"överträdelse" — deviation is stated as measured difference; väsentlighet is explicitly left to handläggaren.

- [ ] **Step 1: Write the failing tests**

```python
"""Unit tests for the Fall 3 dossier builder.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

import json
from datetime import date
from pathlib import Path

from shapely.geometry import box

from geo_tillsyn.datering import DateringsResultat
from geo_tillsyn.delta import jamfor_lage
from geo_tillsyn.dossier import Kalla, render_markdown
from geo_tillsyn.fall3 import bygg_fall3_dossier
from geo_tillsyn.juridik import fall3_lage
from geo_tillsyn.lovarkiv import hitta_lov

KALLA = Kalla("test", "https://example.com", hamtad="2026-07-23T00:00:00Z")


def _lov(tmp_path: Path):
    record = {
        "syntetisk": True,
        "anmarkning": "Syntetiskt testärende — inga verkliga byggärenden.",
        "dnr": "SBN 2009-0412",
        "fastighet": "ALNÖ-USLAND 1:45",
        "beslutsdatum": "2009-06-19",
        "atgard": "Nybyggnad av enbostadshus",
        "byggnadsarea_m2": 80.0,
        "godkant_lage": {
            "crs": "EPSG:3014",
            "koordinater": [[0.0, 0.0], [10.0, 0.0], [10.0, 8.0], [0.0, 8.0]],
        },
        "villkor": [],
        "handling": None,
    }
    (tmp_path / "a.json").write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    return hitta_lov(tmp_path, fastighet="ALNÖ-USLAND 1:45")


def _dossier(tmp_path, korsjamforelse=None):
    lov = _lov(tmp_path)
    delta = jamfor_lage(box(0, 0, 10, 8), box(2, 0, 12.9, 8.7))
    datering = DateringsResultat(sista_ar_utan=2007, forsta_ar_med=2010)
    lage = fall3_lage(date(2009, 6, 19), 2007, 2010, date(2026, 7, 23), delta)
    return bygg_fall3_dossier(
        rubrik="Fall 3 — test",
        byggnad_id="byggnad.1",
        lov=lov,
        korsjamforelse=korsjamforelse,
        tolkat_anmarkningar=[],
        delta=delta,
        datering=datering,
        lage=lage,
        lov_kalla=KALLA,
        handling_kalla=KALLA if korsjamforelse else None,
        byggnad_kalla=KALLA,
        grans_kalla=None,
        tidslinje_kalla=KALLA,
        regelverk_kalla=KALLA,
    )


def test_lovfaktan_bar_syntetisk_markering(tmp_path):
    md = render_markdown(_dossier(tmp_path))

    assert "SBN 2009-0412" in md
    assert "Syntetiskt testärende" in md


def test_deltafakta_kvantifierar(tmp_path):
    md = render_markdown(_dossier(tmp_path))

    assert "+14,8" in md or "+14.8" in md
    assert "18" in md  # ~ +18.5 %


def test_korsjamforelse_redovisas_nar_den_finns(tmp_path):
    md = render_markdown(
        _dossier(tmp_path, korsjamforelse={"dnr": "överens", "byggnadsarea_m2": "avviker"})
    )

    assert "överens" in md and "avviker" in md


def test_apbl_som_styrande_lag_redovisas(tmp_path):
    md = render_markdown(_dossier(tmp_path))

    assert "ÄPBL" in md
    assert "övergångs" in md.lower()


def test_inga_skuldord_i_bedomningen(tmp_path):
    md = render_markdown(_dossier(tmp_path))
    bedomning = md.split("## 2. Bedömning")[1].split("## 3. Beslut")[0]

    for ord_ in ("olovligt", "överträdelse", "brott"):
        assert ord_ not in bedomning.lower()


def test_vasentlighet_lamnas_till_handlaggaren(tmp_path):
    md = render_markdown(_dossier(tmp_path))

    assert "väsentlig" in md.lower()
    assert "handläggaren" in md


def test_beslut_ar_tomt(tmp_path):
    md = render_markdown(_dossier(tmp_path))

    assert "avsiktligt tom" in md
```

- [ ] **Step 2: Run to verify failure, then implement `src/geo_tillsyn/fall3.py`**

Follow `fall1.py`'s structure exactly (module docstring explaining REALITY/RULE/DIFF/TIME for Fall 3 + SPDX). Key texts:

```python
"""Fall 3 — lovavvikelse: godkänt läge vs verkligt läge, sammansatt till dossier.

REALITY = byggnadens verkliga läge och area (WFS + ortofoto-datering).
RULE = det beviljade (syntetiska) lovet: godkänt läge, area, villkor — läst ur
mock-ByggR OCH ur den skannade handlingen (OCR), i öppen korsjämförelse.
DIFF = delta-motorns kvantifierade avvikelser. TIME = när avvikelsen
färdigställdes -> PBL-klockorna; vilken lag som styr lovet avgörs av
ärendets start (ÄPBL för lov före 2011-05-02). Bedömningen kvantifierar —
om avvikelsen är väsentlig, och beslutet, är handläggarens.

SPDX-License-Identifier: AGPL-3.0-or-later
"""
```

Fact builders (complete list — the implementer composes `bygg_fall3_dossier` in the same accumulating style as `bygg_fall1_dossier`, appending each non-None fact and collecting its index into `grund`):

```python
def _lovfakta(lov) -> str:
    text = (
        f"Bygglov {lov.dnr} ({lov.fastighet}) beviljades {lov.beslutsdatum}: "
        f"{lov.atgard}, byggnadsarea {lov.byggnadsarea_m2:.1f} m²."
    )
    if lov.anmarkning:
        text += f" [{lov.anmarkning}]"
    return text


def _korsjamforelsefakta(korsjamforelse: dict[str, str] | None) -> str | None:
    if not korsjamforelse:
        return None
    delar = [f"{namn}: {status}" for namn, status in sorted(korsjamforelse.items())]
    return (
        "Korskontroll skannad handling (OCR) mot registerposten — "
        + "; ".join(delar) + "."
    )


def _areadeltafakta(delta) -> str:
    return (
        f"Verklig byggnadsarea {delta.verklig_area_m2:.1f} m² mot godkänd "
        f"{delta.godkand_area_m2:.1f} m² — skillnad {delta.area_diff_m2:+.1f} m² "
        f"({delta.area_diff_procent:+.1f} %)."
    )


def _lagedeltafakta(delta) -> str | None:
    if delta.avstand_grans_godkant_m is None or delta.avstand_grans_verklig_m is None:
        return None
    return (
        f"Byggnaden ligger {delta.avstand_grans_verklig_m:.1f} m från fastighetsgräns "
        f"mot godkända {delta.avstand_grans_godkant_m:.1f} m; "
        f"{delta.utanfor_godkant_m2:.1f} m² av byggnaden ligger utanför godkänt läge "
        f"(förskjutning {delta.centroid_forskjutning_m:.1f} m)."
    )


def _regelverksfakta(lage) -> str | None:
    if lage.pbl_vid_beslut is None:
        return None
    text = f"Lovet prövas enligt {lage.pbl_vid_beslut} ({lage.tillsyn_lagrum})."
    if lage.overgangsregel_tillampad:
        text += (
            " Övergångsbestämmelsen i PBL 2010:900 p. 2 tillämpas: ärenden "
            "påbörjade före 2011-05-02 följer äldre lag tills de är slutligt avgjorda."
        )
    return text
```

Dating fact: reuse fall1's wording via a local copy (fall1's `_dateringsfakta` is private; copy the two-branch text with "färdigställ" wording):

```python
def _dateringsfakta(datering) -> str:
    if datering.forsta_ar_med is None:
        return (
            "Färdigställandet kunde inte dateras från ortofoto-tidslinjen "
            "(för få eller otydliga årgångar)."
        )
    return (
        f"Byggnaden i sitt nuvarande läge syns första gången i ortofoto "
        f"{datering.forsta_ar_med} och saknas fortfarande i ortofoto "
        f"{datering.sista_ar_utan}."
    )
```

Bedömning påstående (NO guilt words; väsentlighet explicitly handed over; decimal comma rendering comes from `:.1f` being replaced — use Swedish comma by `.replace(".", ",")` ONLY inside the two delta fact strings' numbers if desired; simplest: format with f-strings then `_sv(x)` helper `f"{x:+.1f}".replace(".", ",")` for the area fact so the `+14,8` test passes):

```python
def _bedomning_pastaende(lage, delta) -> str:
    text = (
        f"Byggnadens utförande avviker mätbart från det beviljade lovet "
        f"({delta.area_diff_m2:+.1f} m² area; "
        f"{delta.utanfor_godkant_m2:.1f} m² utanför godkänt läge). "
        "Om avvikelsen är väsentlig är en rättslig kvalificering som görs av "
        "handläggaren, inte av systemet."
    )
    if lage.rattelse_preskriberad is True:
        text += " Möjligheten till rättelseföreläggande (10 år) är preskriberad."
    elif lage.rattelse_preskriberad is False:
        text += " Möjligheten till rättelseföreläggande (10 år) är inte preskriberad."
    if lage.sanktionsavgift_mojlig is False:
        text += " Byggsanktionsavgift (5 år) är utesluten."
    elif lage.sanktionsavgift_mojlig is True:
        text += " Byggsanktionsavgift (5 år) är fortfarande möjlig."
    return text
```

Number formatting: apply `.replace(".", ",")` to the formatted numbers in `_areadeltafakta` (the test accepts either, but Swedish copy prefers comma).

- [ ] **Step 3: Run tests, whole suite, ruff; commit**

```bash
python -m pytest tests/test_fall3_dossier.py -q && python -m pytest -q && python -m ruff check src tests
git add src/geo_tillsyn/fall3.py tests/test_fall3_dossier.py
git commit -m "feat(fall3): dossier - lov, korskontroll, delta och styrande lag i tre nivaer"
```

---

### Task 7: Runner — `kor_fall3` + `analysera_fall3_punkt` + overlay

**Files:**
- Modify: `src/geo_tillsyn/runner.py` (append Fall 3 section; add `FASTIGHETSGRANS_LAYER = "SundsvallsKommun:FastighetGrans_linje"` and `LOVARKIV_KATALOG = Path(__file__).resolve().parents[2] / "data" / "synthetic" / "lovarkiv"` near the other constants)
- Test: `tests/test_fall3_runner.py`

**Interfaces:**
- Consumes: `_valj_byggnad`, `_getfeature_url`, `hamta_tidslinje`, `datera_byggnad`, `hitta_lov`, `tolka_handling`, `korsjamfor`, `jamfor_lage`, `fall3_lage`, `bygg_fall3_dossier`, existing constants.
- Produces:
  - `_fall3_underlag(ows_url, punkt, nu, radie_m, ar, hamta_wfs, hamta_wms, lovarkiv_katalog, ocr) -> dict | None` — `None` result key pattern NOT used; returns dict with `"lov": LovBeslut | None`; when lov is None downstream renders the honest no-permit answer.
  - `kor_fall3(ows_url, punkt, ut_katalog, nu, radie_m=100.0, ar=None, hamta_wfs=query_wfs_features, hamta_wms=None, lovarkiv_katalog=LOVARKIV_KATALOG, ocr=None) -> Path` — writes `fall3_dossier.md`, `overlay.png`, `tidslinje/*.png`; raises `ValueError("Inget (test)ärende ...")` when no lov matches.
  - `analysera_fall3_punkt(ows_url, punkt, nu, radie_m=100.0, ar=None, hamta_wfs=query_wfs_features, hamta_wms=None, lovarkiv_katalog=LOVARKIV_KATALOG, ocr=None) -> dict` — compact JSON; when no lov: `{"lov_hittat": False, "meddelande": "Inget ärende i (test)arkivet för punkten — se Fall 1-analysen för lovplikt.", ...}`.

Implementation notes for the subagent:
- `_fall3_underlag` flow: fetch byggnader (bbox radie) → `_valj_byggnad` → footprint/area → `hitta_lov(lovarkiv_katalog, punkt=punkt)`; if None return `{"lov": None, "byggnad_id": ..., "bbox_sok": ...}` early. Else: fetch gränser `hamta_wfs(ows_url, FASTIGHETSGRANS_LAYER, bbox=bbox_sok, max_features=200)` inside try/except (failure ⇒ `granser=None` + osäkerhet, same pattern as strandskydd in `_fall1_underlag`); build `granser` as `[shape(f["geometry"]) for f in ...]`; tidslinje over `bbox_foot` (bounds+30 m) exactly as `_fall1_underlag` including the `bilder_for_datering` re-flag idiom → `datera_byggnad`; `delta = jamfor_lage(lov.godkant_lage, footprint, granser)`; handling: if `lov.handling` and file exists → `tolka_handling(lov.handling.read_bytes(), ocr=ocr)` + `korsjamfor` (OCR exceptions already handled inside), else `tolkat=None, korsjamforelse=None` + osäkerhet "Ingen skannad handling i ärendet — korskontroll ej möjlig."; `lage = fall3_lage(date.fromisoformat(lov.beslutsdatum), datering.sista_ar_utan, datering.forsta_ar_med, bedomningsdatum, delta)`; always append `_BYGGLOVSREGISTER_OSAKERHET`-analog: `"Lovuppgifterna kommer ur ett SYNTETISKT testarkiv (mock-ByggR) — prototypfasen har ingen åtkomst till kommunens ärendesystem."`.
- Overlay: draw on the LAST tidslinje image (or blank 512² if none): `ImageDraw.polygon` outlines — approved in blue `(40, 80, 255)`, actual in red `(230, 40, 40)` — coordinates mapped world→pixel with the same bbox math as `datering._footprint_mask` (row 0 = maxy). Legend text "BLÅ = godkänt läge, RÖD = verkligt läge". Save `ut_katalog / "overlay.png"`.
- `analysera_fall3_punkt` result keys: `byggnad_id, punkt{easting,northing,crs}, lov_hittat, dnr, beslutsdatum, pbl_vid_beslut, overgangsregel_tillampad, godkand_area_m2, verklig_area_m2, area_diff_m2, area_diff_procent, utanfor_godkant_m2, avstand_grans_godkant_m, avstand_grans_verklig_m, korsjamforelse, sista_ar_utan, forsta_ar_med, rattelse_preskriberad, sanktionsavgift_mojlig, matningskritiska, osakerheter, kallor, hamtad` — all floats rounded to 1 decimal.

- [ ] **Step 1: Write the failing tests**

```python
"""Runner tests for Fall 3 — hermetic fake WFS/WMS + temp lovarkiv.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

import io
import json
import re

import numpy as np
from PIL import Image

from geo_tillsyn.runner import analysera_fall3_punkt, kor_fall3

PUNKT = (105.0, 104.0)
NU = "2026-07-23T00:00:00Z"

_BYGGNAD = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "id": "bal_byggnad_yta.1",
            "geometry": {
                "type": "Polygon",
                # Actual: 12x9 m = 108 m², at (100,100)-(112,109)
                "coordinates": [[[100, 100], [112, 100], [112, 109], [100, 109], [100, 100]]],
            },
            "properties": {"bal_nybyggnadsar": 2010},
        }
    ],
}

_GRANSER = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "id": "grans.1",
            "geometry": {"type": "LineString", "coordinates": [[118, 80], [118, 130]]},
            "properties": {},
        }
    ],
}


def _fake_wfs(_url, layer, bbox=None, max_features=None):
    if "byggnad" in layer:
        return _BYGGNAD
    if "FastighetGrans" in layer:
        return _GRANSER
    return {"type": "FeatureCollection", "features": []}


def _png(seed: int) -> bytes:
    rng = np.random.RandomState(seed)
    arr = rng.uniform(30, 120, (64, 64)).astype(np.uint8)
    # persistent "building" texture in later years is added by caller
    img = Image.fromarray(arr, mode="L")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _bygg_png() -> bytes:
    rng = np.random.RandomState(7)
    base = rng.uniform(30, 120, (64, 64))
    base[16:48, 16:48] = 210.0
    base[18:46:4, 18:46] = 160.0
    arr = (base + rng.normal(0, 3, (64, 64))).clip(0, 255).astype(np.uint8)
    img = Image.fromarray(arr, mode="L")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


_BYGG = _bygg_png()


def _fake_wms(url, layer, bbox, crs=None, width=None, height=None):
    ar = int(re.search(r"(19|20)\d{2}", layer).group(0))
    return _BYGG if ar >= 2010 else _png(ar)


def _skriv_lov(katalog):
    katalog.mkdir(parents=True, exist_ok=True)
    record = {
        "syntetisk": True,
        "anmarkning": "Syntetiskt testärende.",
        "dnr": "SBN 2009-0412",
        "fastighet": "ALNÖ-USLAND 1:45",
        "beslutsdatum": "2009-06-19",
        "atgard": "Nybyggnad av enbostadshus",
        "byggnadsarea_m2": 80.0,
        "godkant_lage": {
            "crs": "EPSG:3014",
            # Approved: 10x8 m = 80 m² at (100,100)-(110,108)
            "koordinater": [[100, 100], [110, 100], [110, 108], [100, 108]],
        },
        "villkor": [],
        "handling": None,
    }
    (katalog / "a.json").write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")


def test_kor_fall3_skriver_dossier_och_overlay(tmp_path):
    arkiv = tmp_path / "lovarkiv"
    _skriv_lov(arkiv)
    ut = tmp_path / "ut"

    dossier = kor_fall3(
        "https://example.com/ows",
        PUNKT,
        ut,
        NU,
        ar=[2007, 2010, 2013, 2015, 2021, 2023],
        hamta_wfs=_fake_wfs,
        hamta_wms=_fake_wms,
        lovarkiv_katalog=arkiv,
    )

    md = dossier.read_text(encoding="utf-8")
    assert dossier.name == "fall3_dossier.md"
    assert "SBN 2009-0412" in md
    assert (ut / "overlay.png").exists()


def test_analysera_fall3_ar_kompakt_och_korrekt(tmp_path):
    arkiv = tmp_path / "lovarkiv"
    _skriv_lov(arkiv)

    svar = analysera_fall3_punkt(
        "https://example.com/ows",
        PUNKT,
        NU,
        ar=[2007, 2010, 2013, 2015, 2021, 2023],
        hamta_wfs=_fake_wfs,
        hamta_wms=_fake_wms,
        lovarkiv_katalog=arkiv,
    )

    assert svar["lov_hittat"] is True
    assert svar["godkand_area_m2"] == 80.0
    assert svar["verklig_area_m2"] == 108.0
    assert svar["area_diff_m2"] == 28.0
    assert svar["avstand_grans_godkant_m"] == 8.0   # 118 - 110
    assert svar["avstand_grans_verklig_m"] == 6.0   # 118 - 112
    assert "ÄPBL" in svar["pbl_vid_beslut"]
    assert len(json.dumps(svar, ensure_ascii=False).encode()) < 8_000
    assert any("syntetiskt" in o.lower() for o in svar["osakerheter"])


def test_utan_lov_ges_arligt_svar(tmp_path):
    arkiv = tmp_path / "tomt"
    arkiv.mkdir()

    svar = analysera_fall3_punkt(
        "https://example.com/ows",
        PUNKT,
        NU,
        ar=[2007, 2010, 2013, 2015, 2021, 2023],
        hamta_wfs=_fake_wfs,
        hamta_wms=_fake_wms,
        lovarkiv_katalog=arkiv,
    )

    assert svar["lov_hittat"] is False
    assert "Fall 1" in svar["meddelande"]


def test_grans_bortfall_ger_osakerhet(tmp_path):
    arkiv = tmp_path / "lovarkiv"
    _skriv_lov(arkiv)

    def wfs_utan_granser(url, layer, bbox=None, max_features=None):
        if "FastighetGrans" in layer:
            raise RuntimeError("layer down")
        return _fake_wfs(url, layer, bbox, max_features)

    svar = analysera_fall3_punkt(
        "https://example.com/ows",
        PUNKT,
        NU,
        ar=[2007, 2010, 2013, 2015, 2021, 2023],
        hamta_wfs=wfs_utan_granser,
        hamta_wms=_fake_wms,
        lovarkiv_katalog=arkiv,
    )

    assert svar["avstand_grans_verklig_m"] is None
    assert any("fastighetsgräns" in o.lower() for o in svar["osakerheter"])
```

Note on the fake WMS: `hamta_tidslinje`'s injected fetcher signature must match how `timeline.py` calls it — check `timeline.hamta_tidslinje` and mirror the existing `tests/test_fall1_runner.py` fake exactly (same signature, keyed by year regex on layer name). If `test_fall1_runner.py`'s fake differs from the sketch above, COPY the fall1 fake's signature — that file is the source of truth.

- [ ] **Step 2: Run to verify failure, implement runner additions**

Follow the notes in **Interfaces** above. Reuse `_valj_byggnad` and constants; append the Fall 3 section after `analysera_fall1_punkt`. World→pixel mapping for the overlay:

```python
def _varld_till_pixel(punkter, bbox, storlek):
    minx, miny, maxx, maxy = bbox
    bredd, hojd = storlek
    return [
        ((x - minx) / (maxx - minx) * bredd, (maxy - y) / (maxy - miny) * hojd)
        for x, y in punkter
    ]
```

- [ ] **Step 3: Run tests, whole suite, ruff; commit**

```bash
python -m pytest tests/test_fall3_runner.py -q && python -m pytest -q && python -m ruff check src tests
git add src/geo_tillsyn/runner.py tests/test_fall3_runner.py
git commit -m "feat(fall3): runner - kor_fall3, analysera_fall3_punkt (<8kB), overlay godkant vs verkligt"
```

---

### Task 8: MCP tool + CLI + protagonist asset + live verification

**Files:**
- Modify: `src/geo_tillsyn/server.py` (new tool after `analysera_olovligt_byggande_vid_punkt`)
- Modify: `src/geo_tillsyn/cli.py:30-58` (`choices=[7, 1, 3]`, route `kor_fall3`)
- Create: `verktyg/skapa_protagonist_lov.py` (one-shot asset script, live WFS)
- Create (generated, committed): `data/synthetic/lovarkiv/sbn-2009-0412.json` + `sbn-2009-0412-situationsplan.pdf`
- Test: `tests/test_server.py` (extend), `tests/test_cli.py` if it exists (check first with `ls tests/`)

**Interfaces:**
- Produces: MCP tool `analysera_lovavvikelse_vid_punkt(easting: float, northing: float, radie_m: float = 100.0) -> dict` calling `analysera_fall3_punkt(ows_url=SUNDSVALL_OWS, punkt=(easting, northing), nu=_nu(), radie_m=radie_m)`. Docstring in Swedish, same shape as the Fall 1 tool's, ending in "Systemet gör en bedömning — beslutet fattas av handläggaren."; MUST mention that lovuppgifter come from a synthetic test archive.

- [ ] **Step 1: Server tool + test**

Extend `tests/test_server.py` following its existing pattern (check how the fall1 tool is tested there first — mirror it: import the tool function, monkeypatch/inject, or assert tool registration). Minimal registration test if that's the established pattern:

```python
def test_lovavvikelse_verktyget_ar_registrerat():
    import asyncio

    from geo_tillsyn.server import mcp

    verktyg = asyncio.run(mcp.list_tools())
    namn = [v.name for v in verktyg]
    assert "analysera_lovavvikelse_vid_punkt" in namn
```

Implement the tool in `server.py`:

```python
@mcp.tool()
def analysera_lovavvikelse_vid_punkt(
    easting: float,
    northing: float,
    radie_m: float = 100.0,
) -> dict:
    """Analysera avvikelse från beviljat bygglov vid en kartpunkt (Fall 3).

    Hämtar (syntetiskt) lov ur testarkivet, korskontrollerar den skannade
    handlingen (OCR) mot registerposten, kvantifierar avvikelsen mellan
    godkänt och verkligt läge (area, placering, avstånd till gräns), daterar
    färdigställandet via ortofoto-tidslinjen och bedömer PBL-klockorna.
    Vilken lag som styr lovet avgörs av ärendets start (ÄPBL före 2011-05-02).
    Lovuppgifterna kommer ur ett SYNTETISKT testarkiv — prototypfasen har
    ingen åtkomst till kommunens ärendesystem. Systemet gör en bedömning —
    beslutet fattas av handläggaren.

    Args:
        easting: E-koordinat i EPSG:3014 (SWEREF99 17 15, kommunlagrens CRS).
        northing: N-koordinat i EPSG:3014.
        radie_m: Sökradie i meter runt punkten (standard 100).

    Returns:
        Kompakt JSON: lov, korskontroll, kvantifierad avvikelse, klockor,
        osäkerheter och käll-URL:er.
    """
    return analysera_fall3_punkt(
        ows_url=SUNDSVALL_OWS,
        punkt=(easting, northing),
        nu=_nu(),
        radie_m=radie_m,
    )
```

(Import `analysera_fall3_punkt` in the existing runner import line.) CLI: add `3` to `choices`, insert an `elif args.fall == 3:` branch calling `kor_fall3(ows_url=args.ows, punkt=..., ut_katalog=args.ut, nu=nu, radie_m=args.radie, ar=args.ar)`.

Run suite + ruff, commit:

```bash
git add src/geo_tillsyn/server.py src/geo_tillsyn/cli.py tests/test_server.py
git commit -m "feat(fall3): MCP-verktyg analysera_lovavvikelse_vid_punkt + CLI --fall 3"
```

- [ ] **Step 2: Protagonist asset script `verktyg/skapa_protagonist_lov.py`**

One-shot, run manually against live WFS (no test — it is a data-authoring tool; keep it deterministic given the WFS answer):

```python
"""Engångsverktyg: skapa protagonistens syntetiska Fall 3-ärende (lov + handling).

Hämtar huvudbyggnadens verkliga footprint (störst inom 100 m från punkten),
härleder ett godkänt läge (skala 0,85 kring centroiden, förskjutet 2,3 m bort
från närmaste fastighetsgräns) och skriver lovarkiv-JSON + skannad handling.
Determinism: samma WFS-svar -> samma filer.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from mcp_ogc.tools.wfs import query_wfs_features
from shapely import affinity
from shapely.geometry import Point, shape

from geo_tillsyn.handling import VATTENMARKE, rita_situationsplan, till_pdf_bytes
from geo_tillsyn.runner import BYGGNAD_LAYER, FASTIGHETSGRANS_LAYER

OWS = "https://karta.sundsvall.se/geoserver/ows"
PUNKT = (158140.4, 6918389.3)  # ALNÖ-USLAND 1:45 (EPSG:3014)
UT = Path(__file__).resolve().parents[1] / "data" / "synthetic" / "lovarkiv"


def main() -> None:
    e, n = PUNKT
    bbox = (e - 100, n - 100, e + 100, n + 100)
    byggnader = query_wfs_features(OWS, BYGGNAD_LAYER, bbox=bbox, max_features=500)
    storst = max(byggnader["features"], key=lambda f: shape(f["geometry"]).area)
    footprint = shape(storst["geometry"])

    granser = query_wfs_features(OWS, FASTIGHETSGRANS_LAYER, bbox=bbox, max_features=200)
    grans_geoms = [shape(f["geometry"]) for f in granser["features"]]
    narmast = min(grans_geoms, key=lambda g: g.distance(footprint))

    godkant = affinity.scale(footprint, 0.85, 0.85, origin="centroid")
    p_grans = narmast.interpolate(narmast.project(footprint.centroid))
    c = footprint.centroid
    langd = math.hypot(c.x - p_grans.x, c.y - p_grans.y) or 1.0
    riktning = ((c.x - p_grans.x) / langd, (c.y - p_grans.y) / langd)
    godkant = affinity.translate(godkant, xoff=riktning[0] * 2.3, yoff=riktning[1] * 2.3)
    godkant = godkant.simplify(0.05)

    area = round(godkant.area, 1)
    koords = [[round(x, 2), round(y, 2)] for x, y in godkant.exterior.coords[:-1]]
    avstand = round(godkant.distance(narmast), 1)

    record = {
        "syntetisk": True,
        "anmarkning": "Syntetiskt testärende — inga verkliga byggärenden (prototypfas).",
        "dnr": "SBN 2009-0412",
        "fastighet": "ALNÖ-USLAND 1:45",
        "beslutsdatum": "2009-06-19",
        "laga_kraft": "2009-07-24",
        "atgard": "Nybyggnad av enbostadshus",
        "byggnadsarea_m2": area,
        "hojd_m": None,
        "godkant_lage": {"crs": "EPSG:3014", "koordinater": koords},
        "villkor": [f"Byggnaden placeras minst {str(avstand).replace('.', ',')} m från fastighetsgräns."],
        "handling": "sbn-2009-0412-situationsplan.pdf",
    }

    UT.mkdir(parents=True, exist_ok=True)
    (UT / "sbn-2009-0412.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    minx = min(k[0] for k in koords)
    miny = min(k[1] for k in koords)
    lokala = [(x - minx, y - miny) for x, y in koords]
    falt = {
        "DNR": "SBN 2009-0412",
        "BESLUTSDATUM": "2009-06-19",
        "BYGGNADSAREA": f"{str(area).replace('.', ',')} m2",
        "AVSTAND TILL GRANS": f"{str(avstand).replace('.', ',')} m",
    }
    pdf = till_pdf_bytes(rita_situationsplan(falt, lokala, VATTENMARKE))
    (UT / "sbn-2009-0412-situationsplan.pdf").write_bytes(pdf)
    print(f"Skrev {UT / 'sbn-2009-0412.json'} (BYA {area} m², avstånd {avstand} m)")


if __name__ == "__main__":
    main()
```

Run it: `python verktyg/skapa_protagonist_lov.py`. Inspect the JSON (sane area, ≥4 coordinates), open the PDF (watermark visible). Commit assets + script:

```bash
git add verktyg/skapa_protagonist_lov.py data/synthetic/lovarkiv/
git commit -m "feat(fall3): protagonistens syntetiska testarende (lov + skannad handling)"
```

- [ ] **Step 3: Live verification (manual, not a subagent task)**

```powershell
geo-tillsyn 158140.4 6918389.3 --fall 3 --ut demo_ut/alno-usland-1-45-fall3
```

Check `fall3_dossier.md`: lov fact with syntetisk marking, ÄPBL as governing law, quantified delta (≈ +18 % / 2,3 m), completion interval from live ortofoto, OCR cross-check section (or the graceful "OCR ej tillgänglig" osäkerhet if tesseract is absent), empty Beslut, `overlay.png` with both outlines. If tesseract was installed in Task 3, verify the cross-check shows `överens` on all three fields.

- [ ] **Step 4: Eneo re-sync (manual)**

Restart the MCP server detached (`geo-tillsyn-mcp --host 0.0.0.0 --port 8464`), then re-run the known drill (spikes/spike-a-live/drive_alive.py or manual API calls): sync tools (expect `tools_discovered: 4`), tenant-enable the new tool (PUT `/mcp-servers/settings/tools/{id}/`), assistant-enable via `mcp_tools` on assistant `1d9f8781-41c4-40d8-8187-74ae0f1083a7`. For a chat demo of Fall 3 with the mock model, pin `MOCK_PREFERRED_TOOL=lovavvikelse` in the overlay.

- [ ] **Step 5: Final commit + memory update**

Whole suite + ruff one last time; commit anything remaining; update the `pilot3-prototype-phase` memory with a Fall 3 completion block (live numbers, any surprises).

---

## Self-review notes (already applied)

- Spec §1–§7 all mapped: lovarkiv→Task 1, handling→Task 2, lovtolk→Task 3, delta→Task 4, juridik→Task 5, dossier→Task 6, runner/MCP/CLI→Task 7–8, asset+live→Task 8.
- `korsjamfor` takes the full `TolkatDokument` (not just falt) so `saknas` distinguishes "OCR ran but field missing" from "OCR unavailable" (the latter never reaches korsjamfor — runner passes `korsjamforelse=None`).
- Fall 1's clock refactor is behavior-preserving and committed separately so a regression bisects cleanly.
- The fake-WMS signature in Task 7 must be copied from `tests/test_fall1_runner.py` — flagged in the task.

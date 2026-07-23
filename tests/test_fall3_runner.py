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


def _fake_wms(wms_url, layer, bbox, crs, width, height):
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

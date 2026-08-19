"""Integration-shaped unit tests for the Fall 1 runner (injected fetchers).

The fake WMS is a deterministic time machine: vintages before the build year
return independent noise, vintages after return a persistent structured
pattern — so the datering core finds the interval without any network.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

import io
import json
import re

import numpy as np
import pytest
from PIL import Image

from geo_tillsyn.runner import analysera_fall1_punkt, kor_fall1

OWS = "http://example.test/ows"
SIZE = 64
MED_AR = {2015, 2021, 2023}  # building visible from 2015 on
ALLA_AR = [2007, 2010, 2013, 2015, 2021, 2023]


def _png(arr: np.ndarray) -> bytes:
    buf = io.BytesIO()
    Image.fromarray(arr.astype(np.uint8), mode="L").save(buf, format="PNG")
    return buf.getvalue()


def _fejk_wms(wms_url, layer, bbox, crs, width, height):
    ar = int(re.search(r"(19|20)\d{2}", layer).group(0))
    rng = np.random.RandomState(ar)
    if ar in MED_AR:
        base = np.tile(np.linspace(40, 80, SIZE), (SIZE, 1))
        base[16:48, 16:48] = 210.0
        base[18:46:4, 18:46] = 160.0
        return _png(base + rng.normal(0, 4, (SIZE, SIZE)))
    return _png(rng.uniform(30, 120, (SIZE, SIZE)))


BYGGNADER = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "id": "bal_byggnad_yta.38472",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[10, 10], [20, 10], [20, 20], [10, 20], [10, 10]]],
            },
            "properties": {"bal_nybyggnadsar": 2014},
        }
    ],
}
STRANDSKYDD = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "id": "lm_strandskydd_y.1",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[0, 0], [100, 0], [100, 100], [0, 100], [0, 0]]],
            },
            "properties": {"lm_aktbeteckning": "2281K-ÖVR-241"},
        }
    ],
}


def _fejk_wfs(wfs_url, type_name, bbox=None, max_features=100):
    if type_name.endswith("bal_byggnad_yta"):
        return BYGGNADER
    if type_name.endswith("lm_strandskydd_y"):
        return STRANDSKYDD
    raise RuntimeError("simulated broken layer")


def test_kor_fall1_skriver_dossier_med_hela_kedjan(tmp_path):
    resultat = kor_fall1(
        ows_url=OWS,
        punkt=(15.0, 15.0),
        ut_katalog=tmp_path,
        nu="2026-07-21T10:00:00Z",
        ar=ALLA_AR,
        hamta_wfs=_fejk_wfs,
        hamta_wms=_fejk_wms,
    )

    md = resultat.read_text(encoding="utf-8")
    assert resultat.name == "fall1_dossier.md"
    # Dating: absent 2013, first visible 2015.
    assert "2015" in md and "2013" in md
    # BAL 2014 inside the interval.
    assert "2014" in md and "förenlig" in md
    # 100 m2 was never exempt; both PBL clocks have run out by 2026.
    assert "bygglovsplikt" in md.lower()
    assert "11 kap. 20 §" in md and "preskriberad" in md
    assert "11 kap. 58 §" in md
    # Inside strandskydd: the MB clock never stops — cross-reference present.
    assert "MÖD 2021:6" in md
    # Prototype honesty: no permit register available.
    assert "Bygglovsregistret" in md
    # Timeline images written for the used vintages.
    assert (tmp_path / "tidslinje" / "ortofoto_2015.png").exists()


def test_punkt_utan_byggnad_ger_tydligt_fel(tmp_path):
    tomt = {"type": "FeatureCollection", "features": []}

    with pytest.raises(ValueError, match="[Ii]ngen byggnad"):
        kor_fall1(
            ows_url=OWS,
            punkt=(15.0, 15.0),
            ut_katalog=tmp_path,
            nu="2026-07-21T10:00:00Z",
            ar=ALLA_AR,
            hamta_wfs=lambda *a, **k: tomt,
            hamta_wms=_fejk_wms,
        )


def test_analysera_fall1_punkt_ar_kompakt_och_mcp_vanlig():
    resultat = analysera_fall1_punkt(
        ows_url=OWS,
        punkt=(15.0, 15.0),
        nu="2026-07-21T10:00:00Z",
        ar=ALLA_AR,
        hamta_wfs=_fejk_wfs,
        hamta_wms=_fejk_wms,
    )

    assert resultat["byggnad_id"] == "bal_byggnad_yta.38472"
    assert resultat["sista_ar_utan"] == 2013
    assert resultat["forsta_ar_med"] == 2015
    assert resultat["bal_nybyggnadsar"] == 2014
    assert resultat["bygglov_kravdes"] is True
    assert resultat["rattelse_preskriberad"] is True
    assert resultat["inom_strandskydd"] is True
    assert resultat["kallor"]

    serialiserad = json.dumps(resultat, ensure_ascii=False)
    assert "coordinates" not in serialiserad
    assert len(serialiserad.encode()) < 8_000


def test_mcp_servern_har_fall1_verktyget():
    import asyncio

    from geo_tillsyn.server import mcp

    verktyg = {t.name for t in asyncio.run(mcp.list_tools())}
    assert "analysera_olovligt_byggande_vid_punkt" in verktyg


# --- rättigheter / gemensamhetsanläggningar (Lantmäteriet via GeoServer) --------

RATTIGHETER = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "id": "rk_rattighet_y.1",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[12, 0], [16, 0], [16, 40], [12, 40], [12, 0]]],
            },
            "properties": {
                "Typ": "Ledningsrätt", "AKTBET": "2281-80/58", "RANDAMAL": "VATTEN OCH AVLOPP",
                "FASTIGHET": "ALNÖ-VI 3:112", "RBESK": None,
            },
        },
        {
            "type": "Feature",
            "id": "rk_rattighet_y.2",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[200, 200], [210, 200], [210, 210], [200, 210], [200, 200]]],
            },
            "properties": {"Typ": "Officialservitut", "AKTBET": "LÅNGT-BORT", "RANDAMAL": "VÄG"},
        },
    ],
}
GA = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "id": "rk_ga_y.1",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[0, 18], [30, 18], [30, 22], [0, 22], [0, 18]]],
            },
            "properties": {"FASTIGHET": "ALNÖ-USLAND GA:6", "AKTBET": "2281K-F-50", "ANM": "SPILLVATTENLEDNING"},
        }
    ],
}


def _fejk_wfs_med_rattigheter(wfs_url, type_name, bbox=None, max_features=100):
    if type_name == "Lantmateriet:rk_rattighet_y":
        return RATTIGHETER
    if type_name == "Lantmateriet:rk_ga_y":
        return GA
    if type_name in ("Lantmateriet:rk_rattighet_l", "Lantmateriet:rk_ga_l"):
        return {"type": "FeatureCollection", "features": []}
    return _fejk_wfs(wfs_url, type_name, bbox, max_features)


def test_rattigheter_som_beror_byggnaden_blir_fakta_med_kalla(tmp_path):
    resultat = kor_fall1(
        ows_url=OWS, punkt=(15.0, 15.0), ut_katalog=tmp_path,
        nu="2026-07-21T10:00:00Z", ar=ALLA_AR,
        hamta_wfs=_fejk_wfs_med_rattigheter, hamta_wms=_fejk_wms,
    )
    md = resultat.read_text(encoding="utf-8")
    assert "berör ledningsrätt 2281-80/58 (VATTEN OCH AVLOPP) på ALNÖ-VI 3:112." in md
    assert "berör gemensamhetsanläggning 2281K-F-50 (SPILLVATTENLEDNING) på ALNÖ-USLAND GA:6." in md
    assert "LÅNGT-BORT" not in md  # berör inte byggnaden
    assert "Lantmateriet:rk_rattighet_y (WFS)" in md


def test_analysera_fall1_bar_rattigheter_och_deklarerar_otillgangliga_lager():
    resultat = analysera_fall1_punkt(
        ows_url=OWS, punkt=(15.0, 15.0), nu="2026-07-21T10:00:00Z", ar=ALLA_AR,
        hamta_wfs=_fejk_wfs_med_rattigheter, hamta_wms=_fejk_wms,
    )
    assert [r["typ"] for r in resultat["rattigheter"]] == ["Ledningsrätt", "Gemensamhetsanläggning"]
    assert resultat["rattigheter"][0]["aktbeteckning"] == "2281-80/58"

    # Alla rättighetslager trasiga (som _fejk_wfs gör) → en osäkerhet per lager, inget krascher.
    trasigt = analysera_fall1_punkt(
        ows_url=OWS, punkt=(15.0, 15.0), nu="2026-07-21T10:00:00Z", ar=ALLA_AR,
        hamta_wfs=_fejk_wfs, hamta_wms=_fejk_wms,
    )
    assert trasigt["rattigheter"] == []
    koder = [getattr(o, "kod", None) for o in trasigt["osakerheter"]]
    assert koder.count("runner.rattighetslager_otillgangligt") == 4

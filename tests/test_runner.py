"""Integration-shaped unit test for the Fall 7 runner (injected fetchers, no network).

SPDX-License-Identifier: AGPL-3.0-or-later
"""

from geo_tillsyn.runner import kor_fall7

OWS = "http://example.test/ows"

BYGGNADER = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "id": "bal_byggnad_yta.10",
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
    if type_name == "SundsvallsKommun:bal_byggnad_yta":
        return BYGGNADER
    if type_name == "SundsvallsKommun:lm_strandskydd_y":
        return STRANDSKYDD
    # The Lansstyrelsen layers are broken server-side; the runner must turn
    # that into declared uncertainty, not crash and not stay silent.
    raise RuntimeError("simulated GeoServer IndexOutOfBoundsException")


def _fejk_wms(wms_url, layer, bbox, crs, width, height):
    return b"\x89PNG" + b"x" * 100_000


def test_kor_fall7_skriver_dossier_och_tidslinje(tmp_path):
    resultat = kor_fall7(
        ows_url=OWS,
        punkt=(15.0, 15.0),
        radie_m=100.0,
        ut_katalog=tmp_path,
        nu="2026-07-17T10:00:00Z",
        ar=[1960, 2023],
        hamta_wfs=_fejk_wfs,
        hamta_wms=_fejk_wms,
    )

    md = resultat.read_text(encoding="utf-8")
    assert resultat.name == "dossier.md"
    assert "## 1. Fakta" in md and "## 2. Bedömning" in md and "## 3. Beslut" in md
    assert "bal_byggnad_yta.10" in md and "helt inom" in md
    assert "2281K-ÖVR-241" in md
    assert "hämtad 2026-07-17T10:00:00Z" in md

    assert (tmp_path / "tidslinje" / "ortofoto_1960.png").exists()
    assert (tmp_path / "tidslinje" / "ortofoto_2023.png").exists()


def test_juridisk_tidsdimension_ingar_i_dossieren(tmp_path):
    resultat = kor_fall7(
        ows_url=OWS,
        punkt=(15.0, 15.0),
        radie_m=100.0,
        ut_katalog=tmp_path,
        nu="2026-07-17T10:00:00Z",
        ar=[2023],
        hamta_wfs=_fejk_wfs,
        hamta_wms=_fejk_wms,
    )

    md = resultat.read_text(encoding="utf-8")
    # bal_nybyggnadsar=2014 -> the zone applied at construction; the mandatory
    # preskription + skälighet counterweight must render, citing official SFS.
    assert "uppfördes år 2014" in md
    assert "MÖD 2021:6" in md and "MÖD 2017:16" in md
    assert "rkrattsdb.gov.se/SFSdoc/98/980808.PDF" in md


def test_otillgangliga_regelkallor_blir_deklarerad_osakerhet(tmp_path):
    resultat = kor_fall7(
        ows_url=OWS,
        punkt=(15.0, 15.0),
        radie_m=100.0,
        ut_katalog=tmp_path,
        nu="2026-07-17T10:00:00Z",
        ar=[2023],
        hamta_wfs=_fejk_wfs,
        hamta_wms=_fejk_wms,
    )

    md = resultat.read_text(encoding="utf-8")
    assert "Ej fastställt" in md
    assert "UtvidgatStrandskydd_yta" in md
    assert "UpphavdaStrandskydd_yta" in md

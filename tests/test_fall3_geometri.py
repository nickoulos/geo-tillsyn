"""Runner tests for fall3_geometri — GeoJSON export of godkänt/verkligt läge.

Hermetic: fake WFS + temp lovarkiv, same fixtures as test_fall3_runner.py.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

import json

from geo_tillsyn.runner import fall3_geometri

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
                # Actual: 12x9 m = 108 m², at (100,100)-(112,109). 3D coords
                # mirror karta.sundsvall.se's live WFS (x, y, z survey noise).
                "coordinates": [
                    [
                        [100, 100, 12.3],
                        [112, 100, 12.3],
                        [112, 109, 12.3],
                        [100, 109, 12.3],
                        [100, 100, 12.3],
                    ]
                ],
            },
            "properties": {"bal_nybyggnadsar": 2010},
        }
    ],
}


def _fake_wfs(_url, layer, bbox=None, max_features=None):
    if "byggnad" in layer:
        return _BYGGNAD
    return {"type": "FeatureCollection", "features": []}


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


def test_fall3_geometri_med_lov_returnerar_geojson(tmp_path):
    arkiv = tmp_path / "lovarkiv"
    _skriv_lov(arkiv)

    resultat = fall3_geometri(
        "https://example.com/ows",
        PUNKT,
        NU,
        hamta_wfs=_fake_wfs,
        lovarkiv_katalog=arkiv,
    )

    assert resultat["lov_hittat"] is True
    assert resultat["dnr"] == "SBN 2009-0412"

    godkant = resultat["godkant_lage"]
    verkligt = resultat["verkligt_lage"]
    assert godkant["type"] == "Polygon"
    assert verkligt["type"] == "Polygon"

    # No z-coordinates should leak through (force_2d applied to footprint).
    for ring in verkligt["coordinates"]:
        for coord in ring:
            assert len(coord) == 2


def test_fall3_geometri_utan_lov_ger_nulls(tmp_path):
    arkiv = tmp_path / "tomt"
    arkiv.mkdir()

    resultat = fall3_geometri(
        "https://example.com/ows",
        PUNKT,
        NU,
        hamta_wfs=_fake_wfs,
        lovarkiv_katalog=arkiv,
    )

    assert resultat == {
        "lov_hittat": False,
        "godkant_lage": None,
        "verkligt_lage": None,
        "dnr": None,
    }

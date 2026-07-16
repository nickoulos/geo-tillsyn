"""Unit tests for the strandskydd intersection analysis (REALITY ∩ RULE).

Pure geometry on synthetic GeoJSON — hermetic, no network, no mocks.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

import math

from geo_tillsyn.analysis import analysera_strandskydd


def _polygon_feature(feature_id, coords, properties=None):
    return {
        "type": "Feature",
        "id": feature_id,
        "geometry": {"type": "Polygon", "coordinates": [coords]},
        "properties": properties or {},
    }


def _square(minx, miny, maxx, maxy):
    return [
        [minx, miny],
        [maxx, miny],
        [maxx, maxy],
        [minx, maxy],
        [minx, miny],
    ]


def _fc(features):
    return {"type": "FeatureCollection", "features": features}


ZON = _fc(
    [
        _polygon_feature(
            "lm_strandskydd_y.1",
            _square(0, 0, 100, 100),
            {"lm_aktbeteckning": "2281K-ÖVR-241", "lm_detaljtyp": "Strandskydd"},
        )
    ]
)


def test_byggnad_helt_inom_zon():
    byggnader = _fc([_polygon_feature("bal_byggnad_yta.10", _square(10, 10, 20, 20))])

    (analys,) = analysera_strandskydd(byggnader, ZON)

    assert analys.byggnad_id == "bal_byggnad_yta.10"
    assert analys.laege == "inom"
    assert analys.andel_inom == 1.0
    assert analys.avstand_m == 0.0
    assert analys.zon_referenser == ["2281K-ÖVR-241"]


def test_byggnad_helt_utanfor_zon_med_avstand():
    byggnader = _fc([_polygon_feature("bal_byggnad_yta.20", _square(200, 200, 210, 210))])

    (analys,) = analysera_strandskydd(byggnader, ZON)

    assert analys.laege == "utanfor"
    assert analys.andel_inom == 0.0
    # Nearest zone corner (100,100) to nearest building corner (200,200).
    assert math.isclose(analys.avstand_m, math.sqrt(2) * 100, rel_tol=1e-9)
    assert analys.zon_referenser == []


def test_byggnad_delvis_inom_zon():
    # Straddles the zone's east edge at x=100: exactly half the area inside.
    byggnader = _fc([_polygon_feature("bal_byggnad_yta.30", _square(90, 10, 110, 30))])

    (analys,) = analysera_strandskydd(byggnader, ZON)

    assert analys.laege == "delvis"
    assert math.isclose(analys.andel_inom, 0.5, rel_tol=1e-9)
    assert analys.avstand_m == 0.0
    assert analys.zon_referenser == ["2281K-ÖVR-241"]


def test_zon_utan_aktbeteckning_faller_tillbaka_pa_feature_id():
    zon = _fc([_polygon_feature("lm_strandskydd_y.99", _square(0, 0, 100, 100))])
    byggnader = _fc([_polygon_feature("b.1", _square(10, 10, 20, 20))])

    (analys,) = analysera_strandskydd(byggnader, zon)

    assert analys.zon_referenser == ["lm_strandskydd_y.99"]


def test_flera_byggnader_ger_en_analys_per_byggnad():
    byggnader = _fc(
        [
            _polygon_feature("b.inne", _square(10, 10, 20, 20)),
            _polygon_feature("b.ute", _square(500, 500, 510, 510)),
        ]
    )

    analyser = analysera_strandskydd(byggnader, ZON)

    assert [a.byggnad_id for a in analyser] == ["b.inne", "b.ute"]
    assert [a.laege for a in analyser] == ["inom", "utanfor"]

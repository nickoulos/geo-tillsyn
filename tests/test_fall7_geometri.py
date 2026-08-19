"""Runner tests for rangordna_traffar + fall7_geometri — radar-lite GeoJSON export.

Hermetic: fake WFS, same fixture shapes as test_runner.py.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

import pytest

from geo_tillsyn.runner import fall7_geometri, rangordna_traffar

OWS = "http://example.test/ows"


# --- rangordna_traffar (ren funktion) --------------------------------------------


def _traff(byggnad_id, laege, byggnads_ar, gallde_vid_uppforande):
    return {
        "byggnad_id": byggnad_id,
        "laege": laege,
        "byggnads_ar": byggnads_ar,
        "gallde_vid_uppforande": gallde_vid_uppforande,
        "dispens_kravs_idag": True,
        "preskriberas": False,
        "har_atgarder": False,
    }


def test_rangordna_traffar_grupperar_a_b_c():
    a = _traff("a", "delvis", 2015, True)  # (a) gällde vid uppförande
    b = _traff("b", "inom", None, None)  # (b) år okänt
    c = _traff("c", "inom", 1950, False)  # (c) gällde inte

    resultat = rangordna_traffar([c, b, a])  # input order shouldn't matter

    assert [t["byggnad_id"] for t in resultat] == ["a", "b", "c"]
    assert [t["rang"] for t in resultat] == [1, 2, 3]


def test_rangordna_traffar_inom_fore_delvis_inom_samma_grupp():
    delvis = _traff("x", "delvis", 2015, True)
    inom = _traff("y", "inom", 2016, True)

    resultat = rangordna_traffar([delvis, inom])

    assert [t["byggnad_id"] for t in resultat] == ["y", "x"]


def test_rangordna_traffar_byggnad_id_stigande_vid_fullstandig_likhet():
    t1 = _traff("bal_byggnad_yta.9", "inom", 2015, True)
    t2 = _traff("bal_byggnad_yta.10", "inom", 2016, True)

    resultat = rangordna_traffar([t1, t2])

    # Plain string comparison, as specified — not numeric.
    assert [t["byggnad_id"] for t in resultat] == sorted(
        ["bal_byggnad_yta.9", "bal_byggnad_yta.10"]
    )


def test_rangordna_traffar_ar_ren_paverkar_inte_indata():
    original = [_traff("a", "inom", 2015, True)]
    kopia = [dict(t) for t in original]

    rangordna_traffar(original)

    assert original == kopia
    assert "rang" not in original[0]


# --- fall7_geometri ----------------------------------------------------------------

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
        },
        {
            "type": "Feature",
            "id": "bal_byggnad_yta.20",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[30, 30], [40, 30], [40, 40], [30, 40], [30, 30]]],
            },
            "properties": {"bal_nybyggnadsar": None},
        },
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
    raise RuntimeError("simulated broken layer")


def test_fall7_geometri_returnerar_geojson_med_alla_traffar_och_rang():
    resultat = fall7_geometri(
        ows_url=OWS, punkt=(15.0, 15.0), nu="2026-08-19T10:00:00Z",
        radie_m=100.0, hamta_wfs=_fejk_wfs,
    )

    assert resultat["type"] == "FeatureCollection"
    assert resultat["vald_byggnad_id"] == "bal_byggnad_yta.10"
    assert resultat["antal_traffar"] == 2
    assert len(resultat["features"]) == 2

    for feature in resultat["features"]:
        assert feature["type"] == "Feature"
        assert feature["geometry"]["type"] == "Polygon"
        props = feature["properties"]
        assert set(props) == {
            "byggnad_id", "laege", "byggnads_ar", "gallde_vid_uppforande",
            "dispens_kravs_idag", "preskriberas", "har_atgarder", "rang",
        }

    ranger = sorted(f["properties"]["rang"] for f in resultat["features"])
    assert ranger == [1, 2]
    # byggnad .10 uppfördes 2014, inom zonen -> gällde vid uppförande = group
    # (a); .20 saknar byggnadsår -> group (b). (a) outranks (b).
    forst = next(f for f in resultat["features"] if f["properties"]["rang"] == 1)
    assert forst["properties"]["byggnad_id"] == "bal_byggnad_yta.10"


def test_fall7_geometri_ingen_byggnad_i_radien_ger_valueerror():
    tomt = {"type": "FeatureCollection", "features": []}

    def _fejk_wfs_tom(wfs_url, type_name, bbox=None, max_features=100):
        if type_name == "SundsvallsKommun:bal_byggnad_yta":
            return tomt
        return _fejk_wfs(wfs_url, type_name, bbox, max_features)

    with pytest.raises(ValueError, match="[Ii]ngen byggnad"):
        fall7_geometri(
            ows_url=OWS, punkt=(15.0, 15.0), nu="2026-08-19T10:00:00Z",
            radie_m=100.0, hamta_wfs=_fejk_wfs_tom,
        )

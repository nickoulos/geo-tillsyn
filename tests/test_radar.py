"""Tillsynsradar: skanna en zon -> rangordnade kandidater (injicerad hämtare, inget nät).

SPDX-License-Identifier: AGPL-3.0-or-later
"""

import pytest

from geo_tillsyn.meddelanden import Meddelande
from geo_tillsyn.radar import MAX_ZON_AREA_M2, skanna_zon

OWS = "http://example.test/ows"
NU = "2026-08-19T10:00:00Z"
BBOX = (0.0, 0.0, 200.0, 200.0)


def _kvadrat(x, y, s=10):
    return {
        "type": "Polygon",
        "coordinates": [[[x, y], [x + s, y], [x + s, y + s], [x, y + s], [x, y]]],
    }


def _byggnad(bid, x, y, ar, s=10):
    return {
        "type": "Feature",
        "id": bid,
        "geometry": _kvadrat(x, y, s),
        "properties": {"bal_nybyggnadsar": ar},
    }


# Zonen täcker x in [0, 100]: A helt inom (2014), B helt inom men från 1960,
# C delvis (halva), D utanför, E inom utan år.
BYGGNADER = {
    "type": "FeatureCollection",
    "features": [
        _byggnad("bal_byggnad_yta.A", 10, 10, 2014),
        _byggnad("bal_byggnad_yta.B", 30, 10, 1960),
        _byggnad("bal_byggnad_yta.C", 95, 10, 2010),
        _byggnad("bal_byggnad_yta.D", 150, 10, 2014),
        _byggnad("bal_byggnad_yta.E", 50, 50, None),
    ],
}
STRANDSKYDD = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "id": "lm_strandskydd_y.1",
            "geometry": _kvadrat(0, 0, 100),
            "properties": {"lm_aktbeteckning": "AKT-1"},
        }
    ],
}
FASTIGHETER = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "id": "Fastighet_yta.1",
            "geometry": _kvadrat(0, 0, 100),
            "properties": {"FBET": "ALNÖ-TEST 1:1"},
        },
        {
            "type": "Feature",
            "id": "Fastighet_yta.2",
            "geometry": _kvadrat(100, 0, 100),
            "properties": {"FBET": "ALNÖ-TEST 1:2"},
        },
    ],
}
TOM = {"type": "FeatureCollection", "features": []}


def _hamta(ows_url, type_name, bbox=None, max_features=None):
    if type_name.endswith("bal_byggnad_yta"):
        return BYGGNADER
    if type_name.endswith("lm_strandskydd_y"):
        return STRANDSKYDD
    if type_name.endswith("Fastighet_yta"):
        return FASTIGHETER
    return TOM


def test_skanna_zon_rangordnar_kandidater_och_utesluter_utanfor():
    res = skanna_zon(OWS, BBOX, NU, hamta_wfs=_hamta)

    ids = [k["byggnad_id"] for k in res["kandidater"]]
    assert "bal_byggnad_yta.D" not in ids
    assert res["antal_byggnader"] == 5
    assert res["antal_traffar"] == 4
    # A: inom + strandskydd gällde 2014 -> högst. B (1960, före generellt
    # strandskydd) hamnar under E (år okänt) och C (delvis, 2010).
    assert ids[0] == "bal_byggnad_yta.A"
    assert ids[-1] == "bal_byggnad_yta.B"
    poang = [k["poang"] for k in res["kandidater"]]
    assert poang == sorted(poang, reverse=True)
    assert [k["rang"] for k in res["kandidater"]] == [1, 2, 3, 4]


def test_varje_kandidat_bar_grunder_fastighet_och_centroid():
    res = skanna_zon(OWS, BBOX, NU, hamta_wfs=_hamta)

    a = res["kandidater"][0]
    assert a["fastighet"] == "ALNÖ-TEST 1:1"
    assert a["laege"] == "inom"
    assert a["byggnads_ar"] == 2014
    assert a["gallde_vid_uppforande"] is True
    assert a["preskriberas"] is False
    assert 10 <= a["centroid"]["easting"] <= 20
    assert all(isinstance(g, Meddelande) for g in a["grunder"])
    assert a["grunder"]  # poängen förklaras alltid
    # Poängmodellen redovisas öppet, och beslutet är aldrig radarens.
    assert res["poangmodell"]
    assert isinstance(res["juridisk_not"], Meddelande)
    assert "kandidat" in res["juridisk_not"].lower()


def test_kandidat_utan_ar_flaggas_inte_tyst():
    res = skanna_zon(OWS, BBOX, NU, hamta_wfs=_hamta)
    e = next(k for k in res["kandidater"] if k["byggnad_id"] == "bal_byggnad_yta.E")
    assert e["byggnads_ar"] is None
    assert e["gallde_vid_uppforande"] is None
    assert any("ej fastställt" in str(g) or "okänt" in str(g) for g in e["grunder"])


def test_max_kandidater_trunkerar_och_deklarerar():
    res = skanna_zon(OWS, BBOX, NU, hamta_wfs=_hamta, max_kandidater=2)
    assert len(res["kandidater"]) == 2
    assert res["antal_traffar"] == 4
    assert res["kandidater_trunkerade_till"] == 2


def test_fastighetslager_nere_ger_osakerhet_inte_krasch():
    def hamta(ows_url, type_name, bbox=None, max_features=None):
        if type_name.endswith("Fastighet_yta"):
            raise RuntimeError("WFS nere")
        return _hamta(ows_url, type_name, bbox, max_features)

    res = skanna_zon(OWS, BBOX, NU, hamta_wfs=hamta)
    assert all(k["fastighet"] is None for k in res["kandidater"])
    assert any("Fastighet_yta" in str(o) for o in res["osakerheter"])


def test_for_stor_zon_avvisas():
    sida = (MAX_ZON_AREA_M2**0.5) + 100
    with pytest.raises(ValueError):
        skanna_zon(OWS, (0.0, 0.0, sida, sida), NU, hamta_wfs=_hamta)


def test_kallor_pekar_pa_wfs_och_lag():
    res = skanna_zon(OWS, BBOX, NU, hamta_wfs=_hamta)
    urls = " ".join(k["url"] for k in res["kallor"])
    assert "bal_byggnad_yta" in urls
    assert "lm_strandskydd_y" in urls
    assert "980808" in urls

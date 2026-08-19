"""Tests for geodata.py — snapshot → live → stale cache, alltid deklarerat.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

from __future__ import annotations

import json

import pytest

from geo_tillsyn import geodata

OWS = "https://example.test/geoserver/ows"
LAGER = "SundsvallsKommun:lm_strandskydd_y"


def _ruta(x0, y0, x1, y1, **props):
    return {
        "type": "Feature",
        "id": f"f.{x0}",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]],
        },
        "properties": props,
    }


def _fc(*features):
    return {"type": "FeatureCollection", "features": list(features)}


def _bytes(obj) -> bytes:
    return json.dumps(obj).encode("utf-8")


def test_getfeature_url_bar_bbox_crs_count_och_srsname():
    url = geodata.getfeature_url(OWS, LAGER, (1.0, 2.0, 3.0, 4.0), 50)
    assert "typeNames=SundsvallsKommun%3Alm_strandskydd_y" in url
    assert "bbox=1.0%2C2.0%2C3.0%2C4.0%2CEPSG%3A3014" in url
    assert "count=50" in url and "srsName=EPSG%3A3014" in url


def test_live_svar_cachas_och_markeras_live(tmp_path):
    anrop = []

    def hamta(url, timeout):
        anrop.append(url)
        return _bytes(_fc(_ruta(0, 0, 10, 10)))

    fc = geodata.hamta_wfs_robust(
        OWS, LAGER, bbox=(0, 0, 5, 5), max_features=10,
        snapshot_katalog=tmp_path / "snap", cache_katalog=tmp_path / "cache", hamta=hamta,
    )
    assert len(fc["features"]) == 1
    assert geodata.kalla_typ(fc) == ("live", fc["geo_tillsyn_kalla"]["hamtad"])
    assert len(anrop) == 1 and "GetCapabilities" not in anrop[0]
    assert list((tmp_path / "cache").glob("*.json"))


def test_live_fel_faller_tillbaka_pa_stale_cache_och_deklarerar_det(tmp_path):
    svar = [_bytes(_fc(_ruta(0, 0, 10, 10)))]

    def hamta(url, timeout):
        if svar:
            return svar.pop()
        raise TimeoutError("timed out")

    kw = dict(snapshot_katalog=tmp_path / "snap", cache_katalog=tmp_path / "cache", hamta=hamta)
    forst = geodata.hamta_wfs_robust(OWS, LAGER, bbox=(0, 0, 5, 5), **kw)
    andra = geodata.hamta_wfs_robust(OWS, LAGER, bbox=(0, 0, 5, 5), **kw)
    assert geodata.kalla_typ(andra) == ("cache", forst["geo_tillsyn_kalla"]["hamtad"])
    assert andra["features"] == forst["features"]


def test_shapefile_fel_fran_geoserver_ar_ett_fel_inte_tom_lista(tmp_path):
    """GeoServer svarar 200 + XML vid det rapporterade shapefile-felet — får inte tolkas som 0 träffar."""

    def hamta(url, timeout):
        return b"<ows:ExceptionReport>Error occurred getting features ... not one of the files types</ows:ExceptionReport>"

    with pytest.raises(geodata.GeodataFel):
        geodata.hamta_wfs_robust(
            OWS, LAGER, bbox=(0, 0, 5, 5),
            snapshot_katalog=tmp_path / "snap", cache_katalog=tmp_path / "cache", hamta=hamta,
        )


def test_snapshot_besvarar_bbox_lokalt_utan_natverk(tmp_path):
    hela = _fc(_ruta(0, 0, 10, 10, lm_aktbeteckning="A"), _ruta(100, 100, 110, 110, lm_aktbeteckning="B"))
    snap = tmp_path / "snap"
    geodata.spara_snapshot(OWS, LAGER, katalog=snap, hamta=lambda url, timeout: _bytes(hela))

    def hamta_aldrig(url, timeout):
        raise AssertionError("nätverket ska inte röras när ögonblicksbild finns")

    fc = geodata.hamta_wfs_robust(
        OWS, LAGER, bbox=(5, 5, 20, 20), max_features=100,
        snapshot_katalog=snap, cache_katalog=tmp_path / "cache", hamta=hamta_aldrig,
    )
    assert [f["properties"]["lm_aktbeteckning"] for f in fc["features"]] == ["A"]
    typ, hamtad = geodata.kalla_typ(fc)
    assert typ == "snapshot" and hamtad


def test_offline_utan_cache_ar_ett_arligt_fel(tmp_path):
    with pytest.raises(geodata.GeodataFel):
        geodata.hamta_wfs_robust(
            OWS, "X:y", bbox=(0, 0, 1, 1),
            snapshot_katalog=tmp_path / "snap", cache_katalog=tmp_path / "cache",
            hamta=lambda u, t: b"{}", offline=True,
        )


def test_kalla_typ_for_frammande_svar_ar_live_utan_datum():
    assert geodata.kalla_typ({"type": "FeatureCollection", "features": []}) == ("live", None)


# --- WMS-bildcache (ortofoto-tidslinjen) ---------------------------------------


def test_wms_cache_first_for_immutabla_ortofoton(tmp_path):
    """Historiska årgångar ändras aldrig — andra hämtningen går aldrig på nätet."""
    anrop = []

    def hamta(wms_url, layer, bbox, crs, width, height):
        anrop.append(layer)
        return b"P" * 30_000

    kw = dict(
        wms_url="http://example.test/ows", layer="Lantmateriet:Orto2015_wms",
        bbox=(1.0, 2.0, 3.0, 4.0), crs="EPSG:3014", width=512, height=512,
        hamta=hamta, katalog=tmp_path, offline=False,
    )
    forsta = geodata.hamta_wms_robust(**kw)
    andra = geodata.hamta_wms_robust(**kw)

    assert forsta == andra == b"P" * 30_000
    assert anrop == ["Lantmateriet:Orto2015_wms"]  # exakt ett nätanrop


def test_misstankt_tom_wms_bild_cachas_aldrig(tmp_path):
    """En nästan tom PNG är WMS:ens tysta felläge — den får inte förgifta cachen."""
    svar = [b"x" * 5_000, b"P" * 30_000]

    def hamta(wms_url, layer, bbox, crs, width, height):
        return svar.pop(0)

    kw = dict(
        wms_url="http://example.test/ows", layer="Lantmateriet:Orto2015_wms",
        bbox=(1.0, 2.0, 3.0, 4.0), crs="EPSG:3014", width=512, height=512,
        hamta=hamta, katalog=tmp_path, offline=False,
    )
    assert geodata.hamta_wms_robust(**kw) == b"x" * 5_000
    assert geodata.hamta_wms_robust(**kw) == b"P" * 30_000  # hämtar om, tar det riktiga


def test_wms_offline_utan_cache_ar_ett_arligt_fel(tmp_path):
    with pytest.raises(geodata.GeodataFel):
        geodata.hamta_wms_robust(
            wms_url="http://example.test/ows", layer="Lantmateriet:Orto2015_wms",
            bbox=(1.0, 2.0, 3.0, 4.0), crs="EPSG:3014", width=512, height=512,
            hamta=lambda *a, **k: (_ for _ in ()).throw(AssertionError("nät i offline")),
            katalog=tmp_path, offline=True,
        )


def test_wms_cache_nyckeln_skiljer_pa_bbox(tmp_path):
    def hamta(wms_url, layer, bbox, crs, width, height):
        return f"bbox={bbox}".encode() + b"0" * 30_000

    kw = dict(
        wms_url="http://example.test/ows", layer="Lantmateriet:Orto2015_wms",
        crs="EPSG:3014", width=512, height=512, hamta=hamta, katalog=tmp_path, offline=False,
    )
    a = geodata.hamta_wms_robust(bbox=(1.0, 2.0, 3.0, 4.0), **kw)
    b = geodata.hamta_wms_robust(bbox=(5.0, 6.0, 7.0, 8.0), **kw)
    assert a != b

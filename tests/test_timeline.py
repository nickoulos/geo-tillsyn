"""Unit tests for the ortofoto tidslinje fetcher.

Hermetic: the WMS fetch function is injected, no network.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

from geo_tillsyn.timeline import ORTOFOTO_LAYERS, hamta_tidslinje

WMS_URL = "http://example.test/ows"
BBOX = (158000.0, 6925000.0, 159000.0, 6926000.0)

STOR_PNG = b"\x89PNG" + b"x" * 200_000
LITEN_PNG = b"\x89PNG" + b"x" * 3_000


def test_alla_18_verifierade_ar_finns():
    assert len(ORTOFOTO_LAYERS) == 18
    assert ORTOFOTO_LAYERS[1960] == "Lantmateriet:HistoriskaOrtofoton1960_wms"
    assert ORTOFOTO_LAYERS[2002] == "Lantmateriet:HistoriskaOrtofoton2002_wms"
    assert ORTOFOTO_LAYERS[2007] == "Lantmateriet:Orto2007_wms"
    assert ORTOFOTO_LAYERS[2023] == "Lantmateriet:Orto2023_wms"


def test_hamtar_valda_ar_i_stigande_ordning():
    anropade_lager = []

    def fejk_hamta(wms_url, layer, bbox, crs, width, height):
        anropade_lager.append(layer)
        return STOR_PNG

    bilder = hamta_tidslinje(
        WMS_URL, BBOX, ar=[2023, 1960, 2007], crs="EPSG:3014", hamta=fejk_hamta
    )

    assert [b.ar for b in bilder] == [1960, 2007, 2023]
    assert anropade_lager == [
        "Lantmateriet:HistoriskaOrtofoton1960_wms",
        "Lantmateriet:Orto2007_wms",
        "Lantmateriet:Orto2023_wms",
    ]
    assert all(b.png == STOR_PNG for b in bilder)


def test_liten_bild_flaggas_misstankt_tom():
    def fejk_hamta(wms_url, layer, bbox, crs, width, height):
        return LITEN_PNG if layer.endswith("1960_wms") else STOR_PNG

    bilder = hamta_tidslinje(WMS_URL, BBOX, ar=[1960, 2023], hamta=fejk_hamta)

    per_ar = {b.ar: b for b in bilder}
    assert per_ar[1960].misstankt_tom is True
    assert per_ar[2023].misstankt_tom is False


def test_standard_ar_alla_18():
    def fejk_hamta(wms_url, layer, bbox, crs, width, height):
        return STOR_PNG

    bilder = hamta_tidslinje(WMS_URL, BBOX, hamta=fejk_hamta)

    assert len(bilder) == 18
    assert bilder[0].ar == 1960
    assert bilder[-1].ar == 2023

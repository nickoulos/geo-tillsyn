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


# --- kompletterande regellager (utvidgat/upphävt) + källförbehåll -------------

UPPHAVT = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "id": "UpphavdaStrandskydd_yta.7",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[12, 12], [18, 12], [18, 18], [12, 18], [12, 12]]],
            },
            "properties": {"Diarienumm": "521-1234-2019", "Beslutsdat": "2019-05-02"},
        }
    ],
}
UTVIDGAT = {"type": "FeatureCollection", "features": []}


def _fejk_wfs_med_regellager(wfs_url, type_name, bbox=None, max_features=100):
    if type_name == "Lansstyrelsen:UpphavdaStrandskydd_yta":
        return UPPHAVT
    if type_name == "Lansstyrelsen:UtvidgatStrandskydd_yta":
        return UTVIDGAT
    if type_name == "SundsvallsKommun:lm_strandskydd_y":
        # Som om svaret kom ur geodata.py:s ögonblicksbild — måste deklareras.
        return {**STRANDSKYDD, "geo_tillsyn_kalla": {"typ": "snapshot", "hamtad": "2026-08-19T08:00:00Z"}}
    return _fejk_wfs(wfs_url, type_name, bbox, max_features)


def test_upphavt_strandskydd_blir_fakta_och_synlig_kallkonflikt(tmp_path):
    resultat = kor_fall7(
        ows_url=OWS, punkt=(15.0, 15.0), radie_m=100.0, ut_katalog=tmp_path,
        nu="2026-08-19T10:00:00Z", ar=[2023],
        hamta_wfs=_fejk_wfs_med_regellager, hamta_wms=_fejk_wms,
    )
    md = resultat.read_text(encoding="utf-8")
    # Fakta med egen källa (Länsstyrelsens lager), och konflikten som Ej fastställt.
    assert "berör även område med upphävt strandskydd (521-1234-2019 (2019-05-02))" in md
    assert "UpphavdaStrandskydd_yta (WFS)" in md
    assert "Ej fastställt:** Byggnad bal_byggnad_yta.10 berör även område med upphävt" in md
    # Ögonblicksbilden deklareras — aldrig tyst.
    assert "lokal ögonblicksbild från 2026-08-19T08:00:00Z" in md


def test_analysera_punkt_bar_komplement_och_forbehall():
    from geo_tillsyn.runner import analysera_punkt

    res = analysera_punkt(
        ows_url=OWS, punkt=(15.0, 15.0), radie_m=100.0,
        nu="2026-08-19T10:00:00Z", hamta_wfs=_fejk_wfs_med_regellager,
    )
    traff = res["traffar"][0]
    assert traff["upphavt_strandskydd"] == ["521-1234-2019 (2019-05-02)"]
    assert "utvidgat_strandskydd" not in traff
    koder = [getattr(o, "kod", None) for o in res["osakerheter"]]
    assert "runner.upphavt_strandskydd_konflikt" in koder
    assert "geodata.snapshot_anvant" in koder
    assert "runner.regellager_otillgangligt" not in koder


# --- vald_byggnad_id + vald träff först i traffar (fastighetsbiografi) -----------

BYGGNADER_TVA = {
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
            "properties": {"bal_nybyggnadsar": 1990},
        },
    ],
}


def _fejk_wfs_tva_byggnader(wfs_url, type_name, bbox=None, max_features=100):
    if type_name == "SundsvallsKommun:bal_byggnad_yta":
        return BYGGNADER_TVA
    return _fejk_wfs(wfs_url, type_name, bbox, max_features)


def test_analysera_punkt_flyttar_vald_traff_forst_utan_att_andra_antal_traffar():
    from geo_tillsyn.runner import analysera_punkt

    # Punkt inuti byggnad .20 -> _valj_byggnad väljer den, trots att den ligger
    # sist i WFS-svaret (byggnad .10 kommer först i input-ordning).
    res = analysera_punkt(
        ows_url=OWS, punkt=(35.0, 35.0), radie_m=100.0,
        nu="2026-08-19T10:00:00Z", hamta_wfs=_fejk_wfs_tva_byggnader,
    )

    assert res["vald_byggnad_id"] == "bal_byggnad_yta.20"
    assert [t["byggnad_id"] for t in res["traffar"]] == [
        "bal_byggnad_yta.20", "bal_byggnad_yta.10",
    ]
    assert res["antal_traffar"] == 2  # oförändrat av omordningen


def test_analysera_punkt_utan_byggnader_ger_vald_byggnad_id_none_och_kraschar_inte():
    from geo_tillsyn.runner import analysera_punkt

    tomt = {"type": "FeatureCollection", "features": []}

    def _fejk_wfs_tom(wfs_url, type_name, bbox=None, max_features=100):
        if type_name == "SundsvallsKommun:bal_byggnad_yta":
            return tomt
        return _fejk_wfs(wfs_url, type_name, bbox, max_features)

    res = analysera_punkt(
        ows_url=OWS, punkt=(15.0, 15.0), radie_m=100.0,
        nu="2026-08-19T10:00:00Z", hamta_wfs=_fejk_wfs_tom,
    )

    assert res["vald_byggnad_id"] is None
    assert res["traffar"] == []
    assert res["antal_traffar"] == 0


# --- Rättigheter/servitut i Fall 7 (anbudssvar 151260 7d) -------------------------

_RATTIGHET_Y = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature", "id": "rk_rattighet_y.7",
            "geometry": {"type": "Polygon", "coordinates": [[[15, 5], [25, 5], [25, 25], [15, 25], [15, 5]]]},
            "properties": {"Typ": "Officialservitut", "AKTBET": "2281-91/12", "RANDAMAL": "VÄG", "FASTIGHET": "ALNÖ-USLAND 1:45"},
        },
        {
            "type": "Feature", "id": "rk_rattighet_y.8",
            "geometry": {"type": "Polygon", "coordinates": [[[80, 80], [90, 80], [90, 90], [80, 90], [80, 80]]]},
            "properties": {"Typ": "Ledningsrätt", "AKTBET": "LÅNGT-BORT", "RANDAMAL": "EL"},
        },
    ],
}


def _fejk_wfs_med_rattigheter(wfs_url, type_name, bbox=None, max_features=100):
    if type_name == "Lantmateriet:rk_rattighet_y":
        return _RATTIGHET_Y
    if type_name in ("Lantmateriet:rk_rattighet_l", "Lantmateriet:rk_ga_y", "Lantmateriet:rk_ga_l"):
        return {"type": "FeatureCollection", "features": []}
    return _fejk_wfs(wfs_url, type_name, bbox, max_features)


def test_fall7_rattigheter_som_beror_traffbyggnad_blir_fakta_med_kalla(tmp_path):
    resultat = kor_fall7(
        ows_url=OWS, punkt=(15.0, 15.0), radie_m=100.0, ut_katalog=tmp_path,
        nu="2026-08-19T10:00:00Z", ar=[2023],
        hamta_wfs=_fejk_wfs_med_rattigheter, hamta_wms=_fejk_wms,
    )
    md = resultat.read_text(encoding="utf-8")
    assert "Byggnad bal_byggnad_yta.10 berör officialservitut 2281-91/12 (VÄG) på ALNÖ-USLAND 1:45." in md
    assert "Lantmateriet:rk_rattighet_y (WFS)" in md
    assert "LÅNGT-BORT" not in md  # rör inte byggnaden


def test_analysera_punkt_bar_rattigheter_per_traff_och_deklarerar_otillgangliga_lager():
    from geo_tillsyn.runner import analysera_punkt

    res = analysera_punkt(
        ows_url=OWS, punkt=(15.0, 15.0), radie_m=100.0,
        nu="2026-08-19T10:00:00Z", hamta_wfs=_fejk_wfs_med_rattigheter,
    )
    (traff,) = res["traffar"]
    assert traff["rattigheter"] == [
        {"typ": "Officialservitut", "aktbeteckning": "2281-91/12", "andamal": "VÄG", "lager": "Lantmateriet:rk_rattighet_y"}
    ]
    assert any(k["beskrivning"] == "Lantmateriet:rk_rattighet_y (WFS)" for k in res["kallor"])

    # Lagren nere (grund-_fejk_wfs kastar) -> deklarerat, inte tyst, och ingen nyckel 'rattigheter'.
    trasigt = analysera_punkt(
        ows_url=OWS, punkt=(15.0, 15.0), radie_m=100.0,
        nu="2026-08-19T10:00:00Z", hamta_wfs=_fejk_wfs,
    )
    assert "rattigheter" not in trasigt["traffar"][0]
    koder = [getattr(o, "kod", None) for o in trasigt["osakerheter"]]
    assert koder.count("runner.rattighetslager_otillgangligt") == 4

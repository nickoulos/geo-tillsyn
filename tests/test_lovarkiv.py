"""Unit tests for the mock-ByggR lovarkiv (Fall 3).

SPDX-License-Identifier: AGPL-3.0-or-later
"""

import json

import pytest

from geo_tillsyn.lovarkiv import hitta_lov


def _lov_record(dnr="SBN 2009-0412", fastighet="ALNÖ-USLAND 1:45", koords=None, **extra):
    koords = koords or [[100.0, 100.0], [110.0, 100.0], [110.0, 108.0], [100.0, 108.0]]
    record = {
        "syntetisk": True,
        "anmarkning": "Syntetiskt testärende — inga verkliga byggärenden.",
        "dnr": dnr,
        "fastighet": fastighet,
        "beslutsdatum": "2009-06-19",
        "laga_kraft": "2009-07-24",
        "atgard": "Nybyggnad av enbostadshus",
        "byggnadsarea_m2": 80.0,
        "hojd_m": None,
        "godkant_lage": {"crs": "EPSG:3014", "koordinater": koords},
        "villkor": ["Byggnaden placeras minst 4,5 m från fastighetsgräns."],
        "handling": None,
    }
    record.update(extra)
    return record


def _skriv(katalog, namn, record):
    katalog.mkdir(parents=True, exist_ok=True)
    (katalog / namn).write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")


def test_hittar_lov_via_punkt_inom_avstand(tmp_path):
    _skriv(tmp_path, "a.json", _lov_record())

    lov = hitta_lov(tmp_path, punkt=(105.0, 104.0))

    assert lov is not None
    assert lov.dnr == "SBN 2009-0412"
    assert lov.godkant_lage.area == pytest.approx(80.0)
    assert lov.kalla_fil == tmp_path / "a.json"


def test_punkt_langt_bort_ger_none(tmp_path):
    _skriv(tmp_path, "a.json", _lov_record())

    assert hitta_lov(tmp_path, punkt=(5000.0, 5000.0)) is None


def test_hittar_via_fastighetsbeteckning(tmp_path):
    _skriv(tmp_path, "a.json", _lov_record())

    lov = hitta_lov(tmp_path, fastighet="ALNÖ-USLAND 1:45")

    assert lov is not None and lov.fastighet == "ALNÖ-USLAND 1:45"


def test_narmaste_valjs_vid_flera_traffar(tmp_path):
    _skriv(tmp_path, "nara.json", _lov_record(dnr="SBN 2009-0001"))
    fjarran = [[160.0, 100.0], [170.0, 100.0], [170.0, 108.0], [160.0, 108.0]]
    _skriv(tmp_path, "fjarran.json", _lov_record(dnr="SBN 2009-0002", koords=fjarran))

    lov = hitta_lov(tmp_path, punkt=(105.0, 104.0))

    assert lov.dnr == "SBN 2009-0001"


def test_record_utan_syntetisk_flagga_avvisas(tmp_path):
    record = _lov_record()
    del record["syntetisk"]
    _skriv(tmp_path, "a.json", record)

    with pytest.raises(ValueError, match="syntetisk"):
        hitta_lov(tmp_path, punkt=(105.0, 104.0))


def test_tom_katalog_ger_none(tmp_path):
    assert hitta_lov(tmp_path, punkt=(0.0, 0.0)) is None


def test_fel_crs_avvisas_med_epsg_i_felmeddelandet(tmp_path):
    record = _lov_record()
    record["godkant_lage"]["crs"] = "EPSG:3006"
    _skriv(tmp_path, "a.json", record)

    with pytest.raises(ValueError, match="3006"):
        hitta_lov(tmp_path, punkt=(105.0, 104.0))


# --- ByggR-kompatibel yta (ArendeExportWS, kommunens mejl 2026-08-19) -----------

from geo_tillsyn.lovarkiv import (  # noqa: E402
    dela_fastighetsbeteckning,
    get_document,
    hamta_arenden_by_fastighet,
)


def test_dela_fastighetsbeteckning_i_trakt_och_nummer():
    assert dela_fastighetsbeteckning("ALNÖ-USLAND 1:45") == ("ALNÖ-USLAND", "1:45")
    assert dela_fastighetsbeteckning("SUNDSVALL NORRMALM 2:1") == ("SUNDSVALL NORRMALM", "2:1")
    assert dela_fastighetsbeteckning("  Alnö-Usland   1:45 ") == ("ALNÖ-USLAND", "1:45")


def test_dela_fastighetsbeteckning_utan_nummer_ger_fel():
    with pytest.raises(ValueError, match="registernummer"):
        dela_fastighetsbeteckning("ALNÖ-USLAND")


def test_arenden_by_fastighet_har_tekis_falt(tmp_path):
    _skriv(tmp_path, "a.json", _lov_record(handling="a.pdf"))
    (tmp_path / "a.pdf").write_bytes(b"%PDF-1.4 syntetisk")

    arenden = hamta_arenden_by_fastighet(tmp_path, "ALNÖ-USLAND", "1:45")

    assert len(arenden) == 1
    a = arenden[0]
    # Fältnamn enligt TekisProxy.arende (kommunens Get-Member-dump)
    for falt in ("arendeId", "dnr", "diarieprefix", "arendetyp", "arendeslag", "beskrivning",
                 "status", "registreradDatum", "slutDatum", "handelseLista", "objektLista"):
        assert falt in a, falt
    assert a["dnr"] == "SBN 2009-0412"
    assert a["diarieprefix"] == "SBN"
    assert a["arendetyp"] == "Bygglov"
    assert a["beskrivning"] == "Nybyggnad av enbostadshus"
    assert a["slutDatum"] == "2009-06-19"
    assert isinstance(a["arendeId"], int)
    # objektLista pekar på fastigheten med trakt + fBetNr separat, som tjänsten
    (obj,) = a["objektLista"]
    assert obj["trakt"] == "ALNÖ-USLAND" and obj["fBetNr"] == "1:45"
    # handelseLista → handlingLista → handlingId
    handling = a["handelseLista"][0]["handlingLista"][0]
    assert handling["handlingId"]
    assert handling["namn"] == "a.pdf"
    # Mock-markering: aldrig tyst om att detta är syntetiskt
    assert a["_geoTillsynMock"]["syntetisk"] is True
    assert a["_geoTillsynMock"]["laga_kraft"] == "2009-07-24"


def test_arenden_by_fastighet_matchar_skiftlage_och_blanksteg(tmp_path):
    _skriv(tmp_path, "a.json", _lov_record())
    assert hamta_arenden_by_fastighet(tmp_path, "alnö-usland", " 1:45 ") != []


def test_arenden_by_fastighet_annan_fastighet_ger_tom_lista(tmp_path):
    _skriv(tmp_path, "a.json", _lov_record())
    assert hamta_arenden_by_fastighet(tmp_path, "ALNÖ-USLAND", "1:46") == []


def test_arenden_by_fastighet_utan_handling_ger_tom_handelselista(tmp_path):
    _skriv(tmp_path, "a.json", _lov_record(handling=None))
    (a,) = hamta_arenden_by_fastighet(tmp_path, "ALNÖ-USLAND", "1:45")
    assert a["handelseLista"] == []


def test_get_document_returnerar_fil_som_bytes(tmp_path):
    _skriv(tmp_path, "a.json", _lov_record(handling="a.pdf"))
    (tmp_path / "a.pdf").write_bytes(b"%PDF-1.4 syntetisk")
    (a,) = hamta_arenden_by_fastighet(tmp_path, "ALNÖ-USLAND", "1:45")
    handling_id = a["handelseLista"][0]["handlingLista"][0]["handlingId"]

    doc = get_document(tmp_path, handling_id)

    assert doc["namn"] == "a.pdf"
    assert doc["fil"]["filBuffer"] == b"%PDF-1.4 syntetisk"
    assert doc["beskrivning"]


def test_get_document_okant_id_ger_none(tmp_path):
    _skriv(tmp_path, "a.json", _lov_record())
    assert get_document(tmp_path, "finns-inte") is None


def test_get_document_utan_fil_ger_metadata_men_ingen_buffer(tmp_path):
    _skriv(tmp_path, "a.json", _lov_record(handling="a.pdf"))
    (tmp_path / "a.pdf").write_bytes(b"x")
    (a,) = hamta_arenden_by_fastighet(tmp_path, "ALNÖ-USLAND", "1:45")
    handling_id = a["handelseLista"][0]["handlingLista"][0]["handlingId"]

    doc = get_document(tmp_path, handling_id, inkludera_fil=False)

    assert doc["namn"] == "a.pdf" and doc["fil"] is None

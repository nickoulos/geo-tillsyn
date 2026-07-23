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

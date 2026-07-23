"""Unit tests for the OCR lov-tolk + register cross-check (Fall 3).

Hermetic: OCR is injected; the PDF is built with handling.py so the
pypdfium2 rasterization path runs for real (pure-python wheel, no binary).

SPDX-License-Identifier: AGPL-3.0-or-later
"""

import json
from pathlib import Path

import pytest

from geo_tillsyn.handling import VATTENMARKE, rita_situationsplan, till_pdf_bytes
from geo_tillsyn.lovarkiv import hitta_lov
from geo_tillsyn.lovtolk import korsjamfor, tolka_handling

OCR_TEXT = """SUNDSVALLS KOMMUN
STADSBYGGNADSKONTORET — SITUATIONSPLAN
DNR: SBN 2009-0412
BESLUTSDATUM: 2009-06-19
BYGGNADSAREA: 80,0 m2
AVSTAND TILL GRANS: 4,5 m
BEVILJAS
"""


def _pdf() -> bytes:
    falt = {
        "DNR": "SBN 2009-0412",
        "BESLUTSDATUM": "2009-06-19",
        "BYGGNADSAREA": "80,0 m2",
        "AVSTAND TILL GRANS": "4,5 m",
    }
    kontur = [(0.0, 0.0), (10.0, 0.0), (10.0, 8.0), (0.0, 8.0)]
    return till_pdf_bytes(rita_situationsplan(falt, kontur, VATTENMARKE))


def _fake_ocr(_bild):
    return OCR_TEXT, 0.93


def test_extraherar_falt_ur_ocr_text():
    tolkat = tolka_handling(_pdf(), ocr=_fake_ocr)

    assert tolkat.tillganglig
    assert tolkat.falt["dnr"].varde == "SBN 2009-0412"
    assert tolkat.falt["beslutsdatum"].varde == "2009-06-19"
    assert tolkat.falt["byggnadsarea_m2"].varde == "80.0"
    assert tolkat.falt["avstand_grans_m"].varde == "4.5"
    assert tolkat.falt["dnr"].konfidens == pytest.approx(0.93)


def test_saknad_ocr_motor_ger_otillganglig_med_anmarkning():
    def trasig_ocr(_bild):
        raise RuntimeError("tesseract is not installed")

    tolkat = tolka_handling(_pdf(), ocr=trasig_ocr)

    assert not tolkat.tillganglig
    assert tolkat.falt == {}
    assert any("OCR ej tillgänglig" in a for a in tolkat.anmarkningar)


def test_korrupt_pdf_ger_otillganglig_utan_krasch():
    tolkat = tolka_handling(b"inte en pdf", ocr=_fake_ocr)

    assert tolkat.tillganglig is False
    assert any("OCR ej tillgänglig" in a for a in tolkat.anmarkningar)


def test_lag_konfidens_flaggas():
    def osaker_ocr(_bild):
        return OCR_TEXT, 0.31

    tolkat = tolka_handling(_pdf(), ocr=osaker_ocr)

    assert tolkat.tillganglig
    assert any("konfidens" in a.lower() for a in tolkat.anmarkningar)


def _lov(tmp_path: Path, **extra):
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
            "koordinater": [[0.0, 0.0], [10.0, 0.0], [10.0, 8.0], [0.0, 8.0]],
        },
        "villkor": [],
        "handling": None,
    }
    record.update(extra)
    (tmp_path / "a.json").write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    return hitta_lov(tmp_path, fastighet="ALNÖ-USLAND 1:45")


def test_korsjamforelse_overens(tmp_path):
    tolkat = tolka_handling(_pdf(), ocr=_fake_ocr)

    resultat = korsjamfor(tolkat, _lov(tmp_path))

    assert resultat == {"dnr": "överens", "beslutsdatum": "överens", "byggnadsarea_m2": "överens"}


def test_korsjamforelse_avvikande_register(tmp_path):
    tolkat = tolka_handling(_pdf(), ocr=_fake_ocr)

    resultat = korsjamfor(tolkat, _lov(tmp_path, byggnadsarea_m2=95.0))

    assert resultat["byggnadsarea_m2"] == "avviker"


def test_korsjamforelse_saknat_falt(tmp_path):
    def ocr_utan_area(_bild):
        text = OCR_TEXT.replace("BYGGNADSAREA: 80,0 m2\n", "")
        return text, 0.9

    tolkat = tolka_handling(_pdf(), ocr=ocr_utan_area)

    resultat = korsjamfor(tolkat, _lov(tmp_path))

    assert resultat["byggnadsarea_m2"] == "saknas"

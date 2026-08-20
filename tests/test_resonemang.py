"""Resonemang: den juridiska kedjan som explicit, granskningsbar nodlista.

Regelgraf-tanken (regelgraf/README, "ingen svart låda") i tunn form: varje
fall exponerar sina steg — fråga, lagrum, svar — härledda ur redan beräknade
fält. Ingen nod räknar något nytt; kedjan slutar alltid i handläggarens beslut.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

from geo_tillsyn.meddelanden import Meddelande
from geo_tillsyn.resonemang import resonemang_fall1, resonemang_fall3, resonemang_fall7


def _kontrollera_form(noder):
    assert noder, "kedjan får inte vara tom"
    for nod in noder:
        assert isinstance(nod["fraga"], Meddelande)
        assert isinstance(nod["lagrum"], str) and nod["lagrum"]
        assert "svar" in nod
    # Sista noden är alltid beslutet, och dess svar är alltid handläggarens.
    assert noder[-1]["fraga"].kod == "resonemang.beslut"
    assert noder[-1]["svar"] is None


def test_fall7_kedjan_foljer_utfallet():
    traff = {
        "laege": "inom",
        "gallde_vid_uppforande": True,
        "dispens_kravs_idag": True,
        "preskriberas": False,
    }
    noder = resonemang_fall7(traff)
    _kontrollera_form(noder)
    koder = [n["fraga"].kod for n in noder]
    assert koder == [
        "resonemang.f7_inom_zon",
        "resonemang.f7_gallde_vid_uppforande",
        "resonemang.f7_dispens_idag",
        "resonemang.f7_preskription",
        "resonemang.beslut",
    ]
    assert noder[0]["svar"] == "inom"
    assert noder[1]["svar"] is True
    assert noder[3]["svar"] is False
    assert "MÖD 2021:6" in noder[3]["lagrum"]


def test_fall7_okant_ar_ger_ej_faststallt_inte_gissning():
    noder = resonemang_fall7(
        {"laege": "delvis", "gallde_vid_uppforande": None,
         "dispens_kravs_idag": True, "preskriberas": False}
    )
    assert noder[1]["svar"] is None


def test_fall1_kedjan_bar_datering_register_plikt_och_klockor():
    resultat = {
        "sista_ar_utan": 2001,
        "forsta_ar_med": 2007,
        "bal_nybyggnadsar": 2014,
        "bal_forenligt": False,
        "bygglov_kravdes": True,
        "lovbefrielse": None,
        "rattelse_preskriberad": True,
        "sanktionsavgift_mojlig": False,
    }
    noder = resonemang_fall1(resultat)
    _kontrollera_form(noder)
    koder = [n["fraga"].kod for n in noder]
    assert koder == [
        "resonemang.f1_nar_uppford",
        "resonemang.f1_forenligt_register",
        "resonemang.f1_bygglov_kravdes",
        "resonemang.f1_lovbefrielse",
        "resonemang.f1_klocka_rattelse",
        "resonemang.f1_klocka_sanktion",
        "resonemang.beslut",
    ]
    assert noder[0]["svar"] == "2001–2007"
    assert noder[1]["svar"] is False
    assert noder[4]["svar"] is True


def test_fall1_utan_datering_svarar_ej_faststallt():
    noder = resonemang_fall1(
        {"sista_ar_utan": None, "forsta_ar_med": None, "bal_forenligt": None,
         "bygglov_kravdes": None, "lovbefrielse": None,
         "rattelse_preskriberad": None, "sanktionsavgift_mojlig": None}
    )
    assert noder[0]["svar"] is None


def test_fall3_kedjan_lov_korskontroll_delta_klockor():
    resultat = {
        "lov_hittat": True,
        "dnr": "SBN 2009-0412",
        "pbl_vid_beslut": "ÄPBL (1987:10)",
        "korsjamforelse": {"dnr": "overens", "beslutsdatum": "overens", "byggnadsarea_m2": "overens"},
        "area_diff_m2": 90.3,
        "area_diff_procent": 38.4,
        "rattelse_preskriberad": None,
        "sanktionsavgift_mojlig": None,
    }
    noder = resonemang_fall3(resultat)
    _kontrollera_form(noder)
    koder = [n["fraga"].kod for n in noder]
    assert koder == [
        "resonemang.f3_lov_finns",
        "resonemang.f3_vilken_lag",
        "resonemang.f3_korskontroll",
        "resonemang.f3_avvikelse",
        "resonemang.f3_vasentlighet",
        "resonemang.f3_klockor",
        "resonemang.beslut",
    ]
    assert noder[0]["svar"] is True
    assert noder[1]["svar"] == "ÄPBL (1987:10)"
    assert noder[3]["svar"] == "+90,3 m² (+38,4 %)"
    # Väsentlighet är alltid handläggarens fråga — aldrig ett beräknat svar.
    assert noder[4]["svar"] is None


def test_fall3_utan_lov_ar_en_kort_kedja():
    noder = resonemang_fall3({"lov_hittat": False})
    koder = [n["fraga"].kod for n in noder]
    assert koder == ["resonemang.f3_lov_finns", "resonemang.beslut"]
    assert noder[0]["svar"] is False

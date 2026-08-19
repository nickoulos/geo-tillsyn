"""Tests for the message-code seam between Python and the Origo plugin.

Meddelandekoderna är kontraktet mellan analysmotorn och panelen: backend
skickar `{kod, params}` i stället för färdig svenska, och pluginet renderar
koden på valt språk. Två kataloger som glider isär ger antingen en oöversatt
sträng eller en tom ruta — därför vaktas de här.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from geo_tillsyn.meddelanden import _SV, Meddelande, fran_regelverk, till_json

I18N_MJS = (
    Path(__file__).resolve().parents[1] / "origo-plugin" / "src" / "i18n.mjs"
)


def test_meddelande_ar_sin_svenska_text():
    """En Meddelande ÄR sin svenska sträng — markdown och CLI ser ingen skillnad."""
    m = Meddelande("datering.otydliga_argangar", ar=[2007, 2013, 2019])
    assert isinstance(m, str)
    assert m == (
        "Otydliga årgångar (varken klar närvaro eller frånvaro): "
        "2007, 2013, 2019 — manuell granskning rekommenderas."
    )
    assert m.kod == "datering.otydliga_argangar"
    assert m.params == {"ar": [2007, 2013, 2019]}


def test_okand_kod_ar_ett_fel_inte_en_tyst_tom_strang():
    with pytest.raises(KeyError):
        Meddelande("finns.inte")


def test_till_json_byter_meddelande_mot_kod_och_params():
    data = {
        "osakerheter": [Meddelande("runner.lovarkiv_syntetiskt")],
        "kallor": [{"beskrivning": "Miljöbalken 7 kap. (SFS 1998:808)", "url": "x"}],
        "byggnad_id": "bal_byggnad_yta.26007",
        "area_m2": 325.6,
    }
    assert till_json(data) == {
        "osakerheter": [{"kod": "runner.lovarkiv_syntetiskt", "params": {}}],
        # Författningsnamn och identifierare är ren str och passerar ordagrant.
        "kallor": [{"beskrivning": "Miljöbalken 7 kap. (SFS 1998:808)", "url": "x"}],
        "byggnad_id": "bal_byggnad_yta.26007",
        "area_m2": 325.6,
    }


def test_fran_regelverk_mappar_kand_atgard_men_tappar_aldrig_okand():
    kand = "Ange ärendets startdatum — datum ensamt avgör inte vilken lag som gäller."
    assert isinstance(fran_regelverk(kand), Meddelande)
    assert fran_regelverk(kand).kod == "regelverk.ange_startdatum"

    okand = "En ny åtgärd som regler.json hittat på."
    assert fran_regelverk(okand) == okand
    assert not isinstance(fran_regelverk(okand), Meddelande)


def _koder_i_i18n() -> dict[str, int]:
    """Räkna varje meddelandekod i i18n.mjs — en gång per språk förväntas.

    Meddelandekoder är de enda nycklarna med punkt i sig; fält- och
    värdeetiketterna använder rena identifierare och filtreras därmed bort.
    """
    text = I18N_MJS.read_text(encoding="utf-8")
    antal: dict[str, int] = {}
    for kod in re.findall(r"'([a-z]+\.[a-z0-9_.]+)':", text):
        antal[kod] = antal.get(kod, 0) + 1
    return antal


def test_varje_python_kod_finns_i_i18n_pa_bada_spraken():
    antal = _koder_i_i18n()
    saknas = sorted(k for k in _SV if k not in antal)
    assert not saknas, f"koder utan motsvarighet i i18n.mjs: {saknas}"

    bara_ett_sprak = sorted(k for k in _SV if antal[k] != 2)
    assert not bara_ett_sprak, (
        f"koder som inte finns på exakt två språk i i18n.mjs: {bara_ett_sprak}"
    )


def test_i18n_har_inga_koder_som_backend_inte_kan_skicka():
    """En kod i pluginet utan avsändare i Python är död text — fånga den."""
    overblivna = sorted(k for k in _koder_i_i18n() if k not in _SV)
    assert not overblivna, f"koder i i18n.mjs som saknas i meddelanden.py: {overblivna}"


def test_alla_koder_renderar_pa_svenska():
    """Varje mall går att anropa — en trasig f-sträng får inte gömma sig."""
    params = {
        "datering.argangar_utan_bild": {"ar": [1998, 2002]},
        "datering.for_fa_argangar": {"antal": 2, "minst": 3},
        "datering.argangar_utan_innehall": {"ar": [2012]},
        "datering.otydliga_argangar": {"ar": [2007]},
        "datering.syns_i_aldsta": {"ar": 1960},
        "juridik.byggnadsar_ar_ikrafttradandear": {
            "ar": 1975, "generellt_fran": "1975-07-01"
        },
        "juridik.matningskritisk_areaavvikelse": {"diff_m2": 0.5, "band_m2": 2.0},
        "juridik.matningskritisk_avstand": {"band_m": 0.5},
        "lovtolk.ocr_ej_tillganglig": {"feltyp": "ImportError"},
        "lovtolk.lag_konfidens": {"konfidens": 0.42},
        "runner.regellager_otillgangligt": {"lager": "X:y"},
        "runner.strandskyddslager_otillgangligt": {"lager": "X:y"},
        "runner.granslager_otillgangligt": {"lager": "X:y"},
        "runner.lov_byggnad_koppling_osaker": {"avstand_m": 12.4},
        "runner.ingen_byggnad_hittad": {
            "radie_m": 100.0, "easting": 1.0, "northing": 2.0
        },
        "runner.inget_arende_matchar": {"easting": 1.0, "northing": 2.0},
        "kalla.lovarkiv_syntetiskt": {"dnr": "SBN 2009-0412"},
        "kalla.skannad_handling": {"dnr": "SBN 2009-0412"},
        "server.parametrar_ogiltiga": {"detalj": "'easting'"},
        "runner.upphavt_strandskydd_konflikt": {
            "byggnad_id": "bal_byggnad_yta.1", "referens": "521-1234-2019 (2019-05-02)"
        },
        "runner.rattighetslager_otillgangligt": {"lager": "X:y"},
        "runner.hojd_granska_snedbilder": {"ar": [2018, 2022]},
        "geodata.snapshot_anvant": {"lager": "X:y", "hamtad": "2026-08-19T10:00:00Z"},
        "geodata.cache_anvant": {"lager": "X:y", "hamtad": "2026-08-19T10:00:00Z"},
    }
    for kod in _SV:
        text = Meddelande(kod, **params.get(kod, {}))
        assert text, f"{kod} gav tom text"

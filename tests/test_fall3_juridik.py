"""Unit tests for fall3_lage: which law governs the lov + clocks + bands.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

from datetime import date

from geo_tillsyn.delta import DeltaResultat
from geo_tillsyn.juridik import fall3_lage

BEDOMNING = date(2026, 7, 23)


def _delta(area_diff=14.8, avstand_godkant=6.0, avstand_verklig=3.1):
    return DeltaResultat(
        godkand_area_m2=80.0,
        verklig_area_m2=80.0 + area_diff,
        area_diff_m2=area_diff,
        area_diff_procent=area_diff / 80.0 * 100.0,
        centroid_forskjutning_m=2.4,
        utanfor_godkant_m2=max(area_diff, 0.0),
        avstand_grans_godkant_m=avstand_godkant,
        avstand_grans_verklig_m=avstand_verklig,
    )


def test_lov_fran_2009_styrs_av_apbl_via_overgangsregeln():
    lage = fall3_lage(
        beslutsdatum=date(2009, 6, 19),
        sista_ar_utan=2007,
        forsta_ar_med=2010,
        bedomningsdatum=BEDOMNING,
        delta=_delta(),
    )

    assert lage.overgangsregel_tillampad is True
    assert "ÄPBL" in lage.pbl_vid_beslut
    assert lage.tillsyn_lagrum == "10 kap. ÄPBL"


def test_lov_fran_2015_styrs_av_pbl_2010():
    lage = fall3_lage(
        beslutsdatum=date(2015, 3, 2),
        sista_ar_utan=2013,
        forsta_ar_med=2016,
        bedomningsdatum=BEDOMNING,
        delta=_delta(),
    )

    assert lage.overgangsregel_tillampad is False
    assert "2010:900" in lage.pbl_vid_beslut


def test_klockorna_utvarderas_over_intervallet():
    lage = fall3_lage(
        beslutsdatum=date(2009, 6, 19),
        sista_ar_utan=2009,
        forsta_ar_med=2013,
        bedomningsdatum=BEDOMNING,
        delta=_delta(),
    )

    # senaste = 2013-12-31: +10 yr = 2023 < 2026 -> preskriberad; +5 yr < 2026 -> avgift borta
    assert lage.rattelse_preskriberad is True
    assert lage.sanktionsavgift_mojlig is False


def test_okand_datering_ger_none_och_atgard():
    lage = fall3_lage(
        beslutsdatum=date(2009, 6, 19),
        sista_ar_utan=None,
        forsta_ar_med=None,
        bedomningsdatum=BEDOMNING,
        delta=_delta(),
    )

    assert lage.rattelse_preskriberad is None
    assert lage.sanktionsavgift_mojlig is None
    assert any("datera" in a.lower() for a in lage.atgarder)


def test_liten_areaavvikelse_ar_matningskritisk():
    lage = fall3_lage(
        beslutsdatum=date(2009, 6, 19),
        sista_ar_utan=2007,
        forsta_ar_med=2010,
        bedomningsdatum=BEDOMNING,
        delta=_delta(area_diff=1.5),
    )

    assert any("area" in m.lower() for m in lage.matningskritiska)


def test_litet_avstandsdelta_ar_matningskritiskt():
    lage = fall3_lage(
        beslutsdatum=date(2009, 6, 19),
        sista_ar_utan=2007,
        forsta_ar_med=2010,
        bedomningsdatum=BEDOMNING,
        delta=_delta(avstand_godkant=4.5, avstand_verklig=4.2),
    )

    assert any("avstånd" in m.lower() or "gräns" in m.lower() for m in lage.matningskritiska)


def test_tydliga_avvikelser_ar_inte_matningskritiska():
    lage = fall3_lage(
        beslutsdatum=date(2009, 6, 19),
        sista_ar_utan=2007,
        forsta_ar_med=2010,
        bedomningsdatum=BEDOMNING,
        delta=_delta(),
    )

    assert lage.matningskritiska == []

"""Unit tests for the Fall 1 legal evaluation (olovligt byggande).

Drives the real regelverk_core dataset — hermetic, no network.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

from datetime import date

from geo_tillsyn.juridik import fall1_lage

IDAG = date(2026, 7, 21)


def test_protagonisten_55kvm_2014_bygglov_kravdes_och_pbl_preskriberad():
    # 55.5 m2 komplementbyggnad, ortofoto-interval 2013 -> 2015. No exemption
    # ever covered 55.5 m2, and even the LATEST possible construction year is
    # >10 yrs ago: the PBL rattelse clock has run out, the 5-yr avgift too.
    lage = fall1_lage(
        area_m2=55.5,
        sista_ar_utan=2013,
        forsta_ar_med=2015,
        bedomningsdatum=IDAG,
    )

    assert lage.bygglov_kravdes is True
    assert lage.lovbefrielse is None
    assert lage.rattelse_preskriberad is True
    assert lage.sanktionsavgift_mojlig is False


def test_liten_friggebod_var_lovbefriad():
    # 12 m2 in 2008-2010: friggebod cap was 15 m2 -> no permit needed.
    lage = fall1_lage(
        area_m2=12.0, sista_ar_utan=2007, forsta_ar_med=2010, bedomningsdatum=IDAG
    )

    assert lage.bygglov_kravdes is False
    assert lage.lovbefrielse == "friggebod"


def test_intervall_over_regelandring_ger_inget_avgorande():
    # 12 m2, interval 2006-2010 straddles the 2008 friggebod change (10 -> 15
    # m2): permit verdict depends on the unknown construction year.
    lage = fall1_lage(
        area_m2=12.0, sista_ar_utan=2005, forsta_ar_med=2010, bedomningsdatum=IDAG
    )

    assert lage.bygglov_kravdes is None
    assert any("regeländring" in a.lower() or "avgöra" in a.lower() for a in lage.atgarder)


def test_area_nara_trosklen_ar_matningskritisk():
    # 26 m2 vs the 25 m2 attefall cap: one metre of measurement error flips
    # the verdict -> MEASUREMENT_CRITICAL, the handlaggare must verify.
    lage = fall1_lage(
        area_m2=26.0, sista_ar_utan=2015, forsta_ar_med=2016, bedomningsdatum=IDAG
    )

    assert lage.matningskritiskt is True
    assert any("mät" in a.lower() for a in lage.atgarder)


def test_ny_byggnad_inte_preskriberad_men_avgift_oklar():
    # Interval 2019 -> 2021: rattelse (10 yr) definitely still open; the 5-yr
    # avgift window expires somewhere inside the interval -> undecidable.
    lage = fall1_lage(
        area_m2=55.5, sista_ar_utan=2019, forsta_ar_med=2021, bedomningsdatum=IDAG
    )

    assert lage.rattelse_preskriberad is False
    assert lage.sanktionsavgift_mojlig is None


def test_utan_datering_avgor_vi_ingenting():
    lage = fall1_lage(
        area_m2=55.5, sista_ar_utan=None, forsta_ar_med=None, bedomningsdatum=IDAG
    )

    assert lage.bygglov_kravdes is None
    assert lage.rattelse_preskriberad is None
    assert any("dater" in a.lower() for a in lage.atgarder)


def test_inom_strandskydd_paminner_om_mb_klockan():
    from geo_tillsyn.juridik import _ladda_regelverk_core  # noqa: F401 (same loader)

    lage = fall1_lage(
        area_m2=55.5,
        sista_ar_utan=2013,
        forsta_ar_med=2015,
        bedomningsdatum=IDAG,
        inom_strandskydd=True,
    )

    # PBL preskription never silences the MB side: strandskydd has no clock.
    assert any("MÖD 2021:6" in a for a in lage.atgarder)

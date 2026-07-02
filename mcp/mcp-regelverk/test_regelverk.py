"""Spike D — regelverk_vid(datum, kontext): time-aware legal context.

These tests encode the legal facts the engine must know. The dataset is a
simplified prototype model — flagged for legal review in Sprint 3.
"""

from datetime import date

from regelverk_core import Kontext, regelverk_vid


def befrielse(result, namn):
    """Find an exemption by name in the result, or None."""
    return next((b for b in result["lovbefrielser"] if b["namn"] == namn), None)


def test_apbl_era_2009_friggebod_15_no_attefall():
    """2009: ÄPBL in force; friggebod is 15 m2 (since 2008); attefall doesn't exist."""
    r = regelverk_vid(date(2009, 6, 15))
    assert r["pbl_version"]["sfs"] == "1987:10"
    assert befrielse(r, "friggebod")["max_kvm"] == 15
    assert befrielse(r, "attefallshus") is None


def test_nya_pbl_in_force_from_2011_05_02():
    r_before = regelverk_vid(date(2011, 5, 1))
    r_after = regelverk_vid(date(2011, 5, 2))
    assert r_before["pbl_version"]["sfs"] == "1987:10"
    assert r_after["pbl_version"]["sfs"] == "2010:900"


def test_attefall_boundary_2014_07_02():
    """Attefallshus introduced 2014-07-02 (25 m2) — day-boundary test."""
    assert befrielse(regelverk_vid(date(2014, 6, 30)), "attefallshus") is None
    a = befrielse(regelverk_vid(date(2014, 7, 2)), "attefallshus")
    assert a is not None and a["max_kvm"] == 25


def test_attefall_30_kvm_from_2020():
    assert befrielse(regelverk_vid(date(2021, 1, 1)), "attefallshus")["max_kvm"] == 30


def test_structure_predating_1975_needs_no_strandskydd_dispens():
    """Generellt strandskydd exists since 1975-07-01: what stood before is lawful,
    even if the point lies inside today's zone."""
    r = regelverk_vid(date(1970, 5, 1), Kontext(inom_strandskydd=True))
    assert r["strandskydd"]["gallde_vid_datum"] is False
    assert r["strandskydd"]["dispens_kravs"] is False


def test_attefall_does_not_exempt_from_strandskydd_dispens():
    """The key trap: bygglov exemption (attefall) does NOT exempt from
    strandskydd dispens — both regimes apply independently."""
    r = regelverk_vid(date(2016, 8, 1), Kontext(inom_strandskydd=True))
    assert befrielse(r, "attefallshus") is not None
    assert r["strandskydd"]["dispens_kravs"] is True
    assert r["strandskydd"]["bygglovsbefrielse_ger_inte_dispens"] is True


def test_upphavt_strandskydd_requires_no_dispens():
    r = regelverk_vid(
        date(2016, 8, 1),
        Kontext(inom_strandskydd=True, strandskydd_upphavt=True),
    )
    assert r["strandskydd"]["dispens_kravs"] is False


def test_preskription_pbl_ten_years_but_never_for_strandskydd():
    """PBL rättelseföreläggande barred after 10 years; MB (strandskydd) tillsyn
    has no such limit."""
    old = regelverk_vid(date(2009, 8, 14), bedomningsdatum=date(2026, 7, 2))
    recent = regelverk_vid(date(2020, 1, 1), bedomningsdatum=date(2026, 7, 2))
    assert old["preskription"]["pbl_tioarsregeln_lopt_ut"] is True
    assert recent["preskription"]["pbl_tioarsregeln_lopt_ut"] is False
    assert old["preskription"]["strandskydd_preskriberas"] is False

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


# --- 2025-12-01 reform: friggebod/attefall abolished (SFS 2025:974/975) ---
# See docs/legal-findings.md §2.3. The largest PBL change since 2011, in force
# seven months before submission. Without this the engine reports abolished
# exemptions as current law — the exact error the product promises to prevent.


def test_friggebod_and_attefall_abolished_from_2025_12_01():
    """The terms are gone from 2025-12-01; querying today must not return them."""
    r = regelverk_vid(date(2026, 7, 17))
    assert befrielse(r, "friggebod") is None
    assert befrielse(r, "attefallshus") is None


def test_reform_boundary_2025_12_01():
    """Day-boundary: old regime through 2025-11-30, new regime from 2025-12-01."""
    before = regelverk_vid(date(2025, 11, 30))
    after = regelverk_vid(date(2025, 12, 1))
    assert befrielse(before, "attefallshus")["max_kvm"] == 30
    assert befrielse(after, "attefallshus") is None
    assert befrielse(after, "komplementbostadshus") is not None


def test_new_regime_area_pot_differs_inside_and_outside_detaljplan():
    """Post-reform the exemption is a combined area pot, and it depends on
    whether the point lies inside a detaljplan (45 m2) or outside (65 m2)."""
    inom = regelverk_vid(date(2026, 7, 17), Kontext(inom_detaljplan=True))
    utom = regelverk_vid(date(2026, 7, 17), Kontext(inom_detaljplan=False))
    assert inom["samlad_area_pott"]["max_kvm_totalt"] == 45
    assert utom["samlad_area_pott"]["max_kvm_totalt"] == 65


def test_attefall_rules_still_apply_to_a_2014_structure():
    """The whole point of time-awareness: a 2014 structure is judged by 2014
    rules (25 m2 cap), not by today's regime. Protagonist ALNÖ-USLAND 1:45 is
    55.5 m2 built 2014 — over the then-cap either way."""
    r = regelverk_vid(date(2014, 9, 1))
    assert befrielse(r, "attefallshus")["max_kvm"] == 25
    assert befrielse(r, "komplementbostadshus") is None


# --- Övergångsbestämmelser: "which law applied on date X" is under-specified ---
# See docs/legal-findings.md §4.1. PBL 2010:900's own transitional provision
# keeps the repealed ÄPBL alive for ärenden *started* before 2011-05-02, until
# finally decided. A pure calendar lookup gives the wrong answer.


def test_transitional_warning_near_the_2011_pbl_transition():
    """A date shortly after 2011-05-02 must carry an explicit warning that an
    ärende started earlier is still governed by ÄPBL."""
    r = regelverk_vid(date(2011, 9, 1))
    varning = r["overgangsbestammelser"]
    assert varning["gäller"] is True
    assert "1987:10" in varning["kommentar"]


def test_arende_started_before_2011_is_governed_by_old_law():
    """When the caller knows when the ärende began, the engine must route to the
    law in force then — not the law in force at the measure's date."""
    r = regelverk_vid(date(2011, 9, 1), arende_startdatum=date(2011, 3, 1))
    assert r["pbl_version"]["sfs"] == "1987:10"
    assert r["overgangsbestammelser"]["tillampad_pga_arendestart"] is True


def test_no_transitional_warning_far_from_any_transition():
    r = regelverk_vid(date(2018, 6, 1))
    assert r["overgangsbestammelser"]["gäller"] is False

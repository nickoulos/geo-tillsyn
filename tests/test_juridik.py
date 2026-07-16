"""Unit tests for the ZonAnalys -> Kontext -> regelverk_vid seam.

Uses the real regelverk_core (pure, file-local regler.json) — hermetic, no network.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

from datetime import date

from geo_tillsyn.analysis import ZonAnalys
from geo_tillsyn.juridik import juridiskt_lage

BEDOMNING = date(2026, 7, 17)


def _inom(byggnad_id="b.1"):
    return ZonAnalys(byggnad_id, "inom", 1.0, 0.0, ["2281K-ÖVR-241"])


def test_byggnad_fore_1975_traffas_inte_av_strandskyddet():
    lage = juridiskt_lage(_inom(), byggnads_ar=1960, bedomningsdatum=BEDOMNING)

    assert lage.gallde_vid_uppforande is False
    assert lage.dispens_kravs_vid_uppforande is False
    # The zone exists today, so today's actions still need dispens.
    assert lage.dispens_kravs_idag is True


def test_byggnad_2014_traffas_och_preskriberas_aldrig():
    lage = juridiskt_lage(_inom(), byggnads_ar=2014, bedomningsdatum=BEDOMNING)

    assert lage.gallde_vid_uppforande is True
    assert lage.dispens_kravs_vid_uppforande is True
    assert lage.preskriberas is False


def test_okant_byggnadsar_flaggas_inte_gissas():
    lage = juridiskt_lage(_inom(), byggnads_ar=None, bedomningsdatum=BEDOMNING)

    assert lage.gallde_vid_uppforande is None
    assert any("tillkomstår" in a.lower() for a in lage.atgarder)


def test_ikrafttradandearet_1975_ar_tvetydigt_utan_manad():
    # Strandskyddet trädde i kraft 1975-07-01: built Jan-Jun = before, Jul-Dec
    # = after. Year granularity cannot decide — flag, don't guess.
    lage = juridiskt_lage(_inom(), byggnads_ar=1975, bedomningsdatum=BEDOMNING)

    assert lage.gallde_vid_uppforande is None
    assert any("1975" in a for a in lage.atgarder)


def test_byggnad_utanfor_zon_har_ingen_dispensplikt():
    utanfor = ZonAnalys("b.2", "utanfor", 0.0, 120.0, [])

    lage = juridiskt_lage(utanfor, byggnads_ar=2014, bedomningsdatum=BEDOMNING)

    assert lage.dispens_kravs_vid_uppforande is False
    assert lage.dispens_kravs_idag is False


def test_delvis_raknas_som_inom_zon():
    delvis = ZonAnalys("b.3", "delvis", 0.4, 0.0, ["2281K-ÖVR-241"])

    lage = juridiskt_lage(delvis, byggnads_ar=2014, bedomningsdatum=BEDOMNING)

    assert lage.dispens_kravs_idag is True

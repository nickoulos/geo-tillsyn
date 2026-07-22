"""Unit tests for the Fall 1 dossier assembly (olovligt byggande — datering).

Pure assembly — hermetic, no network. The three-level discipline from Fall 7
carries over: Fakta with källor, Bedömning that never concludes guilt,
Beslut structurally empty.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

from geo_tillsyn.datering import DateringsResultat
from geo_tillsyn.dossier import Kalla, render_markdown
from geo_tillsyn.fall1 import bygg_fall1_dossier
from geo_tillsyn.juridik import Fall1Lage

BYGGNAD_KALLA = Kalla(
    beskrivning="SundsvallsKommun:bal_byggnad_yta (WFS)",
    url="https://karta.sundsvall.se/geoserver/ows?service=WFS",
    hamtad="2026-07-21T10:00:00Z",
)
TIDSLINJE_KALLA = Kalla(
    beskrivning="Ortofoto-tidslinje 1960–2023 (WMS)",
    url="https://karta.sundsvall.se/geoserver/ows?service=WMS",
    hamtad="2026-07-21T10:00:05Z",
)
REGELVERK_KALLA = Kalla(
    beskrivning="PBL 9-11 kap. + lovbefrielser (regelverk_vid)",
    url="https://rkrattsdb.gov.se/SFSdoc/10/100900.PDF",
    hamtad="2026-07-21T10:00:06Z",
    referens="SFS 2010:900",
)


def _datering(sista=2013, forsta=2015, anmarkningar=None):
    return DateringsResultat(
        sista_ar_utan=sista,
        forsta_ar_med=forsta,
        poang_per_ar={2013: 0.1, 2015: 0.9},
        anvanda_ar=[2013, 2015],
        anmarkningar=anmarkningar or [],
    )


def _lage(**kwargs):
    grund = dict(
        sista_ar_utan=2013,
        forsta_ar_med=2015,
        area_m2=55.5,
        lovbefrielse=None,
        bygglov_kravdes=True,
        rattelse_preskriberad=True,
        sanktionsavgift_mojlig=False,
        matningskritiskt=False,
        atgarder=[],
    )
    grund.update(kwargs)
    return Fall1Lage(**grund)


def _dossier(datering=None, lage=None, bal_ar=2014, extra=None):
    return bygg_fall1_dossier(
        rubrik="Fall 1 — ALNÖ-USLAND 1:45",
        byggnad_id="bal_byggnad_yta.38472",
        datering=datering or _datering(),
        lage=lage or _lage(),
        bal_nybyggnadsar=bal_ar,
        byggnad_kalla=BYGGNAD_KALLA,
        tidslinje_kalla=TIDSLINJE_KALLA,
        regelverk_kalla=REGELVERK_KALLA,
        extra_osakerheter=extra,
    )


def test_protagonisten_fullt_dossier():
    md = render_markdown(_dossier())

    # Three levels render, in order.
    assert md.index("## 1. Fakta") < md.index("## 2. Bedömning") < md.index("## 3. Beslut")
    # Dating interval as Fakta, citing the timeline källa.
    assert "2013" in md and "2015" in md
    assert "Ortofoto-tidslinje 1960–2023 (WMS)" in md
    # Area as Fakta.
    assert "55" in md
    # BAL year 2014 inside (2013, 2015] -> consistent.
    assert "2014" in md and "förenlig" in md


def test_bedomningen_namner_bada_klockorna_men_aldrig_skuld():
    md = render_markdown(_dossier())
    bedomning = md.split("## 2. Bedömning", 1)[1].split("## 3. Beslut", 1)[0]

    assert "bygglovsplikt" in bedomning.lower()
    assert "11 kap. 20 §" in bedomning and "preskriberad" in bedomning
    assert "11 kap. 58 §" in bedomning and "utesluten" in bedomning.lower()
    # Never a guilt conclusion — that qualification is the handläggare's.
    assert "olovligt" not in bedomning.lower()
    assert "överträdelse" not in bedomning.lower()


def test_bal_ar_utanfor_intervallet_flaggas_som_avvikelse():
    dossier = _dossier(bal_ar=2009)

    texter = [f.pastaende for f in dossier.fakta]
    assert any("2009" in t and "avvik" in t.lower() for t in texter)
    alla_osakerheter = [o for b in dossier.bedomningar for o in b.osakerheter]
    assert any("register" in o.lower() or "avvik" in o.lower() for o in alla_osakerheter)


def test_saknat_bal_ar_ger_osakerhet():
    dossier = _dossier(bal_ar=None)

    alla_osakerheter = [o for b in dossier.bedomningar for o in b.osakerheter]
    assert any("bal_nybyggnadsar" in o or "saknas" in o.lower() for o in alla_osakerheter)


def test_ej_faststalld_datering_ger_forsiktig_bedomning():
    datering = _datering(
        sista=None, forsta=None, anmarkningar=["Datering ej fastställd: för få årgångar."]
    )
    lage = _lage(
        sista_ar_utan=None,
        forsta_ar_med=None,
        bygglov_kravdes=None,
        rattelse_preskriberad=None,
        sanktionsavgift_mojlig=None,
        atgarder=["Byggnadens tillkomstår är inte fastställt — datera först."],
    )

    md = render_markdown(_dossier(datering=datering, lage=lage))

    assert "Ej fastställt" in md
    bedomning = md.split("## 2. Bedömning", 1)[1].split("## 3. Beslut", 1)[0]
    assert "preskriberad" not in bedomning.split("Ej fastställt")[0]


def test_atgarder_och_extra_hamnar_i_osakerhetskanalen():
    lage = _lage(
        atgarder=["Strandskyddstillsyn preskriberas aldrig (MÖD 2021:6) — se Fall 7."]
    )
    dossier = _dossier(
        lage=lage,
        extra=["Bygglovsregistret är inte tillgängligt i prototypfasen (testärenden används)."],
    )

    alla_osakerheter = [o for b in dossier.bedomningar for o in b.osakerheter]
    assert any("MÖD 2021:6" in o for o in alla_osakerheter)
    assert any("Bygglovsregistret" in o for o in alla_osakerheter)


def test_dateringens_anmarkningar_foljer_med_som_osakerheter():
    datering = _datering(anmarkningar=["Otydliga årgångar: 1998 — manuell granskning."])

    dossier = _dossier(datering=datering)

    alla_osakerheter = [o for b in dossier.bedomningar for o in b.osakerheter]
    assert any("Otydliga årgångar" in o for o in alla_osakerheter)

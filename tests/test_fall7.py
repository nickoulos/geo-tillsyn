"""Unit tests for the Fall 7 dossier assembly (strandskydd).

Pure assembly from analysis results — hermetic, no network.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

from geo_tillsyn.analysis import ZonAnalys
from geo_tillsyn.dossier import Kalla, render_markdown
from geo_tillsyn.fall7 import bygg_dossier
from geo_tillsyn.juridik import JuridisktLage

BYGGNAD_KALLA = Kalla(
    beskrivning="SundsvallsKommun:bal_byggnad_yta (WFS)",
    url="https://karta.sundsvall.se/geoserver/ows?service=WFS&request=GetFeature&typeNames=SundsvallsKommun:bal_byggnad_yta",
    hamtad="2026-07-17T09:00:00Z",
)
ZON_KALLA = Kalla(
    beskrivning="SundsvallsKommun:lm_strandskydd_y (WFS)",
    url="https://karta.sundsvall.se/geoserver/ows?service=WFS&request=GetFeature&typeNames=SundsvallsKommun:lm_strandskydd_y",
    hamtad="2026-07-17T09:00:01Z",
    referens="2281K-ÖVR-241",
)

ANALYSER = [
    ZonAnalys("bal_byggnad_yta.10", "inom", 1.0, 0.0, ["2281K-ÖVR-241"]),
    ZonAnalys("bal_byggnad_yta.20", "utanfor", 0.0, 141.4, []),
    ZonAnalys("bal_byggnad_yta.30", "delvis", 0.5, 0.0, ["2281K-ÖVR-241"]),
]


def _dossier():
    return bygg_dossier(
        rubrik="Strandskyddskontroll — Aktervägen",
        analyser=ANALYSER,
        byggnad_kalla=BYGGNAD_KALLA,
        strandskydd_kalla=ZON_KALLA,
        extra_osakerheter=["Utvidgat strandskydd kunde inte kontrolleras."],
    )


def test_fakta_om_antal_byggnader_och_traffar():
    dossier = _dossier()
    texter = [f.pastaende for f in dossier.fakta]

    assert any("3 byggnader" in t for t in texter)
    assert any("bal_byggnad_yta.10" in t and "helt inom" in t for t in texter)
    assert any("bal_byggnad_yta.30" in t and "delvis" in t for t in texter)


def test_utanfor_byggnader_aggregeras_till_en_fakta():
    # Absence of a träff is underlag too, but 140 identical "utanför" lines is
    # noise, not fakta: they aggregate to ONE fact with count + min distance.
    dossier = _dossier()
    texter = [f.pastaende for f in dossier.fakta]

    utanfor = [t for t in texter if "utanför" in t]
    assert len(utanfor) == 1
    assert "1 byggnad" in utanfor[0]
    assert "141 m" in utanfor[0]
    # No per-building fact for buildings outside the zone.
    assert not any("bal_byggnad_yta.20" in t for t in texter)


def test_zonfakta_bar_strandskyddskallan_med_aktbeteckning():
    dossier = _dossier()

    traff_fakta = [f for f in dossier.fakta if "helt inom" in f.pastaende]
    assert traff_fakta[0].kalla == ZON_KALLA


def test_bedomning_bara_for_byggnader_med_traff():
    dossier = _dossier()

    paastaenden = [b.pastaende for b in dossier.bedomningar]
    assert any("bal_byggnad_yta.10" in p for p in paastaenden)
    assert any("bal_byggnad_yta.30" in p for p in paastaenden)
    assert not any("bal_byggnad_yta.20" in p for p in paastaenden)


def test_bedomning_ar_bedomning_inte_slutsats_om_overtradelse():
    dossier = _dossier()

    for bedomning in dossier.bedomningar:
        # 7:15 MB dispensplikt may be raised; guilt/violation may not.
        assert "olovlig" not in bedomning.pastaende.lower()
        assert "överträdelse" not in bedomning.pastaende.lower()


def test_extra_osakerheter_hamnar_i_bedomningen():
    dossier = _dossier()

    alla_osakerheter = [o for b in dossier.bedomningar for o in b.osakerheter]
    assert "Utvidgat strandskydd kunde inte kontrolleras." in alla_osakerheter


REGELVERK_KALLA = Kalla(
    beskrivning="Miljöbalken 7 kap. (SFS 1998:808)",
    url="https://rkrattsdb.gov.se/SFSdoc/98/980808.PDF",
    hamtad="2026-07-17T09:00:02Z",
    referens="MB 7 kap. 13-18h §§",
)


def _dossier_med_juridik(lage):
    analys = ZonAnalys(lage.byggnad_id, "inom", 1.0, 0.0, ["2281K-ÖVR-241"])
    return bygg_dossier(
        rubrik="Strandskyddskontroll",
        analyser=[analys],
        byggnad_kalla=BYGGNAD_KALLA,
        strandskydd_kalla=ZON_KALLA,
        juridik={lage.byggnad_id: lage},
        regelverk_kalla=REGELVERK_KALLA,
    )


def test_byggnad_fore_1975_far_lagligt_uppforande_i_dossieren():
    lage = JuridisktLage(
        byggnad_id="b.gammal",
        byggnads_ar=1960,
        gallde_vid_uppforande=False,
        dispens_kravs_vid_uppforande=False,
        dispens_kravs_idag=True,
        preskriberas=False,
    )

    md = render_markdown(_dossier_med_juridik(lage))

    assert "1960" in md
    assert "gällde inte" in md and "uppför" in md
    # The old building must NOT get the dispensplikt assessment for its
    # construction — but new actions in the zone still need dispens.
    bedomning = md.split("## 2. Bedömning", 1)[1].split("## 3. Beslut", 1)[0]
    assert "krävde inte strandskyddsdispens" in bedomning
    assert "Nya åtgärder" in bedomning


def test_byggnad_2014_far_preskription_och_skalighet_som_human_node():
    lage = JuridisktLage(
        byggnad_id="b.ny",
        byggnads_ar=2014,
        gallde_vid_uppforande=True,
        dispens_kravs_vid_uppforande=True,
        dispens_kravs_idag=True,
        preskriberas=False,
    )

    md = render_markdown(_dossier_med_juridik(lage))

    assert "2014" in md
    bedomning = md.split("## 2. Bedömning", 1)[1].split("## 3. Beslut", 1)[0]
    # "No preskription" must never render as "still enforceable" alone:
    # the skälighet counterweight and its case law are mandatory.
    assert "MÖD 2021:6" in bedomning
    assert "MÖD 2017:16" in bedomning
    assert "skälighet" in bedomning.lower()
    assert "handläggaren" in bedomning


def test_okant_ar_ger_atgard_som_osakerhet():
    lage = JuridisktLage(
        byggnad_id="b.okand",
        byggnads_ar=None,
        gallde_vid_uppforande=None,
        dispens_kravs_vid_uppforande=False,
        dispens_kravs_idag=True,
        preskriberas=False,
        atgarder=["Byggnadens tillkomstår är inte fastställt — datera via ortofoto."],
    )

    md = render_markdown(_dossier_med_juridik(lage))

    assert "Ej fastställt" in md
    assert "datera via ortofoto" in md


def test_regelverksfakta_bar_sfs_kallan():
    lage = JuridisktLage(
        byggnad_id="b.ny",
        byggnads_ar=2014,
        gallde_vid_uppforande=True,
        dispens_kravs_vid_uppforande=True,
        dispens_kravs_idag=True,
        preskriberas=False,
    )

    dossier = _dossier_med_juridik(lage)

    regel_fakta = [f for f in dossier.fakta if f.kalla == REGELVERK_KALLA]
    assert regel_fakta, "regelverksfakta ska peka på officiell SFS-källa"


def test_dossier_utan_traffar_har_ingen_dispensbedomning():
    dossier = bygg_dossier(
        rubrik="Strandskyddskontroll",
        analyser=[ZonAnalys("b.1", "utanfor", 0.0, 55.0, [])],
        byggnad_kalla=BYGGNAD_KALLA,
        strandskydd_kalla=ZON_KALLA,
    )

    assert not any("dispens" in b.pastaende.lower() for b in dossier.bedomningar)
    # Still a renderable three-level dossier.
    md = render_markdown(dossier)
    assert "## 3. Beslut" in md

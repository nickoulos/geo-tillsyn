"""Unit tests for the dossier model and markdown renderer.

The three-level separation IS the product: Fakta (each with a clickable
källa), Bedömning (with explicit uncertainty), Beslut (always empty — the
handläggare's). Hermetic, no network.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

import dataclasses

from geo_tillsyn.dossier import Bedomning, Dossier, Fakta, Kalla, render_markdown

KALLA_WFS = Kalla(
    beskrivning="SundsvallsKommun:lm_strandskydd_y (WFS)",
    url="https://karta.sundsvall.se/geoserver/ows?service=WFS&request=GetFeature",
    hamtad="2026-07-17T09:00:00Z",
    referens="2281K-ÖVR-241",
)


def _dossier():
    return Dossier(
        rubrik="Strandskyddskontroll — Aktervägen, Sundsvall",
        fakta=[
            Fakta("Byggnaden ligger helt inom strandskyddszon.", KALLA_WFS),
            Fakta(
                "Byggnaden syns första gången i ortofoto 2016.",
                Kalla(
                    beskrivning="Lantmateriet:Orto2016_wms (WMS)",
                    url="https://karta.sundsvall.se/geoserver/ows?service=WMS&request=GetMap",
                    hamtad="2026-07-17T09:00:05Z",
                    referens="ortofoto 2016",
                ),
            ),
        ],
        bedomningar=[
            Bedomning(
                pastaende="Åtgärden är sannolikt dispenspliktig enligt 7 kap. 15 § miljöbalken.",
                grund=[0, 1],
                osakerheter=[
                    "Utvidgat strandskydd kunde inte kontrolleras (källan otillgänglig)."
                ],
            )
        ],
    )


def test_dossier_har_inget_beslutsfalt():
    # Beslut is the handläggare's. The model must not even be able to carry one.
    field_names = {f.name for f in dataclasses.fields(Dossier)}
    assert "beslut" not in field_names
    assert field_names == {"rubrik", "fakta", "bedomningar"}


def test_render_har_tre_nivaer_i_ordning():
    md = render_markdown(_dossier())

    i_fakta = md.index("## 1. Fakta")
    i_bedomning = md.index("## 2. Bedömning")
    i_beslut = md.index("## 3. Beslut")
    assert i_fakta < i_bedomning < i_beslut


def test_varje_fakta_far_klickbar_kalla_med_tidsstampel():
    md = render_markdown(_dossier())

    assert "[SundsvallsKommun:lm_strandskydd_y (WFS)](" in md
    assert "https://karta.sundsvall.se/geoserver/ows?service=WFS&request=GetFeature" in md
    assert "2026-07-17T09:00:00Z" in md
    assert "2281K-ÖVR-241" in md


def test_bedomning_refererar_grund_och_redovisar_osakerhet():
    md = render_markdown(_dossier())

    assert "F1" in md and "F2" in md
    assert "Ej fastställt" in md
    assert "Utvidgat strandskydd kunde inte kontrolleras" in md


def test_beslutsdelen_ar_tom_och_markerad_for_handlaggaren():
    md = render_markdown(_dossier())

    beslut = md.split("## 3. Beslut", 1)[1]
    assert "handläggaren" in beslut
    # No assessment language may leak into the decision level.
    assert "dispens" not in beslut.lower()
    assert "sannolikt" not in beslut.lower()


def test_fakta_numreras_f1_f2():
    md = render_markdown(_dossier())

    assert "**F1**" in md
    assert "**F2**" in md

"""Klarspråksvyn: samma fakta, samma källor — ett språk för berörd part.

Effektmålet "pedagogiskt beslutsunderlag" (Konceptbeskrivning; dossier/README:
två vyer ur samma fakta). Vyn är en ren omrendering — den lägger aldrig till
påståenden, tar aldrig bort källor, och fäller aldrig ett omdöme.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

from geo_tillsyn.dossier import (
    Bedomning,
    Dossier,
    Fakta,
    Kalla,
    render_klarsprak,
    render_markdown,
)

_KALLA = Kalla(
    beskrivning="SundsvallsKommun:lm_strandskydd_y (WFS)",
    url="https://example.test/wfs",
    hamtad="2026-08-20T10:00:00Z",
)

DOSSIER = Dossier(
    rubrik="Strandskyddskontroll — punkt E 158140, N 6918389 (EPSG:3014), radie 120 m",
    fakta=[
        Fakta("Byggnad bal_byggnad_yta.38472 ligger helt inom strandskyddszon.", _KALLA),
        Fakta(
            "Byggnad bal_byggnad_yta.38472 uppfördes år 2014 enligt byggnadsregistret (BAL).",
            Kalla("SundsvallsKommun:bal_byggnad_yta (WFS)", "https://example.test/wfs2", "2026-08-20T10:00:00Z"),
        ),
    ],
    bedomningar=[
        Bedomning(
            "Dispens krävs i dag för byggnaden.",
            grund=[0, 1],
            osakerheter=["Beviljade strandskyddsdispenser har inte kontrollerats mot dispensregistret."],
        )
    ],
)


def test_klarsprak_har_pedagogiska_rubriker_i_ordning():
    text = render_klarsprak(DOSSIER)
    rubriker = [r for r in text.splitlines() if r.startswith("## ")]
    assert rubriker == [
        "## Vad handlar det här om?",
        "## Det här har vi sett",
        "## Så här kan det tolkas",
        "## Vad händer nu?",
        "## Ordlista",
    ]
    # Ingen juridisk nivånumrering i den här vyn.
    assert "## 1. Fakta" not in text
    assert "## 2. Bedömning" not in text


def test_varje_fakta_behaller_sin_kalla_och_tidsstampel():
    text = render_klarsprak(DOSSIER)
    for fakta in DOSSIER.fakta:
        assert fakta.pastaende in text
        assert fakta.kalla.url in text
    assert "2026-08-20" in text
    # Klarspråk får aldrig bli sämre spårbarhet än den juridiska vyn.
    assert text.count("https://example.test/") == len(DOSSIER.fakta)


def test_osakerheter_star_kvar_med_klarsprakig_inledning():
    text = render_klarsprak(DOSSIER)
    assert "Det här vet vi inte säkert:" in text
    assert "dispensregistret" in text


def test_ingen_dator_beslutar_star_uttryckligen():
    text = render_klarsprak(DOSSIER)
    assert "## Vad händer nu?" in text
    assert "inte ett beslut" in text
    assert "handläggare" in text


def test_ordlistan_forklarar_bara_termer_som_forekommer():
    text = render_klarsprak(DOSSIER)
    # Förekommer i dossiern:
    assert "**strandskydd**" in text
    assert "**dispens**" in text
    assert "**byggnadsregistret**" in text
    # Förekommer inte — får inte förklaras:
    assert "**sanktionsavgift**" not in text
    assert "**bygglov**" not in text


def test_ordlistan_hittar_termer_aven_i_bedomningar_och_osakerheter():
    d = Dossier(
        rubrik="Kontroll",
        fakta=[Fakta("Byggnaden är 55 kvadratmeter.", _KALLA)],
        bedomningar=[
            Bedomning("Sanktionsavgift är inte längre möjlig.", osakerheter=["Preskription oklar."])
        ],
    )
    text = render_klarsprak(d)
    assert "**sanktionsavgift**" in text
    assert "**preskription**" in text


def test_klarsprak_lagger_aldrig_till_pastaenden():
    """Varje mening i 'Det här har vi sett' ska ordagrant finnas i dossiern."""
    text = render_klarsprak(DOSSIER)
    sett = text.split("## Det här har vi sett")[1].split("## Så här kan det tolkas")[0]
    for rad in sett.splitlines():
        if rad.startswith("- "):
            assert rad[2:].strip() in [f.pastaende for f in DOSSIER.fakta]


def test_bada_vyerna_fran_samma_dossier_ar_konsistenta():
    juridisk = render_markdown(DOSSIER)
    klarsprak = render_klarsprak(DOSSIER)
    for fakta in DOSSIER.fakta:
        assert fakta.pastaende in juridisk
        assert fakta.pastaende in klarsprak

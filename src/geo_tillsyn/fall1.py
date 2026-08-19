"""Fall 1 — olovligt byggande: sätt samman datering och lovplikt till en dossier.

REALITY = ortofoto-tidslinjen (när dök byggnaden upp, enligt bildserien).
RULE = bygglovsplikten och dess klockor (PBL 9-11 kap., lovbefrielser,
preskription) sådana de gällde under det intervall byggnaden sannolikt
uppfördes. DIFF = om byggnadsregistrets (BAL) uppgivna nybyggnadsår är
förenligt med det datum-intervall som ortofoto-tidslinjen ger. Bedömningen
stannar vid att uppförandet sannolikt var bygglovspliktigt (eller inte) —
aldrig en slutsats om att bygget var olovligt eller en överträdelse; den
kvalificeringen, och beslutet, är handläggarens.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

from __future__ import annotations

from geo_tillsyn.datering import DateringsResultat
from geo_tillsyn.dossier import Bedomning, Dossier, Fakta, Kalla
from geo_tillsyn.juridik import Fall1Lage


def _dateringsfakta(datering: DateringsResultat) -> str:
    if datering.forsta_ar_med is None:
        return (
            "Byggnadens tillkomstår kunde inte fastställas från "
            "ortofoto-tidslinjen (för få eller otydliga årgångar)."
        )
    return (
        f"Byggnaden syns första gången i ortofoto {datering.forsta_ar_med} "
        f"och saknas fortfarande i ortofoto {datering.sista_ar_utan}."
    )


def _bal_cross_check(
    bal_nybyggnadsar: int | None,
    lage: Fall1Lage,
) -> tuple[str | None, list[str]]:
    """Return (fact text or None, extra osäkerheter) for the BAL cross-check."""
    osakerheter: list[str] = []

    if bal_nybyggnadsar is None:
        osakerheter.append(
            "Byggnadsregistrets nybyggnadsår (bal_nybyggnadsar) saknas — "
            "ingen jämförelse mot ortofoto-intervallet kan göras."
        )
        return None, osakerheter

    if lage.forsta_ar_med is None:
        # Interval unknown: report the BAL year plainly, no förenlig/avvik claim.
        return (
            f"Byggnadsregistret (BAL) anger nybyggnadsår {bal_nybyggnadsar}."
        ), osakerheter

    if lage.sista_ar_utan is not None and (
        lage.sista_ar_utan < bal_nybyggnadsar <= lage.forsta_ar_med
    ):
        return (
            f"Byggnadsregistret (BAL) anger nybyggnadsår {bal_nybyggnadsar}, "
            "vilket är förenligt med ortofoto-intervallet."
        ), osakerheter

    osakerheter.append(
        f"Byggnadsregistrets nybyggnadsår ({bal_nybyggnadsar}) avviker från "
        "ortofoto-intervallet — registeruppgiften bör granskas manuellt."
    )
    return (
        f"Byggnadsregistret (BAL) anger nybyggnadsår {bal_nybyggnadsar}, "
        "vilket avviker från ortofoto-intervallet."
    ), osakerheter


def _regelverksfakta(lage: Fall1Lage, area_m2: float) -> str | None:
    if lage.bygglov_kravdes is None:
        return None
    if lage.bygglov_kravdes:
        return (
            f"Vid uppförandet fanns ingen lovbefrielse som täckte {area_m2:.1f} "
            "m² — bygglov krävdes enligt då gällande regelverk."
        )
    return (
        f"Uppförandet omfattades av lovbefrielsen \"{lage.lovbefrielse}\" — "
        "inget bygglov krävdes enligt då gällande regelverk."
    )


def _bedomning_pastaende(lage: Fall1Lage) -> str:
    if lage.bygglov_kravdes is True:
        pastaende = (
            "Uppförandet var sannolikt bygglovspliktigt enligt det regelverk "
            "som gällde vid uppförandet."
        )
        if lage.rattelse_preskriberad is True:
            pastaende += (
                " Möjligheten till rättelseföreläggande enligt PBL 11 kap. 20 § "
                "är preskriberad (10 år)."
            )
        elif lage.rattelse_preskriberad is False:
            pastaende += (
                " Möjligheten till rättelseföreläggande enligt PBL 11 kap. 20 § "
                "är inte preskriberad (10 år)."
            )
        if lage.sanktionsavgift_mojlig is False:
            pastaende += (
                " Byggsanktionsavgift enligt PBL 11 kap. 58 § är utesluten (5 år)."
            )
        elif lage.sanktionsavgift_mojlig is True:
            pastaende += (
                " Byggsanktionsavgift enligt PBL 11 kap. 58 § är fortfarande möjlig (5 år)."
            )
        return pastaende

    if lage.bygglov_kravdes is False:
        return (
            "Uppförandet omfattades sannolikt av lovbefrielsen och krävde "
            "därmed inget bygglov enligt det regelverk som gällde vid "
            "uppförandet."
        )

    return (
        "Bygglovsplikten vid uppförandet kan inte avgöras ännu — "
        "byggnadens tillkomstår behöver preciseras."
    )


def bygg_fall1_dossier(
    rubrik: str,
    byggnad_id: str,
    datering: DateringsResultat,
    lage: Fall1Lage,
    bal_nybyggnadsar: int | None,
    byggnad_kalla: Kalla,
    tidslinje_kalla: Kalla,
    regelverk_kalla: Kalla,
    extra_osakerheter: list[str] | None = None,
    extra_fakta: list[Fakta] | None = None,
) -> Dossier:
    """Assemble the three-level Fall 1 dossier from datering + juridiskt läge.

    Every fact carries the källa it came from: the area and BAL cross-check
    cite the building layer, the dating interval cites the ortofoto-tidslinje,
    and the bygglovsplikt fact cites the official regelverk källa. The
    bedömning never concludes that the building was olovligt — only whether
    bygglovsplikt is judged likely, and how the PBL preskriptionsklockor (11
    kap. 20 § resp. 58 §) currently stand. That qualification, and any
    beslut, is handläggarens.
    """
    fakta: list[Fakta] = []

    area_index = len(fakta)
    fakta.append(
        Fakta(
            f"Byggnad {byggnad_id} har en byggnadsyta på ca {lage.area_m2:.1f} m².",
            byggnad_kalla,
        )
    )

    datering_index = len(fakta)
    fakta.append(Fakta(_dateringsfakta(datering), tidslinje_kalla))

    grund = [area_index, datering_index]

    bal_text, bal_osakerheter = _bal_cross_check(bal_nybyggnadsar, lage)
    if bal_text is not None:
        grund.append(len(fakta))
        fakta.append(Fakta(bal_text, byggnad_kalla))

    regelverks_text = _regelverksfakta(lage, lage.area_m2)
    if regelverks_text is not None:
        grund.append(len(fakta))
        fakta.append(Fakta(regelverks_text, regelverk_kalla))

    osakerheter = (
        list(datering.anmarkningar)
        + list(lage.atgarder)
        + bal_osakerheter
        + list(extra_osakerheter or [])
    )

    bedomning = Bedomning(
        pastaende=_bedomning_pastaende(lage),
        grund=grund,
        osakerheter=osakerheter,
    )

    fakta.extend(extra_fakta or [])

    return Dossier(rubrik=rubrik, fakta=fakta, bedomningar=[bedomning])

"""Fall 7 — strandskydd: sätt samman analysresultat till en dossier.

REALITY = byggnader (bal_byggnad_yta), RULE = strandskyddszoner
(lm_strandskydd_y). DIFF = vilka byggnader som träffar en zon. Bedömningen
stannar vid dispensplikt enligt 7 kap. 15 § miljöbalken — aldrig en slutsats
om överträdelse; den kvalificeringen, och beslutet, är handläggarens.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

from __future__ import annotations

from geo_tillsyn.analysis import ZonAnalys
from geo_tillsyn.dossier import Bedomning, Dossier, Fakta, Kalla
from geo_tillsyn.juridik import JuridisktLage

# "Ingen preskription" får aldrig ensamt läsas som "fortfarande verkställbart":
# skälighetsmotvikten och dess rättsfall är obligatoriska (docs/legal-findings.md §3).
_PRESKRIPTION_MED_SKALIGHET = (
    "Ingen preskription gäller för strandskyddstillsyn (MÖD 2021:6), men "
    "skälighetsbedömningen enligt MÖD 2017:16 — särskilt mot godtroende ny "
    "ägare — är handläggarens."
)


def _traff_fakta(analys: ZonAnalys) -> str:
    if analys.laege == "inom":
        return f"Byggnad {analys.byggnad_id} ligger helt inom strandskyddszon."
    return (
        f"Byggnad {analys.byggnad_id} ligger delvis inom strandskyddszon "
        f"({analys.andel_inom:.0%} av byggnadsytan)."
    )


def _utanfor_fakta(utanfor: list[ZonAnalys]) -> str:
    antal = len(utanfor)
    byggnad_ord = "byggnad" if antal == 1 else "byggnader"
    minsta = min(a.avstand_m for a in utanfor)
    if minsta == float("inf"):
        return (
            f"{antal} {byggnad_ord} ligger utanför strandskyddszon "
            "(ingen zon i det undersökta området)."
        )
    return (
        f"{antal} {byggnad_ord} ligger utanför strandskyddszon "
        f"(minsta avstånd till zon: {minsta:.0f} m)."
    )


def bygg_dossier(
    rubrik: str,
    analyser: list[ZonAnalys],
    byggnad_kalla: Kalla,
    strandskydd_kalla: Kalla,
    extra_osakerheter: list[str] | None = None,
    juridik: dict[str, JuridisktLage] | None = None,
    regelverk_kalla: Kalla | None = None,
    extra_fakta_per_byggnad: dict[str, list[Fakta]] | None = None,
) -> Dossier:
    """Assemble the three-level Fall 7 dossier from intersection analyses.

    Every fact carries the källa it came from: counts cite the building layer,
    zone positions cite the strandskydd layer, and — when `juridik` is given —
    the time-aware regime facts cite `regelverk_kalla` (official SFS). A
    pre-1975 building inside today's zone is reported as lawfully erected;
    its åtgärder land in the osäkerhet channel. `extra_fakta_per_byggnad`
    (e.g. utvidgat/upphävt strandskydd touched) is appended to that building's
    facts and counted into its bedömning's grund.
    """
    juridik = juridik or {}
    extra_fakta_per_byggnad = extra_fakta_per_byggnad or {}
    fakta: list[Fakta] = [
        Fakta(
            f"{len(analyser)} byggnader identifierade inom det undersökta området.",
            byggnad_kalla,
        )
    ]
    grund_per_byggnad: dict[str, list[int]] = {}
    traffar = [a for a in analyser if a.laege in ("inom", "delvis")]
    utanfor = [a for a in analyser if a.laege == "utanfor"]
    for analys in traffar:
        grund_per_byggnad[analys.byggnad_id] = [len(fakta)]
        fakta.append(Fakta(_traff_fakta(analys), strandskydd_kalla))

        lage = juridik.get(analys.byggnad_id)
        if lage and lage.byggnads_ar is not None:
            grund_per_byggnad[analys.byggnad_id].append(len(fakta))
            fakta.append(
                Fakta(
                    f"Byggnad {analys.byggnad_id} uppfördes år {lage.byggnads_ar} "
                    "enligt byggnadsregistret (BAL).",
                    byggnad_kalla,
                )
            )
        if lage and lage.gallde_vid_uppforande is not None:
            grund_per_byggnad[analys.byggnad_id].append(len(fakta))
            gallde_text = (
                f"Strandskyddet gällde när byggnad {analys.byggnad_id} uppfördes."
                if lage.gallde_vid_uppforande
                else (
                    f"Strandskyddet gällde inte när byggnad {analys.byggnad_id} "
                    "uppfördes (generellt strandskydd infördes 1975-07-01)."
                )
            )
            fakta.append(Fakta(gallde_text, regelverk_kalla or strandskydd_kalla))
        for extra in extra_fakta_per_byggnad.get(analys.byggnad_id, []):
            grund_per_byggnad[analys.byggnad_id].append(len(fakta))
            fakta.append(extra)
    if utanfor:
        fakta.append(Fakta(_utanfor_fakta(utanfor), strandskydd_kalla))

    osakerheter = list(extra_osakerheter or [])
    bedomningar: list[Bedomning] = []
    for analys in traffar:
        lage = juridik.get(analys.byggnad_id)
        zoner = ", ".join(analys.zon_referenser) or "strandskyddszon"
        grund = [0, *grund_per_byggnad[analys.byggnad_id]]
        byggnad_osakerheter = osakerheter + (list(lage.atgarder) if lage else [])

        if lage and lage.gallde_vid_uppforande is False:
            pastaende = (
                f"Uppförandet av byggnad {analys.byggnad_id} krävde inte "
                "strandskyddsdispens — byggnaden tillkom före strandskyddets "
                f"ikraftträdande. Nya åtgärder inom zonen ({zoner}) kräver dock "
                "dispens enligt 7 kap. 15 § miljöbalken."
            )
        else:
            pastaende = (
                f"Åtgärder på byggnad {analys.byggnad_id} inom zonen ({zoner}) "
                "kan vara dispenspliktiga enligt 7 kap. 15 § miljöbalken."
            )
            if lage and lage.gallde_vid_uppforande is True:
                pastaende += f" {_PRESKRIPTION_MED_SKALIGHET}"

        bedomningar.append(
            Bedomning(
                pastaende=pastaende,
                grund=grund,
                osakerheter=byggnad_osakerheter,
            )
        )

    if not bedomningar:
        bedomningar.append(
            Bedomning(
                pastaende=(
                    "Ingen byggnad i området träffar en strandskyddszon; "
                    "inget underlag för vidare åtgärd utifrån detta lager."
                ),
                grund=list(range(len(fakta))),
                osakerheter=osakerheter,
            )
        )

    return Dossier(rubrik=rubrik, fakta=fakta, bedomningar=bedomningar)

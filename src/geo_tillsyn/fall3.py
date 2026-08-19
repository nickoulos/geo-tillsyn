"""Fall 3 — lovavvikelse: godkänt läge vs verkligt läge, sammansatt till dossier.

REALITY = byggnadens verkliga läge och area (WFS + ortofoto-datering).
RULE = det beviljade (syntetiska) lovet: godkänt läge, area, villkor — läst ur
mock-ByggR OCH ur den skannade handlingen (OCR), i öppen korsjämförelse.
DIFF = delta-motorns kvantifierade avvikelser. TIME = när avvikelsen
färdigställdes -> PBL-klockorna; Vilken lag som styr lovet är den som gällde
vid beslutsdatum (ÄPBL för lov beslutade före 2011-05-02). Bedömningen kvantifierar —
om avvikelsen är väsentlig, och beslutet, är handläggarens.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

from __future__ import annotations

from geo_tillsyn.datering import DateringsResultat
from geo_tillsyn.delta import DeltaResultat
from geo_tillsyn.dossier import Bedomning, Dossier, Fakta, Kalla
from geo_tillsyn.juridik import _AREA_BAND_M2, _AVSTAND_BAND_M, Fall3Lage
from geo_tillsyn.lovarkiv import LovBeslut


def _lovfakta(lov: LovBeslut) -> str:
    byggnadsarea = (
        f"byggnadsarea {lov.byggnadsarea_m2:.1f} m²."
        if lov.byggnadsarea_m2 is not None
        else "byggnadsarea ej angiven i registerposten."
    )
    text = (
        f"Bygglov {lov.dnr} ({lov.fastighet}) beviljades {lov.beslutsdatum}: "
        f"{lov.atgard}, {byggnadsarea}"
    )
    if lov.villkor:
        text += " Villkor: " + "; ".join(lov.villkor)
    if lov.anmarkning:
        text += f" [{lov.anmarkning}]"
    return text


def _korsjamforelsefakta(korsjamforelse: dict[str, str] | None) -> str | None:
    if not korsjamforelse:
        return None
    delar = [f"{namn}: {status}" for namn, status in sorted(korsjamforelse.items())]
    return (
        "Korskontroll skannad handling (OCR) mot registerposten — "
        + "; ".join(delar) + "."
    )


def _sv(x: float) -> str:
    return f"{x:+.1f}".replace(".", ",")


def _areadeltafakta(delta: DeltaResultat) -> str:
    return (
        f"Verklig byggnadsarea {delta.verklig_area_m2:.1f} m² mot godkänd "
        f"{delta.godkand_area_m2:.1f} m² — skillnad {_sv(delta.area_diff_m2)} m² "
        f"({_sv(delta.area_diff_procent)} %)."
    )


def _lagedeltafakta(delta: DeltaResultat) -> str | None:
    if delta.avstand_grans_godkant_m is None or delta.avstand_grans_verklig_m is None:
        return None
    return (
        f"Byggnaden ligger {delta.avstand_grans_verklig_m:.1f} m från fastighetsgräns "
        f"mot godkända {delta.avstand_grans_godkant_m:.1f} m; "
        f"{delta.utanfor_godkant_m2:.1f} m² av byggnaden ligger utanför godkänt läge "
        f"(förskjutning {delta.centroid_forskjutning_m:.1f} m)."
    )


def _dateringsfakta(datering: DateringsResultat) -> str:
    if datering.forsta_ar_med is None:
        return (
            "Färdigställandet kunde inte dateras från ortofoto-tidslinjen "
            "(för få eller otydliga årgångar)."
        )
    return (
        f"Byggnaden i sitt nuvarande läge syns första gången i ortofoto "
        f"{datering.forsta_ar_med} och saknas fortfarande i ortofoto "
        f"{datering.sista_ar_utan}."
    )


def _regelverksfakta(lage: Fall3Lage) -> str | None:
    if lage.pbl_vid_beslut is None:
        return None
    text = f"Lovet prövas enligt {lage.pbl_vid_beslut} ({lage.tillsyn_lagrum})."
    if lage.overgangsregel_tillampad:
        text += (
            " Övergångsbestämmelsen i PBL 2010:900 p. 2 tillämpas: ärenden "
            "påbörjade före 2011-05-02 följer äldre lag tills de är slutligt avgjorda."
        )
    return text


def _bedomning_pastaende(lage: Fall3Lage, delta: DeltaResultat) -> str:
    avstandsskillnad = (
        abs(delta.avstand_grans_godkant_m - delta.avstand_grans_verklig_m)
        if delta.avstand_grans_godkant_m is not None and delta.avstand_grans_verklig_m is not None
        else 0.0
    )
    tydlig = (
        abs(delta.area_diff_m2) > _AREA_BAND_M2
        or delta.utanfor_godkant_m2 > _AREA_BAND_M2
        or avstandsskillnad > _AVSTAND_BAND_M
    )
    nagon_avvikelse = (
        abs(delta.area_diff_m2) > 0.05 or delta.utanfor_godkant_m2 > 0.05 or avstandsskillnad > 0.05
    )

    if tydlig:
        text = (
            f"Byggnadens utförande avviker mätbart från det beviljade lovet "
            f"({delta.area_diff_m2:+.1f} m² area; "
            f"{delta.utanfor_godkant_m2:.1f} m² utanför godkänt läge). "
            "Om avvikelsen är väsentlig är en rättslig kvalificering som görs av "
            "handläggaren, inte av systemet."
        )
    elif nagon_avvikelse:
        text = (
            "Avvikelser mellan utförandet och det beviljade lovet har uppmätts "
            "men ligger inom mätosäkerheten och kan inte beläggas utan inmätning."
        )
    else:
        text = "Inga mätbara avvikelser mellan utförandet och det beviljade lovet har konstaterats."

    if lage.rattelse_preskriberad is True:
        text += " Möjligheten till rättelseföreläggande (10 år) är preskriberad."
    elif lage.rattelse_preskriberad is False:
        text += " Möjligheten till rättelseföreläggande (10 år) är inte preskriberad."
    if lage.sanktionsavgift_mojlig is False:
        text += " Byggsanktionsavgift (5 år) är utesluten."
    elif lage.sanktionsavgift_mojlig is True:
        text += " Byggsanktionsavgift (5 år) är fortfarande möjlig."
    return text


def bygg_fall3_dossier(
    rubrik: str,
    lov: LovBeslut,
    korsjamforelse: dict[str, str] | None,
    tolkat_anmarkningar: list[str],
    delta: DeltaResultat,
    datering: DateringsResultat,
    lage: Fall3Lage,
    lov_kalla: Kalla,
    handling_kalla: Kalla | None,
    byggnad_kalla: Kalla,
    grans_kalla: Kalla | None,
    tidslinje_kalla: Kalla,
    regelverk_kalla: Kalla,
    extra_osakerheter: list[str] | None = None,
    extra_fakta: list[Fakta] | None = None,
) -> Dossier:
    """Assemble the three-level Fall 3 dossier: lov, korskontroll, delta, lag.

    Every fact carries the källa it came from: the lov cites the (syntetiska)
    mock-ByggR-arkivet, the OCR cross-check cites the skannade handlingen, the
    area/läge-avvikelser cite byggnaden resp. fastighetsgränsen, the
    färdigställande-datering cites ortofoto-tidslinjen, and the styrande lag
    cites den officiella regelverkskällan. The bedömning quantifies the
    deviation and states both PBL-klockor without ever concluding olovligt
    byggande eller överträdelse — väsentlighet och beslut är handläggarens.
    """
    fakta: list[Fakta] = []
    grund: list[int] = []

    grund.append(len(fakta))
    fakta.append(Fakta(_lovfakta(lov), lov_kalla))

    korsjamforelse_text = _korsjamforelsefakta(korsjamforelse)
    if korsjamforelse_text is not None and handling_kalla is not None:
        grund.append(len(fakta))
        fakta.append(Fakta(korsjamforelse_text, handling_kalla))

    grund.append(len(fakta))
    fakta.append(Fakta(_areadeltafakta(delta), byggnad_kalla))

    lage_text = _lagedeltafakta(delta)
    if lage_text is not None:
        grund.append(len(fakta))
        fakta.append(Fakta(lage_text, grans_kalla if grans_kalla is not None else byggnad_kalla))

    grund.append(len(fakta))
    fakta.append(Fakta(_dateringsfakta(datering), tidslinje_kalla))

    regelverks_text = _regelverksfakta(lage)
    if regelverks_text is not None:
        grund.append(len(fakta))
        fakta.append(Fakta(regelverks_text, regelverk_kalla))

    osakerheter = (
        list(datering.anmarkningar)
        + list(lage.matningskritiska)
        + list(lage.atgarder)
        + list(delta.anmarkningar)
        + list(tolkat_anmarkningar)
        + list(extra_osakerheter or [])
    )

    bedomning = Bedomning(
        pastaende=_bedomning_pastaende(lage, delta),
        grund=grund,
        osakerheter=osakerheter,
    )

    fakta.extend(extra_fakta or [])

    return Dossier(rubrik=rubrik, fakta=fakta, bedomningar=[bedomning])

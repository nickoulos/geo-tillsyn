"""Juridisk tidsdimension: ZonAnalys -> Kontext -> regelverk_vid (Spike D).

Sömmen mellan de spatiala fakta som analysis.py löser och den tidsmedvetna
regelmotorn i mcp/mcp-regelverk. Årsgranularitet räcker inte alltid —
ikraftträdandeåret 1975 kan inte avgöras utan månad: flagga, gissa inte.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from geo_tillsyn.analysis import ZonAnalys


def _ladda_regelverk_core():
    """Load Spike D's pure rule engine from mcp/mcp-regelverk (not a package).

    geo-tillsyn is installed editable, so __file__ sits inside the repo and the
    spike directory is reachable relative to it. regelverk_core reads its
    regler.json relative to its own __file__, which this loading preserves.
    """
    fil = Path(__file__).resolve().parents[2] / "mcp" / "mcp-regelverk" / "regelverk_core.py"
    if not fil.exists():
        raise FileNotFoundError(
            f"regelverk_core saknas: {fil} — kör geo-tillsyn från repo-roten "
            "(editable install) så att mcp/mcp-regelverk är nåbar."
        )
    spec = importlib.util.spec_from_file_location("regelverk_core", fil)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


_regelverk = _ladda_regelverk_core()


@dataclass(frozen=True)
class JuridisktLage:
    """The time-aware legal position of one building vs the strandskydd."""

    byggnad_id: str
    byggnads_ar: int | None
    gallde_vid_uppforande: bool | None  # None = cannot be determined from the year
    dispens_kravs_vid_uppforande: bool
    dispens_kravs_idag: bool
    preskriberas: bool
    atgarder: list[str] = field(default_factory=list)


def juridiskt_lage(
    analys: ZonAnalys,
    byggnads_ar: int | None,
    bedomningsdatum: date,
) -> JuridisktLage:
    """Evaluate the strandskydd regime for one building at its construction year.

    Year granularity: the regime is evaluated at both 1 Jan and 31 Dec of
    `byggnads_ar`; if they disagree (the zone entered into force mid-year) the
    answer is None plus an åtgärd asking for the month — flag, don't guess.
    """
    inom_zon = analys.laege in ("inom", "delvis")
    kontext = _regelverk.Kontext(inom_strandskydd=inom_zon)

    idag = _regelverk.regelverk_vid(bedomningsdatum, kontext, bedomningsdatum=bedomningsdatum)
    dispens_idag = idag["strandskydd"]["dispens_kravs"]
    preskriberas = idag["preskription"]["strandskydd_preskriberas"]

    atgarder: list[str] = []
    if byggnads_ar is None:
        gallde = None
        dispens_da = False
        atgarder.append(
            "Byggnadens tillkomstår är inte fastställt (bal_nybyggnadsar saknas) — "
            "datera via ortofoto-tidslinjen innan regelverket vid uppförandet kan avgöras."
        )
    else:
        vid_arets_borjan = _regelverk.regelverk_vid(
            date(byggnads_ar, 1, 1), kontext, bedomningsdatum=bedomningsdatum
        )["strandskydd"]
        vid_arets_slut = _regelverk.regelverk_vid(
            date(byggnads_ar, 12, 31), kontext, bedomningsdatum=bedomningsdatum
        )["strandskydd"]

        if vid_arets_borjan["gallde_vid_datum"] != vid_arets_slut["gallde_vid_datum"]:
            gallde = None
            dispens_da = False
            atgarder.append(
                f"Byggnadsåret {byggnads_ar} är ikraftträdandeår för strandskyddet "
                f"({vid_arets_slut['generellt_fran']}) — månad krävs för att avgöra "
                "vilket regelverk som gällde vid uppförandet."
            )
        else:
            gallde = vid_arets_slut["gallde_vid_datum"]
            dispens_da = vid_arets_slut["dispens_kravs"]

        for nyckel in ("overgangsbestammelser",):
            atgard = _regelverk.regelverk_vid(
                date(byggnads_ar, 12, 31), kontext, bedomningsdatum=bedomningsdatum
            )[nyckel].get("atgard")
            if atgard:
                atgarder.append(atgard)

    return JuridisktLage(
        byggnad_id=analys.byggnad_id,
        byggnads_ar=byggnads_ar,
        gallde_vid_uppforande=gallde,
        dispens_kravs_vid_uppforande=dispens_da,
        dispens_kravs_idag=dispens_idag,
        preskriberas=preskriberas,
        atgarder=atgarder,
    )


@dataclass(frozen=True)
class Fall1Lage:
    """The legal position of one suspected olovligt byggande (Fall 1).

    The construction year is only known as an interval — [sista_ar_utan+1,
    forsta_ar_med] from the ortofoto-tidslinje — so every verdict below is
    evaluated across the whole interval. Where candidate years disagree, we
    flag rather than guess.
    """

    sista_ar_utan: int | None
    forsta_ar_med: int | None
    area_m2: float
    lovbefrielse: str | None
    bygglov_kravdes: bool | None
    rattelse_preskriberad: bool | None
    sanktionsavgift_mojlig: bool | None
    matningskritiskt: bool
    atgarder: list[str] = field(default_factory=list)


def _plus_ar(d: date, ar: int) -> date:
    """`d` plus `ar` years, with the Feb-29 -> Mar-1 fallback for non-leap targets."""
    try:
        return date(d.year + ar, d.month, d.day)
    except ValueError:
        return date(d.year + ar, 3, 1)


def _matchad_lovbefrielse(datum: date, area_m2: float, inom_detaljplan: bool):
    """Return (matched exemption dict or None, list of caps considered)."""
    resultat = _regelverk.regelverk_vid(datum, _regelverk.Kontext(inom_detaljplan=inom_detaljplan))
    caps: list[float] = []
    for e in resultat["lovbefrielser"]:
        cap = (
            e["max_kvm_utom_detaljplan"]
            if (not inom_detaljplan and e.get("max_kvm_utom_detaljplan") is not None)
            else e["max_kvm"]
        )
        caps.append(cap)
        if cap >= area_m2:
            return e, caps
    return None, caps


def _pbl_klockor(
    sista_ar_utan: int | None,
    forsta_ar_med: int,
    bedomningsdatum: date,
) -> tuple[bool | None, bool | None, list[str]]:
    """Both PBL clocks over the completion interval — conservative at the bounds.

    Returns (rattelse_preskriberad, sanktionsavgift_mojlig, atgarder); None
    where the interval straddles a clock's expiry.
    """
    atgarder: list[str] = []
    senaste = date(forsta_ar_med, 12, 31)
    tidigaste = date(sista_ar_utan + 1, 1, 1) if sista_ar_utan is not None else None

    if _plus_ar(senaste, 10) < bedomningsdatum:
        rattelse_preskriberad: bool | None = True
    elif tidigaste is not None and _plus_ar(tidigaste, 10) >= bedomningsdatum:
        rattelse_preskriberad = False
    else:
        rattelse_preskriberad = None
        atgarder.append(
            "PBL 11 kap. 20 §-klockan (10 år) löper ut någonstans inom "
            "dateringsintervallet — konstruktionsåret måste pinpointas för att avgöra "
            "om rättelse är preskriberad."
        )

    if tidigaste is not None and _plus_ar(tidigaste, 5) >= bedomningsdatum:
        sanktionsavgift_mojlig: bool | None = True
    elif _plus_ar(senaste, 5) < bedomningsdatum:
        sanktionsavgift_mojlig = False
    else:
        sanktionsavgift_mojlig = None
        atgarder.append(
            "PBL 11 kap. 58 §-klockan (5 år) löper ut någonstans inom "
            "dateringsintervallet — konstruktionsåret måste pinpointas för att avgöra "
            "om sanktionsavgift fortfarande är möjlig."
        )

    return rattelse_preskriberad, sanktionsavgift_mojlig, atgarder


def fall1_lage(
    area_m2: float,
    sista_ar_utan: int | None,
    forsta_ar_med: int | None,
    bedomningsdatum: date,
    inom_detaljplan: bool = False,
    inom_strandskydd: bool = False,
) -> Fall1Lage:
    """Evaluate an olovligt-byggande suspicion whose byggnadsår is only an interval.

    The construction happened sometime in [sista_ar_utan+1, forsta_ar_med] (the
    ortofoto-tidslinje bracket). Every legal question — bygglovsplikt vid
    uppförande, PBL 11 kap. 20 § rättelse-preskription (10 år), PBL 11 kap. 58 §
    sanktionsavgift (5 år) — is answered across the WHOLE interval; if candidate
    years disagree the answer is None plus an åtgärd, never a guess.
    """
    atgarder: list[str] = []

    if forsta_ar_med is None:
        if inom_strandskydd:
            atgarder.append(
                "Strandskyddstillsyn preskriberas aldrig enligt PBL-klockorna (MÖD 2021:6) "
                "— se Fall 7-analysen för strandskyddsdelen."
            )
        atgarder.append(
            "Byggnadens tillkomstår är inte fastställt — datera via ortofoto-tidslinjen "
            "innan bygglovsplikt och preskription kan avgöras."
        )
        return Fall1Lage(
            sista_ar_utan=sista_ar_utan,
            forsta_ar_med=forsta_ar_med,
            area_m2=area_m2,
            lovbefrielse=None,
            bygglov_kravdes=None,
            rattelse_preskriberad=None,
            sanktionsavgift_mojlig=None,
            matningskritiskt=False,
            atgarder=atgarder,
        )

    if sista_ar_utan is None:
        kandidat_ar = [forsta_ar_med]
        atgarder.append(
            "Nedre gränsen för uppförandeåret är okänd (sista_ar_utan saknas) — "
            "intervallets start kan inte fastställas från ortofoto-tidslinjen."
        )
    else:
        kandidat_ar = list(range(sista_ar_utan + 1, forsta_ar_med + 1))

    verdikter: set[bool] = set()
    matchade_namn: set[str] = set()
    alla_caps: list[float] = []
    for ar in kandidat_ar:
        for datum in (date(ar, 1, 1), date(ar, 12, 31)):
            matchad, caps = _matchad_lovbefrielse(datum, area_m2, inom_detaljplan)
            alla_caps.extend(caps)
            verdikter.add(matchad is None)
            if matchad is not None:
                matchade_namn.add(matchad["namn"])

    if len(verdikter) == 1:
        bygglov_kravdes = next(iter(verdikter))
        lovbefrielse = next(iter(matchade_namn)) if not bygglov_kravdes and matchade_namn else None
    else:
        bygglov_kravdes = None
        lovbefrielse = None
        atgarder.append(
            "Intervallet för uppförandeåret spänner över en regeländring i "
            "bygglovsbefrielserna — konstruktionsåret måste pinpointas innan "
            "bygglovsplikten kan avgöras."
        )

    matningskritiskt = any(abs(area_m2 - cap) <= 2.0 for cap in alla_caps)
    if matningskritiskt:
        atgarder.append(
            "Bedömningen är mätningskritisk — arean ligger nära en tröskel och måste "
            "verifieras genom mätning innan handläggaren lägger fast slutsatsen."
        )

    rattelse_preskriberad, sanktionsavgift_mojlig, klock_atgarder = _pbl_klockor(
        sista_ar_utan, forsta_ar_med, bedomningsdatum
    )
    atgarder.extend(klock_atgarder)

    if inom_strandskydd:
        atgarder.append(
            "Strandskyddstillsyn preskriberas aldrig enligt PBL-klockorna (MÖD 2021:6) "
            "— se Fall 7-analysen för strandskyddsdelen."
        )

    return Fall1Lage(
        sista_ar_utan=sista_ar_utan,
        forsta_ar_med=forsta_ar_med,
        area_m2=area_m2,
        lovbefrielse=lovbefrielse,
        bygglov_kravdes=bygglov_kravdes,
        rattelse_preskriberad=rattelse_preskriberad,
        sanktionsavgift_mojlig=sanktionsavgift_mojlig,
        matningskritiskt=matningskritiskt,
        atgarder=atgarder,
    )


_AREA_BAND_M2 = 2.0
_AVSTAND_BAND_M = 0.5


@dataclass(frozen=True)
class Fall3Lage:
    """The time-aware legal position of a suspected lovavvikelse (Fall 3)."""

    pbl_vid_beslut: str | None
    overgangsregel_tillampad: bool
    tillsyn_lagrum: str | None
    sista_ar_utan: int | None
    forsta_ar_med: int | None
    rattelse_preskriberad: bool | None
    sanktionsavgift_mojlig: bool | None
    matningskritiska: list[str] = field(default_factory=list)
    atgarder: list[str] = field(default_factory=list)


def fall3_lage(
    beslutsdatum: date,
    sista_ar_utan: int | None,
    forsta_ar_med: int | None,
    bedomningsdatum: date,
    delta=None,
) -> Fall3Lage:
    """Evaluate a lovavvikelse suspicion: which law governs the lov, both PBL
    clocks over the completion interval, and which deviations are inside the
    measurement band (and thus cannot be asserted without inmätning).

    Vilken lag som styr lovet är den som gällde vid beslutsdatum; om den eran
    skiljer sig från dagens flaggas övergångsregeln (PBL 2010:900 p. 2).
    """
    atgarder: list[str] = []

    vid_beslut_resultat = _regelverk.regelverk_vid(
        beslutsdatum, _regelverk.Kontext(), bedomningsdatum=bedomningsdatum
    )
    vid_beslut = vid_beslut_resultat["pbl_version"]
    idag = _regelverk.regelverk_vid(
        bedomningsdatum, _regelverk.Kontext(), bedomningsdatum=bedomningsdatum
    )["pbl_version"]
    pbl_vid_beslut = f"{vid_beslut['namn']} (SFS {vid_beslut['sfs']})" if vid_beslut else None
    tillsyn_lagrum = vid_beslut["tillsyn_lagrum"] if vid_beslut else None
    overgang = bool(vid_beslut and idag and vid_beslut["sfs"] != idag["sfs"])

    overgangsbestammelse_atgard = vid_beslut_resultat["overgangsbestammelser"].get("atgard")
    if overgangsbestammelse_atgard:
        atgarder.append(overgangsbestammelse_atgard)

    if forsta_ar_med is None:
        rattelse, sanktion = None, None
        atgarder.append(
            "Färdigställandet är inte daterat — datera via ortofoto-tidslinjen "
            "innan preskriptionsklockorna kan avgöras."
        )
    else:
        rattelse, sanktion, klock_atgarder = _pbl_klockor(
            sista_ar_utan, forsta_ar_med, bedomningsdatum
        )
        atgarder.extend(klock_atgarder)

    matningskritiska: list[str] = []
    if delta is not None:
        if abs(delta.area_diff_m2) <= _AREA_BAND_M2:
            matningskritiska.append(
                f"Areaavvikelsen ({delta.area_diff_m2:+.1f} m²) ligger inom "
                f"mätosäkerheten (±{_AREA_BAND_M2:.0f} m²) — kan inte beläggas utan inmätning."
            )
        if (
            delta.avstand_grans_godkant_m is not None
            and delta.avstand_grans_verklig_m is not None
            and abs(delta.avstand_grans_godkant_m - delta.avstand_grans_verklig_m)
            <= _AVSTAND_BAND_M
        ):
            matningskritiska.append(
                "Skillnaden i avstånd till fastighetsgräns ligger inom mätosäkerheten "
                f"(±{_AVSTAND_BAND_M:.1f} m) — kan inte beläggas utan inmätning."
            )
    if matningskritiska:
        atgarder.append(
            "Bedömningen är mätningskritisk — avvikelser inom mätosäkerheten måste "
            "verifieras genom inmätning innan handläggaren lägger fast slutsatsen."
        )

    return Fall3Lage(
        pbl_vid_beslut=pbl_vid_beslut,
        overgangsregel_tillampad=overgang,
        tillsyn_lagrum=tillsyn_lagrum,
        sista_ar_utan=sista_ar_utan,
        forsta_ar_med=forsta_ar_med,
        rattelse_preskriberad=rattelse,
        sanktionsavgift_mojlig=sanktion,
        matningskritiska=matningskritiska,
        atgarder=atgarder,
    )

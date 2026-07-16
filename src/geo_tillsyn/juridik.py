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

"""Lovarkiv: mock-ByggR-lager med syntetiska bygglovsärenden (Fall 3).

Prototypfasen har ingen åtkomst till riktiga byggärenden (Sokigo Nova kräver
TRIP-avtal) — arkivet håller SYNTETISKA testärenden och vägrar läsa poster som
inte uttryckligen är märkta `syntetisk: true`. Ett saknat lov är ett ärligt
svar (None), aldrig en gissning.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from shapely.geometry import Point, Polygon


@dataclass(frozen=True)
class LovBeslut:
    """One granted (synthetic) bygglov from the mock archive."""

    dnr: str
    fastighet: str
    beslutsdatum: str
    laga_kraft: str | None
    atgard: str
    byggnadsarea_m2: float | None
    hojd_m: float | None
    godkant_lage: Polygon
    villkor: list[str]
    handling: Path | None
    anmarkning: str
    kalla_fil: Path


def _las_record(fil: Path) -> LovBeslut:
    data = json.loads(fil.read_text(encoding="utf-8"))
    if data.get("syntetisk") is not True:
        raise ValueError(
            f"{fil.name}: posten saknar 'syntetisk: true' — arkivet läser enbart "
            "uttryckligen syntetiska testärenden i prototypfasen."
        )
    handling = data.get("handling")
    return LovBeslut(
        dnr=data["dnr"],
        fastighet=data["fastighet"],
        beslutsdatum=data["beslutsdatum"],
        laga_kraft=data.get("laga_kraft"),
        atgard=data["atgard"],
        byggnadsarea_m2=data.get("byggnadsarea_m2"),
        hojd_m=data.get("hojd_m"),
        godkant_lage=Polygon(data["godkant_lage"]["koordinater"]),
        villkor=list(data.get("villkor", [])),
        handling=(fil.parent / handling) if handling else None,
        anmarkning=data.get("anmarkning", ""),
        kalla_fil=fil,
    )


def hitta_lov(
    katalog: Path,
    punkt: tuple[float, float] | None = None,
    fastighet: str | None = None,
    max_avstand_m: float = 100.0,
) -> LovBeslut | None:
    """Find the (nearest) synthetic lov matching a point or a fastighet.

    Returns None when nothing matches — the caller renders that as the honest
    "inget ärende i (test)arkivet", never an invented permit.
    """
    kandidater: list[tuple[float, LovBeslut]] = []
    for fil in sorted(katalog.glob("*.json")):
        lov = _las_record(fil)
        if fastighet is not None and lov.fastighet == fastighet:
            kandidater.append((0.0, lov))
        elif punkt is not None:
            avstand = lov.godkant_lage.distance(Point(punkt))
            if avstand <= max_avstand_m:
                kandidater.append((avstand, lov))
    if not kandidater:
        return None
    return min(kandidater, key=lambda par: par[0])[1]

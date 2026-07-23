"""Delta-motor: kvantifierad avvikelse godkänt läge vs verkligt läge (Fall 3).

Ren geometri (shapely, EPSG:3014): areaskillnad, förskjutning, yta utanför
godkänt läge, avstånd till fastighetsgräns. Motorn kvantifierar — den
kvalificerar aldrig (väsentlig/ringa är handläggarens fråga).

SPDX-License-Identifier: AGPL-3.0-or-later
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from shapely.geometry import Polygon
from shapely.geometry.base import BaseGeometry


@dataclass(frozen=True)
class DeltaResultat:
    godkand_area_m2: float
    verklig_area_m2: float
    area_diff_m2: float
    area_diff_procent: float
    centroid_forskjutning_m: float
    utanfor_godkant_m2: float
    avstand_grans_godkant_m: float | None
    avstand_grans_verklig_m: float | None
    anmarkningar: list[str] = field(default_factory=list)


def jamfor_lage(
    godkant: Polygon,
    verkligt: Polygon,
    granser: list[BaseGeometry] | None = None,
) -> DeltaResultat:
    """Quantify how the actual footprint deviates from the approved one."""
    anmarkningar: list[str] = []

    godkand_area = godkant.area
    verklig_area = verkligt.area
    diff = verklig_area - godkand_area
    procent = (diff / godkand_area * 100.0) if godkand_area else 0.0
    if godkand_area == 0:
        anmarkningar.append(
            "Godkänt läge har ingen mätbar yta — procentjämförelse ej möjlig."
        )

    gc, vc = godkant.centroid, verkligt.centroid
    forskjutning = math.hypot(vc.x - gc.x, vc.y - gc.y)

    utanfor = verkligt.difference(godkant).area

    if granser:
        avstand_godkant = min(godkant.distance(g) for g in granser)
        avstand_verklig = min(verkligt.distance(g) for g in granser)
    else:
        avstand_godkant = avstand_verklig = None
        anmarkningar.append(
            "Ingen fastighetsgräns tillgänglig — avstånd till gräns har inte "
            "kunnat jämföras."
        )

    return DeltaResultat(
        godkand_area_m2=godkand_area,
        verklig_area_m2=verklig_area,
        area_diff_m2=diff,
        area_diff_procent=procent,
        centroid_forskjutning_m=forskjutning,
        utanfor_godkant_m2=utanfor,
        avstand_grans_godkant_m=avstand_godkant,
        avstand_grans_verklig_m=avstand_verklig,
        anmarkningar=anmarkningar,
    )

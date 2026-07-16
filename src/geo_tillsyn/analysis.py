"""Strandskydd intersection analysis: byggnader (REALITY) ∩ strandskyddszoner (RULE).

SPDX-License-Identifier: AGPL-3.0-or-later
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from shapely.geometry import shape
from shapely.ops import unary_union

Laege = Literal["inom", "delvis", "utanfor"]

# Buildings whose area lies inside the zone beyond this share count as fully
# "inom" — guards against float noise at shared boundaries, not a legal margin.
_HELT_INOM_TOLERANS = 1e-9


@dataclass(frozen=True)
class ZonAnalys:
    """Where one building sits relative to the strandskydd zones."""

    byggnad_id: str
    laege: Laege
    andel_inom: float
    avstand_m: float
    zon_referenser: list[str]


def _feature_id(feature: dict[str, Any]) -> str:
    return str(feature.get("id") or feature.get("properties", {}).get("id") or "")


def _zon_referens(feature: dict[str, Any]) -> str:
    props = feature.get("properties") or {}
    return str(props.get("lm_aktbeteckning") or _feature_id(feature))


def analysera_strandskydd(
    byggnader_fc: dict[str, Any],
    strandskydd_fc: dict[str, Any],
) -> list[ZonAnalys]:
    """Classify each building as inom / delvis / utanfor the strandskydd zones.

    Args:
        byggnader_fc: GeoJSON FeatureCollection of building polygons (REALITY),
            as returned by query_wfs_features. Same CRS as strandskydd_fc;
            distances are in that CRS's unit (metres for SWEREF99 zones).
        strandskydd_fc: GeoJSON FeatureCollection of strandskydd polygons (RULE).

    Returns:
        One ZonAnalys per building, in input order. `zon_referenser` carries the
        lm_aktbeteckning (or feature id) of each zone the building touches.
    """
    zoner = [
        (shape(f["geometry"]), _zon_referens(f))
        for f in strandskydd_fc.get("features", [])
        if f.get("geometry")
    ]
    zon_union = unary_union([geom for geom, _ in zoner]) if zoner else None

    analyser: list[ZonAnalys] = []
    for feature in byggnader_fc.get("features", []):
        byggnad = shape(feature["geometry"])

        if zon_union is None or zon_union.is_empty:
            analyser.append(
                ZonAnalys(_feature_id(feature), "utanfor", 0.0, float("inf"), [])
            )
            continue

        andel = byggnad.intersection(zon_union).area / byggnad.area if byggnad.area else 0.0
        if andel >= 1.0 - _HELT_INOM_TOLERANS:
            laege: Laege = "inom"
            andel = 1.0
        elif andel > 0.0:
            laege = "delvis"
        else:
            laege = "utanfor"

        analyser.append(
            ZonAnalys(
                byggnad_id=_feature_id(feature),
                laege=laege,
                andel_inom=andel,
                avstand_m=0.0 if andel > 0.0 else byggnad.distance(zon_union),
                zon_referenser=[ref for geom, ref in zoner if byggnad.intersects(geom)],
            )
        )

    return analyser

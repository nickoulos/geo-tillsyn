"""Ortofoto-tidslinje: samma bbox över alla verifierade årgångar.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol

from mcp_ogc.tools.wms import get_wms_map

# Verified live against karta.sundsvall.se 2026-07-16: all 18 vintages return
# imagery without auth (Lantmäteriet data re-served by the kommun's GeoServer).
ORTOFOTO_LAYERS: dict[int, str] = {
    **{ar: f"Lantmateriet:HistoriskaOrtofoton{ar}_wms" for ar in (1960, 1975, 1998, 1999, 2001, 2002)},
    **{
        ar: f"Lantmateriet:Orto{ar}_wms"
        for ar in (2007, 2010, 2011, 2012, 2013, 2015, 2016, 2017, 2019, 2020, 2021, 2023)
    },
}

# A correctly-fetched ortofoto tile at ~512px is hundreds of KB; axis-order or
# out-of-coverage failures return HTTP 200 with a near-blank PNG of a few KB
# (measured live: 365 KB real vs 5.6 KB blank). Flag, don't guess.
_MISSTANKT_TOM_GRANS = 20_000


class _Hamtare(Protocol):
    def __call__(
        self, wms_url: str, layer: str, bbox: tuple, crs: str, width: int, height: int
    ) -> bytes: ...


@dataclass(frozen=True)
class TidslinjeBild:
    ar: int
    layer: str
    png: bytes
    misstankt_tom: bool


def _standard_hamta(wms_url, layer, bbox, crs, width, height) -> bytes:
    return get_wms_map(wms_url, layer=layer, bbox=bbox, crs=crs, width=width, height=height)


def hamta_tidslinje(
    wms_url: str,
    bbox: tuple[float, float, float, float],
    crs: str = "EPSG:3014",
    width: int = 512,
    height: int = 512,
    ar: list[int] | None = None,
    hamta: Callable | None = None,
) -> list[TidslinjeBild]:
    """Fetch the same bbox across ortofoto vintages, oldest first.

    Args:
        wms_url: WMS endpoint (karta.sundsvall.se GeoServer in the pilot).
        bbox: (minx, miny, maxx, maxy) easting-first — never pre-swap; see
            mcp-ogc's get_wms_map contract.
        crs: CRS of the bbox (default EPSG:3014, the kommun layers' native CRS).
        ar: Years to fetch (default: all in ORTOFOTO_LAYERS). Unknown years raise.
        hamta: Fetch function, injectable for tests (default: mcp-ogc get_wms_map).

    Returns:
        One TidslinjeBild per year, ascending. `misstankt_tom` flags payloads so
        small they are probably blank (silent WMS failure mode) — the caller
        must surface this as uncertainty, not drop the year.
    """
    hamta = hamta or _standard_hamta
    valda_ar = sorted(ar) if ar is not None else sorted(ORTOFOTO_LAYERS)

    bilder: list[TidslinjeBild] = []
    for ett_ar in valda_ar:
        layer = ORTOFOTO_LAYERS[ett_ar]
        png = hamta(wms_url, layer=layer, bbox=bbox, crs=crs, width=width, height=height)
        bilder.append(
            TidslinjeBild(
                ar=ett_ar,
                layer=layer,
                png=png,
                misstankt_tom=len(png) < _MISSTANKT_TOM_GRANS,
            )
        )
    return bilder

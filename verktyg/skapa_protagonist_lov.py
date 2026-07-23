"""Engångsverktyg: skapa protagonistens syntetiska Fall 3-ärende (lov + handling).

Hämtar huvudbyggnadens verkliga footprint (störst inom 100 m från punkten),
härleder ett godkänt läge (skala 0,85 kring centroiden, förskjutet 2,3 m bort
från närmaste fastighetsgräns) och skriver lovarkiv-JSON + skannad handling.
Determinism: samma WFS-svar -> samma filer.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from mcp_ogc.tools.wfs import query_wfs_features
from shapely import affinity
from shapely.geometry import shape

from geo_tillsyn.handling import VATTENMARKE, rita_situationsplan, till_pdf_bytes
from geo_tillsyn.runner import BYGGNAD_LAYER, FASTIGHETSGRANS_LAYER

OWS = "https://karta.sundsvall.se/geoserver/ows"
PUNKT = (158140.4, 6918389.3)  # ALNÖ-USLAND 1:45 (EPSG:3014)
UT = Path(__file__).resolve().parents[1] / "data" / "synthetic" / "lovarkiv"


def main() -> None:
    e, n = PUNKT
    bbox = (e - 100, n - 100, e + 100, n + 100)
    byggnader = query_wfs_features(OWS, BYGGNAD_LAYER, bbox=bbox, max_features=500)
    storst = max(byggnader["features"], key=lambda f: shape(f["geometry"]).area)
    footprint = shape(storst["geometry"])

    granser = query_wfs_features(OWS, FASTIGHETSGRANS_LAYER, bbox=bbox, max_features=200)
    grans_geoms = [shape(f["geometry"]) for f in granser["features"]]
    narmast = min(grans_geoms, key=lambda g: g.distance(footprint))

    godkant = affinity.scale(footprint, 0.85, 0.85, origin="centroid")
    p_grans = narmast.interpolate(narmast.project(footprint.centroid))
    c = footprint.centroid
    langd = math.hypot(c.x - p_grans.x, c.y - p_grans.y) or 1.0
    riktning = ((c.x - p_grans.x) / langd, (c.y - p_grans.y) / langd)
    godkant = affinity.translate(godkant, xoff=riktning[0] * 2.3, yoff=riktning[1] * 2.3)
    godkant = godkant.simplify(0.05)

    area = round(godkant.area, 1)
    koords = [[round(x, 2), round(y, 2)] for x, y in godkant.exterior.coords[:-1]]
    avstand = round(godkant.distance(narmast), 1)

    record = {
        "syntetisk": True,
        "anmarkning": "Syntetiskt testärende — inga verkliga byggärenden (prototypfas).",
        "dnr": "SBN 2009-0412",
        "fastighet": "ALNÖ-USLAND 1:45",
        "beslutsdatum": "2009-06-19",
        "laga_kraft": "2009-07-24",
        "atgard": "Nybyggnad av enbostadshus",
        "byggnadsarea_m2": area,
        "hojd_m": None,
        "godkant_lage": {"crs": "EPSG:3014", "koordinater": koords},
        "villkor": [f"Byggnaden placeras minst {str(avstand).replace('.', ',')} m från fastighetsgräns."],
        "handling": "sbn-2009-0412-situationsplan.pdf",
    }

    UT.mkdir(parents=True, exist_ok=True)
    (UT / "sbn-2009-0412.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    minx = min(k[0] for k in koords)
    miny = min(k[1] for k in koords)
    lokala = [(x - minx, y - miny) for x, y in koords]
    falt = {
        "DNR": "SBN 2009-0412",
        "BESLUTSDATUM": "2009-06-19",
        "BYGGNADSAREA": f"{str(area).replace('.', ',')} m2",
        "AVSTAND TILL GRANS": f"{str(avstand).replace('.', ',')} m",
    }
    pdf = till_pdf_bytes(rita_situationsplan(falt, lokala, VATTENMARKE))
    (UT / "sbn-2009-0412-situationsplan.pdf").write_bytes(pdf)
    print(f"Skrev {UT / 'sbn-2009-0412.json'} (BYA {area} m², avstånd {avstand} m)")


if __name__ == "__main__":
    main()

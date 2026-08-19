"""Spike C — find candidate protagonist properties for the demo.

Strategy: buildings with bal_nybyggnadsar 2008-2020 in three coastal strips,
point-in-polygon checks against strandskydd zones (incl. utvidgat/upphävt),
detaljplan coverage and fastighet lookup.

KEY FINDING baked into this spike (see docs/data-access.md): on
karta.sundsvall.se CQL INTERSECTS/DWITHIN silently match nothing (0 hits even
for a polygon covering all of Sweden). CQL BBOX *does* work, and WMS
**GetFeatureInfo** is a reliable, cheap server-side point-in-polygon that
returns attributes without geometry (with propertyName). All point tests here
use GetFeatureInfo. This constraint must inform mcp-geodata's design.

Throwaway spike code (Prototypmetodik: learn, don't build).

Run:  python find_candidates.py
Out:  out/candidates.json + ranked table on stdout
"""

import json
import os
import time

import requests

OWS = "https://karta.sundsvall.se/geoserver/ows"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")

# Coastal strips, EPSG:3006 (minE, minN, maxE, maxN)
STRIPS = {
    "alno_west": (623500, 6912000, 627500, 6922000),
    "south_coast": (621000, 6903000, 628000, 6909500),
    "north_shore": (621000, 6919000, 626000, 6924000),
}
YEAR_MIN, YEAR_MAX = 2008, 2020
MAX_POINT_CHECKS = 60
SLEEP = 0.12

# layer -> small attribute to request (keeps responses tiny, excludes geometry)
POINT_LAYERS = {
    "strandskydd": ("Lansstyrelsen:Strandskydd_yta", "OBJECTID"),
    "utvidgat": ("Lansstyrelsen:UtvidgatStrandskydd_yta", "OBJECTID"),
    "upphavt": ("Lansstyrelsen:UpphavdaStrandskydd_yta", "Beslutsdat"),
    # STALE layer (kommun, Aug 2026): authoritative gällande plan is
    # NGP_Detaljplan_yta + DetaljplanGallande_minusNGP_yta. Rerun before
    # trusting the detaljplan-coverage score for any new candidate.
    "detaljplan": ("RIGES:DetaljplanGallande_yta", "AKTBET"),
    "fastighet": ("SundsvallsKommun:Fastighet_yta", "FBET"),
}

session = requests.Session()
session.headers["User-Agent"] = "geo-tillsyn-spike-c/0.2 (Govtech4all Pilot 3 prototype)"


def wfs_json(type_name, **extra):
    params = {
        "service": "WFS", "version": "2.0.0", "request": "GetFeature",
        "typeNames": type_name, "outputFormat": "application/json",
        "srsName": "EPSG:3006",
    }
    params.update(extra)
    r = session.get(OWS, params=params, timeout=90)
    r.raise_for_status()
    return r.json()


def point_info(layer, prop, e, n, half=40):
    """Server-side point-in-polygon via WMS GetFeatureInfo (EPSG:3006, axis N,E)."""
    params = {
        "service": "WMS", "version": "1.3.0", "request": "GetFeatureInfo",
        "layers": layer, "query_layers": layer, "crs": "EPSG:3006",
        "bbox": f"{n - half},{e - half},{n + half},{e + half}",
        "width": 81, "height": 81, "i": 40, "j": 40,
        "info_format": "application/json", "propertyName": prop,
        "feature_count": 3,
    }
    r = session.get(OWS, params=params, timeout=60)
    r.raise_for_status()
    feats = r.json().get("features", [])
    return feats[0]["properties"].get(prop) if feats else None


def centroid(geometry):
    coords = geometry["coordinates"]
    ring = coords[0][0] if geometry["type"] == "MultiPolygon" else coords[0]
    xs = [p[0] for p in ring]
    ys = [p[1] for p in ring]
    return sum(xs) / len(xs), sum(ys) / len(ys)


def ring_area_m2(geometry):
    """Shoelace on the exterior ring — building footprint size (approx)."""
    coords = geometry["coordinates"]
    ring = coords[0][0] if geometry["type"] == "MultiPolygon" else coords[0]
    a = 0.0
    for (x1, y1, *_), (x2, y2, *_) in zip(ring, ring[1:]):
        a += x1 * y2 - x2 * y1
    return abs(a) / 2


def main():
    os.makedirs(OUT, exist_ok=True)

    feats, seen = [], set()
    props = "geom,bal_nybyggnadsar,bal_tillbyggnadsar,bal_andamal,bal_huvudbyggnad"
    for name, (e1, n1, e2, n2) in STRIPS.items():
        cql = (f"BBOX(geom,{e1},{n1},{e2},{n2},'EPSG:3006')"
               f" AND bal_nybyggnadsar BETWEEN {YEAR_MIN} AND {YEAR_MAX}")
        data = wfs_json("SundsvallsKommun:bal_byggnad_yta",
                        CQL_FILTER=cql, count=600, propertyName=props)
        got = data.get("features", [])
        print(f"strip {name}: matched {data.get('totalFeatures')} returned {len(got)}")
        for f in got:
            if f["id"] not in seen and f.get("geometry"):
                seen.add(f["id"])
                f["_strip"] = name
                feats.append(f)
        time.sleep(SLEEP)

    # Prefer years that straddle the ortofoto series & preskription edge (2016)
    feats.sort(key=lambda f: abs((f["properties"].get("bal_nybyggnadsar") or 0) - 2015))
    sample = feats[:MAX_POINT_CHECKS]

    print(f"Point-testing {len(sample)} of {len(feats)} buildings (GetFeatureInfo) ...")
    candidates = []
    for i, f in enumerate(sample):
        e, n = centroid(f["geometry"])
        vals = {}
        try:
            for key, (layer, prop) in POINT_LAYERS.items():
                vals[key] = point_info(layer, prop, e, n)
                time.sleep(SLEEP)
        except Exception as exc:
            print(f"  [{i}] point check failed: {exc}")
            continue

        p = f["properties"]
        cand = {
            "building_id": f["id"],
            "strip": f["_strip"],
            "fastighet": vals["fastighet"],
            "nybyggnadsar": p.get("bal_nybyggnadsar"),
            "tillbyggnadsar": p.get("bal_tillbyggnadsar"),
            "andamal": p.get("bal_andamal"),
            "huvudbyggnad": p.get("bal_huvudbyggnad"),
            "footprint_m2": round(ring_area_m2(f["geometry"]), 1),
            "centroid_3006": [round(e, 1), round(n, 1)],
            "in_strandskydd": vals["strandskydd"] is not None,
            "in_utvidgat": vals["utvidgat"] is not None,
            "upphavt_beslutsdat": vals["upphavt"],
            "detaljplan_aktbet": vals["detaljplan"],
        }
        score = 0
        if cand["in_strandskydd"] or cand["in_utvidgat"]:
            score += 5                       # Fall 7 possible
        if cand["upphavt_beslutsdat"]:
            score -= 2                       # zone lifted -> edge case, weaker headline
        if cand["detaljplan_aktbet"]:
            score += 2                       # Fall 1/3 richer inside detaljplan
        yr = cand["nybyggnadsar"] or 0
        if 2012 <= yr <= 2017:
            score += 2                       # appears inside photo series, near preskription edge
        if cand["andamal"] == "Komplementbyggnad":
            score += 1                       # classic friggebod/attefall confusion story
        if 15 <= cand["footprint_m2"] <= 60:
            score += 1                       # attefall-sized -> juicier legal question
        cand["score"] = score
        candidates.append(cand)
        mark = " ***" if score >= 8 else ""
        print(f"  [{i:2d}] {str(cand['fastighet']):22.22s} yr={yr} "
              f"{str(cand['andamal']):18.18s} {cand['footprint_m2']:7.1f}m2 "
              f"ss={int(cand['in_strandskydd'])} ut={int(cand['in_utvidgat'])} "
              f"dp={'y' if cand['detaljplan_aktbet'] else '-'} s={score}{mark}")

    candidates.sort(key=lambda c: -c["score"])
    with open(os.path.join(OUT, "candidates.json"), "w", encoding="utf-8") as fh:
        json.dump(candidates, fh, ensure_ascii=False, indent=2)

    print("\n=== TOP 8 ===")
    for c in candidates[:8]:
        print(f"  score={c['score']:2d}  {str(c['fastighet']):24.24s} yr={c['nybyggnadsar']} "
              f"{c['andamal']} {c['footprint_m2']}m2 ss={c['in_strandskydd']} "
              f"dp={c['detaljplan_aktbet'] or '-'} strip={c['strip']} @ {c['centroid_3006']}")


if __name__ == "__main__":
    main()

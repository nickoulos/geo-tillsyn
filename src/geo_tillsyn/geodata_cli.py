"""CLI: förbered geodata inför demo — ögonblicksbilder + förvärmd cache.

    geo-tillsyn-geodata snapshot            # hela strandskyddslagren lokalt (~20 MB)
    geo-tillsyn-geodata varm E N [E N ...]  # kör alla tre analyserna per punkt så att
                                            # varje WFS-svar ligger i cachen (stale fallback)
    geo-tillsyn-geodata status              # vad finns lokalt, och hur gammalt är det

Körs dagen före demon, och igen på morgonen. Därefter överlever demon att
karta.sundsvall.se svarar med shapefile-fel eller timeout (anbudsfrågor
151260/151373) — och dossiern säger uttryckligen när den lutar sig mot en
ögonblicksbild eller ett cachat svar.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime

from geo_tillsyn import geodata
from geo_tillsyn.runner import analysera_fall1_punkt, analysera_fall3_punkt, analysera_punkt

SUNDSVALL_OWS = "https://karta.sundsvall.se/geoserver/ows"


def _snapshot(args) -> int:
    fel = 0
    for lager in args.lager or geodata.SNAPSHOT_LAGER:
        try:
            fil = geodata.spara_snapshot(args.ows, lager)
        except Exception as exc:  # noqa: BLE001 — rapportera, fortsätt med nästa lager
            print(f"FEL  {lager}: {exc}")
            fel += 1
            continue
        meta = json.loads(fil.read_text(encoding="utf-8")).get("geo_tillsyn_snapshot", {})
        print(f"OK   {lager}: {meta.get('antal')} objekt -> {fil} ({fil.stat().st_size // 1024} kB)")
    return 1 if fel else 0


def _varm(args) -> int:
    if len(args.koordinater) % 2:
        print("ange punkter som par: E N [E N ...]", file=sys.stderr)
        return 2
    nu = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    punkter = list(zip(args.koordinater[::2], args.koordinater[1::2]))
    fel = 0
    for e, n in punkter:
        for namn, fn, radie in (
            ("strandskydd", analysera_punkt, 150.0),
            ("olovligt", analysera_fall1_punkt, 100.0),
            ("lovavvikelse", analysera_fall3_punkt, 100.0),
        ):
            try:
                res = fn(ows_url=args.ows, punkt=(e, n), radie_m=radie, nu=nu)
                kallor = {
                    getattr(o, "kod", "") for o in res.get("osakerheter", [])
                } & {"geodata.snapshot_anvant", "geodata.cache_anvant"}
                print(f"OK   {namn:<13} E {e:.0f} N {n:.0f}" + (f"  [{', '.join(sorted(kallor))}]" if kallor else ""))
            except ValueError as exc:
                # Ärligt "hittades inte" (ingen byggnad/inget lov) — inget fel för cachen.
                print(f"INFO {namn:<13} E {e:.0f} N {n:.0f}: {exc}")
            except Exception as exc:  # noqa: BLE001
                print(f"FEL  {namn:<13} E {e:.0f} N {n:.0f}: {exc}")
                fel += 1
    return 1 if fel else 0


def _status(args) -> int:
    print(f"snapshot-katalog: {geodata.SNAPSHOT_KATALOG}")
    for lager in geodata.SNAPSHOT_LAGER:
        fil = geodata.snapshot_fil(lager)
        if fil.exists():
            meta = json.loads(fil.read_text(encoding="utf-8")).get("geo_tillsyn_snapshot", {})
            print(f"  {lager}: {meta.get('antal')} objekt, hämtad {meta.get('hamtad')}")
        else:
            print(f"  {lager}: SAKNAS (kör `geo-tillsyn-geodata snapshot`)")
    cache = geodata.WFS_CACHE_KATALOG
    antal = len(list(cache.glob("*.json"))) if cache.exists() else 0
    print(f"wfs-cache: {antal} svar i {cache}")
    print(f"offline-läge: {'PÅ' if geodata.OFFLINE else 'av'} (GEO_TILLSYN_OFFLINE)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="geo-tillsyn-geodata", description=__doc__.split("\n\n")[0])
    parser.add_argument("--ows", default=SUNDSVALL_OWS)
    sub = parser.add_subparsers(dest="kommando", required=True)

    p_snap = sub.add_parser("snapshot", help="spara hela lager lokalt")
    p_snap.add_argument("lager", nargs="*", help=f"lagernamn (standard: {', '.join(geodata.SNAPSHOT_LAGER)})")
    p_snap.set_defaults(fn=_snapshot)

    p_varm = sub.add_parser("varm", help="förvärm WFS-cachen för givna punkter (EPSG:3014)")
    p_varm.add_argument("koordinater", type=float, nargs="+", metavar="E_N")
    p_varm.set_defaults(fn=_varm)

    p_status = sub.add_parser("status", help="visa lokalt läge")
    p_status.set_defaults(fn=_status)

    args = parser.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())

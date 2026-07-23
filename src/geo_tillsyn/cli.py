"""CLI: kör Fall 7-skivan runt en kartpunkt.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path

from geo_tillsyn.runner import kor_fall1, kor_fall3, kor_fall7

SUNDSVALL_OWS = "https://karta.sundsvall.se/geoserver/ows"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="geo-tillsyn",
        description="Fall 7 strandskydd: punkt -> spårbar dossier + ortofoto-tidslinje.",
    )
    parser.add_argument("easting", type=float, help="E-koordinat (EPSG:3014)")
    parser.add_argument("northing", type=float, help="N-koordinat (EPSG:3014)")
    parser.add_argument("--radie", type=float, default=250.0, help="sökradie i meter")
    parser.add_argument("--ut", type=Path, default=Path("dossier_ut"), help="utkatalog")
    parser.add_argument("--ows", default=SUNDSVALL_OWS, help="GeoServer OWS-endpoint")
    parser.add_argument(
        "--ar", type=int, nargs="*", default=None, help="ortofoto-år (standard: alla 18)"
    )
    parser.add_argument(
        "--fall",
        type=int,
        choices=[7, 1, 3],
        default=7,
        help=(
            "fall 7 (strandskydd, standard), fall 1 (olovligt byggande) "
            "eller fall 3 (lovavvikelse)"
        ),
    )
    args = parser.parse_args(argv)

    nu = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    if args.fall == 1:
        dossier = kor_fall1(
            ows_url=args.ows,
            punkt=(args.easting, args.northing),
            ut_katalog=args.ut,
            nu=nu,
            radie_m=args.radie,
            ar=args.ar,
        )
    elif args.fall == 3:
        dossier = kor_fall3(
            ows_url=args.ows,
            punkt=(args.easting, args.northing),
            ut_katalog=args.ut,
            nu=nu,
            radie_m=args.radie,
            ar=args.ar,
        )
    else:
        dossier = kor_fall7(
            ows_url=args.ows,
            punkt=(args.easting, args.northing),
            radie_m=args.radie,
            ut_katalog=args.ut,
            nu=nu,
            ar=args.ar,
        )
    print(f"Dossier: {dossier}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

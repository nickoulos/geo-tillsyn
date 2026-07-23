"""geo-tillsyn MCP server — Fall 7-verktygen för Eneo-assistenten.

Eneo talar Streamable HTTP (inte stdio) och trunkerar verktygssvar vid 8 kB —
verktygen returnerar kompakt JSON med referenser, aldrig geometri eller bilder
(docs/spike-a-eneo-findings.md). Beslutet fattas alltid av handläggaren.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from geo_tillsyn.runner import (
    analysera_fall1_punkt,
    analysera_fall3_punkt,
    analysera_punkt,
    kor_fall7,
)

SUNDSVALL_OWS = "https://karta.sundsvall.se/geoserver/ows"

# Eneo's backend runs in Docker and reaches this server via host.docker.internal;
# FastMCP's default DNS-rebinding allowlist is localhost-only and answers such
# requests with 421 Misdirected Request. Keep the protection, widen the allowlist.
mcp = FastMCP(
    "geo-tillsyn",
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=["127.0.0.1:*", "localhost:*", "[::1]:*", "host.docker.internal:*"],
        allowed_origins=[
            "http://127.0.0.1:*",
            "http://localhost:*",
            "http://[::1]:*",
            "http://host.docker.internal:*",
        ],
    ),
)


def _nu() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


@mcp.tool()
def analysera_strandskydd_vid_punkt(
    easting: float,
    northing: float,
    radie_m: float = 150.0,
) -> dict:
    """Analysera strandskyddsläget runt en kartpunkt (Fall 7).

    Korsar byggnader (bal_byggnad_yta) med strandskyddszoner (lm_strandskydd_y)
    och bedömer det tidsmedvetna rättsläget per byggnad: gällde strandskyddet
    när byggnaden uppfördes (zon från 1975-07-01), krävs dispens idag, och att
    strandskyddstillsyn aldrig preskriberas — alltid med skälighetsförbehållet.
    Osäkerheter deklareras uttryckligen; systemet bedömer, handläggaren beslutar.

    Args:
        easting: E-koordinat i EPSG:3014 (SWEREF99 17 15, kommunlagrens CRS).
        northing: N-koordinat i EPSG:3014.
        radie_m: Sökradie i meter runt punkten (standard 150).

    Returns:
        Kompakt JSON: träffar med juridiskt läge, osäkerheter och käll-URL:er.
    """
    return analysera_punkt(
        ows_url=SUNDSVALL_OWS,
        punkt=(easting, northing),
        radie_m=radie_m,
        nu=_nu(),
    )


@mcp.tool()
def generera_dossier(
    easting: float,
    northing: float,
    radie_m: float = 150.0,
    ut_katalog: str = "dossier_ut",
    ortofoto_ar: list[int] | None = None,
) -> dict:
    """Generera den fullständiga tre-nivå-dossieren + ortofoto-tidslinje på disk.

    Skriver dossier.md (Fakta med klickbara källor / Bedömning med osäkerheter /
    Beslut — alltid tomt, handläggarens) samt tidslinje-PNG:er. Returnerar
    sökvägar och en kompakt sammanfattning — aldrig bildinnehåll.

    Args:
        easting: E-koordinat i EPSG:3014.
        northing: N-koordinat i EPSG:3014.
        radie_m: Sökradie i meter (standard 150).
        ut_katalog: Katalog dossier + tidslinje skrivs till.
        ortofoto_ar: Valfria årgångar (standard: alla 18 verifierade 1960-2023).

    Returns:
        {"dossier": sökväg, "tidslinje": [{"ar", "fil", "misstankt_tom"}, ...]}
    """
    ut = Path(ut_katalog)
    dossier_fil = kor_fall7(
        ows_url=SUNDSVALL_OWS,
        punkt=(easting, northing),
        radie_m=radie_m,
        ut_katalog=ut,
        nu=_nu(),
        ar=ortofoto_ar,
    )
    tidslinje = sorted((ut / "tidslinje").glob("ortofoto_*.png"))
    # The directory may hold vintages from earlier runs — report only this call's.
    if ortofoto_ar is not None:
        tidslinje = [f for f in tidslinje if int(f.stem.split("_")[1]) in ortofoto_ar]
    return {
        "dossier": str(dossier_fil),
        "tidslinje": [
            {
                "ar": int(fil.stem.split("_")[1]),
                "fil": str(fil),
                "misstankt_tom": fil.stat().st_size < 20_000,
            }
            for fil in tidslinje
        ],
    }


@mcp.tool()
def analysera_olovligt_byggande_vid_punkt(
    easting: float,
    northing: float,
    radie_m: float = 100.0,
) -> dict:
    """Analysera misstänkt olovligt byggande vid en kartpunkt (Fall 1).

    Daterar närmaste byggnad via ortofoto-tidslinjen (intervall, aldrig
    gissning), jämför mot byggnadsregistrets nybyggnadsår, bedömer
    bygglovsplikten vid uppförandet och PBL-klockorna (11 kap. 20 §
    rättelse-preskription, 11 kap. 58 § sanktionsavgift). Systemet gör en
    bedömning — beslutet fattas av handläggaren.

    Args:
        easting: E-koordinat i EPSG:3014 (SWEREF99 17 15, kommunlagrens CRS).
        northing: N-koordinat i EPSG:3014.
        radie_m: Sökradie i meter runt punkten (standard 100).

    Returns:
        Kompakt JSON: datering, BAL-jämförelse, bygglovsplikt, PBL-klockor,
        osäkerheter och käll-URL:er.
    """
    return analysera_fall1_punkt(
        ows_url=SUNDSVALL_OWS,
        punkt=(easting, northing),
        nu=_nu(),
        radie_m=radie_m,
    )


@mcp.tool()
def analysera_lovavvikelse_vid_punkt(
    easting: float,
    northing: float,
    radie_m: float = 100.0,
) -> dict:
    """Analysera avvikelse från beviljat bygglov vid en kartpunkt (Fall 3).

    Hämtar (syntetiskt) lov ur testarkivet, korskontrollerar den skannade
    handlingen (OCR) mot registerposten, kvantifierar avvikelsen mellan
    godkänt och verkligt läge (area, placering, avstånd till gräns), daterar
    färdigställandet via ortofoto-tidslinjen och bedömer PBL-klockorna.
    Vilken lag som styr lovet avgörs av ärendets start (ÄPBL före 2011-05-02).
    Lovuppgifterna kommer ur ett SYNTETISKT testarkiv — prototypfasen har
    ingen åtkomst till kommunens ärendesystem. Systemet gör en bedömning —
    beslutet fattas av handläggaren.

    Args:
        easting: E-koordinat i EPSG:3014 (SWEREF99 17 15, kommunlagrens CRS).
        northing: N-koordinat i EPSG:3014.
        radie_m: Sökradie i meter runt punkten (standard 100).

    Returns:
        Kompakt JSON: lov, korskontroll, kvantifierad avvikelse, klockor,
        osäkerheter och käll-URL:er.
    """
    return analysera_fall3_punkt(
        ows_url=SUNDSVALL_OWS,
        punkt=(easting, northing),
        nu=_nu(),
        radie_m=radie_m,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="geo-tillsyn-mcp",
        description="Geo-Tillsyn MCP server (Streamable HTTP för Eneo).",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8464)
    parser.add_argument(
        "--transport",
        choices=["streamable-http", "stdio"],
        default="streamable-http",
        help="Eneo kräver streamable-http; stdio för lokala klienter.",
    )
    args = parser.parse_args(argv)

    mcp.settings.host = args.host
    mcp.settings.port = args.port
    mcp.run(transport=args.transport)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

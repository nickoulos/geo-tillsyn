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
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from geo_tillsyn.meddelanden import Meddelande
from geo_tillsyn.meddelanden import Meddelande as M
from geo_tillsyn.meddelanden import till_json
from geo_tillsyn import snedbild
from geo_tillsyn.radar import skanna_zon
from geo_tillsyn.runner import (
    analysera_fall1_punkt,
    analysera_fall3_punkt,
    analysera_punkt,
    fall3_geometri,
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
    Vilken lag som styr lovet är den som gällde vid beslutsdatum (ÄPBL för
    lov beslutade före 2011-05-02).
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


@mcp.tool()
def hamta_snedbilder_vid_punkt(
    easting: float,
    northing: float,
    ut_katalog: str = "dossier_ut/snedbilder",
    datum: str | None = None,
) -> dict:
    """Hämta snedbilder (oblique, MapSpace) över en kartpunkt och spara dem på disk.

    Snedbilder visar fasader — det flygfoton inte gör — och är handläggarens
    underlag för att själv granska höjd och utseende mot lovet (Fall 3) eller
    en byggnads karaktär (Fall 1/5). Bästa bilden per riktning (N/E/S/W) sys
    ihop till en PNG med punkten markerad. Ingen automatisk mätning görs.
    Kommunens MapSpace-userkey (upphandlingsfråga F5/7a) läses ur miljön och
    lämnar aldrig servern.

    Args:
        easting: E-koordinat i EPSG:3014.
        northing: N-koordinat i EPSG:3014.
        ut_katalog: Katalog PNG:erna skrivs till.
        datum: Valfritt YYYY eller YYYYMMDD — senaste bild före det datumet
            (tidsdimension: t.ex. 2019 ger 2018-års bilder).

    Returns:
        {"tillganglig": bool, "bilder": [{"riktning", "datum", "fil"}], "ar",
         "viewer_url"} — sökvägar och referenser, aldrig bildinnehåll.
    """
    oversikt = snedbild.snedbilder_vid_punkt(easting, northing, datum=datum)
    if not oversikt.get("tillganglig"):
        return oversikt
    ut = Path(ut_katalog)
    ut.mkdir(parents=True, exist_ok=True)
    nyckel = snedbild.userkey()
    bilder = []
    for b in oversikt["bilder"]:
        try:
            png = snedbild.hamta_utsnitt(snedbild.bild_fran_dict(b), nyckel)
        except Exception:  # noqa: BLE001 — en riktning som fallerar tar inte de andra
            continue
        fil = ut / f"snedbild_{b['riktning']}_{b['datum']}.png"
        fil.write_bytes(png)
        bilder.append({"riktning": b["riktning"], "datum": b["datum"], "fil": str(fil)})
    return {
        "tillganglig": bool(bilder),
        "bilder": bilder,
        "ar": oversikt.get("ar", []),
        "viewer_url": oversikt.get("viewer_url"),
        "kalla": oversikt.get("kalla"),
    }


@mcp.tool()
def skanna_strandskyddszon(
    min_easting: float,
    min_northing: float,
    max_easting: float,
    max_northing: float,
    max_kandidater: int = 15,
) -> dict:
    """Tillsynsradar: skanna en hel zon och rangordna kandidater (Fall 7, upptäckt).

    I stället för en klickad punkt: alla byggnader i rutan korsas med
    strandskyddszonerna, bedöms tidsmedvetet (gällde strandskyddet när de
    uppfördes?) och poängsätts enligt en öppen, redovisad modell. Resultatet
    är en kandidatlista för granskning — inte beslut, inte påståenden om
    överträdelse. Dispenser kontrolleras inte. Handläggaren beslutar, alltid.

    Args:
        min_easting: Rutans västra kant i EPSG:3014.
        min_northing: Rutans södra kant i EPSG:3014.
        max_easting: Rutans östra kant i EPSG:3014.
        max_northing: Rutans norra kant i EPSG:3014.
        max_kandidater: Högsta antal kandidater i svaret (standard 15 — Eneo
            trunkerar vid 8 kB; trunkering deklareras i svaret).

    Returns:
        Kompakt JSON: kandidater (rang, byggnad_id, fastighet, centroid, läge,
        regim vid uppförandet, poäng + grunder), poängmodell, osäkerheter,
        käll-URL:er. Aldrig geometri utöver centroider.
    """
    return skanna_zon(
        ows_url=SUNDSVALL_OWS,
        bbox=(min_easting, min_northing, max_easting, max_northing),
        nu=_nu(),
        max_kandidater=max_kandidater,
    )


def _json(data: dict, status: int = 200) -> JSONResponse:
    """Bygg ett JSONResponse med permissiv CORS (Origo-pluginet är cross-origin).

    `till_json` byter varje Meddelande mot {"kod", "params"} så att pluginet kan
    rendera det på svenska eller engelska; MCP-verktygen får samma dict med
    meddelandena kvar som svensk text (str-subklassen serialiseras som sträng).
    """
    return JSONResponse(
        till_json(data), status_code=status, headers={"Access-Control-Allow-Origin": "*"}
    )


def _fel(exc: Exception) -> Meddelande | str:
    """Plocka fram ett ValueErrors Meddelande om det bär ett, annars dess text."""
    argument = exc.args[0] if exc.args else None
    return argument if isinstance(argument, Meddelande) else str(exc)


def _cors_preflight() -> Response:
    """Svara på CORS-preflight (OPTIONS) för /api/*-rutterna."""
    return Response(
        status_code=204,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        },
    )


def _parsa_punkt(request: Request) -> tuple[float, float, float | None]:
    """Läs easting/northing/radie_m ur query-strängen; kastar ValueError vid fel."""
    try:
        easting = float(request.query_params["easting"])
        northing = float(request.query_params["northing"])
    except (KeyError, ValueError) as exc:
        raise ValueError(M("server.parametrar_ogiltiga", detalj=str(exc))) from exc

    radie_raw = request.query_params.get("radie_m")
    radie_m = float(radie_raw) if radie_raw is not None else None
    return easting, northing, radie_m


async def _hantera_analys(request: Request, analysfunktion, default_radie: float) -> Response:
    """Gemensam hantering av GET/OPTIONS för de tre analys-endpointen.

    Parsar easting/northing/radie_m, anropar `analysfunktion`, och mappar fel
    till 400 (dåliga query-parametrar), 404 (ValueError — ingen byggnad/lov
    hittad, ett ärligt "hittades inte"-svar) respektive 500 (oväntat fel).
    """
    if request.method == "OPTIONS":
        return _cors_preflight()

    try:
        easting, northing, radie_m = _parsa_punkt(request)
    except ValueError as exc:
        return _json({"fel": _fel(exc)}, status=400)

    try:
        resultat = analysfunktion(
            ows_url=SUNDSVALL_OWS,
            punkt=(easting, northing),
            radie_m=radie_m if radie_m is not None else default_radie,
            nu=_nu(),
        )
    except ValueError as exc:
        return _json({"fel": _fel(exc)}, status=404)
    except Exception:
        return _json({"fel": M("server.internt_fel")}, status=500)

    return _json(resultat)


@mcp.custom_route("/api/strandskydd", methods=["GET", "OPTIONS"])
async def api_strandskydd(request: Request) -> Response:
    """REST-motsvarighet till analysera_strandskydd_vid_punkt (Fall 7), för Origo."""
    return await _hantera_analys(request, analysera_punkt, default_radie=150.0)


@mcp.custom_route("/api/olovligt", methods=["GET", "OPTIONS"])
async def api_olovligt(request: Request) -> Response:
    """REST-motsvarighet till analysera_olovligt_byggande_vid_punkt (Fall 1), för Origo."""
    return await _hantera_analys(request, analysera_fall1_punkt, default_radie=100.0)


@mcp.custom_route("/api/lovavvikelse", methods=["GET", "OPTIONS"])
async def api_lovavvikelse(request: Request) -> Response:
    """REST-motsvarighet till analysera_lovavvikelse_vid_punkt (Fall 3), för Origo."""
    return await _hantera_analys(request, analysera_fall3_punkt, default_radie=100.0)


@mcp.custom_route("/api/lovavvikelse/geometri", methods=["GET", "OPTIONS"])
async def api_lovavvikelse_geometri(request: Request) -> Response:
    """Godkänt/verkligt läge som GeoJSON (EPSG:3014) för Fall 3-overlay på kartan."""
    if request.method == "OPTIONS":
        return _cors_preflight()

    try:
        easting, northing, radie_m = _parsa_punkt(request)
    except ValueError as exc:
        return _json({"fel": _fel(exc)}, status=400)

    try:
        resultat = fall3_geometri(
            ows_url=SUNDSVALL_OWS,
            punkt=(easting, northing),
            radie_m=radie_m if radie_m is not None else 100.0,
            nu=_nu(),
        )
    except ValueError as exc:
        return _json({"fel": _fel(exc)}, status=404)
    except Exception:
        return _json({"fel": M("server.internt_fel")}, status=500)

    return _json(resultat)


@mcp.custom_route("/api/snedbild", methods=["GET", "OPTIONS"])
async def api_snedbild(request: Request) -> Response:
    """Vilka snedbilder (riktning/datum) finns över punkten + visarlänk — för Origo-panelen."""
    if request.method == "OPTIONS":
        return _cors_preflight()
    try:
        easting, northing, _radie = _parsa_punkt(request)
    except ValueError as exc:
        return _json({"fel": _fel(exc)}, status=400)
    datum = request.query_params.get("datum") or None
    try:
        oversikt = snedbild.snedbilder_vid_punkt(easting, northing, datum=datum)
    except Exception:
        return _json({"fel": M("server.internt_fel")}, status=500)
    # Pluginet behöver bara riktning/datum — position/storlek är serverns sak.
    if oversikt.get("tillganglig"):
        oversikt = {
            **oversikt,
            "bilder": [
                {k: b[k] for k in ("riktning", "datum", "copyright")} for b in oversikt["bilder"]
            ],
        }
    return _json(oversikt)


@mcp.custom_route("/api/snedbild/bild", methods=["GET", "OPTIONS"])
async def api_snedbild_bild(request: Request) -> Response:
    """PNG-utsnitt (punkten markerad) för en riktning — nyckeln stannar på servern."""
    if request.method == "OPTIONS":
        return _cors_preflight()
    try:
        easting, northing, _radie = _parsa_punkt(request)
    except ValueError as exc:
        return _json({"fel": _fel(exc)}, status=400)
    riktning = (request.query_params.get("riktning") or "N").upper()
    datum = request.query_params.get("datum") or None
    zoom_raw = request.query_params.get("zoom")
    zoom = int(zoom_raw) if zoom_raw else None
    try:
        png = snedbild.utsnitt_vid_punkt(easting, northing, riktning, datum=datum, zoom=zoom)
    except Exception:
        return _json({"fel": M("server.internt_fel")}, status=500)
    if png is None:
        return _json({"fel": M("runner.snedbilder_otillgangliga")}, status=404)
    return Response(
        png,
        media_type="image/png",
        headers={"Access-Control-Allow-Origin": "*", "Cache-Control": "public, max-age=3600"},
    )


def _parsa_bbox(request: Request) -> tuple[float, float, float, float]:
    """Läs bbox=minE,minN,maxE,maxN (EPSG:3014) ur query-strängen; ValueError vid fel."""
    raw = request.query_params.get("bbox")
    try:
        delar = [float(v) for v in (raw or "").split(",")]
        if len(delar) != 4:
            raise ValueError(f"förväntade 4 tal, fick {len(delar)}")
    except ValueError as exc:
        raise ValueError(M("server.bbox_ogiltig", detalj=str(exc))) from exc
    return delar[0], delar[1], delar[2], delar[3]


@mcp.custom_route("/api/radar", methods=["GET", "OPTIONS"])
async def api_radar(request: Request) -> Response:
    """REST-motsvarighet till skanna_strandskyddszon (tillsynsradar), för Origo."""
    if request.method == "OPTIONS":
        return _cors_preflight()
    try:
        bbox = _parsa_bbox(request)
    except ValueError as exc:
        return _json({"fel": _fel(exc)}, status=400)
    max_raw = request.query_params.get("max_kandidater")
    try:
        resultat = skanna_zon(
            ows_url=SUNDSVALL_OWS,
            bbox=bbox,
            nu=_nu(),
            max_kandidater=int(max_raw) if max_raw else 25,
        )
    except ValueError as exc:
        # För stor zon / ogiltig ruta: ett deklarerat nej, inte ett serverfel.
        return _json({"fel": _fel(exc)}, status=400)
    except Exception:
        return _json({"fel": M("server.internt_fel")}, status=500)
    return _json(resultat)


@mcp.custom_route("/api/health", methods=["GET", "OPTIONS"])
async def api_health(request: Request) -> Response:
    """Enkel hälsokontroll: bekräftar hur många MCP-verktyg som är registrerade."""
    if request.method == "OPTIONS":
        return _cors_preflight()
    return _json({"status": "ok", "tools": len(await mcp.list_tools())})


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

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
    crs = data["godkant_lage"].get("crs")
    if crs is not None and crs != "EPSG:3014":
        raise ValueError(
            f"{fil.name}: godkant_lage har crs {crs!r}, förväntat EPSG:3014 — "
            "felaktig CRS ger tyst kilometerskaliga fel (axelordnings-fällan i EPSG:3006)."
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


# --- ByggR-kompatibel yta (Sokigo/Tekis ArendeExportWS) -----------------------
#
# Kommunen skickade 2026-08-19 fältbeskrivning + metodlista för den verkliga
# exporttjänsten (docs/byggr-arendeexportws.md). Funktionerna nedan exponerar
# SAMMA nycklar och fältnamn över de syntetiska posterna, så att en framtida
# koppling blir ett byte av datakälla — inte av gränssnitt:
#
#   GetRelateradeArendenByFastighet(fnr, trakt, fBetNr, arHuvudObjekt, status)
#       -> hamta_arenden_by_fastighet(katalog, trakt, fbetnr, status)
#   GetDocument(documentId, inkluderaFil, docSplitToken)
#       -> get_document(katalog, handling_id, inkludera_fil)
#
# Det verkliga `arende`-objektet bär INTE beslutets sakinnehåll (laga kraft,
# BYA, höjd, godkänt läge) — det ligger i handlingarna. Mocken behåller därför
# de uppgifterna under `_geoTillsynMock`, tydligt markerat, så att ingen
# förväxlar dem med fält som tjänsten levererar.

import re
import zlib

_TRAKT_NR_RE = re.compile(r"^(?P<trakt>.+?)\s+(?P<nr>\d+:\d+)$")


def dela_fastighetsbeteckning(beteckning: str) -> tuple[str, str]:
    """'ALNÖ-USLAND 1:45' -> ('ALNÖ-USLAND', '1:45') — tjänstens nyckelform."""
    m = _TRAKT_NR_RE.match(" ".join(beteckning.split()).upper())
    if not m:
        raise ValueError(
            f"{beteckning!r}: förväntade 'TRAKT registernummer' (t.ex. 'ALNÖ-USLAND 1:45')"
        )
    return m.group("trakt"), m.group("nr")


def _arende_id(dnr: str) -> int:
    """Stabilt heltals-id per dnr (tjänsten har ett internt int-id)."""
    return zlib.crc32(dnr.encode("utf-8")) & 0x7FFFFFFF


def _handling_id(lov: LovBeslut) -> str:
    return f"{lov.kalla_fil.stem}/{lov.handling.name}" if lov.handling else ""


def _till_tekis_arende(lov: LovBeslut) -> dict:
    trakt, nr = dela_fastighetsbeteckning(lov.fastighet)
    prefix, _, _rest = lov.dnr.partition(" ")
    handelser: list[dict] = []
    if lov.handling is not None:
        handelser.append(
            {
                "handelsetyp": "Beslut",
                "datum": lov.beslutsdatum,
                "rubrik": "Bygglov beviljat",
                "handlingLista": [
                    {
                        "handlingId": _handling_id(lov),
                        "typ": "Situationsplan",
                        "namn": lov.handling.name,
                        "beskrivning": "Godkänd situationsplan (syntetisk)",
                    }
                ],
            }
        )
    return {
        "arendeId": _arende_id(lov.dnr),
        "dnr": lov.dnr,
        "diarieprefix": prefix,
        "arendetyp": "Bygglov",
        "arendeslag": lov.atgard,
        "arendeklass": None,
        "arendegrupp": "BYGG",
        "beskrivning": lov.atgard,
        "status": {"namn": "Beslutat"},
        "registreradDatum": None,
        "ankomstDatum": None,
        "slutDatum": lov.beslutsdatum,
        "makulerDatum": None,
        "handlaggare": None,
        "handelseLista": handelser,
        "intressentLista": [],
        "objektLista": [
            {"typ": "Fastighet", "trakt": trakt, "fBetNr": nr, "beteckning": lov.fastighet}
        ],
        "kalla": "geo-tillsyn syntetiskt lovarkiv",
        "_geoTillsynMock": {
            "syntetisk": True,
            "anmarkning": lov.anmarkning,
            "laga_kraft": lov.laga_kraft,
            "byggnadsarea_m2": lov.byggnadsarea_m2,
            "hojd_m": lov.hojd_m,
            "villkor": list(lov.villkor),
            "kalla_fil": lov.kalla_fil.name,
        },
    }


def _alla_lov(katalog: Path) -> list[LovBeslut]:
    return [_las_record(fil) for fil in sorted(katalog.glob("*.json"))]


def hamta_arenden_by_fastighet(
    katalog: Path,
    trakt: str,
    fbetnr: str,
    status: str = "Aktiv",
) -> list[dict]:
    """Mock av GetRelateradeArendenByFastighet — ärenden för trakt + registernummer.

    `status` tas emot för signaturkompatibilitet (tjänstens StatusFilter);
    testarkivet innehåller enbart beslutade ärenden och filtrerar inte.
    """
    vill = (" ".join(trakt.split()).upper(), fbetnr.strip())
    return [
        _till_tekis_arende(lov)
        for lov in _alla_lov(katalog)
        if dela_fastighetsbeteckning(lov.fastighet) == vill
    ]


def get_document(katalog: Path, handling_id: str, inkludera_fil: bool = True) -> dict | None:
    """Mock av GetDocument — {namn, beskrivning, fil: {filBuffer: bytes} | None}."""
    for lov in _alla_lov(katalog):
        if lov.handling is None or _handling_id(lov) != handling_id:
            continue
        return {
            "handlingId": handling_id,
            "namn": lov.handling.name,
            "beskrivning": f"Godkänd situationsplan, {lov.dnr} (syntetisk)",
            "fil": {"filBuffer": lov.handling.read_bytes()} if inkludera_fil else None,
        }
    return None

"""Snedbilder (oblique imagery) via MapSpace — kommunens userkey, REST-API:t.

Anbudsunderlaget (Geodata i pilot3.xlsx) pekar på MapSpace med kommunens
userkey (Q&A F5/7a). MapSpace har förutom visaren ett lågnivå-HTTP-API
(`/mapSvcs/*`, dokumenterat under your.mapspace.com/svcs/):

- `SEOblique?x&y&crs&view=*&output=json`  → bästa bilden per riktning N/S/E/W,
  med bildens id (`N+017.404731_62.371189_180727` = riktning, lon, lat, YYMMDD),
  pixelpositionen för punkten och bildens storlek.
- `DAObliqueTile?id&meshid=Z_Y_X`        → 256×256-JPEG-tiles; zoom 1 = full
  upplösning, 2/3/4 = halv/fjärdedels/åttondels.
- `date=YYYY` väljer senaste bild före det datumet → tidsdimension även här.

Verifierat live 2026-08-19 mot Alnö-punkten: Blom-bilder 2018 och 2022, alla
fyra riktningarna. Nyckeln läses ur miljövariabeln MAPSPACE_USERKEY (eller
repo-rotens .env) och lämnar aldrig servern: pluginet får färdiga PNG:er via
/api/snedbild/bild, inte nyckeln.

Prototypförbehåll: snedbilderna är underlag för handläggarens egen
granskning av höjd och utseende — ingen automatisk mätning görs här.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

from __future__ import annotations

import io
import json
import os
from concurrent.futures import ThreadPoolExecutor
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlencode

from PIL import Image, ImageDraw

MAPSPACE_BAS = "https://your.mapspace.com"
RIKTNINGAR = ("N", "E", "S", "W")
TILE_PX = 256
TIMEOUT_S = 20.0

_ROT = Path(__file__).resolve().parents[2]


def userkey() -> str | None:
    """MAPSPACE_USERKEY ur miljön, annars ur repo-rotens .env (gitignorerad)."""
    nyckel = os.environ.get("MAPSPACE_USERKEY", "").strip()
    if nyckel:
        return nyckel
    env = _ROT / ".env"
    if env.exists():
        for rad in env.read_text(encoding="utf-8").splitlines():
            rad = rad.strip()
            if rad.startswith("MAPSPACE_USERKEY="):
                varde = rad.split("=", 1)[1].strip().strip('"').strip("'")
                return varde or None
    return None


def _hamta(url: str, timeout: float = TIMEOUT_S) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "geo-tillsyn/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return resp.read()


@dataclass(frozen=True)
class Snedbild:
    """Metadata för den bästa snedbilden i en riktning över en punkt."""

    riktning: str  # N/E/S/W
    id: str
    datum: str  # ISO YYYY-MM-DD ur bild-id:t
    position_x: float  # punktens pixel i originalbilden
    position_y: float
    kolumner: int
    rader: int
    copyright: str

    @property
    def ar(self) -> int:
        return int(self.datum[:4])


def _datum_ur_id(bild_id: str) -> str:
    """`N+017.404731_62.371189_180727` → '2018-07-27'."""
    yymmdd = bild_id.rsplit("_", 1)[-1]
    if len(yymmdd) == 6 and yymmdd.isdigit():
        return f"20{yymmdd[:2]}-{yymmdd[2:4]}-{yymmdd[4:]}"
    return ""


def _tolka_seoblique(data: bytes) -> list[dict[str, Any]]:
    """SEOblique ger en lista av {"metadata": {...}} för view=*, ett objekt för en riktning.

    Serverbugg (verifierad 2026-08-19): för view=* saknas den avslutande `]`
    (Content-Length klipper svaret) — komplettera och försök igen innan vi ger upp.
    """
    text = data.decode("utf-8", errors="replace").strip()
    svar = None
    for kandidat in (text, text + "]", text + "}]"):
        try:
            svar = json.loads(kandidat)
            break
        except ValueError:
            continue
    if svar is None:
        return []
    if isinstance(svar, dict):
        if svar.get("success") is False:
            return []
        svar = [svar]
    poster = []
    for post in svar:
        meta = post.get("metadata", post) if isinstance(post, dict) else None
        if meta and meta.get("idOblique"):
            poster.append(meta)
    return poster


def hitta_snedbilder(
    easting: float,
    northing: float,
    nyckel: str,
    crs: str = "EPSG:3014",
    datum: str | None = None,
    hamta: Callable[[str], bytes] = _hamta,
) -> list[Snedbild]:
    """Bästa snedbilden per riktning över punkten (tom lista = ingen täckning)."""
    params = {
        "userkey": nyckel,
        "x": easting,
        "y": northing,
        "crs": crs,
        "view": "*",
        "output": "json",
    }
    if datum:
        params["date"] = datum
    url = f"{MAPSPACE_BAS}/mapSvcs/SEOblique?{urlencode(params)}"
    poster = _tolka_seoblique(hamta(url))
    if not poster:
        # Fallback: en fråga per riktning (tål serverbuggen i view=* helt).
        for riktning in RIKTNINGAR:
            params["view"] = riktning
            url = f"{MAPSPACE_BAS}/mapSvcs/SEOblique?{urlencode(params)}"
            try:
                poster += _tolka_seoblique(hamta(url))
            except Exception:  # noqa: BLE001 — en riktning utan svar är inte ett fel
                continue
    bilder = []
    for meta in poster:
        bild_id = str(meta["idOblique"])
        bilder.append(
            Snedbild(
                riktning=bild_id[0],
                id=bild_id,
                datum=_datum_ur_id(bild_id),
                position_x=float(meta.get("positionX", 0)),
                position_y=float(meta.get("positionY", 0)),
                kolumner=int(meta.get("imageCols", 0)),
                rader=int(meta.get("imageRows", 0)),
                copyright=str(meta.get("copyright", "")),
            )
        )
    ordning = {r: i for i, r in enumerate(RIKTNINGAR)}
    return sorted(bilder, key=lambda b: ordning.get(b.riktning, 9))


def _tile_url(nyckel: str, bild_id: str, zoom: int, rad: int, kol: int) -> str:
    params = {"userkey": nyckel, "id": bild_id, "meshid": f"{zoom}_{rad}_{kol}"}
    return f"{MAPSPACE_BAS}/mapSvcs/DAObliqueTile?{urlencode(params)}"


def hamta_utsnitt(
    bild: Snedbild,
    nyckel: str,
    zoom: int | None = None,
    tiles: int = 3,
    markera: bool = True,
    hamta: Callable[[str], bytes] = _hamta,
) -> bytes:
    """Sy ihop `tiles`×`tiles` rutor runt punkten till en PNG, med punkten markerad.

    zoom None = anpassa till bildens storlek så att utsnittet täcker ungefär
    samma markyta oavsett årgång (Blom 2018: 7 700 px bred → zoom 3, fjärdedels
    upplösning; Blom 2022: 14 144 px → zoom 2). Saknade rutor (utanför bilden)
    lämnas vita — MapSpace svarar då med en transparent PNG.
    """
    if zoom is None:
        zoom = 2 if bild.kolumner > 10_000 else 3
    zoom = max(1, min(4, int(zoom)))
    faktor = TILE_PX * 2 ** (zoom - 1)
    mitt_kol = int(bild.position_x // faktor)
    mitt_rad = int(bild.position_y // faktor)
    halv = tiles // 2
    duk = Image.new("RGB", (TILE_PX * tiles, TILE_PX * tiles), "white")
    rutor = [
        (di, dj, mitt_kol - halv + di, mitt_rad - halv + dj)
        for dj in range(tiles)
        for di in range(tiles)
        if mitt_kol - halv + di >= 0 and mitt_rad - halv + dj >= 0
    ]

    def _ruta(post):
        di, dj, kol, rad = post
        try:
            data = hamta(_tile_url(nyckel, bild.id, zoom, rad, kol))
            return di, dj, Image.open(io.BytesIO(data)).convert("RGBA")
        except Exception:  # noqa: BLE001 — en saknad ruta är inte ett fel för helheten
            return di, dj, None

    # Rutorna är oberoende — hämta dem parallellt (9 anrop ≈ 1 tur i stället för 9).
    with ThreadPoolExecutor(max_workers=min(8, len(rutor) or 1)) as pool:
        for di, dj, ruta in pool.map(_ruta, rutor):
            if ruta is not None:
                duk.paste(ruta, (di * TILE_PX, dj * TILE_PX), ruta)

    if markera:
        px = (bild.position_x - (mitt_kol - halv) * faktor) / faktor * TILE_PX
        py = (bild.position_y - (mitt_rad - halv) * faktor) / faktor * TILE_PX
        rita = ImageDraw.Draw(duk)
        r = 14
        rita.ellipse((px - r, py - r, px + r, py + r), outline=(230, 40, 40), width=3)
        rita.line((px - r - 8, py, px - r + 2, py), fill=(230, 40, 40), width=3)
        rita.line((px + r - 2, py, px + r + 8, py), fill=(230, 40, 40), width=3)
        rita.line((px, py - r - 8, px, py - r + 2), fill=(230, 40, 40), width=3)
        rita.line((px, py + r - 2, px, py + r + 8), fill=(230, 40, 40), width=3)
        etikett = f"{bild.riktning} · {bild.datum} · © {bild.copyright}".strip(" ·")
        rita.rectangle((0, 0, 8 + 7 * len(etikett), 18), fill=(255, 255, 255))
        rita.text((4, 3), etikett, fill=(0, 0, 0))

    ut = io.BytesIO()
    duk.save(ut, format="PNG")
    return ut.getvalue()


def viewer_url(
    easting: float,
    northing: float,
    nyckel: str,
    crs: str = "EPSG:3014",
    riktning: str = "N",
    zoom: int = 4,
) -> str:
    """Länk till MapSpace-visaren vid punkten (dokumenterad URL-access, tutorial 06)."""
    params = {
        "workspace": "Default",
        "x": easting,
        "y": northing,
        "srs": crs,
        "zoom": zoom,
        "viewmode": "oblique",
        "orientation": riktning,
        "pin": "true",
        "userkey": nyckel,
    }
    return f"{MAPSPACE_BAS}/?{urlencode(params)}"


def snedbilder_vid_punkt(
    easting: float,
    northing: float,
    nyckel: str | None = None,
    datum: str | None = None,
    hamta: Callable[[str], bytes] = _hamta,
) -> dict[str, Any]:
    """Kompakt, JSON-vänlig översikt: vilka riktningar/datum finns, och visar-länk.

    Returnerar {"tillganglig": False, "orsak": ...} utan nyckel eller täckning —
    aldrig ett undantag: snedbilder är ett komplement, inte ett krav.
    """
    nyckel = nyckel or userkey()
    if not nyckel:
        return {"tillganglig": False, "orsak": "ingen MAPSPACE_USERKEY"}
    try:
        bilder = hitta_snedbilder(easting, northing, nyckel, datum=datum, hamta=hamta)
    except Exception as exc:  # noqa: BLE001
        return {"tillganglig": False, "orsak": f"MapSpace svarade inte: {exc}"}
    if not bilder:
        return {"tillganglig": False, "orsak": "ingen snedbildstäckning vid punkten"}
    return {
        "tillganglig": True,
        "bilder": [bild_till_dict(b) for b in bilder],
        "ar": sorted({b.ar for b in bilder}),
        "viewer_url": viewer_url(easting, northing, nyckel),
        "kalla": "MapSpace (Sundsvalls kommun, userkey via upphandlingen F5/7a)",
    }


def bild_till_dict(b: Snedbild) -> dict[str, Any]:
    """JSON-vänlig form av Snedbild (position/storlek behövs för att sy utsnittet senare)."""
    return {
        "riktning": b.riktning,
        "id": b.id,
        "datum": b.datum,
        "copyright": b.copyright,
        "position_x": b.position_x,
        "position_y": b.position_y,
        "kolumner": b.kolumner,
        "rader": b.rader,
    }


def bild_fran_dict(d: dict[str, Any]) -> Snedbild:
    return Snedbild(
        riktning=str(d["riktning"]),
        id=str(d["id"]),
        datum=str(d.get("datum") or _datum_ur_id(str(d["id"]))),
        position_x=float(d.get("position_x", 0)),
        position_y=float(d.get("position_y", 0)),
        kolumner=int(d.get("kolumner", 0)),
        rader=int(d.get("rader", 0)),
        copyright=str(d.get("copyright", "")),
    )


def utsnitt_vid_punkt(
    easting: float,
    northing: float,
    riktning: str,
    nyckel: str | None = None,
    datum: str | None = None,
    zoom: int | None = None,
    hamta: Callable[[str], bytes] = _hamta,
) -> bytes | None:
    """PNG-utsnitt för en riktning över punkten, eller None om nyckel/täckning saknas."""
    nyckel = nyckel or userkey()
    if not nyckel:
        return None
    bilder = [
        b for b in hitta_snedbilder(easting, northing, nyckel, datum=datum, hamta=hamta)
        if b.riktning == riktning.upper()
    ]
    if not bilder:
        return None
    return hamta_utsnitt(bilder[0], nyckel, zoom=zoom, hamta=hamta)

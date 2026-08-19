"""Robust geodata-hämtning: WFS utan GetCapabilities, lokal ögonblicksbild, disk-cache.

Bakgrund (anbudsfrågor 151260/151373, aug 2026): flera anbudsgivare rapporterade
att karta.sundsvall.se:s WFS tidvis svarar med shapefile-fel eller timeout för
strandskydds- och riksintresselagren. Kommunen "ser inte problemen" — men en
demo som står och faller med en extern GeoServer just den timmen är ett dåligt
vad. Den här modulen gör tre saker, i den ordningen:

1. **Ögonblicksbild (snapshot).** Hela lagret sparas lokalt en gång
   (`geo-tillsyn-geodata snapshot`); bbox-frågor besvaras med shapely utan
   nätverk. Strandskyddszonerna är få (363 st) men enorma polygoner — en
   bbox-fråga mot servern returnerar ändå ~16 MB, så det lokala svaret är
   dessutom snabbare. Varje svar deklarerar att det kommer ur en
   ögonblicksbild och när den hämtades: aldrig tyst.
2. **Live med timeout.** GetFeature byggs direkt (ingen GetCapabilities på
   577 kB per anrop, som owslib gör). Lyckas det cachas svaret på disk.
3. **Stale fallback.** Misslyckas live-anropet men ett cachat svar finns,
   returneras det — märkt med hämtningsdatum, så att dossiern kan säga det.

Svaret är alltid ett GeoJSON FeatureCollection-dict, med ett extra fält
`geo_tillsyn_kalla = {"typ": "live" | "snapshot" | "cache", "hamtad": ISO}`
som runner.py läser för att formulera förbehållet.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlencode

from shapely.geometry import box, shape

CRS = "EPSG:3014"

# Lager som tjänar på en hel-lager-ögonblicksbild: få, stora polygoner som
# bbox-filtret ändå inte kan klippa. Utvidgat/upphävt ingår så att Fall 7 kan
# visa dem även när Länsstyrelsens lager ligger nere (juli 2026-incidenten).
# Rättigheter/gemensamhetsanläggningar (Lantmäteriet via kommunen, 7d) tas med
# av samma skäl: ~12 000 objekt, ~29 MB totalt — billigt lokalt, och lagren är
# nya i underlaget (aug 2026) så ingen driftshistorik finns att luta sig mot.
SNAPSHOT_LAGER: tuple[str, ...] = (
    "SundsvallsKommun:lm_strandskydd_y",
    "Lansstyrelsen:UtvidgatStrandskydd_yta",
    "Lansstyrelsen:UpphavdaStrandskydd_yta",
    "Lantmateriet:rk_rattighet_y",
    "Lantmateriet:rk_rattighet_l",
    "Lantmateriet:rk_ga_y",
    "Lantmateriet:rk_ga_l",
)

_ROT = Path(__file__).resolve().parents[2]
CACHE_KATALOG = _ROT / "data" / "cache"
SNAPSHOT_KATALOG = CACHE_KATALOG / "snapshot"
WFS_CACHE_KATALOG = CACHE_KATALOG / "wfs"

TIMEOUT_S = float(os.environ.get("GEO_TILLSYN_WFS_TIMEOUT", "30"))
# GEO_TILLSYN_OFFLINE=1: hoppa över nätet helt (demo på osäker uppkoppling);
# snapshot/cache måste då vara förvärmda, annars kastas fel som vanligt.
OFFLINE = os.environ.get("GEO_TILLSYN_OFFLINE", "") not in ("", "0", "false")


class GeodataFel(Exception):
    """Lagret kunde inte hämtas — varken live, ur cache eller ögonblicksbild."""


def _nu() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _lagerfil(lager: str) -> str:
    return lager.replace(":", "__")


def getfeature_url(
    ows_url: str,
    lager: str,
    bbox: tuple[float, float, float, float] | None,
    max_features: int | None,
    crs: str = CRS,
) -> str:
    """Bygg GetFeature-URL:en själv — samma som dossiern länkar till som källa."""
    params: dict[str, Any] = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeNames": lager,
        "outputFormat": "application/json",
        "srsName": crs,
    }
    if bbox is not None:
        params["bbox"] = ",".join(str(v) for v in bbox) + f",{crs}"
    if max_features is not None:
        params["count"] = max_features
    return f"{ows_url}?{urlencode(params)}"


def _hamta_url(url: str, timeout: float) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "geo-tillsyn/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (https, känd värd)
        return resp.read()


def _tolka_geojson(data: bytes, lager: str) -> dict[str, Any]:
    """GeoServer svarar 200 med ett XML-ServiceExceptionReport vid lagerfel — fånga det."""
    try:
        fc = json.loads(data)
    except ValueError as exc:
        text = data[:300].decode("utf-8", errors="replace")
        raise GeodataFel(f"{lager}: icke-JSON-svar från WFS: {text!r}") from exc
    if not isinstance(fc, dict) or fc.get("type") != "FeatureCollection":
        raise GeodataFel(f"{lager}: oväntat WFS-svar (ingen FeatureCollection)")
    return fc


# --- ögonblicksbild -----------------------------------------------------------


def snapshot_fil(lager: str, katalog: Path = SNAPSHOT_KATALOG) -> Path:
    return katalog / f"{_lagerfil(lager)}.geojson"


def spara_snapshot(
    ows_url: str,
    lager: str,
    katalog: Path = SNAPSHOT_KATALOG,
    hamta: Callable[[str, float], bytes] = _hamta_url,
    timeout: float = 300.0,
) -> Path:
    """Hämta HELA lagret och spara det som GeoJSON + metadata (hamtad, antal, url)."""
    url = getfeature_url(ows_url, lager, bbox=None, max_features=None)
    fc = _tolka_geojson(hamta(url, timeout), lager)
    fc["geo_tillsyn_snapshot"] = {
        "lager": lager,
        "hamtad": _nu(),
        "antal": len(fc.get("features", [])),
        "url": url,
    }
    katalog.mkdir(parents=True, exist_ok=True)
    fil = snapshot_fil(lager, katalog)
    fil.write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")
    return fil


_snapshot_minne: dict[Path, tuple[dict[str, Any], list]] = {}


def _ladda_snapshot(fil: Path) -> tuple[dict[str, Any], list]:
    """Läs + förbered (geometri, feature)-par; hålls i minnet processen ut."""
    cached = _snapshot_minne.get(fil)
    if cached is not None:
        return cached
    fc = json.loads(fil.read_text(encoding="utf-8"))
    par = [
        (shape(f["geometry"]), f)
        for f in fc.get("features", [])
        if f.get("geometry")
    ]
    _snapshot_minne[fil] = (fc, par)
    return fc, par


def fraga_snapshot(
    lager: str,
    bbox: tuple[float, float, float, float] | None,
    max_features: int | None,
    katalog: Path = SNAPSHOT_KATALOG,
) -> dict[str, Any] | None:
    """Besvara en bbox-fråga ur ögonblicksbilden, eller None om ingen finns."""
    fil = snapshot_fil(lager, katalog)
    if not fil.exists():
        return None
    fc, par = _ladda_snapshot(fil)
    if bbox is None:
        traffar = [f for _, f in par]
    else:
        ruta = box(*bbox)
        traffar = [f for geom, f in par if geom.intersects(ruta)]
    if max_features is not None:
        traffar = traffar[:max_features]
    meta = fc.get("geo_tillsyn_snapshot", {})
    return {
        "type": "FeatureCollection",
        "features": traffar,
        "numberReturned": len(traffar),
        "geo_tillsyn_kalla": {"typ": "snapshot", "hamtad": meta.get("hamtad")},
    }


# --- disk-cache ---------------------------------------------------------------


def _cachefil(url: str, katalog: Path) -> Path:
    return katalog / f"{hashlib.sha256(url.encode()).hexdigest()[:24]}.json"


def _las_cache(url: str, katalog: Path) -> dict[str, Any] | None:
    fil = _cachefil(url, katalog)
    if not fil.exists():
        return None
    try:
        return json.loads(fil.read_text(encoding="utf-8"))
    except ValueError:
        return None


def _skriv_cache(url: str, fc: dict[str, Any], katalog: Path) -> None:
    katalog.mkdir(parents=True, exist_ok=True)
    _cachefil(url, katalog).write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")


# --- huvudingång --------------------------------------------------------------


def hamta_wfs_robust(
    ows_url: str,
    type_name: str,
    bbox: tuple[float, float, float, float] | None = None,
    max_features: int = 100,
    *,
    snapshot_katalog: Path = SNAPSHOT_KATALOG,
    cache_katalog: Path = WFS_CACHE_KATALOG,
    hamta: Callable[[str, float], bytes] = _hamta_url,
    timeout: float = TIMEOUT_S,
    offline: bool = OFFLINE,
) -> dict[str, Any]:
    """Drop-in för mcp_ogc.tools.wfs.query_wfs_features — men tålig.

    Ordning: ögonblicksbild → live (cachas) → stale cache. Kastar GeodataFel
    först när alla tre vägar är stängda. Svaret bär `geo_tillsyn_kalla`.
    """
    ur_snapshot = fraga_snapshot(type_name, bbox, max_features, snapshot_katalog)
    if ur_snapshot is not None:
        return ur_snapshot

    url = getfeature_url(ows_url, type_name, bbox, max_features)

    if not offline:
        try:
            fc = _tolka_geojson(hamta(url, timeout), type_name)
        except (GeodataFel, urllib.error.URLError, OSError, TimeoutError) as exc:
            live_fel: Exception | None = exc
            fc = None
        else:
            live_fel = None
            fc["geo_tillsyn_kalla"] = {"typ": "live", "hamtad": _nu()}
            _skriv_cache(url, fc, cache_katalog)
            return fc
    else:
        live_fel = GeodataFel("offline-läge (GEO_TILLSYN_OFFLINE)")

    cachad = _las_cache(url, cache_katalog)
    if cachad is not None:
        kalla = dict(cachad.get("geo_tillsyn_kalla") or {})
        cachad["geo_tillsyn_kalla"] = {"typ": "cache", "hamtad": kalla.get("hamtad")}
        return cachad

    raise GeodataFel(f"{type_name}: {live_fel}") from live_fel


def kalla_typ(fc: dict[str, Any]) -> tuple[str, str | None]:
    """(typ, hamtad) ur ett svar från hamta_wfs_robust; ("live", None) för andra hämtare."""
    meta = fc.get("geo_tillsyn_kalla") if isinstance(fc, dict) else None
    if not meta:
        return "live", None
    return str(meta.get("typ", "live")), meta.get("hamtad")

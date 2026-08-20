"""Tillsynsradar: skanna en zon i stället för en punkt -> rangordnade kandidater.

Allt annat i Geo-Tillsyn utgår från att någon redan klickat på rätt fastighet.
Radarn vänder på det: samma motor (REALITET ∩ RÄTTIGHET, tidsstämplad) körs
över en hel yta, och resultatet är en kandidatlista sorterad efter hur tydligt
byggnad och strandskyddszon sammanfaller — över tid. Anmälningsdriven tillsyn
är ojämlik; systematisk skanning ger samma måttstock åt alla.

Poängen är ingen sannolikhet och inget omdöme: den är en summa av få, öppet
redovisade regler (se `POANGMODELL`), och varje kandidat bär sina egna grunder.
Dispenser kontrolleras inte här (ingen åtkomst i prototypen) — deklarerat.
Beslutet fattas av handläggaren; det finns inget fält för något annat.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

from __future__ import annotations

from datetime import date
from typing import Any, Callable

from shapely.geometry import shape

from geo_tillsyn.analysis import ZonAnalys, analysera_strandskydd, komplettera_med_regellager
from geo_tillsyn.geodata import getfeature_url, hamta_wfs_robust, kalla_typ
from geo_tillsyn.juridik import JuridisktLage, juridiskt_lage
from geo_tillsyn.meddelanden import Meddelande as M

BYGGNAD_LAYER = "SundsvallsKommun:bal_byggnad_yta"
STRANDSKYDD_LAYER = "SundsvallsKommun:lm_strandskydd_y"
UTVIDGAT_LAYER = "Lansstyrelsen:UtvidgatStrandskydd_yta"
UPPHAVT_LAYER = "Lansstyrelsen:UpphavdaStrandskydd_yta"
FASTIGHET_LAYER = "SundsvallsKommun:Fastighet_yta"
FBET_PROPERTY = "FBET"
CRS = "EPSG:3014"
REGELVERK_KALLA_URL = "https://rkrattsdb.gov.se/SFSdoc/98/980808.PDF"

# En radarkörning är en WFS-bbox-fråga mot byggnadslagret; 4 km² (~2×2 km)
# håller svaret hanterbart och matchar demozonen på nordvästra Alnö (~3,7 km²).
MAX_ZON_AREA_M2 = 4_000_000
_MAX_BYGGNADER = 5000
_MAX_FASTIGHETER = 5000
DEFAULT_MAX_KANDIDATER = 25

POANGMODELL = (
    "radar.modell_lage",
    "radar.modell_regim",
    "radar.modell_ar_okant",
    "radar.modell_utvidgat",
)


def poangsatt(
    analys: ZonAnalys,
    lage: JuridisktLage,
    komplement: dict[str, list[str]],
) -> tuple[int, list[str]]:
    """Summan av öppet redovisade regler + grunderna bakom varje poäng."""
    poang = 0
    grunder: list[str] = []

    if analys.laege == "inom":
        poang += 3
        grunder.append(M("radar.poang_inom"))
    else:
        poang += 2
        grunder.append(M("radar.poang_delvis", andel=analys.andel_inom))

    if lage.byggnads_ar is None:
        poang += 1
        grunder.append(M("radar.poang_ar_okant"))
    elif lage.gallde_vid_uppforande is None:
        poang += 1
        grunder.append(M("radar.poang_ar_ikrafttradandear", ar=lage.byggnads_ar))
    elif lage.gallde_vid_uppforande:
        poang += 3
        grunder.append(M("radar.poang_gallde_vid_uppforande", ar=lage.byggnads_ar))
    else:
        grunder.append(M("radar.poang_fore_strandskydd", ar=lage.byggnads_ar))

    if komplement.get(UTVIDGAT_LAYER):
        poang += 1
        grunder.append(M("radar.poang_utvidgat"))
    if komplement.get(UPPHAVT_LAYER):
        grunder.append(
            M("radar.kallkonflikt_upphavt", referens=", ".join(komplement[UPPHAVT_LAYER]))
        )
    return poang, grunder


def _kontrollera_zon(bbox: tuple[float, float, float, float]) -> None:
    min_e, min_n, max_e, max_n = bbox
    if not (max_e > min_e and max_n > min_n):
        raise ValueError(M("server.bbox_ogiltig", detalj="max måste vara större än min"))
    area = (max_e - min_e) * (max_n - min_n)
    if area > MAX_ZON_AREA_M2:
        raise ValueError(
            M(
                "radar.zon_for_stor",
                area_km2=round(area / 1e6, 1),
                max_km2=round(MAX_ZON_AREA_M2 / 1e6, 1),
            )
        )


def _kallforbehall(fc: dict, lager: str) -> list[str]:
    typ, hamtad = kalla_typ(fc)
    if typ == "snapshot":
        return [M("geodata.snapshot_anvant", lager=lager, hamtad=hamtad or "okänt datum")]
    if typ == "cache":
        return [M("geodata.cache_anvant", lager=lager, hamtad=hamtad or "okänt datum")]
    return []


def _fastighet_per_byggnad(
    byggnader: dict,
    fastigheter: dict | None,
) -> dict[str, str | None]:
    """Byggnadens representativa punkt -> fastighetsbeteckning (FBET), eller None."""
    if not fastigheter:
        return {}
    polygoner = [
        (shape(f["geometry"]), (f.get("properties") or {}).get(FBET_PROPERTY))
        for f in fastigheter.get("features", [])
        if f.get("geometry")
    ]
    resultat: dict[str, str | None] = {}
    for f in byggnader.get("features", []):
        if not f.get("geometry"):
            continue
        punkt = shape(f["geometry"]).representative_point()
        traff = next((fbet for geom, fbet in polygoner if geom.contains(punkt)), None)
        resultat[str(f.get("id"))] = str(traff) if traff else None
    return resultat


def skanna_zon(
    ows_url: str,
    bbox: tuple[float, float, float, float],
    nu: str,
    hamta_wfs: Callable = hamta_wfs_robust,
    max_kandidater: int = DEFAULT_MAX_KANDIDATER,
) -> dict[str, Any]:
    """Skanna en bbox (EPSG:3014) och rangordna byggnader som möter strandskyddszon.

    Returns:
        JSON-serialiserbar dict: kandidater (rang, byggnad_id, fastighet, centroid,
        läge, tidsmedveten regim, poäng + grunder), öppen poängmodell, deklarerade
        osäkerheter och källor. Aldrig geometri utöver en centroid, aldrig bilder.
    """
    _kontrollera_zon(bbox)

    byggnader = hamta_wfs(ows_url, BYGGNAD_LAYER, bbox=bbox, max_features=_MAX_BYGGNADER)
    strandskydd = hamta_wfs(ows_url, STRANDSKYDD_LAYER, bbox=bbox, max_features=500)

    osakerheter: list[str] = []
    osakerheter += _kallforbehall(byggnader, BYGGNAD_LAYER)
    osakerheter += _kallforbehall(strandskydd, STRANDSKYDD_LAYER)

    regellager: dict[str, dict] = {}
    for lager in (UTVIDGAT_LAYER, UPPHAVT_LAYER):
        try:
            fc = hamta_wfs(ows_url, lager, bbox=bbox, max_features=500)
        except Exception:
            osakerheter.append(M("runner.regellager_otillgangligt", lager=lager))
            continue
        osakerheter += _kallforbehall(fc, lager)
        regellager[lager] = fc

    fastigheter: dict | None
    try:
        fastigheter = hamta_wfs(ows_url, FASTIGHET_LAYER, bbox=bbox, max_features=_MAX_FASTIGHETER)
        osakerheter += _kallforbehall(fastigheter, FASTIGHET_LAYER)
    except Exception:
        fastigheter = None
        osakerheter.append(M("radar.fastighetslager_otillgangligt", lager=FASTIGHET_LAYER))
    osakerheter.append(M("runner.dispenser_ej_kontrollerade"))

    analyser = analysera_strandskydd(byggnader, strandskydd)
    komplement = komplettera_med_regellager(byggnader, regellager)
    fastighet_for = _fastighet_per_byggnad(byggnader, fastigheter)
    features_per_id = {str(f.get("id")): f for f in byggnader.get("features", [])}
    bedomningsdatum = date.fromisoformat(nu[:10])

    kandidater: list[dict[str, Any]] = []
    for analys in analyser:
        if analys.laege not in ("inom", "delvis"):
            continue
        feature = features_per_id.get(analys.byggnad_id, {})
        ar = (feature.get("properties") or {}).get("bal_nybyggnadsar")
        lage = juridiskt_lage(analys, ar, bedomningsdatum)
        poang, grunder = poangsatt(analys, lage, komplement.get(analys.byggnad_id, {}))
        punkt = shape(feature["geometry"]).representative_point()
        kandidater.append(
            {
                "byggnad_id": analys.byggnad_id,
                "fastighet": fastighet_for.get(analys.byggnad_id),
                "centroid": {"easting": round(punkt.x, 1), "northing": round(punkt.y, 1), "crs": CRS},
                "laege": analys.laege,
                "andel_inom": round(analys.andel_inom, 2),
                "zon_referenser": analys.zon_referenser,
                "byggnads_ar": lage.byggnads_ar,
                "gallde_vid_uppforande": lage.gallde_vid_uppforande,
                "dispens_kravs_idag": lage.dispens_kravs_idag,
                "preskriberas": lage.preskriberas,
                "poang": poang,
                "grunder": grunder,
            }
        )

    # Högst poäng först; lika poäng -> nyare byggnad först (kortare väg till
    # ortofoto-datering), okänt år sist bland lika.
    kandidater.sort(
        key=lambda k: (-k["poang"], -(k["byggnads_ar"] or 0), k["byggnad_id"])
    )
    antal_traffar = len(kandidater)
    kandidater = kandidater[:max_kandidater]
    for i, k in enumerate(kandidater, start=1):
        k["rang"] = i

    resultat: dict[str, Any] = {
        "zon": {"bbox": list(bbox), "crs": CRS},
        "antal_byggnader": len(analyser),
        "antal_traffar": antal_traffar,
        "kandidater": kandidater,
        "poangmodell": [M(kod) for kod in POANGMODELL],
        "juridisk_not": M("radar.juridisk_not"),
        "osakerheter": osakerheter,
        "kallor": [
            {
                "beskrivning": f"{BYGGNAD_LAYER} (WFS)",
                "url": getfeature_url(ows_url, BYGGNAD_LAYER, bbox, _MAX_BYGGNADER),
            },
            {
                "beskrivning": f"{STRANDSKYDD_LAYER} (WFS)",
                "url": getfeature_url(ows_url, STRANDSKYDD_LAYER, bbox, 500),
            },
            {"beskrivning": "Miljöbalken 7 kap. (SFS 1998:808)", "url": REGELVERK_KALLA_URL},
        ],
        "hamtad": nu,
    }
    if antal_traffar > max_kandidater:
        resultat["kandidater_trunkerade_till"] = max_kandidater
    return resultat

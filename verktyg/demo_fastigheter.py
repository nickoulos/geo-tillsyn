"""Demo-fastigheter: egna testfastigheter, verifierade mot kommunens data.

Kommunen lämnar inget format för testfastigheter och ingen lista före demon
(e-Avrop 151234, aug 2026) — vi förbereder därför egna: protagonisten
ALNÖ-USLAND 1:45 plus reserver från Spike C:s rankning (docs/data-findings.md),
var och en verifierad LIVE mot karta.sundsvall.se vid körning:

  * fastighetsgeometri (SundsvallsKommun:Fastighet_yta, nyckel TRAKT + FBETNR —
    samma nyckelform som ByggR:s GetRelateradeArendenByFastighet),
  * byggnader på fastigheten (bal_byggnad_yta) med area, nybyggnadsår och
    klickpunkt (centroid, EPSG:3014),
  * läge mot strandskydd (lm_strandskydd_y — ur ögonblicksbilden om den finns),
  * rättigheter/GA som berör byggnaden (rk_rattighet_*/rk_ga_* — ögonblicksbild).

Skriver data/demo/fastigheter.json (maskinläsbart, matas till
`geo-tillsyn-geodata varm`) och docs/demo-fastigheter.md (tabell för manuset).

    .venv/Scripts/python verktyg/demo_fastigheter.py               # standardlistan
    .venv/Scripts/python verktyg/demo_fastigheter.py "ALNÖ-VI 3:100" # egna

SPDX-License-Identifier: AGPL-3.0-or-later
"""

from __future__ import annotations

import json
import sys
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlencode

from shapely.geometry import shape
from shapely import force_2d

ROT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROT / "src"))

from geo_tillsyn.geodata import hamta_wfs_robust  # noqa: E402
from geo_tillsyn.runner import (  # noqa: E402
    BYGGNAD_LAYER,
    RATTIGHET_LAGER,
    STRANDSKYDD_LAYER,
    _rattighet_post,
)

import re  # noqa: E402

_TRAKT_NR_RE = re.compile(r"^(?P<trakt>.+?)\s+(?P<nr>\d+:\d+)$")


def dela_fastighetsbeteckning(beteckning: str) -> tuple[str, str]:
    """'ALNÖ-USLAND 1:45' -> ('ALNÖ-USLAND', '1:45') — samma nyckelform som ByggR/Fastighet_yta."""
    m = _TRAKT_NR_RE.match(" ".join(beteckning.split()).upper())
    if not m:
        raise ValueError(f"{beteckning!r}: förväntade 'TRAKT registernummer'")
    return m.group("trakt"), m.group("nr")


def _hamta_rattighetslager(ows_url: str, bbox: tuple, hamta_wfs) -> tuple[dict[str, dict], list[str]]:
    lager_fc: dict[str, dict] = {}
    osakerheter: list[str] = []
    for lager in RATTIGHET_LAGER:
        try:
            lager_fc[lager] = hamta_wfs(ows_url, lager, bbox=bbox, max_features=200)
        except Exception as exc:  # noqa: BLE001
            osakerheter.append(f"{lager} otillgängligt: {exc}")
    return lager_fc, osakerheter


def _rattigheter_som_beror(lager_fc: dict[str, dict], footprint) -> list[dict]:
    traffar: list[dict] = []
    sedda: set[tuple[str, str]] = set()
    for lager, fc in lager_fc.items():
        for feature in fc.get("features", []):
            if not feature.get("geometry"):
                continue
            if not force_2d(shape(feature["geometry"])).intersects(footprint):
                continue
            post = _rattighet_post(feature, lager)
            nyckel = (post["typ"], post["aktbeteckning"])
            if nyckel not in sedda:
                sedda.add(nyckel)
                traffar.append(post)
    return traffar

OWS = "https://karta.sundsvall.se/geoserver/ows"
FASTIGHET_LAYER = "SundsvallsKommun:Fastighet_yta"
CRS = "EPSG:3014"

# Protagonist + reserver (Spike C, docs/data-findings.md §3). Ordningen är
# prioritetsordning för demon. Rollen är vår egen regi — verifieras av körningen.
STANDARD = [
    "ALNÖ-USLAND 1:45",
    "ALNÖ-VI 3:100",
    "NJURUNDA PRÄSTBOL 1:117",
    "ALNÖ-VI 3:109",
    "ALNÖ-USLAND 7:1",
    "RÖKLAND 1:82",
]
ROLL = {
    "ALNÖ-USLAND 1:45": "PROTAGONIST (manus Akt 1–3): komplementbyggnad 55,5 m² 2014 (Fall 1), "
    "huvudbyggnad 325 m² 2014 + syntetiskt lov SBN 2009-0412 (Fall 3), allt i strandskydd (Fall 7); "
    "uthus 64 m² berör ledningsrätt 2281-80/58 (rättigheter).",
    "ALNÖ-VI 3:100": "RESERV Fall 1/7, 250 m från protagonisten: komplement 93 m² 2014, delvis i zon.",
    "NJURUNDA PRÄSTBOL 1:117": "RESERV sydkusten: stor fastighet, komplement 61,5 m² 2014 i zon; "
    "flera byggnader berör officialservitut (rättigheter-demo).",
    "ALNÖ-VI 3:109": "RESERV Fall 1: hus 178 m² 2016 + NY byggnad 10,8 m² nybyggnadsår 2025 i zon "
    "(färsk förändring — syns i tidslinjen 2023 vs nu?).",
    "ALNÖ-USLAND 7:1": "RESERV Fall 7: hus 293 m² 2015 helt i zon, granne till protagonisten.",
    "RÖKLAND 1:82": "RESERV utanför Alnö-klustret: hus 115 m² 2015 helt i zon.",
}

UT_JSON = ROT / "data" / "demo" / "fastigheter.json"
UT_MD = ROT / "docs" / "demo-fastigheter.md"


def _wfs_cql(layer: str, cql: str, count: int = 50) -> dict:
    params = {
        "service": "WFS", "version": "2.0.0", "request": "GetFeature",
        "typeNames": layer, "outputFormat": "application/json", "srsName": CRS,
        "count": count, "cql_filter": cql,
    }
    req = urllib.request.Request(f"{OWS}?{urlencode(params)}", headers={"User-Agent": "geo-tillsyn/0.1"})
    with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
        return json.loads(resp.read())


def hamta_fastighet(beteckning: str) -> dict | None:
    trakt, nr = dela_fastighetsbeteckning(beteckning)
    # TRAKT + FBETNR i stället för FBET: FBET-strängen kommer tillbaka med
    # teckenfel (ALN�-USLAND) och CQL-likhet på den är opålitlig.
    fc = _wfs_cql(FASTIGHET_LAYER, f"TRAKT='{trakt}' AND FBETNR='{nr}'")
    feats = [f for f in fc.get("features", []) if f.get("geometry")]
    if not feats:
        return None
    # En fastighet kan ha flera områden (OMR) — ta det största.
    return max(feats, key=lambda f: shape(f["geometry"]).area)


def _lage(footprint, zoner_fc: dict) -> tuple[str, list[str]]:
    refs: list[str] = []
    andel = 0.0
    for z in zoner_fc.get("features", []):
        if not z.get("geometry"):
            continue
        zg = force_2d(shape(z["geometry"]))
        if zg.intersects(footprint):
            refs.append(str((z.get("properties") or {}).get("lm_aktbeteckning") or z.get("id")))
            andel += footprint.intersection(zg).area / footprint.area
    if not refs:
        return "utanför", []
    return ("inom" if andel >= 0.99 else "delvis"), refs


def analysera(beteckning: str) -> dict:
    fast = hamta_fastighet(beteckning)
    if fast is None:
        return {"fastighet": beteckning, "fel": "hittades inte i Fastighet_yta"}
    geom = force_2d(shape(fast["geometry"]))
    props = fast.get("properties") or {}
    minx, miny, maxx, maxy = geom.bounds
    bbox = (minx - 5, miny - 5, maxx + 5, maxy + 5)

    byggnader = hamta_wfs_robust(OWS, BYGGNAD_LAYER, bbox=bbox, max_features=200)
    zoner = hamta_wfs_robust(OWS, STRANDSKYDD_LAYER, bbox=bbox, max_features=100)
    ratt_fc, ratt_osak = _hamta_rattighetslager(OWS, bbox, hamta_wfs_robust)

    rader = []
    for b in byggnader.get("features", []):
        if not b.get("geometry"):
            continue
        fp = force_2d(shape(b["geometry"]))
        if not fp.intersects(geom) or fp.intersection(geom).area / fp.area < 0.5:
            continue
        c = fp.centroid
        lage, refs = _lage(fp, zoner)
        bp = b.get("properties") or {}
        rader.append({
            "byggnad_id": str(b.get("id")),
            "klickpunkt": {"easting": round(c.x, 1), "northing": round(c.y, 1), "crs": CRS},
            "area_m2": round(fp.area, 1),
            "bal_nybyggnadsar": bp.get("bal_nybyggnadsar"),
            "andamal": bp.get("bal_andamal") or bp.get("andamal"),
            "strandskydd": lage,
            "zon_referenser": refs,
            "rattigheter": [
                {k: r[k] for k in ("typ", "aktbeteckning", "andamal")}
                for r in _rattigheter_som_beror(ratt_fc, fp)
            ],
        })
    rader.sort(key=lambda r: -r["area_m2"])
    cen = geom.centroid
    return {
        "fastighet": beteckning,
        "trakt": props.get("TRAKT"),
        "fBetNr": props.get("FBETNR"),
        "fnr": props.get("FNR"),
        "area_m2": props.get("AREA"),
        "centroid": {"easting": round(cen.x, 1), "northing": round(cen.y, 1), "crs": CRS},
        "bbox": [round(v, 1) for v in bbox],
        "antal_byggnader": len(rader),
        "antal_i_strandskydd": sum(r["strandskydd"] != "utanför" for r in rader),
        "byggnader": rader,
        "osakerheter": list(ratt_osak),
        # OBS: props["link"] (FB-webb) bär inloggningsuppgifter i URL:en — persisteras aldrig.
    }


def _md(resultat: list[dict], nu: str) -> str:
    ut = [
        "# Demo-fastigheter (egna testfastigheter)",
        "",
        f"Genererad {nu} av `verktyg/demo_fastigheter.py` — verifierad live mot karta.sundsvall.se.",
        "Kommunen lämnar inget testdataformat före demon (e-Avrop 151234); dessa är våra.",
        "Klickpunkter i **EPSG:3014** (kommunlagrens CRS). Förvärm cachen: se kommandot sist.",
        "",
    ]
    for r in resultat:
        ut.append(f"## {r['fastighet']}")
        if ROLL.get(r["fastighet"]):
            ut += [f"*{ROLL[r['fastighet']]}*", ""]
        if "fel" in r:
            ut += [f"⚠ {r['fel']}", ""]
            continue
        ut.append(
            f"TRAKT `{r['trakt']}` · FBETNR `{r['fBetNr']}` · FNR {r['fnr']} · {r['area_m2']} m² · "
            f"centroid E {r['centroid']['easting']} N {r['centroid']['northing']} · "
            f"{r['antal_byggnader']} byggnader, {r['antal_i_strandskydd']} berör strandskydd"
        )
        ut.append("")
        ut.append("| Byggnad | Klickpunkt E, N | Area m² | Nybyggnadsår | Strandskydd | Rättigheter |")
        ut.append("| --- | --- | --- | --- | --- | --- |")
        for b in r["byggnader"]:
            ratt = "; ".join(f"{x['typ']} {x['aktbeteckning']}".strip() for x in b["rattigheter"]) or "—"
            ss = b["strandskydd"] + (f" ({', '.join(b['zon_referenser'])})" if b["zon_referenser"] else "")
            ut.append(
                f"| {b['byggnad_id']} | {b['klickpunkt']['easting']}, {b['klickpunkt']['northing']} | "
                f"{b['area_m2']} | {b['bal_nybyggnadsar'] or '—'} | {ss} | {ratt} |"
            )
        if r["osakerheter"]:
            ut.append("")
            ut.append("Osäkerheter: " + ", ".join(r["osakerheter"]))
        ut.append("")
    punkter = " ".join(
        f"{b['klickpunkt']['easting']} {b['klickpunkt']['northing']}"
        for r in resultat if "byggnader" in r
        for b in r["byggnader"][:3]
    )
    ut += [
        "## Att tänka på",
        "",
        "- Kommunen kan ge egna testfastigheter vid demon (F9): motorn är generell, men kör",
        "  `verktyg/demo_fastigheter.py \"TRAKT nr\"` på dem så fort de kommer — då får vi",
        "  klickpunkter, strandskyddsläge och rättigheter på 30 s, och cachen förvärms.",
        "- Fall 3 (lovavvikelse) har syntetiskt lov ENBART för ALNÖ-USLAND 1:45; övriga ger",
        "  ärligt »inget ärende i testarkivet« — säg det högt, det är poängen.",
        "- Detaljplan: ingen av dessa ligger inom detaljplan (kustläge) — regelgrenen är",
        "  *utanför detaljplan*. Behövs en inom-DP-variant: NOLBY/SKOTTSUND (Spike C).",
        "",
        "## Förvärm cachen (dagen före + demomorgonen)",
        "",
        "```sh",
        ".venv/Scripts/python -m geo_tillsyn.geodata_cli snapshot",
        f".venv/Scripts/python -m geo_tillsyn.geodata_cli varm {punkter}",
        "```",
        "",
    ]
    return "\n".join(ut)


def main(argv: list[str]) -> int:
    lista = argv or STANDARD
    nu = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    resultat = []
    for bet in lista:
        try:
            r = analysera(bet)
        except Exception as exc:  # noqa: BLE001 — rapportera, fortsätt
            r = {"fastighet": bet, "fel": f"{type(exc).__name__}: {exc}"}
        resultat.append(r)
        if "fel" in r:
            print(f"FEL  {bet}: {r['fel']}")
        else:
            print(f"OK   {bet}: {r['antal_byggnader']} byggnader, {r['antal_i_strandskydd']} i strandskydd")
    UT_JSON.parent.mkdir(parents=True, exist_ok=True)
    UT_JSON.write_text(json.dumps({"genererad": nu, "fastigheter": resultat}, ensure_ascii=False, indent=2), encoding="utf-8")
    UT_MD.write_text(_md(resultat, nu), encoding="utf-8")
    print(f"-> {UT_JSON}\n-> {UT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

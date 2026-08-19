"""Fall 7-körning: punkt -> WFS-hämtning -> analys -> dossier + tidslinje på disk.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

from __future__ import annotations

import io
from datetime import date
from pathlib import Path
from typing import Callable
from urllib.parse import urlencode

from PIL import Image, ImageDraw
from shapely import force_2d
from shapely.geometry import Point, mapping, shape

from geo_tillsyn.analysis import analysera_strandskydd, komplettera_med_regellager
from geo_tillsyn.datering import datera_byggnad
from geo_tillsyn.delta import jamfor_lage
from geo_tillsyn.dossier import Fakta, Kalla, render_markdown
from geo_tillsyn.fall1 import bygg_fall1_dossier
from geo_tillsyn.fall3 import bygg_fall3_dossier
from geo_tillsyn.fall7 import bygg_dossier
from geo_tillsyn.geodata import hamta_wfs_robust, kalla_typ
from geo_tillsyn.juridik import fall1_lage, fall3_lage, juridiskt_lage
from geo_tillsyn.lovarkiv import hitta_lov
from geo_tillsyn.lovtolk import korsjamfor, tolka_handling
from geo_tillsyn.meddelanden import Meddelande as M
from geo_tillsyn import snedbild as _snedbild
from geo_tillsyn.timeline import hamta_tidslinje

BYGGNAD_LAYER = "SundsvallsKommun:bal_byggnad_yta"
STRANDSKYDD_LAYER = "SundsvallsKommun:lm_strandskydd_y"

# Complementary RULE layers that legally widen (utvidgat) or lift (upphävt)
# the zone. Intermittently broken server-side on karta.sundsvall.se (GeoServer
# shapefile exception, July 2026 — kommun-confirmed); the runner tries them each
# run (snapshot/cache via geodata.py), reports failure as uncertainty and, when
# they answer, shows per building which objects it touches — a visible source
# conflict for the handläggare, never a silent override of the kommun's zone.
UTVIDGAT_LAYER = "Lansstyrelsen:UtvidgatStrandskydd_yta"
UPPHAVT_LAYER = "Lansstyrelsen:UpphavdaStrandskydd_yta"
KOMPLETTERANDE_REGELLAGER = [UTVIDGAT_LAYER, UPPHAVT_LAYER]

CRS = "EPSG:3014"  # native CRS of the kommun's WFS layers

FASTIGHETSGRANS_LAYER = "SundsvallsKommun:FastighetGrans_linje"

# Rättigheter (ledningsrätt, officialservitut) och gemensamhetsanläggningar —
# Lantmäteriet via kommunens GeoServer (anbudssvar 151260 7d, aug 2026). Ytor
# och linjer; punktlagren bär inte utbredning och utelämnas. En byggnad som
# berör en ledningsrätt eller ett servitut är ett faktum för handläggaren att
# väga in — ingen slutsats dras här.
RATTIGHET_LAGER = [
    "Lantmateriet:rk_rattighet_y",
    "Lantmateriet:rk_rattighet_l",
    "Lantmateriet:rk_ga_y",
    "Lantmateriet:rk_ga_l",
]
_MAX_RATTIGHETER = 12

# Snedbilder (MapSpace) — seam: tests byter ut mot en stubb (conftest.py) så att
# sviten aldrig rör nätet även när en MAPSPACE_USERKEY finns i .env.
SNEDBILDER_VID_PUNKT = _snedbild.snedbilder_vid_punkt
SNEDBILD_UTSNITT = _snedbild.utsnitt_vid_punkt

# Synthetic mock-ByggR archive (Fall 3) — no real ärendesystem is reachable in
# the prototype; see lovarkiv.py's docstring for the ärlighet contract.
LOVARKIV_KATALOG = Path(__file__).resolve().parents[2] / "data" / "synthetic" / "lovarkiv"

# Miljöbalken as official PDF (rkrattsdb covers SFS 1998:306-2018:159) — every
# time-aware regime fact in the dossier cites primary law, not our dataset.
REGELVERK_KALLA_URL = "https://rkrattsdb.gov.se/SFSdoc/98/980808.PDF"


def _kalla_url(p: Path) -> str:
    """Render a källa path repo-relative when possible (portable, no local-fs leak).

    Committed-archive paths (under the repo root) render as a repo-relative
    posix path; tmp-path test records fall back to a file:// URI.
    """
    rot = Path(__file__).resolve().parents[2]
    try:
        return p.resolve().relative_to(rot).as_posix()
    except ValueError:
        return p.as_uri()


def _getfeature_url(ows_url: str, type_name: str, bbox: tuple) -> str:
    params = {
        "service": "WFS",
        "version": "2.0.0",
        "request": "GetFeature",
        "typeNames": type_name,
        "bbox": ",".join(str(v) for v in bbox) + f",{CRS}",
        "outputFormat": "application/json",
    }
    return f"{ows_url}?{urlencode(params)}"


def _hamta_underlag(
    ows_url: str,
    punkt: tuple[float, float],
    radie_m: float,
    nu: str,
    hamta_wfs: Callable,
):
    """Fetch + analyse everything both the dossier and the MCP tools need."""
    e, n = punkt
    bbox = (e - radie_m, n - radie_m, e + radie_m, n + radie_m)

    byggnader = hamta_wfs(ows_url, BYGGNAD_LAYER, bbox=bbox, max_features=500)
    strandskydd = hamta_wfs(ows_url, STRANDSKYDD_LAYER, bbox=bbox, max_features=100)

    osakerheter: list[str] = []
    osakerheter += _kallforbehall(byggnader, BYGGNAD_LAYER)
    osakerheter += _kallforbehall(strandskydd, STRANDSKYDD_LAYER)
    regellager: dict[str, dict] = {}
    for lager in KOMPLETTERANDE_REGELLAGER:
        try:
            fc = hamta_wfs(ows_url, lager, bbox=bbox, max_features=100)
        except Exception:
            osakerheter.append(M("runner.regellager_otillgangligt", lager=lager))
            continue
        osakerheter += _kallforbehall(fc, lager)
        regellager[lager] = fc
    osakerheter.append(M("runner.dispenser_ej_kontrollerade"))

    analyser = analysera_strandskydd(byggnader, strandskydd)
    komplement = komplettera_med_regellager(byggnader, regellager)

    ar_per_byggnad = {
        str(f.get("id")): (f.get("properties") or {}).get("bal_nybyggnadsar")
        for f in byggnader.get("features", [])
    }
    bedomningsdatum = date.fromisoformat(nu[:10])
    juridik = {
        analys.byggnad_id: juridiskt_lage(
            analys, ar_per_byggnad.get(analys.byggnad_id), bedomningsdatum
        )
        for analys in analyser
        if analys.laege in ("inom", "delvis")
    }
    return bbox, byggnader, analyser, juridik, osakerheter, komplement


def _kallforbehall(fc: dict, lager: str) -> list[str]:
    """Förbehåll när ett lager inte kom live (ögonblicksbild/stale cache) — aldrig tyst."""
    typ, hamtad = kalla_typ(fc)
    if typ == "snapshot":
        return [M("geodata.snapshot_anvant", lager=lager, hamtad=hamtad or "okänt datum")]
    if typ == "cache":
        return [M("geodata.cache_anvant", lager=lager, hamtad=hamtad or "okänt datum")]
    return []


def _upphavt_konflikter(komplement: dict, analyser) -> list[str]:
    """En träffbyggnad som också berör upphävt strandskydd = synlig källkonflikt."""
    traff_ids = {a.byggnad_id for a in analyser if a.laege in ("inom", "delvis")}
    return [
        M(
            "runner.upphavt_strandskydd_konflikt",
            byggnad_id=byggnad_id,
            referens=", ".join(per_lager[UPPHAVT_LAYER]),
        )
        for byggnad_id, per_lager in komplement.items()
        if byggnad_id in traff_ids and per_lager.get(UPPHAVT_LAYER)
    ]


# Eneo's MCP client truncates tool output at 8 kB — cap the per-building list
# and declare the truncation (docs/spike-a-eneo-findings.md). 15 keeps a real
# response under the cap (measured live: 27 träffar serialised to 12.3 kB).
_MAX_TRAFFAR_I_SVAR = 15


def _rangordna_grupp(traff: dict) -> int:
    """(a) gällde vid uppförande, (b) år okänt, (c) gällde inte — spec §5.

    En byggnad med känt byggnadsår men okänd regim (ikraftträdandeårets
    månad saknas — `gallde_vid_uppforande is None` med `byggnads_ar` satt)
    är ett randfall spec §5 inte namnger; det hamnar sist, efter de tre
    uttryckliga grupperna, snarare än att tyst kollapsas in i någon av dem.
    """
    gallde = traff.get("gallde_vid_uppforande")
    if gallde is True:
        return 0
    if traff.get("byggnads_ar") is None:
        return 1
    if gallde is False:
        return 2
    return 3


def rangordna_traffar(traffar: list[dict]) -> list[dict]:
    """Radar-lite-rangordning: mest underlag för granskning först (spec §5).

    Ren funktion: tar kopior av indata, muterar aldrig `traffar`. Grupperar
    (a) gällde_vid_uppforande är True, (b) byggnads_ar är None,
    (c) gällde_vid_uppforande är False; inom grupp: läge "inom" före
    "delvis", sedan byggnad_id stigande (sträng). Ger varje kopia ett
    1-baserat `"rang"`.
    """
    ordnade = sorted(
        traffar,
        key=lambda t: (
            _rangordna_grupp(t),
            0 if t.get("laege") == "inom" else 1,
            t["byggnad_id"],
        ),
    )
    return [{**t, "rang": i} for i, t in enumerate(ordnade, start=1)]


def analysera_punkt(
    ows_url: str,
    punkt: tuple[float, float],
    radie_m: float,
    nu: str,
    hamta_wfs: Callable = hamta_wfs_robust,
) -> dict:
    """Compact, MCP-friendly strandskydd analysis around a point.

    Returns plain JSON-serialisable data: per-building läge + time-aware legal
    position, declared uncertainties and källa URLs. Never geometry, never
    imagery — references only.
    """
    bbox, byggnader, analyser, juridik, osakerheter, komplement = _hamta_underlag(
        ows_url, punkt, radie_m, nu, hamta_wfs
    )
    osakerheter = osakerheter + _upphavt_konflikter(komplement, analyser)

    # Byggnaden närmast klicket — aldrig ett hårt fel: en punkt utan byggnader
    # inom radien är ett giltigt (om ointressant) Fall 7-svar, inte en krasch.
    try:
        vald = _valj_byggnad(byggnader, punkt, radie_m)
    except ValueError:
        vald = None
    vald_byggnad_id = str(vald.get("id")) if vald is not None else None

    traff_analyser = [a for a in analyser if a.laege in ("inom", "delvis")]
    if vald_byggnad_id is not None:
        # Stabil sortering: den valda byggnadens träff (om någon) hamnar
        # först, resten behåller sin inbördes ordning — görs FÖRE trunkering
        # så den alltid finns med i svaret.
        traff_analyser = sorted(
            traff_analyser, key=lambda a: a.byggnad_id != vald_byggnad_id
        )
    traffar = []
    for analys in traff_analyser[:_MAX_TRAFFAR_I_SVAR]:
        lage = juridik[analys.byggnad_id]
        traff = {
            "byggnad_id": analys.byggnad_id,
            "laege": analys.laege,
            "zon_referenser": analys.zon_referenser,
            "byggnads_ar": lage.byggnads_ar,
            "gallde_vid_uppforande": lage.gallde_vid_uppforande,
            "dispens_kravs_idag": lage.dispens_kravs_idag,
            "preskriberas": lage.preskriberas,
        }
        if analys.laege == "delvis":
            traff["andel_inom"] = round(analys.andel_inom, 2)
        if lage.atgarder:
            traff["atgarder"] = lage.atgarder
        extra = komplement.get(analys.byggnad_id, {})
        if extra.get(UTVIDGAT_LAYER):
            traff["utvidgat_strandskydd"] = extra[UTVIDGAT_LAYER]
        if extra.get(UPPHAVT_LAYER):
            traff["upphavt_strandskydd"] = extra[UPPHAVT_LAYER]
        traffar.append(traff)

    resultat = {
        "punkt": {"easting": punkt[0], "northing": punkt[1], "crs": CRS},
        "radie_m": radie_m,
        "antal_byggnader": len(analyser),
        "antal_traffar": len(traff_analyser),
        "antal_utanfor": len(analyser) - len(traff_analyser),
        "vald_byggnad_id": vald_byggnad_id,
        "traffar": traffar,
        "juridisk_not": M("runner.juridisk_not"),
        "osakerheter": osakerheter,
        "kallor": [
            {"beskrivning": f"{BYGGNAD_LAYER} (WFS)", "url": _getfeature_url(ows_url, BYGGNAD_LAYER, bbox)},
            {"beskrivning": f"{STRANDSKYDD_LAYER} (WFS)", "url": _getfeature_url(ows_url, STRANDSKYDD_LAYER, bbox)},
            {"beskrivning": "Miljöbalken 7 kap. (SFS 1998:808)", "url": REGELVERK_KALLA_URL},
        ],
        "hamtad": nu,
    }
    if len(traff_analyser) > _MAX_TRAFFAR_I_SVAR:
        resultat["traffar_trunkerade_till"] = _MAX_TRAFFAR_I_SVAR
    return resultat


def kor_fall7(
    ows_url: str,
    punkt: tuple[float, float],
    radie_m: float,
    ut_katalog: Path,
    nu: str,
    ar: list[int] | None = None,
    hamta_wfs: Callable = hamta_wfs_robust,
    hamta_wms: Callable | None = None,
) -> Path:
    """Run the Fall 7 slice around a point and write dossier.md + tidslinje PNGs.

    Args:
        ows_url: GeoServer OWS endpoint.
        punkt: (easting, northing) in EPSG:3014 — the handläggare's map click.
        radie_m: Half-side of the square search box around the point, metres.
        ut_katalog: Output directory (created if missing).
        nu: ISO timestamp stamped on every källa (injected: scripts stay
            deterministic and testable).
        ar: Ortofoto years for the tidslinje (default: all 18 verified).
        hamta_wfs / hamta_wms: Fetchers, injectable for tests.

    Returns:
        Path to the written dossier.md.
    """
    bbox, _byggnader, analyser, juridik, osakerheter, komplement = _hamta_underlag(
        ows_url, punkt, radie_m, nu, hamta_wfs
    )
    osakerheter = osakerheter + _upphavt_konflikter(komplement, analyser)
    e, n = punkt

    regellager_kallor = {
        lager: Kalla(
            beskrivning=f"{lager} (WFS)",
            url=_getfeature_url(ows_url, lager, bbox),
            hamtad=nu,
        )
        for lager in KOMPLETTERANDE_REGELLAGER
    }
    komplement_fakta: dict[str, list[Fakta]] = {}
    for byggnad_id, per_lager in komplement.items():
        komplement_fakta[byggnad_id] = [
            Fakta(
                f"Byggnad {byggnad_id} berör även område med "
                f"{'utvidgat' if lager == UTVIDGAT_LAYER else 'upphävt'} strandskydd "
                f"({', '.join(refs)}).",
                regellager_kallor[lager],
            )
            for lager, refs in per_lager.items()
        ]

    dossier = bygg_dossier(
        rubrik=(
            f"Strandskyddskontroll — punkt E {e:.0f}, N {n:.0f} ({CRS}), "
            f"radie {radie_m:.0f} m"
        ),
        analyser=analyser,
        byggnad_kalla=Kalla(
            beskrivning=f"{BYGGNAD_LAYER} (WFS)",
            url=_getfeature_url(ows_url, BYGGNAD_LAYER, bbox),
            hamtad=nu,
        ),
        strandskydd_kalla=Kalla(
            beskrivning=f"{STRANDSKYDD_LAYER} (WFS)",
            url=_getfeature_url(ows_url, STRANDSKYDD_LAYER, bbox),
            hamtad=nu,
        ),
        extra_osakerheter=osakerheter,
        juridik=juridik,
        regelverk_kalla=Kalla(
            beskrivning="Miljöbalken 7 kap. (SFS 1998:808)",
            url=REGELVERK_KALLA_URL,
            hamtad=nu,
            referens="MB 7 kap. 13-18h §§",
        ),
        extra_fakta_per_byggnad=komplement_fakta,
    )

    tidslinje_kwargs = {"hamta": hamta_wms} if hamta_wms is not None else {}
    bilder = hamta_tidslinje(ows_url, bbox, crs=CRS, ar=ar, **tidslinje_kwargs)

    ut_katalog.mkdir(parents=True, exist_ok=True)
    tidslinje_katalog = ut_katalog / "tidslinje"
    tidslinje_katalog.mkdir(exist_ok=True)
    for bild in bilder:
        (tidslinje_katalog / f"ortofoto_{bild.ar}.png").write_bytes(bild.png)

    md = render_markdown(dossier)
    md += "\n## Bilaga: ortofoto-tidslinje\n\n"
    for bild in bilder:
        flagga = " ⚠ misstänkt tom bild (kontrollera täckning)" if bild.misstankt_tom else ""
        md += f"- [{bild.ar}](tidslinje/ortofoto_{bild.ar}.png) — {bild.layer}{flagga}\n"

    dossier_fil = ut_katalog / "dossier.md"
    dossier_fil.write_text(md, encoding="utf-8")
    return dossier_fil


# Prototype honesty: no permit register is reachable yet — every Fall 1
# result must say so explicitly, never silently omit it.
_BYGGLOVSREGISTER_OSAKERHET = M("runner.bygglovsregister_saknas")


def _valj_byggnad(byggnader: dict, punkt: tuple[float, float], radie_m: float):
    """Pick the target building: containing the point, else nearest by distance."""
    features = byggnader.get("features", [])
    if not features:
        raise ValueError(
            M(
                "runner.ingen_byggnad_hittad",
                radie_m=radie_m,
                easting=punkt[0],
                northing=punkt[1],
            )
        )

    p = Point(punkt)
    innehallande = None
    narmast = None
    narmast_avstand = None
    for feature in features:
        geom = shape(feature["geometry"])
        if innehallande is None and geom.contains(p):
            innehallande = feature
            break
        avstand = geom.distance(p)
        if narmast_avstand is None or avstand < narmast_avstand:
            narmast_avstand = avstand
            narmast = feature

    return innehallande if innehallande is not None else narmast


def _rattighet_post(feature: dict, lager: str) -> dict:
    props = feature.get("properties") or {}
    ar_ga = "rk_ga" in lager
    return {
        "typ": "Gemensamhetsanläggning" if ar_ga else (props.get("Typ") or "Rättighet"),
        "aktbeteckning": props.get("AKTBET") or "",
        "andamal": (props.get("ANM") if ar_ga else props.get("RANDAMAL")) or "",
        "beskrivning": props.get("RBESK") or "",
        "fastighet": props.get("FASTIGHET") or "",
        "lager": lager,
    }


def _rattigheter_for_byggnad(
    ows_url: str,
    footprint,
    bbox: tuple,
    hamta_wfs: Callable,
) -> tuple[list[dict], list[str], list[str]]:
    """(rättigheter som berör footprint, osäkerheter, lager som faktiskt svarade)."""
    traffar: list[dict] = []
    osakerheter: list[str] = []
    svarade: list[str] = []
    sedda: set[tuple[str, str]] = set()
    for lager in RATTIGHET_LAGER:
        try:
            fc = hamta_wfs(ows_url, lager, bbox=bbox, max_features=200)
        except Exception:
            osakerheter.append(M("runner.rattighetslager_otillgangligt", lager=lager))
            continue
        svarade.append(lager)
        osakerheter += _kallforbehall(fc, lager)
        for feature in fc.get("features", []):
            if not feature.get("geometry"):
                continue
            if not force_2d(shape(feature["geometry"])).intersects(footprint):
                continue
            post = _rattighet_post(feature, lager)
            nyckel = (post["typ"], post["aktbeteckning"])
            if nyckel in sedda:
                continue
            sedda.add(nyckel)
            traffar.append(post)
    return traffar[:_MAX_RATTIGHETER], osakerheter, svarade


def _rattighet_fakta(byggnad_id: str, rattigheter: list[dict], ows_url: str, bbox: tuple, nu: str) -> list[Fakta]:
    fakta = []
    for r in rattigheter:
        detalj = r["andamal"] or r["beskrivning"]
        text = f"Byggnad {byggnad_id} berör {r['typ'].lower()} {r['aktbeteckning']}".rstrip()
        if detalj:
            text += f" ({detalj})"
        if r["fastighet"]:
            text += f" på {r['fastighet']}"
        fakta.append(
            Fakta(
                text + ".",
                Kalla(f"{r['lager']} (WFS)", _getfeature_url(ows_url, r["lager"], bbox), hamtad=nu),
            )
        )
    return fakta


def _fall1_underlag(
    ows_url: str,
    punkt: tuple[float, float],
    nu: str,
    radie_m: float,
    ar: list[int] | None,
    hamta_wfs: Callable,
    hamta_wms: Callable | None,
):
    """Fetch + analyse everything both Fall 1 entry points need."""
    e, n = punkt
    bbox_sok = (e - radie_m, n - radie_m, e + radie_m, n + radie_m)

    byggnader = hamta_wfs(ows_url, BYGGNAD_LAYER, bbox=bbox_sok, max_features=500)
    building_feature = _valj_byggnad(byggnader, punkt, radie_m)

    byggnad_id = str(building_feature.get("id"))
    footprint = shape(building_feature["geometry"])
    minx, miny, maxx, maxy = footprint.bounds
    bbox_foot = (minx - 30.0, miny - 30.0, maxx + 30.0, maxy + 30.0)

    tidslinje_kwargs = {"hamta": hamta_wms} if hamta_wms is not None else {}
    bilder = hamta_tidslinje(ows_url, bbox_foot, crs=CRS, ar=ar, **tidslinje_kwargs)

    # `misstankt_tom` in timeline.py is a byte-size heuristic calibrated for
    # full 512x512 search-radius tiles (hundreds of KB); the footprint bbox
    # here is a tight ~building-sized crop whose legitimate content is small
    # by comparison, so that heuristic does not transfer. The dating core
    # gets its own tom-check based on whether any bytes were returned at all;
    # the byte-size flag is still preserved on `bilder` for the tidslinje
    # appendix (⚠ display), unchanged from kor_fall7's convention.
    bilder_for_datering = [
        type(bild)(ar=bild.ar, layer=bild.layer, png=bild.png, misstankt_tom=not bild.png)
        for bild in bilder
    ]
    datering = datera_byggnad(bilder_for_datering, footprint, bbox_foot)

    osakerheter: list[str] = []
    inom_strandskydd = False
    try:
        zoner_fc = hamta_wfs(ows_url, STRANDSKYDD_LAYER, bbox=bbox_sok, max_features=100)
        byggnad_fc = {"type": "FeatureCollection", "features": [building_feature]}
        analyser = analysera_strandskydd(byggnad_fc, zoner_fc)
        inom_strandskydd = bool(analyser) and analyser[0].laege in ("inom", "delvis")
    except Exception:
        inom_strandskydd = False
        osakerheter.append(
            M("runner.strandskyddslager_otillgangligt", lager=STRANDSKYDD_LAYER)
        )

    rattigheter, ratt_osakerheter, _svarade = _rattigheter_for_byggnad(
        ows_url, footprint, bbox_sok, hamta_wfs
    )
    osakerheter += ratt_osakerheter

    area_m2 = footprint.area
    bal_nybyggnadsar = (building_feature.get("properties") or {}).get("bal_nybyggnadsar")

    bedomningsdatum = date.fromisoformat(nu[:10])
    lage = fall1_lage(
        area_m2=area_m2,
        sista_ar_utan=datering.sista_ar_utan,
        forsta_ar_med=datering.forsta_ar_med,
        bedomningsdatum=bedomningsdatum,
        inom_strandskydd=inom_strandskydd,
    )

    osakerheter.append(_BYGGLOVSREGISTER_OSAKERHET)

    return {
        "byggnad_id": byggnad_id,
        "building_feature": building_feature,
        "footprint": footprint,
        "bbox_sok": bbox_sok,
        "bbox_foot": bbox_foot,
        "bilder": bilder,
        "datering": datering,
        "lage": lage,
        "area_m2": area_m2,
        "bal_nybyggnadsar": bal_nybyggnadsar,
        "inom_strandskydd": inom_strandskydd,
        "rattigheter": rattigheter,
        "osakerheter": osakerheter,
    }


def kor_fall1(
    ows_url: str,
    punkt: tuple[float, float],
    ut_katalog: Path,
    nu: str,
    radie_m: float = 100.0,
    ar: list[int] | None = None,
    hamta_wfs: Callable = hamta_wfs_robust,
    hamta_wms: Callable | None = None,
) -> Path:
    """Run the Fall 1 slice around a point and write fall1_dossier.md + tidslinje PNGs.

    Args:
        ows_url: GeoServer OWS endpoint.
        punkt: (easting, northing) in EPSG:3014 — the handläggare's map click.
        ut_katalog: Output directory (created if missing).
        nu: ISO timestamp stamped on every källa (injected: scripts stay
            deterministic and testable).
        radie_m: Half-side of the square search box for the target building, metres.
        ar: Ortofoto years for the tidslinje (default: all 18 verified).
        hamta_wfs / hamta_wms: Fetchers, injectable for tests.

    Returns:
        Path to the written fall1_dossier.md.
    """
    underlag = _fall1_underlag(ows_url, punkt, nu, radie_m, ar, hamta_wfs, hamta_wms)
    e, n = punkt

    dossier = bygg_fall1_dossier(
        rubrik=(
            f"Fall 1 — olovligt byggande? Byggnad {underlag['byggnad_id']} vid "
            f"E {e:.0f}, N {n:.0f} ({CRS})"
        ),
        byggnad_id=underlag["byggnad_id"],
        datering=underlag["datering"],
        lage=underlag["lage"],
        bal_nybyggnadsar=underlag["bal_nybyggnadsar"],
        byggnad_kalla=Kalla(
            f"{BYGGNAD_LAYER} (WFS)",
            _getfeature_url(ows_url, BYGGNAD_LAYER, underlag["bbox_sok"]),
            hamtad=nu,
        ),
        tidslinje_kalla=Kalla(M("kalla.ortofoto_tidslinje"), ows_url, hamtad=nu),
        regelverk_kalla=Kalla(
            M("kalla.pbl_lovbefrielser_regelverk_vid"),
            "https://rkrattsdb.gov.se/SFSdoc/10/100900.PDF",
            hamtad=nu,
            referens="SFS 2010:900",
        ),
        extra_osakerheter=underlag["osakerheter"],
        extra_fakta=_rattighet_fakta(
            underlag["byggnad_id"], underlag["rattigheter"], ows_url, underlag["bbox_sok"], nu
        ),
    )

    ut_katalog.mkdir(parents=True, exist_ok=True)
    tidslinje_katalog = ut_katalog / "tidslinje"
    tidslinje_katalog.mkdir(exist_ok=True)
    bilder = underlag["bilder"]
    for bild in bilder:
        (tidslinje_katalog / f"ortofoto_{bild.ar}.png").write_bytes(bild.png)

    poang_per_ar = underlag["datering"].poang_per_ar

    md = render_markdown(dossier)
    md += "\n## Bilaga: ortofoto-tidslinje\n\n"
    for bild in bilder:
        flagga = " ⚠ misstänkt tom bild (kontrollera täckning)" if bild.misstankt_tom else ""
        poang = f" (poäng {poang_per_ar[bild.ar]:.2f})" if bild.ar in poang_per_ar else ""
        md += f"- [{bild.ar}](tidslinje/ortofoto_{bild.ar}.png) — {bild.layer}{poang}{flagga}\n"

    dossier_fil = ut_katalog / "fall1_dossier.md"
    dossier_fil.write_text(md, encoding="utf-8")
    return dossier_fil


def analysera_fall1_punkt(
    ows_url: str,
    punkt: tuple[float, float],
    nu: str,
    radie_m: float = 100.0,
    ar: list[int] | None = None,
    hamta_wfs: Callable = hamta_wfs_robust,
    hamta_wms: Callable | None = None,
) -> dict:
    """Compact, MCP-friendly Fall 1 analysis (olovligt byggande?) at a point.

    Returns plain JSON-serialisable data: dating interval, BAL cross-check,
    bygglovsplikt + PBL-klockor, declared uncertainties and källa URLs. Never
    geometry, never imagery — references only.
    """
    underlag = _fall1_underlag(ows_url, punkt, nu, radie_m, ar, hamta_wfs, hamta_wms)
    datering = underlag["datering"]
    lage = underlag["lage"]
    bal_nybyggnadsar = underlag["bal_nybyggnadsar"]

    bal_forenligt = None
    if (
        bal_nybyggnadsar is not None
        and datering.sista_ar_utan is not None
        and datering.forsta_ar_med is not None
    ):
        bal_forenligt = datering.sista_ar_utan < bal_nybyggnadsar <= datering.forsta_ar_med

    poang_per_ar = {ar_: round(p, 2) for ar_, p in datering.poang_per_ar.items()}
    narvaro_per_ar = {str(ar_): kl for ar_, kl in datering.narvaro_per_ar.items()}

    osakerheter = list(datering.anmarkningar) + list(lage.atgarder) + list(underlag["osakerheter"])

    return {
        "byggnad_id": underlag["byggnad_id"],
        "punkt": {"easting": punkt[0], "northing": punkt[1], "crs": CRS},
        "area_m2": round(underlag["area_m2"], 1),
        "sista_ar_utan": datering.sista_ar_utan,
        "forsta_ar_med": datering.forsta_ar_med,
        "bal_nybyggnadsar": bal_nybyggnadsar,
        "bal_forenligt": bal_forenligt,
        "bygglov_kravdes": lage.bygglov_kravdes,
        "lovbefrielse": lage.lovbefrielse,
        "rattelse_preskriberad": lage.rattelse_preskriberad,
        "sanktionsavgift_mojlig": lage.sanktionsavgift_mojlig,
        "matningskritiskt": lage.matningskritiskt,
        "inom_strandskydd": underlag["inom_strandskydd"],
        "rattigheter": underlag["rattigheter"],
        "poang_per_ar": poang_per_ar,
        "narvaro_per_ar": narvaro_per_ar,
        "uteslutna_ar": datering.uteslutna_ar,
        "osakerheter": osakerheter,
        "kallor": [
            {
                "beskrivning": f"{BYGGNAD_LAYER} (WFS)",
                "url": _getfeature_url(ows_url, BYGGNAD_LAYER, underlag["bbox_sok"]),
            },
            {
                "beskrivning": M("kalla.pbl_lovbefrielser_preskription"),
                "url": "https://rkrattsdb.gov.se/SFSdoc/10/100900.PDF",
            },
        ],
        "hamtad": nu,
    }


# Prototype honesty: the lov archive is a SYNTETISKT mock-ByggR testarkiv, not
# the kommunens verkliga ärendesystem — every Fall 3 result must say so.
_LOVARKIV_OSAKERHET = M("runner.lovarkiv_syntetiskt")

_INGET_LOV_MEDDELANDE = M("runner.inget_lov_i_arkivet")


def _fall3_underlag(
    ows_url: str,
    punkt: tuple[float, float],
    nu: str,
    radie_m: float,
    ar: list[int] | None,
    hamta_wfs: Callable,
    hamta_wms: Callable | None,
    lovarkiv_katalog: Path,
    ocr: Callable | None,
    hamta_snedbilder: Callable | None = None,
):
    """Fetch + analyse everything both Fall 3 entry points need."""
    hamta_snedbilder = hamta_snedbilder or SNEDBILDER_VID_PUNKT
    e, n = punkt
    bbox_sok = (e - radie_m, n - radie_m, e + radie_m, n + radie_m)

    byggnader = hamta_wfs(ows_url, BYGGNAD_LAYER, bbox=bbox_sok, max_features=500)
    building_feature = _valj_byggnad(byggnader, punkt, radie_m)
    byggnad_id = str(building_feature.get("id"))
    # karta.sundsvall.se's WFS returns 3D (x, y, z) coordinates; EPSG:3014 is a
    # 2D CRS and the z is survey noise — normalize right where the footprint
    # is built so it never reaches the delta/overlay math downstream.
    footprint = force_2d(shape(building_feature["geometry"]))

    lov = hitta_lov(lovarkiv_katalog, punkt=punkt)
    if lov is None:
        return {"lov": None, "byggnad_id": byggnad_id, "bbox_sok": bbox_sok}

    minx, miny, maxx, maxy = footprint.bounds
    bbox_foot = (minx - 30.0, miny - 30.0, maxx + 30.0, maxy + 30.0)

    osakerheter: list[str] = []
    granser = None
    try:
        granser_fc = hamta_wfs(
            ows_url, FASTIGHETSGRANS_LAYER, bbox=bbox_sok, max_features=200
        )
        granser = [shape(f["geometry"]) for f in granser_fc.get("features", [])]
    except Exception:
        granser = None
        osakerheter.append(
            M("runner.granslager_otillgangligt", lager=FASTIGHETSGRANS_LAYER)
        )

    rattigheter, ratt_osakerheter, _svarade = _rattigheter_for_byggnad(
        ows_url, footprint, bbox_sok, hamta_wfs
    )
    osakerheter += ratt_osakerheter

    tidslinje_kwargs = {"hamta": hamta_wms} if hamta_wms is not None else {}
    bilder = hamta_tidslinje(ows_url, bbox_foot, crs=CRS, ar=ar, **tidslinje_kwargs)

    # Same re-flag idiom as _fall1_underlag: the datering core's own tom-check
    # (any bytes at all) replaces the byte-size heuristic, which doesn't
    # transfer to the tight footprint crop used here.
    bilder_for_datering = [
        type(bild)(ar=bild.ar, layer=bild.layer, png=bild.png, misstankt_tom=not bild.png)
        for bild in bilder
    ]
    datering = datera_byggnad(bilder_for_datering, footprint, bbox_foot)

    if lov.godkant_lage.distance(footprint) > 5.0:
        avstand = lov.godkant_lage.distance(footprint)
        osakerheter.append(
            M("runner.lov_byggnad_koppling_osaker", avstand_m=avstand)
        )

    delta = jamfor_lage(lov.godkant_lage, footprint, granser)

    tolkat = None
    korsjamforelse = None
    if lov.handling is not None and lov.handling.exists():
        tolkat = tolka_handling(lov.handling.read_bytes(), ocr=ocr)
        if tolkat.tillganglig:
            korsjamforelse = korsjamfor(tolkat, lov)
    else:
        osakerheter.append(M("runner.ingen_skannad_handling"))

    tolkat_anmarkningar = list(tolkat.anmarkningar) if tolkat is not None else []

    bedomningsdatum = date.fromisoformat(nu[:10])
    lage = fall3_lage(
        beslutsdatum=date.fromisoformat(lov.beslutsdatum),
        sista_ar_utan=datering.sista_ar_utan,
        forsta_ar_med=datering.forsta_ar_med,
        bedomningsdatum=bedomningsdatum,
        delta=delta,
    )

    osakerheter.append(_LOVARKIV_OSAKERHET)

    # Snedbilder (MapSpace): höjd/utseende är handläggarens egen granskning —
    # vi levererar bilderna och säger vad som inte kunde granskas, aldrig tyst.
    snedbilder = hamta_snedbilder(e, n)
    if snedbilder.get("tillganglig"):
        osakerheter.append(M("runner.hojd_granska_snedbilder", ar=snedbilder.get("ar", [])))
    elif snedbilder.get("orsak") == "ingen MAPSPACE_USERKEY":
        osakerheter.append(M("runner.hojd_ej_kontrollerbar"))
    else:
        osakerheter.append(M("runner.snedbilder_otillgangliga"))

    return {
        "lov": lov,
        "snedbilder": snedbilder,
        "rattigheter": rattigheter,
        "byggnad_id": byggnad_id,
        "footprint": footprint,
        "bbox_sok": bbox_sok,
        "bbox_foot": bbox_foot,
        "bilder": bilder,
        "datering": datering,
        "delta": delta,
        "tolkat_anmarkningar": tolkat_anmarkningar,
        "korsjamforelse": korsjamforelse,
        "lage": lage,
        "granser": granser,
        "osakerheter": osakerheter,
    }


def _varld_till_pixel(punkter, bbox, storlek):
    minx, miny, maxx, maxy = bbox
    bredd, hojd = storlek
    return [
        ((x - minx) / (maxx - minx) * bredd, (maxy - y) / (maxy - miny) * hojd)
        for x, y in punkter
    ]


def _exteriorer(geom):
    """Yield exterior rings for a Polygon or MultiPolygon — never .exterior directly."""
    if hasattr(geom, "geoms"):
        for del_ in geom.geoms:
            yield del_.exterior
    else:
        yield geom.exterior


def _rita_overlay(godkant, verkligt, bbox_foot, bilder) -> Image.Image:
    """Overlay godkänt (blue) vs verkligt (red) läge on the last tidslinje image."""
    basbild = None
    for bild in reversed(bilder):
        if bild.png:
            basbild = Image.open(io.BytesIO(bild.png)).convert("RGB")
            break
    if basbild is None:
        basbild = Image.new("RGB", (512, 512), color="white")

    storlek = basbild.size
    rita = ImageDraw.Draw(basbild)

    for ring in _exteriorer(godkant):
        rita.polygon(_varld_till_pixel(list(ring.coords), bbox_foot, storlek), outline=(40, 80, 255), width=3)
    for ring in _exteriorer(verkligt):
        rita.polygon(_varld_till_pixel(list(ring.coords), bbox_foot, storlek), outline=(230, 40, 40), width=3)
    rita.text((5, 5), "BLÅ = godkänt läge, RÖD = verkligt läge", fill=(0, 0, 0))

    return basbild


def kor_fall3(
    ows_url: str,
    punkt: tuple[float, float],
    ut_katalog: Path,
    nu: str,
    radie_m: float = 100.0,
    ar: list[int] | None = None,
    hamta_wfs: Callable = hamta_wfs_robust,
    hamta_wms: Callable | None = None,
    lovarkiv_katalog: Path = LOVARKIV_KATALOG,
    ocr: Callable | None = None,
    hamta_snedbilder: Callable | None = None,
    hamta_snedbild_utsnitt: Callable | None = None,
) -> Path:
    """Run the Fall 3 slice around a point and write fall3_dossier.md + overlay.png.

    Args:
        ows_url: GeoServer OWS endpoint.
        punkt: (easting, northing) in EPSG:3014 — the handläggare's map click.
        ut_katalog: Output directory (created if missing).
        nu: ISO timestamp stamped on every källa (injected: scripts stay
            deterministic and testable).
        radie_m: Half-side of the square search box for the target building, metres.
        ar: Ortofoto years for the tidslinje (default: all 18 verified).
        hamta_wfs / hamta_wms: Fetchers, injectable for tests.
        lovarkiv_katalog: Directory of synthetic lov JSON records (mock-ByggR).
        ocr: OCR callable, injectable for tests (default: tesseract).
        hamta_snedbilder / hamta_snedbild_utsnitt: MapSpace-hämtare (metadata
            resp. PNG-utsnitt), injectable for tests.

    Returns:
        Path to the written fall3_dossier.md.

    Raises:
        ValueError: no (test)ärende matches the point in the lovarkiv.
    """
    underlag = _fall3_underlag(
        ows_url, punkt, nu, radie_m, ar, hamta_wfs, hamta_wms, lovarkiv_katalog, ocr,
        hamta_snedbilder,
    )
    if underlag["lov"] is None:
        raise ValueError(
            M("runner.inget_arende_matchar", easting=punkt[0], northing=punkt[1])
        )

    e, n = punkt
    lov = underlag["lov"]

    handling_kalla = None
    if underlag["korsjamforelse"] is not None:
        handling_kalla = Kalla(
            beskrivning=M("kalla.skannad_handling", dnr=lov.dnr),
            url=_kalla_url(lov.handling),
            hamtad=nu,
        )

    grans_kalla = None
    if underlag["granser"] is not None:
        grans_kalla = Kalla(
            beskrivning=f"{FASTIGHETSGRANS_LAYER} (WFS)",
            url=_getfeature_url(ows_url, FASTIGHETSGRANS_LAYER, underlag["bbox_sok"]),
            hamtad=nu,
        )

    dossier = bygg_fall3_dossier(
        rubrik=(
            f"Fall 3 — lovavvikelse? Byggnad {underlag['byggnad_id']} vid "
            f"E {e:.0f}, N {n:.0f} ({CRS})"
        ),
        lov=lov,
        korsjamforelse=underlag["korsjamforelse"],
        tolkat_anmarkningar=underlag["tolkat_anmarkningar"],
        delta=underlag["delta"],
        datering=underlag["datering"],
        lage=underlag["lage"],
        lov_kalla=Kalla(
            beskrivning=M("kalla.lovarkiv_syntetiskt", dnr=lov.dnr),
            url=_kalla_url(lov.kalla_fil),
            hamtad=nu,
        ),
        handling_kalla=handling_kalla,
        byggnad_kalla=Kalla(
            f"{BYGGNAD_LAYER} (WFS)",
            _getfeature_url(ows_url, BYGGNAD_LAYER, underlag["bbox_sok"]),
            hamtad=nu,
        ),
        grans_kalla=grans_kalla,
        tidslinje_kalla=Kalla(M("kalla.ortofoto_tidslinje"), ows_url, hamtad=nu),
        regelverk_kalla=Kalla(
            M("kalla.pbl_apbl_overgang_regelverk_vid"),
            "https://rkrattsdb.gov.se/SFSdoc/10/100900.PDF",
            hamtad=nu,
            referens="SFS 2010:900 p. 2",
        ),
        extra_osakerheter=underlag["osakerheter"],
        extra_fakta=_rattighet_fakta(
            underlag["byggnad_id"], underlag["rattigheter"], ows_url, underlag["bbox_sok"], nu
        ),
    )

    ut_katalog.mkdir(parents=True, exist_ok=True)
    tidslinje_katalog = ut_katalog / "tidslinje"
    tidslinje_katalog.mkdir(exist_ok=True)
    bilder = underlag["bilder"]
    for bild in bilder:
        (tidslinje_katalog / f"ortofoto_{bild.ar}.png").write_bytes(bild.png)

    overlay = _rita_overlay(
        lov.godkant_lage, underlag["footprint"], underlag["bbox_foot"], bilder
    )
    overlay.save(ut_katalog / "overlay.png")

    md = render_markdown(dossier)
    md += "\n## Bilaga: ortofoto-tidslinje\n\n"
    for bild in bilder:
        flagga = " ⚠ misstänkt tom bild (kontrollera täckning)" if bild.misstankt_tom else ""
        md += f"- [{bild.ar}](tidslinje/ortofoto_{bild.ar}.png) — {bild.layer}{flagga}\n"
    md += "\n## Bilaga: överlagring\n\n"
    md += "- [overlay.png](overlay.png) — BLÅ = godkänt läge, RÖD = verkligt läge\n"

    snedbilder = underlag["snedbilder"]
    if snedbilder.get("tillganglig"):
        hamta_utsnitt = hamta_snedbild_utsnitt or SNEDBILD_UTSNITT
        md += "\n## Bilaga: snedbilder (MapSpace)\n\n"
        md += (
            "Underlag för handläggarens egen granskning av höjd och utseende — "
            "punkten är markerad med röd ring.\n\n"
        )
        sned_katalog = ut_katalog / "snedbilder"
        sned_katalog.mkdir(exist_ok=True)
        for bild in snedbilder.get("bilder", []):
            png = hamta_utsnitt(e, n, bild["riktning"])
            if not png:
                continue
            fil = sned_katalog / f"snedbild_{bild['riktning']}_{bild['datum']}.png"
            fil.write_bytes(png)
            md += (
                f"- [{bild['riktning']} {bild['datum']}](snedbilder/{fil.name}) — "
                f"© {bild.get('copyright', '')}\n"
            )
        if snedbilder.get("viewer_url"):
            md += f"- [Öppna i MapSpace-visaren]({snedbilder['viewer_url']})\n"

    dossier_fil = ut_katalog / "fall3_dossier.md"
    dossier_fil.write_text(md, encoding="utf-8")
    return dossier_fil


def analysera_fall3_punkt(
    ows_url: str,
    punkt: tuple[float, float],
    nu: str,
    radie_m: float = 100.0,
    ar: list[int] | None = None,
    hamta_wfs: Callable = hamta_wfs_robust,
    hamta_wms: Callable | None = None,
    lovarkiv_katalog: Path = LOVARKIV_KATALOG,
    ocr: Callable | None = None,
    hamta_snedbilder: Callable | None = None,
) -> dict:
    """Compact, MCP-friendly Fall 3 analysis (lovavvikelse?) at a point.

    Returns plain JSON-serialisable data: delta godkänt vs verkligt läge,
    time-aware PBL position, declared uncertainties and källa URLs. Never
    geometry, never imagery — references only.
    """
    underlag = _fall3_underlag(
        ows_url, punkt, nu, radie_m, ar, hamta_wfs, hamta_wms, lovarkiv_katalog, ocr,
        hamta_snedbilder,
    )

    if underlag["lov"] is None:
        return {
            "lov_hittat": False,
            "byggnad_id": underlag["byggnad_id"],
            "punkt": {"easting": punkt[0], "northing": punkt[1], "crs": CRS},
            "meddelande": _INGET_LOV_MEDDELANDE,
            "osakerheter": [_LOVARKIV_OSAKERHET],
            "hamtad": nu,
        }

    lov = underlag["lov"]
    delta = underlag["delta"]
    lage = underlag["lage"]
    datering = underlag["datering"]

    osakerheter = (
        list(datering.anmarkningar)
        + list(lage.matningskritiska)
        + list(lage.atgarder)
        + list(delta.anmarkningar)
        + list(underlag["tolkat_anmarkningar"])
        + list(underlag["osakerheter"])
    )

    def _r(x):
        return round(x, 1) if x is not None else None

    return {
        "byggnad_id": underlag["byggnad_id"],
        "punkt": {"easting": punkt[0], "northing": punkt[1], "crs": CRS},
        "lov_hittat": True,
        "dnr": lov.dnr,
        "beslutsdatum": lov.beslutsdatum,
        "pbl_vid_beslut": lage.pbl_vid_beslut,
        "overgangsregel_tillampad": lage.overgangsregel_tillampad,
        "godkand_area_m2": _r(delta.godkand_area_m2),
        "verklig_area_m2": _r(delta.verklig_area_m2),
        "area_diff_m2": _r(delta.area_diff_m2),
        "area_diff_procent": _r(delta.area_diff_procent),
        "utanfor_godkant_m2": _r(delta.utanfor_godkant_m2),
        "avstand_grans_godkant_m": _r(delta.avstand_grans_godkant_m),
        "avstand_grans_verklig_m": _r(delta.avstand_grans_verklig_m),
        "korsjamforelse": underlag["korsjamforelse"],
        "sista_ar_utan": datering.sista_ar_utan,
        "forsta_ar_med": datering.forsta_ar_med,
        "rattelse_preskriberad": lage.rattelse_preskriberad,
        "sanktionsavgift_mojlig": lage.sanktionsavgift_mojlig,
        "matningskritiska": lage.matningskritiska,
        "rattigheter": underlag["rattigheter"],
        "snedbilder": _snedbilder_kompakt(underlag["snedbilder"]),
        "osakerheter": osakerheter,
        "kallor": [
            {
                "beskrivning": f"{BYGGNAD_LAYER} (WFS)",
                "url": _getfeature_url(ows_url, BYGGNAD_LAYER, underlag["bbox_sok"]),
            },
            {
                "beskrivning": M("kalla.lovarkiv_syntetiskt", dnr=lov.dnr),
                "url": _kalla_url(lov.kalla_fil),
            },
            {
                "beskrivning": M("kalla.pbl_apbl_overgang"),
                "url": "https://rkrattsdb.gov.se/SFSdoc/10/100900.PDF",
            },
            *(
                [{"beskrivning": M("kalla.snedbilder_mapspace"), "url": underlag["snedbilder"]["viewer_url"]}]
                if underlag["snedbilder"].get("tillganglig")
                else []
            ),
        ],
        "hamtad": nu,
    }


def _snedbilder_kompakt(snedbilder: dict) -> dict:
    """Eneo-vänlig sammanfattning: riktningar/årgångar + visarlänk, aldrig bilddata."""
    if not snedbilder.get("tillganglig"):
        return {"tillganglig": False, "orsak": snedbilder.get("orsak")}
    return {
        "tillganglig": True,
        "riktningar": [b["riktning"] for b in snedbilder.get("bilder", [])],
        "ar": snedbilder.get("ar", []),
        "viewer_url": snedbilder.get("viewer_url"),
    }


def fall3_geometri(
    ows_url: str,
    punkt: tuple[float, float],
    nu: str,
    radie_m: float = 100.0,
    hamta_wfs: Callable = hamta_wfs_robust,
    lovarkiv_katalog: Path = LOVARKIV_KATALOG,
) -> dict:
    """Hämta godkänt och verkligt läge som GeoJSON för karta-overlay (Fall 3).

    Till skillnad från `analysera_fall3_punkt` (kompakt JSON, inga geometrier —
    Eneo-kontraktet) returnerar denna funktion faktiska polygoner i EPSG:3014,
    avsedda för Origo-pluginets kartlager, aldrig för Eneo-verktygen.

    Args:
        ows_url: GeoServer OWS endpoint.
        punkt: (easting, northing) i EPSG:3014 — kartklicket.
        nu: ISO-tidsstämpel (injiceras för deterministiska tester).
        radie_m: Sökradie i meter runt punkten (standard 100).
        hamta_wfs: WFS-hämtare, injicerbar för tester.
        lovarkiv_katalog: Katalog med syntetiska lov-poster (mock-ByggR).

    Returns:
        {"lov_hittat": bool, "godkant_lage": GeoJSON | None,
         "verkligt_lage": GeoJSON | None, "dnr": str | None}
    """
    e, n = punkt
    bbox = (e - radie_m, n - radie_m, e + radie_m, n + radie_m)

    byggnader = hamta_wfs(ows_url, BYGGNAD_LAYER, bbox=bbox, max_features=500)
    building_feature = _valj_byggnad(byggnader, punkt, radie_m)
    footprint = force_2d(shape(building_feature["geometry"]))

    lov = hitta_lov(lovarkiv_katalog, punkt=punkt)
    if lov is None:
        return {
            "lov_hittat": False,
            "godkant_lage": None,
            "verkligt_lage": None,
            "dnr": None,
        }

    return {
        "lov_hittat": True,
        "godkant_lage": mapping(lov.godkant_lage),
        "verkligt_lage": mapping(footprint),
        "dnr": lov.dnr,
    }


def fall7_geometri(
    ows_url: str,
    punkt: tuple[float, float],
    nu: str,
    radie_m: float = 150.0,
    hamta_wfs: Callable = hamta_wfs_robust,
) -> dict:
    """Hämta alla träffars byggnadspolygoner som GeoJSON för radar-lite (Fall 7).

    Till skillnad från `analysera_punkt` (kompakt JSON, inga geometrier —
    Eneo-kontraktet) returnerar denna funktion faktiska polygoner i EPSG:3014,
    avsedda för Origo-pluginets kartlager — aldrig ett MCP-verktyg (samma
    gräns som `fall3_geometri`). Använder samma `_hamta_underlag` + juridiska
    resultat som `analysera_punkt`, så siffrorna i den kompakta träffen och
    polygonen på kartan alltid är samma.

    Args:
        ows_url: GeoServer OWS endpoint.
        punkt: (easting, northing) i EPSG:3014 — kartklicket.
        nu: ISO-tidsstämpel (injiceras för deterministiska tester).
        radie_m: Sökradie i meter runt punkten (standard 150).
        hamta_wfs: WFS-hämtare, injicerbar för tester.

    Returns:
        GeoJSON FeatureCollection (EPSG:3014, se "crs"): en Feature per träff
        (ALLA, ingen trunkering) med properties {byggnad_id, laege,
        byggnads_ar, gallde_vid_uppforande, dispens_kravs_idag, preskriberas,
        har_atgarder, rang} — `rang` från `rangordna_traffar` (1 = mest
        underlag för granskning). Plus "antal_traffar" och "vald_byggnad_id".

    Raises:
        ValueError: ingen byggnad hittades inom radien.
    """
    bbox, byggnader, analyser, juridik, osakerheter, komplement = _hamta_underlag(
        ows_url, punkt, radie_m, nu, hamta_wfs
    )
    vald = _valj_byggnad(byggnader, punkt, radie_m)
    vald_byggnad_id = str(vald.get("id"))

    geometri_per_id = {
        str(f.get("id")): f.get("geometry") for f in byggnader.get("features", [])
    }

    traffar = []
    for analys in analyser:
        if analys.laege not in ("inom", "delvis"):
            continue
        lage = juridik[analys.byggnad_id]
        traffar.append(
            {
                "byggnad_id": analys.byggnad_id,
                "laege": analys.laege,
                "byggnads_ar": lage.byggnads_ar,
                "gallde_vid_uppforande": lage.gallde_vid_uppforande,
                "dispens_kravs_idag": lage.dispens_kravs_idag,
                "preskriberas": lage.preskriberas,
                "har_atgarder": bool(lage.atgarder),
            }
        )

    features = []
    for traff in rangordna_traffar(traffar):
        geom = geometri_per_id.get(traff["byggnad_id"])
        if geom is None:
            continue
        features.append(
            {
                "type": "Feature",
                "geometry": mapping(force_2d(shape(geom))),
                "properties": traff,
            }
        )

    return {
        "type": "FeatureCollection",
        "crs": CRS,
        "features": features,
        "antal_traffar": len(traffar),
        "vald_byggnad_id": vald_byggnad_id,
    }

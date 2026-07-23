"""Fall 7-körning: punkt -> WFS-hämtning -> analys -> dossier + tidslinje på disk.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

from __future__ import annotations

import io
from datetime import date
from pathlib import Path
from typing import Callable
from urllib.parse import urlencode

from mcp_ogc.tools.wfs import query_wfs_features

from PIL import Image, ImageDraw
from shapely import force_2d
from shapely.geometry import Point, mapping, shape

from geo_tillsyn.analysis import analysera_strandskydd
from geo_tillsyn.datering import datera_byggnad
from geo_tillsyn.delta import jamfor_lage
from geo_tillsyn.dossier import Kalla, render_markdown
from geo_tillsyn.fall1 import bygg_fall1_dossier
from geo_tillsyn.fall3 import bygg_fall3_dossier
from geo_tillsyn.fall7 import bygg_dossier
from geo_tillsyn.juridik import fall1_lage, fall3_lage, juridiskt_lage
from geo_tillsyn.lovarkiv import hitta_lov
from geo_tillsyn.lovtolk import korsjamfor, tolka_handling
from geo_tillsyn.timeline import hamta_tidslinje

BYGGNAD_LAYER = "SundsvallsKommun:bal_byggnad_yta"
STRANDSKYDD_LAYER = "SundsvallsKommun:lm_strandskydd_y"

# Complementary RULE layers that legally narrow or widen the zone. Broken
# server-side on karta.sundsvall.se (GeoServer exception, verified 2026-07-17);
# the runner still tries them each run and reports failure as uncertainty.
KOMPLETTERANDE_REGELLAGER = [
    "Lansstyrelsen:UtvidgatStrandskydd_yta",
    "Lansstyrelsen:UpphavdaStrandskydd_yta",
]

CRS = "EPSG:3014"  # native CRS of the kommun's WFS layers

FASTIGHETSGRANS_LAYER = "SundsvallsKommun:FastighetGrans_linje"

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
    for lager in KOMPLETTERANDE_REGELLAGER:
        try:
            hamta_wfs(ows_url, lager, bbox=bbox, max_features=100)
        except Exception:
            osakerheter.append(
                f"{lager} kunde inte hämtas (källan otillgänglig); "
                "zonens exakta utbredning är inte fullständigt kontrollerad."
            )
    osakerheter.append(
        "Beviljade strandskyddsdispenser har inte kontrollerats mot dispensregistret."
    )

    analyser = analysera_strandskydd(byggnader, strandskydd)

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
    return bbox, byggnader, analyser, juridik, osakerheter


# Eneo's MCP client truncates tool output at 8 kB — cap the per-building list
# and declare the truncation (docs/spike-a-eneo-findings.md). 15 keeps a real
# response under the cap (measured live: 27 träffar serialised to 12.3 kB).
_MAX_TRAFFAR_I_SVAR = 15


def analysera_punkt(
    ows_url: str,
    punkt: tuple[float, float],
    radie_m: float,
    nu: str,
    hamta_wfs: Callable = query_wfs_features,
) -> dict:
    """Compact, MCP-friendly strandskydd analysis around a point.

    Returns plain JSON-serialisable data: per-building läge + time-aware legal
    position, declared uncertainties and källa URLs. Never geometry, never
    imagery — references only.
    """
    bbox, byggnader, analyser, juridik, osakerheter = _hamta_underlag(
        ows_url, punkt, radie_m, nu, hamta_wfs
    )

    traff_analyser = [a for a in analyser if a.laege in ("inom", "delvis")]
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
        traffar.append(traff)

    resultat = {
        "punkt": {"easting": punkt[0], "northing": punkt[1], "crs": CRS},
        "radie_m": radie_m,
        "antal_byggnader": len(analyser),
        "antal_traffar": len(traff_analyser),
        "antal_utanfor": len(analyser) - len(traff_analyser),
        "traffar": traffar,
        "juridisk_not": (
            "Ingen preskription för strandskyddstillsyn (MÖD 2021:6); "
            "skälighetsbedömning enligt MÖD 2017:16 är handläggarens. "
            "Systemet gör en bedömning — beslutet fattas av handläggaren."
        ),
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
    hamta_wfs: Callable = query_wfs_features,
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
    bbox, _byggnader, analyser, juridik, osakerheter = _hamta_underlag(
        ows_url, punkt, radie_m, nu, hamta_wfs
    )
    e, n = punkt

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
_BYGGLOVSREGISTER_OSAKERHET = (
    "Bygglovsregistret är inte tillgängligt i prototypfasen (Sokigo Nova kräver "
    "TRIP-avtal) — ingen lovprövning har kunnat kontrolleras mot register; "
    "kommunens testärenden används."
)


def _valj_byggnad(byggnader: dict, punkt: tuple[float, float], radie_m: float):
    """Pick the target building: containing the point, else nearest by distance."""
    features = byggnader.get("features", [])
    if not features:
        raise ValueError(
            f"Ingen byggnad hittades inom {radie_m:.0f} m från punkten "
            f"E {punkt[0]:.0f}, N {punkt[1]:.0f}."
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
            f"{STRANDSKYDD_LAYER} kunde inte hämtas (källan otillgänglig) — "
            "strandskyddsläget har inte kunnat kontrolleras."
        )

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
        "osakerheter": osakerheter,
    }


def kor_fall1(
    ows_url: str,
    punkt: tuple[float, float],
    ut_katalog: Path,
    nu: str,
    radie_m: float = 100.0,
    ar: list[int] | None = None,
    hamta_wfs: Callable = query_wfs_features,
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
        tidslinje_kalla=Kalla("Ortofoto-tidslinje 1960–2023 (WMS)", ows_url, hamtad=nu),
        regelverk_kalla=Kalla(
            "PBL lovbefrielser + preskription (regelverk_vid)",
            "https://rkrattsdb.gov.se/SFSdoc/10/100900.PDF",
            hamtad=nu,
            referens="SFS 2010:900",
        ),
        extra_osakerheter=underlag["osakerheter"],
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
    hamta_wfs: Callable = query_wfs_features,
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
        "poang_per_ar": poang_per_ar,
        "osakerheter": osakerheter,
        "kallor": [
            {
                "beskrivning": f"{BYGGNAD_LAYER} (WFS)",
                "url": _getfeature_url(ows_url, BYGGNAD_LAYER, underlag["bbox_sok"]),
            },
            {
                "beskrivning": "PBL lovbefrielser + preskription (SFS 2010:900)",
                "url": "https://rkrattsdb.gov.se/SFSdoc/10/100900.PDF",
            },
        ],
        "hamtad": nu,
    }


# Prototype honesty: the lov archive is a SYNTETISKT mock-ByggR testarkiv, not
# the kommunens verkliga ärendesystem — every Fall 3 result must say so.
_LOVARKIV_OSAKERHET = (
    "Lovuppgifterna kommer ur ett SYNTETISKT testarkiv (mock-ByggR) — "
    "prototypfasen har ingen åtkomst till kommunens ärendesystem."
)

_INGET_LOV_MEDDELANDE = (
    "Inget ärende i (test)arkivet för punkten — se Fall 1-analysen för lovplikt."
)


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
):
    """Fetch + analyse everything both Fall 3 entry points need."""
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
            f"{FASTIGHETSGRANS_LAYER} kunde inte hämtas (källan otillgänglig) — "
            "avstånd till fastighetsgräns har inte kunnat kontrolleras."
        )

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
            "Kopplingen lov–byggnad är inte säkerställd: det godkända läget ligger "
            f"{avstand:.0f} m från den valda byggnaden — kontrollera att ärendet "
            "avser denna byggnad."
        )

    delta = jamfor_lage(lov.godkant_lage, footprint, granser)

    tolkat = None
    korsjamforelse = None
    if lov.handling is not None and lov.handling.exists():
        tolkat = tolka_handling(lov.handling.read_bytes(), ocr=ocr)
        if tolkat.tillganglig:
            korsjamforelse = korsjamfor(tolkat, lov)
    else:
        osakerheter.append(
            "Ingen skannad handling i ärendet — korskontroll ej möjlig."
        )

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
    osakerheter.append(
        "Byggnadens höjd och utseende kan inte kontrolleras mot lovet — flygbilder "
        "ser inte fasader (snedbilder saknas i prototypfasen)."
    )

    return {
        "lov": lov,
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
    hamta_wfs: Callable = query_wfs_features,
    hamta_wms: Callable | None = None,
    lovarkiv_katalog: Path = LOVARKIV_KATALOG,
    ocr: Callable | None = None,
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

    Returns:
        Path to the written fall3_dossier.md.

    Raises:
        ValueError: no (test)ärende matches the point in the lovarkiv.
    """
    underlag = _fall3_underlag(
        ows_url, punkt, nu, radie_m, ar, hamta_wfs, hamta_wms, lovarkiv_katalog, ocr
    )
    if underlag["lov"] is None:
        raise ValueError(
            "Inget (test)ärende i lovarkivet matchar punkten "
            f"E {punkt[0]:.0f}, N {punkt[1]:.0f} — se Fall 1-analysen för lovplikt."
        )

    e, n = punkt
    lov = underlag["lov"]

    handling_kalla = None
    if underlag["korsjamforelse"] is not None:
        handling_kalla = Kalla(
            beskrivning=f"Skannad handling, ärende {lov.dnr}",
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
            beskrivning=f"Lovarkiv (syntetiskt), ärende {lov.dnr}",
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
        tidslinje_kalla=Kalla("Ortofoto-tidslinje 1960–2023 (WMS)", ows_url, hamtad=nu),
        regelverk_kalla=Kalla(
            "PBL/ÄPBL övergångsbestämmelser + preskription (regelverk_vid)",
            "https://rkrattsdb.gov.se/SFSdoc/10/100900.PDF",
            hamtad=nu,
            referens="SFS 2010:900 p. 2",
        ),
        extra_osakerheter=underlag["osakerheter"],
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

    dossier_fil = ut_katalog / "fall3_dossier.md"
    dossier_fil.write_text(md, encoding="utf-8")
    return dossier_fil


def analysera_fall3_punkt(
    ows_url: str,
    punkt: tuple[float, float],
    nu: str,
    radie_m: float = 100.0,
    ar: list[int] | None = None,
    hamta_wfs: Callable = query_wfs_features,
    hamta_wms: Callable | None = None,
    lovarkiv_katalog: Path = LOVARKIV_KATALOG,
    ocr: Callable | None = None,
) -> dict:
    """Compact, MCP-friendly Fall 3 analysis (lovavvikelse?) at a point.

    Returns plain JSON-serialisable data: delta godkänt vs verkligt läge,
    time-aware PBL position, declared uncertainties and källa URLs. Never
    geometry, never imagery — references only.
    """
    underlag = _fall3_underlag(
        ows_url, punkt, nu, radie_m, ar, hamta_wfs, hamta_wms, lovarkiv_katalog, ocr
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
        "osakerheter": osakerheter,
        "kallor": [
            {
                "beskrivning": f"{BYGGNAD_LAYER} (WFS)",
                "url": _getfeature_url(ows_url, BYGGNAD_LAYER, underlag["bbox_sok"]),
            },
            {
                "beskrivning": f"Lovarkiv (syntetiskt), ärende {lov.dnr}",
                "url": _kalla_url(lov.kalla_fil),
            },
            {
                "beskrivning": "PBL/ÄPBL övergångsbestämmelser (SFS 2010:900 p. 2)",
                "url": "https://rkrattsdb.gov.se/SFSdoc/10/100900.PDF",
            },
        ],
        "hamtad": nu,
    }


def fall3_geometri(
    ows_url: str,
    punkt: tuple[float, float],
    nu: str,
    radie_m: float = 100.0,
    hamta_wfs: Callable = query_wfs_features,
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

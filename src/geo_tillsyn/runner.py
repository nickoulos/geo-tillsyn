"""Fall 7-körning: punkt -> WFS-hämtning -> analys -> dossier + tidslinje på disk.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Callable
from urllib.parse import urlencode

from mcp_ogc.tools.wfs import query_wfs_features

from geo_tillsyn.analysis import analysera_strandskydd
from geo_tillsyn.dossier import Kalla, render_markdown
from geo_tillsyn.fall7 import bygg_dossier
from geo_tillsyn.juridik import juridiskt_lage
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

# Miljöbalken as official PDF (rkrattsdb covers SFS 1998:306-2018:159) — every
# time-aware regime fact in the dossier cites primary law, not our dataset.
REGELVERK_KALLA_URL = "https://rkrattsdb.gov.se/SFSdoc/98/980808.PDF"


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

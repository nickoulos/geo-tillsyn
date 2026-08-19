"""Ortofoto-datering: när dök byggnaden upp? (Fall 1 delta-kärna).

Deterministisk och förklarbar — ingen ML. För varje årgång jämförs
pixlarna inom byggnadens footprint med referensåret (senaste användbara
ortofotot, där byggnaden antas finnas): hög korrelation = byggnaden syns,
låg = den saknas. Otydliga år flaggas — vi daterar till ett INTERVALL,
aldrig till en gissning (jfr Konceptbeskrivning §7).

SPDX-License-Identifier: AGPL-3.0-or-later
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field

import numpy as np
from PIL import Image
from shapely import contains_xy

from geo_tillsyn.meddelanden import Meddelande as M
from geo_tillsyn.timeline import TidslinjeBild

# Correlation thresholds against the reference year. Between the two the year
# is ambiguous and is flagged rather than classified.
_NARVARO_GRANS = 0.6
_FRANVARO_GRANS = 0.35

# Fewer usable vintages than this cannot support a dating claim.
_MINSTA_ANTAL_AR = 3

# A no-coverage tile is near-uniform; masked pixels with std-dev below this
# carry no correlation evidence and must never be read as "building absent".
# Content-based on purpose: byte-size heuristics don't transfer to tight
# footprint crops (see _fall1_underlag in runner.py).
_MINSTA_STD = 3.0


@dataclass(frozen=True)
class DateringsResultat:
    """Interval dating of one building from the ortofoto timeline."""

    sista_ar_utan: int | None
    forsta_ar_med: int | None
    poang_per_ar: dict[int, float] = field(default_factory=dict)
    anvanda_ar: list[int] = field(default_factory=list)
    anmarkningar: list[str] = field(default_factory=list)
    narvaro_per_ar: dict[int, str] = field(default_factory=dict)
    uteslutna_ar: list[int] = field(default_factory=list)


def _grayscale(png: bytes) -> np.ndarray:
    with Image.open(io.BytesIO(png)) as img:
        return np.asarray(img.convert("L"), dtype=np.float64)


def _footprint_mask(shape: tuple[int, int], footprint, bbox) -> np.ndarray:
    """Boolean mask of pixels whose centers fall inside the footprint.

    Row 0 is the TOP of the image = bbox max northing.
    """
    hojd, bredd = shape
    minx, miny, maxx, maxy = bbox
    xs = minx + (np.arange(bredd) + 0.5) * (maxx - minx) / bredd
    ys = maxy - (np.arange(hojd) + 0.5) * (maxy - miny) / hojd
    gx, gy = np.meshgrid(xs, ys)
    return contains_xy(footprint, gx.ravel(), gy.ravel()).reshape(shape)


def _klassificera_per_ar(poang: dict[int, float]) -> dict[int, str]:
    """narvaro/franvaro/otydlig per år, samma trösklar som datera_byggnad."""
    resultat: dict[int, str] = {}
    for ar, p in poang.items():
        if p >= _NARVARO_GRANS:
            resultat[ar] = "narvaro"
        elif p <= _FRANVARO_GRANS:
            resultat[ar] = "franvaro"
        else:
            resultat[ar] = "otydlig"
    return resultat


def _korrelation(a: np.ndarray, b: np.ndarray) -> float:
    a = a - a.mean()
    b = b - b.mean()
    norm = np.sqrt((a * a).sum() * (b * b).sum())
    if norm == 0:
        return 0.0
    return float((a * b).sum() / norm)


def datera_byggnad(
    bilder: list[TidslinjeBild],
    footprint,
    bbox: tuple[float, float, float, float],
) -> DateringsResultat:
    """Date a building to the interval [sista_ar_utan, forsta_ar_med].

    Args:
        bilder: Timeline images covering `bbox` (misstankt_tom ones are skipped).
        footprint: Building polygon in the same CRS as bbox.
        bbox: (minx, miny, maxx, maxy) of every image, easting-first.

    Returns:
        DateringsResultat with per-year scores for traceability. When the
        evidence cannot support a claim the bounds are None and the reason is
        spelled out in `anmarkningar` — flag, don't guess.
    """
    anmarkningar: list[str] = []

    anvandbara = sorted(
        (b for b in bilder if not b.misstankt_tom), key=lambda b: b.ar
    )
    hoppade = sorted(b.ar for b in bilder if b.misstankt_tom)
    if hoppade:
        anmarkningar.append(M("datering.argangar_utan_bild", ar=hoppade))

    if len(anvandbara) < _MINSTA_ANTAL_AR:
        anmarkningar.append(
            M("datering.for_fa_argangar", antal=len(anvandbara), minst=_MINSTA_ANTAL_AR)
        )
        return DateringsResultat(
            None, None, {}, [b.ar for b in anvandbara], anmarkningar
        )

    referens_bild = _grayscale(anvandbara[-1].png)
    mask = _footprint_mask(referens_bild.shape, footprint, bbox)
    if not mask.any():
        anmarkningar.append(M("datering.footprint_utan_pixlar"))
        return DateringsResultat(None, None, {}, [], anmarkningar)

    # Content check: drop near-uniform (no-coverage) vintages BEFORE scoring —
    # a flat patch has no signal and must not masquerade as absence evidence.
    patchar: dict[int, np.ndarray] = {}
    innehallslosa: list[int] = []
    for bild in anvandbara:
        arsbild = _grayscale(bild.png)
        if arsbild.shape != referens_bild.shape:
            arsbild = np.asarray(
                Image.fromarray(arsbild.astype(np.uint8)).resize(
                    referens_bild.shape[::-1]
                ),
                dtype=np.float64,
            )
        patch = arsbild[mask]
        if patch.std() < _MINSTA_STD:
            innehallslosa.append(bild.ar)
        else:
            patchar[bild.ar] = patch

    uteslutna_ar = sorted(innehallslosa)
    if innehallslosa:
        anmarkningar.append(M("datering.argangar_utan_innehall", ar=uteslutna_ar))
    anvandbara = [b for b in anvandbara if b.ar in patchar]
    if len(anvandbara) < _MINSTA_ANTAL_AR:
        anmarkningar.append(
            M("datering.for_fa_argangar", antal=len(anvandbara), minst=_MINSTA_ANTAL_AR)
        )
        return DateringsResultat(
            None, None, {}, [b.ar for b in anvandbara], anmarkningar,
            uteslutna_ar=uteslutna_ar,
        )

    referens = patchar[anvandbara[-1].ar]
    poang: dict[int, float] = {
        bild.ar: _korrelation(patchar[bild.ar], referens) for bild in anvandbara
    }

    narvaro = {ar: p >= _NARVARO_GRANS for ar, p in poang.items()}
    franvaro = {ar: p <= _FRANVARO_GRANS for ar, p in poang.items()}
    osakra = [
        ar for ar in poang if not narvaro[ar] and not franvaro[ar]
    ]
    if osakra:
        anmarkningar.append(M("datering.otydliga_argangar", ar=sorted(osakra)))

    ar_stigande = [b.ar for b in anvandbara]

    # First PRESENT year with no clear ABSENCE after it. Ambiguous dips (bad
    # exposure, clouds, registration drift) are flagged above but do not veto
    # the run — only unambiguous absence after presence does.
    forsta_ar_med = None
    for i, ar in enumerate(ar_stigande):
        if narvaro[ar] and not any(franvaro[a] for a in ar_stigande[i + 1 :]):
            forsta_ar_med = ar
            break

    # The reference year matches itself by construction (score 1.0) and thus
    # carries no evidence on its own: presence must be corroborated by at
    # least one earlier vintage.
    if forsta_ar_med == ar_stigande[-1]:
        forsta_ar_med = None

    if forsta_ar_med is None:
        anmarkningar.append(M("datering.ingen_bortom_referensar"))
        return DateringsResultat(
            None, None, poang, ar_stigande, anmarkningar,
            narvaro_per_ar=_klassificera_per_ar(poang), uteslutna_ar=uteslutna_ar,
        )

    fore = [ar for ar in ar_stigande if ar < forsta_ar_med and franvaro[ar]]
    sista_ar_utan = max(fore) if fore else None
    if sista_ar_utan is None:
        anmarkningar.append(M("datering.syns_i_aldsta", ar=forsta_ar_med))

    return DateringsResultat(
        sista_ar_utan=sista_ar_utan,
        forsta_ar_med=forsta_ar_med,
        poang_per_ar=poang,
        anvanda_ar=ar_stigande,
        anmarkningar=anmarkningar,
        narvaro_per_ar=_klassificera_per_ar(poang),
        uteslutna_ar=uteslutna_ar,
    )

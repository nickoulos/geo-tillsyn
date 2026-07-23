"""Syntetisk situationsplan: ritar en 'skannad' handling som raster-PDF (Fall 3).

Prototypen har inga riktiga bygglovshandlingar — vi ritar en fiktiv
situationsplan (Pillow) och packar den som raster-PDF, samma natur som
kommunens skannade 2281K-handlingar. Varje sida bär ett obligatoriskt
vattenmärke; en handling som liknar en myndighetshandling får aldrig
existera omärkt.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

from __future__ import annotations

import io

from PIL import Image, ImageDraw, ImageFont

VATTENMARKE = "SYNTETISK TESTHANDLING — GEO-TILLSYN PROTOTYP"

_BREDD, _HOJD = 1240, 1754  # ~A4 at 150 dpi
_MARGINAL = 60


def _font(storlek: int) -> ImageFont.ImageFont:
    # Deterministic across machines: Pillow's bundled bitmap font as fallback.
    try:
        return ImageFont.truetype("arial.ttf", storlek)
    except OSError:
        try:
            return ImageFont.load_default(storlek)
        except TypeError:
            return ImageFont.load_default()


def rita_situationsplan(
    falt: dict[str, str],
    kontur: list[tuple[float, float]],
    vattenmarke: str,
) -> Image.Image:
    """Draw the synthetic situationsplan: title block, approved outline, stamp.

    `falt` keys are printed as `NYCKEL: värde`, one per line — these labels are
    the OCR contract for lovtolk (Task 3). `kontur` is the approved footprint
    in local metres; it is scaled to fit the drawing area.
    """
    if not vattenmarke.strip():
        raise ValueError("vattenmärke krävs — en omärkt syntetisk handling får inte renderas")

    bild = Image.new("L", (_BREDD, _HOJD), color=245)
    rita = ImageDraw.Draw(bild)

    # Title block
    rita.rectangle([_MARGINAL, _MARGINAL, _BREDD - _MARGINAL, 320], outline=0, width=3)
    rita.text((_MARGINAL + 20, _MARGINAL + 15), "SUNDSVALLS KOMMUN", font=_font(40), fill=0)
    rita.text(
        (_MARGINAL + 20, _MARGINAL + 65),
        "STADSBYGGNADSKONTORET — SITUATIONSPLAN",
        font=_font(28),
        fill=0,
    )
    y = _MARGINAL + 115
    for nyckel, varde in falt.items():
        rita.text((_MARGINAL + 20, y), f"{nyckel}: {varde}", font=_font(26), fill=0)
        y += 36

    # Approved outline, scaled into the drawing area
    xs = [p[0] for p in kontur]
    ys = [p[1] for p in kontur]
    bredd_m = max(xs) - min(xs) or 1.0
    hojd_m = max(ys) - min(ys) or 1.0
    rityta = (200, 420, _BREDD - 200, _HOJD - 400)
    skala = min((rityta[2] - rityta[0]) / bredd_m, (rityta[3] - rityta[1]) / hojd_m) * 0.6
    cx = (rityta[0] + rityta[2]) / 2 - (min(xs) + bredd_m / 2) * skala
    cy = (rityta[1] + rityta[3]) / 2 + (min(ys) + hojd_m / 2) * skala
    punkter = [(cx + x * skala, cy - y_ * skala) for x, y_ in kontur]
    rita.polygon(punkter, outline=0, width=4)
    rita.text((rityta[0], rityta[3] + 20), "GODKANT LAGE (SKALA EJ BINDANDE)", font=_font(24), fill=0)

    # Stamp
    rita.rectangle([_BREDD - 460, _HOJD - 330, _BREDD - _MARGINAL, _HOJD - 210], outline=0, width=5)
    rita.text((_BREDD - 430, _HOJD - 300), "BEVILJAS", font=_font(48), fill=0)

    # Mandatory watermark, twice for visibility
    for wy in (370, _HOJD - 120):
        rita.text((_MARGINAL, wy), vattenmarke, font=_font(30), fill=100)

    return bild


def till_pdf_bytes(bild: Image.Image) -> bytes:
    """Package the drawing as a raster-only, single-page PDF (no text layer)."""
    buf = io.BytesIO()
    bild.convert("L").save(buf, format="PDF", resolution=150.0)
    return buf.getvalue()

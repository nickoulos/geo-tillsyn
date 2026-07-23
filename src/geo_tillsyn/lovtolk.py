"""Lov-tolk: OCR av skannad handling + korskontroll mot registret (Fall 3).

Handlingen är en raster-PDF (som kommunens 2281K-skanningar). pypdfium2
rastrerar, tesseract läser; varje extraherat fält bär sin konfidens och
korskontrolleras mot mock-ByggR-posten — två oberoende källor i öppen
jämförelse (bevisstyrka). Saknas OCR-motorn fortsätter kedjan register-only
med en deklarerad osäkerhet; vi maskerar aldrig ett verktygsbortfall.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable

import pypdfium2 as pdfium
from PIL import Image

from geo_tillsyn.lovarkiv import LovBeslut

_KONFIDENS_GRANS = 0.5

# Label contract with handling.rita_situationsplan — uppercase, no diacritics.
_FALT_MONSTER: dict[str, re.Pattern] = {
    "dnr": re.compile(r"DNR:\s*(SBN\s*\d{4}-\d{4})"),
    "beslutsdatum": re.compile(r"BESLUTSDATUM:\s*(\d{4}-\d{2}-\d{2})"),
    "byggnadsarea_m2": re.compile(r"BYGGNADSAREA:\s*([\d]+[,.]?\d*)\s*m2"),
    "avstand_grans_m": re.compile(r"AVSTAND TILL GRANS:\s*([\d]+[,.]?\d*)\s*m"),
}


@dataclass(frozen=True)
class TolkatFalt:
    varde: str
    konfidens: float


@dataclass(frozen=True)
class TolkatDokument:
    tillganglig: bool
    falt: dict[str, TolkatFalt] = field(default_factory=dict)
    ratext: str = ""
    anmarkningar: list[str] = field(default_factory=list)


def _rasterisera(pdf_bytes: bytes) -> Image.Image:
    dokument = pdfium.PdfDocument(pdf_bytes)
    try:
        return dokument[0].render(scale=2.0).to_pil()
    finally:
        dokument.close()


def _tesseract_ocr(bild: Image.Image) -> tuple[str, float]:
    """Default OCR: tesseract via pytesseract, mean word confidence 0..1."""
    import pytesseract

    data = pytesseract.image_to_data(bild, output_type=pytesseract.Output.DICT)
    konfidenser = [int(k) for k in data["conf"] if str(k).lstrip("-").isdigit() and int(k) >= 0]
    text = pytesseract.image_to_string(bild)
    medel = (sum(konfidenser) / len(konfidenser) / 100.0) if konfidenser else 0.0
    return text, medel


def tolka_handling(
    pdf_bytes: bytes,
    ocr: Callable[[Image.Image], tuple[str, float]] | None = None,
) -> TolkatDokument:
    """OCR the scanned handling and extract the known fields with confidence."""
    bild = _rasterisera(pdf_bytes)
    try:
        text, konfidens = (ocr or _tesseract_ocr)(bild)
    except Exception as fel:
        return TolkatDokument(
            tillganglig=False,
            anmarkningar=[
                "OCR ej tillgänglig — handlingen har inte kunnat verifieras maskinellt "
                f"({type(fel).__name__})."
            ],
        )

    falt: dict[str, TolkatFalt] = {}
    for namn, monster in _FALT_MONSTER.items():
        traff = monster.search(text)
        if traff:
            varde = traff.group(1).replace(",", ".")
            falt[namn] = TolkatFalt(varde=varde, konfidens=konfidens)

    anmarkningar: list[str] = []
    if konfidens < _KONFIDENS_GRANS:
        anmarkningar.append(
            f"OCR-konfidensen är låg ({konfidens:.2f}) — extraherade fält bör "
            "kontrolleras mot handlingen manuellt."
        )
    return TolkatDokument(tillganglig=True, falt=falt, ratext=text, anmarkningar=anmarkningar)


def _normalisera(namn: str, varde) -> str:
    if namn == "byggnadsarea_m2":
        return f"{float(varde):.1f}"
    return re.sub(r"\s+", " ", str(varde)).strip()


def korsjamfor(tolkat: TolkatDokument, lov: LovBeslut) -> dict[str, str]:
    """Per-field comparison OCR vs register: överens / avviker / saknas."""
    register = {
        "dnr": lov.dnr,
        "beslutsdatum": lov.beslutsdatum,
        "byggnadsarea_m2": lov.byggnadsarea_m2,
    }
    resultat: dict[str, str] = {}
    for namn, registervarde in register.items():
        if registervarde is None:
            continue
        ocr_falt = tolkat.falt.get(namn)
        if ocr_falt is None:
            resultat[namn] = "saknas"
        elif _normalisera(namn, ocr_falt.varde) == _normalisera(namn, registervarde):
            resultat[namn] = "överens"
        else:
            resultat[namn] = "avviker"
    return resultat

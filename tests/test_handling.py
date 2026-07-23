"""Unit tests for the synthetic situationsplan renderer (Fall 3).

SPDX-License-Identifier: AGPL-3.0-or-later
"""

import pytest

from geo_tillsyn.handling import VATTENMARKE, rita_situationsplan, till_pdf_bytes

FALT = {
    "DNR": "SBN 2009-0412",
    "BESLUTSDATUM": "2009-06-19",
    "BYGGNADSAREA": "80,0 m2",
    "AVSTAND TILL GRANS": "4,5 m",
}
KONTUR = [(0.0, 0.0), (10.0, 0.0), (10.0, 8.0), (0.0, 8.0)]


def test_ritar_bild_med_deterministiskt_innehall():
    a = rita_situationsplan(FALT, KONTUR, VATTENMARKE)
    b = rita_situationsplan(FALT, KONTUR, VATTENMARKE)

    assert a.size == b.size
    assert a.tobytes() == b.tobytes()


def test_vagrar_rendera_utan_vattenmarke():
    with pytest.raises(ValueError, match="vattenmärke"):
        rita_situationsplan(FALT, KONTUR, "")


def test_vattenmarket_paverkar_bilden():
    med = rita_situationsplan(FALT, KONTUR, VATTENMARKE)
    annan = rita_situationsplan(FALT, KONTUR, "ANNAN MARKERING X")

    assert med.tobytes() != annan.tobytes()


def test_pdf_ar_raster_pdf():
    bild = rita_situationsplan(FALT, KONTUR, VATTENMARKE)
    pdf = till_pdf_bytes(bild)

    assert pdf.startswith(b"%PDF")
    # Raster-only: the page is one embedded image, no text operators.
    assert b"/Image" in pdf and b"Tj" not in pdf

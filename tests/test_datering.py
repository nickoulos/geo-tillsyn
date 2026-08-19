"""Unit tests for ortofoto-based building dating (Fall 1 delta core).

Synthetic, seeded images — hermetic and deterministic. A "building" is a
structured pattern that correlates strongly with itself across years; empty
ground is independent noise that does not.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

import io

import numpy as np
from PIL import Image
from shapely.geometry import box

from geo_tillsyn.datering import datera_byggnad
from geo_tillsyn.timeline import TidslinjeBild

BBOX = (0.0, 0.0, 100.0, 100.0)
FOOTPRINT = box(30.0, 30.0, 70.0, 70.0)
SIZE = 64  # px


def _png(arr: np.ndarray) -> bytes:
    img = Image.fromarray(arr.astype(np.uint8), mode="L")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _mark(ar: int, png: bytes, tom: bool = False) -> TidslinjeBild:
    return TidslinjeBild(ar=ar, layer=f"Orto{ar}", png=png, misstankt_tom=tom)


def _byggnads_monster(rng: np.random.RandomState) -> np.ndarray:
    """Structured 'roof' pattern: bright building block + fine noise."""
    base = np.linspace(40, 80, SIZE, dtype=np.float64)
    arr = np.tile(base, (SIZE, 1))
    arr[18:46, 18:46] = 210.0  # the building footprint region, bright roof
    arr[20:44:4, 20:44] = 160.0  # roof ridges -> texture that self-correlates
    return arr + rng.normal(0, 4, (SIZE, SIZE))


def _mark_utan_byggnad(rng: np.random.RandomState) -> np.ndarray:
    """Empty ground: independent noise per year, no persistent structure."""
    return rng.uniform(30, 120, (SIZE, SIZE))


def _serie(utan_ar: list[int], med_ar: list[int], tomma_ar: list[int] | None = None):
    rng = np.random.RandomState(42)
    bilder = []
    for ar in sorted(utan_ar + med_ar + (tomma_ar or [])):
        if tomma_ar and ar in tomma_ar:
            bilder.append(_mark(ar, _png(np.zeros((SIZE, SIZE))), tom=True))
        elif ar in med_ar:
            bilder.append(_mark(ar, _png(_byggnads_monster(rng))))
        else:
            bilder.append(_mark(ar, _png(_mark_utan_byggnad(rng))))
    return bilder


def test_byggnad_dateras_till_intervall_mellan_franvaro_och_narvaro():
    bilder = _serie(utan_ar=[1998, 2007, 2010], med_ar=[2013, 2015, 2021, 2023])

    resultat = datera_byggnad(bilder, FOOTPRINT, BBOX)

    assert resultat.sista_ar_utan == 2010
    assert resultat.forsta_ar_med == 2013


def test_misstankt_tomma_ar_deltar_inte_i_dateringen():
    bilder = _serie(
        utan_ar=[2007, 2010], med_ar=[2015, 2021, 2023], tomma_ar=[2012, 2016]
    )

    resultat = datera_byggnad(bilder, FOOTPRINT, BBOX)

    assert 2012 not in resultat.anvanda_ar and 2016 not in resultat.anvanda_ar
    assert resultat.sista_ar_utan == 2010
    assert resultat.forsta_ar_med == 2015


def test_byggnad_i_aldsta_bilden_ger_ingen_undre_grans():
    bilder = _serie(utan_ar=[], med_ar=[1998, 2010, 2015, 2023])

    resultat = datera_byggnad(bilder, FOOTPRINT, BBOX)

    assert resultat.sista_ar_utan is None
    assert resultat.forsta_ar_med == 1998
    assert any("äldsta" in a for a in resultat.anmarkningar)


def test_byggnad_som_aldrig_syns_flaggas():
    bilder = _serie(utan_ar=[1998, 2007, 2015, 2023], med_ar=[])

    resultat = datera_byggnad(bilder, FOOTPRINT, BBOX)

    assert resultat.forsta_ar_med is None
    assert any("ej fastställ" in a.lower() for a in resultat.anmarkningar)


def test_for_fa_anvandbara_ar_ger_ej_faststallt():
    bilder = _serie(utan_ar=[2010], med_ar=[2023], tomma_ar=[2013, 2016, 2020])

    resultat = datera_byggnad(bilder, FOOTPRINT, BBOX)

    assert resultat.sista_ar_utan is None and resultat.forsta_ar_med is None
    assert any("ej fastställ" in a.lower() for a in resultat.anmarkningar)


def test_enstaka_otydligt_ar_bryter_inte_narvarokedjan():
    # A single ambiguous vintage (bad exposure, clouds, registration drift)
    # inside the presence run must not veto the dating — only clear ABSENCE
    # after presence does. The ambiguous year is still flagged for review.
    rng = np.random.RandomState(42)
    bilder = _serie(utan_ar=[2007], med_ar=[2010, 2015, 2023])
    # Mostly noise with a faint trace of the structure -> ambiguous band
    # (empirically ~0.43 with these seeds: between _FRANVARO_GRANS 0.35 and
    # _NARVARO_GRANS 0.6).
    suddig = 0.35 * _byggnads_monster(rng) + 0.65 * _mark_utan_byggnad(rng)
    bilder.append(_mark(2021, _png(suddig)))
    bilder.sort(key=lambda b: b.ar)

    resultat = datera_byggnad(bilder, FOOTPRINT, BBOX)

    assert resultat.sista_ar_utan == 2007
    assert resultat.forsta_ar_med == 2010
    assert any("2021" in a for a in resultat.anmarkningar)


def test_innehallslost_ar_utesluts_aven_utan_tom_flagga():
    # A no-coverage tile is near-uniform. Byte-size heuristics don't transfer
    # to tight footprint crops, so the dating core must detect blankness from
    # CONTENT: a flat image carries no correlation evidence and must never be
    # read as "building absent".
    bilder = _serie(utan_ar=[2010, 2013], med_ar=[2015, 2021, 2023])
    platt = np.full((SIZE, SIZE), 128.0)  # uniform gray, NOT flagged tom
    bilder.append(_mark(2016, _png(platt)))
    bilder.sort(key=lambda b: b.ar)

    resultat = datera_byggnad(bilder, FOOTPRINT, BBOX)

    assert 2016 not in resultat.anvanda_ar
    # The flat 2016 tile must not break the presence run 2015->2023.
    assert resultat.sista_ar_utan == 2013
    assert resultat.forsta_ar_med == 2015


def test_poang_redovisas_per_ar_for_sparbarhet():
    bilder = _serie(utan_ar=[2010], med_ar=[2015, 2021, 2023])

    resultat = datera_byggnad(bilder, FOOTPRINT, BBOX)

    # Every used year gets a traceable score; scores separate cleanly.
    assert set(resultat.poang_per_ar) == {2010, 2015, 2021, 2023}
    assert resultat.poang_per_ar[2010] < 0.35
    assert resultat.poang_per_ar[2021] > 0.6


# --- narvaro_per_ar / uteslutna_ar (fastighetsbiografi, verklighet-vy) ------------


def test_narvaro_per_ar_klassificerar_varje_anvant_ar():
    bilder = _serie(utan_ar=[1998, 2007, 2010], med_ar=[2013, 2015, 2021, 2023])

    resultat = datera_byggnad(bilder, FOOTPRINT, BBOX)

    # One classification per year that made it into poang_per_ar — no more, no less.
    assert set(resultat.narvaro_per_ar) == set(resultat.poang_per_ar)
    for ar in (1998, 2007, 2010):
        assert resultat.narvaro_per_ar[ar] == "franvaro"
    for ar in (2013, 2015, 2021):
        assert resultat.narvaro_per_ar[ar] == "narvaro"
    assert resultat.uteslutna_ar == []


def test_otydligt_ar_klassificeras_som_otydlig_i_narvaro_per_ar():
    rng = np.random.RandomState(42)
    bilder = _serie(utan_ar=[2007], med_ar=[2010, 2015, 2023])
    suddig = 0.35 * _byggnads_monster(rng) + 0.65 * _mark_utan_byggnad(rng)
    bilder.append(_mark(2021, _png(suddig)))
    bilder.sort(key=lambda b: b.ar)

    resultat = datera_byggnad(bilder, FOOTPRINT, BBOX)

    assert resultat.narvaro_per_ar[2021] == "otydlig"
    assert resultat.narvaro_per_ar[2007] == "franvaro"
    assert resultat.narvaro_per_ar[2010] == "narvaro"


def test_uteslutna_ar_speglar_innehallslosa_ar():
    bilder = _serie(utan_ar=[2010, 2013], med_ar=[2015, 2021, 2023])
    platt = np.full((SIZE, SIZE), 128.0)  # uniform gray, NOT flagged tom
    bilder.append(_mark(2016, _png(platt)))
    bilder.sort(key=lambda b: b.ar)

    resultat = datera_byggnad(bilder, FOOTPRINT, BBOX)

    assert resultat.uteslutna_ar == [2016]
    assert 2016 not in resultat.narvaro_per_ar


def test_uteslutna_ar_satts_aven_om_for_fa_argangar_kvarstar_efter_filtrering():
    # 2010 + 2016(platt) + 2023 pass the initial >= 3 usable-vintage gate, but
    # dropping the content-less 2016 leaves only 2 -> the "for few years" early
    # return fires. uteslutna_ar must still carry 2016 — the exclusion happened
    # before that gate, and must never be silently dropped.
    bilder = _serie(utan_ar=[2010], med_ar=[2023])
    platt = np.full((SIZE, SIZE), 128.0)
    bilder.append(_mark(2016, _png(platt)))
    bilder.sort(key=lambda b: b.ar)

    resultat = datera_byggnad(bilder, FOOTPRINT, BBOX)

    assert resultat.sista_ar_utan is None and resultat.forsta_ar_med is None
    assert resultat.uteslutna_ar == [2016]
    assert resultat.narvaro_per_ar == {}


def test_narvaro_per_ar_och_uteslutna_ar_defaultar_tomt():
    bilder = _serie(utan_ar=[2010], med_ar=[2023])  # only 2 usable vintages

    resultat = datera_byggnad(bilder, FOOTPRINT, BBOX)

    assert resultat.narvaro_per_ar == {}
    assert resultat.uteslutna_ar == []

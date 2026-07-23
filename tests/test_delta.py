"""Unit tests for the geometric delta engine (Fall 3).

Known-answer geometry: approved 10x8 m at origin; actual 10.9x8.7 m shifted
2 m east — area +18.5 %, centroid shift computable by hand.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

import pytest
from shapely.geometry import LineString, box

from geo_tillsyn.delta import jamfor_lage

GODKANT = box(0.0, 0.0, 10.0, 8.0)          # 80 m²
VERKLIGT = box(2.0, 0.0, 12.9, 8.7)          # 94.83 m², shifted east
GRANS = LineString([(16.0, -10.0), (16.0, 20.0)])  # boundary east of both


def test_areaskillnad_i_m2_och_procent():
    d = jamfor_lage(GODKANT, VERKLIGT)

    assert d.godkand_area_m2 == pytest.approx(80.0)
    assert d.verklig_area_m2 == pytest.approx(94.83)
    assert d.area_diff_m2 == pytest.approx(14.83)
    assert d.area_diff_procent == pytest.approx(18.5, abs=0.1)


def test_centroidforskjutning():
    d = jamfor_lage(GODKANT, VERKLIGT)

    # centroids: (5, 4) vs (7.45, 4.35) -> sqrt(2.45² + 0.35²)
    assert d.centroid_forskjutning_m == pytest.approx(2.4749, abs=0.001)


def test_yta_utanfor_godkant_lage():
    d = jamfor_lage(GODKANT, VERKLIGT)

    assert d.utanfor_godkant_m2 == pytest.approx(VERKLIGT.difference(GODKANT).area)
    assert d.utanfor_godkant_m2 > 0


def test_avstand_till_grans_godkant_vs_verkligt():
    d = jamfor_lage(GODKANT, VERKLIGT, granser=[GRANS])

    assert d.avstand_grans_godkant_m == pytest.approx(6.0)   # 16 - 10
    assert d.avstand_grans_verklig_m == pytest.approx(3.1)   # 16 - 12.9


def test_utan_granser_ar_avstanden_none_med_anmarkning():
    d = jamfor_lage(GODKANT, VERKLIGT)

    assert d.avstand_grans_godkant_m is None
    assert d.avstand_grans_verklig_m is None
    assert any("fastighetsgräns" in a for a in d.anmarkningar)


def test_identiska_lagen_ger_nollavvikelse():
    d = jamfor_lage(GODKANT, GODKANT, granser=[GRANS])

    assert d.area_diff_m2 == pytest.approx(0.0)
    assert d.centroid_forskjutning_m == pytest.approx(0.0)
    assert d.utanfor_godkant_m2 == pytest.approx(0.0)

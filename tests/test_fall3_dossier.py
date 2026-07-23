"""Unit tests for the Fall 3 dossier builder.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

import json
from datetime import date
from pathlib import Path

from shapely.geometry import box

from geo_tillsyn.datering import DateringsResultat
from geo_tillsyn.delta import jamfor_lage
from geo_tillsyn.dossier import Kalla, render_markdown
from geo_tillsyn.fall3 import bygg_fall3_dossier
from geo_tillsyn.juridik import fall3_lage
from geo_tillsyn.lovarkiv import hitta_lov

KALLA = Kalla("test", "https://example.com", hamtad="2026-07-23T00:00:00Z")


def _lov(tmp_path: Path, **extra):
    record = {
        "syntetisk": True,
        "anmarkning": "Syntetiskt testärende — inga verkliga byggärenden.",
        "dnr": "SBN 2009-0412",
        "fastighet": "ALNÖ-USLAND 1:45",
        "beslutsdatum": "2009-06-19",
        "atgard": "Nybyggnad av enbostadshus",
        "byggnadsarea_m2": 80.0,
        "godkant_lage": {
            "crs": "EPSG:3014",
            "koordinater": [[0.0, 0.0], [10.0, 0.0], [10.0, 8.0], [0.0, 8.0]],
        },
        "villkor": [],
        "handling": None,
    }
    record.update(extra)
    (tmp_path / "a.json").write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    return hitta_lov(tmp_path, fastighet="ALNÖ-USLAND 1:45")


def _dossier(tmp_path, korsjamforelse=None, verkligt=None, lov_extra=None):
    lov = _lov(tmp_path, **(lov_extra or {}))
    verkligt = verkligt if verkligt is not None else box(2, 0, 12.9, 8.7)
    delta = jamfor_lage(box(0, 0, 10, 8), verkligt)
    datering = DateringsResultat(sista_ar_utan=2007, forsta_ar_med=2010)
    lage = fall3_lage(date(2009, 6, 19), 2007, 2010, date(2026, 7, 23), delta)
    return bygg_fall3_dossier(
        rubrik="Fall 3 — test",
        lov=lov,
        korsjamforelse=korsjamforelse,
        tolkat_anmarkningar=[],
        delta=delta,
        datering=datering,
        lage=lage,
        lov_kalla=KALLA,
        handling_kalla=KALLA if korsjamforelse else None,
        byggnad_kalla=KALLA,
        grans_kalla=None,
        tidslinje_kalla=KALLA,
        regelverk_kalla=KALLA,
    )


def test_lovfaktan_bar_syntetisk_markering(tmp_path):
    md = render_markdown(_dossier(tmp_path))

    assert "SBN 2009-0412" in md
    assert "Syntetiskt testärende" in md


def test_deltafakta_kvantifierar(tmp_path):
    md = render_markdown(_dossier(tmp_path))

    assert "+14,8" in md or "+14.8" in md
    assert "18" in md  # ~ +18.5 %


def test_korsjamforelse_redovisas_nar_den_finns(tmp_path):
    md = render_markdown(
        _dossier(tmp_path, korsjamforelse={"dnr": "överens", "byggnadsarea_m2": "avviker"})
    )

    assert "överens" in md and "avviker" in md


def test_apbl_som_styrande_lag_redovisas(tmp_path):
    md = render_markdown(_dossier(tmp_path))

    assert "ÄPBL" in md
    assert "övergångs" in md.lower()


def test_inga_skuldord_i_bedomningen(tmp_path):
    md = render_markdown(_dossier(tmp_path))
    bedomning = md.split("## 2. Bedömning")[1].split("## 3. Beslut")[0]

    for ord_ in ("olovligt", "överträdelse", "brott"):
        assert ord_ not in bedomning.lower()


def test_vasentlighet_lamnas_till_handlaggaren(tmp_path):
    md = render_markdown(_dossier(tmp_path))

    assert "väsentlig" in md.lower()
    assert "handläggaren" in md


def test_beslut_ar_tomt(tmp_path):
    md = render_markdown(_dossier(tmp_path))

    assert "avsiktligt tom" in md


def test_identiska_lagen_ger_inga_matbara_avvikelser(tmp_path):
    md = render_markdown(_dossier(tmp_path, verkligt=box(0, 0, 10, 8)))

    assert "Inga mätbara avvikelser" in md
    assert "avviker mätbart" not in md


def test_liten_areaavvikelse_ger_matosakerhetstext(tmp_path):
    # 80 m² godkänt, 81.5 m² verkligt -> +1.5 m² diff, inside the 2.0 m² band.
    md = render_markdown(_dossier(tmp_path, verkligt=box(0, 0, 10, 8.15)))

    assert "inom mätosäkerheten" in md


def test_byggnadsarea_saknas_renderas_utan_krasch(tmp_path):
    md = render_markdown(_dossier(tmp_path, lov_extra={"byggnadsarea_m2": None}))

    assert "ej angiven" in md


def test_villkor_redovisas_i_lovfaktan(tmp_path):
    md = render_markdown(
        _dossier(tmp_path, lov_extra={"villkor": ["Byggnaden ska målas i rött."]})
    )

    assert "Byggnaden ska målas i rött." in md

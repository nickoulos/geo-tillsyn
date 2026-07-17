"""Unit tests for the MCP-facing compact analysis + FastMCP tool registration.

Eneo's MCP client truncates text blocks at 8 kB (docs/spike-a-eneo-findings.md)
— tool output must be compact JSON with references, never geometry dumps.
Hermetic: fetchers injected.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

import asyncio
import json

from geo_tillsyn.runner import analysera_punkt

from tests.test_runner import _fejk_wfs

OWS = "http://example.test/ows"


def _resultat():
    return analysera_punkt(
        ows_url=OWS,
        punkt=(15.0, 15.0),
        radie_m=100.0,
        nu="2026-07-17T10:00:00Z",
        hamta_wfs=_fejk_wfs,
    )


def test_kompakt_resultat_har_traffar_med_juridik():
    resultat = _resultat()

    (traff,) = resultat["traffar"]
    assert traff["byggnad_id"] == "bal_byggnad_yta.10"
    assert traff["laege"] == "inom"
    assert traff["zon_referenser"] == ["2281K-ÖVR-241"]
    assert traff["byggnads_ar"] == 2014
    assert traff["gallde_vid_uppforande"] is True
    assert traff["dispens_kravs_idag"] is True
    assert traff["preskriberas"] is False


def test_kompakt_resultat_utan_geometri_och_under_8kb():
    resultat = _resultat()

    serialiserad = json.dumps(resultat, ensure_ascii=False)
    assert "coordinates" not in serialiserad
    assert len(serialiserad.encode()) < 8_000


def test_osakerheter_och_kallor_foljer_med():
    resultat = _resultat()

    assert any("UtvidgatStrandskydd_yta" in o for o in resultat["osakerheter"])
    assert any("GetFeature" in k["url"] for k in resultat["kallor"])
    assert resultat["antal_byggnader"] == 1
    assert resultat["antal_utanfor"] == 0


def test_stora_resultat_trunkeras_deklarerat():
    def manga_byggnader_wfs(wfs_url, type_name, bbox=None, max_features=100):
        fc = _fejk_wfs(wfs_url, type_name, bbox, max_features)
        if type_name.endswith("bal_byggnad_yta"):
            mall = fc["features"][0]
            return {
                "type": "FeatureCollection",
                "features": [
                    {**mall, "id": f"bal_byggnad_yta.{i}"} for i in range(120)
                ],
            }
        return fc

    resultat = analysera_punkt(
        ows_url=OWS,
        punkt=(15.0, 15.0),
        radie_m=100.0,
        nu="2026-07-17T10:00:00Z",
        hamta_wfs=manga_byggnader_wfs,
    )

    # No silent caps: the list is bounded but the truncation is declared.
    assert len(resultat["traffar"]) == 15
    assert resultat["traffar_trunkerade_till"] == 15
    assert resultat["antal_traffar"] == 120
    assert len(json.dumps(resultat, ensure_ascii=False).encode()) < 8_000


def test_mcp_servern_registrerar_verktygen():
    from geo_tillsyn.server import mcp

    verktyg = {t.name for t in asyncio.run(mcp.list_tools())}
    assert "analysera_strandskydd_vid_punkt" in verktyg
    assert "generera_dossier" in verktyg

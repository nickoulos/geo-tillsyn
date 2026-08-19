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


def test_lovavvikelse_verktyget_ar_registrerat():
    from geo_tillsyn.server import mcp

    verktyg = [t.name for t in asyncio.run(mcp.list_tools())]
    assert "analysera_lovavvikelse_vid_punkt" in verktyg


def test_snedbildsverktyget_ar_registrerat_och_svarar_arligt_utan_nyckel(monkeypatch, tmp_path):
    from geo_tillsyn import server

    verktyg = [t.name for t in asyncio.run(server.mcp.list_tools())]
    assert "hamta_snedbilder_vid_punkt" in verktyg
    monkeypatch.setattr(
        server.snedbild, "snedbilder_vid_punkt",
        lambda e, n, datum=None: {"tillganglig": False, "orsak": "ingen MAPSPACE_USERKEY"},
    )
    res = server.hamta_snedbilder_vid_punkt(1.0, 2.0, ut_katalog=str(tmp_path))
    assert res == {"tillganglig": False, "orsak": "ingen MAPSPACE_USERKEY"}


def test_bygglovsarenden_verktyget_ar_byggr_kompatibelt(monkeypatch, tmp_path):
    """Mock-ByggR via ArendeExportWS-formen: trakt + fBetNr in, Tekis-fält ut."""
    import json as _json
    from geo_tillsyn import server

    verktyg = [t.name for t in asyncio.run(server.mcp.list_tools())]
    assert "hamta_bygglovsarenden_for_fastighet" in verktyg

    (tmp_path / "x.json").write_text(_json.dumps({
        "syntetisk": True, "dnr": "SBN 2009-0412", "fastighet": "ALNÖ-USLAND 1:45",
        "beslutsdatum": "2009-06-19", "atgard": "Nybyggnad av enbostadshus",
        "godkant_lage": {"crs": "EPSG:3014", "koordinater": [[0, 0], [1, 0], [1, 1]]},
    }), encoding="utf-8")
    monkeypatch.setattr(server, "LOVARKIV_KATALOG", tmp_path)

    res = server.hamta_bygglovsarenden_for_fastighet("Alnö-Usland 1:45")

    assert res["trakt"] == "ALNÖ-USLAND" and res["fBetNr"] == "1:45"
    assert res["antal"] == 1
    assert res["arenden"][0]["dnr"] == "SBN 2009-0412"
    assert res["kalla"]["syntetisk"] is True
    assert "ArendeExportWS" in res["kalla"]["format"]
    assert len(json.dumps(res, ensure_ascii=False).encode()) < 8_000


def test_bygglovsarenden_verktyget_avvisar_ogiltig_beteckning():
    from geo_tillsyn import server

    res = server.hamta_bygglovsarenden_for_fastighet("ALNÖ-USLAND")
    assert res["antal"] == 0 and "fel" in res

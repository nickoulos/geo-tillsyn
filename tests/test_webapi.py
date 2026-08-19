"""Tests for the browser-callable REST seam (Origo-plugin) — CORS + JSON contracts.

The MCP tool contracts must stay unchanged (Eneo path); these tests exercise
only the parallel `/api/*` Starlette routes mounted via `mcp.custom_route`,
hermetically, with the underlying runner functions monkeypatched to canned
dicts (dependency injection isn't wired through the routes — the routes call
the module-level runner functions directly, so patching those is the seam).

SPDX-License-Identifier: AGPL-3.0-or-later
"""

import pytest
from starlette.testclient import TestClient

import geo_tillsyn.server as server_mod
from geo_tillsyn.meddelanden import Meddelande

# `mcp.streamable_http_app()` memoizes a StreamableHTTPSessionManager on the
# module-level `mcp` singleton whose lifespan `.run()` may only execute once
# per process — entering a fresh TestClient context per test re-triggers that
# lifespan and raises RuntimeError. Build the app once, share one TestClient
# (and its lifespan) across every test in this module.
_APP = server_mod.mcp.streamable_http_app()


@pytest.fixture(scope="module")
def client():
    with TestClient(_APP) as c:
        yield c


def test_health_returns_fem_verktyg(client):
    r = client.get("/api/health")

    assert r.status_code == 200
    assert r.json() == {"status": "ok", "tools": 5}
    assert r.headers["access-control-allow-origin"] == "*"


def test_lovavvikelse_returnerar_kompakt_dict(client, monkeypatch):
    canned = {"lov_hittat": True, "dnr": "SBN 2009-0412"}
    monkeypatch.setattr(server_mod, "analysera_fall3_punkt", lambda **kw: canned)

    r = client.get("/api/lovavvikelse", params={"easting": 105.0, "northing": 104.0})

    assert r.status_code == 200
    assert r.json() == canned
    assert r.headers["access-control-allow-origin"] == "*"


def test_strandskydd_anropar_analysera_punkt_med_defaultradie(client, monkeypatch):
    fanget = {}

    def fake(**kw):
        fanget.update(kw)
        return {"ok": True}

    monkeypatch.setattr(server_mod, "analysera_punkt", fake)

    r = client.get("/api/strandskydd", params={"easting": 1.0, "northing": 2.0})

    assert r.status_code == 200
    assert fanget["punkt"] == (1.0, 2.0)
    assert fanget["radie_m"] == 150.0


def test_olovligt_anropar_analysera_fall1_punkt_med_defaultradie(client, monkeypatch):
    fanget = {}

    def fake(**kw):
        fanget.update(kw)
        return {"ok": True}

    monkeypatch.setattr(server_mod, "analysera_fall1_punkt", fake)

    r = client.get("/api/olovligt", params={"easting": 1.0, "northing": 2.0})

    assert r.status_code == 200
    assert fanget["punkt"] == (1.0, 2.0)
    assert fanget["radie_m"] == 100.0


def test_saknad_easting_ger_400_med_cors(client):
    r = client.get("/api/lovavvikelse", params={"northing": 104.0})

    assert r.status_code == 400
    assert "fel" in r.json()
    assert r.headers["access-control-allow-origin"] == "*"


def test_ej_parsbar_easting_ger_400_med_cors(client):
    r = client.get("/api/lovavvikelse", params={"easting": "abc", "northing": 104.0})

    assert r.status_code == 400
    assert "fel" in r.json()
    assert r.headers["access-control-allow-origin"] == "*"


def test_valueerror_ger_404_med_cors(client, monkeypatch):
    def fake(**kw):
        raise ValueError("Ingen byggnad hittades inom 100 m från punkten.")

    monkeypatch.setattr(server_mod, "analysera_fall1_punkt", fake)

    r = client.get("/api/olovligt", params={"easting": 1.0, "northing": 2.0})

    assert r.status_code == 404
    assert "byggnad" in r.json()["fel"]
    assert r.headers["access-control-allow-origin"] == "*"


def test_ovrigt_fel_ger_500_med_cors(client, monkeypatch):
    def fake(**kw):
        raise RuntimeError("boom")

    monkeypatch.setattr(server_mod, "analysera_fall3_punkt", fake)

    r = client.get("/api/lovavvikelse", params={"easting": 1.0, "northing": 2.0})

    assert r.status_code == 500
    # Felet går som meddelandekod, inte färdig svenska — pluginet översätter.
    assert r.json() == {"fel": {"kod": "server.internt_fel", "params": {}}}
    assert r.headers["access-control-allow-origin"] == "*"


def test_valueerror_med_meddelande_ger_kod_och_params(client, monkeypatch):
    """Ett ValueError som bär ett Meddelande serialiseras som {kod, params}."""

    def fake(**kw):
        raise ValueError(
            Meddelande(
                "runner.ingen_byggnad_hittad", radie_m=100.0, easting=1.0, northing=2.0
            )
        )

    monkeypatch.setattr(server_mod, "analysera_fall1_punkt", fake)

    r = client.get("/api/olovligt", params={"easting": 1.0, "northing": 2.0})

    assert r.status_code == 404
    assert r.json()["fel"] == {
        "kod": "runner.ingen_byggnad_hittad",
        "params": {"radie_m": 100.0, "easting": 1.0, "northing": 2.0},
    }


def test_options_preflight_ger_204_med_cors_headers(client):
    r = client.options("/api/lovavvikelse")

    assert r.status_code == 204
    assert r.headers["access-control-allow-origin"] == "*"
    assert r.headers["access-control-allow-methods"] == "GET, OPTIONS"
    assert r.headers["access-control-allow-headers"] == "*"


def test_lovavvikelse_geometri_returnerar_geojson(client, monkeypatch):
    canned = {
        "lov_hittat": True,
        "dnr": "SBN 2009-0412",
        "godkant_lage": {
            "type": "Polygon",
            "coordinates": [[[100, 100], [110, 100], [110, 108], [100, 108], [100, 100]]],
        },
        "verkligt_lage": {
            "type": "Polygon",
            "coordinates": [[[100, 100], [112, 100], [112, 109], [100, 109], [100, 100]]],
        },
    }
    monkeypatch.setattr(server_mod, "fall3_geometri", lambda **kw: canned)

    r = client.get("/api/lovavvikelse/geometri", params={"easting": 105.0, "northing": 104.0})

    assert r.status_code == 200
    assert r.json() == canned
    assert r.headers["access-control-allow-origin"] == "*"


def test_snedbild_returnerar_oversikt_utan_position_eller_nyckel(client, monkeypatch):
    monkeypatch.setattr(
        server_mod.snedbild, "snedbilder_vid_punkt",
        lambda e, n, datum=None: {
            "tillganglig": True,
            "bilder": [{"riktning": "N", "id": "N+1_2_180727", "datum": "2018-07-27",
                        "copyright": "Blom", "position_x": 1.0, "position_y": 2.0,
                        "kolumner": 7700, "rader": 10300}],
            "ar": [2018], "viewer_url": "https://your.mapspace.com/?userkey=K", "kalla": "MapSpace",
        },
    )
    r = client.get("/api/snedbild?easting=158140&northing=6918389")
    assert r.status_code == 200
    data = r.json()
    assert data["bilder"] == [{"riktning": "N", "datum": "2018-07-27", "copyright": "Blom"}]
    assert data["ar"] == [2018]


def test_snedbild_bild_proxar_png_och_404_utan_tackning(client, monkeypatch):
    monkeypatch.setattr(
        server_mod.snedbild, "utsnitt_vid_punkt",
        lambda e, n, riktning, datum=None, zoom=None: b"\x89PNG fake" if riktning == "S" else None,
    )
    ok = client.get("/api/snedbild/bild?easting=1&northing=2&riktning=s")
    assert ok.status_code == 200 and ok.headers["content-type"] == "image/png"
    assert ok.content.startswith(b"\x89PNG")
    saknas = client.get("/api/snedbild/bild?easting=1&northing=2&riktning=W")
    assert saknas.status_code == 404
    assert saknas.json()["fel"]["kod"] == "runner.snedbilder_otillgangliga"

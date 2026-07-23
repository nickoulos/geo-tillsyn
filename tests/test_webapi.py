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


def test_health_returns_fyra_verktyg(client):
    r = client.get("/api/health")

    assert r.status_code == 200
    assert r.json() == {"status": "ok", "tools": 4}
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
    assert r.json() == {"fel": "internt fel"}
    assert r.headers["access-control-allow-origin"] == "*"


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

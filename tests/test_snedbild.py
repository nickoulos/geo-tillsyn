"""Tests for snedbild.py — MapSpace-klienten, hermetiskt (injicerad hämtare).

SPDX-License-Identifier: AGPL-3.0-or-later
"""

from __future__ import annotations

import io
import json

from PIL import Image

from geo_tillsyn import snedbild

META_N = {
    "positionX": 5368.5, "positionY": 4466.5, "idOblique": "N+017.404731_62.371189_180727",
    "imageCols": 7700, "imageRows": 10300, "copyright": "Blom",
}
META_S = {
    "positionX": 7470.5, "positionY": 6234.5, "idOblique": "S+017.407632_62.371078_220720",
    "imageCols": 14144, "imageRows": 10560, "copyright": "Blom",
}


def _tile_png() -> bytes:
    ut = io.BytesIO()
    Image.new("RGB", (256, 256), (90, 120, 60)).save(ut, format="JPEG")
    return ut.getvalue()


def test_datum_ur_id():
    assert snedbild._datum_ur_id("N+017.404731_62.371189_180727") == "2018-07-27"
    assert snedbild._datum_ur_id("konstigt") == ""


def test_tolka_seoblique_tal_serverbuggen_utan_avslutande_hakparentes():
    """Live 2026-08-19: view=* svarar med en lista som saknar `]` (Content-Length klipper)."""
    trasig = json.dumps([{"metadata": META_N}, {"metadata": META_S}])[:-1].encode()
    ids = [m["idOblique"] for m in snedbild._tolka_seoblique(trasig)]
    assert ids == [META_N["idOblique"], META_S["idOblique"]]


def test_tolka_seoblique_enstaka_objekt_och_felsvar():
    assert snedbild._tolka_seoblique(json.dumps(META_N).encode())[0]["idOblique"] == META_N["idOblique"]
    assert snedbild._tolka_seoblique(b'{ "success" : false, "data" : "ERROR 19"}') == []
    assert snedbild._tolka_seoblique(b"<html>nope</html>") == []


def test_hitta_snedbilder_sorterar_n_e_s_w_och_faller_tillbaka_per_riktning():
    anrop = []

    def hamta(url):
        anrop.append(url)
        if "view=%2A" in url:
            return b"garbage"  # tvinga fallback per riktning
        if "view=N" in url:
            return json.dumps(META_N).encode()
        if "view=S" in url:
            return json.dumps(META_S).encode()
        return b'{ "success" : false, "data" : "ERROR 1, no image"}'

    bilder = snedbild.hitta_snedbilder(158140.4, 6918389.3, "KEY", hamta=hamta)
    assert [b.riktning for b in bilder] == ["N", "S"]
    assert bilder[0].datum == "2018-07-27" and bilder[1].ar == 2022
    assert len(anrop) == 5  # 1 (view=*) + 4 riktningar
    assert all("userkey=KEY" in u and "crs=EPSG%3A3014" in u for u in anrop)


def test_hamta_utsnitt_syr_ihop_rutor_runt_punkten_och_markerar():
    begarda = []

    def hamta(url):
        begarda.append(url)
        return _tile_png()

    bild = snedbild.hitta_snedbilder(0, 0, "KEY", hamta=lambda u: json.dumps(META_N).encode())[0]
    png = snedbild.hamta_utsnitt(bild, "KEY", zoom=3, tiles=3, hamta=hamta)
    im = Image.open(io.BytesIO(png))
    assert im.size == (768, 768)
    # positionX 5368.5 / 1024 = kol 5, positionY 4466.5 / 1024 = rad 4 → 3×3 runt (4,5)
    meshids = sorted(u.split("meshid=")[1] for u in begarda)
    assert meshids == sorted(f"3_{r}_{c}" for r in (3, 4, 5) for c in (4, 5, 6))
    # Markeringen (röd ring) finns nära punktens pixel i utsnittet.
    px = (5368.5 - 4 * 1024) / 1024 * 256
    py = (4466.5 - 3 * 1024) / 1024 * 256
    r, g, b = im.getpixel((int(px) + 14, int(py)))
    assert r > 200 and g < 80 and b < 80


def test_hamta_utsnitt_anpassar_zoom_efter_bildbredd():
    meshids = []

    def hamta(url):
        meshids.append(url.split("meshid=")[1][0])
        return _tile_png()

    stor = snedbild.hitta_snedbilder(0, 0, "KEY", hamta=lambda u: json.dumps(META_S).encode())[0]
    snedbild.hamta_utsnitt(stor, "KEY", hamta=hamta)
    assert set(meshids) == {"2"}


def test_snedbilder_vid_punkt_utan_nyckel_ar_inte_ett_undantag(monkeypatch):
    monkeypatch.setenv("MAPSPACE_USERKEY", "")
    monkeypatch.setattr(snedbild, "_ROT", snedbild._ROT / "finns-inte")
    res = snedbild.snedbilder_vid_punkt(1, 2)
    assert res == {"tillganglig": False, "orsak": "ingen MAPSPACE_USERKEY"}


def test_snedbilder_vid_punkt_kompakt_svar_utan_nyckel_i_bilddata():
    res = snedbild.snedbilder_vid_punkt(
        158140.4, 6918389.3, nyckel="HEMLIG",
        hamta=lambda u: json.dumps([{"metadata": META_N}, {"metadata": META_S}]).encode(),
    )
    assert res["tillganglig"] is True
    assert [b["riktning"] for b in res["bilder"]] == ["N", "S"]
    assert res["ar"] == [2018, 2022]
    assert "HEMLIG" in res["viewer_url"]  # visarlänken bär nyckeln (avsedd användning)
    assert all("HEMLIG" not in json.dumps(b) for b in res["bilder"])


def test_viewer_url_foljer_mapspace_url_access():
    url = snedbild.viewer_url(158140.4, 6918389.3, "K", riktning="E")
    assert url.startswith("https://your.mapspace.com/?workspace=Default")
    assert "srs=EPSG%3A3014" in url and "viewmode=oblique" in url and "orientation=E" in url

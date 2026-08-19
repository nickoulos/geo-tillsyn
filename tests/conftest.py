"""Gemensamma fixturer: sviten är hermetisk — inga nätverksanrop, aldrig.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _inga_snedbilder_fran_natet(monkeypatch):
    """MapSpace-seamen i runner.py byts mot en stubb som svarar 'ingen nyckel'.

    Utan detta skulle Fall 3-testerna gå mot your.mapspace.com på en maskin
    som har MAPSPACE_USERKEY i .env. Tester som vill ha snedbilder injicerar
    sin egen `hamta_snedbilder`.
    """
    from geo_tillsyn import runner

    monkeypatch.setattr(
        runner, "SNEDBILDER_VID_PUNKT",
        lambda e, n: {"tillganglig": False, "orsak": "ingen MAPSPACE_USERKEY"},
    )
    monkeypatch.setattr(runner, "SNEDBILD_UTSNITT", lambda e, n, r, **kw: None)

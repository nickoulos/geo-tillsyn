"""regelverk_vid — time-aware legal context for a point and a date.

Pure core: spatial facts (is the point inside a strandskydd zone, a
detaljplan, ...) are injected via `Kontext` by the caller — in production the
MCP server resolves them via WMS GetFeatureInfo (see docs/data-findings.md §1).
The rule model lives in regler.json (versioned, data-driven); this module only
evaluates validity windows and regime interplay.

Prototype simplification — the dataset must pass legal review (Sprint 3).
"""

import json
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

_REGLER = json.loads(
    (Path(__file__).parent / "regler.json").read_text(encoding="utf-8")
)


@dataclass
class Kontext:
    """Spatial facts about the point, resolved by the caller."""
    inom_detaljplan: bool = False
    inom_strandskydd: bool = False
    inom_utvidgat_strandskydd: bool = False
    strandskydd_upphavt: bool = False


def _d(value):
    return date.fromisoformat(value) if isinstance(value, str) else value


def _within(rule, datum):
    fran = _d(rule["fran"])
    till = _d(rule["till"]) if rule.get("till") else None
    return fran <= datum and (till is None or datum <= till)


def _pbl_version(datum):
    for version in _REGLER["pbl_versioner"]:
        if _within(version, datum):
            return version
    return None


def _lovbefrielser(datum):
    return [r for r in _REGLER["lovbefrielser"] if _within(r, datum)]


def _strandskydd(datum, kontext):
    ss = _REGLER["strandskydd"]
    inom_zon = kontext.inom_strandskydd or kontext.inom_utvidgat_strandskydd
    gallde = inom_zon and datum >= _d(ss["generellt_fran"])
    dispens_kravs = gallde and not kontext.strandskydd_upphavt
    return {
        "inom_zon_idag": inom_zon,
        "gallde_vid_datum": gallde,
        "dispens_kravs": dispens_kravs,
        "bygglovsbefrielse_ger_inte_dispens": True,
        "lagrum": ss["lagrum"],
        "dispens_lagrum": ss["dispens_lagrum"],
        "generellt_fran": ss["generellt_fran"],
    }


def _preskription(datum, bedomningsdatum):
    p = _REGLER["preskription"]
    tioar = p["pbl_tioarsregel"]
    gransdatum = date(datum.year + tioar["ar"], datum.month, datum.day) \
        if not (datum.month == 2 and datum.day == 29) \
        else _d(f"{datum.year + tioar['ar']}-03-01")
    return {
        "pbl_tioarsregeln_lopt_ut": bedomningsdatum > gransdatum,
        "pbl_gransdatum": gransdatum.isoformat(),
        "pbl_lagrum": tioar["lagrum"],
        "byggsanktionsavgift_ar": p["byggsanktionsavgift"]["ar"],
        "strandskydd_preskriberas": p["strandskydd"]["preskriberas"],
    }


def regelverk_vid(datum, kontext=None, bedomningsdatum=None):
    """Return the legal regime in force at `datum` for a point with `kontext`.

    `bedomningsdatum` (default: today) drives the preskription assessment.
    """
    datum = _d(datum)
    kontext = kontext or Kontext()
    bedomningsdatum = _d(bedomningsdatum) if bedomningsdatum else date.today()
    return {
        "datum": datum.isoformat(),
        "pbl_version": _pbl_version(datum),
        "lovbefrielser": _lovbefrielser(datum),
        "strandskydd": _strandskydd(datum, kontext),
        "preskription": _preskription(datum, bedomningsdatum),
    }

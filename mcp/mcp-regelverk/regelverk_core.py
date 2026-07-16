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


def _samlad_area_pott(datum, kontext):
    """Post-2025-12-01 the exemption is a combined area pot per fastighet.

    Returns None before the reform, where exemptions were per building type.
    """
    pott = _REGLER["samlad_area_pott"]
    if datum < _d(pott["fran"]):
        return None
    zon = "inom_detaljplan" if kontext.inom_detaljplan else "utom_detaljplan"
    return {
        **pott[zon],
        "zon": zon,
        "sfs": pott["sfs"],
        "forarbeten": pott["forarbeten"],
        "kalla": pott["kalla"],
    }


def _overgangsbestammelser(datum, arende_startdatum):
    """Which law applies is driven by when the ärende began, not by `datum`.

    PBL 2010:900 p. 2 keeps the repealed ÄPBL alive for ärenden started before
    2011-05-02 until finally decided — see docs/legal-findings.md §4.1. When the
    caller supplies `arende_startdatum` we route on it; otherwise we warn if
    `datum` falls close enough to a transition for this to matter.
    """
    for ob in _REGLER["overgangsbestammelser"]:
        ikraft = _d(ob["ikrafttradande"])
        if arende_startdatum and arende_startdatum < ikraft <= datum:
            return {
                "gäller": True,
                "tillampad_pga_arendestart": True,
                "aldre_sfs": ob["aldre_sfs"],
                "ikrafttradande": ob["ikrafttradande"],
                "kommentar": ob["kommentar"],
            }
        fonster = timedelta(days=365 * ob["varningsfonster_ar"])
        if ikraft <= datum < ikraft + fonster and not arende_startdatum:
            return {
                "gäller": True,
                "tillampad_pga_arendestart": False,
                "aldre_sfs": ob["aldre_sfs"],
                "ikrafttradande": ob["ikrafttradande"],
                "kommentar": ob["kommentar"],
                "atgard": "Ange ärendets startdatum — datum ensamt avgör inte vilken lag som gäller.",
            }
    return {"gäller": False, "tillampad_pga_arendestart": False}


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


def regelverk_vid(datum, kontext=None, bedomningsdatum=None, arende_startdatum=None):
    """Return the legal regime in force at `datum` for a point with `kontext`.

    `bedomningsdatum` (default: today) drives the preskription assessment.
    `arende_startdatum` — when the ärende began. If it predates a transition,
    the older law governs (PBL 2010:900 p. 2); pass it whenever it is known.
    """
    datum = _d(datum)
    kontext = kontext or Kontext()
    bedomningsdatum = _d(bedomningsdatum) if bedomningsdatum else date.today()
    arende_startdatum = _d(arende_startdatum) if arende_startdatum else None

    overgang = _overgangsbestammelser(datum, arende_startdatum)
    # An ärende started before a transition is judged by the law in force then.
    rattsdatum = arende_startdatum if overgang["tillampad_pga_arendestart"] else datum

    return {
        "datum": datum.isoformat(),
        "pbl_version": _pbl_version(rattsdatum),
        "lovbefrielser": _lovbefrielser(rattsdatum),
        "samlad_area_pott": _samlad_area_pott(rattsdatum, kontext),
        "strandskydd": _strandskydd(datum, kontext),
        "preskription": _preskription(datum, bedomningsdatum),
        "overgangsbestammelser": overgang,
    }

"""Resonemang: den juridiska kedjan som explicit, granskningsbar nodlista.

Regelgraf-tanken (regelgraf/README, "ingen svart låda") i tunn form: varje
fall exponerar de steg motorn faktiskt gått igenom — fråga, lagrum, svar —
härledda ur redan beräknade fält. Ingen nod räknar något nytt: kedjan är en
läsbar projektion av analysens resultat, och den slutar alltid i samma nod —
beslutet, vars svar är None eftersom det är handläggarens.

Svaren är rådata (bool/str/None), aldrig formuleringar: None betyder »Ej
fastställt«, och klienten renderar på valfritt språk via meddelandekoderna.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

from __future__ import annotations

from typing import Any

from geo_tillsyn.meddelanden import Meddelande as M

_BESLUT_LAGRUM = "PBL 11 kap. / MB 26 kap. — tillsynsmyndighetens prövning"


def _nod(kod: str, lagrum: str, svar: Any, **params: Any) -> dict[str, Any]:
    return {"fraga": M(kod, **params), "lagrum": lagrum, "svar": svar}


def _beslut() -> dict[str, Any]:
    return _nod("resonemang.beslut", _BESLUT_LAGRUM, None)


def resonemang_fall7(traff: dict[str, Any]) -> list[dict[str, Any]]:
    """Kedjan för en strandskydds-träff (Fall 7), ur analysera_punkt-fälten."""
    return [
        _nod("resonemang.f7_inom_zon", "MB 7 kap. 13–14 §§", traff.get("laege")),
        _nod(
            "resonemang.f7_gallde_vid_uppforande",
            "MB 7 kap.; generellt strandskydd 1975-07-01",
            traff.get("gallde_vid_uppforande"),
        ),
        _nod("resonemang.f7_dispens_idag", "MB 7 kap. 15 och 18b §§", traff.get("dispens_kravs_idag")),
        _nod("resonemang.f7_preskription", "MÖD 2021:6 — ingen preskriptionsregel", traff.get("preskriberas")),
        _beslut(),
    ]


def resonemang_fall1(resultat: dict[str, Any]) -> list[dict[str, Any]]:
    """Kedjan för olovligt byggande (Fall 1), ur analysera_fall1_punkt-fälten."""
    sista = resultat.get("sista_ar_utan")
    forsta = resultat.get("forsta_ar_med")
    intervall = f"{sista}–{forsta}" if sista is not None and forsta is not None else None
    return [
        _nod("resonemang.f1_nar_uppford", "Ortofoto-tidslinje (deterministisk datering)", intervall),
        _nod("resonemang.f1_forenligt_register", "BAL (byggnadsregistret)", resultat.get("bal_forenligt")),
        _nod("resonemang.f1_bygglov_kravdes", "PBL 9 kap. 2 § (resp. ÄPBL)", resultat.get("bygglov_kravdes")),
        _nod("resonemang.f1_lovbefrielse", "PBL 9 kap. 4–4d §§ (friggebod/attefall)", resultat.get("lovbefrielse")),
        _nod("resonemang.f1_klocka_rattelse", "PBL 11 kap. 20 § (10 år)", resultat.get("rattelse_preskriberad")),
        _nod("resonemang.f1_klocka_sanktion", "PBL 11 kap. 58 § (5 år)", resultat.get("sanktionsavgift_mojlig")),
        _beslut(),
    ]


def resonemang_fall3(resultat: dict[str, Any]) -> list[dict[str, Any]]:
    """Kedjan för lovavvikelse (Fall 3), ur analysera_fall3_punkt-fälten."""
    if not resultat.get("lov_hittat"):
        return [
            _nod("resonemang.f3_lov_finns", "Lovarkiv (syntetiskt i prototypfasen)", False),
            _beslut(),
        ]

    kors = resultat.get("korsjamforelse") or {}
    korssvar = None
    if kors:
        korssvar = "overens" if all(v == "overens" for v in kors.values()) else "avviker"

    diff_m2 = resultat.get("area_diff_m2")
    diff_pct = resultat.get("area_diff_procent")
    avvikelse = None
    if diff_m2 is not None:
        tecken = "+" if diff_m2 > 0 else ""
        m2 = f"{tecken}{diff_m2:.1f}".replace(".", ",")
        avvikelse = f"{m2} m²"
        if diff_pct is not None:
            pct = f"{'+' if diff_pct > 0 else ''}{diff_pct:.1f}".replace(".", ",")
            avvikelse += f" ({pct} %)"

    return [
        _nod("resonemang.f3_lov_finns", "Lovarkiv (syntetiskt i prototypfasen)", True),
        _nod(
            "resonemang.f3_vilken_lag",
            "SFS 2010:900 övergångsbestämmelser p. 2",
            resultat.get("pbl_vid_beslut"),
        ),
        _nod("resonemang.f3_korskontroll", "Skannad handling (OCR) mot registerpost", korssvar),
        _nod("resonemang.f3_avvikelse", "Geometrisk jämförelse godkänt/verkligt läge", avvikelse),
        # Väsentlig eller ringa är alltid handläggarens fråga — aldrig motorns.
        _nod("resonemang.f3_vasentlighet", "PBL 9 kap. 31b–31c §§ (praxis)", None),
        _nod(
            "resonemang.f3_klockor",
            "PBL 11 kap. 20 och 58 §§",
            resultat.get("rattelse_preskriberad"),
        ),
        _beslut(),
    ]

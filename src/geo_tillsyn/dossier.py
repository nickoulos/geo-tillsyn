"""Dossier: tre nivåer — Fakta, Bedömning, Beslut.

Fakta bär alltid en klickbar källa. Bedömning redovisar sin grund och sina
osäkerheter. Beslut är alltid tomt: modellen kan inte ens bära ett beslut,
eftersom beslutet är handläggarens (jfr Konceptbeskrivning §3.4, §7).

SPDX-License-Identifier: AGPL-3.0-or-later
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Kalla:
    """A verifiable source: what was fetched, from where, when."""

    beskrivning: str
    url: str
    hamtad: str
    referens: str | None = None


@dataclass(frozen=True)
class Fakta:
    pastaende: str
    kalla: Kalla


@dataclass(frozen=True)
class Bedomning:
    pastaende: str
    grund: list[int] = field(default_factory=list)  # indices into Dossier.fakta
    osakerheter: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Dossier:
    # Deliberately no `beslut` field: the decision level exists only in the
    # rendered output, as an empty section addressed to the handläggare.
    rubrik: str
    fakta: list[Fakta] = field(default_factory=list)
    bedomningar: list[Bedomning] = field(default_factory=list)


_BESLUT_TEXT = (
    "*Denna del är avsiktligt tom. Beslutet fattas av handläggaren; "
    "underlaget ovan kan granskas källa för källa och avvisas.*"
)


def render_markdown(dossier: Dossier) -> str:
    """Render the dossier as markdown with the three levels in fixed order."""
    lines: list[str] = [f"# {dossier.rubrik}", ""]

    lines += ["## 1. Fakta", ""]
    for i, fakta in enumerate(dossier.fakta, start=1):
        kalla = fakta.kalla
        referens = f" — {kalla.referens}" if kalla.referens else ""
        lines.append(
            f"- **F{i}** {fakta.pastaende}  \n"
            f"  Källa: [{kalla.beskrivning}]({kalla.url}){referens}, "
            f"hämtad {kalla.hamtad}"
        )
    lines.append("")

    lines += ["## 2. Bedömning", ""]
    for bedomning in dossier.bedomningar:
        grund = ", ".join(f"F{i + 1}" for i in bedomning.grund)
        grund_del = f" (grund: {grund})" if grund else ""
        lines.append(f"- {bedomning.pastaende}{grund_del}")
        for osakerhet in bedomning.osakerheter:
            lines.append(f"  - **Ej fastställt:** {osakerhet}")
    lines.append("")

    lines += ["## 3. Beslut", "", _BESLUT_TEXT, ""]

    return "\n".join(lines)

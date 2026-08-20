"""Dossier: tre nivåer — Fakta, Bedömning, Beslut — i två vyer.

Fakta bär alltid en klickbar källa. Bedömning redovisar sin grund och sina
osäkerheter. Beslut är alltid tomt: modellen kan inte ens bära ett beslut,
eftersom beslutet är handläggarens (jfr Konceptbeskrivning §3.4, §7).

Två vyer ur samma data (dossier/README, effektmålet "pedagogiskt
beslutsunderlag"): `render_markdown` — juridiskt precis för diariet, och
`render_klarsprak` — klarspråk för berörd part. Klarspråksvyn är en ren
omrendering: den lägger aldrig till påståenden, tar aldrig bort källor och
fäller aldrig ett omdöme; ordlistan förklarar bara termer som förekommer.

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


# --- klarspråksvyn -------------------------------------------------------------

# Ordlistan är medvetet liten och ordagrann: (nyckel att söka på, gemener) ->
# (uppslagsord, förklaring enligt klarspråksprincipen "förklara facktermer").
# Bara termer som faktiskt förekommer i dossiern tas med.
_ORDLISTA: tuple[tuple[str, str, str], ...] = (
    ("strandskydd", "strandskydd", "en skyddszon vid hav, sjöar och vattendrag "
     "(normalt 100 meter från strandlinjen) där det är förbjudet att bygga utan "
     "ett särskilt tillstånd som kallas dispens."),
    ("dispens", "dispens", "ett undantag från ett förbud. Strandskyddsdispens är "
     "kommunens eller länsstyrelsens tillstånd att ändå bygga inom strandskyddszonen."),
    ("preskri", "preskription", "att en tidsfrist har löpt ut. När en åtgärd är "
     "preskriberad får kommunen inte längre kräva rättelse. För strandskydd finns "
     "ingen sådan tidsfrist."),
    ("bygglov", "bygglov", "kommunens tillstånd att bygga, riva eller ändra en "
     "byggnad. Krävs för de flesta byggnader, med vissa undantag."),
    ("lovavvikelse", "lovavvikelse", "en skillnad mellan det som faktiskt byggdes "
     "och det som bygglovet tillät — till exempel större yta eller annat läge."),
    ("sanktionsavgift", "sanktionsavgift", "en avgift som kommunen kan ta ut av "
     "den som byggt utan lov eller i strid med lovet, inom en viss tid."),
    ("ortofoto", "ortofoto", "ett flygfoto som räknats om så att det stämmer med "
     "kartan och går att mäta i."),
    ("byggnadsregist", "byggnadsregistret", "kommunens och Lantmäteriets register "
     "över byggnader (BAL), med bland annat uppgivet nybyggnadsår."),
    ("situationsplan", "situationsplan", "en ritning som visar var på tomten en "
     "byggnad ligger eller ska ligga."),
    ("detaljplan", "detaljplan", "kommunens plan som bestämmer vad marken i ett "
     "område får användas till och vad som får byggas där."),
    ("fastighetsgräns", "fastighetsgräns", "gränsen för en fastighet (tomt) så "
     "som den är registrerad hos Lantmäteriet."),
    ("snedbild", "snedbild", "ett flygfoto taget snett från sidan, så att "
     "byggnaders fasader syns."),
)

_KLARSPRAK_INGRESS = (
    "*Det här är samma underlag som det formella dokumentet, skrivet för att "
    "vara lätt att läsa. Uppgifterna och källorna är exakt desamma. "
    "Ingenting i det här dokumentet är ett beslut.*"
)

_VAD_HANDER_NU = (
    "Det här underlaget är framtaget av ett IT-stöd som sammanställer kartor, "
    "register och regler. Det är inte ett beslut, och inget beslut fattas av "
    "datorn. En handläggare på kommunen granskar underlaget, väger in sådant "
    "som systemet inte ser och tar ställning. Varje uppgift ovan har en källa, "
    "så att den kan kontrolleras — och ifrågasättas."
)


def render_klarsprak(dossier: Dossier) -> str:
    """Render the dossier in plain language for the berörd part.

    Same fakta, same sources, same declared uncertainties as render_markdown —
    only the structure and framing change. Never adds a claim, never drops a
    source, never passes judgement.
    """
    lines: list[str] = [f"# {dossier.rubrik} — i klarspråk", "", _KLARSPRAK_INGRESS, ""]

    lines += ["## Vad handlar det här om?", ""]
    lines.append(
        "Kommunen har tagit fram ett underlag utifrån kartor, flygfoton och "
        "register. Nedan ser du vad som har hittats, hur det kan tolkas, och "
        "vad som händer härnäst."
    )
    lines.append("")

    lines += ["## Det här har vi sett", ""]
    for fakta in dossier.fakta:
        kalla = fakta.kalla
        referens = f" ({kalla.referens})" if kalla.referens else ""
        lines.append(f"- {fakta.pastaende}")
        lines.append(
            f"  Uppgiften kommer från: [{kalla.beskrivning}]({kalla.url}){referens}, "
            f"hämtad {kalla.hamtad}."
        )
    lines.append("")

    lines += ["## Så här kan det tolkas", ""]
    for bedomning in dossier.bedomningar:
        lines.append(f"- {bedomning.pastaende}")
        for osakerhet in bedomning.osakerheter:
            lines.append(f"  - Det här vet vi inte säkert: {osakerhet}")
    lines.append("")

    lines += ["## Vad händer nu?", "", _VAD_HANDER_NU, ""]

    # Ordlista: bara termer som faktiskt förekommer någonstans i dossiern.
    hela_texten = "\n".join(lines).lower()
    uppslag = [
        (ord_, forklaring)
        for nyckel, ord_, forklaring in _ORDLISTA
        if nyckel in hela_texten
    ]
    lines += ["## Ordlista", ""]
    if uppslag:
        for ord_, forklaring in uppslag:
            lines.append(f"- **{ord_}** — {forklaring}")
    else:
        lines.append("*Inga facktermer att förklara i det här underlaget.*")
    lines.append("")

    return "\n".join(lines)

# Geo-Tillsyn

Prototyp för Govtech4all Pilot 3 — AI och geodata (Sundsvalls kommun, UH-2026-159).

Geo-Tillsyn är en handläggar-copilot för tillsynsärenden enligt PBL. Lösningen sammanställer geodata, bygglovshistorik och tillämplig lagstiftning för ett valt objekt och producerar ett transparent, citerbart beslutsunderlag — för handläggaren och för berörd part.

Kärnidén: alla tillsynsärenden är samma fråga — **Verklighet vs. Rättighet, över Tid** — vad finns, vad får finnas, och när uppstod avvikelsen. En motor, konfigurerbar per ärendeslag.

## Arkitektur

```text
Origo-plugin (karta + tidslinje + dossier)
        │
Eneo-assistent "Geo-Tillsyn"  (resonemang via regelgraf)
        │  MCP
┌───────┴────────────────────────────────────────┐
│ mcp-geodata   — WFS/WMS-fasad (via mcp-ogc)    │
│ mcp-ortofoto  — ortofoto-tidsserier            │
│ mcp-bygglov   — syntetiska bygglov (prototyp)  │
│ mcp-regelverk — regelverk_vid(punkt, datum)    │
│ mcp-delta     — förändringsanalys + segmentering│
└────────────────────────────────────────────────┘
        │  OGC WMS/WFS, STAC
GeoServer (karta.sundsvall.se), Lantmäteriet, Länsstyrelsen
```

## Struktur

| Katalog | Innehåll |
| --- | --- |
| `mcp/` | MCP-servrar, en per datakälla |
| `regelgraf/` | Juridiska beslutsträd per ärendeslag (YAML) + motor |
| `origo-plugin/` | Handläggargränssnitt (tidslinje, dossier, regelgraf-vy) |
| `dossier/` | Mallar: juridisk + klarspråksversion |
| `data/synthetic/` | Syntetiska testdata (inga verkliga personuppgifter) |
| `docs/adr/` | Arkitekturbeslut |
| `src/geo_tillsyn/` | Körbar Fall 7-skiva: analys, dossier, tidslinje (se nedan) |
| `tests/` | Hermetisk testsvit för skivan (pytest, inga nätverksanrop) |

## Körbar skiva — Fall 7 strandskydd

```sh
.venv/Scripts/pip install -e .[dev] -e ../mcp-ogc
.venv/Scripts/geo-tillsyn 158140.4 6918389.3 --radie 120 --ut demo_ut/alno-usland-1-45
```

Punkt (EPSG:3014, kommunlagrens native CRS) → byggnader (`bal_byggnad_yta`) korsas med
strandskyddszoner (`lm_strandskydd_y`, med lm_aktbeteckning som källreferens) → `dossier.md`
i tre nivåer — **Fakta** (klickbar källa per påstående), **Bedömning** (grund + »Ej fastställt«),
**Beslut** (alltid tomt; handläggarens) — plus ortofoto-tidslinje 1960–2023 som PNG.

Otillgängliga regelkällor (t.ex. `Lansstyrelsen:UtvidgatStrandskydd_yta`, trasig server-side
2026-07-17) prövas varje körning och redovisas som osäkerhet — aldrig tyst. Tomma
WMS-svar (täckningsglapp per årgång) flaggas »misstänkt tom bild«.

## Status

Prototypfas (Steg 2), under aktiv utveckling. Prototypen arbetar uteslutande mot syntetiska eller öppna data — inga verkliga byggärenden och inga personuppgifter.

## Licens

AGPL-3.0-or-later — se [LICENSE](LICENSE). All kod utvecklad inom uppdraget publiceras öppet från första commit.

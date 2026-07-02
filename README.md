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

## Status

Prototypfas (Steg 2), under aktiv utveckling. Prototypen arbetar uteslutande mot syntetiska eller öppna data — inga verkliga byggärenden och inga personuppgifter.

## Licens

AGPL-3.0-or-later — se [LICENSE](LICENSE). All kod utvecklad inom uppdraget publiceras öppet från första commit.

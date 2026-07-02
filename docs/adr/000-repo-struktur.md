# ADR-000: Repo-struktur, licens och arbetsspråk

**Datum:** 2026-07-02 · **Status:** Accepterad

## Beslut

1. **Monorepo** med en katalog per komponent: `mcp/*` (en MCP-server per datakälla), `regelgraf/`, `origo-plugin/`, `dossier/`, `data/synthetic/`, `docs/`. Motiv: prototypfas med 4 utvecklare, gemensam CI, atomiska ändringar över komponentgränser. Kan splittras senare (rule of three).
2. **AGPL-3.0-or-later** för all kod, från första commit — bindande krav i upphandlingen.
3. **Arbetsspråk:** README och leveransdokument på svenska; interna arbetsdokument och kodkommentarer på engelska under utvecklingen. Slutleverans: fullständig svensk dokumentation (åtagande i anbudet).
4. **Inga verkliga personuppgifter eller byggärenden i repot** — endast syntetiska dataset (`data/synthetic/`) och öppna geodata.
5. MCP-servrar i Python/FastMCP (återanvänder mönster från `mcp-ogc`); Origo-plugin i TypeScript; regelgraf-definitioner i YAML.

## Konsekvenser

- CI kör per komponent-katalog (paths-filter) när kod tillkommer (Sprint 1+).
- Generalisering/abstraktion skjuts upp tills samma mönster setts tre gånger (Prototypmetodik §6).

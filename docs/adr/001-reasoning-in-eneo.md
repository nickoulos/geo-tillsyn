# ADR-001: Resonemanget bor i Eneo-assistenten; regelgrafen exponeras som MCP-verktyg

**Datum:** 2026-07-02 · **Status:** Accepterad (bekräftas med körtest, Sprint 1)

## Kontext

Spike A granskade Eneos källkod (eneo-ai/eneo, klonad 2026-07-02) för att avgöra
var Geo-Tillsyns resonemang ska bo: i en Eneo-assistent eller i en egen
orkestrator. Fynd:

- **MCP är förstaklass i Eneo**: egen domänmodul (`backend/src/eneo/mcp_servers/`),
  databasschema + migrationer, admin-UI för serverregistrering, val av
  MCP-servrar per space, governance-policyer, säkerhetsklassning per server,
  chat-session-MCP-state samt **verktygsreferenser** (`mcp_tool_references`)
  som knyter verktygsanrop till svar — dvs. citerbarhet är inbyggd.
- **Transport: enbart Streamable HTTP** (`mcp.client.streamable_http`).
  Servrar registreras med `http_url` + `http_auth_type` (default "none").
  Stdio stöds inte.
- **Defensiva tak**: resursblock kapas (text 8 kB, meta 16 kB). Verktyg ska
  returnera kompakta svar och referenser (URL:er, id:n) — inte stora blobbar.

## Beslut

1. **Ingen parallell orkestrator.** Eneo-assistenten "Geo-Tillsyn" är värd för
   resonemanget (systemprompt + MCP-verktyg), i linje med skakravet.
2. **Regelgrafen är vår kod, exponerad som MCP-verktyg.** Grafmotorn kör
   deterministiskt på serversidan (t.ex. `starta_arende`, `nasta_steg`,
   `hamta_graf_status` i mcp-regelverk); assistenten anropar den och
   presenterar stegen. LLM:en improviserar inte juridiken — den fyller noder.
3. **Alla våra MCP-servrar körs som HTTP-tjänster** (streamable HTTP) i samma
   Docker Compose-nät som Eneo; auth "none" i prototyp, schema-driven auth i
   genomförandefas.
4. **Verktygssvar är kompakta och referensbaserade** (geometri-id:n, WMS-URL:er,
   nyckeltal) — aldrig råbilder eller stora GeoJSON-blobbar, pga Eneos tak.

## Konsekvenser

- `mcp-ogc` (grunden för mcp-geodata) kör idag enbart stdio → arbetspunkt:
  lägg till streamable HTTP-läge + container (bra kandidat för mcp-ogc v0.2.0,
  publikt).
- Live-verifiering återstår (Sprint 1): registrera en server i admin-UI,
  koppla till space/assistent, se verktygsanrop + citat i chatten. Eneos
  e2e-uppsättning (`docker-compose.e2e.yml`) innehåller en **mock-modellserver**
  — hela kedjan kan testas utan LLM-nycklar.
- Fallback om körtestet motsäger fynden: egen tunn orkestrator bakom ett enda
  MCP-verktyg, dokumenterad som ADR + upstream-issue till eneo-ai/eneo.

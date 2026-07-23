# ADR-003: En MCP-server med fyra verktyg (i stället för sex separata)

**Datum:** 2026-07-23 · **Status:** Accepterad

## Kontext

Steg 1-konceptet (`Konceptbeskrivning_Foursight_Lab.md` §3.3) skisserade sex
fristående MCP-servrar — `mcp-bygglov`, `mcp-ortofoto`, `mcp-detaljplan`,
`mcp-pbl`, `mcp-ngp`, `mcp-lokala-foreskrifter` — en per datakälla. Det var en
arkitektonisk ambition, formulerad innan prototypkoden fanns.

Under Steg 2 visade sig de tre byggda fallen (1, 3, 7) dela samma
hämtnings- och sammanställningsprimitiver: ortofoto-tidslinje, WFS-hämtning,
klientsidig shapely-geometri, tidsmedveten regeltolkning, dossier-rendering.
Sex separata serverprocesser hade inneburit sex driftsenheter, sex
transport-uppsättningar och sex testsviter kring i praktiken delad logik.

## Beslut

Bygg **en** MCP-server, `geo-tillsyn` (FastMCP, streamable HTTP), som exponerar
**fyra verktyg**: `analysera_strandskydd_vid_punkt` (Fall 7),
`analysera_olovligt_byggande_vid_punkt` (Fall 1),
`analysera_lovavvikelse_vid_punkt` (Fall 3) och `generera_dossier`.

Den interna moduluppdelningen bevaras dock med skarpa gränser — `timeline.py`,
`datering.py`, `delta.py`, `juridik.py`, `lovarkiv.py`, `lovtolk.py`,
`dossier.py` är fristående, testbara moduler. Det gör en framtida uppdelning i
flera publicerbara paket billig när den blir motiverad.

## Konsekvenser

- Färre driftsenheter, en gemensam testsvit (118 hermetiska tester), en
  transport-uppsättning att härda mot Eneos krav (streamable HTTP, 8 kB-tak,
  DNS-rebinding-allowlist).
- Skakravet påverkas inte: verktygen är fortfarande fristående anropbara
  MCP-funktioner över den transport Eneo kräver, med kompakta
  referensbaserade svar.
- Uppdelning i flera servrar kvarstår som en riktig utbyggnadspunkt för
  genomförandefasen, särskilt när kommuner med andra käll-system ansluts
  (rule of three, jfr [[000-repo-struktur]] §1). `mcp-ogc` (redan publicerad
  under AGPLv3) är prejudikatet för hur ett sådant paket ser ut.

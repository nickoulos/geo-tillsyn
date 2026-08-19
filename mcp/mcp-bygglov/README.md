# mcp-bygglov

Bygglovshistorik för en fastighet. **I prototypfasen: enbart syntetiska testärenden**
från `data/synthetic/lovarkiv/` (verkliga byggärenden är inte tillgängliga —
Sokigo Nova kräver avtal).

Implementerat i `src/geo_tillsyn/lovarkiv.py` + MCP-verktyget
`hamta_bygglovsarenden_for_fastighet(fastighetsbeteckning)` i `server.py`.

## ByggR-kompatibel yta (2026-08-19)

Kommunen skickade fältbeskrivning + metodlista för den verkliga exporttjänsten
Sokigo/Tekis **ArendeExportWS** (se `docs/byggr-arendeexportws.md`). Mocken
speglar den:

| ArendeExportWS | lovarkiv.py |
| --- | --- |
| `GetRelateradeArendenByFastighet(fnr, trakt, fBetNr, arHuvudObjekt, status)` | `hamta_arenden_by_fastighet(katalog, trakt, fbetnr, status)` |
| `GetDocument(documentId, inkluderaFil, docSplitToken)` | `get_document(katalog, handling_id, inkludera_fil)` |
| `arende.{arendeId, dnr, diarieprefix, arendetyp, beskrivning, slutDatum, handelseLista→handlingLista→handlingId, objektLista}` | samma nycklar |

Beslutets sakinnehåll (laga kraft, BYA, höjd, godkänt läge) finns inte som fält
i tjänstens `arende` — det ligger i handlingarna. Mocken lägger dem under
`_geoTillsynMock` (tydligt markerat) så att ingen förväxlar dem med tjänstens fält.
En framtida koppling byter datakälla, inte gränssnitt.

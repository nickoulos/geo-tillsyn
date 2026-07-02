# mcp-regelverk

Tidsmedveten regeltolkning: `regelverk_vid(punkt, datum)` returnerar det
juridiska sammanhang som gällde vid en given tidpunkt på en given plats.

**Nuläge (Spike D):** ren kärna `regelverk_core.regelverk_vid(datum, kontext,
bedomningsdatum)` + versionerad regelmodell i `regler.json` + 8 gröna tester
(`pytest test_regelverk.py`). Rumsliga fakta (inom strandskydd/detaljplan)
injiceras via `Kontext` — i produktion löses de av MCP-servern via WMS
GetFeatureInfo (se `docs/data-findings.md` §1).

Modellen kodar bl.a.:

- PBL-eror: BL/BS → ÄPBL (1987-07-01) → PBL 2010:900 (2011-05-02)
- Friggebod 10 m² (1979) → 15 m² (2008); attefallshus 25 m² (2014-07-02) →
  30 m² (2020-03-01)
- Generellt strandskydd sedan 1975-07-01: äldre anläggningar lagliga;
  **bygglovsbefrielse (attefall) ger INTE strandskyddsdispens**; upphävda
  zoner kräver ingen dispens
- Preskription: PBL-tioårsregeln (11 kap. 20 § 2 st), byggsanktionsavgift 5 år
  (11 kap. 58 §), **ingen preskription för strandskyddstillsyn enligt MB**

> ⚠ **Förenklad prototypmodell.** Datum och lagrum ska juridikgranskas innan
> demo (Sprint 3). Modellen är datadriven — korrigeringar görs i `regler.json`
> utan kodändring.

**Kommande (Sprint 3):** MCP-server (streamable HTTP, ADR-001) som exponerar
`regelverk_vid` som verktyg och löser `Kontext` live mot GeoServer; koppling
till detaljplan-versioner.

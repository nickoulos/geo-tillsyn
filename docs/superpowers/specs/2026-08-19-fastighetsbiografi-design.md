# Geo-Tillsyn v0.7 — Fastighetsbiografi: tesen som en bild

**Datum:** 2026-08-19 · **Status:** Godkänd riktning (scope C) · **Deadline:** inlämning 2026-08-25
**Bygger på:** v0.5 UX-redesign (2026-07-30) och v0.6 (språk hela vägen, snedbilder).

## Motiv

Headless-rendering av dagens UI efter ett klick på ALNÖ-USLAND 1:45 visar att
produkten är en **ärlig datainspektör, inte en berättelse** — och den muntliga
demon väger 70 %:

1. Panelen är en *förbehållsmaskin*: kortrubriken "Se underlag" följs av en
   bärnstensfärgad vägg med sex punkter (upprepad ordagrant i nästa kort) och en
   tabell där varje rad är »Ej fastställt«. Ärligheten dränker fynden.
2. Kartan gör inget berättande: 75 % av skärmen är 2023 års ortofoto, Fall 3-
   överlägget är ~30 px brett och zoomas inte till, tidslinjen är en slider med
   ett årtal. **"Verklighet vs Rättighet över Tid" syns ingenstans som en bild.**
3. Ingen hierarki: tre identiska kort oavsett om de hittat +38,4 % eller inget.
   13 px nyckel/värde-rader läses som DevTools på projektor.
4. Demomanuset lovar UI som inte finns: 2007-rutan "byggnad syns", Fall 1:s
   utgångna klocka bredvid Fall 7:s icke-existerande, radar-vyn, det synligt
   tomma Beslut-fältet.
5. Strandskyddskortets rubrik "28 av 71 byggnader berör strandskyddszon" handlar
   om radien, inte fastigheten; Bedömning är "—".

## Mål

En juryledamot ska efter ett klick se **en bild som bär tesen** (tid × verklighet
× rättighet), **siffrorna först** i panelen, och i finalen en **radar** över zonen —
allt utan att UI:t någonsin säger ett skuld- eller friande ord som backend inte
skickat.

## Icke-mål

- Ingen ramverksmigrering, inget nytt beroende (vanilla JS, webpack, `node --test`).
- MCP-verktygens kontrakt (Eneo) ändras endast additivt (nya fält), aldrig
  brytande; ≤ 8 kB-gränsen respekteras.
- Ingen ny juridik i UI:t: alla utfall (preskriberad, dispens krävs, överens …)
  kommer från backend-fält; stripen ritar bara geometri av datum + regler.json.
- Inget riktigt radar-batchjobb över hela kommunen — "radar-lite" återanvänder
  Fall 7-analysens träffar inom klickradien.

## 1. Layout

```
┌──────────────────────────────────────────────┬──────────────────┐
│  Karta (Origo)                               │  Panel (420 px)  │
│                                              │  huvud           │
│        [fastighetsmarkör + överlägg]          │  fastighet       │
│                                              │  sammanfattning  │
│                                              │  kort ×3         │
│  [legend]                                    │  snedbilder      │
├──────────────────────────────────────────────┤  beslut          │
│  Biografi-strip (full kartbredd, ~170 px)    │                  │
│  ‹ 1960 ───────────── cursor ─────── 2027 ›  │  fot             │
└──────────────────────────────────────────────┴──────────────────┘
```

- Panelen breddas 380 → **420 px**; bastypografi 13 → **14 px**; rubriksiffror
  **22 px/800**; kortrubrik 15 px. Stripen dockas längst ned i **kartytan**
  (inte under panelen) med full bredd; den kan fällas ihop till en 40 px rad
  (endast år + ‹ ›) via en knapp i stripens högra kant. Under 900 px bredd
  visas stripen i ihopfällt läge.
- Tidslinjepillen (`timeline.js`) tas bort och ersätts av `biografi.js`.

## 2. Biografi-stripen (`biografi.js` + `biografi-logik.mjs`)

En SVG (viewBox skalad till containerbredd) med en gemensam x-axel
**1960 → innevarande år + 1** (2027) och fyra spår. Ett vertikalt **cursor-streck**
= valt år; drag/klick på axeln och ‹ › snappar till närmaste ortofotoårgång
(samma logik som idag: `narmasteAr`, `stegAr`). Ett tunt streck markerar "idag".
Ortofotoårgångarna är ticks på axeln (ojämnt — visas ärligt).

**Spår uppifrån:**

| Spår | Innehåll | Källa |
|---|---|---|
| **Verklighet** | En punkt per ortofotoårgång: fylld blå = byggnad syns (`narvaro`), grå ring = syns inte (`franvaro`), bärnsten = otydlig (`otydlig`), streckad ring = utesluten (saknar bildinnehåll). Dateringsintervallet `sista_ar_utan → forsta_ar_med` ritas som en klammer med etikett "först synlig 2002–2007". Före klick: bara ticks. | `/api/olovligt`: `narvaro_per_ar` (NYTT), `uteslutna_ar` (NYTT), `sista_ar_utan`, `forsta_ar_med` |
| **Register & lov** | Händelsemarkörer: BAL nybyggnadsår (romb, "Register 2014"), lovbeslut (dokumentikon, "Lov SBN 2009-0412"), ev. tillbyggnadsår. Ligger registret utanför dateringsintervallet ritas ett streckat "gap" mellan intervallets slut och registret med flaggan "avviker" — **endast** när backend skickat `bal_forenligt: false`. | `olovligt.bal_nybyggnadsar`, `olovligt.bal_forenligt`, `lovavvikelse.beslutsdatum`, `lovavvikelse.dnr` |
| **Rättighet** | Band: lagregim (BL/BS → ÄPBL → PBL) som bakgrundsfält med namn; lovbefrielser (friggebod 10 → 15, attefall 25 → 30, komplementbyggnad 30/50) som tunna staplar med m²-etikett; strandskydd som band från 1975-07-01 som löper ut ur högerkanten. Cursorn lyfter fram banden som gäller valt år (övriga dämpas). Klick på "Regelverk YYYY" öppnar samma detaljvy som idag (`renderKontextDetalj`). | `regler.json` (oförändrad) |
| **Klockor** | Endast efter klick. Från dateringsintervallets slut: stapel **Rättelse 10 år** (PBL 11:20) och **Sanktionsavgift 5 år** (11:58); den del av stapeln som beror på intervallets osäkerhet (mellan `sista_ar_utan`+N och `forsta_ar_med`+N) är skrafferad. Stapeln märks "utgången YYYY" resp. "löper till YYYY" **enligt backend-fältet** (`rattelse_preskriberad`, `sanktionsavgift_mojlig`), aldrig egen beräkning. Ligger byggnaden inom strandskydd: tredje stapel **Strandskydd** från samma start, ut genom högerkanten med pil och etikett "ingen preskription · MÖD 2021:6" — när `preskriberas === false` i träffen för vald byggnad. | `olovligt.*`, `strandskydd.traffar[vald]`, `regler.json.preskription` |

**Neutralitetsregel för stripen:** etiketter hämtas från backend-fält eller
regler.json; stripen räknar bara *var* något ritas (datum + antal år), aldrig
*om* något gäller.

**Interaktion:** cursorbyte → samma effekt som idag (`visaAr`: ortofotolager +
regelkontext). Hover på en punkt i Verklighet visar årets poäng (`poang_per_ar`)
i en tooltip. Klick på en punkt i Verklighet flyttar cursorn dit.

**Ren logik (`biografi-logik.mjs`, testad):** `xSkala(domain, bredd)`,
`klassificeraAr(olovligtSvar) -> {ar: 'narvaro'|'franvaro'|'otydlig'|'utesluten'|'okand'}`,
`lagBand(regler, domain)`, `lovbefrielseBand(regler)`, `klockor(olovligt, strandskyddTraff, regler)`
→ lista `{namn, start, slutSaker, slutOsaker, oandlig, etikettKod}`, `registerGap(olovligt)`.

## 3. Panelen — fynden först

- **Fastighetsrubrik** som idag + rad "Granskad punkt · E/N (SWEREF 99 TM)" i 11 px.
- **Sammanfattningsrad** (nytt, direkt under rubriken): tre chips, en per kontroll,
  med kontrollens namn och ett *underlagsläge* — aldrig ett utfall:
  `Underlag finns` (rubrikraden kunde komponeras av backend-fält) ·
  `Osäkert underlag` (rubrik finns men `matningskritiskt`/`matningskritiska` ≠ tomt
  eller datering saknas) · `Inget underlag` (404/info) · `Hämtar…` · `Fel`.
  Klick på chip scrollar till kortet.
- **Kontrollkort:**
  - Rubrikraden blir **display-storlek** (22 px/800, tabular-nums) med en
    underrad i 13 px. Exempel Fall 3: **+90,3 m²** / "+38,4 % mot godkänt lov ·
    SBN 2009-0412". Fall 1: **2002 → 2007** / "först synlig i ortofoto · registret
    säger 2014" (+ badge "avviker" endast vid `bal_forenligt === false`). Fall 7
    (vald byggnad): **Inom strandskydd** / "zon 2281K-ÖVR-241 · uppförd 2014 ·
    ingen preskription". Saknas komponerbara fält: "Se underlag" (som idag).
  - **Osäkerheter** visas som en chip "6 osäkerheter ▸" som expanderar listan —
    inte som en öppen vägg. Dubbletter mellan korten lämnas (backend-fråga).
  - Fakta hopfällt, Bedömning öppet (som idag), större radtypografi (13.5 px).
- **Strandskyddskortet byts till fastighetsperspektiv:** rubriken gäller den
  byggnad närmast klicket (`vald_byggnad_id`, NYTT backend-fält; träffen ligger
  först i `traffar`). Därunder rad "27 andra byggnader inom 150 m berör zonen" med
  knappen **"Visa kandidater i kartan"** → radar-lite (avsnitt 5). Är vald
  byggnad inte en träff: rubrik "Utanför zon" + samma kandidatrad.
- **Beslut-block** (nytt, sist i kortlistan, före snedbilder): ett kort med
  låsikon, rubrik "Beslut", och ett *avsiktligt tomt*, streckat fält med texten
  "— fylls inte i av verktyget —" och underraden "Dossiern har inget beslutsfält:
  bedömningen är handläggarens." (Demomanusets close-up.)
- Foten behålls.

## 4. Kartan

- **Auto-zoom vid klick:** när `/api/lovavvikelse/geometri` svarar, `fit` till
  verkligt+godkänt läge med padding (höger padding = panelbredd); annars `fit`
  till en 80 m-ruta runt punkten. Max zoom begränsas så ortofotot inte blir
  pixelgröt (Origo-resolution ≥ 0,1 m/px).
- **Klickmarkör:** ring + punkt på klickpunkten (eget vektorlager, rensas vid nytt klick).
- **Fall 3-överlägg:** linjer 3 px + halvtransparent skraffering (blå godkänt /
  röd verkligt), legend som idag men 13 px.
- **Fall 7:** när vald byggnad är `inom`/`delvis` tänds lagret
  `Lansstyrelsen:Strandskydd_yta` (Tillsynslager) automatiskt.

## 5. Radar-lite (finalen)

- **Backend NYTT:** `GET /api/strandskydd/geometri?easting&northing&radie_m` →
  GeoJSON FeatureCollection (EPSG:3014) med träffarnas byggnadspolygoner och
  properties `{byggnad_id, laege, byggnads_ar, gallde_vid_uppforande,
  dispens_kravs_idag, preskriberas, har_atgarder, rang}`; `rang` (1 = mest
  underlag för granskning) ges av en ren, testad funktion:
  (a) `gallde_vid_uppforande === true` (uppförd efter 1975-07-01 inom zon),
  (b) `byggnads_ar === null` (år okänt), (c) `gallde_vid_uppforande === false`
  (lagligen uppförd före 1975); inom grupp: `laege` inom före delvis, sedan
  byggnad_id. Svaret är för kartan — **aldrig ett MCP-verktyg** (samma gräns som
  `fall3_geometri`).
- **Frontend:** knappen i strandskyddskortet hämtar geometrin, ritar träffarna
  som bärnstensfärgade polygoner med numrerade markörer (`rang`) i ett eget
  lager, och byter panelens kropp till **Kandidatlista**: rubrik "Kandidater inom
  150 m — sorterade efter underlag, inte beslut", rader `#rang · byggnad_id ·
  byggår/okänt · inom/delvis` med hover-highlight på kartan; **klick på rad =
  kartklick på byggnadens centroid** (full granskning). Tillbaka-knapp.
  Förklaringsrad: "Anmälningsdriven tillsyn är ojämlik — listan är kandidater,
  handläggaren beslutar." (UI-chrome, översätts.)

## 6. Backend-tillägg (additiva)

| Ändring | Fil | Test |
|---|---|---|
| `DateringsResultat.narvaro_per_ar: dict[int,str]` (narvaro/franvaro/otydlig) + `uteslutna_ar: list[int]` | `datering.py` | befintliga + nytt |
| `/api/olovligt` + MCP-verktyg: `narvaro_per_ar`, `uteslutna_ar` | `runner.py` | `test_fall1_runner` |
| `/api/strandskydd` + MCP-verktyg: `vald_byggnad_id` (via `_valj_byggnad`), vald träff först i `traffar` | `runner.py` | `test_runner` |
| `rangordna_traffar(traffar) -> list` (ren) + `fall7_geometri(...)` | `runner.py` | nytt |
| `GET /api/strandskydd/geometri` (CORS/OPTIONS som övriga) | `server.py` | `test_webapi` |

## 7. Teststrategi

- Backend: pytest hermetiskt (164 → fler), inga nätanrop i tester.
- Plugin: `node --test` för `biografi-logik.mjs`, uppdaterade `dossier`-/`i18n`-
  tester (nya rubriker, underlagsläge, radar-texter), `panel`-logik där den är ren.
- `npm run build` grönt; headless Chrome-rendering med autoklick-harnessen
  (`demo/autoklick.html`, ej i bundle) på 1600×900: tomläge, efter klick på
  komplementbyggnaden (E 158140.4 N 6918389.3, EPSG:3014), efter klick på
  huvudbyggnaden (E 158132.2 N 6918382.6), radar-läge, EN-läge. Skärmdumpar
  granskas av människa/Fable före commit av sista steget.

## 8. Ordning (värde först, så att tidsbrist landar i ett bra läge)

1. Backend-tillägg (liten, hermetisk).
2. Panel fynden-först (kort, chips, beslut-block, strandskydd-perspektiv).
3. Biografi-strip (ersätter pillen).
4. Kartbeteenden (auto-zoom, markör, skraffering, zon-lager).
5. Radar-lite.
6. Docs (README, B-LIVE-STATUS) + demomanusets VISAS-rader.

## Öppna punkter

Inga — riktning godkänd av beställaren 2026-08-19 ("yes go with C").

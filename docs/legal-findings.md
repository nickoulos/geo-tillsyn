# Legal findings — the rules the regelgraf must encode, and where the law lives

> Working document (English during development). Produced 2026-07-17 from multi-agent
> web research against primary sources (riksdagen.se, rkrattsdb.gov.se,
> svenskforfattningssamling.se, Boverket PBL kunskapsbanken, MÖD case law).
> Feeds anchor 3 (**Regelgraf**) and the `regelverk_vid()` MCP tool of
> `docs/superpowers/specs/2026-07-02-geo-tillsyn-steg2-design.md` (bid folder).

> **DISCLAIMER:** this is engineering research, not legal advice. Every paragraph
> reference below must be re-verified against the official SFS before it is cited
> in the written deliverable or shown to the jury. Consolidated text is a
> convenience service — only the original SFS is legally binding (see §4.3).
> Confidence is flagged per claim; items marked ⚠️ are **not** yet verified.

---

## 1. The headline finding: strandskydd has NO preskription

This is the single most valuable finding for the demo, and it is **not** in the
current design doc (which only notes "pre-1975 = legal" for Fall 7).

**Verified.** MÖD 2021:6 (mål nr M 9303-19) states directly:

> *"I strandskyddslagstiftningen finns ingen preskriptionsregel."*

Corroborated by Miljösamverkan Sverige's tillsynsvägledning (*"Det finns ingen
preskription på strandskyddstillsyn"*). Miljöbalken 26 kap contains **no**
time-bar provision for issuing a föreläggande — structurally unlike PBL 11 kap
20 §, which bars rättelseföreläggande after 10 years.

### Why this is the strongest possible proof of "one engine, 9 configurations"

Same property, same timeline, same engine — **opposite legal outcome**, purely
because the applicable rule differs:

| Structure built ~2005 | Rule | Outcome today (2026) |
|---|---|---|
| Unpermitted extension (Fall 1) | PBL 11 kap 20 § — 10-year preskription | **Time-barred** — no rättelseföreläggande |
| Brygga in strandskydd zone (Fall 7) | MB 7 kap / 26 kap — no preskription | **Still enforceable** |

The tidslinje makes this visible: one slider, two verdicts. A naive
"GIS + chatbot" cannot produce this distinction.

### The mandatory counterweight — proportionality (do not overstate)

"No preskription" does **not** mean "enforceable forever against anyone". Two
tempering doctrines, both of which belong in the regelgraf as **human-decides**
nodes, not automated verdicts:

- **MÖD 2017:16 (M 7737-16)**, 2017-04-19: dock from 1989, property acquired 2012.
  Court held the structure's age is irrelevant to strandskydd (no preskription),
  **but** it was not *skäligt* to order a good-faith new owner to demolish —
  *"Det hade inte framkommit något som tyder på att överlåtelsen skett i syfte att
  kringgå strandskyddet…"*. Companion case: M 3186-16.
- **MÖD 2021:6**: confirmed no preskription, but annulled demolition of a ~40-year
  jetty as disproportionate, while upholding removal of fence/table/grill (cheap
  to remove). Also: a föreläggande binds a new owner, but **vite does not** unless
  registered.

Miljösamverkan's four cumulative factors making enforcement against a new owner
unreasonable: (i) measure long ago; (ii) long gap between construction and
transfer; (iii) not done to circumvent strandskydd; (iv) no reason to suspect a
dispens was missing.

**Regelgraf implication:** the strandskydd branch must terminate in
`proportionality_assessment → HUMAN` rather than an automated "demolish" verdict.
This is a *feature* for rättssäkerhet framing, not a limitation.

⚠️ Do not confuse with **åtalspreskription** (criminal): the offence *brott mot
områdesskydd* (MB 29 kap 2 §, referencing 7 kap 15 §) carries up to 2 years, so
criminal prosecution time-bars at 5 years under Brottsbalken 35 kap. That is
entirely separate from — and does not limit — the administrative restoration order.

⚠️ **Watch:** Kommittédirektiv 2025:59 *"Ett reformerat strandskydd"* is an ongoing
inquiry; SFS 2025:512 (in force 2025-07-01, prop. 2024/25:102) already narrowed
scope at small waters. Verify currency before the demo.

---

## 2. Rule timeline — the content of `regelverk_vid()`

The design doc asks for `regelverk_vid(koordinat, datum)`. Below is the verified
content it must return. **Recommendation: hand-curate these ~5 rule families as a
versioned table rather than building a general law-reconstruction engine** (see §4
for why).

### 2.1 Friggebod (permit-exempt complementary building)

| Period | Rule | Source confidence |
|---|---|---|
| From 1980-01-01 | max **two** buildings, **10 m²** combined | Boverket PBL kunskapsbanken (verbatim history) |
| From 2008-01-01 | **15 m²** byggnadsarea per fastighet; the "max 2 buildings" cap removed | Boverket (verbatim) |
| Until 2025-11-30 | 15 m² total, nockhöjd ≤ 3.0 m, ≥ 4.5 m from boundary | Boverket |

⚠️ No SFS number located for the original 1979/80 introduction — sources give the
date, not a statute number. Named after Birgit Friggebo (bostadsminister 1979).

### 2.2 Attefall (komplementbostadshus / komplementbyggnad)

| Date | Change | SFS | Confidence |
|---|---|---|---|
| **2014-07-02** | Introduced, **25 m²** | **SFS 2014:477** (utfärdad 2014-06-05, prop. 2013/14:127) | **Verified** — PDF fetched live |
| **2020-03-01** | komplementbostadshus 25 → **30 m²** | **SFS 2019:412** (utfärdad 2019-06-05, prop. 2019/20:31) | **Verified** — PDF read in full |
| **2020-08-01** | komplementbyggnad also 25 → **30 m²** | Boverket "Lagändringar i PBL 1 augusti 2020" | High |

⚠️ SFS 2019:412's in-force date: trust Boverket's **1 March 2020**; an automated
PDF extraction suggested "1 January 2020" and is unreliable.

### 2.3 ⚠️ CRITICAL — the 2025-12-01 overhaul (NOT in the design doc)

**The largest PBL change since 2011 took effect 2025-12-01** — seven months before
this prototype is submitted. It **abolishes the terms "friggebod" and
"attefallshus"** entirely, replacing them with generic *bygglovsbefriad
komplementbyggnad / komplementbostadshus* and a **combined area pot**:

- within detaljplan: ~**45 m²** total (permit threshold > 30 m² per building)
- outside detaljplan: ~**65 m²** total (permit threshold > 50 m² per building)
- SFS **2025:974 / 2025:975** (+ MB-side 2025:976), prop. 2024/25:169
- Övergångsbestämmelser run to **end of Nov 2027** for certain plan provisions

**Why this is a gift to the demo narrative:** it is live, recent proof that a
solution without a time dimension gives the *wrong answer today*. The jury is
living this change right now. It belongs on the tidslinje as the most recent
event, and it strengthens the ALNÖ-USLAND 1:45 protagonist (55.5 m² built 2014,
2× the then-25 m² cap) — the engine must apply the **2014** rules to it, not
today's.

Source: Boverket change list —
`https://www.boverket.se/sv/samhallsplanering/uppdrag/avslutade-uppdrag/nytt-regelverk-for-bygglov/lista-pbl--andringar/`

### 2.4 Strandskydd (MB 7 kap)

| Date | Change | SFS / source |
|---|---|---|
| Baseline | **100 m** from strandlinjen at normal mean water, land **and** water side (7 kap 14 § 1 st); extendable to **300 m** by Länsstyrelsen (14 § 2 st) | MB 1998:808 |
| **2009-07-01** | "Differentierat strandskydd" reform | **SFS 2009:532**, prop. 2008/09:119 |
| **2010-02-01** | LIS-områden (landsbygdsutveckling i strandnära lägen) provisions enter force | same |
| 2022 | ⚠️ **NO change** — prop. 2021/22:168 was **rejected** by the Riksdag (bet. 2021/22:MJU27). Do not record as an enacted amendment. | — |
| **2025-07-01** | Narrows scope at small waters (lakes ≤1 ha, watercourses ≤2 m), removes protection at artificial/post-1975-06-30 waters, new dispens ground | **SFS 2025:512**, prop. 2024/25:102 |

Prohibited within zone (7 kap 15 §): new buildings, changed use of buildings,
digging/preparation for buildings, measures deterring allemansrätt or harming
flora/fauna. Dispens requires *särskilda skäl* — the six grounds in 7 kap 18c §.

**Tillsynsmyndighet** (Miljötillsynsförordningen 2011:13): **kommun is the default**
(2 kap 9 § p. 4); Länsstyrelsen only in the carve-outs of 2 kap 7 § p. 2
(nationalparker, naturreservat, etc.). Enforcement basis: **MB 26 kap 9 §**
(förelägganden/förbud), 12 § (new owner, *om det är skäligt*), 14 § (vite),
15 § (registration).

### 2.5 Fall 1 sanction mechanics — the m²-threshold sensitivity

Directly relevant to the **bevisstyrka indicator** (design doc line 47), because
measurement uncertainty maps onto hard legal thresholds:

- **Sanktionsarea = bruttoarea − 15 m²** (PBF 1 kap 7 §) — the per-m² charge only
  applies above 15 m².
- Nybyggnad without lov, en-/tvåbostadshus: **1 pbb + 0,025 pbb/m²** sanktionsarea
  (PBF 9 kap 6 § p. 1). Komplementbyggnad > 15 m²: 0,35 pbb + 0,025 pbb/m².
  Byggnad ≤ 15 m²: 0,25 pbb flat.
- Worked example: unpermitted 100 m² house → sanktionsarea 85 → 1 + 2,125 = **3,125 pbb**.
- Cap: **50 prisbasbelopp** (PBL 11 kap 52 §). Prisbasbelopp of the **decision
  year** applies (PBF 9 kap 1 §).
- **Strict liability**: charged even without intent/negligence (PBL 11 kap 53 § 1 st).
- **Nedsättning** to ½ or ¼ only, if disproportionate (PBL 11 kap 53 a §, SFS 2013:307).
- **No avgift if rättelse happens before the matter is taken up at a nämnd meeting**
  (PBL 11 kap 54 §) — an actionable insight for the klarspråk dossier.
- **5-year limit** for byggsanktionsavgift (PBL 11 kap 58 § 2 st) — *distinct from*
  the 10-year preskription for rättelseföreläggande. Two different clocks.

**Engine implication:** report footprint as an **interval** (e.g. 23–26 m² given
~2 m Fastighetskartan accuracy) and state whether the *whole interval* clears the
threshold. When the interval straddles a threshold → `MEASUREMENT_CRITICAL → HUMAN`.

### 2.6 Fall 1 enforcement path (PBL 11 kap)

`5 §` tillsyn is **mandatory** ("ska pröva … så snart det finns anledning att anta")
→ `17 §` **lovföreläggande** if lov could probably be granted retroactively ("ska")
→ `20 §` **rättelseföreläggande** (10-year bar in 2 st; handräckning bar in 39 §)
→ `37 §` vite (available for 19/20 §, **not** for 17 §)
→ `40–41 §§` anteckning i fastighetsregistret → binds new owner (46 §)
→ `51 §` byggsanktionsavgift.
Appeal: nämnd → länsstyrelsen (13 kap 3 §) → mark- och miljödomstol (13 kap 6 §)
→ MÖD (prövningstillstånd).

---

## 3. Where the law actually lives (verified live)

**Verdict: `regelverk_vid()` is data-feasible and free.** All endpoints below were
verified reachable, no auth, free (riksdagen requires attribution to "Sveriges riksdag").

| Source | What it gives | As-of-date? | Status |
|---|---|---|---|
| **rkrattsdb.gov.se** `/SFSdoc/{YY}/{YYNNNN}.PDF` | **As-issued original PDFs**, base acts *and* every amendment | n/a (per-act) | **Verified live.** Range **1998:306 → 2018:159** exactly (1998:305 = 404; 2018:200 = 404). Pre-1998 **not** present (1987:10 → 404). |
| **svenskforfattningssamling.se** `/sites/default/files/sfs/{YYYY-MM}/SFS{YYYY}-{NNN}.pdf` | As-issued PDFs, **official & authentic** | n/a (per-act) | **Verified** (PDFs fetch; HTML 403s bots). **Only from 2018-04-01.** |
| **data.riksdagen.se** `/dokument/sfs-2010-900.json\|.text\|.html` | **Current consolidated** text, machine-readable | **No** | **Verified** — 11,536 SFS docs. `undertitel` = "t.o.m. SFS …". **No** amendment array, **no** bulk SFS dataset. |
| **rkrattsbaser.gov.se** `/sfsr?bet=2010:900` | **Amendment register** — every SFS + in-force date + affected §§ + förarbeten | No | Verified (~76 amendments for PBL). **HTML only, no API.** |
| **lagen.nu** `/{SFS}/konsolidering/{amending-SFS}` | **True historical snapshots** ("Tidsmaskin", 2019) | **Yes** | Free but **unofficial**; ~last 15 years; incomplete (some snapshots 404). Self-disclaims accuracy. |
| **Boverket PBL kunskapsbanken** | Dated narrative rule history | n/a | Best free source for the 1980/2008/2014 chronology. |
| Karnov Open (free) / JUNO, JP Infonet (paid) | "Ändrade lydelser" / as-of-date | Yes | Karnov Open is free; JUNO/JP Infonet paywalled. |

**Not available:** Sweden does **not** implement **ELI**, does **not** publish
**Akoma Ntoso**. The old national RDF/SPARQL system (rinfo/lagrummet) is
**defunct** (last commit 2016, `dev.lagrummet.se` offline). No structured
amendment→base-act graph exists anywhere official.

**Direct hits for our timeline** (verified HTTP 200, application/pdf):
- PBL base: `https://rkrattsdb.gov.se/SFSdoc/10/100900.PDF` (265,079 bytes)
- Attefall: `https://rkrattsdb.gov.se/SFSdoc/14/140477.PDF` (34,430 bytes)
- 30 m²: `https://svenskforfattningssamling.se/sites/default/files/sfs/2019-06/SFS2019-412.pdf`
- Strandskydd 2009: `https://rkrattsdb.gov.se/SFSdoc/09/090532.PDF`

---

## 4. The hard part — and why it makes us look good

### 4.1 ⚠️ "Which law applied on date X?" is the WRONG question

**Verified verbatim** from the official PBL PDF (rkrattsdb.gov.se/SFSdoc/10/100900.PDF,
övergångsbestämmelser p. 72–73):

> **1.** Denna lag träder i kraft den 2 maj 2011 då plan- och bygglagen (1987:10)
> … ska upphöra att gälla.
> **2.** Äldre föreskrifter ska fortfarande gälla för mål och ärenden som har
> **påbörjats** före den 2 maj 2011 … **till dess målet eller ärendet är slutligt avgjort.**

So the repealed ÄPBL 1987:10 governs any ärende *started* before 2011-05-02 —
possibly for years, through appeals. **A pure calendar lookup gives wrong answers.**

The pattern recurs *inside* amendments: SFS 2020:239 entered force 2020-05-15 but
keeps the older 8 kap 4 § wording for bygglov applications filed **before
2021-03-11** — a date tied to *when the application was filed*, not to the
in-force date.

**Design implication for `regelverk_vid()`:** the signature in the design doc
(`koordinat, datum`) is insufficient. Either add an `ärende_startdatum` parameter,
or — cheaper and equally persuasive — return an explicit
`övergångsbestämmelse_varning` field whenever the queried date falls near a
transition. **This is precisely where naive solutions are wrong.** Rival "GeoReason"
(change-detection-centric) almost certainly does not model it.

### 4.2 Amendments are edit instructions, not diffs

Verified verbatim (SFS 2020:239): *"föreskrivs att 8 kap. 4 § … ska ha följande
lydelse"*, plus forms *"ska upphöra att gälla"* / *"det ska införas … av följande
lydelse"*. Reconstruction requires parsing natural-language edit directives,
resolving a textual address ("8 kap. 4 §"), and splicing. Chapters/paragraphs get
**renumbered** across time, so address identity must be tracked. Also: one SFS can
have **different provisions enter force on different dates**, so applying
amendments in SFS-number order is **wrong** — order by ikraftträdande, per provision.

### 4.3 Consolidated text is not binding

Official SFS (printed pre-2018-04-01; electronic after) is the authentic text.
Consolidated versions are a convenience — riksdagen replaces old text on
amendment (*"Om en författning ändras ersätts den gamla texten med den nya"*),
so **history is destroyed** in the consolidated view. lagen.nu disclaims accuracy
and notes its own reformatting can introduce errors.

**Product implication:** always present reconstructed wording as *editorial
guidance* and cite the official SFS PDF URL. This is the **citation discipline**
the regelgraf already implies — now it has a documented reason.

### 4.4 Recommendation for the sprint

**Do NOT build a general as-of-date reconstruction engine.** That is the expensive,
error-prone part and it would consume the remaining weeks. Instead:

1. Hand-curate a **versioned rule table** for the ~5 rule families in §2:
   `{rule_id, valid_from, valid_to, sfs, threshold_values, source_url, transitional_caveat}`.
2. Populate from **Boverket + rkrattsbaser amendment register** (both free).
3. Link every version to its **official SFS PDF** (§3) for citation.
4. Make `transitional_caveat` a **first-class, surfaced field** — the differentiator.
5. Optionally use **lagen.nu konsolidering URLs** as a convenience link for
   "see the wording as it stood" — free, but label it unofficial.

---

## 5. Open items / to verify before submission

- ⚠️ Exact SFS number for the original friggebod introduction (1979/80) — not found.
- ⚠️ Whether the 2025-12-01 overhaul changes the **strandskydd** analysis (MB-side
  SFS 2025:976) — confirm scope.
- ⚠️ Confirm PBF 9 kap coefficients against the **live** PBF; some åtgärdstyp
  sub-sections have been amended (Attefall-related).
- ⚠️ Boverket's dynamic pages 404 to automated fetchers but are live in a browser —
  re-verify the friggebod/attefall history quotes manually before citing.
- ⚠️ Förvaltningslagen cross-references inside PBL still cite the repealed
  FL 1986:223; the applicable act is **FL 2017:900** (kommunicering 25 §,
  motivering 32 §).
- Decide: does the prototype model the **pre-** or **post-**2025-12-01 regime as
  "today"? (Recommendation: post — it is current law, and the contrast with 2014
  is the whole point.)

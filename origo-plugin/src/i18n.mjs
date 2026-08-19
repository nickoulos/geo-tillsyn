/**
 * i18n för Geo-Tillsyn-pluginet: UI-chrome, fältetiketter, värden och
 * backendens meddelanden på sv/en.
 *
 * Endast våra egna etiketter översätts — författningsnamn ur regler.json
 * (SFS-titlar, "friggebod", lagrum) är officiella svenska termer och står
 * kvar ordagrant på båda språken. Detsamma gäller tekniska identifierare:
 * WFS-lagernamn, diarienummer och fältnamn som `bal_nybyggnadsar`.
 *
 * MEDDELANDEN speglar den svenska katalogen i src/geo_tillsyn/meddelanden.py.
 * Backend skickar `{kod, params}` i stället för färdig svenska, så att panelen
 * kan rendera osäkerheter, åtgärder och felmeddelanden på valt språk utan att
 * hämta om analysen. Ordalydelsen ska hållas lika mellan katalogerna;
 * decimaltecknet följer däremot varje språks konvention (sv: komma), precis
 * som formatTal gör för panelens övriga tal.
 */

export const TEXTS = {
  sv: {
    appNamn: 'Geo-Tillsyn',
    appKontext: 'Sundsvall · pilot',
    panelAria: 'Geo-Tillsyn analyspanel',
    sprakKnapp: 'EN',
    sprakKnappAria: 'Switch to English',
    kollapsAria: 'Fäll ihop panelen',
    oppnaAria: 'Öppna Geo-Tillsyn-panelen',
    knappTooltip: 'Geo-Tillsyn',
    tomRubrik: 'Granska en fastighet',
    tomText: 'Klicka på en fastighet i kartan så granskar Geo-Tillsyn den mot '
      + 'ortofotohistorik, bygglov och strandskydd.',
    fastighet: 'Fastighet',
    saknarBeteckning: 'beteckning saknas',
    ingenFastighet: 'Ingen fastighetsbeteckning på denna punkt',
    checkTitel: {
      olovligt: 'Byggnad utan lov',
      lovavvikelse: 'Avvikelse från bygglov',
      strandskydd: 'Strandskydd'
    },
    checkUndertitel: {
      olovligt: 'Ortofotohistorik mot byggnadsregistret',
      lovavvikelse: 'Verkligt läge mot godkänt lov',
      strandskydd: 'Byggnader mot skyddszoner'
    },
    analyserar: 'Analyserar…',
    seUnderlag: 'Se underlag',
    fakta: 'Fakta',
    bedomning: 'Bedömning',
    kallor: 'Källor',
    osakerheter: 'Osäkerheter',
    beslutText: 'Beslutet fattas alltid av handläggaren.',
    forsokIgen: 'Försök igen',
    felHamtning: 'Kunde inte hämta analysen',
    ejFaststallt: '»Ej fastställt«',
    inga: 'inga',
    ja: 'Ja',
    nej: 'Nej',
    godkantLage: 'Godkänt läge',
    verkligtLage: 'Verkligt läge',
    tidslinjeAria: 'Tidslinje',
    sliderAria: 'Välj årtal för ortofoto och regelverk',
    foregAr: 'Föregående årgång',
    nastaAr: 'Nästa årgång',
    regelverk: 'Regelverk',
    regelverkAria: 'Visa regelverket för valt år',
    statutNot: '',
    biografiAria: 'Fastighetsbiografi',
    sparVerklighet: 'Verklighet',
    sparRegister: 'Register & lov',
    sparRattighet: 'Rättighet',
    sparKlockor: 'Klockor',
    biografiKollapsAria: 'Fäll ihop biografistripen',
    biografiOppnaAria: 'Fäll ut biografistripen',
    forstSynlig: (sista, forsta) => `först synlig ${sista}–${forsta}`,
    registerEtikett: (ar) => `Register ${ar}`,
    lovEtikett: (dnr) => `Lov ${dnr}`,
    rattelse: 'Rättelse',
    sanktion: 'Sanktionsavgift',
    arLabel: 'år',
    utgangen: (ar) => `utgången ${ar}`,
    loperTill: (ar) => `löper till ${ar}`,
    ingenPreskription: 'ingen preskription · MÖD 2021:6',
    idagLabel: 'idag',
    avvikerBadge: 'avviker',
    lag: 'Lag',
    lovbefrielser: 'Lovbefrielser',
    ingaLovbefrielser: 'inga lovbefrielser',
    strandskydd: 'Strandskydd',
    ssKort: 'strandskydd gäller',
    ssKortInte: 'inget generellt strandskydd',
    ssGaller: '<b>gäller</b> inom zon (dispens krävs — lovbefrielse ger inte dispens)',
    ssFinnsInte: (d) => `<b>fanns inte än</b> (generellt strandskydd infördes ${d})`,
    preskription: 'Preskription',
    preskriptionText: (ar, slut, harLopt) =>
      `åtgärd från ${ar} — tioårsregeln löper ut <b>${slut}</b> `
      + `(${harLopt ? 'har löpt ut' : 'löper ännu'}; strandskydd preskriberas aldrig)`,
    regelmodellEjLaddad: 'regelmodell ej laddad',
    rubrikOlovligt: (sista, forsta) => `Uppförd ${sista}–${forsta} enligt ortofoto`,
    rubrikOlovligtRegister: (ar) => `nybyggnadsår ${ar} i registret`,
    rubrikAvvikelse: (diff, pct) => `${diff} m² (${pct} %) mot godkänt lov`,
    rubrikStrandskydd: (traffar, totalt) => `${traffar} av ${totalt} byggnader berör strandskyddszon`,
    snedbildRubrik: 'Snedbilder',
    snedbildUnder: 'Fasader från fyra håll (MapSpace) — för egen granskning av höjd och utseende',
    snedbildLaddar: 'Hämtar snedbilder…',
    snedbildOppna: 'Öppna i MapSpace',
    snedbildSaknas: 'Inga snedbilder över punkten',
    snedbildFel: 'Snedbilder kunde inte hämtas',
    snedbildAlt: (riktning, datum) => `Snedbild mot ${riktning}, ${datum}`,
    riktning: { N: 'Norr', E: 'Öster', S: 'Söder', W: 'Väster' },
    radarKnapp: 'Skanna vyn',
    radarKnappAria: 'Tillsynsradar: skanna synlig kartvy efter byggnader i strandskyddszon',
    radarRubrik: 'Tillsynsradar',
    radarUnder: 'Byggnader mot strandskyddszoner i hela den synliga vyn — samma motor, samma måttstock för alla',
    radarRubrikRad: (traffar, totalt) => `${traffar} kandidater av ${totalt} byggnader i vyn`,
    radarLaddar: 'Skannar vyn…',
    radarIngaKandidater: 'Inga byggnader möter strandskyddszon i vyn.',
    radarFel: 'Skanningen kunde inte genomföras',
    radarTrunkerad: (visade, totalt) => `Visar ${visade} av ${totalt} kandidater — zooma in för resten.`,
    radarPoangmodell: 'Så räknas poängen',
    radarVisaGrunder: 'Grunder',
    radarPoangEnhet: 'p',
    radarAr: 'år',
    radarOppnaAria: (rang) => `Öppna kandidat ${rang} i kartan och granska`,
    radarTillbaka: 'Till radarlistan',
    rattighetTyp: {
      'Ledningsrätt': 'Ledningsrätt', 'Officialservitut': 'Officialservitut',
      'Avtalsservitut': 'Avtalsservitut', 'Gemensamhetsanläggning': 'Gemensamhetsanläggning'
    }
  },
  en: {
    appNamn: 'Geo-Tillsyn',
    appKontext: 'Sundsvall · pilot',
    panelAria: 'Geo-Tillsyn analysis panel',
    sprakKnapp: 'SV',
    sprakKnappAria: 'Byt till svenska',
    kollapsAria: 'Collapse the panel',
    oppnaAria: 'Open the Geo-Tillsyn panel',
    knappTooltip: 'Geo-Tillsyn',
    tomRubrik: 'Inspect a property',
    tomText: 'Click a property on the map and Geo-Tillsyn checks it against the '
      + 'orthophoto record, building permits and shoreline protection.',
    fastighet: 'Property',
    saknarBeteckning: 'no designation',
    ingenFastighet: 'No property designation at this point',
    checkTitel: {
      olovligt: 'Building without permit',
      lovavvikelse: 'Deviation from permit',
      strandskydd: 'Shoreline protection'
    },
    checkUndertitel: {
      olovligt: 'Orthophoto record vs building register',
      lovavvikelse: 'Actual vs approved position',
      strandskydd: 'Buildings vs protected zones'
    },
    analyserar: 'Analysing…',
    seUnderlag: 'See underlying data',
    fakta: 'Facts',
    bedomning: 'Assessment',
    kallor: 'Sources',
    osakerheter: 'Uncertainties',
    beslutText: "The decision is always the caseworker's.",
    forsokIgen: 'Try again',
    felHamtning: 'Could not fetch the analysis',
    ejFaststallt: '»Not established«',
    inga: 'none',
    ja: 'Yes',
    nej: 'No',
    godkantLage: 'Approved position',
    verkligtLage: 'Actual position',
    tidslinjeAria: 'Timeline',
    sliderAria: 'Select year for orthophoto and legislation',
    foregAr: 'Previous vintage',
    nastaAr: 'Next vintage',
    regelverk: 'Legislation',
    regelverkAria: 'Show the legislation in force for the selected year',
    statutNot: 'Swedish statutory names (acts, “friggebod”, “attefallshus”) are kept verbatim.',
    biografiAria: 'Property biography',
    sparVerklighet: 'Reality',
    sparRegister: 'Register & permit',
    sparRattighet: 'Entitlement',
    sparKlockor: 'Clocks',
    biografiKollapsAria: 'Collapse the biography strip',
    biografiOppnaAria: 'Expand the biography strip',
    forstSynlig: (sista, forsta) => `first visible ${sista}–${forsta}`,
    registerEtikett: (ar) => `Register ${ar}`,
    lovEtikett: (dnr) => `Permit ${dnr}`,
    rattelse: 'Correction',
    sanktion: 'Building sanction fee',
    arLabel: 'years',
    utgangen: (ar) => `expired ${ar}`,
    loperTill: (ar) => `runs until ${ar}`,
    ingenPreskription: 'never time-barred · MÖD 2021:6',
    idagLabel: 'today',
    avvikerBadge: 'differs',
    lag: 'Act',
    lovbefrielser: 'Permit exemptions',
    ingaLovbefrielser: 'no permit exemptions',
    strandskydd: 'Shoreline protection',
    ssKort: 'shoreline protection applies',
    ssKortInte: 'no general shoreline protection',
    ssGaller: '<b>applies</b> within zone (dispensation required — a permit exemption does not grant dispensation)',
    ssFinnsInte: (d) => `<b>did not yet exist</b> (general shoreline protection introduced ${d})`,
    preskription: 'Limitation',
    preskriptionText: (ar, slut, harLopt) =>
      `measure from ${ar} — the ten-year rule expires <b>${slut}</b> `
      + `(${harLopt ? 'has expired' : 'still running'}; shoreline protection never lapses)`,
    regelmodellEjLaddad: 'rule model not loaded',
    rubrikOlovligt: (sista, forsta) => `Erected ${sista}–${forsta} according to orthophotos`,
    rubrikOlovligtRegister: (ar) => `construction year ${ar} in the register`,
    rubrikAvvikelse: (diff, pct) => `${diff} m² (${pct} %) vs approved permit`,
    rubrikStrandskydd: (traffar, totalt) => `${traffar} of ${totalt} buildings touch a protection zone`,
    snedbildRubrik: 'Oblique images',
    snedbildUnder: 'Façades from four directions (MapSpace) — for your own review of height and appearance',
    snedbildLaddar: 'Fetching oblique images…',
    snedbildOppna: 'Open in MapSpace',
    snedbildSaknas: 'No oblique images over this point',
    snedbildFel: 'Oblique images could not be fetched',
    snedbildAlt: (riktning, datum) => `Oblique view facing ${riktning}, ${datum}`,
    riktning: { N: 'North', E: 'East', S: 'South', W: 'West' },
    radarKnapp: 'Scan view',
    radarKnappAria: 'Supervision radar: scan the visible map view for buildings in shoreline protection zones',
    radarRubrik: 'Supervision radar',
    radarUnder: 'Buildings against shoreline protection zones across the whole visible view — same engine, same yardstick for all',
    radarRubrikRad: (traffar, totalt) => `${traffar} candidates of ${totalt} buildings in view`,
    radarLaddar: 'Scanning view…',
    radarIngaKandidater: 'No buildings meet a shoreline protection zone in view.',
    radarFel: 'The scan could not be completed',
    radarTrunkerad: (visade, totalt) => `Showing ${visade} of ${totalt} candidates — zoom in for the rest.`,
    radarPoangmodell: 'How the score is computed',
    radarVisaGrunder: 'Grounds',
    radarPoangEnhet: 'pts',
    radarAr: 'year',
    radarOppnaAria: (rang) => `Open candidate ${rang} on the map and review`,
    radarTillbaka: 'Back to radar list',
    rattighetTyp: {
      'Ledningsrätt': 'Utility easement (ledningsrätt)', 'Officialservitut': 'Official easement (officialservitut)',
      'Avtalsservitut': 'Contractual easement (avtalsservitut)', 'Gemensamhetsanläggning': 'Joint facility (gemensamhetsanläggning)'
    }
  }
};

export const FALT_LABEL = {
  sv: {
    byggnad_id: 'Byggnad', area_m2: 'Area',
    sista_ar_utan: 'Sista år utan byggnad (ortofoto)',
    forsta_ar_med: 'Första år med byggnad (ortofoto)',
    bal_nybyggnadsar: 'Nybyggnadsår (byggnadsregistret)',
    bal_forenligt: 'Förenligt med byggnadsregistret',
    bygglov_kravdes: 'Bygglov krävdes',
    lovbefrielse: 'Lovbefrielse',
    rattelse_preskriberad: 'Rättelse preskriberad (11 kap. 20 § PBL)',
    sanktionsavgift_mojlig: 'Byggsanktionsavgift möjlig (11 kap. 58 § PBL)',
    matningskritiskt: 'Mätningskritiskt',
    matningskritiska: 'Mätningskritiska punkter',
    inom_strandskydd: 'Inom strandskydd',
    poang_per_ar: 'Poäng per år (datering)',
    dnr: 'Diarienummer', beslutsdatum: 'Beslutsdatum',
    pbl_vid_beslut: 'Lag vid beslut', overgangsregel_tillampad: 'Övergångsregel tillämpad',
    godkand_area_m2: 'Godkänd area', verklig_area_m2: 'Verklig area',
    area_diff_m2: 'Areaavvikelse', area_diff_procent: 'Areaavvikelse (%)',
    utanfor_godkant_m2: 'Yta utanför godkänt läge',
    avstand_grans_godkant_m: 'Avstånd till gräns (godkänt läge)',
    avstand_grans_verklig_m: 'Avstånd till gräns (verkligt läge)',
    antal_traffar: 'Antal träffar', antal_byggnader: 'Antal byggnader',
    antal_utanfor: 'Antal utanför', radie_m: 'Sökradie',
    laege: 'Läge', byggnads_ar: 'Byggnadsår',
    dispens_kravs_idag: 'Dispens krävs idag', preskriberas: 'Preskriberas',
    gallde_vid_uppforande: 'Gällde vid uppförande', atgarder: 'Åtgärder',
    zon_referenser: 'Zonreferenser', andel_inom: 'Andel inom zon',
    utvidgat_strandskydd: 'Berör utvidgat strandskydd', upphavt_strandskydd: 'Berör upphävt strandskydd',
    rattigheter: 'Rättigheter och gemensamhetsanläggningar', snedbilder: 'Snedbilder',
    lov_hittat: 'Lov hittat i arkivet',
    traffar_trunkerade_till: 'Träfflistan trunkerad till',
    centroid_forskjutning_m: 'Centroidförskjutning',
    byggnadsarea_m2: 'Byggnadsarea', avstand_grans_m: 'Avstånd till gräns'
  },
  en: {
    byggnad_id: 'Building', area_m2: 'Area',
    sista_ar_utan: 'Last year without building (orthophoto)',
    forsta_ar_med: 'First year with building (orthophoto)',
    bal_nybyggnadsar: 'Construction year (building register)',
    bal_forenligt: 'Consistent with building register',
    bygglov_kravdes: 'Building permit required',
    lovbefrielse: 'Permit exemption',
    rattelse_preskriberad: 'Correction time-barred (ch. 11 §20 PBL)',
    sanktionsavgift_mojlig: 'Building sanction fee possible (ch. 11 §58 PBL)',
    matningskritiskt: 'Measurement-critical',
    matningskritiska: 'Measurement-critical points',
    inom_strandskydd: 'Within shoreline protection',
    poang_per_ar: 'Score per year (dating)',
    dnr: 'Case number', beslutsdatum: 'Decision date',
    pbl_vid_beslut: 'Act in force at decision', overgangsregel_tillampad: 'Transitional rule applied',
    godkand_area_m2: 'Approved area', verklig_area_m2: 'Actual area',
    area_diff_m2: 'Area difference', area_diff_procent: 'Area difference (%)',
    utanfor_godkant_m2: 'Area outside approved position',
    avstand_grans_godkant_m: 'Distance to boundary (approved position)',
    avstand_grans_verklig_m: 'Distance to boundary (actual position)',
    antal_traffar: 'Number of hits', antal_byggnader: 'Number of buildings',
    antal_utanfor: 'Number outside', radie_m: 'Search radius',
    laege: 'Position', byggnads_ar: 'Construction year',
    dispens_kravs_idag: 'Dispensation required today', preskriberas: 'Time-barred',
    gallde_vid_uppforande: 'In force at construction', atgarder: 'Measures',
    zon_referenser: 'Zone references', andel_inom: 'Share within zone',
    utvidgat_strandskydd: 'Touches extended shoreline protection', upphavt_strandskydd: 'Touches revoked shoreline protection',
    rattigheter: 'Easements and joint facilities', snedbilder: 'Oblique images',
    lov_hittat: 'Permit found in archive',
    traffar_trunkerade_till: 'Hit list truncated to',
    centroid_forskjutning_m: 'Centroid displacement',
    byggnadsarea_m2: 'Building area', avstand_grans_m: 'Distance to boundary'
  }
};

export function faltLabel(key, sprak) {
  const map = FALT_LABEL[sprak] || FALT_LABEL.sv;
  return map[key] || key;
}

export function formatTal(n, sprak) {
  const rundat = Math.round(n * 10) / 10;
  const s = String(rundat);
  return sprak === 'sv' ? s.replace('.', ',') : s;
}

export function teckenTal(n, sprak) {
  return (n > 0 ? '+' : '') + formatTal(n, sprak);
}

/* --- värden som är uppräkningar, inte fritext --- */

// Backend skickar ZonAnalys.laege och korsjamforelse-utfallen som stabila
// koder; de är API-värden och översätts därför här, inte i Python.
export const VARDE_LABEL = {
  sv: {
    laege: { inom: 'Inom zon', delvis: 'Delvis inom zon', utanfor: 'Utanför zon' },
    korsjamforelse: { överens: 'Överens', avviker: 'Avviker', saknas: 'Saknas i handlingen' }
  },
  en: {
    laege: { inom: 'Inside zone', delvis: 'Partly inside zone', utanfor: 'Outside zone' },
    korsjamforelse: {
      överens: 'Matches', avviker: 'Differs', saknas: 'Missing from the document'
    }
  }
};

export function vardeLabel(falt, varde, sprak) {
  const map = (VARDE_LABEL[sprak] || VARDE_LABEL.sv)[falt];
  return (map && map[varde]) || varde;
}

/* --- backendens meddelanden (osäkerheter, åtgärder, fel, källbeskrivningar) --- */

// Tal formaterade med fast antal decimaler; sv använder komma som decimaltecken.
function tal(n, decimaler, sprak) {
  const s = Number(n).toFixed(decimaler);
  return sprak === 'sv' ? s.replace('.', ',') : s;
}

function teckenFast(n, decimaler, sprak) {
  return (Number(n) > 0 ? '+' : '') + tal(n, decimaler, sprak);
}

const arLista = (ar) => (Array.isArray(ar) ? ar : []).join(', ');

export const MEDDELANDEN = {
  sv: {
    'datering.argangar_utan_bild': (p) =>
      `Årgångar utan användbar bild (hoppade över): ${arLista(p.ar)}.`,
    'datering.for_fa_argangar': (p) =>
      'Datering ej fastställd: för få användbara ortofoto-årgångar '
      + `(${p.antal} st, minst ${p.minst} krävs).`,
    'datering.footprint_utan_pixlar': () =>
      'Datering ej fastställd: byggnadens footprint täcker inga pixlar i bilden.',
    'datering.argangar_utan_innehall': (p) =>
      'Årgångar utan bildinnehåll i byggnadens footprint (uteslutna): '
      + `${arLista(p.ar)}.`,
    'datering.otydliga_argangar': (p) =>
      'Otydliga årgångar (varken klar närvaro eller frånvaro): '
      + `${arLista(p.ar)} — manuell granskning rekommenderas.`,
    'datering.ingen_bortom_referensar': () =>
      'Datering ej fastställd: byggnaden kan inte beläggas i någon årgång '
      + 'utöver referensåret (självmatchning räknas inte som bevis).',
    'datering.syns_i_aldsta': (p) =>
      `Byggnaden syns redan i äldsta användbara ortofotot (${p.ar}) `
      + '— ingen undre gräns kan sättas från bildserien.',

    'juridik.tillkomstar_ej_faststallt_bal': () =>
      'Byggnadens tillkomstår är inte fastställt (bal_nybyggnadsar saknas) — '
      + 'datera via ortofoto-tidslinjen innan regelverket vid uppförandet kan avgöras.',
    'juridik.byggnadsar_ar_ikrafttradandear': (p) =>
      `Byggnadsåret ${p.ar} är ikraftträdandeår för strandskyddet `
      + `(${p.generellt_fran}) — månad krävs för att avgöra `
      + 'vilket regelverk som gällde vid uppförandet.',
    'juridik.klocka_20_osaker': () =>
      'PBL 11 kap. 20 §-klockan (10 år) löper ut någonstans inom '
      + 'dateringsintervallet — konstruktionsåret måste pinpointas för att avgöra '
      + 'om rättelse är preskriberad.',
    'juridik.klocka_58_osaker': () =>
      'PBL 11 kap. 58 §-klockan (5 år) löper ut någonstans inom '
      + 'dateringsintervallet — konstruktionsåret måste pinpointas för att avgöra '
      + 'om sanktionsavgift fortfarande är möjlig.',
    'juridik.strandskydd_preskriberas_aldrig': () =>
      'Strandskyddstillsyn preskriberas aldrig enligt PBL-klockorna (MÖD 2021:6) '
      + '— se Fall 7-analysen för strandskyddsdelen.',
    'juridik.tillkomstar_ej_faststallt': () =>
      'Byggnadens tillkomstår är inte fastställt — datera via ortofoto-tidslinjen '
      + 'innan bygglovsplikt och preskription kan avgöras.',
    'juridik.undre_grans_okand': () =>
      'Nedre gränsen för uppförandeåret är okänd (sista_ar_utan saknas) — '
      + 'intervallets start kan inte fastställas från ortofoto-tidslinjen.',
    'juridik.regelandring_i_intervallet': () =>
      'Intervallet för uppförandeåret spänner över en regeländring i '
      + 'bygglovsbefrielserna — konstruktionsåret måste pinpointas innan '
      + 'bygglovsplikten kan avgöras.',
    'juridik.matningskritisk_area': () =>
      'Bedömningen är mätningskritisk — arean ligger nära en tröskel och måste '
      + 'verifieras genom mätning innan handläggaren lägger fast slutsatsen.',
    'juridik.fardigstallande_ej_daterat': () =>
      'Färdigställandet är inte daterat — datera via ortofoto-tidslinjen '
      + 'innan preskriptionsklockorna kan avgöras.',
    'juridik.matningskritisk_areaavvikelse': (p, s) =>
      `Areaavvikelsen (${teckenFast(p.diff_m2, 1, s)} m²) ligger inom `
      + `mätosäkerheten (±${tal(p.band_m2, 0, s)} m²) — kan inte beläggas utan inmätning.`,
    'juridik.matningskritisk_avstand': (p, s) =>
      'Skillnaden i avstånd till fastighetsgräns ligger inom mätosäkerheten '
      + `(±${tal(p.band_m, 1, s)} m) — kan inte beläggas utan inmätning.`,
    'juridik.matningskritisk_bedomning': () =>
      'Bedömningen är mätningskritisk — avvikelser inom mätosäkerheten måste '
      + 'verifieras genom inmätning innan handläggaren lägger fast slutsatsen.',

    'regelverk.ange_startdatum': () =>
      'Ange ärendets startdatum — datum ensamt avgör inte vilken lag som gäller.',

    'delta.godkant_utan_yta': () =>
      'Godkänt läge har ingen mätbar yta — procentjämförelse ej möjlig.',
    'delta.ingen_fastighetsgrans': () =>
      'Ingen fastighetsgräns tillgänglig — avstånd till gräns har inte '
      + 'kunnat jämföras.',

    'lovtolk.ocr_ej_tillganglig': (p) =>
      `OCR ej tillgänglig — handlingen kunde inte läsas (${p.feltyp}).`,
    'lovtolk.lag_konfidens': (p, s) =>
      `OCR-konfidensen är låg (${tal(p.konfidens, 2, s)}) — extraherade fält bör `
      + 'kontrolleras mot handlingen manuellt.',

    'runner.regellager_otillgangligt': (p) =>
      `${p.lager} kunde inte hämtas (källan otillgänglig); `
      + 'zonens exakta utbredning är inte fullständigt kontrollerad.',
    'runner.dispenser_ej_kontrollerade': () =>
      'Beviljade strandskyddsdispenser har inte kontrollerats mot dispensregistret.',
    'runner.juridisk_not': () =>
      'Ingen preskription för strandskyddstillsyn (MÖD 2021:6); '
      + 'skälighetsbedömning enligt MÖD 2017:16 är handläggarens. '
      + 'Systemet gör en bedömning — beslutet fattas av handläggaren.',
    'runner.bygglovsregister_saknas': () =>
      'Bygglovsregistret är inte tillgängligt i prototypfasen (Sokigo Nova kräver '
      + 'TRIP-avtal) — ingen lovprövning har kunnat kontrolleras mot register; '
      + 'kommunens testärenden används.',
    'runner.strandskyddslager_otillgangligt': (p) =>
      `${p.lager} kunde inte hämtas (källan otillgänglig) — `
      + 'strandskyddsläget har inte kunnat kontrolleras.',
    'runner.granslager_otillgangligt': (p) =>
      `${p.lager} kunde inte hämtas (källan otillgänglig) — `
      + 'avstånd till fastighetsgräns har inte kunnat kontrolleras.',
    'runner.lov_byggnad_koppling_osaker': (p, s) =>
      'Kopplingen lov–byggnad är inte säkerställd: det godkända läget ligger '
      + `${tal(p.avstand_m, 0, s)} m från den valda byggnaden — kontrollera att ärendet `
      + 'avser denna byggnad.',
    'runner.ingen_skannad_handling': () =>
      'Ingen skannad handling i ärendet — korskontroll ej möjlig.',
    'runner.lovarkiv_syntetiskt': () =>
      'Lovuppgifterna kommer ur ett SYNTETISKT testarkiv (mock-ByggR) — '
      + 'prototypfasen har ingen åtkomst till kommunens ärendesystem.',
    'runner.hojd_ej_kontrollerbar': () =>
      'Byggnadens höjd och utseende kan inte kontrolleras mot lovet — flygbilder '
      + 'ser inte fasader (snedbilder saknas i prototypfasen).',
    'runner.ingen_byggnad_hittad': (p, s) =>
      `Ingen byggnad hittades inom ${tal(p.radie_m, 0, s)} m från punkten `
      + `E ${tal(p.easting, 0, s)}, N ${tal(p.northing, 0, s)}.`,
    'runner.inget_lov_i_arkivet': () =>
      'Inget ärende i (test)arkivet för punkten — se Fall 1-analysen för lovplikt.',
    'runner.inget_arende_matchar': (p, s) =>
      'Inget (test)ärende i lovarkivet matchar punkten '
      + `E ${tal(p.easting, 0, s)}, N ${tal(p.northing, 0, s)} — `
      + 'se Fall 1-analysen för lovplikt.',

    'runner.upphavt_strandskydd_konflikt': (p) =>
      `Byggnad ${p.byggnad_id} berör även område med upphävt strandskydd (${p.referens}) `
      + '— zonens aktuella utbredning måste kontrolleras mot Länsstyrelsens beslut.',
    'runner.rattighetslager_otillgangligt': (p) =>
      `${p.lager} kunde inte hämtas (källan otillgänglig) — `
      + 'rättigheter och gemensamhetsanläggningar har inte kunnat kontrolleras.',
    'runner.hojd_granska_snedbilder': (p) =>
      'Byggnadens höjd och utseende kan inte mätas automatiskt — granska '
      + `snedbilderna (${arLista(p.ar)}) manuellt mot lovet.`,
    'runner.snedbilder_otillgangliga': () =>
      'Snedbilder kunde inte hämtas (MapSpace otillgänglig eller ingen täckning) — '
      + 'höjd och utseende har inte kunnat granskas.',

    'geodata.snapshot_anvant': (p) =>
      `${p.lager} hämtades ur en lokal ögonblicksbild från ${p.hamtad} — inte live `
      + 'från kommunens GeoServer; kontrollera mot tjänsten vid beslut.',
    'geodata.cache_anvant': (p) =>
      `${p.lager} kunde inte hämtas live; ett tidigare svar från ${p.hamtad} användes `
      + 'i stället — kontrollera mot tjänsten vid beslut.',

    'kalla.ortofoto_tidslinje': () => 'Ortofoto-tidslinje 1960–2023 (WMS)',
    'kalla.snedbilder_mapspace': () => 'Snedbilder (MapSpace, Sundsvalls kommun)',
    'kalla.lovarkiv_syntetiskt': (p) => `Lovarkiv (syntetiskt), ärende ${p.dnr}`,
    'kalla.skannad_handling': (p) => `Skannad handling, ärende ${p.dnr}`,
    'kalla.pbl_lovbefrielser_preskription': () =>
      'PBL lovbefrielser + preskription (SFS 2010:900)',
    'kalla.pbl_lovbefrielser_regelverk_vid': () =>
      'PBL lovbefrielser + preskription (regelverk_vid)',
    'kalla.pbl_apbl_overgang': () =>
      'PBL/ÄPBL övergångsbestämmelser (SFS 2010:900 p. 2)',
    'kalla.pbl_apbl_overgang_regelverk_vid': () =>
      'PBL/ÄPBL övergångsbestämmelser + preskription (regelverk_vid)',

    'radar.poang_inom': () => 'Byggnaden ligger helt inom strandskyddszon (+3).',
    'radar.poang_delvis': (p) =>
      `Byggnaden ligger delvis inom strandskyddszon (${Math.round(p.andel * 100)} %) (+2).`,
    'radar.poang_gallde_vid_uppforande': (p) =>
      `Strandskyddet gällde redan när byggnaden uppfördes (${p.ar}) — dispensplikt vid uppförandet (+3).`,
    'radar.poang_fore_strandskydd': (p) =>
      `Uppförd ${p.ar}, innan strandskyddet gällde på platsen — ingen dispensplikt vid uppförandet (+0).`,
    'radar.poang_ar_okant': () =>
      'Tillkomstår ej fastställt i registret — kan inte uteslutas; datera via ortofoto-tidslinjen (+1).',
    'radar.poang_ar_ikrafttradandear': (p) =>
      `Uppförd ikraftträdandeåret ${p.ar} — månad krävs för att avgöra regimen (+1).`,
    'radar.poang_utvidgat': () => 'Berör även utvidgat strandskydd enligt Länsstyrelsen (+1).',
    'radar.kallkonflikt_upphavt': (p) =>
      `Berör upphävt strandskydd (${p.referens}) — källkonflikt mot kommunens zonlager; granska innan åtgärd (±0).`,
    'radar.modell_lage': () => 'Läge: helt inom zon +3, delvis inom +2, utanför = ingen kandidat.',
    'radar.modell_regim': () =>
      'Regim vid uppförandet: strandskyddet gällde redan +3, gällde inte +0, ikraftträdandeår +1 (månad saknas).',
    'radar.modell_ar_okant': () => 'Tillkomstår okänt i registret +1 — aldrig uteslutet, aldrig högst.',
    'radar.modell_utvidgat': () =>
      'Utvidgat strandskydd (Länsstyrelsen) +1; upphävt strandskydd ger ingen poäng men flaggas som källkonflikt.',
    'radar.juridisk_not': () =>
      'Listan är kandidater för granskning, rangordnade efter hur tydligt byggnad och strandskyddszon sammanfaller över tid — inte beslut och inte påståenden om överträdelse. Dispenser är inte kontrollerade. Systematisk skanning ger samma måttstock för alla; handläggaren beslutar, alltid.',
    'radar.fastighetslager_otillgangligt': (p) =>
      `Fastighetslagret ${p.lager} kunde inte hämtas — kandidater redovisas utan fastighetsbeteckning.`,
    'radar.zon_for_stor': (p) =>
      `Zonen är ${tal(p.area_km2, 1, 'sv')} km² — radarn skannar högst ${tal(p.max_km2, 1, 'sv')} km² åt gången; zooma in eller dela upp.`,
    'server.parametrar_ogiltiga': (p) =>
      `easting/northing saknas eller kunde inte tolkas: ${p.detalj}`,
    'server.bbox_ogiltig': (p) =>
      `bbox saknas eller kunde inte tolkas (minE,minN,maxE,maxN i EPSG:3014): ${p.detalj}`,
    'server.internt_fel': () => 'internt fel'
  },

  en: {
    'datering.argangar_utan_bild': (p) =>
      `Vintages without a usable image (skipped): ${arLista(p.ar)}.`,
    'datering.for_fa_argangar': (p) =>
      'Dating not established: too few usable orthophoto vintages '
      + `(${p.antal}, at least ${p.minst} required).`,
    'datering.footprint_utan_pixlar': () =>
      "Dating not established: the building's footprint covers no pixels in the image.",
    'datering.argangar_utan_innehall': (p) =>
      "Vintages with no image content inside the building's footprint (excluded): "
      + `${arLista(p.ar)}.`,
    'datering.otydliga_argangar': (p) =>
      'Ambiguous vintages (neither clear presence nor clear absence): '
      + `${arLista(p.ar)} — manual review recommended.`,
    'datering.ingen_bortom_referensar': () =>
      'Dating not established: the building cannot be evidenced in any vintage '
      + 'beyond the reference year (a self-match does not count as evidence).',
    'datering.syns_i_aldsta': (p) =>
      `The building is already visible in the oldest usable orthophoto (${p.ar}) `
      + '— no lower bound can be set from the image series.',

    'juridik.tillkomstar_ej_faststallt_bal': () =>
      "The building's year of origin is not established (bal_nybyggnadsar is missing) — "
      + 'date it via the orthophoto timeline before the rules in force at construction '
      + 'can be determined.',
    'juridik.byggnadsar_ar_ikrafttradandear': (p) =>
      `The construction year ${p.ar} is the year the shoreline protection entered into `
      + `force (${p.generellt_fran}) — the month is required to determine which rules `
      + 'applied at construction.',
    'juridik.klocka_20_osaker': () =>
      'The PBL ch. 11 §20 clock (10 years) expires somewhere inside the dating '
      + 'interval — the construction year must be pinpointed to determine whether '
      + 'correction is time-barred.',
    'juridik.klocka_58_osaker': () =>
      'The PBL ch. 11 §58 clock (5 years) expires somewhere inside the dating '
      + 'interval — the construction year must be pinpointed to determine whether '
      + 'a sanction fee is still possible.',
    'juridik.strandskydd_preskriberas_aldrig': () =>
      'Shoreline protection enforcement never lapses under the PBL clocks (MÖD 2021:6) '
      + '— see the Case 7 analysis for the shoreline protection part.',
    'juridik.tillkomstar_ej_faststallt': () =>
      "The building's year of origin is not established — date it via the orthophoto "
      + 'timeline before permit liability and limitation can be determined.',
    'juridik.undre_grans_okand': () =>
      'The lower bound of the construction year is unknown (sista_ar_utan is missing) — '
      + 'the start of the interval cannot be established from the orthophoto timeline.',
    'juridik.regelandring_i_intervallet': () =>
      'The construction-year interval spans a rule change in the permit exemptions — '
      + 'the construction year must be pinpointed before permit liability can be '
      + 'determined.',
    'juridik.matningskritisk_area': () =>
      'The assessment is measurement-critical — the area lies close to a threshold and '
      + 'must be verified by measurement before the caseworker settles the conclusion.',
    'juridik.fardigstallande_ej_daterat': () =>
      'Completion is not dated — date it via the orthophoto timeline before the '
      + 'limitation clocks can be determined.',
    'juridik.matningskritisk_areaavvikelse': (p, s) =>
      `The area deviation (${teckenFast(p.diff_m2, 1, s)} m²) lies within the `
      + `measurement uncertainty (±${tal(p.band_m2, 0, s)} m²) — it cannot be evidenced `
      + 'without a survey.',
    'juridik.matningskritisk_avstand': (p, s) =>
      'The difference in distance to the property boundary lies within the measurement '
      + `uncertainty (±${tal(p.band_m, 1, s)} m) — it cannot be evidenced without a survey.`,
    'juridik.matningskritisk_bedomning': () =>
      'The assessment is measurement-critical — deviations within the measurement '
      + 'uncertainty must be verified by survey before the caseworker settles the '
      + 'conclusion.',

    'regelverk.ange_startdatum': () =>
      "State the case's start date — the date alone does not determine which act applies.",

    'delta.godkant_utan_yta': () =>
      'The approved position has no measurable area — a percentage comparison is not '
      + 'possible.',
    'delta.ingen_fastighetsgrans': () =>
      'No property boundary available — distance to the boundary could not be compared.',

    'lovtolk.ocr_ej_tillganglig': (p) =>
      `OCR unavailable — the document could not be read (${p.feltyp}).`,
    'lovtolk.lag_konfidens': (p, s) =>
      `OCR confidence is low (${tal(p.konfidens, 2, s)}) — the extracted fields should `
      + 'be checked against the document manually.',

    'runner.regellager_otillgangligt': (p) =>
      `${p.lager} could not be fetched (source unavailable); the exact extent of the `
      + 'zone is not fully verified.',
    'runner.dispenser_ej_kontrollerade': () =>
      'Granted shoreline protection dispensations have not been checked against the '
      + 'dispensation register.',
    'runner.juridisk_not': () =>
      'Shoreline protection enforcement is never time-barred (MÖD 2021:6); the '
      + "reasonableness assessment under MÖD 2017:16 is the caseworker's. The system "
      + 'makes an assessment — the decision is taken by the caseworker.',
    'runner.bygglovsregister_saknas': () =>
      'The building permit register is not available in the prototype phase (Sokigo '
      + 'Nova requires a TRIP agreement) — no permit review could be checked against a '
      + "register; the municipality's test cases are used.",
    'runner.strandskyddslager_otillgangligt': (p) =>
      `${p.lager} could not be fetched (source unavailable) — the shoreline protection `
      + 'status could not be verified.',
    'runner.granslager_otillgangligt': (p) =>
      `${p.lager} could not be fetched (source unavailable) — the distance to the `
      + 'property boundary could not be verified.',
    'runner.lov_byggnad_koppling_osaker': (p, s) =>
      'The permit–building link is not confirmed: the approved position lies '
      + `${tal(p.avstand_m, 0, s)} m from the selected building — check that the case `
      + 'concerns this building.',
    'runner.ingen_skannad_handling': () =>
      'No scanned document in the case — a cross-check is not possible.',
    'runner.lovarkiv_syntetiskt': () =>
      'The permit data comes from a SYNTHETIC test archive (mock-ByggR) — the prototype '
      + "phase has no access to the municipality's case system.",
    'runner.hojd_ej_kontrollerbar': () =>
      "The building's height and appearance cannot be checked against the permit — "
      + 'aerial imagery does not see façades (oblique imagery is absent in the prototype '
      + 'phase).',
    'runner.ingen_byggnad_hittad': (p, s) =>
      `No building was found within ${tal(p.radie_m, 0, s)} m of the point `
      + `E ${tal(p.easting, 0, s)}, N ${tal(p.northing, 0, s)}.`,
    'runner.inget_lov_i_arkivet': () =>
      'No case in the (test) archive for this point — see the Case 1 analysis for '
      + 'permit liability.',
    'runner.inget_arende_matchar': (p, s) =>
      'No (test) case in the permit archive matches the point '
      + `E ${tal(p.easting, 0, s)}, N ${tal(p.northing, 0, s)} — see the Case 1 analysis `
      + 'for permit liability.',

    'runner.upphavt_strandskydd_konflikt': (p) =>
      `Building ${p.byggnad_id} also touches an area where shoreline protection was `
      + `revoked (${p.referens}) — the current extent of the zone must be checked against `
      + "the County Administrative Board's decision.",
    'runner.rattighetslager_otillgangligt': (p) =>
      `${p.lager} could not be fetched (source unavailable) — easements and joint `
      + 'facilities could not be checked.',
    'runner.hojd_granska_snedbilder': (p) =>
      "The building's height and appearance cannot be measured automatically — review "
      + `the oblique images (${arLista(p.ar)}) manually against the permit.`,
    'runner.snedbilder_otillgangliga': () =>
      'Oblique images could not be fetched (MapSpace unavailable or no coverage) — '
      + 'height and appearance could not be reviewed.',

    'geodata.snapshot_anvant': (p) =>
      `${p.lager} was read from a local snapshot taken ${p.hamtad} — not live from the `
      + "municipality's GeoServer; verify against the service before deciding.",
    'geodata.cache_anvant': (p) =>
      `${p.lager} could not be fetched live; an earlier response from ${p.hamtad} was `
      + 'used instead — verify against the service before deciding.',

    'kalla.ortofoto_tidslinje': () => 'Orthophoto timeline 1960–2023 (WMS)',
    'kalla.snedbilder_mapspace': () => 'Oblique imagery (MapSpace, Sundsvall municipality)',
    'kalla.lovarkiv_syntetiskt': (p) => `Permit archive (synthetic), case ${p.dnr}`,
    'kalla.skannad_handling': (p) => `Scanned document, case ${p.dnr}`,
    'kalla.pbl_lovbefrielser_preskription': () =>
      'PBL permit exemptions + limitation (SFS 2010:900)',
    'kalla.pbl_lovbefrielser_regelverk_vid': () =>
      'PBL permit exemptions + limitation (regelverk_vid)',
    'kalla.pbl_apbl_overgang': () =>
      'PBL/ÄPBL transitional provisions (SFS 2010:900 p. 2)',
    'kalla.pbl_apbl_overgang_regelverk_vid': () =>
      'PBL/ÄPBL transitional provisions + limitation (regelverk_vid)',

    'radar.poang_inom': () => 'The building lies entirely within a shoreline protection zone (+3).',
    'radar.poang_delvis': (p) =>
      `The building lies partly within a shoreline protection zone (${Math.round(p.andel * 100)} %) (+2).`,
    'radar.poang_gallde_vid_uppforande': (p) =>
      `Shoreline protection already applied when the building was erected (${p.ar}) — exemption was required at construction (+3).`,
    'radar.poang_fore_strandskydd': (p) =>
      `Erected ${p.ar}, before shoreline protection applied at the site — no exemption required at construction (+0).`,
    'radar.poang_ar_okant': () =>
      'Year of construction not established in the register — cannot be ruled out; date it via the orthophoto timeline (+1).',
    'radar.poang_ar_ikrafttradandear': (p) =>
      `Erected in the year of entry into force ${p.ar} — the month is needed to decide the regime (+1).`,
    'radar.poang_utvidgat': () => 'Also touches extended shoreline protection per the County Administrative Board (+1).',
    'radar.kallkonflikt_upphavt': (p) =>
      `Touches revoked shoreline protection (${p.referens}) — source conflict with the municipal zone layer; review before acting (±0).`,
    'radar.modell_lage': () => 'Position: entirely within zone +3, partly within +2, outside = not a candidate.',
    'radar.modell_regim': () =>
      'Regime at construction: protection already applied +3, did not apply +0, year of entry into force +1 (month missing).',
    'radar.modell_ar_okant': () => 'Year of construction unknown in the register +1 — never excluded, never top-ranked.',
    'radar.modell_utvidgat': () =>
      'Extended shoreline protection (County Administrative Board) +1; revoked protection scores nothing but is flagged as a source conflict.',
    'radar.juridisk_not': () =>
      'The list holds candidates for review, ranked by how clearly building and shoreline protection zone coincide over time — not decisions and not claims of violation. Exemptions are not checked. Systematic scanning applies the same yardstick to everyone; the case officer always decides.',
    'radar.fastighetslager_otillgangligt': (p) =>
      `The property layer ${p.lager} could not be fetched — candidates are listed without property designation.`,
    'radar.zon_for_stor': (p) =>
      `The zone is ${tal(p.area_km2, 1, 'en')} km² — the radar scans at most ${tal(p.max_km2, 1, 'en')} km² at a time; zoom in or split it.`,
    'server.parametrar_ogiltiga': (p) =>
      `easting/northing is missing or could not be parsed: ${p.detalj}`,
    'server.bbox_ogiltig': (p) =>
      `bbox missing or unparseable (minE,minN,maxE,maxN in EPSG:3014): ${p.detalj}`,
    'server.internt_fel': () => 'internal error'
  }
};

/**
 * Rendera ett backend-meddelande på valt språk.
 *
 * Tar emot antingen `{kod, params}` (översätts) eller en ren sträng (ordagrann
 * text: författningsnamn, WFS-lagernamn, diarienummer — står kvar som den är).
 * En okänd kod faller tillbaka på svenskan, och därefter på koden själv: ett
 * oöversatt förbehåll är alltid bättre än ett tappat.
 */
export function meddelandeText(varde, sprak) {
  if (varde === null || varde === undefined) return '';
  if (typeof varde === 'string') return varde;
  if (typeof varde !== 'object' || typeof varde.kod !== 'string') return String(varde);

  const params = varde.params || {};
  const mall = (MEDDELANDEN[sprak] || {})[varde.kod] || MEDDELANDEN.sv[varde.kod];
  if (!mall) return varde.kod;
  return mall(params, sprak);
}

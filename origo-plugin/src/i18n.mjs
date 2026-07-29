/**
 * i18n för Geo-Tillsyn-pluginet: UI-chrome på sv/en.
 *
 * Endast våra egna etiketter översätts — författningsnamn ur regler.json
 * (SFS-titlar, "friggebod", lagrum) är officiella svenska termer och står
 * kvar ordagrant på båda språken.
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
    rubrikStrandskydd: (traffar, totalt) => `${traffar} av ${totalt} byggnader berör strandskyddszon`
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
    rubrikStrandskydd: (traffar, totalt) => `${traffar} of ${totalt} buildings touch a protection zone`
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
    lov_hittat: 'Lov hittat i arkivet'
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
    lov_hittat: 'Permit found in archive'
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

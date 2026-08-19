"""Meddelandekoder: en sträng som också bär sin i18n-kod och sina parametrar.

Bakgrunden: analysmotorn formulerade tidigare färdiga svenska meningar, vilket
gjorde dem omöjliga att översätta i Origo-pluginets SV/EN-växel — panelen kunde
bara byta språk på sina egna etiketter, medan varje osäkerhet, åtgärd och
felmeddelande förblev svenskt.

`Meddelande` är därför en `str`-subklass: den ÄR sin svenska text (markdown-
dossiern, CLI:t och testerna ser ingen skillnad) men bär samtidigt `kod` och
`params`, så att `till_json` kan serialisera den som `{"kod", "params"}` och
klienten rendera den på valfritt språk ur samma katalog.

Svenskan här är normativ: den svenska katalogen nedan och `MEDDELANDEN.sv` i
origo-plugin/src/i18n.mjs måste hållas ordagrant lika. Författningsnamn
(SFS-titlar, lagrum, "friggebod") och tekniska identifierare (WFS-lagernamn,
fältnamn som `bal_nybyggnadsar`) står kvar ordagrant på båda språken.

SPDX-License-Identifier: AGPL-3.0-or-later
"""

from __future__ import annotations

from typing import Any, Callable


def _ar_lista(ar: list[int]) -> str:
    return ", ".join(str(a) for a in ar)


# Svensk katalog. Nyckeln är meddelandekoden som går på tråden; värdet en
# funktion av de parametrar koden deklarerar. Håll synkad med i18n.mjs.
_SV: dict[str, Callable[..., str]] = {
    # --- datering.py: ortofoto-dateringens anmärkningar ---
    "datering.argangar_utan_bild": lambda ar: (
        f"Årgångar utan användbar bild (hoppade över): {_ar_lista(ar)}."
    ),
    "datering.for_fa_argangar": lambda antal, minst: (
        "Datering ej fastställd: för få användbara ortofoto-årgångar "
        f"({antal} st, minst {minst} krävs)."
    ),
    "datering.footprint_utan_pixlar": lambda: (
        "Datering ej fastställd: byggnadens footprint täcker inga pixlar i bilden."
    ),
    "datering.argangar_utan_innehall": lambda ar: (
        "Årgångar utan bildinnehåll i byggnadens footprint (uteslutna): "
        f"{_ar_lista(ar)}."
    ),
    "datering.otydliga_argangar": lambda ar: (
        "Otydliga årgångar (varken klar närvaro eller frånvaro): "
        f"{_ar_lista(ar)} — manuell granskning rekommenderas."
    ),
    "datering.ingen_bortom_referensar": lambda: (
        "Datering ej fastställd: byggnaden kan inte beläggas i någon årgång "
        "utöver referensåret (självmatchning räknas inte som bevis)."
    ),
    "datering.syns_i_aldsta": lambda ar: (
        f"Byggnaden syns redan i äldsta användbara ortofotot ({ar}) "
        "— ingen undre gräns kan sättas från bildserien."
    ),
    # --- juridik.py: tidsmedveten rättslig bedömning ---
    "juridik.tillkomstar_ej_faststallt_bal": lambda: (
        "Byggnadens tillkomstår är inte fastställt (bal_nybyggnadsar saknas) — "
        "datera via ortofoto-tidslinjen innan regelverket vid uppförandet kan avgöras."
    ),
    "juridik.byggnadsar_ar_ikrafttradandear": lambda ar, generellt_fran: (
        f"Byggnadsåret {ar} är ikraftträdandeår för strandskyddet "
        f"({generellt_fran}) — månad krävs för att avgöra "
        "vilket regelverk som gällde vid uppförandet."
    ),
    "juridik.klocka_20_osaker": lambda: (
        "PBL 11 kap. 20 §-klockan (10 år) löper ut någonstans inom "
        "dateringsintervallet — konstruktionsåret måste pinpointas för att avgöra "
        "om rättelse är preskriberad."
    ),
    "juridik.klocka_58_osaker": lambda: (
        "PBL 11 kap. 58 §-klockan (5 år) löper ut någonstans inom "
        "dateringsintervallet — konstruktionsåret måste pinpointas för att avgöra "
        "om sanktionsavgift fortfarande är möjlig."
    ),
    "juridik.strandskydd_preskriberas_aldrig": lambda: (
        "Strandskyddstillsyn preskriberas aldrig enligt PBL-klockorna (MÖD 2021:6) "
        "— se Fall 7-analysen för strandskyddsdelen."
    ),
    "juridik.tillkomstar_ej_faststallt": lambda: (
        "Byggnadens tillkomstår är inte fastställt — datera via ortofoto-tidslinjen "
        "innan bygglovsplikt och preskription kan avgöras."
    ),
    "juridik.undre_grans_okand": lambda: (
        "Nedre gränsen för uppförandeåret är okänd (sista_ar_utan saknas) — "
        "intervallets start kan inte fastställas från ortofoto-tidslinjen."
    ),
    "juridik.regelandring_i_intervallet": lambda: (
        "Intervallet för uppförandeåret spänner över en regeländring i "
        "bygglovsbefrielserna — konstruktionsåret måste pinpointas innan "
        "bygglovsplikten kan avgöras."
    ),
    "juridik.matningskritisk_area": lambda: (
        "Bedömningen är mätningskritisk — arean ligger nära en tröskel och måste "
        "verifieras genom mätning innan handläggaren lägger fast slutsatsen."
    ),
    "juridik.fardigstallande_ej_daterat": lambda: (
        "Färdigställandet är inte daterat — datera via ortofoto-tidslinjen "
        "innan preskriptionsklockorna kan avgöras."
    ),
    "juridik.matningskritisk_areaavvikelse": lambda diff_m2, band_m2: (
        f"Areaavvikelsen ({diff_m2:+.1f} m²) ligger inom "
        f"mätosäkerheten (±{band_m2:.0f} m²) — kan inte beläggas utan inmätning."
    ),
    "juridik.matningskritisk_avstand": lambda band_m: (
        "Skillnaden i avstånd till fastighetsgräns ligger inom mätosäkerheten "
        f"(±{band_m:.1f} m) — kan inte beläggas utan inmätning."
    ),
    "juridik.matningskritisk_bedomning": lambda: (
        "Bedömningen är mätningskritisk — avvikelser inom mätosäkerheten måste "
        "verifieras genom inmätning innan handläggaren lägger fast slutsatsen."
    ),
    # --- regelverk_core.py: åtgärder som kommer ur regelmodellen (regler.json) ---
    "regelverk.ange_startdatum": lambda: (
        "Ange ärendets startdatum — datum ensamt avgör inte vilken lag som gäller."
    ),
    # --- delta.py: kvantifierad avvikelse ---
    "delta.godkant_utan_yta": lambda: (
        "Godkänt läge har ingen mätbar yta — procentjämförelse ej möjlig."
    ),
    "delta.ingen_fastighetsgrans": lambda: (
        "Ingen fastighetsgräns tillgänglig — avstånd till gräns har inte "
        "kunnat jämföras."
    ),
    # --- lovtolk.py: OCR av skannad handling ---
    "lovtolk.ocr_ej_tillganglig": lambda feltyp: (
        "OCR ej tillgänglig — handlingen kunde inte läsas "
        f"({feltyp})."
    ),
    "lovtolk.lag_konfidens": lambda konfidens: (
        f"OCR-konfidensen är låg ({konfidens:.2f}) — extraherade fält bör "
        "kontrolleras mot handlingen manuellt."
    ),
    # --- runner.py: hämtning, prototypförbehåll och ärliga "hittades inte" ---
    "runner.regellager_otillgangligt": lambda lager: (
        f"{lager} kunde inte hämtas (källan otillgänglig); "
        "zonens exakta utbredning är inte fullständigt kontrollerad."
    ),
    "runner.dispenser_ej_kontrollerade": lambda: (
        "Beviljade strandskyddsdispenser har inte kontrollerats mot dispensregistret."
    ),
    "runner.juridisk_not": lambda: (
        "Ingen preskription för strandskyddstillsyn (MÖD 2021:6); "
        "skälighetsbedömning enligt MÖD 2017:16 är handläggarens. "
        "Systemet gör en bedömning — beslutet fattas av handläggaren."
    ),
    "runner.bygglovsregister_saknas": lambda: (
        "Bygglovsregistret är inte tillgängligt i prototypfasen (Sokigo Nova kräver "
        "TRIP-avtal) — ingen lovprövning har kunnat kontrolleras mot register; "
        "kommunens testärenden används."
    ),
    "runner.strandskyddslager_otillgangligt": lambda lager: (
        f"{lager} kunde inte hämtas (källan otillgänglig) — "
        "strandskyddsläget har inte kunnat kontrolleras."
    ),
    "runner.granslager_otillgangligt": lambda lager: (
        f"{lager} kunde inte hämtas (källan otillgänglig) — "
        "avstånd till fastighetsgräns har inte kunnat kontrolleras."
    ),
    "runner.lov_byggnad_koppling_osaker": lambda avstand_m: (
        "Kopplingen lov–byggnad är inte säkerställd: det godkända läget ligger "
        f"{avstand_m:.0f} m från den valda byggnaden — kontrollera att ärendet "
        "avser denna byggnad."
    ),
    "runner.ingen_skannad_handling": lambda: (
        "Ingen skannad handling i ärendet — korskontroll ej möjlig."
    ),
    "runner.lovarkiv_syntetiskt": lambda: (
        "Lovuppgifterna kommer ur ett SYNTETISKT testarkiv (mock-ByggR) — "
        "prototypfasen har ingen åtkomst till kommunens ärendesystem."
    ),
    "runner.hojd_ej_kontrollerbar": lambda: (
        "Byggnadens höjd och utseende kan inte kontrolleras mot lovet — flygbilder "
        "ser inte fasader (snedbilder saknas i prototypfasen)."
    ),
    "runner.ingen_byggnad_hittad": lambda radie_m, easting, northing: (
        f"Ingen byggnad hittades inom {radie_m:.0f} m från punkten "
        f"E {easting:.0f}, N {northing:.0f}."
    ),
    "runner.inget_lov_i_arkivet": lambda: (
        "Inget ärende i (test)arkivet för punkten — se Fall 1-analysen för lovplikt."
    ),
    "runner.inget_arende_matchar": lambda easting, northing: (
        "Inget (test)ärende i lovarkivet matchar punkten "
        f"E {easting:.0f}, N {northing:.0f} — se Fall 1-analysen för lovplikt."
    ),
    "runner.upphavt_strandskydd_konflikt": lambda byggnad_id, referens: (
        f"Byggnad {byggnad_id} berör även område med upphävt strandskydd ({referens}) "
        "— zonens aktuella utbredning måste kontrolleras mot Länsstyrelsens beslut."
    ),
    "runner.rattighetslager_otillgangligt": lambda lager: (
        f"{lager} kunde inte hämtas (källan otillgänglig) — "
        "rättigheter och gemensamhetsanläggningar har inte kunnat kontrolleras."
    ),
    "runner.hojd_granska_snedbilder": lambda ar: (
        "Byggnadens höjd och utseende kan inte mätas automatiskt — granska "
        f"snedbilderna ({_ar_lista(ar)}) manuellt mot lovet."
    ),
    "runner.snedbilder_otillgangliga": lambda: (
        "Snedbilder kunde inte hämtas (MapSpace otillgänglig eller ingen täckning) — "
        "höjd och utseende har inte kunnat granskas."
    ),
    # --- geodata.py: varifrån svaret faktiskt kom ---
    "geodata.snapshot_anvant": lambda lager, hamtad: (
        f"{lager} hämtades ur en lokal ögonblicksbild från {hamtad} — inte live "
        "från kommunens GeoServer; kontrollera mot tjänsten vid beslut."
    ),
    "geodata.cache_anvant": lambda lager, hamtad: (
        f"{lager} kunde inte hämtas live; ett tidigare svar från {hamtad} användes "
        "i stället — kontrollera mot tjänsten vid beslut."
    ),
    # --- källbeskrivningar (författningsnamn står kvar ordagrant) ---
    "kalla.ortofoto_tidslinje": lambda: "Ortofoto-tidslinje 1960–2023 (WMS)",
    "kalla.lovarkiv_syntetiskt": lambda dnr: f"Lovarkiv (syntetiskt), ärende {dnr}",
    "kalla.skannad_handling": lambda dnr: f"Skannad handling, ärende {dnr}",
    "kalla.pbl_lovbefrielser_preskription": lambda: (
        "PBL lovbefrielser + preskription (SFS 2010:900)"
    ),
    "kalla.pbl_lovbefrielser_regelverk_vid": lambda: (
        "PBL lovbefrielser + preskription (regelverk_vid)"
    ),
    "kalla.pbl_apbl_overgang": lambda: (
        "PBL/ÄPBL övergångsbestämmelser (SFS 2010:900 p. 2)"
    ),
    "kalla.pbl_apbl_overgang_regelverk_vid": lambda: (
        "PBL/ÄPBL övergångsbestämmelser + preskription (regelverk_vid)"
    ),
    "kalla.snedbilder_mapspace": lambda: "Snedbilder (MapSpace, Sundsvalls kommun)",
    # --- server.py: HTTP-fel ---
    "server.parametrar_ogiltiga": lambda detalj: (
        f"easting/northing saknas eller kunde inte tolkas: {detalj}"
    ),
    "server.internt_fel": lambda: "internt fel",
}


class Meddelande(str):
    """En svensk meddelandesträng som också bär sin i18n-kod och parametrar.

    Subklassar `str` med flit: allt som redan behandlar meddelanden som text
    (markdown-dossiern, CLI:t, testerna) fortsätter fungera oförändrat, medan
    `till_json` kan plocka ut koden och klienten översätta den.
    """

    kod: str
    params: dict[str, Any]

    def __new__(cls, kod: str, **params: Any) -> Meddelande:
        mall = _SV.get(kod)
        if mall is None:
            raise KeyError(f"okänd meddelandekod: {kod!r}")
        obj = super().__new__(cls, mall(**params))
        obj.kod = kod
        obj.params = params
        return obj

    def __repr__(self) -> str:  # pragma: no cover - felsökningshjälp
        return f"Meddelande({self.kod!r}, {self.params!r})"


# Åtgärdstexter som kommer ur regelmodellen (regler.json via regelverk_core) är
# data, inte kod — mappa de kända ordagrant till en kod. Okända texter släpps
# igenom som ren svenska: hellre ett oöversatt förbehåll än ett tappat.
_REGELVERK_ATGARDER: dict[str, str] = {
    _SV["regelverk.ange_startdatum"](): "regelverk.ange_startdatum",
}


def fran_regelverk(text: str) -> str:
    """Översätt en åtgärdstext ur regelmodellen till ett Meddelande om den är känd."""
    kod = _REGELVERK_ATGARDER.get(text)
    return Meddelande(kod) if kod else text


def till_json(varde: Any) -> Any:
    """Rekursivt: ersätt varje Meddelande med {"kod", "params"} för klienten.

    Allt annat passerar oförändrat — plain `str` betyder "ordagrann text"
    (författningsnamn, WFS-lagernamn, diarienummer) och ska inte översättas.
    """
    if isinstance(varde, Meddelande):
        return {"kod": varde.kod, "params": varde.params}
    if isinstance(varde, dict):
        return {n: till_json(v) for n, v in varde.items()}
    if isinstance(varde, (list, tuple)):
        return [till_json(v) for v in varde]
    return varde

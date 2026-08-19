# ByggR / Sokigo Nova — ArendeExportWS (referens från kommunen)

Källa: mejl från Jonny Olsson, Sundsvalls kommun, 2026-08-19 (svar på e-Avrop
fråga 150823 / P2). Detta är den officiella exportytan mot ByggR (Tekis/Sokigo)
och det som `mcp-bygglov`/`lovarkiv` ska mappas mot vid en framtida integration.
Ingen systemåtkomst i prototypfasen — mocken förblir syntetisk.

## Tjänst

- SOAP/WSDL: `http://[adress]/TekisArende/ArendeExportWS.svc?wsdl`
- Binding: `BasicHttpBinding_IExportArenden`, NetworkCredential-auth.

## Nyckelmetoder (urval)

| Metod | Parametrar | Kommentar |
| --- | --- | --- |
| `GetRelateradeArendenByFastighet` | `fnr?`, `trakt`, `fBetNr`, `arHuvudObjekt?`, `StatusFilter` | **Vår ingång**: ärenden per fastighet. Ex: `(null,'Fastighetsbeteckning AB ','123:4',1,'Aktiv')` → trakt + nr separerat. |
| `GetArende` | `dnr` | Enskilt ärende per diarienummer. |
| `GetDocument` | `documentId`, `inkluderaFil?`, `docSplitToken` | Hämtar handling (`namn`, `beskrivning`, `fil.filBuffer` = bytes). |
| `GetUpdatedArenden` / `GetUpdatedArendenCount` | `BatchFilter` | Inkrementell synk. |
| `GetArendeObjekt`, `GetArendeHandlaggare`, `GetIntressent` | message | Detaljobjekt. |
| `GetRelateradeArendenByPersOrgNr(AndRole)` | persOrgNr, kundNr, roller, StatusFilter | Personuppgifter — EJ relevant för piloten. |
| `GetHandlingTyper`, `GetRoller` | StatusFilter / RollTyp | Kodlistor. |
| `GetBevakadeUtskickByPersOrgNr` | message | Bevakningar. |

## Fältbeskrivning `TekisProxy.arende`

| Fält | Typ | Mappning mot `LovBeslut` (lovarkiv.py) |
| --- | --- | --- |
| `arendeId` | int | (intern nyckel) |
| `dnr`, `diarieprefix` | string | `dnr` |
| `arendetyp`, `arendeslag`, `arendeklass`, `arendegrupp` | string | `atgard` (klassificering; kodlistor okända ännu) |
| `beskrivning` | string | `atgard` (fritext) |
| `status` | `arendeStatus` | — (filtrera på beslutade) |
| `ankomstDatum`, `registreradDatum` | datetime | — |
| `atgardStartDatum`, `atgardSlutDatum` | datetime? | — |
| `slutDatum` | datetime? | kandidat för `beslutsdatum` (verifiera) |
| `makulerDatum` | datetime? | makulerat ärende → ignorera |
| `uppdateradDatum` | datetime | synk |
| `handlaggare` | `handlaggareBas` | — |
| `handelseLista` | `arendeHandelse[]` | händelser → `handlingLista[]` → `handlingId` → `GetDocument` → `handling` (PDF/ritning) |
| `intressentLista` | `arendeIntressent[]` | personuppgifter — ej i piloten |
| `objektLista` | `abstractArendeObjekt[]` | fastighet/byggnad kopplade till ärendet → `fastighet` |
| `bevakningLista` | `bevakning[]` | — |
| `planForhallandeId` | int16? | planförhållande (kodlista okänd) |
| `komplexitet`, `prioritet` | int16? | — |
| `kalla`, `komkod`, `namndkod`, `enhetkod`, `externRef`, `projektnr` | string | metadata |

`*Specified`-fälten är .NET-artefakter (nullable-flaggor), inte data.

## Konsekvenser

1. **Beslutsdatum/laga kraft/beviljad BYA/höjd/läge finns INTE som direkta fält** på
   `arende` — de ligger i handlingar (`handelseLista → handlingLista`) eller i
   `objektLista`. Vår `LovBeslut.godkant_lage` / `byggnadsarea_m2` / `hojd_m`
   måste därför komma från tolkning av handling (lovtolk) även i en riktig
   integration — precis som mocken redan antar.
2. Ingången per fastighet är `trakt` + `fBetNr` separat ("ALNÖ-USLAND", "1:45"),
   inte hel beteckning. Mocken bör exponera samma nyckel.
3. `GetDocument` ger bytes direkt → samma pipeline som `handling`-PDF i mocken.
4. Exempelanropet i PowerShell (från kommunen) sparas ordagrant nedan.

```powershell
$proxy = New-WebServiceProxy -Uri http://[adress]/TekisArende/ArendeExportWS.svc?wsdl -Namespace "TekisProxy"
$proxy.Credentials = New-Object System.Net.NetworkCredential("a","b")
$arenden = $proxy.GetRelateradeArendenByFastighet($null,'Fastighetsbeteckning AB ','123:4',1,'Aktiv')
$data = $proxy.GetDocument($arenden[0].handelseLista[0].handlingLista[0].handlingId,1,$document)
Set-Content -Path (Join-Path C:\Temp\ $data[0].namn) $data[0].fil.filBuffer -Encoding Byte
$arenden | Get-Member   # fältbeskrivning
$proxy | Get-Member     # metoder
```

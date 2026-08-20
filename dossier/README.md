# dossier

Beslutsunderlaget i två vyer från samma fakta — implementerat i
`src/geo_tillsyn/dossier.py`:

1. **Juridisk vy** (`render_markdown`) — tre nivåer för diariet: Fakta (varje
   påstående med klickbar källa och tidsstämpel), Bedömning (grund + »Ej
   fastställt«), Beslut (alltid tomt — handläggarens).
2. **Klarspråksvy** (`render_klarsprak`) — samma fakta, samma källor, samma
   osäkerheter, för berörd part: "Vad handlar det här om? / Det här har vi
   sett / Så här kan det tolkas / Vad händer nu?" plus en ordlista som bara
   förklarar facktermer som faktiskt förekommer i underlaget. Vyn lägger
   aldrig till påståenden och fäller aldrig ett omdöme (testat i
   `tests/test_klarsprak.py`).

Körningarna skriver båda: `dossier.md` + `dossier_klarsprak.md` (Fall 7),
`fall1_dossier[_klarsprak].md`, `fall3_dossier[_klarsprak].md`.

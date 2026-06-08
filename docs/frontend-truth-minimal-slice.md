# Frontend Truth Minimal Slice

Der Minimal Slice ist die temporaere stabile Basis fuer die Frontend Truth Suite.

Ziel ist zuerst ein gruener Kernfluss mit echter API und echter DB. Die Full-Suite bleibt als separater Ausbaupfad bestehen und darf erst erweitert oder wieder als Release-Basis genutzt werden, wenn der Minimal Slice stabil bleibt.

Pflichtscope:
- App erreichbar
- Login sichtbar
- Login erfolgreich
- Workspace ready
- Dokumentliste sichtbar
- Logout funktioniert

Regeln:
- echte API
- echte DB
- keine Mocks
- `failed = 0`
- `errors = 0`
- `skipped = 0`
- `playwright_exit_code = 0`

Ausfuehren:

```powershell
$env:DATABASE_URL = "postgresql+psycopg://Markus:Markus..2026@85.215.131.200:5432/wissen2026"
$env:TEST_DATABASE_URL = $env:DATABASE_URL
python scripts\run_gui_truth.py --minimal --start-api --start-frontend
```

Aktueller Nachweis:
- `reports/archive/m5a/report_integrity_pre_m5a_20260603T091500Z/frontend_truth_minimal_report.json`

Der Minimal-Report ist als stale optionaler Report archiviert und aktuell kein aktiver Gate-Input. Ein neuer Lauf darf wieder einen aktuellen Report erzeugen; bis dahin ist fuer Gate-Entscheidungen der Full-Suite- und Parent-Gate-Status massgeblich.

Die Full-Suite wird weiterhin ueber `python scripts\run_gui_truth.py` erzeugt und bleibt von diesem Minimal-Report getrennt.

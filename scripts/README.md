# Scripts

Hilfsskripte fuer lokale Entwicklung und wiederkehrende Arbeitsablaeufe.

## Zweck

- Entwicklungsstarts fuer Backend und Frontend kapseln.
- Keine Build- oder Laufzeitabhaengigkeit auf Docker Compose einfuehren.
- Skripte bleiben leichtgewichtig und projektbezogen.

## Lokale Dev-Skripte

- `dev-db.ps1` und `dev-db.sh` starten die lokale PostgreSQL-Dev-DB ueber `docker-compose.test.yml` auf Port `5433`.
- `dev-backend.sh` und `dev-frontend.sh` fuer Bash-Umgebungen.
- `dev-backend.ps1` und `dev-frontend.ps1` fuer PowerShell unter Windows.
- `dev-fullstack.ps1` startet Backend und Frontend gemeinsam in zwei separaten PowerShell-Fenstern.
- `run-postgres-truth.ps1` fuehrt `pytest -m postgres_truth tests/postgres_truth -q` ueber das Backend-Venv aus und schreibt aktive Reports nach `reports/current/`.
- `validate-m4-truth-gate.ps1` liest ausschliesslich Reports aus `reports/current/` und setzt das M4 Truth Gate auf `PASS` oder `FAIL`.
- `run-m4-truth-gate.ps1` erzeugt den PostgreSQL-Truth-Report und fuehrt danach den M4-Truth-Gate-Validator aus.
- `run_frontend_connectivity_truth.js` fuehrt einen echten Browser-Connectivity-Test gegen eine echte API aus und schreibt `reports/connectivity_truth_report.json` plus Markdown. Der Test nutzt keine Mock-Responses und klassifiziert DNS, Timeout, Refused, CORS und Mixed Content.
- `validate_frontend_runtime_connectivity_gate.py` wertet ausschliesslich `reports/connectivity_truth_report.json` aus und schreibt den Connectivity-Gate-Score nach `reports/frontend_runtime_connectivity_gate_report.json` plus Markdown.
- `generate_truth_split_reports.py` fuehrt pytest aus, liest die Truth-Gate-Marker je Test und schreibt aktive JSON-Reports nach `reports/current/`. Gate-Validatoren duerfen nur ihren eigenen aktuellen Split-Report auswerten.
- `validate_gate_hierarchy.py` liest aktive Split-Reports aus `reports/current/` und erzeugt `reports/current/gate_hierarchy_result.json` plus Markdown mit Gate-Status, Abhaengigkeitsgraph und Blockern.
- `detect_gate_drift.py` vergleicht aktuelle Gate-Reports aus `reports/current/`, Marker-Taxonomie und Dokumentationsreferenzen gegen `reports/gate_drift_baseline.json`. Drift ist ein Fail, wenn Reports fehlen/veraltet sind, weniger Tests als die Baseline enthalten, Marker fehlen, Tests unklassifiziert sind, Scores trotz neuer Failures steigen oder Dokumente alte oder nicht-current Reports referenzieren.
- `generate_masterplan_status.py` berechnet den Masterplan-Status aus aktuellen Gate-Reports, Release Candidates, Truth Reports, Known Limitations, Documentation Audit und Gate Drift. Es schreibt `reports/current/masterplan_status.json` und den generierbaren Abschnitt `docs/generated/status_section.md`; manuelle Statusaussagen duerfen diesen Maschinenstatus nicht ueberschreiben.
- `bootstrap_local_backend.py` fuehrt `alembic upgrade head` gegen die lokale Dev-DB aus und legt einen Default-Workspace plus Default-User an.

## Truth Split Reportformat

Jeder Split-Report enthaelt mindestens:

- `collected`
- `passed`
- `failed`
- `errors`
- `skipped`
- `exit_code`
- `test_database_url_set`
- `failed_tests`
- `timestamp`

## Frontend Connectivity Truth

```powershell
node scripts\run_frontend_connectivity_truth.js
```

Optionale Umgebung:

- `CONNECTIVITY_FRONTEND_BASE_URL`, Default `http://localhost:5173`
- `VITE_API_BASE_URL` oder `API_BASE_URL`, Default `http://127.0.0.1:8000`
- `CONNECTIVITY_LOGIN` und `CONNECTIVITY_PASSWORD`

Der Report `reports/connectivity_truth_report.json` ist nur `PASS`, wenn Frontend und echter Browser das Backend erreichen, `/health` und `/api/v1/auth/me` erreichbar sind, Login funktioniert, Auth- und Workspace-Header beobachtet werden und keine CORS-, Mixed-Content-, DNS- oder Timeout-Fehler auftreten.

## Frontend Runtime Connectivity Gate

```powershell
python scripts\validate_frontend_runtime_connectivity_gate.py
```

Der Gate-Report `reports/frontend_runtime_connectivity_gate_report.json` wertet nur den eigenen Connectivity-Truth-Report aus. Bewertet werden Backend-Erreichbarkeit, `/health`, `/api/v1/auth/me`, Login, Workspace-Bootstrap, Dokumentliste, API_UNREACHABLE im Normalflow, CORS und Mixed Content. Score `>= 90` bedeutet `CONNECTIVITY_STABLE`; darunter wird `M3A_BLOCKED` ausgegeben.

## Gate-Hierarchie

- M3a Gate: `reports/current/m3a_frontend_truth.json`
- M4a Gate: `reports/current/m4a_auth_truth.json`
- M4b Gate: `reports/current/m4b_upload_queue_truth.json`
- M4c Gate: `reports/current/m4c_lifecycle_retrieval_truth.json`
- M4e Gate: `reports/current/m4e_backup_restore_truth.json`
- M4 Gesamtgate: M4 Cross-Cutting + M4a/b/c/e
- M5 Startgate: M4 Gesamtgate
- Operational Governance Gate: M5 Startgate + `reports/current/governance_truth_report.json`

## Gate Drift Detection

Baseline erzeugen:

```powershell
python scripts\detect_gate_drift.py --write-baseline
```

Drift pruefen:

```powershell
python scripts\detect_gate_drift.py
```

Der Drift-Report wird nach `reports/current/gate_drift_report.json` und Markdown geschrieben. Ein `FAIL` ist blockierend fuer Gate-Freigaben, bis die Findings erklaert oder behoben sind.

## Masterplan Status Engine

```powershell
python scripts\generate_masterplan_status.py
```

Outputs:

- `reports/current/masterplan_status.json`
- `docs/generated/status_section.md`
- JSON Schema: `docs/masterplan_status.schema.json`

Die Engine ist die Status-Quelle fuer Masterplan-Fortschritt, Gate-Scores und Blocker. Dokumentation darf den erzeugten Status zitieren, aber nicht manuell ueberschreiben.

## Governance Boundary

Die Boundary zwischen M3a, M4, M5 und Operational Governance ist in `docs/governance-boundary.json` und `docs/governance-boundary.md` definiert:

- M3a prueft GUI Foundation.
- M4 prueft Produktisierung und Stabilisierung.
- M5 prueft Langzeitbetrieb und Governance.
- `m5_truth` und `governance_truth` duerfen M4 nicht blockieren.
- M4-Gates duerfen M5 blockieren.
- `frontend_truth` darf M4 nur bei deklarierter `gui_dependency=true` blockieren.

`dev-backend.ps1` und `dev-backend.sh` nutzen lokal automatisch
`postgresql+psycopg://testuser:testpass@127.0.0.1:5433/wissen_test`, wenn `DATABASE_URL` nicht gesetzt ist.
Wenn die lokale DB nicht erreichbar ist, brechen sie mit einer konkreten Anweisung zum Start von `dev-db.*` ab.
Vor dem Uvicorn-Start fuehren sie ausserdem das lokale Backend-Bootstrap aus.

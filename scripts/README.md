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
- `run-postgres-truth.ps1` fuehrt `pytest -m postgres_truth tests/postgres_truth -q` ueber das Backend-Venv aus und schreibt den Truth-Test-Report nach `reports/`.
- `validate-m4-truth-gate.ps1` liest ausschliesslich `reports/postgres_truth_report.json` und setzt das M4 Truth Gate auf `PASS` oder `FAIL`.
- `run-m4-truth-gate.ps1` erzeugt den PostgreSQL-Truth-Report und fuehrt danach den M4-Truth-Gate-Validator aus.
- `bootstrap_local_backend.py` fuehrt `alembic upgrade head` gegen die lokale Dev-DB aus und legt einen Default-Workspace plus Default-User an.

`dev-backend.ps1` und `dev-backend.sh` nutzen lokal automatisch
`postgresql+psycopg://testuser:testpass@127.0.0.1:5433/wissen_test`, wenn `DATABASE_URL` nicht gesetzt ist.
Wenn die lokale DB nicht erreichbar ist, brechen sie mit einer konkreten Anweisung zum Start von `dev-db.*` ab.
Vor dem Uvicorn-Start fuehren sie ausserdem das lokale Backend-Bootstrap aus.

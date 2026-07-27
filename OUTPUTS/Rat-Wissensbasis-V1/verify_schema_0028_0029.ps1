<#
================================================================================
 Schema-Verifikation fuer Migration 0028/0029 + ORM-Abgleich
================================================================================
 Zweck: Nachweis "fehlerfreier Live-Lauf" fuer die Aenderungen vom 2026-07-26:

   - ORM-Modelle an die Migrationskette angeglichen (Checks, Unique-Indizes,
     JSONB-Varianten) -> app/models/documents.py, app/models/analysis.py
   - Migration 20260726_0028: vier tote Analyse-Tabellen entfernt
   - Migration 20260726_0029: background_jobs erlaubt Status 'cancelled'
   - scripts/seed_auth.py setzt workspaces.kind='shared' beim Default-Workspace

 Die Sandbox kann PostgreSQL nicht installieren (kein root) und erreicht die
 Test-DB nicht. Deshalb laeuft der Nachweis hier, bei dir.

 SICHERHEIT: Passwort NICHT in dieser Datei. Vorher setzen:
   $env:TEST_DATABASE_URL = "postgresql://wissensdb_test_user:PASS@85.215.131.200:5432/wissensdb_test"

 Aufruf (aus Repo-Root H:\WissenMai2026):
   powershell -ExecutionPolicy Bypass -File .\OUTPUTS\Rat-Wissensbasis-V1\verify_schema_0028_0029.ps1

 VORHER LESEN: Schritt 3 fuehrt DROP TABLE aus. Auf einer DB mit Produktivdaten
 zuerst Schritt 2 (Zeilenzaehlung) bewerten. Die Migration bricht von selbst ab,
 wenn eine der Tabellen Zeilen enthaelt.
================================================================================
#>

$ErrorActionPreference = "Stop"

if (-not $env:TEST_DATABASE_URL) {
  Write-Host "TEST_DATABASE_URL ist nicht gesetzt. Bitte zuerst setzen:" -ForegroundColor Red
  Write-Host '  $env:TEST_DATABASE_URL = "postgresql://wissensdb_test_user:PASS@85.215.131.200:5432/wissensdb_test"'
  exit 1
}
$env:DATABASE_URL = $env:TEST_DATABASE_URL

$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $repo
Write-Host "Repo: $repo" -ForegroundColor Cyan
Write-Host "DB  : $($env:TEST_DATABASE_URL -replace ':[^:@/]+@',':***@')" -ForegroundColor Cyan

$py = if (Test-Path ".\.venv\Scripts\python.exe") { ".\.venv\Scripts\python.exe" } else { "python" }
Write-Host "Python: $py`n"

function Step($n, $t) { Write-Host "`n=== Schritt $n : $t ===" -ForegroundColor Yellow }

# ---------------------------------------------------------------------------
Step 1 "ORM gegen Migrationskette diffen (ohne DB, muss vor allem anderen gruen sein)"
Push-Location backend
& $py -m pytest tests/integration/test_schema_truth_0028_0029.py -q -k "not postgres"
$rcOrm = $LASTEXITCODE
Pop-Location
if ($rcOrm -ne 0) {
  Write-Host "ORM weicht von den Migrationen ab. Abbruch vor jedem DB-Zugriff." -ForegroundColor Red
  exit $rcOrm
}

# ---------------------------------------------------------------------------
Step 2 "Ist-Stand vor dem Upgrade: Head + Zeilenzahlen der Drop-Kandidaten"
Push-Location backend
& $py -m alembic -c alembic.ini current
Pop-Location

$countSql = @"
SELECT c.relname AS tabelle, (SELECT count(*) FROM pg_class x WHERE x.oid = c.oid) AS existiert
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relname IN
  ('analysis_groups','analysis_group_documents','analysis_results_legacy',
   'analysis_result_sources_legacy','migration_document_repairs');
"@
& $py -c @"
import os, psycopg
url = os.environ['TEST_DATABASE_URL'].replace('postgresql+psycopg://','postgresql://',1)
tables = ['analysis_groups','analysis_group_documents','analysis_results_legacy',
          'analysis_result_sources_legacy','migration_document_repairs']
with psycopg.connect(url) as conn:
    cur = conn.cursor()
    for t in tables:
        cur.execute('SELECT to_regclass(%s)', ('public.'+t,))
        if cur.fetchone()[0] is None:
            print(f'  {t:38s} existiert nicht')
            continue
        cur.execute(f'SELECT count(*) FROM \"{t}\"')
        print(f'  {t:38s} Zeilen = {cur.fetchone()[0]}')
"@
Write-Host "Enthaelt eine der ersten vier Tabellen Zeilen, bricht Schritt 3 ab. Das ist gewollt." -ForegroundColor DarkGray

# ---------------------------------------------------------------------------
Step 3 "alembic upgrade head (0027 -> 0028 -> 0029)"
Push-Location backend
& $py -m alembic -c alembic.ini upgrade head
$rcUpgrade = $LASTEXITCODE
& $py -m alembic -c alembic.ini current
Pop-Location

# ---------------------------------------------------------------------------
Step 4 "Constraint-Proben + Round-Trip auf der echten DB"
Push-Location backend
& $py -m pytest tests/integration/test_schema_truth_0028_0029.py -q -m postgres
$rcTruth = $LASTEXITCODE
Pop-Location

# ---------------------------------------------------------------------------
Step 5 "Bestehende Migrations-Integration (Regression)"
Push-Location backend
& $py -m pytest tests/integration/test_migrations.py -q
$rcMigrations = $LASTEXITCODE
Pop-Location

# ---------------------------------------------------------------------------
Step 6 "seed_auth gegen echte DB (setzt kind='shared' auf dem Default-Workspace)"
Push-Location backend
& $py scripts\seed_auth.py
$rcSeed = $LASTEXITCODE
Pop-Location
& $py -c @"
import os, psycopg
url = os.environ['TEST_DATABASE_URL'].replace('postgresql+psycopg://','postgresql://',1)
with psycopg.connect(url) as conn:
    cur = conn.cursor()
    cur.execute('SELECT id, name, is_default, kind, owner_user_id FROM workspaces ORDER BY is_default DESC')
    for row in cur.fetchall():
        print('  ', row)
"@

# ---------------------------------------------------------------------------
Step 7 "Unit-Suite ohne DB (Regression durch die ORM-Aenderungen)"
Push-Location backend
& $py -m pytest -m "not postgres and not postgres_truth" -q
$rcUnit = $LASTEXITCODE
Pop-Location

Write-Host "`n================= ZUSAMMENFASSUNG =================" -ForegroundColor Green
Write-Host (" ORM-vs-Migration   RC={0}" -f $rcOrm)
Write-Host (" alembic upgrade    RC={0}" -f $rcUpgrade)
Write-Host (" Schema-Truth (PG)  RC={0}" -f $rcTruth)
Write-Host (" test_migrations    RC={0}" -f $rcMigrations)
Write-Host (" seed_auth          RC={0}" -f $rcSeed)
Write-Host (" Unit-Suite         RC={0}" -f $rcUnit)
Write-Host " Abnahme nur bei RC=0 in ALLEN Zeilen." -ForegroundColor Green
Write-Host "===================================================" -ForegroundColor Green

<# ---------------------------------------------------------------------------
 OFFEN, BRAUCHT DEINE ENTSCHEIDUNG (nicht im Skript automatisiert):

 1. tests/test_documents_read_api.py::test_get_document_returns_409_when_document_has_no_version
    Der Test baut ein Dokument mit import_status='chunked' ohne current_version_id.
    Genau das verbietet ck_documents_readable_status_requires_current_version.
    Der Zustand ist auf PostgreSQL nicht herstellbar -> der 409-Zweig in der API
    ist toter Code, oder der Check ist zu streng. Eins von beidem muss weg.

 2. 17 Testdateien sind vom Truth-Gate-Klassifizierer in tests/conftest.py nicht
    erfassbar (_classify_truth_gate liefert None). Folge: 'pytest tests/' bricht
    mit UsageError ab, sobald die postgres_truth-Preflight passiert. Liste:
    tests/test_security_headers.py, test_restore_integration.py,
    test_backup_integration.py, test_approval_policy.py,
    test_ga_regression_decoupled.py, test_data_quality_runner.py,
    test_drift_persistence.py, test_drift_run_engine.py,
    test_lifecycle_drift_detector.py, test_metadata_drift_detector.py,
    test_m5b_drift_api.py, test_m5b_drift_api_contracts.py,
    test_m5b_drift_cli_regression.py, test_m5b_drift_runner_idempotency.py,
    test_m5b_drift_severity_truth.py, test_m5b_no_mutation_truth.py,
    test_m5b_workspace_isolation_truth.py

 3. tests/postgres_truth/test_m4e_backup_restore_truth.py importiert weiterhin
    create_backup aus app.services.backup_restore -> ImportError beim Sammeln.
    Bekannt als EVIDENCE.md Fund 2, weiterhin offen.

 4. Doppelter GIN-Index auf document_chunks.search_vector (siehe Kommentar in
    run_truth_against_real_db.ps1) — weiterhin offen.
--------------------------------------------------------------------------- #>

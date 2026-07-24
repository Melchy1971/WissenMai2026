<#
================================================================================
 Truth-/Gate-Neulauf gegen die ECHTE Test-DB  (Empfehlung "Der Rat", Schritt 1)
================================================================================
 Zweck: Den ehrlichen Ist-Stand herstellen, statt auf veraltetem Status
        weiterzubauen. Reproduziert die CI-Sequenz (.github/workflows/ci.yml)
        plus Status-Neugenerierung.

 WARUM DIESES SKRIPT und nicht die Sandbox:
   Die Cowork-Sandbox erreicht 85.215.131.200:5432 nicht (ausgehend gesperrt).
   Bereits in der Sandbox gegen ein lokales Postgres 16 BEWIESEN:
     - alembic upgrade head laeuft sauber bis Head 20260618_0026
     - GIN-Index ix_document_chunks_search_vector_gin existiert  -> GA-PERF-01
     - tests/integration/test_migrations.py: 4 passed
   Der Rest (postgres_truth-Suite, Gate-Recheck) braucht eine ERREICHBARE DB
   und den projekteigenen Truth-Marker-Runner -> deshalb hier, bei dir.

 SICHERHEIT: Passwort steht NICHT in dieser Datei. Vorher als Env setzen:
   $env:TEST_DATABASE_URL = "postgresql://wissensdb_test_user:PASS@85.215.131.200:5432/wissensdb_test"

 Aufruf (aus Repo-Root H:\WissenMai2026):
   powershell -ExecutionPolicy Bypass -File .\OUTPUTS\Rat-Wissensbasis-V1\run_truth_against_real_db.ps1
================================================================================
#>

$ErrorActionPreference = "Stop"

if (-not $env:TEST_DATABASE_URL) {
  Write-Host "TEST_DATABASE_URL ist nicht gesetzt. Bitte zuerst setzen:" -ForegroundColor Red
  Write-Host '  $env:TEST_DATABASE_URL = "postgresql://wissensdb_test_user:PASS@85.215.131.200:5432/wissensdb_test"'
  exit 1
}
# Backend liest DATABASE_URL; alembic/env.py nutzt settings.database_url.
$env:DATABASE_URL = $env:TEST_DATABASE_URL

$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)  # -> Repo-Root
Set-Location $repo
Write-Host "Repo: $repo" -ForegroundColor Cyan
Write-Host "DB  : $($env:TEST_DATABASE_URL -replace ':[^:@/]+@',':***@')" -ForegroundColor Cyan

# Python aus venv, sonst System-Python
$py = if (Test-Path ".\.venv\Scripts\python.exe") { ".\.venv\Scripts\python.exe" } else { "python" }
Write-Host "Python: $py`n"

function Step($n,$t){ Write-Host "`n=== Schritt $n : $t ===" -ForegroundColor Yellow }

# ---------------------------------------------------------------------------
Step 1 "Migrationen gegen echte DB anwenden (beweist GA-PERF-01 real)"
Push-Location backend
& $py -m alembic -c alembic.ini upgrade head
& $py -m alembic -c alembic.ini current
Pop-Location

# ---------------------------------------------------------------------------
Step 2 "Unit-Suite (CI-Job 1: ohne DB)"
Push-Location backend
& $py -m pytest -m "not postgres and not postgres_truth" -q
$rcUnit = $LASTEXITCODE
Pop-Location

# ---------------------------------------------------------------------------
Step 3 "Postgres-Integration (CI-Job 2: -m postgres, braucht DB)"
Push-Location backend
& $py -m pytest -m "postgres and not postgres_truth" -q
$rcPg = $LASTEXITCODE
Pop-Location

# ---------------------------------------------------------------------------
Step 4 "Postgres-Truth-Suite (CI-Job 3: der eigentliche SCGB-01-Nachweis)"
Push-Location backend
& $py -m pytest -m "postgres_truth" -q
$rcTruth = $LASTEXITCODE
Pop-Location

# ---------------------------------------------------------------------------
Step 5 "Gate-Reports + Masterplan-Status NEU generieren"
# Diese Skripte lesen reports/current/*.json und schreiben den Maschinenstatus.
# Reihenfolge: erst die einzelnen Gate-Generatoren, dann der Aggregator.
$gateScripts = @(
  "scripts\generate_m4_truth_report.py",
  "scripts\generate_report_integrity_v2.py",
  "scripts\generate_masterplan_status_v3.py"
)
foreach ($s in $gateScripts) {
  if (Test-Path $s) { Write-Host "-> $s"; & $py $s } else { Write-Host "(uebersprungen, fehlt: $s)" -ForegroundColor DarkGray }
}

# ---------------------------------------------------------------------------
Step 6 "Delta: was hat sich am Status geaendert? (nichts committen)"
git --no-pager diff --stat -- reports/current/ masterplan.md
Write-Host "`nKerngroessen aus dem neuen Status:" -ForegroundColor Cyan
if (Test-Path "reports\current\masterplan_status.json") {
  & $py -c "import json;d=json.load(open('reports/current/masterplan_status.json',encoding='utf-8'));print(' release_status =',d.get('release_status'));print(' maturity       =',d.get('product_maturity_score'),'/ 90');print(' gold_path      =',d.get('gold_path_status'))"
}

Write-Host "`n================= ZUSAMMENFASSUNG =================" -ForegroundColor Green
Write-Host (" Unit-Suite      RC={0}" -f $rcUnit)
Write-Host (" Postgres        RC={0}" -f $rcPg)
Write-Host (" Postgres-Truth  RC={0}" -f $rcTruth)
Write-Host " Naechste Entscheidung (Schritt 3 der Rats-Empfehlung):" -ForegroundColor Green
Write-Host "   Zielbild fixieren: 'lokales V1' ODER 'KI-Analyse-Produkt'?"
Write-Host "   -> Davon haengt ab, ob Maturity >=90 sinnvoll oder Gold-Plating ist."
Write-Host "===================================================" -ForegroundColor Green

<# ---------------------------------------------------------------------------
 OPTIONALE TECH-DEBT-BEREINIGUNG (nicht automatisch, bewusste Entscheidung):
 In 20260618_0026 wurde ein ZWEITER, redundanter GIN-Index auf
 document_chunks.search_vector angelegt (ix_document_chunks_search_vector_gin,
 partiell), zusaetzlich zum bereits seit 0011/0012 existierenden
 ix_document_chunks_search_vector. Zwei GIN-Indizes auf derselben Spalte =
 doppelte Schreiblast/Speicher ohne Lesevorteil. Entscheidung faellig:
 einen der beiden per Folge-Migration droppen (bevorzugt den nicht-partiellen
 alten, falls der partielle die Query-Praedikate abdeckt).
--------------------------------------------------------------------------- #>

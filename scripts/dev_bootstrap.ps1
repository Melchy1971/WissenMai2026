<#
.SYNOPSIS
  Einheitlicher lokaler Bootstrap-Befehl fuer Ruflo.

.DESCRIPTION
  Fuehrt folgende Schritte in Reihenfolge aus:
    1. .env laden
    2. DB-Verbindung pruefen
    3. Alembic upgrade head
    4. seed_auth.py
    5. auth_bootstrap_guard (check_auth_bootstrap.py, kein API-Start)
    6. Backend smoke: /health
    7. Report schreiben → reports/dev_bootstrap_report.json

  Bei Fehler in einem Schritt: klare Meldung, Exit != 0, kein Silent Continue.

.EXAMPLE
  .\scripts\dev_bootstrap.ps1
  .\scripts\dev_bootstrap.ps1 -ApiPort 8002
  .\scripts\dev_bootstrap.ps1 -SkipSeed -SkipSmoke
#>
[CmdletBinding()]
param(
    [int]    $ApiPort   = 8001,
    [switch] $SkipSeed,
    [switch] $SkipSmoke,
    [switch] $DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot   = Split-Path -Parent $scriptDir
$backendDir = Join-Path $repoRoot 'backend'
$venvPy     = Join-Path $backendDir '.venv\Scripts\python.exe'
$reportPath = Join-Path $repoRoot 'reports\dev_bootstrap_report.json'

# ── Hilfsfunktionen ───────────────────────────────────────────────────────────

function Write-Step([string]$msg) {
    Write-Host "`n[dev_bootstrap] $msg" -ForegroundColor Cyan
}

function Write-OK([string]$msg) {
    Write-Host "  [OK] $msg" -ForegroundColor Green
}

function Write-Fail([string]$msg) {
    Write-Host "  [FAIL] $msg" -ForegroundColor Red
}

function Require-ExitCode([int]$code, [string]$step) {
    if ($code -ne 0) {
        Write-Fail "$step fehlgeschlagen (exit $code)"
        exit $code
    }
}

# ── Schritt 0: Venv pruefen ───────────────────────────────────────────────────
if (-not (Test-Path $venvPy)) {
    Write-Fail "Backend-Venv nicht gefunden: $venvPy"
    Write-Host "  Erstelle es mit: cd backend && python -m venv .venv && .venv\Scripts\pip install -e .[dev]"
    exit 1
}

$steps = [ordered]@{}
$overallStart = Get-Date

# ── Schritt 1: .env laden ────────────────────────────────────────────────────
Write-Step "ENV laden (.env)"
$envFile = Join-Path $repoRoot '.env'
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith('#') -and $line -match '=') {
            $parts  = $line -split '=', 2
            $key    = $parts[0].Trim()
            $value  = $parts[1].Trim().Trim('"').Trim("'")
            if (-not [System.Environment]::GetEnvironmentVariable($key)) {
                [System.Environment]::SetEnvironmentVariable($key, $value, 'Process')
            }
        }
    }
    Write-OK ".env geladen aus $envFile"
} else {
    Write-Host "  [WARN] .env nicht gefunden — nur System-ENV wird verwendet"
}

if (-not $env:DATABASE_URL) {
    Write-Fail "DATABASE_URL ist nicht gesetzt. Setze DATABASE_URL in .env oder als Umgebungsvariable."
    exit 2
}
$steps['env'] = 'pass'

if ($DryRun) {
    Write-Host "`n[dev_bootstrap] Dry-run — kein weiterer Aufruf." -ForegroundColor Yellow
    exit 0
}

# ── Schritt 2: DB-Verbindung pruefen ─────────────────────────────────────────
Write-Step "DB-Verbindung pruefen"
$t0 = Get-Date
& $venvPy -c @"
import os, sys
try:
    import psycopg
    url = os.environ['DATABASE_URL'].replace('postgresql+psycopg://', 'postgresql://', 1)
    conn = psycopg.connect(url, connect_timeout=5)
    conn.close()
    print('  DB erreichbar')
except Exception as exc:
    print(f'  DB nicht erreichbar: {exc}', file=sys.stderr)
    sys.exit(1)
"@
Require-ExitCode $LASTEXITCODE "DB-Verbindung"
Write-OK "DB erreichbar ($([int]((Get-Date) - $t0).TotalMilliseconds) ms)"
$steps['db_connection'] = 'pass'

# ── Schritt 3: Alembic upgrade head ──────────────────────────────────────────
Write-Step "Alembic upgrade head"
$t0 = Get-Date
Push-Location $repoRoot
& $venvPy -m alembic --config backend/alembic.ini upgrade head
$alembicCode = $LASTEXITCODE
Pop-Location
Require-ExitCode $alembicCode "Alembic upgrade head"
Write-OK "Schema aktuell ($([int]((Get-Date) - $t0).TotalMilliseconds) ms)"
$steps['alembic_upgrade'] = 'pass'

# ── Schritt 4: seed_auth.py ───────────────────────────────────────────────────
if (-not $SkipSeed) {
    Write-Step "seed_auth.py"
    $t0 = Get-Date
    Push-Location $repoRoot
    & $venvPy backend/scripts/seed_auth.py
    $seedCode = $LASTEXITCODE
    Pop-Location
    Require-ExitCode $seedCode "seed_auth.py"
    Write-OK "Seed abgeschlossen ($([int]((Get-Date) - $t0).TotalMilliseconds) ms)"
    $steps['seed_auth'] = 'pass'
} else {
    Write-Host "`n[dev_bootstrap] Schritt 4 uebersprungen (-SkipSeed)" -ForegroundColor Yellow
    $steps['seed_auth'] = 'skipped'
}

# ── Schritt 5: Auth Bootstrap Guard ──────────────────────────────────────────
Write-Step "Auth Bootstrap Guard (DB-only, kein API-Start)"
$t0 = Get-Date
Push-Location $repoRoot
& $venvPy scripts/check_auth_bootstrap.py --no-start-api
$guardCode = $LASTEXITCODE
Pop-Location
if ($guardCode -ne 0) {
    Write-Fail "Auth Bootstrap Guard FAIL (exit $guardCode) — Seed oder DB-Zustand pruefen"
    $steps['auth_bootstrap_guard'] = 'fail'
    # Schreibe Teilreport und breche ab
    $steps['backend_smoke'] = 'skipped'
} else {
    Write-OK "Auth Bootstrap Guard PASS ($([int]((Get-Date) - $t0).TotalMilliseconds) ms)"
    $steps['auth_bootstrap_guard'] = 'pass'
}

# ── Schritt 6: Backend Smoke (/health) ───────────────────────────────────────
if ($steps['auth_bootstrap_guard'] -eq 'pass' -and -not $SkipSmoke) {
    Write-Step "Backend Smoke /health (Port $ApiPort)"
    $apiUrl = "http://127.0.0.1:$ApiPort/health"
    $t0 = Get-Date
    $smokeOk = $false
    try {
        $response = Invoke-WebRequest -Uri $apiUrl -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-OK "/health HTTP 200 ($([int]((Get-Date) - $t0).TotalMilliseconds) ms)"
            $smokeOk = $true
        } else {
            Write-Host "  [WARN] /health HTTP $($response.StatusCode) — Backend laeuft, aber Status unerwartet"
        }
    } catch {
        Write-Host "  [WARN] Backend nicht erreichbar auf Port $ApiPort — Smoke-Check uebersprungen" -ForegroundColor Yellow
        Write-Host "         Starte das Backend manuell und fuehre den Smoke-Check separat aus."
    }
    $steps['backend_smoke'] = if ($smokeOk) { 'pass' } elseif ($SkipSmoke) { 'skipped' } else { 'warn' }
} elseif ($SkipSmoke) {
    Write-Host "`n[dev_bootstrap] Schritt 6 uebersprungen (-SkipSmoke)" -ForegroundColor Yellow
    $steps['backend_smoke'] = 'skipped'
}

# ── Schritt 7: Report schreiben ───────────────────────────────────────────────
Write-Step "Report schreiben → $reportPath"
$passed   = ($steps.Values | Where-Object { $_ -eq 'pass' }).Count
$failed   = ($steps.Values | Where-Object { $_ -eq 'fail' }).Count
$skipped  = ($steps.Values | Where-Object { $_ -eq 'skipped' }).Count
$warned   = ($steps.Values | Where-Object { $_ -eq 'warn' }).Count
$overall  = if ($failed -gt 0) { 'FAIL' } elseif ($warned -gt 0) { 'WARN' } else { 'PASS' }
$duration = [int]((Get-Date) - $overallStart).TotalSeconds

$stepsJson = ($steps.GetEnumerator() | ForEach-Object {
    "`"$($_.Key)`": `"$($_.Value)`""
}) -join ", "

$maskedUrl = $env:DATABASE_URL -replace '://([^:]+):[^@]+@', '://$1:***@'
$timestamp = (Get-Date -Format 'yyyy-MM-ddTHH:mm:ssZ')
$seedLogin = if ($env:SEED_ADMIN_LOGIN) { $env:SEED_ADMIN_LOGIN } elseif ($env:WISSEN_DEV_LOGIN) { $env:WISSEN_DEV_LOGIN } else { 'admin@localhost' }

$reportJson = @"
{
  "name": "dev_bootstrap",
  "timestamp": "$timestamp",
  "environment": "local",
  "database_url_set": true,
  "test_database_url_set": false,
  "result": "$overall",
  "duration_seconds": $duration,
  "seed_login": "$seedLogin",
  "database_url": "$maskedUrl",
  "steps": { $stepsJson },
  "summary": {
    "passed": $passed,
    "failed": $failed,
    "skipped": $skipped,
    "warned": $warned
  },
  "gate": "m3a_preflight",
  "blockers": [],
  "known_limitations": []
}
"@

New-Item -ItemType Directory -Force -Path (Split-Path $reportPath) | Out-Null
Set-Content -Path $reportPath -Value $reportJson -Encoding UTF8
Write-OK "Report geschrieben"

# ── Ergebnis ──────────────────────────────────────────────────────────────────
Write-Host ""
if ($overall -eq 'PASS') {
    Write-Host "[dev_bootstrap] STATUS: PASS — System bereit ($duration s)" -ForegroundColor Green
} elseif ($overall -eq 'WARN') {
    Write-Host "[dev_bootstrap] STATUS: WARN — Bereit mit Einschraenkungen ($duration s)" -ForegroundColor Yellow
} else {
    Write-Host "[dev_bootstrap] STATUS: FAIL — $failed Schritt(e) fehlgeschlagen ($duration s)" -ForegroundColor Red
    exit 1
}

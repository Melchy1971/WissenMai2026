<#
.SYNOPSIS
  Fuehrt einen Restore-Test in eine leere Test-DB aus.

.DESCRIPTION
  Schritte:
    1. Backup-Datei einlesen (neueste in backups/ oder -BackupFile)
    2. pg_restore in TEST_DATABASE_URL (leere Test-DB)
    3. Alembic current == head pruefen
    4. Login-Test (check_auth_bootstrap.py --no-start-api)
    5. Report: reports/current/restore_test_report.json
  Exit 0 = PASS

.EXAMPLE
  .\scripts\run_restore_test.ps1
  .\scripts\run_restore_test.ps1 -BackupFile H:\backups\2026-06-15_10-00.dump
#>
[CmdletBinding()]
param(
    [string] $BackupFile = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot   = Split-Path -Parent $scriptDir
$backendDir = Join-Path $repoRoot 'backend'
$venvPy     = Join-Path $backendDir '.venv\Scripts\python.exe'
$reportPath = Join-Path $repoRoot 'reports\current\restore_test_report.json'

function Write-Step([string]$msg) { Write-Host "`n[run_restore_test] $msg" -ForegroundColor Cyan }
function Write-OK([string]$msg)   { Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Fail([string]$msg) { Write-Host "  [FAIL] $msg" -ForegroundColor Red }
function Mask-Url([string]$url)   { $url -replace '://([^:]+):[^@]+@', '://$1:***@' }

# ENV laden
$envFile = Join-Path $repoRoot '.env'
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^([^#][^=]+)=(.+)$') {
            $k = $Matches[1].Trim(); $v = $Matches[2].Trim().Trim('"').Trim("'")
            if (-not [System.Environment]::GetEnvironmentVariable($k)) {
                [System.Environment]::SetEnvironmentVariable($k, $v, 'Process')
            }
        }
    }
}

if (-not $env:TEST_DATABASE_URL) {
    Write-Fail "TEST_DATABASE_URL nicht gesetzt. Restore-Test braucht eine separate Test-DB."
    exit 2
}

$maskedTestUrl = Mask-Url $env:TEST_DATABASE_URL
$pgTestUrl     = $env:TEST_DATABASE_URL -replace '^postgresql\+psycopg://', 'postgresql://'

# Neueste Backup-Datei finden
if (-not $BackupFile) {
    $backupsDir = Join-Path $repoRoot 'backups'
    if (-not (Test-Path $backupsDir)) {
        Write-Fail "Kein backups/-Verzeichnis gefunden. run_backup.ps1 zuerst ausfuehren."
        exit 3
    }
    $latest = Get-ChildItem $backupsDir -Filter '*.dump' | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $latest) {
        Write-Fail "Kein .dump-Backup in $backupsDir gefunden."
        exit 3
    }
    $BackupFile = $latest.FullName
}

Write-Step "Backup-Datei: $BackupFile"
$steps = [ordered]@{}
$overallStart = Get-Date

Write-Step "pg_restore in Test-DB: $maskedTestUrl"
$t0 = Get-Date
& pg_restore --clean --if-exists --no-password --dbname=$pgTestUrl $BackupFile 2>&1 | ForEach-Object {
    if ($_ -notmatch 'password') { Write-Host "  $_" }
}
if ($LASTEXITCODE -ne 0) {
    Write-Fail "pg_restore fehlgeschlagen (exit $LASTEXITCODE)"
    $steps['pg_restore'] = 'fail'
} else {
    Write-OK "pg_restore abgeschlossen ($([int]((Get-Date)-$t0).TotalSeconds)s)"
    $steps['pg_restore'] = 'pass'
}

if ($steps['pg_restore'] -eq 'pass') {
    Write-Step "Alembic current == head pruefen"
    $t0 = Get-Date
    $env:DATABASE_URL = $env:TEST_DATABASE_URL
    $alembicOutput = & $venvPy -m alembic --config backend/alembic.ini current 2>&1
    if ($LASTEXITCODE -eq 0 -and ($alembicOutput -match 'head')) {
        Write-OK "Alembic: Schema ist auf head ($([int]((Get-Date)-$t0).TotalMilliseconds)ms)"
        $steps['alembic_head'] = 'pass'
    } else {
        Write-Fail "Alembic: Schema nicht auf head. Ausgabe: $alembicOutput"
        $steps['alembic_head'] = 'fail'
    }
} else {
    $steps['alembic_head'] = 'skipped'
}

if ($steps['alembic_head'] -eq 'pass') {
    Write-Step "Login-Test (check_auth_bootstrap.py --no-start-api)"
    $t0 = Get-Date
    Push-Location $repoRoot
    & $venvPy scripts/check_auth_bootstrap.py --no-start-api
    $loginCode = $LASTEXITCODE
    Pop-Location
    if ($loginCode -eq 0) {
        Write-OK "Login-Test PASS ($([int]((Get-Date)-$t0).TotalMilliseconds)ms)"
        $steps['login_test'] = 'pass'
    } else {
        Write-Fail "Login-Test FAIL (exit $loginCode)"
        $steps['login_test'] = 'fail'
    }
} else {
    $steps['login_test'] = 'skipped'
}

$passed  = ($steps.Values | Where-Object { $_ -eq 'pass' }).Count
$failed  = ($steps.Values | Where-Object { $_ -eq 'fail' }).Count
$overall = if ($failed -gt 0) { 'FAIL' } else { 'PASS' }
$duration = [int]((Get-Date) - $overallStart).TotalSeconds

$stepsJson   = ($steps.GetEnumerator() | ForEach-Object { "`"$($_.Key)`": `"$($_.Value)`"" }) -join ", "
$backupEsc   = $BackupFile -replace '\\', '/'

$reportJson = @"
{
  "name": "restore_test_report",
  "timestamp": "$(Get-Date -Format 'yyyy-MM-ddTHH:mm:ssZ')",
  "result": "$overall",
  "backup_file": "$backupEsc",
  "test_database_url": "$maskedTestUrl",
  "duration_seconds": $duration,
  "steps": { $stepsJson }
}
"@
Set-Content -Path $reportPath -Value $reportJson -Encoding UTF8
Write-OK "Report: $reportPath"

if ($overall -eq 'PASS') {
    Write-Host "`n[run_restore_test] STATUS: PASS ($duration s)" -ForegroundColor Green
    exit 0
} else {
    Write-Host "`n[run_restore_test] STATUS: FAIL ($duration s)" -ForegroundColor Red
    exit 1
}

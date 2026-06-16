<#
.SYNOPSIS
  Fuehrt den Local Final Gate Validator v2 aus und schreibt den Report.

.DESCRIPTION
  Voraussetzungen:
    - DATABASE_URL gesetzt (DB erreichbar)
    - TEST_DATABASE_URL gesetzt (Gate-Tests)
    - Backend nicht zwingend laufend (lokale Tests)
  Output:
    - reports/current/final_gate_report.json

.EXAMPLE
  .\scripts\run_final_gate.ps1
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot   = Split-Path -Parent $scriptDir
$backendDir = Join-Path $repoRoot 'backend'
$venvPy     = Join-Path $backendDir '.venv\Scripts\python.exe'
$reportPath = Join-Path $repoRoot 'reports\current\final_gate_report.json'

function Write-Step([string]$msg) { Write-Host "`n[run_final_gate] $msg" -ForegroundColor Cyan }
function Write-OK([string]$msg)   { Write-Host "  [OK] $msg" -ForegroundColor Green }
function Write-Fail([string]$msg) { Write-Host "  [FAIL] $msg" -ForegroundColor Red }

if (-not (Test-Path $venvPy)) {
    Write-Fail "Backend-Venv nicht gefunden: $venvPy"
    exit 1
}

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
    Write-Fail "TEST_DATABASE_URL ist nicht gesetzt. Gate-Tests koennen nicht ausgefuehrt werden."
    Write-Host "  Setze TEST_DATABASE_URL in .env und fuehre den Befehl erneut aus."
    exit 2
}

Write-Step "pytest -m local_gate"
$t0 = Get-Date
Push-Location $repoRoot
& $venvPy -m pytest tests/api -m local_gate -v --tb=short --no-header
$pytestCode = $LASTEXITCODE
Pop-Location
if ($pytestCode -ne 0) {
    Write-Fail "pytest local_gate fehlgeschlagen (exit $pytestCode)"
    exit $pytestCode
}
Write-OK "pytest local_gate PASS ($([int]((Get-Date)-$t0).TotalSeconds)s)"

Write-Step "report_integrity_v2 generieren"
Push-Location $repoRoot
& $venvPy scripts/generate_report_integrity_v2.py
$riCode = $LASTEXITCODE
Pop-Location
if ($riCode -ne 0) {
    Write-Fail "generate_report_integrity_v2.py fehlgeschlagen (exit $riCode)"
    exit $riCode
}
Write-OK "report_integrity_v2 generiert"

Write-Step "local_final_gate_validator_v2 ausfuehren"
Push-Location $repoRoot
& $venvPy scripts/local_final_gate_validator_v2.py
$gateCode = $LASTEXITCODE
Pop-Location

if ($gateCode -eq 0) {
    Write-OK "Local Final Gate: PASS"
    Write-Host "`n[run_final_gate] STATUS: PASS" -ForegroundColor Green
} else {
    Write-Fail "Local Final Gate: BLOCKED (exit $gateCode)"
    Write-Host "  Report: $reportPath"
    Write-Host "`n[run_final_gate] STATUS: BLOCKED" -ForegroundColor Red
}
exit $gateCode

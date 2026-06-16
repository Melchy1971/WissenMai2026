<#
.SYNOPSIS
  Erstellt ein PostgreSQL-Backup der Produktions-DB.

.DESCRIPTION
  - Liest DATABASE_URL aus .env
  - Fuehrt pg_dump aus
  - Verifiziert Backup (Dateigroesse > 0, pg_restore --list)
  - Schreibt Report: reports/current/backup_report.json
  - Exit 0 = PASS, Exit != 0 = FAIL
  - Keine Credentials im Log

.EXAMPLE
  .\scripts\run_backup.ps1
  .\scripts\run_backup.ps1 -OutputDir H:\backups
#>
[CmdletBinding()]
param(
    [string] $OutputDir = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot  = Split-Path -Parent $scriptDir
$timestamp = Get-Date -Format 'yyyy-MM-dd_HH-mm'

if (-not $OutputDir) { $OutputDir = Join-Path $repoRoot 'backups' }
$backupFile  = Join-Path $OutputDir "$timestamp.dump"
$reportPath  = Join-Path $repoRoot 'reports\current\backup_report.json'

function Write-Step([string]$msg) { Write-Host "`n[run_backup] $msg" -ForegroundColor Cyan }
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

if (-not $env:DATABASE_URL) {
    Write-Fail "DATABASE_URL nicht gesetzt."
    exit 2
}

$maskedUrl = Mask-Url $env:DATABASE_URL

# pg_dump URL-Format konvertieren
$pgUrl = $env:DATABASE_URL -replace '^postgresql\+psycopg://', 'postgresql://'

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$overallStart = Get-Date
$steps = [ordered]@{}

Write-Step "pg_dump -> $backupFile"
Write-Host "  DB: $maskedUrl"
$t0 = Get-Date
$env:PGPASSWORD = ''  # pg_dump liest aus URL
& pg_dump --format=custom --no-password --dbname=$pgUrl --file=$backupFile 2>&1 | ForEach-Object {
    if ($_ -notmatch 'password') { Write-Host "  $_" }
}
if ($LASTEXITCODE -ne 0) {
    Write-Fail "pg_dump fehlgeschlagen (exit $LASTEXITCODE)"
    $steps['pg_dump'] = 'fail'
} else {
    $size = (Get-Item $backupFile).Length
    Write-OK "Backup erstellt: $backupFile ($size Bytes, $([int]((Get-Date)-$t0).TotalSeconds)s)"
    $steps['pg_dump'] = 'pass'
}

if ($steps['pg_dump'] -eq 'pass') {
    Write-Step "Backup verifizieren (pg_restore --list)"
    $t0 = Get-Date
    $listOutput = & pg_restore --list $backupFile 2>&1
    if ($LASTEXITCODE -eq 0 -and $listOutput.Count -gt 0) {
        Write-OK "Backup verifiziert: $($listOutput.Count) Eintraege ($([int]((Get-Date)-$t0).TotalMilliseconds)ms)"
        $steps['verify'] = 'pass'
    } else {
        Write-Fail "Backup-Verifikation fehlgeschlagen"
        $steps['verify'] = 'fail'
    }
} else {
    $steps['verify'] = 'skipped'
}

$passed  = ($steps.Values | Where-Object { $_ -eq 'pass' }).Count
$failed  = ($steps.Values | Where-Object { $_ -eq 'fail' }).Count
$overall = if ($failed -gt 0) { 'FAIL' } else { 'PASS' }
$duration = [int]((Get-Date) - $overallStart).TotalSeconds

$stepsJson = ($steps.GetEnumerator() | ForEach-Object { "`"$($_.Key)`": `"$($_.Value)`"" }) -join ", "
$sizeBytes = if (Test-Path $backupFile) { (Get-Item $backupFile).Length } else { 0 }

$reportJson = @"
{
  "name": "backup_report",
  "timestamp": "$(Get-Date -Format 'yyyy-MM-ddTHH:mm:ssZ')",
  "result": "$overall",
  "backup_file": "$($backupFile -replace '\\', '/')",
  "backup_size_bytes": $sizeBytes,
  "duration_seconds": $duration,
  "database_url": "$maskedUrl",
  "steps": { $stepsJson }
}
"@
Set-Content -Path $reportPath -Value $reportJson -Encoding UTF8
Write-OK "Report: $reportPath"

if ($overall -eq 'PASS') {
    Write-Host "`n[run_backup] STATUS: PASS ($duration s)" -ForegroundColor Green
    exit 0
} else {
    Write-Host "`n[run_backup] STATUS: FAIL ($duration s)" -ForegroundColor Red
    exit 1
}

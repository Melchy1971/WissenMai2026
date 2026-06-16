<#
.SYNOPSIS
  Startet das Backend (FastAPI, Port 8000).

.DESCRIPTION
  - Laedt .env
  - Prueft DATABASE_URL
  - Prueft Venv
  - Startet uvicorn mit --reload

.EXAMPLE
  .\scripts\start_backend.ps1
  .\scripts\start_backend.ps1 -Port 8001
#>
[CmdletBinding()]
param([int] $Port = 8000)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot   = Split-Path -Parent $scriptDir
$backendDir = Join-Path $repoRoot 'backend'
$venvPy     = Join-Path $backendDir '.venv\Scripts\python.exe'

function Write-Fail([string]$msg) { Write-Host "[start_backend] FAIL: $msg" -ForegroundColor Red }

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

if (-not (Test-Path $venvPy)) {
    Write-Fail "Backend-Venv nicht gefunden: $venvPy"
    Write-Host "  cd backend && python -m venv .venv && .venv\Scripts\pip install -e .[dev]"
    exit 1
}

if (-not $env:DATABASE_URL) {
    Write-Fail "DATABASE_URL nicht gesetzt. Setze DATABASE_URL in .env."
    exit 2
}

Write-Host "[start_backend] Starte FastAPI auf Port $Port ..." -ForegroundColor Cyan
Write-Host "  URL: http://127.0.0.1:$Port"
Write-Host "  Health: http://127.0.0.1:$Port/health"
Write-Host "  API Docs: http://127.0.0.1:$Port/docs"
Write-Host "  Stoppen: Ctrl+C"
Write-Host ""

& $venvPy -m uvicorn --app-dir $backendDir app.main:app --reload --host 127.0.0.1 --port $Port

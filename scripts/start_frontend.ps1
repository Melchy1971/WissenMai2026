<#
.SYNOPSIS
  Startet das Frontend (Vite Dev Server, Port 5173).

.DESCRIPTION
  - Prueft package.json
  - Prueft node_modules
  - Startet npm run dev

.EXAMPLE
  .\scripts\start_frontend.ps1
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot    = Split-Path -Parent $scriptDir
$frontendDir = Join-Path $repoRoot 'frontend'

function Write-Fail([string]$msg) { Write-Host "[start_frontend] FAIL: $msg" -ForegroundColor Red }

if (-not (Test-Path (Join-Path $frontendDir 'package.json'))) {
    Write-Fail "frontend/package.json nicht gefunden."
    exit 1
}

if (-not (Test-Path (Join-Path $frontendDir 'node_modules'))) {
    Write-Fail "node_modules nicht gefunden."
    Write-Host "  cd frontend && npm install"
    exit 1
}

Write-Host "[start_frontend] Starte Vite Dev Server ..." -ForegroundColor Cyan
Write-Host "  URL: http://127.0.0.1:5173"
Write-Host "  Stoppen: Ctrl+C"
Write-Host ""

npm --prefix $frontendDir run dev -- --host 127.0.0.1

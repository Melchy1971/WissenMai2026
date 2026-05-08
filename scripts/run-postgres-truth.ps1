Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
$backendDir = Join-Path $repoRoot 'backend'
$venvPython = Join-Path $backendDir '.venv\Scripts\python.exe'
$reportScript = Join-Path $scriptDir 'generate_postgres_truth_report.py'

if (-not (Test-Path $venvPython)) {
    throw "Backend virtual environment not found at $venvPython. Create it first and install requirements.txt plus requirements-dev.txt."
}

Push-Location $backendDir
try {
    & $venvPython $reportScript
}
finally {
    Pop-Location
}
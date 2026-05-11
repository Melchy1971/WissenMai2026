Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
$backendPython = Join-Path $repoRoot 'backend\.venv\Scripts\python.exe'
$rootPython = Join-Path $repoRoot '.venv\Scripts\python.exe'
$validator = Join-Path $scriptDir 'validate_m4_truth_gate.py'

if (Test-Path $backendPython) {
    & $backendPython $validator
    exit $LASTEXITCODE
}

if (Test-Path $rootPython) {
    & $rootPython $validator
    exit $LASTEXITCODE
}

& python $validator
exit $LASTEXITCODE

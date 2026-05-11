Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$runTruth = Join-Path $scriptDir 'run-postgres-truth.ps1'
$validateGate = Join-Path $scriptDir 'validate-m4-truth-gate.ps1'

& $runTruth
& $validateGate

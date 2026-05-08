Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir

Push-Location $repoRoot
try {
    docker compose -f docker-compose.test.yml up -d --wait testdb
}
finally {
    Pop-Location
}
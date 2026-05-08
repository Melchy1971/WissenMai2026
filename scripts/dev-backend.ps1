Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
$backendDir = Join-Path $repoRoot 'backend'
$venvPython = Join-Path $backendDir '.venv\Scripts\python.exe'
$localDevDatabaseUrl = 'postgresql+psycopg://testuser:testpass@127.0.0.1:5433/wissen_test'
$bootstrapScript = Join-Path $repoRoot 'scripts\bootstrap_local_backend.py'

if (-not (Test-Path $venvPython)) {
    throw "Backend virtual environment not found at $venvPython. Create it first with Python 3.13."
}

if (-not $env:DATABASE_URL) {
    $env:DATABASE_URL = $localDevDatabaseUrl
}

& $venvPython -c "import os, sys, psycopg; url=os.environ.get('DATABASE_URL');
if not url:
    raise SystemExit('DATABASE_URL is missing. Set DATABASE_URL or start the local dev database with scripts/dev-db.ps1.')
try:
    conn = psycopg.connect(url.replace('postgresql+psycopg://', 'postgresql://', 1), connect_timeout=3)
    conn.close()
except Exception as exc:
    raise SystemExit(f'Cannot connect to DATABASE_URL={url}. Start the local dev database with scripts/dev-db.ps1 or set DATABASE_URL explicitly. Root cause: {exc}')";
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

& $venvPython $bootstrapScript
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

& $venvPython -m uvicorn --app-dir $backendDir app.main:app --reload --host 127.0.0.1 --port 8000
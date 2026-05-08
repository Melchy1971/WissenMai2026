$ErrorActionPreference = 'Stop'
$repo = 'h:\WissenMai2026'
$backend = Join-Path $repo 'backend'
$python = Join-Path $backend '.venv\Scripts\python.exe'
$env:DATABASE_URL = 'postgresql+psycopg://testuser:testpass@127.0.0.1:5433/wissen_test'
Set-Location $backend
& $python -m uvicorn app.main:app --host 127.0.0.1 --port 8001

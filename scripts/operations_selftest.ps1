# operations_selftest.ps1
# Ziel: Systemzustand für M4e Operations Release automatisiert prüfen
# Output: operations_selftest_report.json, Exit Code 0 nur bei vollständigem PASS

$report = @{}
$report["timestamp"] = (Get-Date).ToString("o")
$success = $true

function Write-Result($key, $value) {
    $serializable = @{
        Passed = $value.Passed
        Output = ($value.Output | Out-String)
    }
    $report[$key] = $serializable
    if (-not $value.Passed) { $global:success = $false }
}

# 1. PostgreSQL erreichbar
try {
    $pgResult = psql -U appuser -d wissen2026 -c "SELECT 1;" 2>&1
    Write-Result "PostgreSQL" @{Passed=$pgResult -match "1"; Output=$pgResult}
} catch { Write-Result "PostgreSQL" @{Passed=$false; Output=$_} }

# 2. Alembic Head
try {
    $alembicResult = & python -m alembic heads 2>&1
    Write-Result "AlembicHead" @{Passed=$alembicResult -match "head"; Output=$alembicResult}
} catch { Write-Result "AlembicHead" @{Passed=$false; Output=$_} }

# 3. Seed User vorhanden
try {
    $userResult = psql -U appuser -d wissen2026 -c "SELECT * FROM users WHERE is_default = true;" 2>&1
    Write-Result "SeedUser" @{Passed=$userResult -match "1 row"; Output=$userResult}
} catch { Write-Result "SeedUser" @{Passed=$false; Output=$_} }

# 4. Login erfolgreich (API)
try {
    $loginResult = Invoke-RestMethod -Uri "http://localhost:8000/api/auth/login" -Method Post -Body '{"login":"seeduser","password":"testpass"}' -ContentType "application/json" -ErrorAction Stop
    Write-Result "Login" @{Passed=$loginResult.token -ne $null; Output=$loginResult}
} catch { Write-Result "Login" @{Passed=$false; Output=$_} }

# 5. Backend /health
try {
    $healthResult = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get -ErrorAction Stop
    Write-Result "BackendHealth" @{Passed=$healthResult.status -eq "ok"; Output=$healthResult}
} catch { Write-Result "BackendHealth" @{Passed=$false; Output=$_} }

# 6. Frontend erreichbar
try {
    $frontendResult = Invoke-WebRequest -Uri "http://localhost:5173" -UseBasicParsing -ErrorAction Stop
    Write-Result "Frontend" @{Passed=$frontendResult.StatusCode -eq 200; Output=$frontendResult.StatusCode}
} catch { Write-Result "Frontend" @{Passed=$false; Output=$_} }

# 7. Search funktionsfähig
try {
    $searchResult = Invoke-RestMethod -Uri "http://localhost:8000/api/search?query=test" -Method Get -ErrorAction Stop
    Write-Result "Search" @{Passed=$searchResult.results.Count -gt 0; Output=$searchResult}
} catch { Write-Result "Search" @{Passed=$false; Output=$_} }

# 8. Backup erzeugbar
try {
    Push-Location backend
    $backupResult = & .venv\Scripts\python.exe -m app.scripts.backup_create --output ..\temp_selftest_backup.json 2>&1
    Pop-Location
    Write-Result "Backup" @{Passed=$backupResult -match "completed"; Output=$backupResult}
} catch { Write-Result "Backup" @{Passed=$false; Output=$_} }

# 9. Restore testbar
try {
    Push-Location backend
    $restoreResult = & .venv\Scripts\python.exe -m app.scripts.backup_restore --input ..\temp_selftest_backup.json 2>&1
    Pop-Location
    Write-Result "Restore" @{Passed=$restoreResult -match "completed"; Output=$restoreResult}
} catch { Write-Result "Restore" @{Passed=$false; Output=$_} }

# 10. Reindex erfolgreich
try {
    Push-Location backend
    $reindexResult = & .venv\Scripts\python.exe -m app.scripts.reindex_full 2>&1
    Pop-Location
    Write-Result "Reindex" @{Passed=$reindexResult -match "completed"; Output=$reindexResult}
} catch { Write-Result "Reindex" @{Passed=$false; Output=$_} }

# Report schreiben
$report | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 operations_selftest_report.json

if ($success) {
    Write-Host "Selftest erfolgreich. Alle Prüfungen bestanden."
    exit 0
} else {
    Write-Host "Selftest FEHLGESCHLAGEN. Siehe operations_selftest_report.json."
    exit 1
}

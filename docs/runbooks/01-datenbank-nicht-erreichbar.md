# Runbook: Datenbank nicht erreichbar

## Symptom

- Backend-Start schlaegt fehl: `FAIL: DATABASE_URL nicht gesetzt` oder `connection refused`
- Health-Check `/health/db` gibt HTTP 503 zurueck
- API-Requests schlagen mit HTTP 500 fehl, Logs zeigen `sqlalchemy.exc.OperationalError`
- `start_backend.ps1` bricht mit Exit 2 ab

## Diagnose

```powershell
# 1. DATABASE_URL in .env vorhanden?
Get-Content .env | Select-String "DATABASE_URL"

# 2. Verbindung prufen (PostgreSQL-Client erforderlich)
$env:PGPASSWORD = "***"
psql $env:DATABASE_URL -c "SELECT 1"

# 3. Port erreichbar?
$uri = [Uri]$env:DATABASE_URL
Test-NetConnection -ComputerName $uri.Host -Port $uri.Port

# 4. Backend-Log auf OperationalError pruefen
.\scripts\start_backend.ps1 2>&1 | Select-String "OperationalError|could not connect|refused"
```

## Sofortmassnahmen

1. `.env` oeffnen, `DATABASE_URL` auf korrektes Format pruefen: `postgresql+psycopg://user:pass@host:5432/dbname`
2. PostgreSQL-Dienst auf Zielserver pruefen (VPS: `systemctl status postgresql`)
3. Firewall pruefen: Port 5432 zwischen Backend-Host und DB-Host offen?
4. Bei lokalem PostgreSQL: `pg_lsclusters` oder `Get-Service postgresql*`

## Recovery

```powershell
# Lokale Entwicklung: PostgreSQL starten
Start-Service postgresql-x64-18   # Windows-Dienst-Name variiert

# VPS:
# ssh user@server "systemctl start postgresql"

# .env korrigieren, dann Backend neu starten
.\scripts\start_backend.ps1
curl http://localhost:8000/health/db
```

## Eskalation

Wenn DB erreichbar aber Verbindung schlaegt fehl: Credentials pruefen (nie in Git committen). Wenn Port geblockt: Netzwerk-/Firewall-Verantwortlichen einbeziehen.

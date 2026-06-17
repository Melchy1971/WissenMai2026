# Runbook: Login funktioniert nicht

## Symptom

- `/login` zeigt Fehlermeldung "Ungueltige Zugangsdaten"
- HTTP 401 von `/api/v1/auth/login`
- HTTP 403 von einem Endpunkt nach erfolgreichem Login
- Token-Fehler nach Page-Reload ("Session abgelaufen")
- Weisser Bildschirm nach Login

## Diagnose

```powershell
# 1. Seed-User in DB vorhanden?
cd backend
.venv\Scripts\python scripts\check_auth_bootstrap.py --no-start-api

# 2. Auth-Endpoint direkt testen (Passwort aus .env)
$creds = @{ username = $env:SEED_ADMIN_LOGIN; password = $env:SEED_ADMIN_PASSWORD } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auth/login" `
    -Method Post -ContentType "application/json" -Body $creds

# 3. Token-Validierung (workspace_id erforderlich)
# x-workspace-id Header fehlt -> 400/422

# 4. Logs auf AuthenticationError pruefen
# Backend-Log: status=failed, event_name=auth_failure
```

## Sofortmassnahmen

1. "Ungueltige Zugangsdaten": `SEED_ADMIN_LOGIN` / `SEED_ADMIN_PASSWORD` in `.env` pruefen
2. Seed-User fehlt: `.\scripts\dev_bootstrap.ps1` ausfuehren (legt Seed-User an)
3. Token abgelaufen / Weisser Bildschirm: Browser `localStorage.clear()`, neu einloggen
4. HTTP 403 nach Login: `x-workspace-id`-Header in Request pruefen

## Recovery

```powershell
# Seed-User neu anlegen (loescht keine Daten)
cd backend
.venv\Scripts\python scripts\check_auth_bootstrap.py --no-start-api

# Wenn Seed-User korrekt aber Login schlaegt fehl:
# Passwort-Reset via direktem DB-Update (nur Entwicklung, nie Produktion ohne Backup)
.\scripts\run_backup.ps1  # zuerst Backup
# dann: alembic-Seed-Script oder manuelles Passwort-Reset-Script
```

## Eskalation

Wenn `check_auth_bootstrap.py` PASS aber Login schlaegt weiterhin fehl: Backend-Log auf `AuthenticationError` pruefen, JWT-Secret-Konfiguration in `.env` verifizieren. Token-Signatur-Fehler deuten auf geaendertes JWT-Secret hin.

---

## Symptom (PRI-6): Admin-Bereich zeigt 403 obwohl eingeloggt

**Ursache:** Benutzer hat `role !== 'admin'`. Der `AdminRoute`-Guard in `routes.jsx` verweigert den Zugriff.

**Diagnose:**
```
GET /api/v1/auth/me → prüfe "role"-Feld in JSON-Response
```

**Lösung:** Admin-Rechte über Benutzerverwaltung vergeben. Kein Frontend-Fix erforderlich — Verhalten ist korrekt.

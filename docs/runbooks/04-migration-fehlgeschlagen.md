# Runbook: Migration fehlgeschlagen

## Symptom

- `alembic upgrade head` gibt Fehler zurueck
- Backend-Startup schlaegt mit `alembic.util.exc.CommandError` fehl
- `alembic current` zeigt nicht `head`
- Datenbanktabellen fehlen oder Schema weicht ab

## Diagnose

```powershell
cd backend

# 1. Aktueller Migrations-Stand
.venv\Scripts\alembic current

# 2. Verfuegbare Migrationen
.venv\Scripts\alembic history --verbose

# 3. Konflikt zwischen Migration-Heads?
.venv\Scripts\alembic heads

# 4. Konkreten Fehler anzeigen
.venv\Scripts\alembic upgrade head 2>&1
```

## Sofortmassnahmen

1. Mehrere Heads (Branch-Konflikt): `alembic merge heads -m "merge"`, dann `alembic upgrade head`
2. Tabelle bereits vorhanden: Migration-Skript pruefen auf `IF NOT EXISTS`-Guards
3. Datenbankverbindung fehlgeschlagen: Runbook 01 (DB nicht erreichbar) anwenden
4. Revision nicht gefunden: `.env` auf korrekte DB zeigen pruefen

## Recovery

```powershell
# Nur wenn Datenbank leer / Test-DB:
.venv\Scripts\alembic downgrade base
.venv\Scripts\alembic upgrade head

# Produktions-DB: NIEMALS downgrade ohne Backup!
# Erst Backup erstellen:
.\scripts\run_backup.ps1
# Dann Migration versuchen:
.venv\Scripts\alembic upgrade head
```

Nach erfolgreicher Migration verifizieren:
```powershell
.venv\Scripts\alembic current
# Ausgabe muss "(head)" enthalten
```

## Eskalation

Wenn `alembic upgrade head` auf Produktions-DB fehlschlaegt: Sofort stoppen, Backup aus `run_backup.ps1` verwenden, Restore-Test in Test-DB durchfuehren. Kein manuelles SQL ohne Review.

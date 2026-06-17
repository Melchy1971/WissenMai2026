# Maintenance — Ruflo

Stand: 2026-06-17

---

## Regelmäßige Aufgaben

| Aufgabe | Frequenz | Skript |
|---------|---------|--------|
| DB-Backup | täglich 02:00 UTC | scripts/backup_db.sh |
| Backup-Validierung | täglich | scripts/validate_backup.sh |
| Job-Cleanup (abgelaufene Jobs) | täglich 03:00 UTC | via BackgroundJobService |
| Log-Rotation | wöchentlich | logrotate |
| Alembic-Heads prüfen | bei jedem Deploy | alembic current |

---

## Job-Cleanup

Abgelaufene Jobs werden automatisch bereinigt:

```sql
-- completed: 7 Tage
-- failed/cancelled: 14 Tage
-- dead: 30 Tage
```

Cleanup läuft täglich um 03:00 UTC als Background-Task.

---

## Disk-Nutzung überwachen

```bash
# Uploads-Ordner
du -sh uploads/

# Exports-Ordner
du -sh exports/

# DB-Größe
psql $DATABASE_URL -c "SELECT pg_size_pretty(pg_database_size(current_database()));"
```

Schwellenwert: > 80% Disk → Warnung. > 90% → kritisch.

---

## Dependency-Updates

```bash
# Python
pip list --outdated
pip install --upgrade <paket>

# Node
npm outdated
npm update
```

Sicherheits-Updates sofort einspielen. Funktions-Updates: im nächsten Sprint evaluieren.

---

## Datenbank-Wartung

```sql
-- Tabellenstatistiken aktualisieren
ANALYZE;

-- Fragmentierung reduzieren
VACUUM ANALYZE;

-- Index-Nutzung prüfen
SELECT indexname, idx_scan, idx_tup_read
FROM pg_stat_user_indexes
ORDER BY idx_scan;
```

---

## Bekannte Tech-Debt (wartungsrelevant)

| ID | Problem | Impact | Priorität |
|----|---------|--------|-----------|
| TD-004 | Kein GIN-Index auf search_vector | Suchanfragen langsam bei > 10k Chunks | HIGH |
| TD-001 | Zwei Import-Pfade | Inkonsistente Import-Fehler | HIGH |
| TD-007 | God Service backup_restore.py | Wartung aufwändig | MEDIUM |

Vollständige Liste: `docs/technical_debt_register.md`

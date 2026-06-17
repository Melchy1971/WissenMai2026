# Backup/Restore Test Report — PRI-7

Stand: 2026-06-17
Quellen: `reports/current/backup_report.json`, `reports/current/restore_report.json`

---

## Status-Übersicht

| Szenario | Beschreibung | Status | Blocker |
|----------|-------------|--------|---------|
| SCN-01 | Full Backup | SPEZIFIZIERT | SCGB-01 |
| SCN-02 | Incremental Backup | SPEZIFIZIERT | SCGB-01 |
| SCN-03 | Restore Empty System | NICHT_GETESTET | SCGB-01 |
| SCN-04 | Restore Existing System | NICHT_GETESTET | SCGB-01 |
| SCN-05 | Restore nach Fehler | NICHT_GETESTET | SCGB-01 |
| SCN-06 | Datenintegrität prüfen | NICHT_GETESTET | SCGB-01 |

**Gesamtstatus: NICHT_GETESTET (Blocker: SCGB-01)**

Alle 6 Szenarien sind spezifiziert. Ausführung erst möglich nach Schließung von SCGB-01 (TEST_DATABASE_URL, DevOps).

---

## Backup-Komponenten

| ID | Komponente | Methode | Schätzgröße |
|----|-----------|---------|-------------|
| BK-01 | PostgreSQL Datenbank | pg_dump --format=custom | 50 MB |
| BK-02 | Uploads | tar.gz | 500 MB |
| BK-03 | Exports | tar.gz | 200 MB |
| BK-04 | Reports | tar.gz | 10 MB |
| BK-05 | Konfiguration | tar.gz (GPG-verschlüsselt) | 1 MB |

---

## Backup-Strategie

- **Full Backup:** täglich 02:00 UTC, 30 Tage Aufbewahrung
- **Incremental:** stündlich via WAL-Archivierung, 7 Tage Aufbewahrung
- **Validierung:** Nach jeder Erstellung `pg_restore --list` + `tar -tzf`

---

## Restore-Prozedur (spezifiziert)

```bash
# 1. Datenbank
pg_restore -d $TARGET_DB backup_db_*.dump

# 2. Schema (bei leerem System)
alembic upgrade head

# 3. Dateien
tar -xzf backup_uploads_*.tar.gz -C uploads/
tar -xzf backup_exports_*.tar.gz -C exports/
tar -xzf backup_reports_*.tar.gz -C reports/

# 4. Integritätsprüfung
python scripts/validate_restore.py
```

**RTO-Ziel:** 30 Minuten | **RPO-Ziel:** 1 Stunde

---

## Nächste Schritte

1. SCGB-01 schließen (DevOps: TEST_DATABASE_URL bereitstellen)
2. `scripts/backup_*.sh` implementieren
3. Backup-Tests in CI-Pipeline integrieren
4. Restore-Validierungsskript `scripts/validate_restore.py` implementieren
